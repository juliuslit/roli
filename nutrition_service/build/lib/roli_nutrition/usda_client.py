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
DETAIL_QUERY = "format=full&nutrients=606,601"
SEARCH_DATA_TYPES = ["Foundation", "SR Legacy"]

RETRY_DELAYS_SECONDS = (0.5, 1.0)  # at most two retries, i.e. three requests in total
RETRY_STATUSES = {500, 502, 503, 504}
TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


class UsdaError(RoliNutritionError):
    """USDA could not give us a usable reply. ``requests`` says how many were made."""

    def __init__(self, code: str, message: str, requests: int) -> None:
        super().__init__(code, message)
        self.requests = requests


@dataclass(frozen=True)
class UsdaReply:
    body: Any  # parsed JSON; its shape is checked later by nutrients.py
    requests: int  # how many HTTP requests this call made, for the log line


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
    ) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=TIMEOUT,
            transport=transport,
            follow_redirects=False,
        )
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    # -- the two requests ---------------------------------------------------

    def get_food(self, fdc_id: int) -> UsdaReply:
        """Spec 5.3: ``GET /food/{fdcId}?format=full&nutrients=606,601``."""
        request = self._client.build_request("GET", f"/food/{int(fdc_id)}?{DETAIL_QUERY}")
        return self._send(request, not_found_code="not_found")

    def search(self, query: str, page_size: int) -> UsdaReply:
        """Spec 5.4: ``POST /foods/search`` with the fixed body. No ``sortBy``."""
        body = {"query": query, "dataType": list(SEARCH_DATA_TYPES), "pageSize": int(page_size)}
        request = self._client.build_request("POST", "/foods/search", json=body)
        # A 404 on the search endpoint would be unexpected, not "food not found".
        return self._send(request, not_found_code="usda_unavailable")

    # -- sending, retrying, status mapping ----------------------------------

    def _send(self, request: httpx.Request, *, not_found_code: str) -> UsdaReply:
        attempts = 0
        while True:
            attempts += 1
            try:
                response = self._client.send(request)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                if self._can_retry(attempts):
                    continue
                raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)
            except httpx.HTTPError:
                raise UsdaError("usda_unavailable", MESSAGES["usda_unavailable"], attempts)

            status = response.status_code
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
                # No retry: USDA blocks the key for an hour once this happens.
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
