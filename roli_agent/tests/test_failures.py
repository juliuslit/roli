"""The Phase 1D lesson, enforced: when USDA cannot give a verified value, Roli says so and gives none.

Every test here asserts three things: the reply contains no nutrition number, the reply
does not attribute any figure to USDA, and no source other than the nutrition service was
consulted (the scripted LLM was called at most twice, for interpretation and selection).
"""

from __future__ import annotations

import httpx
import pytest

from conftest import (
    CHINOOK,
    PINK,
    assert_no_nutrition_numbers,
    interpret_reply,
    load,
    make_graph,
    mutate,
    run,
    select_reply,
    usda_router,
)

INTERP = interpret_reply("cooked Chinook salmon", "salmon chinook cooked dry heat")
UNAVAILABLE = "Verified nutrition information for cooked Chinook salmon is unavailable"


def sequence(*responses):
    """A USDA that answers the search normally, then the lookup with the given sequence."""
    search = load("search_salmon_chinook")
    items = iter(responses)

    def respond(request):
        if request.url.path.endswith("/foods/search"):
            return httpx.Response(200, json=search)
        item = next(items)
        if isinstance(item, Exception):
            raise item
        return item
    return respond


def check_no_values(state, *allowed_ids):
    assert state["numbers_allowed"] is not True
    assert state["nutrition"] is None
    assert_no_nutrition_numbers(state["response"], *allowed_ids)
    assert "Roli does not estimate them from other sources" in state["response"]


# -- USDA failures after a good search -------------------------------------------


def test_timeout_three_times_is_unavailable():
    graph, llm, rec = make_graph([INTERP, select_reply(CHINOOK)], sequence(*[httpx.ReadTimeout("slow")] * 3))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "usda_unavailable"
    assert state["response"].startswith(UNAVAILABLE)
    assert "could not be reached" in state["response"]
    check_no_values(state)
    assert len(rec.requests) == 4 and len(llm.prompts) == 2   # 1 search + 3 attempts; no extra LLM turn


def test_rate_limited_no_retry_no_values():
    body = {"error": {"code": "OVER_RATE_LIMIT"}}
    graph, _, rec = make_graph([INTERP, select_reply(CHINOOK)], sequence(httpx.Response(429, json=body)))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "rate_limited"
    assert "hourly request limit" in state["response"]
    check_no_values(state)
    assert len(rec.requests) == 2


def test_record_not_found():
    graph, _, _ = make_graph([INTERP, select_reply(CHINOOK)], sequence(httpx.Response(404, content=b"")))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "not_found"
    check_no_values(state)


def test_mismatched_id_values_are_discarded(chinook_body):
    """USDA answers the 171999 request with a body labelled 172001: nothing from it may be shown."""
    wrong = mutate(chinook_body, lambda b: b.update(fdcId=PINK))
    graph, _, _ = make_graph([INTERP, select_reply(CHINOOK)], sequence(httpx.Response(200, json=wrong)))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "id_mismatch"
    assert "different record than the one requested" in state["response"]
    check_no_values(state)
    assert "3.214" not in state["response"] and "85" not in state["response"].replace("171999", "")


def test_validation_failure_discards_values(chinook_body):
    import copy
    dup = mutate(chinook_body, lambda b: b["foodNutrients"].append(copy.deepcopy(b["foodNutrients"][0])))
    graph, _, _ = make_graph([INTERP, select_reply(CHINOOK)], sequence(httpx.Response(200, json=dup)))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "validation_failed"
    check_no_values(state)


def test_malformed_usda_reply():
    graph, _, _ = make_graph([INTERP, select_reply(CHINOOK)], sequence(httpx.Response(200, content=b"<html>")))
    state = run(graph, "cooked chinook salmon")
    assert state["nutrition_error"]["error_code"] == "malformed_response"
    check_no_values(state)


# -- USDA completely unavailable: the search itself fails ---------------------------


@pytest.mark.parametrize("failure", [
    [httpx.Response(503)] * 3,
    [httpx.ConnectError("down")] * 3,
    [httpx.Response(429, json={"error": {"code": "OVER_RATE_LIMIT"}})],
    [httpx.Response(403, json={"error": {"code": "API_KEY_INVALID"}})],
])
def test_search_failure_means_no_values_and_no_selection_attempt(failure):
    graph, llm, rec = make_graph([INTERP, select_reply(CHINOOK)], list(failure))
    state = run(graph, "cooked chinook salmon")
    assert state["search_error"] is not None and state["search"] is None
    assert state["selected_fdc_id"] is None
    assert state["response"].startswith(UNAVAILABLE)
    check_no_values(state)
    assert len(llm.prompts) == 1          # the selection step never ran: nothing to select from


# -- selection guards: irrelevant results, hallucinated IDs, garbage ---------------------


def test_irrelevant_results_llm_declines_no_values():
    """USDA returns salmon entries for a query the LLM judges unrelated: it answers null, Roli gives no values."""
    graph, _, rec = make_graph([
        interpret_reply("dragon fruit, raw", "salmon chinook cooked dry heat", "raw"),  # query maps to the salmon list
        select_reply(None, "none of these is dragon fruit"),
    ])
    state = run(graph, "dragon fruit")
    assert state["selected_fdc_id"] is None
    assert "none matches it (no candidate names the same food and preparation)" in state["response"]
    assert "none of these is dragon fruit" not in state["response"]          # LLM wording stays out of the reply
    assert any("none of these is dragon fruit" in line for line in state["trace"])  # but is kept for debugging
    assert_no_nutrition_numbers(state["response"], *[c["fdc_id"] for c in state["search"]["candidates"]])
    assert len(rec.requests) == 1          # search only, no lookup


def test_llm_proposes_id_not_in_candidates_is_rejected():
    """The structural guard: an FDC ID that USDA did not return for this search is never looked up."""
    graph, _, rec = make_graph([INTERP, select_reply(99999999, "I remember this one")])
    state = run(graph, "cooked chinook salmon")
    assert state["selected_fdc_id"] is None
    assert "not among USDA's results" in state["response"]
    assert any("REJECTED" in line for line in state["trace"])
    assert len(rec.requests) == 1          # no lookup of the invented ID
    assert_no_nutrition_numbers(state["response"], *[c["fdc_id"] for c in state["search"]["candidates"]])


def test_llm_proposes_bool_or_string_id_is_rejected():
    for bad in ('{"fdc_id": true, "reason": "x"}', '{"fdc_id": "171999", "reason": "x"}'):
        graph, _, rec = make_graph([INTERP, bad])
        state = run(graph, "cooked chinook salmon")
        assert state["selected_fdc_id"] is None and len(rec.requests) == 1


def test_no_candidates_at_all():
    graph, llm, rec = make_graph([interpret_reply("unicorn steak", "unicorn steak cooked")])
    state = run(graph, "unicorn steak")
    assert state["search"]["candidates"] == [] and state["selected_fdc_id"] is None
    assert 'has no entry matching "unicorn steak"' in state["response"]
    assert_no_nutrition_numbers(state["response"])
    assert len(llm.prompts) == 1


def test_unparsable_interpretation_is_unclear():
    graph, _, rec = make_graph(["Sure! Chinook salmon has about 3.2 g saturated fat per 100 g."])
    state = run(graph, "chinook?")
    assert state["intent"] == "unclear"
    assert rec.requests == []
    assert "could not work out which food" in state["response"]
    assert "3.2" not in state["response"]   # the LLM's own figure never reaches the user


def test_invalid_query_from_llm_is_handled_by_the_service():
    """201 characters of query: the service answers invalid_input; Roli reports unavailability."""
    graph, _, rec = make_graph([interpret_reply("x", "a" * 201)])
    state = run(graph, "x")
    assert state["search_error"]["error_code"] == "invalid_input"
    assert rec.requests == []
    check_no_values(state)


def test_usda_values_never_leak_from_a_failed_run_into_the_next(chinook_body):
    """A failed lookup followed by a good one on the same graph: state is per request."""
    graph, _, _ = make_graph(
        [INTERP, select_reply(CHINOOK), INTERP, select_reply(CHINOOK)],
        sequence(httpx.Response(404, content=b""), httpx.Response(200, json=chinook_body)),
    )
    failed = run(graph, "cooked chinook salmon")
    ok = run(graph, "cooked chinook salmon")
    assert failed["nutrition"] is None and failed["numbers_allowed"] is not True
    assert ok["nutrition"]["saturated_fat_g"] == 3.214 and ok["numbers_allowed"] is True
