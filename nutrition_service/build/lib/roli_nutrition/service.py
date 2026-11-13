"""NutritionService: input checks, USDA client, validation, cache, one log line per call.

After construction it never raises to its caller: every failure comes back as an
``ErrorResult``. Safe to call from several threads at once.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Hashable

from .config import Settings
from .errors import RoliNutritionError
from .nutrients import extract_nutrition, parse_search
from .schemas import ErrorResult, NutritionResult, SearchResult
from .usda_client import UsdaClient, UsdaError

logger = logging.getLogger("roli_nutrition")

QUERY_MIN_CHARS = 1
QUERY_MAX_CHARS = 200
LIMIT_MIN = 1
LIMIT_MAX = 10
DEFAULT_LIMIT = 5

INVALID_FDC_ID = "fdc_id must be a whole number of 1 or more."
INVALID_QUERY = f"query must be text of {QUERY_MIN_CHARS} to {QUERY_MAX_CHARS} characters after trimming."
INVALID_LIMIT = f"limit must be a whole number from {LIMIT_MIN} to {LIMIT_MAX}."
UNEXPECTED = "USDA could not be reached."


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class LruCache:
    """In-memory, per-process cache: time-to-live plus least-recently-used eviction.

    Not thread-safe on its own; ``NutritionService`` holds the lock.
    """

    def __init__(self, ttl_seconds: float, max_entries: int, clock: Callable[[], float]) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._entries: "OrderedDict[Hashable, tuple[Any, float]]" = OrderedDict()

    def get(self, key: Hashable) -> Any | None:
        item = self._entries.get(key)
        if item is None:
            return None
        value, expires_at = item
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)  # most recently used goes to the end
        return value

    def put(self, key: Hashable, value: Any) -> None:
        self._entries[key] = (value, self._clock() + self._ttl)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max:
            self._entries.popitem(last=False)  # drop the least recently used

    def drop(self, key: Hashable) -> None:
        self._entries.pop(key, None)

    def __len__(self) -> int:
        return len(self._entries)


class NutritionService:
    def __init__(
        self,
        settings: Settings,
        *,
        client: UsdaClient | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client if client is not None else UsdaClient(settings.api_key)
        self._cache = LruCache(settings.cache_ttl_seconds, settings.cache_max_entries, clock)
        self._lock = threading.Lock()

    # -- Tool 2 -------------------------------------------------------------

    def get_nutrition(self, fdc_id: Any) -> NutritionResult | ErrorResult:
        started = time.perf_counter()
        cache_hit = False
        usda_requests = 0

        if not _is_int(fdc_id) or fdc_id < 1:
            result: NutritionResult | ErrorResult = ErrorResult.for_food(
                fdc_id if _is_int(fdc_id) else None, "invalid_input", INVALID_FDC_ID
            )
        else:
            key = ("food", fdc_id)
            cached = self._cache_read(key)
            if isinstance(cached, NutritionResult) and cached.fdc_id == fdc_id:
                result, cache_hit = cached, True
            else:
                if cached is not None:
                    # Spec 11: an entry whose fdc_id differs from its key is dropped and refetched.
                    with self._lock:
                        self._cache.drop(key)
                try:
                    reply = self._client.get_food(fdc_id)
                    usda_requests = reply.requests
                    result = extract_nutrition(fdc_id, reply.body)
                    self._cache_write(key, result)
                except UsdaError as exc:
                    usda_requests = exc.requests
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except RoliNutritionError as exc:
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except Exception as exc:  # never raise to the caller
                    logger.error('{"call": "get_nutrition", "unexpected": "%s"}', type(exc).__name__)
                    result = ErrorResult.for_food(fdc_id, "usda_unavailable", UNEXPECTED)

        self._log("get_nutrition", {"fdc_id": fdc_id if _is_int(fdc_id) else None}, result, started, cache_hit, usda_requests)
        return result

    # -- Tool 1 -------------------------------------------------------------

    def search_foods(self, query: Any, limit: Any = DEFAULT_LIMIT) -> SearchResult | ErrorResult:
        started = time.perf_counter()
        cache_hit = False
        usda_requests = 0

        trimmed = query.strip() if isinstance(query, str) else None
        if trimmed is None or not (QUERY_MIN_CHARS <= len(trimmed) <= QUERY_MAX_CHARS):
            shown = trimmed[:QUERY_MAX_CHARS] if trimmed is not None else None
            result: SearchResult | ErrorResult = ErrorResult.for_search(shown, "invalid_input", INVALID_QUERY)
        elif not _is_int(limit) or not (LIMIT_MIN <= limit <= LIMIT_MAX):
            result = ErrorResult.for_search(trimmed, "invalid_input", INVALID_LIMIT)
        else:
            key = ("search", trimmed.lower(), limit)
            cached = self._cache_read(key)
            if isinstance(cached, SearchResult):
                result, cache_hit = cached, True
            else:
                try:
                    reply = self._client.search(trimmed, limit)
                    usda_requests = reply.requests
                    result = parse_search(trimmed, reply.body, limit)
                    self._cache_write(key, result)
                except UsdaError as exc:
                    usda_requests = exc.requests
                    result = ErrorResult.for_search(trimmed, exc.code, exc.message)
                except RoliNutritionError as exc:
                    result = ErrorResult.for_search(trimmed, exc.code, exc.message)
                except Exception as exc:
                    logger.error('{"call": "search_foods", "unexpected": "%s"}', type(exc).__name__)
                    result = ErrorResult.for_search(trimmed, "usda_unavailable", UNEXPECTED)

        self._log("search_foods", {"query": trimmed}, result, started, cache_hit, usda_requests)
        return result

    # -- helpers ------------------------------------------------------------

    def _cache_read(self, key: Hashable) -> Any | None:
        with self._lock:
            return self._cache.get(key)

    def _cache_write(self, key: Hashable, value: NutritionResult | SearchResult) -> None:
        # Only complete, partial and search results reach here; errors are never stored.
        with self._lock:
            self._cache.put(key, value)

    @staticmethod
    def _log(call: str, subject: dict, result: Any, started: float, cache_hit: bool, usda_requests: int) -> None:
        line = {
            "call": call,
            **subject,
            "status": result.status,
            "error_code": getattr(result, "error_code", None),
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "cache_hit": cache_hit,
            "usda_requests": usda_requests,
        }
        logger.info(json.dumps(line))


# ---------------------------------------------------------------------------
# Module-level convenience functions: one default service, built on first use.
# ---------------------------------------------------------------------------

_default_service: NutritionService | None = None
_default_lock = threading.Lock()


def default_service() -> NutritionService:
    global _default_service
    with _default_lock:
        if _default_service is None:
            _default_service = NutritionService(Settings.from_env())
        return _default_service


def get_nutrition(fdc_id: int) -> NutritionResult | ErrorResult:
    return default_service().get_nutrition(fdc_id)


def search_foods(query: str, limit: int = DEFAULT_LIMIT) -> SearchResult | ErrorResult:
    return default_service().search_foods(query, limit)
