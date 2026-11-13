"""Phase 2A worked examples: Bluefin Crudo (T18, T25, T26), Little Gem Lettuces (T19), scenario comparison (T17, T28).

All ingredient weights below are HYPOTHETICAL, chosen to exercise the calculator; they are not
measurements of the restaurant's dishes.
"""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest

from roli_nutrition.recipe import RecipeCalculator, RecipeInvalid, compare_scenarios

from test_recipe_calculator import BLUEFIN, BREAD, CHINOOK, LETTUCE, OLIVE, ROMANO, SESAME, TAHINI, TOMATO, calculator, ing, recipe

D = Decimal

BLUEFIN_CRUDO_A = {
    "recipe_name": "Bluefin crudo, scenario A (hypothetical weights)",
    "servings": 1,
    "ingredients": [
        {"name": "Bluefin tuna, raw", "fdc_id": BLUEFIN, "grams": "85", "preparation_state": "raw",
         "quantity_basis": "total_recipe", "assumption": "hypothetical: typical crudo portion"},
        {"name": "Bottarga", "fdc_id": None, "grams": "5", "preparation_state": "as_used",
         "quantity_basis": "total_recipe", "assumption": "no USDA record selected"},
        {"name": "Olive oil", "fdc_id": OLIVE, "grams": "10", "preparation_state": "as_used",
         "quantity_basis": "total_recipe", "assumption": "hypothetical: drizzle"},
    ],
}

# Spec SPEC_2A_recipe_calculator.md, section 8, reproduced exactly (T25).
SPEC_SECTION_8_EXPECTED = {
    "status": "incomplete",
    "recipe_name": "Bluefin crudo, scenario A (hypothetical weights)",
    "servings": "1",
    "calculator_version": "2a.1",
    "source": "USDA FoodData Central",
    "per_serving_precision": "6 decimal places",
    "completeness_note": "complete = every supplied ingredient was calculated from a validated USDA record with the supplied grams; it does not verify that the list or weights match the restaurant's dish",
    "ingredients": [
        {"ingredient_id": "ing_01", "name": "Bluefin tuna, raw", "grams_declared": "85", "quantity_basis": "total_recipe",
         "grams_in_recipe": "85", "preparation_state": "raw", "assumption": "hypothetical: typical crudo portion",
         "usda": {"fdc_id": 173706, "description": "Fish, tuna, fresh, bluefin, raw", "data_type": "SR Legacy",
                  "saturated_fat_g_per_100g": "1.257", "cholesterol_mg_per_100g": "38", "record_state": "raw"},
         "usda_error": None, "compatibility": "compatible",
         "contribution": {"saturated_fat_g": "1.06845", "cholesterol_mg": "32.3"},
         "resolved": {"saturated_fat_g": True, "cholesterol_mg": True}, "issues": []},
        {"ingredient_id": "ing_02", "name": "Bottarga", "grams_declared": "5", "quantity_basis": "total_recipe",
         "grams_in_recipe": "5", "preparation_state": "as_used", "assumption": "no USDA record selected",
         "usda": None, "usda_error": None, "compatibility": "not_applicable",
         "contribution": {"saturated_fat_g": None, "cholesterol_mg": None},
         "resolved": {"saturated_fat_g": False, "cholesterol_mg": False}, "issues": ["missing_fdc_id"]},
        {"ingredient_id": "ing_03", "name": "Olive oil", "grams_declared": "10", "quantity_basis": "total_recipe",
         "grams_in_recipe": "10", "preparation_state": "as_used", "assumption": "hypothetical: drizzle",
         "usda": {"fdc_id": 171413, "description": "Oil, olive, salad or cooking", "data_type": "SR Legacy",
                  "saturated_fat_g_per_100g": "13.808", "cholesterol_mg_per_100g": "0", "record_state": "unknown"},
         "usda_error": None, "compatibility": "compatible",
         "contribution": {"saturated_fat_g": "1.3808", "cholesterol_mg": "0"},
         "resolved": {"saturated_fat_g": True, "cholesterol_mg": True}, "issues": []},
    ],
    "totals": {
        "saturated_fat_g": {"complete": False, "total": None, "known_subtotal": "2.44925",
                            "covers": ["ing_01", "ing_03"], "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
        "cholesterol_mg": {"complete": False, "total": None, "known_subtotal": "32.3",
                           "covers": ["ing_01", "ing_03"], "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
    },
    "per_serving": {
        "saturated_fat_g": {"complete": False, "total": None, "known_subtotal": "2.449250", "covers": ["ing_01", "ing_03"],
                            "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
        "cholesterol_mg": {"complete": False, "total": None, "known_subtotal": "32.300000", "covers": ["ing_01", "ing_03"],
                           "excludes": [{"ingredient_id": "ing_02", "name": "Bottarga", "reason": "missing_fdc_id"}]},
    },
    "issues": [{"ingredient_id": "ing_02", "code": "missing_fdc_id", "message": "Bottarga has no USDA record; its contribution is unknown and not included."}],
    "display": {"saturated_fat_g": "at least 2.45 g per serving from 2 of 3 ingredients; missing: Bottarga",
                "cholesterol_mg": "at least 32 mg per serving from 2 of 3 ingredients; missing: Bottarga"},
}


def test_t18_t25_bluefin_crudo_matches_the_spec_example_exactly():
    calc, _ = calculator()
    r = calc.calculate(BLUEFIN_CRUDO_A)
    assert r.model_dump(mode="json") == SPEC_SECTION_8_EXPECTED
    # Reconciliation of the example itself: every covered contribution is in the subtotal.
    assert D("1.06845") + D("1.3808") == D("2.44925") and D("32.3") + D("0") == D("32.3")


def test_t18_bottarga_cannot_be_silently_omitted():
    calc, _ = calculator()
    r = calc.calculate(BLUEFIN_CRUDO_A)
    text = json.dumps(r.model_dump(mode="json"))
    assert r.status == "incomplete"
    assert "Bottarga" in r.display["saturated_fat_g"] and "Bottarga" in r.display["cholesterol_mg"]
    assert all(e.name == "Bottarga" for n in r.totals.values() for e in n.excludes)
    assert r.totals["saturated_fat_g"].total is None             # no "dish total" exists
    assert "at least" in r.display["saturated_fat_g"]
    assert text.count("Bottarga") >= 5                           # ingredient, two totals, two per-serving, issue, display


def test_t26_unresolved_contributions_are_null_in_every_case(chinook_body):
    calc, _ = calculator({BLUEFIN: httpx.Response(503)})
    r = calc.calculate(recipe("All the ways to be unresolved", 1,
                              ing("No record", None, "10"),
                              ing("No grams", OLIVE, None),
                              ing("USDA down", BLUEFIN, "50", "raw"),
                              ing("Mismatch", CHINOOK, "50", "raw"),
                              ing("Unknown state", ROMANO, "10", "raw"),
                              ing("as_used fish", CHINOOK, "50", "as_used")))
    for i in r.ingredients:
        assert i.contribution.saturated_fat_g is None and i.contribution.cholesterol_mg is None, i.ingredient_id
        assert i.resolved == {"saturated_fat_g": False, "cholesterol_mg": False}
    # but the reader still sees what was fetched and why each line is out
    assert r.ingredients[3].usda.description == "Fish, salmon, chinook, cooked, dry heat"
    assert [e.reason for e in r.totals["saturated_fat_g"].excludes] == [
        "missing_fdc_id", "missing_grams", "usda_error:usda_unavailable", "preparation_mismatch",
        "preparation_unresolved", "as_used_not_accepted_for_flesh"]
    assert r.display["saturated_fat_g"].startswith("unknown: no ingredient could be calculated")


def test_t19_little_gem_lettuces_complete_with_contributions():
    calc, _ = calculator()
    r = calc.calculate(recipe("Little Gem Lettuces (hypothetical weights)", 1,
                              ing("Little gem lettuce (green leaf lettuce as the nearest USDA record)", LETTUCE, "80", "raw",
                                  assumption="hypothetical: a starter-sized salad"),
                              ing("Tahini vinaigrette (tahini)", TAHINI, "25", assumption="hypothetical: 2 tablespoons"),
                              ing("Pecorino sardo (USDA romano as the nearest record)", ROMANO, "10", assumption="hypothetical: a light grating"),
                              ing("Toasted sesame", SESAME, "5", assumption="hypothetical: a sprinkle")))
    assert r.status == "complete"
    sat = [i.contribution.saturated_fat_g for i in r.ingredients]
    chol = [i.contribution.cholesterol_mg for i in r.ingredients]
    assert sat == [D("0.016"), D("1.88225"), D("1.7115"), D("0.3361")]
    assert chol == [D("0"), D("0"), D("10.4"), D("0")]
    assert r.totals["saturated_fat_g"].total == D("3.94585") and r.totals["cholesterol_mg"].total == D("10.4")
    assert r.display["saturated_fat_g"] == "3.95 g per serving" and r.display["cholesterol_mg"] == "10 mg per serving"
    assert all(i.assumption and i.assumption.startswith("hypothetical") for i in r.ingredients)


# -- T17, T28: three scenarios -------------------------------------------------------------------------


def test_t17_three_scenarios_min_median_max_over_complete_ones():
    calc, _ = calculator()
    a = calc.calculate(recipe("Crudo A, lean", 1, ing("Bluefin", BLUEFIN, "85", "raw"), ing("Olive oil", OLIVE, "5")))
    b = calc.calculate(BLUEFIN_CRUDO_A)                                                         # incomplete: bottarga
    c = calc.calculate(recipe("Crudo C, oily", 1, ing("Bluefin", BLUEFIN, "110", "raw"), ing("Olive oil", OLIVE, "15")))
    cmp = compare_scenarios([a, b, c])
    sat = cmp.nutrients["saturated_fat_g"]
    assert sat.n_scenarios == 3 and sat.n_complete == 2 and sat.range_meaningful is True
    assert set(sat.values) == {"Crudo A, lean", "Crudo C, oily"}
    assert sat.values["Crudo A, lean"] == D("1.758850") and sat.values["Crudo C, oily"] == D("3.453900")
    assert (sat.min, sat.median, sat.max) == (D("1.758850"), D("2.606375"), D("3.453900"))
    assert sat.excluded == [] or sat.excluded[0].recipe_name.startswith("Bluefin crudo, scenario A")
    assert sat.excluded[0].reason == "incomplete"
    assert "not a statistical confidence interval" in sat.note and "confidence interval" not in sat.note.replace("not a statistical confidence interval", "")
    assert cmp.scenarios[1] is b                                                                  # originals preserved
    chol = cmp.nutrients["cholesterol_mg"]
    assert (chol.min, chol.median, chol.max) == (D("32.300000"), D("37.050000"), D("41.800000"))


def test_t28_fewer_than_two_complete_scenarios_is_insufficient():
    calc, _ = calculator()
    one = calc.calculate(recipe("Only complete one", 1, ing("Bluefin", BLUEFIN, "85", "raw")))
    bad = calc.calculate(recipe("Broken", 0, ing("Bluefin", BLUEFIN, "85", "raw")))
    assert isinstance(bad, RecipeInvalid)
    cmp = compare_scenarios([one, BLUEFIN_CRUDO_A and calc.calculate(BLUEFIN_CRUDO_A), bad])
    sat = cmp.nutrients["saturated_fat_g"]
    assert sat.n_complete == 1 and sat.range_meaningful is False
    assert sat.min == sat.median == sat.max == D("1.068450")
    assert "insufficient for a meaningful range" in sat.note
    assert [e.reason for e in sat.excluded] == ["incomplete", "invalid_recipe"]
    none = compare_scenarios([calc.calculate(BLUEFIN_CRUDO_A)])
    assert none.nutrients["cholesterol_mg"].values == {} and none.nutrients["cholesterol_mg"].min is None
    assert "insufficient" in none.nutrients["cholesterol_mg"].note


def test_compare_rejects_mixed_servings_on_totals_basis_and_duplicate_names():
    calc, _ = calculator()
    a = calc.calculate(recipe("A", 1, ing("Bluefin", BLUEFIN, "85", "raw")))
    b = calc.calculate(recipe("B", 2, ing("Bluefin", BLUEFIN, "85", "raw")))
    with pytest.raises(ValueError, match="same servings"):
        compare_scenarios([a, b], basis="totals")
    assert compare_scenarios([a, b], basis="per_serving").nutrients["cholesterol_mg"].n_complete == 2
    with pytest.raises(ValueError, match="distinct"):
        compare_scenarios([a, a])
