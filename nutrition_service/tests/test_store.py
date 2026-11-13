"""Spec v2.3 (Julius, 2026-11-05): saved answers on disk survive a restart, a refusal halts the client, the allowance headers are read,
a new release is detected from ``POST /foods/list`` and staged answers go live only when promoted."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from roli_nutrition import AnswerStore, ErrorResult, NutritionResult, NutritionService, Settings
from roli_nutrition.store import search_key
from roli_nutrition.usda_client import UsdaClient, UsdaError

from pathlib import Path

from conftest import FOOD_171999, FOOD_172001, SENTINEL_KEY, FakeClock, Recorder, food_router, load, make_settings

SERVICE_DIR = Path(__file__).resolve().parents[1]

LIST_FOUNDATION = "list_foundation_newest"


def headers(remaining: int, limit: int = 3600) -> dict[str, str]:
    return {"x-ratelimit-limit": str(limit), "x-ratelimit-remaining": str(remaining)}


def router_with_headers(remaining: list[int]):
    """Serve the saved replies and count the allowance down one per request, like api.data.gov does."""
    inner = food_router()

    def respond(request: httpx.Request) -> httpx.Response:
        r = inner(request)
        remaining[0] -= 1
        return httpx.Response(r.status_code, content=r.content, headers=headers(remaining[0]))
    return respond


def service_on(tmp_path, responder, *, clock=None, store_clock=None, **settings):
    rec = Recorder(responder)
    client = UsdaClient(SENTINEL_KEY, transport=rec.transport, sleep=lambda s: None, clock=clock or FakeClock())
    store = AnswerStore(tmp_path / "store", stale_days=213, clock=store_clock or (lambda: datetime(2026, 11, 5, tzinfo=timezone.utc)))
    return NutritionService(make_settings(**settings), client=client, store=store), rec, store


# -- saved answers --------------------------------------------------------------------------------------------------------


def test_a_saved_answer_survives_a_restart_and_the_second_process_sends_no_request(tmp_path):
    svc, rec, store = service_on(tmp_path, food_router())
    first = svc.get_nutrition(FOOD_171999)
    assert isinstance(first, NutritionResult) and len(rec.requests) == 1
    entry = store.get_food(FOOD_171999)
    assert entry["body"]["fdcId"] == FOOD_171999 and entry["data_type"] == "SR Legacy" and entry["publication_date"] == "4/1/2019" and entry["saved_at"].startswith("2026-11-05")
    # the portions of the same food come from the saved body: no second request (before v2.3 each call kind fetched the record again)
    assert svc.get_portions(FOOD_171999).fdc_id == FOOD_171999 and len(rec.requests) == 1
    # a new process: empty memory, same disk
    svc2, rec2, _ = service_on(tmp_path, food_router())
    again = svc2.get_nutrition(FOOD_171999)
    assert again.model_dump() == first.model_dump() and rec2.requests == [] and svc2.store_hits == 1 and svc2.store_misses == 0


def test_a_saved_search_is_keyed_by_query_limit_and_tables(tmp_path):
    svc, rec, store = service_on(tmp_path, food_router())
    r1 = svc.search_foods("King Salmon cooked dry heat", 5)
    assert r1.status == "complete" and len(rec.requests) == 1
    assert store.get_search("king salmon cooked dry heat", 5, None) is not None
    assert store.get_search("king salmon cooked dry heat", 10, None) is None                     # another limit is another request
    assert search_key("A", 5, None) != search_key("A", 5, ("Survey (FNDDS)",))
    svc2, rec2, _ = service_on(tmp_path, food_router())
    assert svc2.search_foods("  king salmon cooked dry heat ", 5).candidates == r1.candidates and rec2.requests == []


def test_refused_and_failed_answers_are_never_saved(tmp_path):
    bad = Recorder([httpx.Response(429, content=b""), httpx.Response(404, content=b""), httpx.Response(200, content=b"not json")])
    client = UsdaClient(SENTINEL_KEY, transport=bad.transport, sleep=lambda s: None, halt_seconds=0)
    store = AnswerStore(tmp_path / "store")
    svc = NutritionService(make_settings(), client=client, store=store)
    for fid in (FOOD_171999, FOOD_172001, 1):
        assert isinstance(svc.get_nutrition(fid), ErrorResult)
    assert list(store.entries()) == [] and not (tmp_path / "store" / "food").exists()


def test_a_corrupt_saved_file_is_treated_as_absent(tmp_path):
    svc, rec, store = service_on(tmp_path, food_router())
    svc.get_nutrition(FOOD_171999)
    path = store._food_path(FOOD_171999)
    path.write_text("{broken", encoding="utf-8")
    svc2, rec2, _ = service_on(tmp_path, food_router())
    assert isinstance(svc2.get_nutrition(FOOD_171999), NutritionResult) and len(rec2.requests) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["body"]["fdcId"] == FOOD_171999          # rewritten from the fresh reply


# -- refusal and allowance -------------------------------------------------------------------------------------------------


def test_after_the_first_429_nothing_more_is_sent_until_the_hour_passes(tmp_path):
    clock = FakeClock(1000.0)
    rec = Recorder([httpx.Response(429, content=b"", headers=headers(0))] + [httpx.Response(200, json=load("food_171999"))] * 3)
    client = UsdaClient(SENTINEL_KEY, transport=rec.transport, sleep=lambda s: None, halt_seconds=3600, clock=clock)
    svc = NutritionService(make_settings(), client=client)
    assert svc.get_nutrition(FOOD_171999).error_code == "rate_limited" and len(rec.requests) == 1
    assert svc.get_nutrition(FOOD_171999).error_code == "rate_limited" and len(rec.requests) == 1       # refused without a request
    assert svc.search_foods("salmon", 5).error_code == "rate_limited" and len(rec.requests) == 1
    assert svc.allowance_ok() == (False, "USDA refused a request this hour; nothing more is asked until the hour has passed")
    status = svc.usda_status()
    assert status["halted"] is True and status["remaining"] == 0 and status["limit"] == 3600 and status["requests_sent"] == 1
    clock.advance(3601)
    assert isinstance(svc.get_nutrition(FOOD_171999), NutritionResult) and len(rec.requests) == 2 and svc.usda_status()["halted"] is False


def test_the_remaining_count_comes_from_the_headers_and_the_reserve_pauses_callers(tmp_path):
    remaining = [3600]
    svc, rec, _ = service_on(tmp_path, router_with_headers(remaining), reserve_requests=200)
    assert svc.usda_status()["remaining"] is None and svc.allowance_ok() == (True, "")                 # nothing known yet: USDA may be asked
    svc.get_nutrition(FOOD_171999)
    assert svc.usda_status()["remaining"] == 3599 and svc.usda_status()["limit"] == 3600
    remaining[0] = 201
    svc.get_nutrition(FOOD_172001)
    ok, why = svc.allowance_ok()
    assert not ok and why == "USDA allowance reserve reached: 200 requests left this hour, reserve 200"
    assert svc.allowance_ok(reserve=100) == (True, "")


# -- release detection and staging ----------------------------------------------------------------------------------------------


def list_router(foundation_date: str = "2026-10-29", survey_date: str = "2024-10-31"):
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/foods/list"):
            body = json.loads(request.content)
            assert body["sortBy"] == "publishedDate" and body["sortOrder"] == "desc" and body["pageSize"] == 1
            t = body["dataType"][0]
            date = foundation_date if t == "Foundation" else survey_date
            row = {"fdcId": 1, "description": f"newest {t}", "dataType": t, "publicationDate": date}
            return httpx.Response(200, json=[row], headers=headers(3000))
        return food_router()(request)
    return respond


def test_release_detection_records_the_newest_date_and_flags_a_newer_one_as_pending(tmp_path):
    svc, rec, store = service_on(tmp_path, list_router())
    first = svc.check_release()
    assert first["requests"] == 2 and first["new_release"] is False
    assert first["tables"]["Foundation"] == {"known": None, "latest": "2026-10-29", "new_release": False, "error": None, "example": {"fdc_id": 1, "description": "newest Foundation"}}
    assert store.release()["Foundation"]["latest_publication_date"] == "2026-10-29" and store.release()["Survey (FNDDS)"]["latest_publication_date"] == "2024-10-31"
    # an answer saved now carries the release it was fetched under
    svc.get_nutrition(FOOD_171999)
    assert store.get_food(FOOD_171999)["release"] == {"Foundation": "2026-10-29", "Survey (FNDDS)": "2024-10-31"}
    # USDA publishes a new Foundation release: detected, recorded as pending, the live label untouched
    svc2, _, store2 = service_on(tmp_path, list_router(foundation_date="2027-04-15"))
    second = svc2.check_release()
    assert second["new_release"] is True and second["tables"]["Foundation"]["new_release"] is True and second["tables"]["Survey (FNDDS)"]["new_release"] is False
    rel = store2.release()["Foundation"]
    assert rel["latest_publication_date"] == "2026-10-29" and rel["pending_publication_date"] == "2027-04-15"


def test_release_detection_survives_a_refusal_and_reports_the_error(tmp_path):
    rec = Recorder([httpx.Response(429, content=b"")])
    client = UsdaClient(SENTINEL_KEY, transport=rec.transport, sleep=lambda s: None, halt_seconds=3600)
    svc = NutritionService(make_settings(), client=client, store=AnswerStore(tmp_path / "s"))
    out = svc.check_release()
    assert out["tables"]["Foundation"]["error"] == "rate_limited" and out["tables"]["Survey (FNDDS)"]["error"] == "rate_limited" and out["requests"] == 1


def test_the_saved_list_replies_parse_as_release_dates():
    """The real replies of 2026-11-05: the descending sort names the newest publication date of each table, the ascending one an older date."""
    newest = load(LIST_FOUNDATION)
    oldest = load("list_foundation_oldest")
    assert newest[0]["dataType"] == "Foundation" and newest[0]["publicationDate"] >= oldest[0]["publicationDate"]
    assert load("list_survey_newest")[0]["publicationDate"] == "2024-10-31" and load("list_sr_legacy_newest")[0]["publicationDate"] == "2019-04-01"


def test_stale_entries_and_staging_promote_only_on_command(tmp_path):
    now = [datetime(2026, 11, 5, tzinfo=timezone.utc)]
    svc, rec, store = service_on(tmp_path, food_router(), store_clock=lambda: now[0])
    svc.get_nutrition(FOOD_171999)                                                                     # SR Legacy: never stale
    store.put_food(FOOD_172001, dict(load("food_172001"), dataType="Foundation"))                     # pretend a Foundation answer
    assert store.stale_entries() == []
    now[0] += timedelta(days=214)
    stale = store.stale_entries()
    assert [e["request"]["fdc_id"] for _, e in stale] == [FOOD_172001]
    # a refresh stages the new answer; live is unchanged until promoted
    store.put_food(FOOD_172001, load("food_172001"), area="staging")
    assert store.staged_count() == 1 and store.get_food(FOOD_172001)["body"]["dataType"] == "Foundation"
    out = store.promote_staging(snapshot_label="before-test")
    assert out["promoted"] == 1 and store.staged_count() == 0 and store.get_food(FOOD_172001)["body"]["dataType"] == "SR Legacy"
    snap = tmp_path / "store" / "snapshots" / "before-test" / "food" / f"{FOOD_172001}.json"
    assert json.loads(snap.read_text(encoding="utf-8"))["body"]["dataType"] == "Foundation"            # the old answer is kept
    stats = store.stats()
    assert stats["foods"] == 2 and stats["snapshots"] == ["before-test"] and stats["stale"] == 0


def test_settings_read_the_new_variables_and_keep_the_old_defaults():
    s = Settings.from_env({"USDA_FDC_API_KEY": "k"})
    assert (s.store_dir, s.stale_months, s.stale_days, s.reserve_requests, s.halt_seconds) == (None, 7, 213, 200, 3600.0)
    s = Settings.from_env({"USDA_FDC_API_KEY": "k", "ROLI_USDA_STORE_DIR": "/tmp/x", "ROLI_USDA_STALE_MONTHS": "3", "ROLI_USDA_RESERVE_REQUESTS": "0", "ROLI_USDA_HALT_SECONDS": "0"})
    assert (s.store_dir, s.stale_months, s.reserve_requests, s.halt_seconds) == ("/tmp/x", 3, 0, 0.0)
    with pytest.raises(Exception):
        Settings.from_env({"USDA_FDC_API_KEY": "k", "ROLI_USDA_RESERVE_REQUESTS": "-1"})


def test_list_foods_request_shape_and_sort_guard():
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json=[])
    client = UsdaClient(SENTINEL_KEY, transport=httpx.MockTransport(respond), sleep=lambda s: None)
    client.list_foods(["Survey (FNDDS)"])
    assert seen == [("POST", "/fdc/v1/foods/list", {"dataType": ["Survey (FNDDS)"], "pageSize": 1, "pageNumber": 1, "sortBy": "publishedDate", "sortOrder": "desc"})]
    with pytest.raises(ValueError):
        client.list_foods(["Foundation"], sort_by="colour")


def test_staging_script_refetches_refreshable_answers_and_stops_at_the_reserve(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("refresh_usda", SERVICE_DIR / "scripts" / "refresh_usda.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    remaining = [205]
    svc, rec, store = service_on(tmp_path, router_with_headers(remaining), reserve_requests=200)
    svc.get_nutrition(FOOD_171999)                                                                     # SR Legacy: not refreshable
    store.put_food(FOOD_172001, dict(load("food_172001"), dataType="Foundation"))
    store.put_food(FOOD_171999 + 1000, dict(load("food_171999"), dataType="Survey (FNDDS)", fdcId=FOOD_171999 + 1000))
    svc.search_foods("king salmon cooked dry heat", 5)
    out = mod.stage(svc, store, svc._client, stale_only=False, reserve=200, limit=None)
    # 3 refreshable entries (Foundation food, Survey food, the search); the Survey id is unknown to the router (404) so it fails; the allowance
    # falls to 200 after the 4th request of the process and staging stops before anything else is asked
    assert out["candidates"] == 3 and out["failed"] >= 1 and out["staged_total"] >= 1 and remaining[0] >= 200
    assert (tmp_path / "store" / "staging" / "release.json").exists()
    assert store.get_food(FOOD_172001)["body"]["dataType"] == "Foundation"                             # live untouched until --promote --yes


def test_v25_an_old_answer_is_asked_again_only_when_its_saturated_fat_is_missing():
    from roli_nutrition.service import _needs_total_fat
    with_sat = {"foodNutrients": [{"nutrient": {"id": 1258}, "amount": 1.0}]}
    without = {"foodNutrients": [{"nutrient": {"id": 1253}, "amount": 0.0}]}
    assert not _needs_total_fat({"request": {"call": "food"}, "body": with_sat})
    assert _needs_total_fat({"request": {"call": "food"}, "body": without})
    assert not _needs_total_fat({"request": {"call": "food", "nutrients": "606,601,204"}, "body": without})

