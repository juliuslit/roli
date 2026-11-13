"""Spec v2.2 (Julius, 2026-11-05): Survey (FNDDS) records are accepted as per-100 g foods, searched only on request, and their recipe inputs can be read."""

from __future__ import annotations

import json

import httpx
import pytest

from roli_nutrition import ErrorResult, NutritionService, Settings
from roli_nutrition.inputs import InputsError, extract_inputs
from roli_nutrition.nutrients import extract_nutrition
from roli_nutrition.portions import extract_portions
from roli_nutrition.usda_client import UsdaClient

from conftest import load

OLIVES, COD, FRIES = 2710089, 2706244, 2709462


def test_a_survey_food_is_accepted_with_its_values_per_100g():
    r = extract_nutrition(OLIVES, load("food_survey_2710089"))
    assert r.data_type == "Survey (FNDDS)" and r.basis == "per_100g" and r.status == "complete"
    assert r.saturated_fat_g == 2.03 and r.cholesterol_mg == 0.0 and r.description == "Olives, green"
    cod = extract_nutrition(COD, load("food_survey_2706244"))
    assert (cod.saturated_fat_g, cod.cholesterol_mg) == (1.73, 42.0)                      # the finished fried fish, oil and batter included


def test_survey_portions_include_the_cup_weight_sr_legacy_lacks():
    p = extract_portions(OLIVES, load("food_survey_2710089"))
    assert {x.label: x.gram_weight for x in p.portions} == {"1 olive": 4.0, "Quantity not specified": 15.0, "1 cup": 135.0}
    cod = extract_portions(COD, load("food_survey_2706244"))
    assert {x.label: x.gram_weight for x in cod.portions}["1 small/regular fillet"] == 140.0


def test_survey_inputs_are_read_and_other_tables_have_none():
    i = extract_inputs(COD, load("food_survey_2706244"))
    by = {x.description[:12]: x.grams_per_100g for x in i.inputs}
    assert by["Fish, cod, P"] == 65.0 and by["Vegetable oi"] == 10.0 and by["Breading or "] == 25.0 and by["Salt, table"] == 0.6
    assert extract_inputs(171999, load("food_171999")).inputs == []                         # SR Legacy: not built from inputs
    with pytest.raises(InputsError) as info:
        extract_inputs(COD, load("food_survey_2709462"))
    assert info.value.code == "id_mismatch"


def test_search_sends_the_requested_tables_and_defaults_to_the_two_old_ones():
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen.append(json.loads(request.content)["dataType"])
            return httpx.Response(200, json=load("search_survey_olives") if seen[-1] == ["Survey (FNDDS)"] else {"totalHits": 0, "foods": []})
        return httpx.Response(404, content=b"")
    service = NutritionService(Settings(api_key="k"), client=UsdaClient("k", transport=httpx.MockTransport(respond)))
    default = service.search_foods("olives", 5)
    survey = service.search_foods("olives", 5, data_types=["Survey (FNDDS)"])
    assert seen == [["Foundation", "SR Legacy"], ["Survey (FNDDS)"]]
    assert default.candidates == [] and [c.fdc_id for c in survey.candidates][:4] == [2710092, 2710186, 2710090, 2710089]
    assert all(c.data_type == "Survey (FNDDS)" for c in survey.candidates)
    assert service.search_foods("olives", 5, data_types=["Survey (FNDDS)"]).candidates == survey.candidates and len(seen) == 2    # cached per table set
    bad = service.search_foods("olives", 5, data_types=["Branded"])
    assert isinstance(bad, ErrorResult) and bad.error_code == "invalid_input"


def test_service_get_inputs_round_trip():
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=load("food_survey_2706244")) if request.url.path.endswith(f"/food/{COD}") else httpx.Response(404, content=b"")
    service = NutritionService(Settings(api_key="k"), client=UsdaClient("k", transport=httpx.MockTransport(respond)))
    r = service.get_inputs(COD)
    assert r.status == "complete" and len(r.inputs) == 4 and r.description == "Fish, cod, fried"
    assert isinstance(service.get_inputs(999), ErrorResult)


def test_inputs_carry_usdas_moisture_change_and_the_scale_to_100_g_of_finished_food():
    """Spec v2.4 (2026-11-06): input weights are the recipe before cooking. "Fish, cod, fried": 100.6 g of inputs at -15 % moisture; fries from fresh: 115.4 g at 0 %."""
    cod = extract_inputs(COD, load("food_survey_2706244"))
    assert cod.moisture_change_pct == -15.0 and abs(cod.grams_per_100g_scale - 100 / (100.6 * 0.85)) < 1e-9
    fries = extract_inputs(2709458, load("food_survey_2709458"))
    assert fries.moisture_change_pct == 0.0 and abs(fries.grams_per_100g_scale - 100 / 115.4) < 1e-9
    sr = extract_inputs(171999, load("food_171999"))
    assert sr.moisture_change_pct is None and sr.grams_per_100g_scale is None and sr.inputs == []
