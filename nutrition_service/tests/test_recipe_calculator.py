"""Phase 2A recipe calculator: spec SPEC_2A_recipe_calculator.md section 11, tests T1–T21, T24–T27."""

from __future__ import annotations

import copy
import glob
import json
import os
import re
from decimal import Decimal

import httpx
import pytest

from roli_nutrition.recipe import RecipeCalculator, RecipeInput, RecipeInvalid, RecipeResult
from roli_nutrition.recipe.calculator import display_amount

from captured_expectations import RECIPE_RECORDS
from conftest import FIXTURES, FOOD_171999, SENTINEL_KEY, make_service, mutate

D = Decimal
CHINOOK, BLUEFIN, OLIVE, TAHINI, ROMANO, SESAME, LETTUCE, TOMATO, BREAD, BROCCOLI = (
    171999, 173706, 171413, 170189, 171249, 170151, 169249, 170457, 172675, 747447)


# -- USDA on every saved food fixture -------------------------------------------


def all_food_fixtures() -> dict[int, dict]:
    foods = {}
    for path in glob.glob(str(FIXTURES / "food_*.json")):
        name = os.path.basename(path)
        if "unfiltered" in name or "branded" in name:
            continue
        body = json.loads(open(path, encoding="utf-8").read())
        foods[body["fdcId"]] = body
    return foods


def recipe_router(overrides: dict | None = None):
    foods = all_food_fixtures()
    foods.update(overrides or {})

    def respond(request: httpx.Request) -> httpx.Response:
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        item = foods.get(fid)
        if item is None:
            return httpx.Response(404, content=b"")
        if isinstance(item, httpx.Response):
            return item
        if isinstance(item, Exception):
            raise item
        return httpx.Response(200, json=item)
    return respond


def calculator(overrides=None):
    service, rec = make_service(recipe_router(overrides))
    return RecipeCalculator(service), rec


def ing(name, fdc_id, grams, state="as_used", **extra):
    return {"name": name, "fdc_id": fdc_id, "grams": grams, "preparation_state": state, **extra}


def recipe(name, servings, *ingredients):
    return {"recipe_name": name, "servings": servings, "ingredients": list(ingredients)}


def by_id(result: RecipeResult, ingredient_id: str):
    return next(i for i in result.ingredients if i.ingredient_id == ingredient_id)


# -- T1–T4: complete recipes -------------------------------------------------------


def test_t1_single_ingredient_complete():
    calc, rec = calculator()
    r = calc.calculate(recipe("Salmon only", 1, ing("Chinook, cooked", CHINOOK, "100", "cooked")))
    assert isinstance(r, RecipeResult) and r.status == "complete"
    i = r.ingredients[0]
    assert i.usda.description == "Fish, salmon, chinook, cooked, dry heat" and i.compatibility == "compatible"
    assert i.contribution.saturated_fat_g == D("3.214") and i.contribution.cholesterol_mg == D("85")
    assert r.totals["saturated_fat_g"].total == D("3.214") and r.totals["cholesterol_mg"].total == D("85")
    assert r.per_serving["cholesterol_mg"].total == D("85.000000")
    assert r.display["saturated_fat_g"] == "3.21 g per serving"
    assert len(rec.requests) == 1


def test_t4_exact_150g_chinook_acceptance():
    calc, _ = calculator()
    r = calc.calculate(recipe("150 g chinook", 1, ing("Chinook", CHINOOK, "150", "cooked")))
    assert r.totals["saturated_fat_g"].total == D("4.821")      # 3.214 x 1.5, exact
    assert r.totals["cholesterol_mg"].total == D("127.5")       # 85 x 1.5, exact
    assert r.per_serving["saturated_fat_g"].total == D("4.821000")
    dumped = r.model_dump(mode="json")
    assert dumped["totals"]["saturated_fat_g"]["total"] == "4.821" and dumped["totals"]["cholesterol_mg"]["total"] == "127.5"


def test_t2_multiple_ingredients_totals_reconcile():
    calc, rec = calculator()
    r = calc.calculate(recipe("Salmon plate", 1,
                              ing("Chinook", CHINOOK, "150", "cooked"),
                              ing("Tomatoes", TOMATO, "120", "raw"),
                              ing("Sourdough", BREAD, "40")))
    assert r.status == "complete"
    contributions = [i.contribution.saturated_fat_g for i in r.ingredients]
    assert contributions == [D("4.821"), D("0.0336"), D("0.2116")]
    assert r.totals["saturated_fat_g"].total == sum(contributions) == D("5.0662")
    assert r.totals["cholesterol_mg"].total == D("127.5")
    assert r.totals["saturated_fat_g"].covers == ["ing_01", "ing_02", "ing_03"]
    assert len(rec.requests) == 3


def test_t3_four_servings():
    calc, _ = calculator()
    r = calc.calculate(recipe("Family salmon", 4, ing("Chinook", CHINOOK, "600", "cooked")))
    assert r.totals["saturated_fat_g"].total == D("19.284") and r.totals["cholesterol_mg"].total == D("510")
    assert r.per_serving["saturated_fat_g"].total == D("4.821000") and r.per_serving["cholesterol_mg"].total == D("127.500000")
    assert r.display["cholesterol_mg"] == "128 mg per serving (510 mg for the whole recipe, 4 servings)"


def test_t5_oil_and_dressing_as_used_on_unknown_state_records():
    calc, _ = calculator()
    r = calc.calculate(recipe("Dressed", 1, ing("Olive oil", OLIVE, "10"), ing("Tahini", TAHINI, "25")))
    assert r.status == "complete"
    assert r.ingredients[0].usda.record_state == "unknown" and r.ingredients[0].compatibility == "compatible"
    assert r.ingredients[1].usda.record_state == "cooked"       # "roasted and toasted" in the description
    assert r.ingredients[0].contribution.saturated_fat_g == D("1.3808")
    assert r.ingredients[1].contribution.saturated_fat_g == D("1.88225")
    assert r.totals["saturated_fat_g"].total == D("3.26305") and r.totals["cholesterol_mg"].total == D("0")


# -- T6–T8: incomplete recipes -----------------------------------------------------


def test_t6_missing_fdc_id_gives_known_subtotal_not_total():
    calc, _ = calculator()
    r = calc.calculate(recipe("Crudo", 1, ing("Bluefin", BLUEFIN, "85", "raw"), ing("Bottarga", None, "5")))
    assert r.status == "incomplete"
    for n in ("saturated_fat_g", "cholesterol_mg"):
        t = r.totals[n]
        assert t.complete is False and t.total is None
        assert t.covers == ["ing_01"] and [e.name for e in t.excludes] == ["Bottarga"]
        assert t.excludes[0].reason == "missing_fdc_id"
    assert r.totals["saturated_fat_g"].known_subtotal == D("1.06845")
    assert r.totals["cholesterol_mg"].known_subtotal == D("32.3")
    assert by_id(r, "ing_02").contribution.saturated_fat_g is None and by_id(r, "ing_02").usda is None
    assert r.display["cholesterol_mg"] == "at least 32 mg per serving from 1 of 2 ingredients; missing: Bottarga"
    assert "Bottarga has no USDA record" in r.issues[0].message


def test_t7_t16_nutrient_not_reported_distinct_completeness():
    """Foundation broccoli reports saturated fat but no cholesterol: fat complete, cholesterol incomplete."""
    calc, _ = calculator()
    r = calc.calculate(recipe("Greens", 1, ing("Broccoli", BROCCOLI, "100", "raw"), ing("Lettuce", LETTUCE, "50", "raw")))
    assert r.status == "incomplete"
    assert r.totals["saturated_fat_g"].complete is True and r.totals["saturated_fat_g"].total == D("0.049")
    chol = r.totals["cholesterol_mg"]
    assert chol.complete is False and chol.total is None and chol.known_subtotal == D("0") and chol.covers == ["ing_02"]
    assert chol.excludes[0].reason == "nutrient_not_reported:cholesterol_mg"
    assert by_id(r, "ing_01").contribution.cholesterol_mg is None
    assert by_id(r, "ing_01").contribution.saturated_fat_g == D("0.039")
    assert by_id(r, "ing_01").resolved == {"saturated_fat_g": True, "cholesterol_mg": False}


def test_t8_partial_plant_record_in_mixed_recipe():
    calc, _ = calculator()
    r = calc.calculate(recipe("Salmon and broccoli", 2, ing("Chinook", CHINOOK, "300", "cooked"), ing("Broccoli", BROCCOLI, "200", "raw")))
    assert r.totals["saturated_fat_g"].complete and r.totals["saturated_fat_g"].total == D("9.720")
    assert not r.totals["cholesterol_mg"].complete and r.totals["cholesterol_mg"].known_subtotal == D("255")
    assert r.display["cholesterol_mg"].startswith("at least 128 mg per serving from 1 of 2 ingredients; missing: Broccoli")


# -- T9–T11: preparation state -------------------------------------------------------


def test_t9_raw_grams_on_cooked_record_is_a_mismatch():
    calc, _ = calculator()
    r = calc.calculate(recipe("Wrong basis", 1, ing("Chinook, raw weight", CHINOOK, "150", "raw")))
    i = r.ingredients[0]
    assert i.compatibility == "mismatch" and "preparation_mismatch" in i.issues
    assert i.contribution.saturated_fat_g is None and i.contribution.cholesterol_mg is None
    assert r.status == "incomplete" and r.totals["saturated_fat_g"].known_subtotal == D("0")
    assert r.display["saturated_fat_g"].startswith("unknown: no ingredient could be calculated")
    assert "weights are not interchangeable" in r.issues[0].message


def test_t10_cooked_grams_on_raw_record_is_a_mismatch():
    calc, _ = calculator()
    r = calc.calculate(recipe("Seared tuna", 1, ing("Bluefin, cooked", BLUEFIN, "120", "cooked")))
    assert r.ingredients[0].compatibility == "mismatch" and r.status == "incomplete"


def test_t11_unresolved_states():
    calc, _ = calculator()
    r = calc.calculate(recipe("Vague", 1,
                              ing("Romano, raw?", ROMANO, "10", "raw"),          # record state unknown
                              ing("Bluefin, unknown", BLUEFIN, "100", "unknown"),  # ingredient state unknown
                              ing("Bluefin, as used", BLUEFIN, "100", "as_used")))  # as_used refused for fish
    a, b, c = r.ingredients
    assert a.compatibility == "unresolved" and "preparation_unresolved" in a.issues
    assert b.compatibility == "unresolved" and "preparation_unresolved" in b.issues
    assert c.compatibility == "unresolved" and "as_used_not_accepted_for_flesh" in c.issues
    assert all(i.contribution.saturated_fat_g is None for i in r.ingredients)
    assert "declare raw or cooked" in next(x.message for x in r.issues if x.code == "as_used_not_accepted_for_flesh")


# -- T12: invalid recipes --------------------------------------------------------------


@pytest.mark.parametrize("bad, fragment", [
    (recipe("x", 0, ing("a", CHINOOK, "1")), "servings"),
    (recipe("x", -2, ing("a", CHINOOK, "1")), "servings"),
    (recipe("x", "abc", ing("a", CHINOOK, "1")), "servings"),
    (recipe("x", 1, ing("a", CHINOOK, "-5")), "grams"),
    (recipe("x", 1, ing("a", CHINOOK, "NaN")), "grams"),
    (recipe("x", 1, ing("a", CHINOOK, "inf")), "grams"),
    (recipe("x", 1, ing("a", CHINOOK, True)), "grams"),
    (recipe("x", 1, ing("a", 0, "1")), "fdc_id"),
    (recipe("x", 1, ing("a", "171999", "1")), "fdc_id"),
    (recipe("x", 1, ing("a", CHINOOK, "1", "grilled")), "preparation_state"),
    (recipe("x", 1, ing("a", CHINOOK, "1", quantity_basis="per_portion")), "quantity_basis"),
    (recipe("x", 1), "ingredients"),
    (recipe("x", 1, *[ing(f"a{i}", CHINOOK, "1") for i in range(101)]), "ingredients"),
    ({"recipe_name": "x", "servings": 1, "ingredients": [ing("a", CHINOOK, "1")], "extra": 1}, "extra"),
    (recipe("x", 1, ing("a", CHINOOK, "1", ingredient_id="dup"), ing("b", CHINOOK, "1", ingredient_id="dup")), "duplicate ingredient_id"),
])
def test_t12_invalid_recipe_names_every_problem(bad, fragment):
    calc, rec = calculator()
    r = calc.calculate(bad)
    assert isinstance(r, RecipeInvalid) and r.status == "invalid_recipe"
    assert any(fragment in p for p in r.problems), r.problems
    assert rec.requests == []                   # nothing is fetched for an invalid recipe


def test_t12_all_problems_listed_at_once():
    calc, _ = calculator()
    r = calc.calculate(recipe("x", 0, ing("a", CHINOOK, "-1"), ing("b", -3, "1")))
    assert len(r.problems) >= 3


# -- T13, T20, T21: duplicates, basis conversion, explicit zero ---------------------------


def test_t13_duplicate_fdc_ids_counted_twice_fetched_once():
    calc, rec = calculator()
    r = calc.calculate(recipe("Two salmon lines", 1, ing("Fillet A", CHINOOK, "100", "cooked"), ing("Fillet B", CHINOOK, "50", "cooked")))
    assert r.totals["saturated_fat_g"].total == D("4.821")
    assert all("duplicate_fdc_id" in i.issues for i in r.ingredients)
    assert len(rec.requests) == 1
    assert not any(x.code == "duplicate_fdc_id" for x in r.issues)   # informational, not a problem


def test_t20_per_serving_basis_converted_and_flagged():
    calc, _ = calculator()
    r = calc.calculate(recipe("Per plate", 3, ing("Chinook", CHINOOK, "100", "cooked", quantity_basis="per_serving")))
    i = r.ingredients[0]
    assert i.grams_declared == D("100") and i.grams_in_recipe == D("300") and "per_serving_quantity_converted" in i.issues
    assert r.totals["saturated_fat_g"].total == D("9.642") and r.per_serving["saturated_fat_g"].total == D("3.214000")


def test_t21_explicit_zero_vs_unknown_grams():
    calc, _ = calculator()
    r = calc.calculate(recipe("Zero and unknown", 1,
                              ing("Chinook", CHINOOK, "100", "cooked"),
                              ing("Salt (zero)", None, "0"),
                              ing("Parsley (amount unknown)", LETTUCE, None, "raw")))
    zero, unknown = r.ingredients[1], r.ingredients[2]
    assert zero.contribution.saturated_fat_g == D("0") and zero.resolved["saturated_fat_g"] is True and "explicit_zero" in zero.issues
    assert unknown.contribution.saturated_fat_g is None and "missing_grams" in unknown.issues and unknown.usda is not None
    assert r.status == "incomplete" and r.totals["saturated_fat_g"].covers == ["ing_01", "ing_02"]
    assert r.totals["saturated_fat_g"].excludes[0].reason == "missing_grams"


# -- T14: USDA failures ----------------------------------------------------------------------


@pytest.mark.parametrize("failure, code", [
    (httpx.Response(503), "usda_unavailable"),
    (httpx.Response(429, json={"error": {"code": "OVER_RATE_LIMIT"}}), "rate_limited"),
    (httpx.Response(404, content=b""), "not_found"),
    (httpx.Response(200, content=b"not json"), "malformed_response"),
])
def test_t14_usda_failures_exclude_without_substitution(failure, code):
    calc, rec = calculator({BLUEFIN: failure})
    r = calc.calculate(recipe("Crudo", 1, ing("Bluefin", BLUEFIN, "85", "raw"), ing("Olive oil", OLIVE, "10")))
    i = by_id(r, "ing_01")
    assert i.usda is None and i.usda_error["error_code"] == code
    assert i.contribution.saturated_fat_g is None and f"usda_error:{code}" in i.issues
    assert r.status == "incomplete"
    assert r.totals["saturated_fat_g"].known_subtotal == D("1.3808") and r.totals["saturated_fat_g"].covers == ["ing_02"]
    assert r.totals["saturated_fat_g"].excludes[0].reason == f"usda_error:{code}"
    assert not any(req.url.path.endswith("/foods/search") for req in rec.requests)   # no alternative record searched


def test_t14_mismatched_id_from_usda(chinook_body):
    wrong = mutate(chinook_body, lambda b: b.update(fdcId=172001))
    calc, _ = calculator({CHINOOK: wrong})
    r = calc.calculate(recipe("x", 1, ing("Chinook", CHINOOK, "100", "cooked")))
    assert r.ingredients[0].usda_error["error_code"] == "id_mismatch" and r.ingredients[0].contribution.cholesterol_mg is None


# -- T15, T24: reconciliation ------------------------------------------------------------------


def every_test_recipe():
    return [
        recipe("A", 1, ing("Chinook", CHINOOK, "150", "cooked")),
        recipe("B", 3, ing("Chinook", CHINOOK, "100", "cooked"), ing("Tomato", TOMATO, "33", "raw"), ing("Oil", OLIVE, "7")),
        recipe("C", "1.5", ing("Bluefin", BLUEFIN, "85", "raw"), ing("Bottarga", None, "5"), ing("Oil", OLIVE, "10")),
        recipe("D", 7, ing("Lettuce", LETTUCE, "100", "raw"), ing("Romano", ROMANO, "10")),
    ]


@pytest.mark.parametrize("rec_in", every_test_recipe(), ids=lambda r: r["recipe_name"])
def test_t15_contributions_reconcile_with_subtotals(rec_in):
    calc, _ = calculator()
    r = calc.calculate(rec_in)
    s = D(str(rec_in["servings"]))
    for n in ("saturated_fat_g", "cholesterol_mg"):
        exact = sum((getattr(i.contribution, n) for i in r.ingredients if i.resolved[n]), D(0))
        assert exact == r.totals[n].known_subtotal
        assert abs(r.per_serving[n].known_subtotal * s - r.totals[n].known_subtotal) <= D("0.0000005") * s
        assert r.per_serving[n].known_subtotal == r.per_serving[n].known_subtotal.quantize(D("0.000001"))


def test_t24_recurring_decimals_are_quantized_and_reconcile():
    calc, _ = calculator()
    # 100 g of lettuce = 0.02 g saturated fat; over 3 servings -> 0.00666... -> 0.006667
    r = calc.calculate(recipe("Thirds", 3, ing("Lettuce", LETTUCE, "100", "raw")))
    assert r.totals["saturated_fat_g"].total == D("0.02")
    assert r.per_serving["saturated_fat_g"].total == D("0.006667")
    assert r.per_serving_precision == "6 decimal places"
    # 1/7 case: 700 g lettuce over 7 servings is exact, 100 g over 7 is recurring
    r7 = calc.calculate(recipe("Sevenths", 7, ing("Lettuce", LETTUCE, "100", "raw")))
    assert r7.per_serving["saturated_fat_g"].total == D("0.002857")
    assert abs(r7.per_serving["saturated_fat_g"].total * 7 - D("0.02")) <= D("0.0000005") * 7


# -- T27: display rounding -----------------------------------------------------------------------


def test_t27_display_rounding_never_shows_positive_as_zero():
    assert display_amount(D("0.004"), "saturated_fat_g") == "<0.01 g"
    assert display_amount(D("0.4"), "cholesterol_mg") == "<1 mg"
    assert display_amount(D("0"), "saturated_fat_g") == "0 g"
    assert display_amount(D("0.005"), "saturated_fat_g") == "0.01 g"      # half-up
    assert display_amount(D("127.5"), "cholesterol_mg") == "128 mg"
    assert display_amount(D("4.821"), "saturated_fat_g") == "4.82 g"
    calc, _ = calculator()
    r = calc.calculate(recipe("Tiny", 1, ing("Lettuce", LETTUCE, "10", "raw")))   # 0.002 g
    assert r.display["saturated_fat_g"] == "<0.01 g per serving"
    assert r.display["cholesterol_mg"] == "0 mg per serving"


# -- T23: output round-trips ------------------------------------------------------------------------


def test_t23_output_round_trips_through_models():
    calc, _ = calculator()
    r = calc.calculate(every_test_recipe()[2])
    dumped = r.model_dump(mode="json")
    again = RecipeResult.model_validate(dumped)
    assert again == r
    assert dumped["totals"]["saturated_fat_g"]["known_subtotal"] == "2.44925"
    with pytest.raises(Exception):
        RecipeResult.model_validate({**dumped, "surprise": 1})


def test_input_model_accepts_numbers_and_strings_equally():
    a = RecipeInput.model_validate(recipe("x", 2, ing("a", CHINOOK, 0.1)))
    b = RecipeInput.model_validate(recipe("x", "2", ing("a", CHINOOK, "0.1")))
    assert a.servings == b.servings == D("2") and a.ingredients[0].grams == b.ingredients[0].grams == D("0.1")
    assert a.ingredients[0].ingredient_id == "ing_01"
