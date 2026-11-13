"""2B-2 relevance (spec 3.3, D10, D16): the free gate, menu coverage, the LLM rubric and Python's grade."""

from __future__ import annotations

from decimal import Decimal

import pytest

from roli_agent.llm import parse_json_object
from roli_agent.recipes.models import MenuItem, Relevance, SourceRecipe
from roli_agent.recipes.parse import parse_line
from roli_agent.recipes.relevance import combine, gate, grade_batch, menu_coverage

from recipe_test_helpers import RuleLLM

CRUDO = MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START")
GEM = MenuItem(name="LITTLE GEM LETTUCES", description="tahini vinaigrette, pecorino sardo, toasted sesame", section="TO START")
PIZZA = MenuItem(name="MARGHERITA", description="tomato, fior di latte, basil", section="PIZZA")


def recipe(title: str, lines: list[str], verbs=(), flags=(), servings="4 servings") -> SourceRecipe:
    return SourceRecipe(url=f"https://x.test/{title.lower().replace(' ', '-')}", canonical_url=f"https://x.test/{title.lower().replace(' ', '-')}", host="x.test",
                        title=title, found_by=["open"], fetched_at="t", extraction="json_ld", yield_text=servings, servings=Decimal(4) if servings else None,
                        ingredient_lines=lines, cooking_verbs=list(verbs), ingredients=[parse_line(l) for l in lines], content_hash="h", flags=list(flags))


@pytest.mark.parametrize("item, title, lines, flags, expected", [
    (CRUDO, "Tuna Crudo", ["85 g bluefin tuna", "1 tbsp olive oil"], (), None),
    (CRUDO, "Spaghetti with bottarga sauce", ["200 g spaghetti", "40 g bottarga"], (), "dish_word_absent"),
    (CRUDO, "Seared Tuna Steaks", ["2 tuna steaks", "1 tbsp oil"], (), "hard_exclusion:cooked_title_for_raw_dish:seared"),
    (CRUDO, "Yellowtail Carpaccio", ["200 g yellowtail", "lemon"], (), None),                    # a variant passes the gate; the rubric decides
    (CRUDO, "21 Tuna Recipes", ["Tuna salad", "Tuna melt", "Poke", "Tataki", "Crudo"], ("no_quantities_listicle_suspect",), "listicle_or_collection:no_quantities"),
    (CRUDO, "15 Best Crudo Ideas", ["1 lb tuna", "2 tbsp oil"], (), "listicle_or_collection:title"),
    (CRUDO, "Crudo", ["85 g tuna"], (), "too_few_ingredient_lines"),
    (GEM, "Little Gem Salad", ["2 heads little gem lettuce", "2 tbsp tahini"], (), None),
    (GEM, "Grilled Little Gem salad", ["2 heads little gem", "1 tbsp oil"], (), None),           # salads are not raw-dish types: no title exclusion
    (PIZZA, "Margarita Cocktail", ["2 oz tequila", "1 oz lime juice"], (), "dish_word_absent"),
    (PIZZA, "Pizza Margherita", ["500 g flour", "fior di latte"], (), None),
])
def test_gate(item, title, lines, flags, expected):
    passed, reason = gate(item, recipe(title, lines, flags=flags))
    if expected is None:
        assert passed and reason is None
    else:
        assert not passed and reason.startswith(expected)


def test_menu_coverage_uses_synonyms_and_names_what_is_missing():
    r = recipe("Little Gem Salad", ["2 heads little gem lettuce", "2 tbsp tahini", "1/4 cup grated pecorino romano", "1 tbsp olive oil"])
    cov, matched, missing = menu_coverage(GEM, r)
    assert cov == Decimal(2) / Decimal(3) and matched == ["tahini vinaigrette", "pecorino sardo"] and missing == ["toasted sesame"]
    crudo = recipe("Tuna Crudo", ["85 g bluefin tuna", "1 tbsp olive oil", "1 tbsp chives, chopped"])
    cov2, _, missing2 = menu_coverage(CRUDO, crudo)
    assert cov2 == Decimal(1) / Decimal(3) and missing2 == ["bottarga", "muscat grape"]        # bottarga never silently disappears
    assert menu_coverage(MenuItem(name="X"), crudo) == (None, [], [])


@pytest.mark.parametrize("d, p, c, grade, hard", [
    ("same", "same", "same", "high", None),
    ("same", "similar", "same", "high", None),
    ("same", "same", "different", "medium", None),
    ("variant", "same", "same", "high", None),
    ("variant", "similar", "different", "medium", None),
    ("different", "same", "same", "low", "hard_exclusion:dish_type_different"),
    ("same", "different", "same", "low", "hard_exclusion:preparation_different"),
])
def test_combine_is_pythons_decision(d, p, c, grade, hard):
    assert combine(d, p, c) == (grade, hard)


def test_grade_batch_fills_every_recipe_in_one_call_and_keeps_sentences_out_of_grades():
    recipes = [recipe("Tuna Crudo", ["85 g tuna", "oil"]), recipe("Seared Tuna", ["2 tuna steaks", "oil"]), recipe("Tuna Tartare", ["200 g tuna", "capers"])]
    rels = [Relevance() for _ in recipes]
    llm = RuleLLM(grades={"Seared Tuna": ("different", "different", "same"), "Tuna Tartare": ("variant", "similar", "different")})
    log = grade_batch(CRUDO, recipes, rels, llm, parse_json_object)
    assert log == {"called": True, "graded": 3, "of": 3, "from_saved": 0} and len(llm.prompts) == 1
    assert [r.grade for r in rels] == ["high", "low", "medium"]
    assert rels[1].hard_exclusion == "hard_exclusion:dish_type_different" and "test grade" in rels[1].rubric_reason


def test_unparsable_rubric_leaves_recipes_ungraded_never_guessed():
    recipes = [recipe("Tuna Crudo", ["85 g tuna", "oil"])]
    rels = [Relevance()]
    log = grade_batch(CRUDO, recipes, rels, RuleLLM(break_relevance=True), parse_json_object)
    assert log["error"].startswith("invalid_reply") and rels[0].grade == "ungraded" and rels[0].dish_type is None


def test_rubric_rejects_rows_with_values_outside_the_vocabulary():
    class Odd(RuleLLM):
        def invoke(self, messages):
            from langchain_core.messages import AIMessage
            return AIMessage(content='{"recipes": [{"index": 1, "dish_type": "identical", "preparation": "same", "course_portion": "same", "reason": "x"}]}')
    rels = [Relevance()]
    grade_batch(CRUDO, [recipe("Tuna Crudo", ["85 g tuna", "oil"])], rels, Odd(), parse_json_object)
    assert rels[0].grade == "ungraded"
