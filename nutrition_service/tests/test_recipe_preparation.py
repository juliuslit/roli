"""T22: the raw/cooked classifier and compatibility table against every saved USDA description."""

from __future__ import annotations

import pytest

from roli_nutrition.recipe.preparation import compatibility, is_flesh_food, record_state

from captured_expectations import CHINOOK, PINK, RECIPE_RECORDS


@pytest.mark.parametrize("description, expected", [
    ("Fish, salmon, chinook, cooked, dry heat", "cooked"),
    ("Fish, salmon, pink, cooked, dry heat", "cooked"),
    ("Fish, tuna, fresh, bluefin, raw", "raw"),
    ("Lettuce, green leaf, raw", "raw"),
    ("Tomatoes, red, ripe, raw, year round average", "raw"),
    ("Seeds, sesame seeds, whole, roasted and toasted", "cooked"),
    ("Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)", "cooked"),
    ("Cheese, romano", "unknown"),
    ("Oil, olive, salad or cooking", "unknown"),            # 'cooking' is not the whole word 'cooked'
    ("Bread, french or vienna (includes sourdough)", "unknown"),
    ("Broccoli, raw", "raw"),
    ("Fish, salmon, Atlantic, farm raised, raw", "raw"),
    ("Beef, ground, 85% lean, raw and cooked", "unknown"),   # both words: no guess
    ("Rawlings brand snack", "unknown"),                      # 'Rawlings' is not the word 'raw'
    ("Pork, cured, bacon, unprepared", "raw"),                # USDA's word for bacon as sold (Phase 3 regression: was unknown)
    ("Canadian bacon, unprepared", "raw"),
    ("Pork, cured, ham, boneless, extra lean and regular, unheated", "raw"),
    ("Pork, cured, bacon, cooked, baked", "cooked"),
    ("Pork, cured, bacon, cooked, restaurant", "cooked"),
])
def test_t22_record_state(description, expected):
    assert record_state(description) == expected


def test_t22_every_saved_fixture_description_is_classified():
    from conftest import load
    names = {CHINOOK["file"]: CHINOOK["description"], PINK["file"]: PINK["description"]}
    names.update({file: desc for file, desc, _, _ in RECIPE_RECORDS.values()})
    for file, description in names.items():
        assert load(file)["description"] == description
        assert record_state(description) in ("raw", "cooked", "unknown")


@pytest.mark.parametrize("description, flesh", [
    ("Fish, salmon, chinook, cooked, dry heat", True),
    ("Beef, tenderloin, raw", True),
    ("Egg, whole, raw, fresh", True),
    ("Crustaceans, shrimp, raw", True),
    ("Cheese, romano", False),
    ("Oil, olive, salad or cooking", False),
    ("Seeds, sesame seeds, whole, roasted and toasted", False),
    ("Fishcake mix", False),                                 # first comma token must equal the word
])
def test_t22_flesh_detection(description, flesh):
    assert is_flesh_food(description) is flesh


@pytest.mark.parametrize("ingredient_state, description, expected", [
    ("cooked", "Fish, salmon, chinook, cooked, dry heat", ("compatible", None)),
    ("raw", "Fish, salmon, chinook, cooked, dry heat", ("mismatch", "preparation_mismatch")),
    ("raw", "Fish, tuna, fresh, bluefin, raw", ("compatible", None)),
    ("cooked", "Fish, tuna, fresh, bluefin, raw", ("mismatch", "preparation_mismatch")),
    ("as_used", "Oil, olive, salad or cooking", ("compatible", None)),
    ("raw", "Pork, cured, bacon, unprepared", ("compatible", None)),           # a recipe's "2 ounces bacon" on the unprepared record
    ("cooked", "Pork, cured, bacon, unprepared", ("mismatch", "preparation_mismatch")),
    ("as_used", "Cheese, romano", ("compatible", None)),
    ("as_used", "Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)", ("compatible", None)),
    ("as_used", "Fish, tuna, fresh, bluefin, raw", ("unresolved", "as_used_not_accepted_for_flesh")),
    ("as_used", "Beef, ground, cooked", ("unresolved", "as_used_not_accepted_for_flesh")),
    ("raw", "Cheese, romano", ("unresolved", "preparation_unresolved")),
    ("unknown", "Fish, tuna, fresh, bluefin, raw", ("unresolved", "preparation_unresolved")),
    ("unknown", "Cheese, romano", ("unresolved", "preparation_unresolved")),
])
def test_t22_compatibility_table(ingredient_state, description, expected):
    assert compatibility(ingredient_state, description) == expected
