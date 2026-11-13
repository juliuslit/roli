"""Checkpoint 3E (SPEC_3_mvp.md 12.9): the tag prompt and test set, saved grades and tags, the two-figure minimum, like-with-like comparison, top contributors, one fat per
plate with the chips following it, USDA's moisture change, the two sourced rows, and no replacement recipes after a USDA error. No network."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import httpx
from langchain_core.messages import AIMessage

from roli_nutrition.inputs import extract_inputs

from roli_agent.llm import parse_json_object
from roli_agent.mvp.reference import reference_check, top_contributors
from roli_agent.prompts import LINE_TAGS_PROMPT
from roli_agent.recipes.adapt import WeightsTable
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.judgements import JudgementCache, item_key
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import DishInterval, MenuItem, Relevance, ScenarioInterval
from roli_agent.recipes.pipeline import estimate_dish
from roli_agent.recipes.portions import PortionRules
from roli_agent.recipes.relevance import GRADE_PROMPT_VERSION, grade_batch
from roli_agent.recipes.survey import estimate_survey_dish
from roli_agent.recipes.tags import TAG_PROMPT_VERSION, method_sentences, tag_lines
from roli_agent.scripts.compare_mvp_runs import judged, why_changed
from roli_agent.scripts.eval_line_tags import SET, score, source_recipe

from conftest import load
from recipe_test_helpers import FakeSource, RuleLLM, recipe_page
from test_3d_tags_cards import QUERIES, TAGS, TaggingLLM, usda
from test_mvp_local import SurveyFakeService
from test_recipes_fetch_search import Site

D = Decimal
RULES, WEIGHTS = PortionRules.load(), WeightsTable.load()
FC = MenuItem(name="FISH & CHIPS", description="", section="MAINS")


def fish_and_chips(item=FC):
    return estimate_survey_dish(item, "fish_and_chips", service=SurveyFakeService(rebuild=True), rules=RULES, weights=WEIGHTS, slug="fc")


# -- 12.9.2-4: the tag prompt and the test set ------------------------------------------------------------------------------------------


def test_the_prompt_says_what_a_medium_is_and_when_in_doubt_eaten_and_asks_for_short_answers():
    for words in ("frying oil", "a marinade", "a brine", "a poaching or boiling liquid", "confit fat", "blister, saute, sear, stir-fry", 'When in doubt the line is "eaten"',
                  'ONLY for a line tagged cooking_medium, removed or prepared_product'):
        assert words in LINE_TAGS_PROMPT


def test_the_method_sentences_reach_the_model_and_a_tag_answer_needs_no_reason():
    r = source_recipe(1, {"title": "Peppers", "method": "Wash the peppers. Heat the oil in a skillet. Blister the peppers.", "lines": [{"line": "2 tbsp olive oil"}]})
    assert method_sentences(r.instructions_text) == ["Heat the oil in a skillet.", "Blister the peppers."]
    llm = TaggingLLM({})
    tags = tag_lines(MenuItem(name="PADRON PEPPERS"), [r], llm, parse_json_object)
    assert "   method: Heat the oil in a skillet. Blister the peppers.\n" in llm.prompts[0] and tags.available

    class NoReason:
        def invoke(self, messages):
            return AIMessage(content=json.dumps({"recipes": [{"index": 1, "lines": [{"n": 1, "role": "eaten", "kind": "plain_food"}]}]}))
    t = tag_lines(MenuItem(name="PADRON PEPPERS"), [r], NoReason(), parse_json_object).get(r.canonical_url, 1)
    assert (t.role, t.kind, t.reason) == ("eaten", "plain_food", "")


def test_the_test_set_has_every_case_of_the_spec_and_unclear_lines_carry_a_question_not_a_tag():
    doc = json.loads(Path(SET).read_text(encoding="utf-8"))
    lines = [l for r in doc["recipes"] for l in r["lines"]]
    assert all(("role" in l) != ("unclear" in l) for l in lines) and all("rule" in l for l in lines if "role" in l)
    rules = " ".join(l.get("rule", "") for l in lines)
    for case in ("oil used to blister", "searing oil", "pasta water", "water in a soup", "bay leaf", "herb sprigs", "dressing oil", "drizzle oil", "oil on a grill grate", "olive oil of a marinade", "confit fat", "brine"):
        assert case in rules, case
    assert sum("unclear" in l for l in lines) == 0                                             # 12.10.3: Julius decided all 12


def test_the_scorer_counts_harmful_misses_apart_and_never_scores_an_unclear_line():
    doc = {"recipes": [{"dish": "PEPPERS", "title": "Peppers", "method": "", "lines": [
        {"line": "3 tablespoons olive oil", "role": "eaten", "kind": "plain_food", "rule": "12.9.2"}, {"line": "1 cup canola oil, for deep frying", "role": "cooking_medium", "kind": "plain_food", "rule": "12.9.2"},
        {"line": "1 bay leaf", "role": "removed", "kind": "plain_food", "rule": "x"}, {"line": "Cooking spray", "unclear": "?"}]}]}
    llm = TaggingLLM({"olive oil": ("cooking_medium", "plain_food"), "canola": ("eaten", "plain_food"), "bay": ("removed", "plain_food")})
    r = score(doc, llm)
    assert r["scored"] == 3 and r["role_correct"] == 1 and [m["line"] for m in r["harmful_misses"]] == ["3 tablespoons olive oil"] and len(r["role_misses"]) == 2 and [u["line"] for u in r["unclear"]] == ["Cooking spray"]


# -- 12.9.5: saved grades and tags -------------------------------------------------------------------------------------------------------


def recipes():
    return [source_recipe(i, {"title": t, "method": "", "lines": [{"line": "100 g tomatoes"}, {"line": "2 tbsp olive oil"}]}) for i, t in enumerate(("Tuna Crudo", "Tuna Tartare"))]


ITEM = MenuItem(name="BLUEFIN CRUDO", description="chive", section="TO START")


def test_a_saved_grade_is_reused_and_only_the_new_page_goes_to_the_model(tmp_path):
    cache = JudgementCache(tmp_path, "m1")
    rs = recipes()
    first = RuleLLM()
    rels = [Relevance(), Relevance()]
    assert grade_batch(ITEM, rs[:1], rels[:1], first, parse_json_object, cache=cache)["from_saved"] == 0 and rels[0].grade == "high"
    second = RuleLLM(grades={"Tuna Crudo": ("different", "different", "different")})           # another day the model would answer otherwise
    rels2 = [Relevance(), Relevance()]
    log = grade_batch(ITEM, rs, rels2, second, parse_json_object, cache=cache)
    assert log["from_saved"] == 1 and log["graded"] == 2 and rels2[0].grade == "high" and rels2[0].dish_type == "same"
    assert len(second.prompts) == 1 and "Tuna Crudo" not in second.prompts[0] and "Tuna Tartare" in second.prompts[0]
    third = RuleLLM()
    assert grade_batch(ITEM, rs, [Relevance(), Relevance()], third, parse_json_object, cache=cache) == {"called": False, "graded": 2, "of": 2, "from_saved": 2} and third.prompts == []


def test_the_key_is_the_page_the_menu_item_the_prompt_and_the_model_and_failures_save_nothing(tmp_path):
    cache = JudgementCache(tmp_path, "m1")
    r = recipes()[0]
    cache.put("grades", ITEM, r, "v1", {"x": 1})
    assert cache.get("grades", ITEM, r, "v1") == {"x": 1}
    assert cache.get("grades", ITEM, r, "v2") is None                                             # another prompt version
    assert JudgementCache(tmp_path, "m2").get("grades", ITEM, r, "v1") is None                     # another model
    assert cache.get("grades", MenuItem(name="OTHER DISH"), r, "v1") is None                       # another menu item
    assert cache.get("grades", ITEM, r.model_copy(update={"content_hash": "changed"}), "v1") is None     # the page changed
    assert cache.get("grades", MenuItem(name="bluefin crudo*", description="Chive", section="To start"), r, "v1") == {"x": 1}   # footnote marks and case do not matter
    assert item_key(MenuItem(name="Zuni Caesar salad‡")) == item_key(MenuItem(name="Zuni Caesar salad*"))
    expired = JudgementCache(tmp_path, "m1", clock=lambda: 9e12)
    assert expired.get("grades", ITEM, r, "v1") is None
    cache2 = JudgementCache(tmp_path / "b", "m1")

    class Broken:
        def invoke(self, messages):
            return AIMessage(content="not json")
    assert grade_batch(ITEM, [r], [Relevance()], Broken(), parse_json_object, cache=cache2)["error"].startswith("invalid_reply") and not (tmp_path / "b").exists()
    assert not tag_lines(ITEM, [r], Broken(), parse_json_object, cache=cache2).available and not (tmp_path / "b").exists()
    assert len(GRADE_PROMPT_VERSION) == 12 and len(TAG_PROMPT_VERSION) == 12


def test_saved_tags_are_reused_but_validated_again_on_every_load(tmp_path):
    cache = JudgementCache(tmp_path, "m1")
    r = source_recipe(1, {"title": "Olives", "method": "", "lines": [{"line": "1 cup olive oil"}, {"line": "300 g cod fillets"}]})
    llm = TaggingLLM({"olive oil": ("cooking_medium", "plain_food"), "cod": ("cooking_medium", "plain_food")})
    first = tag_lines(ITEM, [r], llm, parse_json_object, cache=cache)
    assert llm.tag_calls == 1 and first.log["from_saved"] == 0 and first.get(r.canonical_url, 2).role == "eaten"     # a fish is no medium, whatever the model said
    again = TaggingLLM({})
    second = tag_lines(ITEM, [r], again, parse_json_object, cache=cache)
    assert again.tag_calls == 0 and second.log == {"called": False, "recipes": 1, "from_saved": 1, "tagged": 2, "missing": 0, "overridden": 1}
    assert second.get(r.canonical_url, 1).role == "cooking_medium" and second.get(r.canonical_url, 2).role == "eaten" and second.get(r.canonical_url, 2).raw_role == "cooking_medium"


def run_like(url="https://a.test/p", dish_type="same", grade="high", calculated=True):
    return {"status": "evaluated", "estimate": {"scenarios": [{"scenario_id": url, "status": "calculated" if calculated else "not_processed", "source": {"canonical_url": url},
                                                              "relevance": {"grade": grade, "dish_type": dish_type, "preparation": "same", "course_portion": "same", "hard_exclusion": None}}], "adapted_pairs": []}}


def test_compare_tells_grading_changes_from_search_results():
    before, after = run_like(), run_like(dish_type="variant", grade="medium", calculated=False)
    assert judged(before)["https://a.test/p"][:2] == ("high", "same")
    text = why_changed(before, after)
    assert "grading changed on 1 page(s), e.g. a.test: same/high -> variant/medium" in text and "search results" not in text
    other = run_like(url="https://b.test/q")
    assert "search results or cache" in why_changed(before, other) and "grading changed" not in why_changed(before, other)


def test_compare_names_what_differed_when_the_grade_itself_did_not():
    before, after = run_like(), run_like(calculated=False)
    after["estimate"]["scenarios"][0]["relevance"]["preparation"] = "different"
    assert "same/high -> same/high (preparation same -> different)" in why_changed(before, after)


def test_compare_reports_a_flag_that_opened_or_closed_as_a_reference_check_change():
    before, after = {**run_like(), "status": "flagged"}, run_like()
    assert why_changed(before, after) == "reference check: flagged -> evaluated"


# -- 12.9.6-7: two figures minimum, like with like --------------------------------------------------------------------------------------


def interval(low, high):
    s = ScenarioInterval(scenario_id="usda-survey:x", nutrient="saturated_fat_g", tier="survey_dish_record", low=D(low), high=D(high), served_mass_low=D(400), served_mass_high=D(600))
    return DishInterval(dish="d", nutrient="saturated_fat_g", low=D(low), high=D(high), bounded=True, n_scenarios=1, n_bounded=1, scenarios=[s])


def ranges(veg, drip):
    return {"vegetable oil": {"saturated_fat_g": {"low": veg[0], "high": veg[1]}}, "beef dripping": {"saturated_fat_g": {"low": drip[0], "high": drip[1]}}}


def find(check, choice):
    return next(c for c in check.comparisons if c.basis == "per_plate" and c.choice == choice)


def test_one_chain_is_one_figure_however_many_dishes_and_one_owner_is_one_figure_however_many_brands():
    card = next(r for r in RULES.rows if r.id == "PR15")
    check = reference_check(interval("6", "20"), card, factor=D("1.5"), choice_ranges=ranges(("5", "8"), ("15", "25")))
    veg, drip, plain = find(check, "vegetable oil"), find(check, "beef dripping"), find(check, "")
    assert veg.independent_figures == 2 and len(veg.figures) == 4 and (veg.published_low, veg.published_high) == (D(2), D("5.2")) and veg.checked      # three Wetherspoon dishes + Beefeater
    assert drip.independent_figures == 1 and not drip.checked and "1 independent figure" in drip.note and drip.published_high == D("35.6")             # Chef & Brewer alone: shown, never flags
    assert plain.independent_figures >= 3 and len(plain.figures) >= 5 and plain.checked                     # 12.16.7: MenuStat's aggregate rows add chains to the count                                                                # Sizzling x2 and Yates + Slug & Lettuce count once each
    only = next(r for r in RULES.rows if r.id == "PR13")
    plate = next(c for c in reference_check(interval("6", "20"), only, factor=D("1.5")).comparisons if c.basis == "per_plate")
    assert not plate.checked and not plate.failed and plate.roli_middle == D("13.000")                                                                  # far above 1.4 g, and it still does not flag


def test_a_labelled_figure_meets_the_range_of_its_own_fat_and_an_unlabelled_one_the_whole_range():
    card = next(r for r in RULES.rows if r.id == "PR15")
    check = reference_check(interval("6", "30"), card, factor=D("1.5"), choice_ranges=ranges(("6", "11"), ("18", "30")))
    veg, plain = find(check, "vegetable oil"), find(check, "")
    assert veg.roli_middle == D("8.500") and veg.allowed_high == D("7.8") and veg.failed and veg.direction == "above"          # 8.5 on the vegetable-oil range, against 2-5.2 x 1.5
    assert plain.roli_middle == D("18.000") and not plain.failed and check.flagged                                              # the whole range's middle is inside 10.2-22.8 x 1.5
    assert any("saturated share 11%" in b for b in veg.choice_basis)
    fig = {f.id: f for f in card.figures}
    v, a = D("0.20"), D("0.35")
    assert fig["F30"].choice(v, a)[0] == "vegetable oil" and fig["F38"].choice(v, a)[0] == "beef dripping" and fig["F36"].choice(v, a) == ("", "")
    assert fig["F36"].choice(D("0.30"), a)[0] == "vegetable oil"                                                                # the limits are settings
    no_range = reference_check(interval("6", "30"), card, factor=D("1.5"))
    assert not find(no_range, "vegetable oil").checked and "no range for vegetable oil" in find(no_range, "vegetable oil").note


def test_top_contributors_are_the_largest_shares_of_the_middle():
    est = fish_and_chips()
    top = top_contributors(est.interval("saturated_fat_g").model_dump(mode="json") | {"scenarios": [est.interval("saturated_fat_g").model_dump(mode="json")]}, None, est.model_dump(mode="json"))
    assert len(top) == 3 and "frying fat" in top[0]["line"] and "CHIPS" in top[0]["line"] and D(top[0]["share_of_middle"]) > D("0.3")
    assert D(top[0]["sat_fat_g"]) >= D(top[1]["sat_fat_g"]) >= D(top[2]["sat_fat_g"])


# -- USDA's moisture change; 12.9.8: one fat per plate ------------------------------------------------------------------------------------


def test_usda_input_weights_are_before_cooking_and_the_stated_moisture_change_reproduces_the_record():
    """The 3D rebuild read input weights as grams per 100 g of the finished food and understated fried fish by about 15 %. With USDA's stated moisture change the record's own inputs give the record's own values."""
    svc = SurveyFakeService(rebuild=True)
    fish, chips = extract_inputs(2706227, load("food_survey_2706227")), extract_inputs(2709458, load("food_survey_2709458"))
    assert fish.moisture_change_pct == -15 and chips.moisture_change_pct == 0 and abs(fish.grams_per_100g_scale - 100 / (100.6 * 0.85)) < 1e-9 and abs(chips.grams_per_100g_scale - 100 / 115.4) < 1e-9
    for result, sat, chol in ((fish, D("2.83"), D(46)), (chips, D("1.76"), D(0))):
        s = c = D(0)
        for i in result.inputs:
            found = svc.search_foods(i.description, 10) if i.description.lower() in svc.default_searches else svc.search_foods(i.description, 10, data_types=["Survey (FNDDS)"])
            rec = next(x for x in found.candidates if x.description.lower() == i.description.lower())
            n = svc.get_nutrition(rec.fdc_id)
            g = D(str(i.grams_per_100g)) * D(str(result.grams_per_100g_scale))
            s += g * D(str(n.saturated_fat_g)) / 100
            c += g * D(str(n.cholesterol_mg)) / 100
        assert abs(s - sat) < D("0.03") and abs(c - chol) < D("0.6"), (result.description, s, c)


def test_one_fat_per_plate_and_the_chips_follow_it():
    est = fish_and_chips()
    assert est.applicable, est.reason
    fish, chips = est.components
    assert fish.rebuilt and chips.rebuilt and chips.description == "Potato, french fries, from fresh, fried" and "named by card PR15" in chips.choice and chips.rule_id == "PR12"
    assert chips.rebuilt["groups"]["oil"]["replaces"] == ["Vegetable oil, NFS"] and D(chips.rebuilt["groups"]["oil"]["grams_per_100g"]) == D("13.00") and D(fish.rebuilt["groups"]["oil"]["grams_per_100g"]) == D("11.69")
    high = {i["ingredient_id"]: i for i in est.calculations["high"]["ingredients"]}
    low = {i["ingredient_id"]: i for i in est.calculations["low"]["ingredients"]}
    assert high["svy_01_oil"]["usda"]["fdc_id"] == high["svy_02_oil"]["usda"]["fdc_id"] == 171400 and low["svy_01_oil"]["usda"]["fdc_id"] == low["svy_02_oil"]["usda"]["fdc_id"] == 2710180
    assert sorted(est.choice_ranges) == ["beef dripping", "vegetable oil"] and "one fat per plate" in est.fat_note and "cannot follow" not in est.fat_note
    veg, drip = est.choice_ranges["vegetable oil"]["saturated_fat_g"], est.choice_ranges["beef dripping"]["saturated_fat_g"]
    sat = est.totals["saturated_fat_g"]
    assert veg["low"] == sat["low"] and drip["high"] == sat["high"] and D(veg["high"]) < D(drip["low"]) * 2 and D(veg["low"]) < D(veg["high"]) < D(drip["high"])
    # the plate at vegetable oil reproduces USDA's own chips value: 200 g at 1.76 g per 100 g
    chips_low = sum(D(str(i["contribution"]["saturated_fat_g"])) for k, i in low.items() if k.startswith("svy_02"))
    pr12 = next(r for r in PortionRules.load().rows if r.id == "PR12")
    assert abs(chips_low - pr12.low * D("1.76") / 100) < D("0.05")


def test_a_named_fat_is_the_only_fat_and_a_named_species_the_only_species():
    est = fish_and_chips(MenuItem(name="Cod & chips", description="fried in beef dripping", section="MAINS"))
    assert list(est.choice_ranges) == ["beef dripping"]
    g = est.components[0].rebuilt["groups"]
    assert g["fish"]["named_on_menu"] == ["Fish, cod, Atlantic, raw"] and g["oil"]["named_on_menu"] == ["Fat, beef tallow"] and len(g["fish"]["options"]) == 1 and len(g["oil"]["options"]) == 1
    assert est.totals["saturated_fat_g"]["low"] == est.choice_ranges["beef dripping"]["saturated_fat_g"]["low"]


def test_chips_without_a_rebuild_keep_a_record_and_the_diagnostics_say_they_cannot_follow_the_fat():
    svc = SurveyFakeService(rebuild=True)
    svc.bodies.pop(2709458)                                                                     # no fried-from-fresh record: the restaurant fries record stays
    est = estimate_survey_dish(FC, "fish_and_chips", service=svc, rules=RULES, weights=WEIGHTS, slug="fc")
    fish, chips = est.components
    assert fish.rebuilt and chips.rebuilt is None and chips.description == "Potato, french fries, restaurant" and "cannot follow the fat choice" in est.fat_note and "CHIPS" in est.fat_note


def test_a_dish_with_no_card_keeps_the_restaurant_fries_record():
    est = estimate_survey_dish(MenuItem(name="Shoestring potatoes", section="STARTERS"), "vegetable_starter", service=SurveyFakeService(rebuild=True), rules=RULES, weights=WEIGHTS)
    assert est.components[0].description == "Potato, french fries, restaurant" and est.components[0].rebuilt is None and est.choice_ranges == {}


# -- 12.9.10: the two sourced rows ---------------------------------------------------------------------------------------------------------


def test_tartare_sauce_has_its_own_row_and_mayonnaise_stays_on_w40():
    row = WEIGHTS.find("Tartar sauce", "fish_and_chips")
    assert row.id == "W56" and row.fdc_id == 171826 and (row.low, row.high) == (D(15), D(28)) and row.sourced and "Duerr" in row.notes and "Colman" in row.measures
    assert WEIGHTS.find("garlic mayo", "fish_main").id == "W40" and WEIGHTS.find("Celeriac & Cranberry Remoulade", "vegetable_starter").id == "W40" and WEIGHTS.find("salmon tartare", "fish_main") is None
    assert WEIGHTS.find("cream of tartar", "fish_main") is None                                # 12.10.8: W27 excludes it
    assert WEIGHTS.find("heavy cream", "fish_main").id == "W27"


# -- 12.5.2, owed since 12.7: no replacement recipes after a USDA error --------------------------------------------------------------------


LINES = ["300 g green olives", "2 tablespoons olive oil", "red onion, sliced"]


def backfill_estimate(service, *, pages=6, llm=None):
    site = {f"https://a.test/{i}": recipe_page(f"Olives {i}", LINES, steps="Toss. Serve.") .replace("300 g", f"{300 + i} g") for i in range(pages)}
    hits = {"open": [{"url": u, "title": ""} for u in site], "structured_hosts": []}
    return estimate_dish(MenuItem(name="MARINATED OLIVES", section="BAR SNACKS"), source=FakeSource(hits), fetcher=PoliteFetcher(transport=httpx.MockTransport(Site(pages=site)), sleep=lambda s: None), service=service,
                         llm=llm or TaggingLLM({}), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental", portion_rules=PortionRules.load(),
                         exclude_herbs_spices=True, backfill_recipes=True, max_scenarios=4)


class Halted:
    """A nutrition service that reports USDA's refusal."""

    def __init__(self, inner, halted):
        self._inner, self._halted = inner, halted

    def usda_status(self):
        return {"halted": self._halted}

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_recipes_that_cannot_be_portioned_are_replaced_when_usda_is_fine_and_never_after_a_refusal():
    """The onion's count has no USDA weight here, so no recipe can be portioned: the condition that fetched more recipes on the Greyhound's schnitzel."""
    QUERIES.setdefault("red onion, sliced", QUERIES["red onion"])
    service, _ = usda()
    ok = backfill_estimate(Halted(service, False))
    assert any(n.startswith("backfill:") and "trying" in n for n in ok.notes), ok.notes
    assert sum(1 for s in ok.scenarios if s.status == "calculated") > 4
    service2, _ = usda()
    refused = backfill_estimate(Halted(service2, True))
    assert any("backfill skipped" in n for n in refused.notes) and not any(n.startswith("backfill:") and "trying" in n for n in refused.notes)
    assert sum(1 for s in refused.scenarios if s.status == "calculated") == 4
