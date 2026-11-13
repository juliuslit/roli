"""Phase 2C.1: input completeness and relevance hardening, on the captured real USDA records.

A: deterministic parsing (typos, doubled units, "garlic cloves", embedded weights beside a measure, sub-recipe references, "plus" lines),
   portion choice (equal-weight ties, dimension-labelled sizes, fl oz and modifier-matched density sources, recorded options).
B: D24 completeness-aware same-food reselection, off by default, applied only within the stated saturated-fat tolerance.
C: method text that cooks the main ingredient of a raw dish is a hard exclusion; a cooked garnish is not.
E: filled + unfilled lines add up to the blocked lines.
"""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest

from roli_nutrition.portions import extract_portions

from roli_agent.llm import parse_json_object
from roli_agent.recipes.adapt import WeightsTable, WeightRow
from roli_agent.recipes.completeness import CompleteRecordPolicy
from roli_agent.recipes.convert import apply_embedded_weight, convert_weight, convert_with_portions, is_sized_label
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import MenuItem, SourceRecipe
from roli_agent.recipes.parse import parse_line, parse_lines
from roli_agent.recipes.pipeline import estimate_dish
from roli_agent.recipes.relevance import _recipe_block, cooked_main_ingredient, gate, raw_family

from conftest import load
from recipe_test_helpers import BLUEFIN, BREAD, OLIVE, TOMATO, FakeSource, RuleLLM, QUERIES, make_usda, recipe_page
from test_recipes_fetch_search import Site

D = Decimal
GARLIC, LEMON, HONEY, SWEET_WINE, OREGANO, WHITE_BREAD, EGG, BROWN_SUGAR, ONION, RED_ONION, THYME, MISO, SUGAR, EVOO = (
    169230, 167746, 169640, 173176, 171328, 174924, 173424, 168833, 170000, 790577, 173470, 172442, 169655, 748608)


def portions(fid: int):
    return extract_portions(fid, load(f"food_{fid}")).portions


def line(text: str):
    return apply_embedded_weight(convert_weight(parse_line(text)))


def convert(text: str, fid: int, proxy: bool = False):
    return convert_with_portions(line(text), portions(fid), fid, proxy=proxy)


# -- A. parsing -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text, quantity, unit, name, flags", [
    ("1-2 tabelspoons capers (drained)", D("1.5"), "tbsp", "capers", {"unit_typo_corrected", "range_midpoint"}),
    ("1-2 tabespoons olive oil", D("1.5"), "tbsp", "olive oil", {"unit_typo_corrected"}),
    ("2 tsp tsp pepper", D(2), "tsp", "pepper", {"unit_repeated"}),
    ("2 garlic cloves, peeled", D(2), "clove", "garlic", {"unit_from_name"}),
    ("1 small garlic clove, grated", D(1), "clove", "garlic", {"unit_from_name"}),
    ("3 to 4 sprigs fresh thyme, chopped", D("3.5"), "sprig", "fresh thyme", set()),
    ("4 heads little gem lettuce", D(4), "head", "little gem lettuce", set()),
    ("3 hard-boiled eggs (grated or finely chopped)", D(3), "each", "hard-boiled eggs", set()),
])
def test_typos_doubled_units_and_count_words_in_the_name(text, quantity, unit, name, flags):
    p = parse_line(text)
    assert (p.quantity, p.unit, p.name) == (quantity, unit, name) and flags <= set(p.flags) and p.line == text


def test_size_word_before_a_count_word_becomes_a_note_the_portion_chooser_reads():
    p = parse_line("1 small garlic clove, grated")
    assert p.preparation_words[0] == "small" and p.unit == "clove"
    c = convert("1 small garlic clove, grated", GARLIC)
    assert c.grams == D(3) and "portion_size_word_unmatched" in c.flags           # the record has one clove weight; the size word is recorded as unmatched


def test_sub_recipe_reference_is_not_an_ingredient():
    p = parse_line("1 recipe fresh pizza dough, recipe follows")
    assert p.quantity is None and p.name == "fresh pizza dough" and {"sub_recipe_reference", "sub_recipe_components_on_page"} <= set(p.flags)
    q = parse_line("1 recipe pizza dough (see link)")
    assert "sub_recipe_components_elsewhere" in q.flags and q.name == "pizza dough"
    assert "sub_recipe_reference" not in parse_line("1 cup pizza sauce").flags


def test_plus_compound_lines_split_only_when_the_tail_names_a_quantified_food():
    parts = parse_lines("Grated zest of 1 small lemon, plus 1 tablespoon lemon juice")
    assert [(p.quantity, p.unit, p.name) for p in parts] == [(None, None, "grated zest of 1 small lemon"), (D(1), "tbsp", "lemon juice")]
    assert all(p.line == "Grated zest of 1 small lemon, plus 1 tablespoon lemon juice" for p in parts)
    assert len(parse_lines("2 tablespoons extra-virgin olive oil, plus extra to grease pan")) == 1
    assert len(parse_lines("2 tablespoons butter, plus 1 tablespoon for the pan")) == 1          # "for the pan" is not a food


def test_a_cooking_word_inside_an_oil_name_is_the_product_not_a_step():
    assert parse_line("2 teaspoons toasted sesame oil").preparation_hint == "as_used"
    assert parse_line("1 cup toasted sesame seeds").preparation_hint == "cooked"               # seeds: the word still picks the roasted record
    assert parse_line("2 roasted red peppers").preparation_hint == "cooked"


def test_weight_stated_beside_a_volume_measure_is_the_lines_total():
    p = line("2 cups (232g) King Arthur '00' Pizza Flour, plus more for dusting")
    assert p.grams == D(232) and "embedded_weight_after_measure" in p.flags and "232g" in p.grams_reference
    q = line("3 tablespoons (38g) extra-virgin olive oil")
    assert q.grams == D(38)
    r = line("1 cup cherry tomatoes (about 6 oz)")                                              # the page's own figure, marked approximate
    assert r.grams == D(6) * D("28.349523125") and "embedded_weight_approximate" in r.flags
    s = line("1 cup walnuts, chopped (4 oz)")                                                   # a bare weight elsewhere on the line: still the page's weight
    assert s.grams == D(4) * D("28.349523125") and "embedded_weight_on_volume_line" in s.flags
    t = line("1 cup chicken stock (from a 14 oz can)")                                          # words around the weight: not the line's weight
    assert t.grams == D("236.5882365") and "density_assumed_1" in t.flags


# -- A. portion choice on the real records ----------------------------------------------------------------


@pytest.mark.parametrize("text, fid, grams, flag", [
    ("2 cloves garlic", GARLIC, D(6), "usda_portion"),                   # '1 clove' = 3 g and '3 cloves' = 9 g weigh the same per clove: no ambiguity
    ("2 garlic cloves, peeled", GARLIC, D(6), "usda_portion"),
    ("1/2 teaspoon fresh minced thyme", THYME, D("0.4"), "usda_portion"),   # '1 tsp' and '0.5 tsp' agree
    ("1/2 teaspoon honey", HONEY, D("0.5") * D("4.92892159375") * (D(339) / D("236.5882365")), "portion_derived_volume"),
    ("1 tsp white miso", MISO, D("4.92892159375") * (D(275) / D("236.5882365")), "portion_derived_volume"),
    ("1 tablespoon sugar", SUGAR, D("14.78676478125") * (D(200) / D("236.5882365")), "portion_derived_volume"),
    ("1-2 tabespoons olive oil", OLIVE, D("1.5") * D("13.5"), "usda_portion"),
    ("1/2 cup red onion (thinly sliced)", ONION, D("57.5"), "usda_portion"),
])
def test_lines_that_now_convert_from_the_records_own_labels(text, fid, grams, flag):
    p = convert(text, fid)
    assert p.grams == grams and flag in p.flags and p.grams_reference and str(fid) in p.grams_reference


def test_fluid_ounce_label_is_a_density_source_and_proxy_volume_stays_flagged():
    p = convert("2 tbsp mirin", SWEET_WINE, proxy=True)
    assert p.grams == D(2) * D("14.78676478125") * (D("29.5") / D("29.5735295625"))
    assert {"portion_derived_volume", "proxy_volume_portion"} <= set(p.flags) and "1 fl oz" in p.grams_reference


def test_dimension_labelled_sizes_take_the_median_and_record_their_options():
    """D20 revised (Julius, 2026-11-03): comparable whole-item sizes -> the median, flagged `assumed_size_median`, labels and range kept."""
    p = convert("1 lemon (zested)", LEMON)
    assert p.grams == D(71) and "assumed_size_median" in p.flags and "portion_size_unspecified" not in p.flags      # (58 + 84) / 2
    assert {o["label"] for o in p.portion_options} == {'1 fruit (2-3/8" dia)', '1 fruit (2-1/8" dia)'} and {o["grams"] for o in p.portion_options} == {"84", "58"}
    assert "ASSUMED size" in p.grams_reference and "range 58-84 g per item" in p.grams_reference and "wedge" not in p.grams_reference   # a wedge never enters
    assert is_sized_label('1 fruit (2-3/8" dia)') and is_sized_label("1 large") and not is_sized_label("1 clove") and not is_sized_label("1 fruit")
    q = convert("1 medium lemon", LEMON)                                              # the line's size word matches no label: the same median
    assert q.grams == D(71) and "assumed_size_median" in q.flags
    e = convert("3 hard-boiled eggs (grated or finely chopped)", EGG)                 # one sized label ('1 large' = 50 g): the record's only size, flagged single
    assert e.grams == D(150) and "assumed_size_median" in e.flags and "single_labelled_size" in e.flags and [o["label"] for o in e.portion_options] == ["1 large"]
    r = convert("1/4 red onion (thinly sliced)", ONION)
    assert r.grams is not None and "assumed_size_median" in r.flags and len(r.portion_options) == 3
    g = convert("2 cloves garlic", GARLIC)                                            # a stated, unambiguous measure is never flagged as assumed
    assert g.grams == D(6) and "assumed_size_median" not in g.flags


@pytest.mark.parametrize("text, fid, labels", [
    ("1 teaspoon dried oregano", OREGANO, {"1 tsp, leaves", "1 tsp, ground"}),
    ("2 c torn day old bread", WHITE_BREAD, {"1 cup, cubes", "1 cup, crumbs"}),
    ("½ teaspoon brown sugar", BROWN_SUGAR, {"1 tsp packed", "1 tsp unpacked", "1 tsp brownulated"}),
])
def test_ambiguous_measures_stay_unresolved_and_list_what_they_could_not_choose_between(text, fid, labels):
    p = convert(text, fid)
    assert p.grams is None and "portion_ambiguous" in p.flags and {o["label"] for o in p.portion_options} == labels
    assert all(D(o["grams"]) > 0 for o in p.portion_options)


# -- A/E. adaptation: G3 from dimension sizes, G5 from ambiguous labels, counts that add up -------------------


SALAD = MenuItem(name="GARLIC LEMON SALAD", description="", section="TO START")        # no printed ingredients: no menu-only lines
SALAD_PAGE = {"https://a.test/salad": recipe_page("Garlic Lemon Salad", ["2 garlic cloves, peeled", "1 lemon (zested)", "1 teaspoon dried oregano",
                                                                        "3 hard-boiled eggs (grated or finely chopped)", "2 tablespoons olive oil"])}
SALAD_RESULTS = {"open": [{"url": "https://a.test/salad", "title": "Salad"}], "structured_hosts": []}
SALAD_QUERIES = dict(QUERIES, **{"garlic": ("garlic raw", GARLIC, "direct"), "lemon": ("lemons raw", LEMON, "direct"),
                                 "dried oregano": ("spices oregano dried", OREGANO, "direct"), "hard-boiled eggs": ("egg whole boiled", EGG, "direct")})
SALAD_SEARCHES = {"garlic raw": [GARLIC], "lemons raw": [LEMON], "spices oregano dried": [OREGANO], "egg whole boiled": [EGG]}


def run(item, pages, results, *, queries=QUERIES, searches=None, grades=None, policy=None, **kwargs):
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, rec = make_usda(searches)
    if policy is not None:                                   # a D24 policy built on this run's service
        kwargs["complete_records"] = policy(service)
    llm = RuleLLM(grades=grades or {}, queries=queries)
    est = estimate_dish(item, source=FakeSource(results), fetcher=fetcher, service=service, llm=llm, parse_json_object=parse_json_object,
                        match_cache=MatchCache(None), prefetch_workers=1, **kwargs)
    return est, service, rec


def test_adapted_pair_bounds_sizes_and_ambiguous_labels_and_the_counts_reconcile():
    est, _, _ = run(SALAD, SALAD_PAGE, SALAD_RESULTS, queries=SALAD_QUERIES, searches=SALAD_SEARCHES, adapt_mode="approved", weights_table=WeightsTable([]))
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    by_name = {l.name: l for l in sc.ingredients}
    assert by_name["garlic"].conversion.grams == D(6) and by_name["garlic"].blocker is None
    # D20 revised: the lemon (71 g median) and the eggs (150 g, single size) are weighed in the published scenario as documented inferences
    assert by_name["lemon"].conversion.grams == D(71) and by_name["lemon"].conversion.method == "usda_portion_median" and by_name["lemon"].blocker is None
    assert sc.calculation_status == "incomplete" and sc.blockers == {"no_usda_portion": 1}
    assert sc.basis == "documented_inferences" and {i.name for i in sc.inferences} == {"lemon", "hard-boiled eggs"} and all(i.kind == "assumed_size_median" for i in sc.inferences)
    assert sc.completeness_basis == {"saturated_fat_g": "incomplete", "cholesterol_mg": "incomplete"} and not sc.eligible_for_range
    (pair,) = est.adapted_pairs
    a = {x.name: x for x in pair.assumptions}
    # the pair carries the labelled spread around the median, with the published median recorded
    assert (a["lemon"].gap, a["lemon"].source, a["lemon"].grams_low, a["lemon"].grams_high, a["lemon"].published_grams) == ("G3_size_unspecified", "record_size_labels", D(58), D(84), D(71))
    assert (a["dried oregano"].gap, a["dried oregano"].source, a["dried oregano"].grams_low, a["dried oregano"].grams_high) == ("G5_measure_ambiguous", "record_measure_labels", D(1), D("1.8"))
    assert "1 tsp, leaves" in a["dried oregano"].basis and "1 tsp, ground" in a["dried oregano"].basis
    assert (a["hard-boiled eggs"].gap, a["hard-boiled eggs"].grams_low, a["hard-boiled eggs"].grams_high, a["hard-boiled eggs"].note) == ("G3_size_unspecified", D(150), D(150), "single labelled size")
    assert pair.unfilled == [] and pair.low.calculation_status == "complete" and pair.high.calculation_status == "complete"
    summ = est.internal_summary
    assert summ.n_blocked_lines == 1 == summ.n_lines_filled + summ.n_unfilled and summ.n_unfilled_in_pairs == 0 and summ.n_unfilled_no_pair == 0
    assert summ.n_median_size_spreads == 2 and "of 1 blocked lines" in summ.statement
    # the published scenario is untouched and still says incomplete; the reply never changes
    assert sc.calculation["status"] == "incomplete" and all(x.grams_declared is None for x in pair.assumptions)


def test_unpaired_scenario_lines_are_counted_separately_so_the_denominator_adds_up():
    pages = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna", "2 tablespoons extra-virgin olive oil", "1 saku tuna block"])}
    results = {"open": [{"url": "https://a.test/crudo", "title": "Crudo"}], "structured_hosts": []}
    item = MenuItem(name="BLUEFIN CRUDO", description="bottarga", section="TO START")
    blocked_table = WeightsTable([WeightRow({"id": "W10", "ingredient_role": "bottarga", "ingredient_keys": "bottarga", "fdc_id": "", "usda_description": "",
                                             "low_g": "", "high_g": "", "basis": "blocked", "measures": "", "review_status": "blocked_questionable_proxy", "approved_by": "", "notes": ""})])
    est, _, _ = run(item, pages, results, adapt_mode="experimental", weights_table=blocked_table)
    summ = est.internal_summary
    assert est.adapted_pairs == [] and summ.n_pairs == 0
    assert summ.n_blocked_lines == 2 and summ.n_unfilled_no_pair == 2 and summ.n_unfilled_in_pairs == 0 and summ.n_lines_filled == 0
    assert set(summ.unfilled_by_reason) == {"no_pair:menu_only", "no_pair:unresolved_usda"}


# -- A. pipeline: blocker attribution and sub-recipe references ----------------------------------------------


def test_blocker_names_the_preparation_problem_not_a_nutrient_gap():
    pages = {"https://a.test/x": recipe_page("Tomato Toast", ["4 ripe plum tomatoes", "2 slices toasted sourdough bread"])}
    results = {"open": [{"url": "https://a.test/x", "title": "x"}], "structured_hosts": []}
    est, _, _ = run(MenuItem(name="HEIRLOOM TOMATOES", description="", section="TO START"), pages, results,
                    queries=dict(QUERIES, **{"toasted sourdough bread": ("bread sourdough", BREAD, "direct")}))
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    bread = next(l for l in sc.ingredients if "sourdough" in l.name)
    assert bread.preparation_state == "cooked" and bread.match.record_state == "unknown"
    assert bread.blocker == "preparation_unresolved" and sc.blockers == {"preparation_unresolved": 1}


def test_sub_recipe_reference_with_components_on_the_page_is_excluded_from_the_calculation_not_counted_as_a_gap():
    pages = {"https://a.test/p": recipe_page("Margherita Pizza", ["1 recipe pizza dough, recipe follows", "4 ripe plum tomatoes", "2 tablespoons olive oil"])}
    results = {"open": [{"url": "https://a.test/p", "title": "p"}], "structured_hosts": []}
    est, _, _ = run(MenuItem(name="MARGHERITA", description="", section="PIZZA"), pages, results)
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    ref = next(l for l in sc.ingredients if l.name == "pizza dough")
    assert ref.excluded_from_calculation == "sub_recipe_reference_components_listed" and ref.blocker is None
    assert [i["name"] for i in sc.calculation["ingredients"]] == ["ripe plum tomatoes", "olive oil"]
    assert sc.calculation_status == "complete" and "sub_recipe_reference_skipped:pizza dough" in sc.flags


# -- B. D24 completeness-aware reselection ----------------------------------------------------------------


EVOO_PAGE = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "2 tablespoons extra virgin olive oil"])}
EVOO_RESULTS = {"open": [{"url": "https://a.test/crudo", "title": "Crudo"}], "structured_hosts": []}
EVOO_QUERIES = dict(QUERIES, **{"extra virgin olive oil": ("oil olive extra virgin", EVOO, "direct")})
EVOO_SEARCHES = {"oil olive extra virgin": [EVOO, OLIVE]}
CRUDO = MenuItem(name="BLUEFIN CRUDO", description="", section="TO START")


def test_d24_is_off_by_default_and_costs_nothing():
    est, _, rec = run(CRUDO, EVOO_PAGE, EVOO_RESULTS, queries=EVOO_QUERIES, searches=EVOO_SEARCHES)
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    oil = next(l for l in sc.ingredients if "olive" in l.name)
    assert oil.match.fdc_id == EVOO and oil.match.source == "llm" and oil.blocker == "nutrient_not_reported"
    assert sc.completeness_by_nutrient == {"saturated_fat_g": True, "cholesterol_mg": False}
    assert not any("D24" in n for n in est.notes)
    assert est.cost.usda_lookups == 3                                                 # tuna and oil nutrition, and the oil read again for the facts of 12.14.7 (saved, no request): none for an idle policy


def test_d24_refuses_the_real_evoo_pair_at_the_d22_tolerance_and_admits_it_only_at_a_wider_one():
    est, service, _ = run(CRUDO, EVOO_PAGE, EVOO_RESULTS, queries=EVOO_QUERIES, searches=EVOO_SEARCHES,
                          policy=lambda svc: CompleteRecordPolicy(svc, enabled=True, tolerance=D("0.05")))
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    oil = next(l for l in sc.ingredients if "olive" in l.name)
    assert oil.match.fdc_id == EVOO and oil.blocker == "nutrient_not_reported"

    est2, service2, _ = run(CRUDO, EVOO_PAGE, EVOO_RESULTS, queries=EVOO_QUERIES, searches=EVOO_SEARCHES,
                            policy=lambda svc: CompleteRecordPolicy(svc, enabled=True, tolerance=D("0.15")))
    (sc2,) = [s for s in est2.scenarios if s.status == "calculated"]
    oil2 = next(l for l in sc2.ingredients if "olive" in l.name)
    assert oil2.match.fdc_id == OLIVE and oil2.match.source == "d24" and oil2.match.substituted_for == EVOO
    assert oil2.match.saturated_fat_delta_per_100g == D("13.808") - D("15.4")        # the whole line now uses one record that reports both
    assert "d24_complete_record" in oil2.flags and oil2.conversion.grams == D(27) and oil2.blocker is None    # re-weighed on 171413's own tablespoon
    assert "USDA 171413" in oil2.conversion.reference and "748608" not in oil2.conversion.reference         # grams and nutrients from one record
    assert sc2.calculation_status == "complete" and sc2.completeness_by_nutrient == {"saturated_fat_g": True, "cholesterol_mg": True}
    assert any(n.startswith("D24 (applied)") and "-1.592" in n for n in est2.notes)


def test_d24_observe_mode_logs_without_applying():
    holder = {}
    def make(svc):
        holder["p"] = CompleteRecordPolicy(svc, enabled=False, observe=True, tolerance=D("0.15"))
        return holder["p"]
    est, _, _ = run(CRUDO, EVOO_PAGE, EVOO_RESULTS, queries=EVOO_QUERIES, searches=EVOO_SEARCHES, policy=make)
    observe = holder["p"]
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    oil = next(l for l in sc.ingredients if "olive" in l.name)
    assert oil.match.fdc_id == EVOO and oil.blocker == "nutrient_not_reported"
    assert any(n.startswith("D24 (not applied: policy off)") for n in est.notes)
    assert [e for e in observe.log if "to" in e][0]["applied"] is False


def test_d24_never_crosses_food_identity_state_or_form():
    """A record missing both nutrients (Foundation red onion) is not replaced by 'Onions, raw': the two-word head differs."""
    service, _ = make_usda({"onions red raw": [RED_ONION, ONION]})
    policy = CompleteRecordPolicy(service, enabled=True, tolerance=D("0.5"))
    from roli_agent.recipes.models import MatchDecision
    match = MatchDecision(name="red onion", preparation_hint="unknown", fdc_id=RED_ONION, description="Onions, red, raw", data_type="Foundation", record_state="raw",
                          match_type="direct", candidates=[{"fdc_id": RED_ONION, "description": "Onions, red, raw", "data_type": "Foundation"},
                                                           {"fdc_id": ONION, "description": "Onions, raw", "data_type": "SR Legacy"}])
    assert policy.find(line("1/2 cup red onion (thinly sliced)"), match) is None


# -- C. relevance: the method text decides ------------------------------------------------------------------


GEM = MenuItem(name="LITTLE GEM LETTUCES", description="tahini vinaigrette, pecorino sardo, toasted sesame", section="TO START")
RAW_CRUDO = MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START")


def recipe(title: str, lines: list[str], steps: str) -> SourceRecipe:
    return SourceRecipe(url="https://x.test/r", canonical_url="https://x.test/r", host="x.test", title=title, found_by=["open"], fetched_at="t", extraction="json_ld",
                        yield_text="4 servings", servings=D(4), ingredient_lines=lines, instructions_text=steps, cooking_verbs=[],
                        ingredients=[q for l in lines for q in parse_lines(l)], content_hash="h")


def test_raw_families_follow_the_menus_own_words():
    assert raw_family(GEM) == "leaf_salad" and raw_family(RAW_CRUDO) == "raw_fish"
    assert raw_family(MenuItem(name="GRILLED LITTLE GEMS", description="", section="TO START")) is None
    assert raw_family(MenuItem(name="KING SALMON", description="shishito, squash", section="")) is None


def test_method_text_that_cooks_the_lettuce_excludes_even_a_salad_title_but_a_baked_garnish_does_not():
    grilled = recipe("Grilled Little Gem salad", ["6 Little Gem lettuce heads", "3 ounces feta"],
                     "Heat grill to medium. Brush the lettuce with a little olive oil and grill for 1 - 2 minutes on either side until lettuce is lightly charred.")
    passed, reason = gate(GEM, grilled)
    assert not passed and reason == "hard_exclusion:main_ingredient_cooked_in_method:grill"
    baked = recipe("Baked Goat Cheese With Garden Lettuces", ["8 ounces goat cheese", "1/2 pound mixed lettuces"],
                   "Bake the cheese until golden. Toss the lettuces with the vinaigrette. Place 2 discs of the baked cheese on each plate.")
    assert gate(GEM, baked) == (True, None)
    garnish = recipe("Little Gem Salad", ["4 heads little gem lettuce", "2 tablespoons sesame seeds"],
                     "Toast the sesame seeds in a dry pan. Top the lettuce with the toasted seeds and serve.")
    assert gate(GEM, garnish) == (True, None)
    seared = recipe("Tuna Crudo with Citrus", ["200 g tuna", "1 orange"], "Sear the tuna for 20 seconds per side, then slice thinly and dress with citrus.")
    assert gate(RAW_CRUDO, seared)[1] == "hard_exclusion:main_ingredient_cooked_in_method:sear"
    # a menu dish that is itself grilled has no raw family: the same recipe passes
    assert gate(MenuItem(name="GRILLED LITTLE GEMS", description="", section="TO START"), grilled) == (True, None)


def test_rubric_block_carries_the_method_sentence_as_evidence():
    grilled = recipe("Grilled Little Gems With Creamy Tarragon Dressing", ["4 heads Little Gem lettuce", "1 cup yogurt"],
                     "Once the grill is hot, place lettuce on the grill, cut-side down, and cook undisturbed for 4 to 5 minutes, until the lettuce is charred.")
    block = _recipe_block(1, grilled, GEM)
    assert "method text cooks the main ingredient" in block and "place lettuce on the grill" in block
    assert "method text cooks" not in _recipe_block(1, grilled, None)
    assert cooked_main_ingredient(GEM, grilled).startswith("grill:")
