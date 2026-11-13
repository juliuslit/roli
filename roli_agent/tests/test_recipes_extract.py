"""2B-1 extraction: JSON-LD by hand and via recipe-scrapers, nutrition blocks ignored, verified LLM fallback."""

from __future__ import annotations

import json

from roli_agent.llm import parse_json_object
from roli_agent.recipes.extract import extract_from_json_ld, extract_recipe, extract_with_llm, find_json_ld_recipe, visible_text

from conftest import FakeLLM

# Synthetic page with our own text (no real recipe copied), including a nutrition block that must be ignored.
RECIPE_LD = {
    "@context": "https://schema.org", "@type": "Recipe", "name": "Test Tuna Crudo",
    "recipeIngredient": ["85 g sushi-grade tuna, thinly sliced", "1 tbsp olive oil", "Flaky salt, to taste"],
    "recipeYield": ["2", "2 servings"],
    "recipeInstructions": [{"@type": "HowToStep", "text": "Slice the raw tuna."}, {"@type": "HowToStep", "text": "Dress with oil and salt."}],
    "nutrition": {"@type": "NutritionInformation", "calories": "999 kcal", "saturatedFatContent": "77 g", "cholesterolContent": "555 mg"},
}
PAGE = f"<html><head><script type='application/ld+json'>{json.dumps({'@graph': [{'@type': 'WebPage'}, RECIPE_LD]})}</script></head><body><h1>Test Tuna Crudo</h1></body></html>"


def test_json_ld_recipe_found_inside_graph_and_nutrition_removed():
    recipe = find_json_ld_recipe(PAGE)
    assert recipe["name"] == "Test Tuna Crudo"
    assert "nutrition" not in recipe
    ex = extract_from_json_ld(PAGE)
    assert ex.method == "json_ld"
    assert ex.ingredient_lines == ["85 g sushi-grade tuna, thinly sliced", "1 tbsp olive oil", "Flaky salt, to taste"]
    assert ex.yield_text == "2 / 2 servings"
    assert ex.instructions_text == "Slice the raw tuna. Dress with oil and salt."


def test_page_nutrition_values_never_appear_anywhere_in_the_extraction():
    ex = extract_recipe(PAGE, "https://example.test/recipe")
    blob = json.dumps(ex.__dict__)
    for forbidden in ("999", "77 g", "555", "calories", "saturatedFat", "cholesterolContent"):
        assert forbidden not in blob


def test_extract_recipe_prefers_structured_data_and_needs_no_llm():
    ex = extract_recipe(PAGE, "https://example.test/recipe")       # recipe-scrapers wild mode or our JSON-LD parser
    assert ex.method in ("recipe_scrapers", "json_ld")
    assert len(ex.ingredient_lines) == 3


def test_no_structured_data_and_no_llm_gives_none():
    ex = extract_recipe("<html><body><p>Just a blog post about dinner.</p></body></html>", "https://example.test/post")
    assert ex.method == "none" and ex.ingredient_lines == []


def test_llm_fallback_keeps_only_verbatim_lines():
    html = "<html><body><h2>Ingredients</h2><ul><li>2 cups cherry tomatoes, halved</li><li>1 tbsp olive oil</li></ul><p>Serves 2</p></body></html>"
    llm = FakeLLM([json.dumps({"ingredient_lines": ["2 cups cherry tomatoes, halved", "1 tbsp olive oil", "100 g bottarga (invented)"],
                               "yield_text": "Serves 2", "instructions_text": "Toss and serve."})])
    ex = extract_with_llm(html, llm, parse_json_object)
    assert ex.method == "llm_text"
    assert ex.ingredient_lines == ["2 cups cherry tomatoes, halved", "1 tbsp olive oil"]       # the invented line is dropped
    assert "extraction_unverifiable:1_lines_dropped" in ex.flags
    assert ex.yield_text == "Serves 2"


def test_llm_fallback_drops_unverifiable_yield_and_handles_garbage():
    html = "<html><body><li>1 tbsp olive oil</li></body></html>"
    llm = FakeLLM([json.dumps({"ingredient_lines": ["1 tbsp olive oil"], "yield_text": "Serves 8", "instructions_text": ""})])
    ex = extract_with_llm(html, llm, parse_json_object)
    assert ex.yield_text == "" and "yield_unverifiable_dropped" in ex.flags
    ex2 = extract_with_llm(html, FakeLLM(["Sure! Here is the recipe: ..."]), parse_json_object)
    assert ex2.method == "none" and ex2.ingredient_lines == []


def test_visible_text_strips_scripts_and_tags():
    assert visible_text("<html><script>var x=1;</script><p>Hello <b>world</b></p></html>") == "Hello world"


def test_extraction_cache_skips_the_llm_fallback_for_an_unchanged_page(tmp_path):
    from roli_agent.recipes.extract import ExtractionCache
    from conftest import FakeLLM
    from roli_agent.llm import parse_json_object
    html = "<html><body><h1>Crudo</h1><p>Ingredients</p><p>85 g tuna</p><p>1 tbsp olive oil</p><p>Serves 2</p></body></html>"
    reply = json.dumps({"ingredient_lines": ["85 g tuna", "1 tbsp olive oil"], "yield_text": "Serves 2", "instructions_text": ""})
    cache = ExtractionCache(tmp_path / "x")
    llm = FakeLLM([reply])
    first = extract_recipe(html, "https://x.test/r", llm=llm, parse_json_object=parse_json_object, cache=cache)
    assert first.method == "llm_text" and first.ingredient_lines == ["85 g tuna", "1 tbsp olive oil"] and len(llm.prompts) == 1
    second = extract_recipe(html, "https://x.test/r", llm=FakeLLM([]), parse_json_object=parse_json_object, cache=cache)   # no reply scripted: must not be called
    assert second.ingredient_lines == first.ingredient_lines and "extraction_from_cache" in second.flags and cache.hits == 1
    changed = extract_recipe(html.replace("85 g", "90 g"), "https://x.test/r", llm=FakeLLM([reply.replace("85 g", "90 g")]), parse_json_object=parse_json_object, cache=cache)
    assert changed.ingredient_lines == ["90 g tuna", "1 tbsp olive oil"] and "extraction_from_cache" not in changed.flags
