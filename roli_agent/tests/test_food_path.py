"""Successful single-food lookups through the whole graph, on saved real USDA replies."""

from __future__ import annotations

from conftest import CHINOOK, MACKEREL, PINK, interpret_reply, make_graph, run, select_reply


def test_chinook_complete_lookup():
    graph, llm, rec = make_graph([
        interpret_reply("cooked Chinook salmon", "salmon chinook cooked dry heat"),
        select_reply(CHINOOK),
    ])
    state = run(graph, "Using USDA, tell me the saturated fat and cholesterol per 100g of cooked Chinook salmon.")

    assert state["intent"] == "food_lookup"
    assert state["selected_fdc_id"] == CHINOOK
    assert state["numbers_allowed"] is True
    n = state["nutrition"]
    assert (n["fdc_id"], n["saturated_fat_g"], n["cholesterol_mg"]) == (CHINOOK, 3.214, 85.0)
    assert state["nutrition_error"] is None and state["search_error"] is None
    assert state["response"] == (
        "Food: Fish, salmon, chinook, cooked, dry heat\n"
        "USDA FoodData Central record 171999 (SR Legacy), values per 100 g:\n"
        "- Saturated fat: 3.214 g\n"
        "- Cholesterol: 85 mg\n"
        "Source: USDA FoodData Central."
    )
    assert len(llm.prompts) == 2                      # interpret + select, nothing else
    assert len(rec.requests) == 2                     # one search, one lookup
    assert [r.url.path.split("/")[-1] for r in rec.requests] == ["search", str(CHINOOK)]


def test_pink_complete_lookup():
    graph, _, _ = make_graph([
        interpret_reply("cooked Pink salmon", "salmon pink cooked dry heat"),
        select_reply(PINK),
    ])
    state = run(graph, "Pink salmon, cooked: saturated fat and cholesterol?")
    n = state["nutrition"]
    assert (n["fdc_id"], n["saturated_fat_g"], n["cholesterol_mg"]) == (PINK, 0.971, 55.0)
    assert "- Saturated fat: 0.971 g" in state["response"]       # no rounding to 0.97
    assert "- Cholesterol: 55 mg" in state["response"]
    assert "Fish, salmon, pink, cooked, dry heat" in state["response"]


def test_king_salmon_resolves_to_chinook_not_mackerel():
    """The saved search for 'king salmon cooked dry heat' lists king mackerel first and chinook second."""
    graph, llm, _ = make_graph([
        interpret_reply("King salmon, cooked with dry heat", "king salmon cooked dry heat"),
        select_reply(CHINOOK, "king salmon is chinook; mackerel is a different fish"),
    ])
    state = run(graph, "Find the USDA nutritional information for King salmon cooked with dry heat.")
    ids = [c["fdc_id"] for c in state["search"]["candidates"]]
    assert ids[0] == MACKEREL and CHINOOK in ids
    assert state["selected_fdc_id"] == CHINOOK
    assert "chinook" in state["response"] and "mackerel" not in state["response"].lower()
    assert "3.214 g" in state["response"] and "85 mg" in state["response"]
    assert "fdc_id 174236: Fish, mackerel, king" in llm.prompts[1]   # the LLM saw the trap and was asked to choose
    assert state["selection_note"] == "selected from USDA's results"
    assert any("king salmon is chinook" in line for line in state["trace"])  # LLM reason kept in the trace only


def test_values_stay_with_their_own_fdc_id():
    """Two lookups in a row on one graph: each reply carries only its own record's values."""
    graph, _, _ = make_graph([
        interpret_reply("pink salmon", "salmon pink cooked dry heat"), select_reply(PINK),
        interpret_reply("chinook salmon", "salmon chinook cooked dry heat"), select_reply(CHINOOK),
    ])
    pink = run(graph, "pink salmon cooked")
    chinook = run(graph, "chinook salmon cooked")
    assert (pink["nutrition"]["fdc_id"], pink["nutrition"]["cholesterol_mg"]) == (PINK, 55.0)
    assert (chinook["nutrition"]["fdc_id"], chinook["nutrition"]["cholesterol_mg"]) == (CHINOOK, 85.0)
    assert "0.971" not in chinook["response"] and "55 mg" not in chinook["response"]
    assert "3.214" not in pink["response"] and "85 mg" not in pink["response"]


def test_partial_record_says_not_reported_never_zero(chinook_body):
    from conftest import mutate, usda_router
    body = mutate(chinook_body, lambda b: b["foodNutrients"].remove(
        next(r for r in b["foodNutrients"] if r["nutrient"]["id"] == 1253)))
    graph, _, _ = make_graph(
        [interpret_reply("chinook", "salmon chinook cooked dry heat"), select_reply(CHINOOK)],
        responder=usda_router(food_override={CHINOOK: body}),
    )
    state = run(graph, "chinook salmon")
    assert state["nutrition"]["status"] == "partial"
    assert state["missing_nutrients"] == ["cholesterol_mg"]
    assert "- Cholesterol: not reported by USDA for this record" in state["response"]
    assert "unknown, not zero" in state["response"]
    assert "Cholesterol: 0" not in state["response"]
    assert "- Saturated fat: 3.214 g" in state["response"]


def test_other_intent_gets_no_numbers_and_no_usda_call():
    graph, llm, rec = make_graph([interpret_reply("", "", intent="other")])
    state = run(graph, "hi there, what can you do?")
    assert state["intent"] == "other"
    assert rec.requests == []
    assert "USDA saturated fat and cholesterol for one specific food" in state["response"]
    assert "g\n" not in state["response"] and " mg" not in state["response"]
