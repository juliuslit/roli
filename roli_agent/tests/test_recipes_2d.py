"""Phase 2D (2026-11-03): documented inferences, restaurant portion models, the dish-comparison prototype. Saved real USDA records; no network.

Order of proof, as asked: the portion arithmetic on controlled recipes whose every line is a stated weight, then the safeguards (f never
from the serving count; incomplete stays incomplete; recipe basis untouched; unapproved rules stay proposed), then the inference layer and
the comparison verdict logic.
"""

from __future__ import annotations

import inspect
import json
import re
from decimal import Decimal

import httpx
import pytest

from roli_nutrition.recipe import RecipeCalculator, RecipeResult
import roli_nutrition.recipe.calculator as calculator_module

from roli_agent.llm import parse_json_object
from roli_agent.recipes.adapt import WeightsTable, WeightRow, adapt_pairs
from roli_agent.recipes.compare_dishes import ExternalEvidence, compare_dishes, dish_interval, scenario_interval
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.inference import apply_inference_layer
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import DishInterval, MenuItem, ScenarioInterval
from roli_agent.recipes.pipeline import estimate_dish, is_flesh_name
from roli_agent.recipes.portions import (PortionRule, PortionRules, dish_type_for, pair_inputs, portion_scenario, published_input, unit_count_from_text)
from roli_agent.responses import dish_reply

from conftest import load, make_service
from recipe_test_helpers import BLUEFIN, OLIVE, ROMANO, TOMATO, FakeSource, RuleLLM, SEARCHES, QUERIES, recipe_page
from test_recipes_fetch_search import Site

D = Decimal
SALT, CHIVES, BASIL, EVOO, GARLIC = 173468, 169994, 172232, 748608, 169230


def usda(extra: dict | None = None):
    foods = {fid: load(f"food_{fid}") for fid in (BLUEFIN, OLIVE, ROMANO, TOMATO, SALT, CHIVES, BASIL, EVOO, GARLIC)}
    searches = dict(SEARCHES, **{"salt table": [SALT], "chives raw": [CHIVES], "basil fresh": [BASIL], "oil olive extra virgin": [EVOO], "garlic raw": [GARLIC]}, **(extra or {}))

    def respond(request):
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = [f for f in searches.get(q, []) if f in foods]
            return httpx.Response(200, json={"foods": [{"fdcId": f, "description": foods[f]["description"], "dataType": foods[f]["dataType"]} for f in ids]})
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=foods[fid]) if fid in foods else httpx.Response(404, content=b"")
    return make_service(respond)


def rules(**overrides) -> PortionRules:
    rows = [
        {"id": "PR01", "dish_type": "pizza_neapolitan", "model": "P1", "low": "0.5", "high": "1", "unit": "pizza units per portion", "restaurant_diameter_low_in": "12",
         "restaurant_diameter_high_in": "13", "key_record_head": "", "basis": "one pizza is one plate", "sources": "test", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""},
        {"id": "PR03", "dish_type": "crudo_starter", "model": "P3", "low": "45", "high": "110", "unit": "g raw fish per plate", "restaurant_diameter_low_in": "", "restaurant_diameter_high_in": "",
         "key_record_head": "fish", "basis": "raw fish per plate", "sources": "test", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""},
        {"id": "PR05", "dish_type": "tomato_salad_starter", "model": "P2", "low": "150", "high": "300", "unit": "g plated salad", "restaurant_diameter_low_in": "", "restaurant_diameter_high_in": "",
         "key_record_head": "", "basis": "plate weight", "sources": "test", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""},
    ]
    for r in rows:
        r.update(overrides.get(r["id"], {}))
    return PortionRules([PortionRule(r) for r in rows])


CRUDO = MenuItem(name="BLUEFIN CRUDO", description="", section="TO START")
TOMATOES = MenuItem(name="HEIRLOOM TOMATOES", description="", section="TO START")
PIZZA = MenuItem(name="MARGHERITA", description="", section="PIZZA")
Q = dict(QUERIES, **{"flaky salt": ("salt table", SALT, "direct"), "chive": ("chives raw", CHIVES, "direct"), "genovese basil": ("basil fresh", BASIL, "direct"),
                     "bottarga": ("fish roe", None, "direct"), "extra virgin olive oil": ("oil olive extra virgin", EVOO, "direct"), "garlic": ("garlic raw", GARLIC, "direct")})


TITLES = {"BLUEFIN CRUDO": "Tuna Crudo", "MARGHERITA": "Margherita Pizza", "HEIRLOOM TOMATOES": "Heirloom Tomato Salad"}


def run(item: MenuItem, lines: list[str], *, yield_text="4 servings", steps="Slice and dress. Serve.", adapt_mode="off", table=None, portion=True, queries=None):
    pages = {"https://a.test/r": recipe_page(TITLES[item.name], lines, yield_text=yield_text, steps=steps)}
    fetcher = PoliteFetcher(transport=httpx.MockTransport(Site(pages=pages)), sleep=lambda s: None)
    service, rec = usda()
    est = estimate_dish(item, source=FakeSource({"open": [{"url": "https://a.test/r", "title": "Test Recipe"}], "structured_hosts": []}), fetcher=fetcher, service=service,
                        llm=RuleLLM(queries=queries or Q), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode=adapt_mode,
                        weights_table=table or WeightsTable([]), portion_rules=rules() if portion else None)
    return est, service


# -- 1. portion arithmetic on controlled recipes (every line a stated weight) -------------------------------------------------------


def test_p3_scales_a_fully_weighed_crudo_by_the_fish_ratio_and_keeps_the_recipe_basis():
    est, _ = run(CRUDO, ["200 g bluefin tuna, thinly sliced", "27 g olive oil", "100 g tomatoes, diced"])        # 4 servings stated
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    assert s.calculation_status == "complete" and s.basis == "source_reported" and s.completeness_basis == {"saturated_fat_g": "complete_source_reported", "cholesterol_mg": "complete_source_reported"}
    (p,) = est.portioned
    assert p.applicable and p.model == "P3" and p.portion_rule_id == "PR03" and p.input_kind == "published" and p.confidence == "portion_proposed"
    assert p.fraction_low.fraction == D(45) / D(200) and p.fraction_high.fraction == D(110) / D(200)
    assert p.fraction_low.arithmetic == "K / K_recipe = 45 g / 200 g" and "serving" not in p.fraction_low.arithmetic
    # per portion = whole-recipe total x f, through the unchanged calculator run at servings = 1 / f
    result = RecipeResult.model_validate(s.calculation)
    total_sat, total_chol = result.totals["saturated_fat_g"].total, result.totals["cholesterol_mg"].total
    assert total_sat == D(200) * D("1.257") / 100 + D(27) * D("13.808") / 100 + D(100) * D("0.028") / 100 and total_chol == D(200) * D(38) / 100
    for bound, f in ((p.low, D(45) / D(200)), (p.high, D(110) / D(200))):
        assert bound.calculation_status == "complete" and bound.servings_for_calculator == D(1) / f
        assert abs(bound.per_portion["saturated_fat_g"]["total"] - total_sat * f) <= D("0.000001") and abs(bound.per_portion["cholesterol_mg"]["total"] - total_chol * f) <= D("0.000001")
        assert bound.calculation["servings"] == str(D(1) / f) and bound.calculation["calculator_version"] == result.calculator_version
    # the recipe basis is preserved untouched and the per-serving (recipe) figure is not the per-portion figure
    assert p.recipe_basis["servings"] == "4" and p.recipe_basis["servings_basis"] == "recipe"
    assert D(p.recipe_basis["per_serving"]["published"]["saturated_fat_g"]["total"]) == result.per_serving["saturated_fat_g"].total
    assert p.servings_basis == "restaurant_model" and "not a verified restaurant serving" in p.note
    assert p.uncertainty["fraction_ratio_high_over_low"] == str((D(110) / D(45)).quantize(D("0.001")))


def test_p1_unit_count_comes_from_the_page_never_from_servings():
    steps = "Make the dough. Divide the dough in half. Stretch one ball into a 10-inch circle and top it. Bake."
    est, _ = run(PIZZA, ["300 g bluefin tuna", "100 g romano cheese", "27 g olive oil"], yield_text="8 servings", steps=steps)
    (p,) = est.portioned
    assert p.applicable and p.model == "P1" and p.fraction_low.inputs["k"] == "2" and "Divide the dough in half" in p.fraction_low.inputs["unit_count_source"]
    assert p.fraction_low.fraction == p.fraction_high.fraction == D("0.5")                       # 12.14.10: no dough weight known: one plate is one of the recipe's pizzas
    # no unit count anywhere on the page: one pizza, whatever the serving count says
    est2, _ = run(PIZZA, ["300 g bluefin tuna", "100 g romano cheese", "27 g olive oil"], yield_text="8 servings", steps="Mix, rest, bake.")
    (p2,) = est2.portioned
    assert p2.applicable and p2.fraction_low.fraction == D(1) and p2.fraction_low.inputs["unit_count_source"] == "the page states no count: one pizza"
    # a reserved piece of dough: the list does not describe one unit
    est3, _ = run(PIZZA, ["300 g bluefin tuna", "100 g romano cheese", "27 g olive oil"], yield_text="1 serving", steps="Cut the dough into 2 pieces and reserve 1 piece for another use. Stretch the other piece.")
    (p3,) = est3.portioned
    assert not p3.applicable and "reserves part of the dough" in p3.not_applicable_reason
    # a page whose only yield is a unit count ("One 12-inch pizza"): approved 2026-11-03, the recipe basis is one serving per unit and P1 reads k = 1
    est5, _ = run(PIZZA, ["300 g bluefin tuna", "100 g romano cheese", "27 g olive oil"], yield_text="One 12-inch pizza", steps="Bake it.")
    (s5,) = [x for x in est5.scenarios if x.status == "calculated"]
    assert s5.source.servings == D(1) and "servings_from_unit_yield" in s5.source.flags and "per unit" in s5.source.servings_note
    (p5,) = est5.portioned
    assert p5.applicable and p5.fraction_low.inputs["k"] == "1" and "yield text" in p5.fraction_low.inputs["unit_count_source"]
    # a slice count or a diameter alone is never a unit count or a serving count
    est6, _ = run(PIZZA, ["300 g bluefin tuna", "100 g romano cheese", "27 g olive oil"], yield_text="8 slices", steps="Bake it.")
    assert est6.scenarios[0].status_reason == "servings_unknown" and est6.portioned == []


def test_unit_count_reader_on_the_frozen_recipes_sentences():
    assert unit_count_from_text("12 servings", "Step 5 Divide the dough in half (about 200g per piece).")["k"] == 2
    assert unit_count_from_text("4 servings", "Separate the dough into two equal-sized portions. Stretch one ball of pizza dough into roughly a 10-inch circle.") == \
        {"k": 2, "evidence": "method text: 'Separate the dough into two equal-sized portions.'", "diameter_in": D(10), "reserved": False, "source": "method_divide"}
    r = unit_count_from_text("6 servings", "Roll it into a 13-inch circle. Then, transfer it to a greased 14-inch pizza pan.")
    assert (r["k"], r["diameter_in"], r["source"]) == (1, D(13), "method_shape_one")             # the dough's circle, not the pan
    assert unit_count_from_text("4 servings", "Slice and dress. Serve.")["k"] is None
    assert unit_count_from_text("", "Makes two 12-inch pizzas.")["k"] == 2


def test_p2_needs_the_whole_recipe_mass_and_counts_menu_only_lines_once_per_plate():
    est, _ = run(TOMATOES, ["600 g tomatoes, sliced", "27 g olive oil"])
    (p,) = est.portioned
    assert p.applicable and p.model == "P2" and p.fraction_low.arithmetic == "W / M_served = 150 g / 627 g" and p.fraction_high.fraction == D(300) / D(627)
    assert any("raw = served" in l or "no cooking loss" in l for l in p.limitations)
    # an unweighed recipe line makes the mass incomplete: P2 refuses rather than overstate f
    est2, _ = run(TOMATOES, ["600 g tomatoes, sliced", "olive oil, for drizzling"])
    (p2,) = est2.portioned
    assert not p2.applicable and "served mass is incomplete" in p2.not_applicable_reason and "olive oil" in p2.not_applicable_reason


def test_published_and_pair_are_portioned_separately_and_per_plate_assumptions_count_once_per_portion():
    table = WeightsTable([WeightRow({"id": "W01", "ingredient_role": "chives", "ingredient_keys": "chive", "fdc_id": str(CHIVES), "usda_description": "Chives, raw", "low_g": "1", "high_g": "3",
                                     "amount_basis": "per_plate", "basis": "usda_measure", "measures": "t", "review_status": "verified_usda_measure; restaurant usage assumed", "approved_by": "", "notes": ""})])
    item = MenuItem(name="BLUEFIN CRUDO", description="chive", section="TO START")
    est, _ = run(item, ["200 g bluefin tuna, thinly sliced", "27 g olive oil", "100 g tomatoes, diced"], adapt_mode="experimental", table=table)
    pub = next(p for p in est.portioned if p.input_kind == "published")
    pair = next(p for p in est.portioned if p.input_kind == "adapted_pair")
    assert pub.applicable and pair.applicable and pair.adapt_mode == "experimental" and pair.derived_from.endswith("::adapted")
    # the published scenario is incomplete (menu-only chive) and stays so when portioned: a scaled subtotal is still a subtotal
    assert pub.low.calculation_status == "incomplete" and pub.low.per_portion["saturated_fat_g"]["total"] is None and pub.low.per_portion["saturated_fat_g"]["known_subtotal"] > 0
    # the pair is complete; its chive line (per plate) contributes the plate amount once per portion, whatever f is
    hi = RecipeResult.model_validate(pair.high.calculation)
    chive = next(i for i in hi.ingredients if i.name == "chive")
    assert chive.quantity_basis == "per_serving" and chive.grams_declared == D(3) and chive.grams_in_recipe == D(3) * pair.high.servings_for_calculator
    assert abs(hi.per_serving["saturated_fat_g"].total - (D(200) * D("1.257") / 100 + D(27) * D("13.808") / 100 + D(100) * D("0.028") / 100) * pair.fraction_high.fraction - D(3) * D("0.146") / 100) <= D("0.000001")
    # the recipe-basis pair figures are untouched beside the portioned ones
    assert pair.recipe_basis["servings"] == "4" and set(pair.recipe_basis["per_serving"]) == {"low", "high"}
    # nothing user-facing changed
    off, _ = run(item, ["200 g bluefin tuna, thinly sliced", "27 g olive oil", "100 g tomatoes, diced"], portion=False)
    assert dish_reply(est.model_dump(mode="json")) == dish_reply(off.model_dump(mode="json")) and "portion" not in dish_reply(est.model_dump(mode="json")).lower()


def test_rules_table_loads_unapproved_and_the_calculator_source_is_untouched():
    t = PortionRules.load()
    assert [r.id for r in t.rows] == [f"PR{i:02d}" for i in range(1, 34)] and all(r.approved_by == "Julius" and r.review_status in ("approved", "unsourced") for r in t.rows)   # 12.18: every row approved 2026-11-07 (PR06, PR08 as unsourced); PR13-PR15: the 3D cards; PR16-PR33: the 3I families
    assert [r.id for r in t.for_dish_type("tomato_salad_starter")] == ["PR05"] and [r.id for r in t.unsourced() if r.dish_type == "tomato_salad_starter"] == ["PR06"]   # 3I second rebuild: the P2 caprese row is sourced (Pizza Express, Vapiano, Zizzi); the raw-tomato P3 row stays unsourced and is never used (12.16.8)
    assert all(r.confidence == ("portion_proposed" if r.review_status == "unsourced" else "portion_reviewed") for r in t.rows)   # 12.18
    src = inspect.getsource(calculator_module)
    assert "portion" not in src.lower() and "infer" not in src.lower()


# -- 2. documented inferences -------------------------------------------------------------------------------------------------------


def test_inference_layer_leaves_other_gaps_open():
    est, _ = run(CRUDO, ["200 g bluefin tuna, thinly sliced", "27 g extra virgin olive oil", "flaky salt, to taste"])
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    t = s.inferred_totals["cholesterol_mg"]
    assert not t.complete_with_inferences and t.total is None and t.inferred_lines == [] and "flaky salt (missing_grams)" in t.remaining_excludes     # with no line tags the facts of 12.14.7 do not apply


def test_leading_list_glyphs_do_not_hide_the_quantity_and_the_verbatim_line_is_kept():
    from roli_agent.recipes.parse import parse_line
    p = parse_line("• ½ lb Bluefin Tuna (Substitute Ahi Tuna )")
    assert (p.quantity, p.unit, p.name) == (D("0.5"), "lb", "bluefin tuna") and "leading_bullet_stripped" in p.flags and p.line.startswith("• ½ lb")
    q = parse_line("▢ 6-8 oz bluefin, sushi grade")
    assert (q.quantity, q.unit, q.name) == (D(7), "oz", "bluefin") and q.line.startswith("▢")
    assert parse_line("- 2 cups flour").quantity == D(2) and "leading_bullet_stripped" not in parse_line("2 cups flour").flags
    assert parse_line("1-2 tbsp oil").quantity == D("1.5")                      # a range is not a bullet


def test_chicken_stock_is_not_a_flesh_food():
    assert is_flesh_name("chicken breast") and is_flesh_name("king salmon fillets") and is_flesh_name("bacon")
    assert not is_flesh_name("chicken stock") and not is_flesh_name("fish sauce") and not is_flesh_name("duck fat") and not is_flesh_name("beef broth")


# -- 3. the comparison prototype -------------------------------------------------------------------------------------------------------


def iv(dish, low, high, tier="modeled_range_complete", **kw) -> DishInterval:
    si = ScenarioInterval(scenario_id=f"{dish}:r", nutrient="saturated_fat_g", tier=tier, low=D(low), high=None if high is None else D(high), **kw)
    return dish_interval(dish, "saturated_fat_g", [si])


def test_pairwise_verdicts_never_rank_on_a_lower_bound_alone():
    per = {"saturated_fat_g": {"a": iv("a", "1", "2"), "b": iv("b", "3", "5"), "c": iv("c", "0.5", None, tier="lower_bound_only", unbounded_lines=["x (missing_grams)"]), "d": iv("d", "2.5", "4")}}
    cmp = compare_dishes(per)
    v = {(p.dish_a, p.dish_b): p for p in cmp.pairwise}
    assert v[("a", "b")].verdict == "well_supported" and v[("a", "b")].lower == "a" and v[("a", "b")].margin == D(1)
    assert v[("b", "d")].verdict == "overlapping"
    assert v[("a", "c")].verdict == "insufficient_evidence" and "c has no upper bound" in v[("a", "c")].reason and "lower bound alone cannot rank" in v[("a", "c")].reason
    assert v[("a", "d")].verdict == "well_supported" and v[("a", "d")].lower == "a"
    assert cmp.ordering[-1] == "c" and "1 do not (c)" in cmp.ordering_note and "unbounded_dishes" in cmp.flags and cmp.statement.startswith("INTERNAL")
    narrow = compare_dishes({"saturated_fat_g": {"a": iv("a", "1", "4.0"), "b": iv("b", "4.1", "9")}})
    assert narrow.pairwise[0].verdict == "tentative" and any(c.startswith("narrow margin") for c in narrow.pairwise[0].tentative_because)
    # a disjoint pair that holds only through an external-evidence bound is tentative, not well supported (Julius, 2026-11-03)
    ext = iv("e", "1", "3", tier="modeled_range_external_bound", external_bound=D("0.5"))
    dep = compare_dishes({"saturated_fat_g": {"e": ext, "f": iv("f", "4", "9")}})
    assert dep.pairwise[0].verdict == "tentative" and any("external-evidence" in w for w in dep.pairwise[0].tentative_because)
    assert ext.high_without_external is None
    two = DishInterval(dish="g", nutrient="saturated_fat_g", low=D(1), high=D(3), high_without_external=D(2), bounded=True, n_scenarios=2, n_bounded=2)
    ok = compare_dishes({"saturated_fat_g": {"g": two, "f": iv("f", "4", "9")}})
    assert ok.pairwise[0].verdict == "well_supported"                         # the USDA-only bound (2) still sits below f's lower bound (4)


def test_dish_interval_withdraws_an_upper_bound_an_incomplete_recipe_already_exceeds():
    bounded = ScenarioInterval(scenario_id="x:a", nutrient="saturated_fat_g", tier="modeled_range_complete", low=D(1), high=D(2))
    open_ = ScenarioInterval(scenario_id="x:b", nutrient="saturated_fat_g", tier="lower_bound_only", low=D(3), high=None, unbounded_lines=["cream (missing_grams)"])
    d = dish_interval("x", "saturated_fat_g", [bounded, open_])
    assert d.low == D(1) and d.high is None and not d.bounded and any("withdrawn" in c for c in d.caveats)
    d2 = dish_interval("x", "saturated_fat_g", [bounded, ScenarioInterval(scenario_id="x:c", nutrient="saturated_fat_g", tier="lower_bound_only", low=D("0.5"), high=None)])
    assert d2.high == D(2) and any("upper bound from 1 of 2 recipes" in c for c in d2.caveats)


def test_external_evidence_bounds_scale_with_the_portion_and_never_enter_a_total():
    ev = ExternalEvidence.load()
    chol = ev.upper_bound("bottarga", "cholesterol_mg", grams_in_recipe=None, fraction_high=D("0.5"))
    assert chol[0] == D(10) * 722 / 100 and "per plate" in chol[1]                                         # a menu-only garnish counts once per plate, unscaled
    milk = ev.upper_bound("milk", "saturated_fat_g", grams_in_recipe=None, fraction_high=D("0.25"))
    assert milk[0] == D(490) * D("1.865") / 100 * D("0.25")                                               # a recipe line's estimated amount is scaled by f
    tom = ev.upper_bound("whole", "saturated_fat_g", grams_in_recipe=D(411), fraction_high=D("0.5"), description="Tomatoes, whole, canned, solids and liquids")
    assert tom[0] == D(411) * D("0.034") / 100 * D("0.5") and "the line's own 411 g" in tom[1]            # a record-gap line uses its own stated grams
    assert ev.upper_bound("white balsamic vinegar", "cholesterol_mg", grams_in_recipe=None, fraction_high=D(1)) == (D(0), ev.upper_bound("vinegar", "cholesterol_mg", grams_in_recipe=None, fraction_high=D(1))[1])
    assert ev.upper_bound("white balsamic vinegar", "saturated_fat_g", grams_in_recipe=None, fraction_high=D(1)) is None   # the record reports that one itself
    assert ev.upper_bound("greek yogurt", "cholesterol_mg", grams_in_recipe=None, fraction_high=D(1))[0] == D(130) * 13 / 100
    assert ev.upper_bound("saku tuna", "saturated_fat_g", grams_in_recipe=None, fraction_high=D(1)) is None


def test_scenario_interval_tiers_from_a_pipeline_run():
    """Crudo with a menu-only bottarga: the pair stays incomplete (blocked row); the interval is bounded only by the labelled external evidence."""
    table = WeightsTable([WeightRow({"id": "W10", "ingredient_role": "bottarga", "ingredient_keys": "bottarga", "fdc_id": "", "usda_description": "", "low_g": "3", "high_g": "10",
                                     "amount_basis": "per_plate", "basis": "blocked", "measures": "", "review_status": "blocked_questionable_proxy", "approved_by": "", "notes": "blocked"}),
                          WeightRow({"id": "W09", "ingredient_role": "olive oil", "ingredient_keys": "olive oil", "fdc_id": str(OLIVE), "usda_description": "Oil, olive, salad or cooking", "low_g": "4.5",
                                     "high_g": "13.5", "amount_basis": "per_plate", "basis": "proposed", "measures": "t", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""})])
    item = MenuItem(name="BLUEFIN CRUDO", description="bottarga", section="TO START")
    est, _ = run(item, ["200 g bluefin tuna, thinly sliced", "olive oil, for drizzling", "100 g tomatoes, diced"], adapt_mode="experimental", table=table)
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    (pair,) = est.adapted_pairs
    pub = next(p for p in est.portioned if p.input_kind == "published")
    pp = next(p for p in est.portioned if p.input_kind == "adapted_pair")
    ev = ExternalEvidence.load()
    sat = scenario_interval(s, pair, pub, pp, "saturated_fat_g", ev)
    chol = scenario_interval(s, pair, pub, pp, "cholesterol_mg", ev)
    assert sat.tier == "modeled_range_external_bound" and sat.external_bound == D(10) * D("3.8") / 100 and sat.unbounded_lines == []
    assert chol.tier == "modeled_range_external_bound" and chol.external_bound == D(10) * 722 / 100
    f_hi = pp.fraction_high.fraction
    assert abs(chol.high - (D(200) * 38 / 100 * f_hi + D("72.2"))) <= D("0.000001") and abs(chol.low - D(200) * 38 / 100 * pp.fraction_low.fraction) <= D("0.000001")
    assert any(d.startswith("external upper bound") for d in chol.drivers) and any("assumed olive oil" in d for d in sat.drivers)
    # a line nothing bounds leaves the scenario a lower bound only
    est2, _ = run(MenuItem(name="BLUEFIN CRUDO", description="caviar pearls", section="TO START"), ["200 g bluefin tuna, thinly sliced", "27 g olive oil", "100 g tomatoes"], adapt_mode="experimental", table=table,
                  queries=dict(Q, **{"caviar pearls": ("fish roe", None, "direct")}))
    (s2,) = [x for x in est2.scenarios if x.status == "calculated"]
    pub2 = next(p for p in est2.portioned if p.input_kind == "published")
    only = scenario_interval(s2, None, pub2, None, "cholesterol_mg", ev)
    assert only.tier == "lower_bound_only" and only.high is None and only.unbounded_lines == ["caviar pearls (missing_fdc_id)"]
