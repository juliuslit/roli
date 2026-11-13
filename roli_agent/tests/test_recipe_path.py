"""Phase 2A in the graph: a caller-supplied recipe takes the calculator path with no LLM call."""

from __future__ import annotations

import json
import re

from roli_agent.graph import run_roli

from conftest import FakeLLM, Recorder, make_service

BLUEFIN, OLIVE, CHINOOK, LETTUCE = 173706, 171413, 171999, 169249


def recipe_service():
    """USDA on every saved food fixture (same files as the nutrition service's own recipe tests)."""
    import glob, os
    from conftest import FIXTURES
    foods = {}
    for path in glob.glob(str(FIXTURES / "food_*.json")):
        name = os.path.basename(path)
        if "unfiltered" in name or "branded" in name:
            continue
        body = json.loads(open(path, encoding="utf-8").read())
        foods[body["fdcId"]] = body
    import httpx

    def respond(request):
        m = re.search(r"/food/(\d+)$", request.url.path)
        body = foods.get(int(m.group(1))) if m else None
        return httpx.Response(200, json=body) if body else httpx.Response(404, content=b"")
    return make_service(respond)


def make_graph_for_recipes():
    from roli_agent.graph import build_graph
    service, rec = recipe_service()
    llm = FakeLLM([])                                   # must never be called on this path
    return build_graph(llm=llm, service=service, load_prompt=lambda v: "x"), llm, rec


CRUDO = {
    "recipe_name": "Bluefin crudo (hypothetical weights)",
    "servings": 1,
    "ingredients": [
        {"name": "Bluefin tuna, raw", "fdc_id": BLUEFIN, "grams": "85", "preparation_state": "raw", "assumption": "hypothetical"},
        {"name": "Bottarga", "fdc_id": None, "grams": "5", "preparation_state": "as_used", "assumption": "no USDA record"},
        {"name": "Olive oil", "fdc_id": OLIVE, "grams": "10", "preparation_state": "as_used", "assumption": "hypothetical"},
    ],
}


def test_complete_recipe_reply_lists_every_contribution_and_totals():
    graph, llm, rec = make_graph_for_recipes()
    out = run_roli(recipe={"recipe_name": "Salmon for two", "servings": 2, "ingredients": [
        {"name": "Chinook, cooked", "fdc_id": CHINOOK, "grams": "300", "preparation_state": "cooked", "assumption": "hypothetical"},
        {"name": "Olive oil", "fdc_id": OLIVE, "grams": "10", "preparation_state": "as_used"},
    ]}, graph=graph)
    state, reply = out["state"], out["response"]
    assert state["intent"] == "recipe" and state["numbers_allowed"] is True and state["recipe_error"] is None
    assert llm.prompts == []                            # no LLM call anywhere on this path
    assert len(rec.requests) == 2                       # one USDA lookup per distinct record
    assert reply.splitlines()[0] == "Recipe: Salmon for two (2 serving(s)); calculation complete."
    assert '- Chinook, cooked: 300 g; USDA 171999 "Fish, salmon, chinook, cooked, dry heat"; 9.642 g saturated fat, 255 mg cholesterol [hypothetical]' in reply
    assert '- Olive oil: 10 g; USDA 171413 "Oil, olive, salad or cooking"; 1.3808 g saturated fat, 0 mg cholesterol' in reply
    assert "- Saturated fat: 5.51 g per serving (11.02 g for the whole recipe, 2 servings)" in reply
    assert "- Cholesterol: 128 mg per serving (255 mg for the whole recipe, 2 servings)" in reply
    assert "known subtotals" not in reply
    assert state["recipe_result"]["totals"]["saturated_fat_g"]["total"] == "11.0228"


def test_incomplete_recipe_reply_never_states_a_dish_total():
    graph, llm, _ = make_graph_for_recipes()
    out = run_roli(recipe=CRUDO, graph=graph)
    reply = out["response"]
    assert "calculation incomplete." in reply.splitlines()[0]
    assert "- Bottarga: 5 g; no USDA record; not included: missing_fdc_id [no USDA record]" in reply
    assert "- Saturated fat: at least 2.45 g per serving from 2 of 3 ingredients; missing: Bottarga" in reply
    assert "- Cholesterol: at least 32 mg per serving from 2 of 3 ingredients; missing: Bottarga" in reply
    assert "known subtotals from the ingredients that could be calculated, not totals for the dish" in reply
    assert not re.search(r"\bcontains\b", reply)
    assert out["state"]["recipe_result"]["totals"]["cholesterol_mg"]["total"] is None
    assert llm.prompts == []


def test_invalid_recipe_reply_has_no_numbers_and_no_usda_calls():
    graph, llm, rec = make_graph_for_recipes()
    out = run_roli(recipe={"recipe_name": "Broken", "servings": 0, "ingredients": [
        {"name": "Chinook", "fdc_id": CHINOOK, "grams": "-1", "preparation_state": "cooked"}]}, graph=graph)
    state, reply = out["state"], out["response"]
    assert state["recipe_error"]["status"] == "invalid_recipe" and state["numbers_allowed"] is False
    assert "could not be calculated because its description is invalid" in reply
    assert "servings" in reply and "grams" in reply
    assert "Roli does not estimate them from other sources" in reply
    assert rec.requests == [] and llm.prompts == []


def test_recipe_path_ignores_text_and_photo_and_keeps_food_path_intact():
    graph, llm, rec = make_graph_for_recipes()
    out = run_roli(text="what is in chinook salmon", photo_path="/nowhere.jpg", recipe=CRUDO, graph=graph)
    assert out["state"]["intent"] == "recipe" and llm.prompts == []
    # and a plain text request still takes the interpret path (LLM would be called: FakeLLM has no reply -> AssertionError)
    import pytest
    with pytest.raises(AssertionError):
        run_roli(text="chinook salmon", graph=graph)
