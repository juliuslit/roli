"""USDA client: request shape (H), status mapping and retries (F), secrets (K)."""

from __future__ import annotations

import httpx
import pytest

from roli_nutrition.usda_client import UsdaClient, UsdaError

from conftest import FOOD_171999, SENTINEL_KEY, Recorder, SleepRecorder, error_response, load


def make_client(responder, sleep=None) -> tuple[UsdaClient, Recorder, SleepRecorder]:
    recorder = Recorder(responder)
    sleeper = sleep or SleepRecorder()
    return UsdaClient(SENTINEL_KEY, transport=recorder.transport, sleep=sleeper), recorder, sleeper


def ok(body) -> httpx.Response:
    return httpx.Response(200, json=body)


def expect_usda_error(fn, code: str) -> UsdaError:
    with pytest.raises(UsdaError) as info:
        fn()
    assert info.value.code == code
    assert SENTINEL_KEY not in info.value.message
    return info.value


# -- H: request shape -------------------------------------------------------------


def test_h_detail_request_shape(chinook_body):
    client, rec, _ = make_client([ok(chinook_body)])
    client.get_food(FOOD_171999)
    (request,) = rec.requests
    assert request.method == "GET"
    assert request.url.host == "api.nal.usda.gov"
    assert request.url.scheme == "https"
    assert request.url.path == f"/fdc/v1/food/{FOOD_171999}"
    assert request.url.query == b"format=full&nutrients=606,601,204"
    assert request.headers["X-Api-Key"] == SENTINEL_KEY
    assert "api_key" not in str(request.url)


def test_h_search_request_shape():
    client, rec, _ = make_client([ok(load("search_king_salmon"))])
    client.search("king salmon cooked dry heat", 10)
    (request,) = rec.requests
    assert request.method == "POST"
    assert request.url.host == "api.nal.usda.gov"
    assert request.url.path == "/fdc/v1/foods/search"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["X-Api-Key"] == SENTINEL_KEY
    assert "api_key" not in str(request.url)
    import json
    assert json.loads(request.content) == {
        "query": "king salmon cooked dry heat",
        "dataType": ["Foundation", "SR Legacy"],
        "pageSize": 10,
    }


# -- F: status mapping ----------------------------------------------------------------


def test_f_saved_404_is_not_found():
    client, rec, _ = make_client([error_response("error_404")])
    err = expect_usda_error(lambda: client.get_food(99999999), "not_found")
    assert err.requests == 1 and len(rec.requests) == 1


def test_f_saved_403_is_auth_failed():
    client, _, _ = make_client([error_response("error_403")])
    expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_auth_failed")


def test_f_saved_400_is_unavailable():
    client, rec, _ = make_client([error_response("error_400")])
    expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_unavailable")
    assert len(rec.requests) == 1  # a 400 is not retried


def test_f_429_rate_limited_after_exactly_one_request():
    body = {"error": {"code": "OVER_RATE_LIMIT", "message": "You have exceeded your rate limit."}}
    client, rec, sleeper = make_client([httpx.Response(429, json=body)])
    err = expect_usda_error(lambda: client.get_food(FOOD_171999), "rate_limited")
    assert len(rec.requests) == 1 and err.requests == 1
    assert sleeper.calls == []


def test_f_503_three_times_is_unavailable_after_three_requests():
    client, rec, sleeper = make_client([httpx.Response(503)] * 3)
    err = expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_unavailable")
    assert len(rec.requests) == 3 and err.requests == 3
    assert sleeper.calls == [0.5, 1.0]


@pytest.mark.parametrize("status", [500, 502, 504])
def test_f_other_5xx_retry_then_fail(status):
    client, rec, _ = make_client([httpx.Response(status)] * 3)
    expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_unavailable")
    assert len(rec.requests) == 3


def test_f_timeout_then_200_succeeds_after_two_requests(chinook_body):
    client, rec, sleeper = make_client([httpx.ReadTimeout("slow"), ok(chinook_body)])
    reply = client.get_food(FOOD_171999)
    assert reply.body["fdcId"] == FOOD_171999
    assert reply.requests == 2 and len(rec.requests) == 2
    assert sleeper.calls == [0.5]


def test_f_connection_error_three_times():
    client, rec, _ = make_client([httpx.ConnectError("down")] * 3)
    expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_unavailable")
    assert len(rec.requests) == 3


def test_f_non_json_body_is_malformed():
    client, _, _ = make_client([httpx.Response(200, content=b"<html>oops</html>")])
    expect_usda_error(lambda: client.get_food(FOOD_171999), "malformed_response")


@pytest.mark.parametrize("status", [201, 301, 401, 418])
def test_f_unexpected_status_is_unavailable(status):
    client, rec, _ = make_client([httpx.Response(status)])
    expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_unavailable")
    assert len(rec.requests) == 1


def test_search_404_is_unavailable_not_not_found():
    client, _, _ = make_client([httpx.Response(404, content=b"")])
    expect_usda_error(lambda: client.search("salmon", 5), "usda_unavailable")


# -- K: secrets never leak through messages ------------------------------------------


def test_k_error_messages_never_contain_usda_text_or_key():
    body = {"error": {"code": "API_KEY_INVALID", "message": f"bad key {SENTINEL_KEY} http://x"}}
    client, _, _ = make_client([httpx.Response(403, json=body)])
    err = expect_usda_error(lambda: client.get_food(FOOD_171999), "usda_auth_failed")
    assert "API_KEY_INVALID" not in err.message
    assert "http" not in err.message
