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
from .inputs import InputsError, InputsResult, extract_inputs
from .portions import PortionsResult, extract_portions
from .schemas import ErrorResult, NutritionResult, SearchResult
from .store import REFRESHABLE_TYPES, AnswerStore
from .usda_client import UsdaClient, UsdaError, ALL_SEARCH_DATA_TYPES

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


def _needs_total_fat(entry: dict[str, Any]) -> bool:
    """Spec v2.5: an answer saved before total fat was requested is asked for again only when its saturated fat is missing, the one case that reads total fat. It is the same record."""
    if (entry.get("request") or {}).get("nutrients") or not isinstance(entry.get("body"), dict):
        return False
    rows = entry["body"].get("foodNutrients") or []
    return not any(isinstance(r, dict) and (r.get("nutrient") or {}).get("id") == 1258 and r.get("amount") is not None for r in rows)


class NutritionService:
    def __init__(
        self,
        settings: Settings,
        *,
        client: UsdaClient | None = None,
        clock: Callable[[], float] = time.monotonic,
        store: AnswerStore | None = None,
    ) -> None:
        self._client = client if client is not None else UsdaClient(settings.api_key, halt_seconds=settings.halt_seconds)
        self._cache = LruCache(settings.cache_ttl_seconds, settings.cache_max_entries, clock)
        self._lock = threading.Lock()
        self._settings = settings
        # spec v2.3: saved answers on disk sit between the in-memory cache and USDA; None keeps the old in-memory-only behaviour
        self._store = store if store is not None else (AnswerStore(settings.store_dir, stale_days=settings.stale_days) if settings.store_dir else None)
        self.store_hits = 0
        self.store_misses = 0

    # -- saved answers (spec v2.3, section 18) ---------------------------------------------

    @property
    def store(self) -> AnswerStore | None:
        return self._store

    def _food_body(self, fdc_id: int) -> tuple[Any, int, str]:
        """(body, usda_requests, source) for one food: the disk store first (no request), else USDA. Raises UsdaError."""
        if self._store is not None:
            entry = self._store.get_food(fdc_id)
            if entry is not None and not _needs_total_fat(entry):
                self.store_hits += 1
                return entry["body"], 0, "store"
            self.store_misses += 1
        reply = self._client.get_food(fdc_id)
        return reply.body, reply.requests, "usda"

    def _search_body(self, query: str, limit: int, types: tuple[str, ...] | None) -> tuple[Any, int, str]:
        if self._store is not None:
            entry = self._store.get_search(query, limit, types)
            if entry is not None:
                self.store_hits += 1
                return entry["body"], 0, "store"
            self.store_misses += 1
        reply = self._client.search(query, limit, types)
        return reply.body, reply.requests, "usda"

    def _save_food(self, fdc_id: int, body: Any, source: str) -> None:
        """Only after a successful parse, and only for answers USDA itself gave in this call: a refused or malformed reply is never saved."""
        if self._store is not None and source == "usda" and isinstance(body, dict):
            try:
                self._store.put_food(fdc_id, body)
            except OSError as exc:
                logger.error('{"call": "store", "unexpected": "%s"}', type(exc).__name__)

    def _save_search(self, query: str, limit: int, types: tuple[str, ...] | None, body: Any, source: str) -> None:
        if self._store is not None and source == "usda":
            try:
                self._store.put_search(query, limit, types, body)
            except OSError as exc:
                logger.error('{"call": "store", "unexpected": "%s"}', type(exc).__name__)

    def usda_status(self) -> dict[str, Any]:
        """The key's allowance as USDA last reported it, whether the client is refusing to send after a 429, the requests this process sent,
        the disk store's inventory and the known release (spec v2.3, 18.2-18.4). Read-only; never sends a request."""
        a = self._client.allowance if hasattr(self._client, "allowance") else None
        status = {"limit": getattr(a, "limit", None), "remaining": getattr(a, "remaining", None), "observed_at": getattr(a, "observed_at", None),
                  "halted": bool(getattr(self._client, "halted", False)), "halted_until": getattr(a, "halted_until", None),
                  "requests_sent": getattr(self._client, "requests_sent", None), "reserve": self._settings.reserve_requests,
                  "store_hits": self.store_hits, "store_misses": self.store_misses, "store": None, "release": {}}
        if self._store is not None:
            status["release"] = self._store.release()
            status["store"] = {"dir": str(self._store.dir), "stale_days": self._store.stale_days}
        return status

    def allowance_ok(self, reserve: int | None = None) -> tuple[bool, str]:
        """(True, "") when USDA may still be asked: not halted, and the remaining allowance (when known) is above the reserve."""
        reserve = self._settings.reserve_requests if reserve is None else int(reserve)
        if getattr(self._client, "halted", False):
            return False, "USDA refused a request this hour; nothing more is asked until the hour has passed"
        a = getattr(self._client, "allowance", None)
        remaining = getattr(a, "remaining", None)
        if remaining is not None and remaining <= reserve:
            return False, f"USDA allowance reserve reached: {remaining} requests left this hour, reserve {reserve}"
        return True, ""

    def check_release(self, data_types: tuple[str, ...] = REFRESHABLE_TYPES) -> dict[str, Any]:
        """Spec v2.3, 18.4: one ``POST /foods/list`` per refreshable table (newest publicationDate first, one row) says whether USDA has published
        a release newer than the one the store knows. The store's live label is NOT changed here when a newer one appears: it is recorded as
        pending, and the refresh script stages the new answers for Julius to approve. Never raises; errors are reported per table."""
        out: dict[str, Any] = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "tables": {}, "requests": 0, "new_release": False}
        known = self._store.release() if self._store is not None else {}
        updated = dict(known)
        for t in data_types:
            row: dict[str, Any] = {"known": (known.get(t) or {}).get("latest_publication_date"), "latest": None, "new_release": False, "error": None}
            try:
                reply = self._client.list_foods([t], page_size=1, sort_by="publishedDate", sort_order="desc")
                out["requests"] += reply.requests
                foods = reply.body if isinstance(reply.body, list) else []
                first = foods[0] if foods and isinstance(foods[0], dict) else {}
                date = first.get("publicationDate")
                row["latest"] = date if isinstance(date, str) else None
                row["example"] = {"fdc_id": first.get("fdcId"), "description": first.get("description")} if first else None
            except UsdaError as exc:
                out["requests"] += exc.requests
                row["error"] = exc.code
            except Exception as exc:  # noqa: BLE001
                row["error"] = type(exc).__name__
            if row["latest"] is not None:
                if row["known"] is None:
                    updated[t] = {"latest_publication_date": row["latest"], "checked_at": out["checked_at"]}
                elif _date_key(row["latest"]) > _date_key(row["known"]):
                    row["new_release"] = True
                    out["new_release"] = True
                    updated[t] = {**(known.get(t) or {}), "checked_at": out["checked_at"], "pending_publication_date": row["latest"], "pending_seen_at": out["checked_at"]}
                else:
                    updated[t] = {**(known.get(t) or {}), "checked_at": out["checked_at"]}
            out["tables"][t] = row
        if self._store is not None and updated != known:
            self._store.write_release(updated)
        return out

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
                    body, usda_requests, source = self._food_body(fdc_id)
                    result = extract_nutrition(fdc_id, body)
                    self._save_food(fdc_id, body, source)
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

    def search_foods(self, query: Any, limit: Any = DEFAULT_LIMIT, data_types: Any = None) -> SearchResult | ErrorResult:
        """``data_types`` (spec v2.2, 2026-11-05): None = the default Foundation + SR Legacy search; a list such as ["Survey (FNDDS)"] searches those
        tables instead. Only the three per-100 g tables are accepted."""
        started = time.perf_counter()
        cache_hit = False
        usda_requests = 0

        trimmed = query.strip() if isinstance(query, str) else None
        types = tuple(data_types) if isinstance(data_types, (list, tuple)) and data_types else None
        if trimmed is None or not (QUERY_MIN_CHARS <= len(trimmed) <= QUERY_MAX_CHARS):
            shown = trimmed[:QUERY_MAX_CHARS] if trimmed is not None else None
            result: SearchResult | ErrorResult = ErrorResult.for_search(shown, "invalid_input", INVALID_QUERY)
        elif not _is_int(limit) or not (LIMIT_MIN <= limit <= LIMIT_MAX):
            result = ErrorResult.for_search(trimmed, "invalid_input", INVALID_LIMIT)
        elif data_types is not None and (types is None or any(t not in ALL_SEARCH_DATA_TYPES for t in types)):
            result = ErrorResult.for_search(trimmed, "invalid_input", "data_types must list one or more of Foundation, SR Legacy, Survey (FNDDS).")
        else:
            key = ("search", trimmed.lower(), limit, types)
            cached = self._cache_read(key)
            if isinstance(cached, SearchResult):
                result, cache_hit = cached, True
            else:
                try:
                    body, usda_requests, source = self._search_body(trimmed, limit, types)
                    result = parse_search(trimmed, body, limit)
                    self._save_search(trimmed, limit, types, body, source)
                    self._cache_write(key, result)
                except UsdaError as exc:
                    usda_requests = exc.requests
                    result = ErrorResult.for_search(trimmed, exc.code, exc.message)
                except RoliNutritionError as exc:
                    result = ErrorResult.for_search(trimmed, exc.code, exc.message)
                except Exception as exc:
                    logger.error('{"call": "search_foods", "unexpected": "%s"}', type(exc).__name__)
                    result = ErrorResult.for_search(trimmed, "usda_unavailable", UNEXPECTED)

        self._log("search_foods", {"query": trimmed, **({"data_types": list(types)} if types else {})}, result, started, cache_hit, usda_requests)
        return result

    # -- Portions (Phase 2B, D4): household-measure weights, read-only -----

    def get_portions(self, fdc_id: Any) -> PortionsResult | ErrorResult:
        """``foodPortions[]`` of one record as gram weights. Same request as ``get_nutrition`` (the
        detail reply carries both), separate cache key, same error shape. Never reads nutrient values."""
        started = time.perf_counter()
        cache_hit = False
        usda_requests = 0

        if not _is_int(fdc_id) or fdc_id < 1:
            result: PortionsResult | ErrorResult = ErrorResult.for_food(fdc_id if _is_int(fdc_id) else None, "invalid_input", INVALID_FDC_ID)
        else:
            key = ("portions", fdc_id)
            cached = self._cache_read(key)
            if isinstance(cached, PortionsResult) and cached.fdc_id == fdc_id:
                result, cache_hit = cached, True
            else:
                if cached is not None:
                    with self._lock:
                        self._cache.drop(key)
                try:
                    body, usda_requests, source = self._food_body(fdc_id)
                    result = extract_portions(fdc_id, body)
                    self._save_food(fdc_id, body, source)
                    with self._lock:
                        self._cache.put(key, result)
                except UsdaError as exc:
                    usda_requests = exc.requests
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except RoliNutritionError as exc:
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except Exception as exc:  # never raise to the caller
                    logger.error('{"call": "get_portions", "unexpected": "%s"}', type(exc).__name__)
                    result = ErrorResult.for_food(fdc_id, "usda_unavailable", UNEXPECTED)

        self._log("get_portions", {"fdc_id": fdc_id if _is_int(fdc_id) else None}, result, started, cache_hit, usda_requests)
        return result

    # -- helpers ------------------------------------------------------------

    def get_inputs(self, fdc_id: Any) -> InputsResult | ErrorResult:
        """``foodPortions[]`` of one record as gram weights. Same request as ``get_nutrition`` (the
        detail reply carries both), separate cache key, same error shape. Never reads nutrient values."""
        started = time.perf_counter()
        cache_hit = False
        usda_requests = 0

        if not _is_int(fdc_id) or fdc_id < 1:
            result: InputsResult | ErrorResult = ErrorResult.for_food(fdc_id if _is_int(fdc_id) else None, "invalid_input", INVALID_FDC_ID)
        else:
            key = ("inputs", fdc_id)
            cached = self._cache_read(key)
            if isinstance(cached, InputsResult) and cached.fdc_id == fdc_id:
                result, cache_hit = cached, True
            else:
                if cached is not None:
                    with self._lock:
                        self._cache.drop(key)
                try:
                    body, usda_requests, source = self._food_body(fdc_id)
                    result = extract_inputs(fdc_id, body)
                    self._save_food(fdc_id, body, source)
                    with self._lock:
                        self._cache.put(key, result)
                except UsdaError as exc:
                    usda_requests = exc.requests
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except RoliNutritionError as exc:
                    result = ErrorResult.for_food(fdc_id, exc.code, exc.message)
                except Exception as exc:  # never raise to the caller
                    logger.error('{"call": "get_inputs", "unexpected": "%s"}', type(exc).__name__)
                    result = ErrorResult.for_food(fdc_id, "usda_unavailable", UNEXPECTED)

        self._log("get_inputs", {"fdc_id": fdc_id if _is_int(fdc_id) else None}, result, started, cache_hit, usda_requests)
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


def _date_key(text: str) -> tuple[int, int, int]:
    """USDA writes publication dates as '2026-10-29' in list replies and '4/1/2019' in food replies; both order correctly as (y, m, d)."""
    t = text.strip()
    try:
        if "-" in t:
            y, m, d = t.split("-")[:3]
        else:
            m, d, y = t.split("/")[:3]
        return int(y), int(m), int(d)
    except ValueError:
        return (0, 0, 0)


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
