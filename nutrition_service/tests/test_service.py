"""NutritionService end to end against the mock transport: A, B, C, F, G, J, K, P."""

from __future__ import annotations

import json
import threading

import httpx
import pytest

from roli_nutrition import ErrorResult, NutritionResult, SearchResult
from roli_nutrition.nutrients import extract_nutrition

from conftest import (
    FOOD_171999,
    FOOD_172001,
    SENTINEL_KEY,
    FakeClock,
    error_response,
    food_router,
    load,
    make_service,
    mutate,
)

NUTRITION_KEYS = {
    "status", "fdc_id", "description", "data_type", "basis", "saturated_fat_g",
    "cholesterol_mg", "missing_nutrients", "nutrient_ids", "source", "total_fat_g", "food_category"}
SEARCH_KEYS = {"status", "query", "candidates", "source"}
ERROR_KEYS_FOOD = {"status", "fdc_id", "error_code", "message"}
ERROR_KEYS_SEARCH = {"status", "query", "error_code", "message"}


def assert_clean(result) -> dict:
    """Result has no trace of the key; returns its dict form."""
    data = result.model_dump()
    assert SENTINEL_KEY not in json.dumps(data)
    return data


# -- A and B ------------------------------------------------------------------


def test_a_chinook_through_service():
    service, rec = make_service(food_router())
    result = service.get_nutrition(FOOD_171999)
    assert isinstance(result, NutritionResult)
    assert result.model_dump() == {
        "status": "complete",
        "fdc_id": 171999,
        "description": "Fish, salmon, chinook, cooked, dry heat",
        "data_type": "SR Legacy",
        "basis": "per_100g",
        "saturated_fat_g": 3.214,
        "cholesterol_mg": 85.0,
        "missing_nutrients": [],
        "total_fat_g": None,
        "food_category": "Finfish and Shellfish Products",
        "nutrient_ids": {"saturated_fat_g": 1258, "cholesterol_mg": 1253},
        "source": "USDA FoodData Central",
    }
    assert len(rec.requests) == 1


def test_b_pink_through_service():
    service, _ = make_service(food_router())
    result = service.get_nutrition(FOOD_172001)
    assert (result.saturated_fat_g, result.cholesterol_mg) == (0.971, 55.0)
    assert result.description == "Fish, salmon, pink, cooked, dry heat"


@pytest.mark.parametrize("order", [(FOOD_172001, FOOD_171999), (FOOD_171999, FOOD_172001)])
def test_b_isolation_with_cache(order):
    service, _ = make_service(food_router())
    results = {fid: service.get_nutrition(fid) for fid in order}
    assert results[FOOD_171999].saturated_fat_g == 3.214 and results[FOOD_171999].cholesterol_mg == 85.0
    assert results[FOOD_172001].saturated_fat_g == 0.971 and results[FOOD_172001].cholesterol_mg == 55.0
    # Second pass from the cache gives identical objects.
    for fid in order:
        assert service.get_nutrition(fid) == results[fid]


@pytest.mark.parametrize("order", [(FOOD_172001, FOOD_171999), (FOOD_171999, FOOD_172001)])
def test_b_isolation_without_cache(order):
    results = {}
    for fid in order:
        service, _ = make_service(food_router())  # fresh service: nothing cached
        results[fid] = service.get_nutrition(fid)
    assert results[FOOD_171999].cholesterol_mg == 85.0 and results[FOOD_171999].saturated_fat_g == 3.214
    assert results[FOOD_172001].cholesterol_mg == 55.0 and results[FOOD_172001].saturated_fat_g == 0.971


# -- C: search --------------------------------------------------------------------


def test_c_search_through_service():
    service, rec = make_service(food_router("search_king_salmon"))
    result = service.search_foods("  king salmon cooked dry heat ", 10)
    assert isinstance(result, SearchResult)
    assert result.query == "king salmon cooked dry heat"
    body = load("search_king_salmon")
    expected = [(f["fdcId"], f["description"], f["dataType"]) for f in body["foods"]]
    assert [(c.fdc_id, c.description, c.data_type) for c in result.candidates] == expected
    (request,) = rec.requests
    assert json.loads(request.content) == {
        "query": "king salmon cooked dry heat",
        "dataType": ["Foundation", "SR Legacy"],
        "pageSize": 10,
    }


def test_c_search_default_limit_is_five():
    service, rec = make_service(food_router())
    service.search_foods("salmon")
    assert json.loads(rec.requests[0].content)["pageSize"] == 5


def test_c_chinook_search_fixture_parses():
    service, _ = make_service(food_router("search_salmon_chinook"))
    result = service.search_foods("salmon chinook cooked dry heat", 10)
    assert isinstance(result, SearchResult)


# -- F: invalid input and USDA failures ----------------------------------------------


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "171999", None])
def test_f_invalid_fdc_id(bad):
    service, rec = make_service(food_router())
    result = service.get_nutrition(bad)
    assert isinstance(result, ErrorResult)
    data = assert_clean(result)
    assert data["error_code"] == "invalid_input"
    assert set(data) == ERROR_KEYS_FOOD
    assert rec.requests == []  # rejected before any USDA call


@pytest.mark.parametrize("query, limit", [
    ("", 5), ("   ", 5), ("x" * 201, 5), (None, 5), (5, 5),
    ("salmon", 0), ("salmon", 11), ("salmon", True), ("salmon", 2.0), ("salmon", "5"),
])
def test_f_invalid_search_input(query, limit):
    service, rec = make_service(food_router())
    result = service.search_foods(query, limit)
    assert isinstance(result, ErrorResult)
    data = assert_clean(result)
    assert data["error_code"] == "invalid_input"
    assert set(data) == ERROR_KEYS_SEARCH
    assert rec.requests == []


def test_f_limit_is_rejected_not_capped():
    service, rec = make_service(food_router())
    assert service.search_foods("salmon", 11).error_code == "invalid_input"
    assert rec.requests == []


def test_f_saved_404_not_found():
    service, _ = make_service([error_response("error_404")])
    result = service.get_nutrition(99999999)
    data = assert_clean(result)
    assert data == {
        "status": "error", "fdc_id": 99999999, "error_code": "not_found",
        "message": "USDA has no food with this FDC ID.",
    }


def test_f_saved_403_auth_failed():
    service, _ = make_service([error_response("error_403")])
    assert assert_clean(service.get_nutrition(FOOD_171999))["error_code"] == "usda_auth_failed"


def test_f_429_rate_limited_one_request():
    service, rec = make_service([httpx.Response(429, json={"error": {"code": "OVER_RATE_LIMIT"}})])
    assert assert_clean(service.get_nutrition(FOOD_171999))["error_code"] == "rate_limited"
    assert len(rec.requests) == 1


def test_f_503_three_times_unavailable():
    service, rec = make_service([httpx.Response(503)] * 3)
    assert assert_clean(service.get_nutrition(FOOD_171999))["error_code"] == "usda_unavailable"
    assert len(rec.requests) == 3


def test_f_timeout_then_200(chinook_body):
    service, rec = make_service([httpx.ReadTimeout("slow"), httpx.Response(200, json=chinook_body)])
    result = service.get_nutrition(FOOD_171999)
    assert result.status == "complete" and result.saturated_fat_g == 3.214
    assert len(rec.requests) == 2


def test_f_non_json_body_malformed():
    service, _ = make_service([httpx.Response(200, content=b"not json")])
    assert assert_clean(service.get_nutrition(FOOD_171999))["error_code"] == "malformed_response"


def test_f_id_mismatch_returns_no_values(chinook_body):
    body = mutate(chinook_body, lambda b: b.update(fdcId=FOOD_172001))
    service, _ = make_service([httpx.Response(200, json=body)])
    result = service.get_nutrition(FOOD_171999)
    data = assert_clean(result)
    assert data["error_code"] == "id_mismatch"
    assert set(data) == ERROR_KEYS_FOOD  # no saturated_fat_g or cholesterol_mg keys at all
    assert data["fdc_id"] == FOOD_171999


def test_f_validation_failed_names_rule(chinook_body):
    body = mutate(chinook_body, lambda b: b["foodNutrients"].append(dict(b["foodNutrients"][0])))
    service, _ = make_service([httpx.Response(200, json=body)])
    result = service.get_nutrition(FOOD_171999)
    assert result.error_code == "validation_failed"
    assert "duplicate_nutrient" in result.message


def test_search_usda_failure_carries_query():
    service, _ = make_service([httpx.Response(429, json={})])
    data = assert_clean(service.search_foods("salmon", 5))
    assert set(data) == ERROR_KEYS_SEARCH and data["query"] == "salmon"


# -- G: shape and size -----------------------------------------------------------------


def test_g_nutrition_shape_and_size():
    service, _ = make_service(food_router())
    for fid in (FOOD_171999, FOOD_172001):
        result = service.get_nutrition(fid)
        assert set(result.model_dump()) == NUTRITION_KEYS
        assert len(result.model_dump_json().encode()) <= 2048


def test_g_partial_shape(chinook_body):
    body = mutate(chinook_body, lambda b: b.update(foodNutrients=[]))
    service, _ = make_service([httpx.Response(200, json=body)])
    data = service.get_nutrition(FOOD_171999).model_dump()
    assert set(data) == NUTRITION_KEYS and data["status"] == "partial"


def test_g_search_shape_and_size():
    service, _ = make_service(food_router("search_king_salmon"))
    result = service.search_foods("king salmon cooked dry heat", 10)
    data = result.model_dump()
    assert set(data) == SEARCH_KEYS
    for candidate in data["candidates"]:
        assert set(candidate) == {"fdc_id", "description", "data_type"}
    assert len(result.model_dump_json().encode()) <= 3072


def test_g_error_shape():
    service, _ = make_service([error_response("error_404")])
    assert set(service.get_nutrition(5).model_dump()) == ERROR_KEYS_FOOD
    service, _ = make_service([httpx.Response(503)] * 3)
    assert set(service.search_foods("salmon").model_dump()) == ERROR_KEYS_SEARCH


# -- J: cache ----------------------------------------------------------------------


def test_j_second_call_makes_no_request():
    service, rec = make_service(food_router())
    first = service.get_nutrition(FOOD_171999)
    second = service.get_nutrition(FOOD_171999)
    assert first == second
    assert len(rec.requests) == 1


def test_j_search_is_cached_case_insensitively():
    service, rec = make_service(food_router())
    service.search_foods("King Salmon cooked dry heat", 10)
    service.search_foods("king salmon COOKED dry heat ", 10)
    assert len(rec.requests) == 1
    service.search_foods("king salmon cooked dry heat", 5)  # different limit: different key
    assert len(rec.requests) == 2


def test_j_errors_are_not_cached(chinook_body):
    service, rec = make_service([error_response("error_404"), httpx.Response(200, json=chinook_body)])
    assert service.get_nutrition(FOOD_171999).status == "error"
    assert service.get_nutrition(FOOD_171999).status == "complete"
    assert len(rec.requests) == 2


def test_j_ttl_expiry_refetches():
    clock = FakeClock()
    service, rec = make_service(food_router(), clock=clock, cache_ttl_seconds=100)
    service.get_nutrition(FOOD_171999)
    clock.advance(99)
    service.get_nutrition(FOOD_171999)
    assert len(rec.requests) == 1
    clock.advance(1)
    service.get_nutrition(FOOD_171999)
    assert len(rec.requests) == 2


def test_j_lru_eviction():
    service, rec = make_service(food_router(), cache_max_entries=1)
    service.get_nutrition(FOOD_171999)
    service.get_nutrition(FOOD_172001)  # evicts 171999
    service.get_nutrition(FOOD_171999)
    assert len(rec.requests) == 3


def test_j_entry_with_wrong_fdc_id_is_dropped(pink_body):
    service, rec = make_service(food_router())
    wrong = extract_nutrition(FOOD_172001, pink_body)
    service._cache.put(("food", FOOD_171999), wrong)  # plant a poisoned entry
    result = service.get_nutrition(FOOD_171999)
    assert result.fdc_id == FOOD_171999 and result.cholesterol_mg == 85.0
    assert len(rec.requests) == 1
    assert service._cache.get(("food", FOOD_171999)).fdc_id == FOOD_171999


# -- K: secrets in logs and results -----------------------------------------------------


def test_k_log_lines_are_json_with_documented_fields(caplog):
    service, _ = make_service(food_router())
    service.get_nutrition(FOOD_171999)
    service.get_nutrition(FOOD_171999)
    service.search_foods("salmon", 3)
    lines = [json.loads(r.message) for r in caplog.records if r.name == "roli_nutrition"]
    assert len(lines) == 3
    assert set(lines[0]) == {"call", "fdc_id", "status", "error_code", "duration_ms", "cache_hit", "usda_requests"}
    assert lines[0]["cache_hit"] is False and lines[0]["usda_requests"] == 1
    assert lines[1]["cache_hit"] is True and lines[1]["usda_requests"] == 0
    assert set(lines[2]) == {"call", "query", "status", "error_code", "duration_ms", "cache_hit", "usda_requests"}
    assert SENTINEL_KEY not in caplog.text


def test_k_failures_never_leak_key(caplog):
    cases = [
        [error_response("error_403")],
        [httpx.Response(429, json={"error": {"message": SENTINEL_KEY}})],
        [httpx.Response(503)] * 3,
        [httpx.ReadTimeout(SENTINEL_KEY)] * 3,
        [httpx.Response(200, content=SENTINEL_KEY.encode())],
    ]
    for responder in cases:
        service, _ = make_service(responder)
        result = service.get_nutrition(FOOD_171999)
        assert result.status == "error"
        assert_clean(result)
    assert SENTINEL_KEY not in caplog.text


# -- P: threads --------------------------------------------------------------------------


def test_p_twenty_threads_get_their_own_food():
    service, _ = make_service(food_router())
    expected = {FOOD_171999: (3.214, 85.0), FOOD_172001: (0.971, 55.0)}
    results: dict[int, list] = {FOOD_171999: [], FOOD_172001: []}
    lock = threading.Lock()
    barrier = threading.Barrier(20)

    def worker(fid: int) -> None:
        barrier.wait()
        r = service.get_nutrition(fid)
        with lock:
            results[fid].append(r)

    threads = [threading.Thread(target=worker, args=(FOOD_171999 if i % 2 else FOOD_172001,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for fid, items in results.items():
        assert len(items) == 10
        for r in items:
            assert r.status == "complete"
            assert r.fdc_id == fid
            assert (r.saturated_fat_g, r.cholesterol_mg) == expected[fid]


# -- limit enforcement (added after Checkpoint 1A, Julius 2026-11-01) --------------------------


def test_limit_caps_candidates_even_if_usda_returns_more():
    # The king salmon fixture holds 10 foods; ask for 3 and USDA's first three must come back, in order.
    service, rec = make_service(food_router("search_king_salmon"))
    result = service.search_foods("king salmon cooked dry heat", 3)
    body = load("search_king_salmon")
    assert len(body["foods"]) == 10
    assert [c.fdc_id for c in result.candidates] == [f["fdcId"] for f in body["foods"][:3]]
    assert json.loads(rec.requests[0].content)["pageSize"] == 3
