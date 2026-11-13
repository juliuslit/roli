"""Talks to USDA FoodData Central and nothing else.

Responsibilities: build the two requests (spec 5.3 and 5.4), send the key in the
``X-Api-Key`` header, retry on transient failures, and translate HTTP status
codes into our error codes (spec 5.5). It does not interpret the food data;
that is ``nutrients.py``.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .errors import RoliNutritionError

logger = logging.getLogger("roli_nutrition")

# A constant, not a setting: no request may go anywhere else.
BASE_URL = "https://api.nal.usda.gov/fdc/v1"
USDA_HOST = "api.nal.usda.gov"

# Nutrient *numbers* (used in the request filter), not nutrient IDs.
DETAIL_QUERY = "format=full&nutrients=606,601,204"     # 204 total fat: spec v2.5
SEARCH_DATA_TYPES = ["Foundation", "SR Legacy"]            # the default search; Survey (FNDDS) only when a caller asks for it (spec v2.2)
SURVEY_DATA_TYPE = "Survey (FNDDS)"
ALL_SEARCH_DATA_TYPES = ("Foundation", "SR Legacy", SURVEY_DATA_TYPE)

RETRY_DELAYS_SECONDS = (0.5, 1.0)  # at most two retries, i.e. three requests in total
RETRY_STATUSES = {500, 502, 503, 504}
TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
# api.data.gov sends the key's hourly allowance on every reply (read live 2026-11-05: limit 3600, remaining counts down within a rolling hour).
RATE_LIMIT_HEADER, RATE_REMAINING_HEADER = "x-ratelimit-limit", "x-ratelimit-remaining"
HALT_SECONDS_DEFAULT = 3600.0               # after a 429 the client refuses to ask USDA again for this long (spec v2.3, 18.2); 0 disables
LIST_SORT_FIELDS = ("dataType.keyword", "lowercaseDescription.keyword", "fdcId", "publishedDate")   # fdc_api.json, FoodListCriteria.sortBy


class UsdaError(RoliNutritionError):
    """USDA could not give us a usable reply. ``requests`` says how many were made."""

    def __init__(self, code: str, message: str, requests: int) -> None:
        super().__init__(code, message)
        self.requests = requests


@dataclass(frozen=True)
class UsdaReply:
    body: Any  # parsed JSON; its shape is checked later by nutrients.py
    requests: int  # how many HTTP requests this call made, for the log line


@dataclass(frozen=True)
class Allowance:
    """The key's hourly allowance as USDA last reported it (spec v2.3, 18.3). ``remaining`` is None until the first reply."""
    limit: int | None = None
    remaining: int | None = None
    observed_at: float | None = None        # time.time() of the reply that carried the headers
    halted_until: float | None = None       # time.time() until which the client refuses to send (after a 429)

    @property
    def halted(self) -> bool:
        return self.halted_until is not None and time.time() < self.halted_until


MESSAGES = {
    "not_found": "USDA has no food with this FDC ID.",
    "rate_limited": "USDA rate limit reached. Try again in an hour.",
    "usda_auth_failed": "USDA rejected the API key.",
    "usda_unavailable": "USDA could not be reached.",
    "malformed_response": "USDA reply was not in the expected format.",
}


class UsdaClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        halt_seconds: float = HALT_SECONDS_DEFAULT,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=TIMEOUT,
            transport=transport,
            follow_redirects=False,
        )
        self._sleep = sleep
        self._halt_seconds = float(halt_seconds)
        self._clock = clock
        self._allowance = Allowance()
        self._halted_until: float | None = None
        self.requests_sent = 0                  # HTTP requests this client actually sent (a halted or cached call sends none)

    # -- allowance and refusal (spec v2.3, 18.2-18.3) --------------------------------------

    @property
    def allowance(self) -> Allowance:
        return Allowance(limit=self._allowance.limit, remaining=self._allowance.remaining, observed_at=self._allowance.observed_at, halted_until=self._halted_until)

    @property
    def halted(self) -> bool:
        return self._halted_until is not None and self._clock() < self._halted_until

    def reset_halt(self) -> None:
        """Lift the refusal early (a person's decision, or a test); USDA's own hour is the real clock."""
        self._halted_until = None

    def _note_headers(self, response: httpx.Response) -> None:
        limit, remaining = response.headers.get(RATE_LIMIT_HEADER), response.headers.get(RATE_REMAINING_HEADER)
        if limit is None and remaining is None:
            return
        try:
            self._allowance = Allowance(limit=int(limit) if limit is not None else self._allowance.limit,
                                        remaining=int(remaining) if remaining is not None else self._allowance.remaining, observed_at=self._clock())
        except ValueError:
            pass

    def close(self) -> None:
        self._client.close()

    # -- the two requests ---------------------------------------------------

    def get_food(self, fdc_id: int) -> UsdaReply:
        """Spec 5.3 and v2.5: ``GET /food/{fdcId}?format=full&nutrients=606,601,204``."""
        request = self._client.build_request("GET", f"/food/{int(fdc_id)}?{DETAIL_QUERY}")
        return self._send(request, not_found_code="not_found")

    def search(self, query: str, page_size: int, data_types: list[str] | tuple[str, ...] | None = None) -> UsdaReply:
        """Spec 5.4: ``POST /foods/search`` with the fixed body. No ``sortBy``. ``data_types`` narrows or widens the default (spec v2.2)."""
        body = {"query": query, "dataType": list(data_types or SEARCH_DATA_TYPES), "pageSize": int(page_size)}
        request = self._client.build_request("POST", "/foods/search", json=body)
        # A 404 on the search endpoint would be unexpected, not "food not found".
        return self._send(request, not_found_code="usda_unavailable")

    def list_foods(self, data_types: list[str] | tuple[str, ...], *, page_size: int = 1, sort_by: str = "publishedDate", sort_order: str = "desc") -> UsdaReply:
        """Spec v2.3, 18.4: ``POST /foods/list`` (fdc_api.json, ``postFoodsList``, body ``FoodListCriteria``) returns abridged foods with their
        ``publicationDate``; sorted by ``publishedDate`` descending with ``pageSize`` 1 it is one request that names the newest publication date of a
        table, which is how a new FoodData Central release is detected. Nothing from the reply but descriptions, ids and dates is ever used."""
        if sort_by not in LIST_SORT_FIELDS:
            raise ValueError(f"sort_by must be one of {LIST_SORT_FIELDS}")
        body = {"dataType": list(data_types), "pageSize": int(page_size), "pageNumber": 1, "sortBy": sort_by, "sortOrder": sort_order}
        request = self._client.build_request("POST", "/foods/list", json=body)
        return self._send(request, not_found_code="usda_unavailable")

    # -- sending, retrying, status mapping ----------------------------------

    def _send(self, request: httpx.Request, *, not_found_code: str) -> UsdaReply:
        if self.halted:
            # spec v2.3, 18.2: after the first 429 nothing more is asked of USDA until the hour has passed; no request is sent
            raise UsdaError("rate_limited", MESSAGES["rate_limited"], 0)
        attempts = 0
        while True:
            attempts += 1
            try:
                self.requests_sent += 1
                response = self._client.send(request)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                if self._can_retry(attempts):
                    continue
                raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)
            except httpx.HTTPError:
                raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)

            status = response.status_code
            self._note_headers(response)
            if status == 200:
                return UsdaReply(body=self._parse_json(response, attempts), requests=attempts)
            if status in RETRY_STATUSES:
                if self._can_retry(attempts):
                    continue
                raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)
            if status == 404:
                raise UsdaError(not_found_code, MESSAGES[not_found_code], attempts)
            if status == 403:
                raise UsdaError("usda_auth_failed", MESSAGES["usda_auth_failed"], attempts)
            if status == 429:
                # No retry: USDA blocks the key for an hour once this happens, and from now on this client refuses to ask (spec v2.3, 18.2).
                if self._halt_seconds > 0:
                    self._halted_until = self._clock() + self._halt_seconds
                raise UsdaError("rate_limited", MESSAGES["rate_limited"], attempts)
            # 400 and anything unexpected.
            raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)

    def _can_retry(self, attempts: int) -> bool:
        """Sleep and return True if another attempt is allowed; otherwise False."""
        if attempts > len(RETRY_DELAYS_SECONDS):
            return False
        self._sleep(RETRY_DELAYS_SECONDS[attempts - 1])
        return True

    @staticmethod
    def _parse_json(response: httpx.Response, attempts: int) -> Any:
        try:
            return json.loads(response.content)
        except (ValueError, UnicodeDecodeError):
            raise UsdaError("malformed_response", MESSAGES["malformed_response"], attempts) from None
