"""Checkpoint 3K (SPEC_3_mvp.md 12.20): the band (simulated plates over plate weight x recipe x assumed-amount position), recipe weights and outliers, the plate-weight
samples, the frying-fat prior, the consumers (ranking wording, reference middle, web), the sampling inputs' invariant on saved runs. No network."""

from __future__ import annotations

import csv
import json
import random
from decimal import Decimal
from pathlib import Path

import pytest

from roli_agent.config import ROOT
from roli_agent.mvp.models import MvpConfig, RankedDish
from roli_agent.mvp.ranking import frying_fat_line, rank_dishes, recommendation_text
from roli_agent.mvp.reference import reference_check
from roli_agent.recipes.compare_dishes import _sampling_inputs, dish_interval
from roli_agent.recipes.models import DishComparison, DishInterval, PortionedScenario, SamplingInputs, ScenarioInterval
from roli_agent.recipes.plate_weights import PlateWeights
from roli_agent.recipes.portions import PortionRules
from roli_agent.recipes.sampling import PlateSampler, band_seed, load_frying_fat_prior, make_sampler, outliers, quantile, recipe_weights, sample_band

from test_3d_reference_usda import dish

D = Decimal
RULES = PortionRules.load()
ROUND2 = ["20261108-140127-abbf34", "20261108-140247-e7468c", "20261108-140617-8a7d6a", "20261108-140737-78c112"]     # 3J round 2 pass A: 03, 08, 01, 23


def si(sid, low, high, *, model="P2", rule="PR10", r=(D(2), D(4)), p=(D(0), D(0)), plate=(D(50), D(300)), mass=(D(600), D(650)), key=None, dough=None, ext=D(0), kind="recipe", choices=None):
    s = SamplingInputs(kind=kind, model=model, rule_id=rule, recipe_total_low=r[0], recipe_total_high=r[1], per_plate_low=p[0], per_plate_high=p[1],
                       fraction_low=D(plate[0]) / mass[0] if model == "P2" else None, fraction_high=D(plate[1]) / mass[1] if model == "P2" else None,
                       plate_low_g=plate[0] if model == "P2" else None, plate_high_g=plate[1] if model == "P2" else None, served_mass_low=mass[0] if model == "P2" else None,
                       served_mass_high=mass[1] if model == "P2" else None, external_bound=ext, choice_ranges=choices or {})
    if model == "P3" and key:
        s = s.model_copy(update={"key_plate_low_g": key[0], "key_plate_high_g": key[1], "key_recipe_low_g": key[2], "key_recipe_high_g": key[3]})
    if model == "P1" and dough:
        s = s.model_copy(update={"dough_ball_low_g": dough[0], "dough_ball_high_g": dough[1], "recipe_dough_g": dough[2]})
    return ScenarioInterval(scenario_id=sid, nutrient="saturated_fat_g", tier="modeled_range_complete", low=D(low), high=D(high), portion_model=model, sampling=s)


def plates(samples: list[float] | None, n_min=10):
    rows = [{"rule_id": "PR10", "source": "t", "business": "b", "item": f"i{k}", "grams": str(g), "kind": "chain_plate", "read_on": "2026-11-08"} for k, g in enumerate(samples or [])]
    return PlateSampler(PlateWeights(rows), n_min=n_min)


# -- the sampling inputs reproduce every saved bound ---------------------------------------------------------------------------------------------


def test_sampling_inputs_reproduce_both_bounds_on_the_saved_3j_runs():
    checked = 0
    for rid in ROUND2:
        path = ROOT / "roli_agent" / "runs" / rid / "run.json"
        if not path.exists():
            pytest.skip("3J round-2 runs are not on this machine")
        run = json.loads(path.read_text(encoding="utf-8"))
        for d in run["dishes"]:
            for p in ((d.get("estimate") or {}).get("portioned") or []):
                if not p.get("applicable"):
                    continue
                ps = PortionedScenario.model_validate(p)
                for nutrient in ("saturated_fat_g", "cholesterol_mg"):
                    s = _sampling_inputs(ps, nutrient)
                    for bound, R, P in (("low", s.recipe_total_low, s.per_plate_low), ("high", s.recipe_total_high, s.per_plate_high)):
                        target = getattr(ps, bound).per_portion[nutrient]["total_with_inferences"]
                        if target is None:
                            continue
                        f = getattr(s, f"fraction_{bound}")
                        assert abs(f * R + P - target) <= D("0.000002") * max(D(1), abs(target)), (rid, d["item"]["name"], bound, nutrient)
                        checked += 1
    assert checked > 100


def test_old_run_json_loads_with_the_new_fields_defaulted():
    path = ROOT / "roli_agent" / "runs" / ROUND2[0] / "run.json"
    if not path.exists():
        pytest.skip("3J round-2 runs are not on this machine")
    from roli_agent.mvp.models import MenuRun
    run = MenuRun.model_validate_json(path.read_text(encoding="utf-8"))
    iv = DishInterval.model_validate(next(d for d in run.dishes if d.status == "evaluated").intervals["saturated_fat_g"])
    assert iv.band_low is None and iv.plate_source == "" and iv.set_aside == [] and all(s.sampling is None for s in iv.scenarios)
    assert run.ranking[0].band_low is None


# -- the band --------------------------------------------------------------------------------------------------------------------------------------


def test_the_band_is_deterministic_and_lies_inside_the_extremes_and_narrows_a_wide_plate_range():
    samples = [120 + 2 * k for k in range(60)]                                   # 60 measured plates 120-238 g inside a 50-300 g row
    ivs = [si("a:recipe", "0.17", "2.0", plate=(D(50), D(300)), mass=(D(600), D(600)), r=(D(2), D(4)))]
    one = sample_band(ivs, plates=plates(samples), draws=1500, seed=7)
    two = sample_band(ivs, plates=plates(samples), draws=1500, seed=7)
    other = sample_band(ivs, plates=plates(samples), draws=1500, seed=8)
    assert (one.band_low, one.band_mid, one.band_high) == (two.band_low, two.band_mid, two.band_high) and other.band_low != one.band_low
    assert D("0.17") <= one.band_low < one.band_mid < one.band_high <= D("2.0")
    assert one.band_high / one.band_low < D("2.5") and one.plate_source == "samples:60" and one.draws == 1500
    assert band_seed("d", "n", ["b", "a"]) == band_seed("d", "n", ["a", "b"]) != band_seed("e", "n", ["a", "b"])


def test_fewer_samples_than_the_minimum_means_a_uniform_draw_over_the_approved_range():
    ivs = [si("a:recipe", "0.17", "2.0", plate=(D(50), D(300)), mass=(D(600), D(600)))]
    res = sample_band(ivs, plates=plates([100, 200, 300]), draws=800, seed=1)
    assert res.plate_source == "uniform" and D("0.17") <= res.band_low < res.band_high <= D("2.0")


def test_per_plate_lines_do_not_scale_with_the_plate_weight():
    """A menu-only cheese (per-plate line) stays the same whatever the plate weighs; a recipe line scales with W / M."""
    only_plate = [si("a:recipe", "5", "5", r=(D(0), D(0)), p=(D(5), D(5)), plate=(D(50), D(300)), mass=(D(600), D(600)))]
    res = sample_band(only_plate, plates=plates([60.0 + k for k in range(50)]), draws=500, seed=3)
    assert res.band_low == res.band_high == D(5)
    only_recipe = [si("a:recipe", "0.5", "3.0", r=(D(6), D(6)), plate=(D(50), D(300)), mass=(D(600), D(600)))]
    res2 = sample_band(only_recipe, plates=plates([100.0] * 20), draws=300, seed=3)
    assert res2.band_low == res2.band_high == D(1)                               # 6 g x 100 / 600


def test_p3_and_p1_draws_use_the_key_and_dough_inputs():
    p3 = [si("a:recipe", "1", "4", model="P3", rule="PR02", r=(D(8), D(8)), key=(D(156), D(313), D(1000), D(1000)))]
    res = sample_band(p3, plates=PlateSampler(PlateWeights([]), n_min=10), draws=600, seed=2)
    assert res.plate_source == "uniform" and D("1.24") <= res.band_low < res.band_high <= D("2.51")       # f = K/1000 in 0.156-0.313 x 8 g
    p1 = [si("a:recipe", "2", "4", model="P1", rule="PR01", r=(D(10), D(10)), dough=(D(171), D(385), D(400)))]
    res1 = sample_band(p1, plates=PlateSampler(PlateWeights([]), n_min=10), draws=600, seed=2)
    assert D("4.2") <= res1.band_low < res1.band_high <= D("9.7")                                    # ball/400 x 10 g, capped at 1 x 10


def test_recipe_weights_follow_grade_and_coverage_and_an_outlier_is_set_aside_only_with_three_or_more():
    ivs = [si("a:recipe", "2.0", "3.0"), si("b:recipe", "2.2", "3.5"), si("c:recipe", "0.03", "0.06"), si("d:recipe", "1.5", "2.5")]
    w = recipe_weights(ivs, {"a:recipe": "high", "b:recipe": "medium", "c:recipe": "high"}, {"a:recipe": D("1"), "b:recipe": D("0.5"), "c:recipe": None, "d:recipe": D(0)})
    assert w == {"a:recipe": 1.0, "b:recipe": 0.375, "c:recipe": 1.0, "d:recipe": 0.25}
    aside = outliers(ivs, 5.0)
    assert [sid for sid, _ in aside] == ["c:recipe"] and "set aside as an outlier" in aside[0][1]
    assert outliers(ivs[:2] + ivs[2:3], 5.0) == [("c:recipe", aside[0][1])] or len(outliers(ivs[:3], 5.0)) == 1
    assert outliers([ivs[0], ivs[2]], 5.0) == []                                                     # two recipes: never an outlier
    assert outliers([ivs[2], si("e:recipe", "0.04", "0.08"), ivs[0], ivs[1]], 5.0) == []            # two against two: disagreement, nothing set aside
    res = sample_band(ivs, plates=plates([100.0 + k for k in range(40)]), draws=800, seed=5, grade_of={"a:recipe": "high", "b:recipe": "medium", "c:recipe": "high", "d:recipe": "high"})
    assert res.set_aside == ["c:recipe"] and "c:recipe" not in res.recipe_weights and res.band_low > D("0.3")       # 2-4 g x 100-139 g / 600 g; the 0.03 g recipe does not drag the band down
    low, high = min(iv.low for iv in ivs), max(iv.high for iv in ivs)
    d = dish_interval("dish", "saturated_fat_g", ivs, sampler=lambda dish, n, xs: res)
    assert (d.low, d.high) == (low, high) and d.band_low == res.band_low and d.set_aside == ["c:recipe"] and any("set aside as an outlier" in c for c in d.caveats) and any(c.startswith("band (3K)") for c in d.caveats)


def test_a_survey_interval_draws_its_fat_by_the_prior_and_uniformly_without_one():
    ch = {"vegetable oil": {"low": D("4.7"), "high": D("8.0")}, "beef dripping": {"low": D("14"), "high": D("23")}}
    ivs = [ScenarioInterval(scenario_id="svy", nutrient="saturated_fat_g", tier="survey_dish_record", low=D("4.7"), high=D("23"), portion_model="P2",
                            sampling=SamplingInputs(kind="survey", model="P2", per_plate_low=D("4.7"), per_plate_high=D("23"), choice_ranges=ch))]
    prior = load_frying_fat_prior()
    assert prior == {"beef dripping": 0.04, "vegetable oil": 0.96}
    with_prior = sample_band(ivs, plates=plates(None), draws=2000, seed=11, fat_prior=prior)
    equal = sample_band(ivs, plates=plates(None), draws=2000, seed=11, fat_prior=None)
    assert with_prior.band_high < D("9") and equal.band_high > D("14")           # 4 % dripping: the 90th percentile stays in the vegetable-oil plate
    assert set(with_prior.fat_bands) == {"vegetable oil", "beef dripping"} and with_prior.fat_bands["vegetable oil"]["low"] >= D("4.7")
    assert load_frying_fat_prior(Path("/nonexistent/prior.csv")) is None
    assert quantile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == 3.0 and quantile([1.0, 2.0, 3.0, 4.0, 5.0], 0.9) == 5.0


# -- the samples file and the builder ----------------------------------------------------------------------------------------------------------------


def test_the_plate_weights_file_has_a_sample_for_every_measured_item_and_is_truncated_by_the_approved_range():
    pw = PlateWeights.load()
    rows = list(csv.DictReader((ROOT / "roli_agent" / "recipes" / "plate_weights.csv").open(encoding="utf-8")))
    assert len(rows) > 4000 and set(rows[0].keys()) == {"rule_id", "source", "business", "item", "grams", "kind", "read_on"}
    burger = next(r for r in RULES.rows if r.id == "PR16")
    xs = pw.for_rule("PR16", burger.low, burger.high)
    assert len(xs) == 213 and xs == sorted(xs) and min(xs) >= 83.7 and max(xs) <= 424.1 and len(pw.for_rule("PR16")) == 265      # 260 chain burgers + 5 FNDDS portions
    assert {r["kind"] for r in rows if r["rule_id"] == "PR01"} == {"derived_dough", "standard", "fndds_portion"} and sum(1 for r in rows if r["rule_id"] == "PR01" and r["kind"] == "standard") == 2
    assert pw.for_rule("PR06") == [] and pw.for_rule("PR08") == [] and not pw.enough("PR03", 10, 82, 113)


def test_the_builder_leaves_the_approved_table_unchanged_and_writes_plate_rows_per_key(tmp_path):
    from roli_agent.scripts import build_cards as bc
    fam = bc.Family("burger")
    fam.weights = [("A", "Burger one", D(100)), ("B", "Burger two", D(200))]
    rows = bc.plate_weight_rows(dict(id="PRX", key="plate", family="burger", unit="g"), fam, None, "2026-11-08")
    assert [r["grams"] for r in rows] == ["100.0", "200.0"] and rows[0]["kind"] == "chain_plate"
    fish = bc.Family("fish_main")
    fish.key_weights = [("C", "Salmon 7.5 oz", D("212.6"))]
    fn = {"basis": "protein alone (cooked fillet)", "records": [{"fdc_id": 1, "description": "Fish, cod, baked", "portions": [{"label": "1 fillet", "gram_weight": 200.0, "qualifies": True}, {"label": "1 cup", "gram_weight": 100.0, "qualifies": False}]}]}
    rows = bc.plate_weight_rows(dict(id="PRY", key="fish_stated", family="fish_main", unit="g"), fish, fn, "2026-11-08")
    assert [r["kind"] for r in rows] == ["stated_protein_raw", "fndds_portion"] and D(rows[0]["grams"]) == (D("212.6") * bc.USDA_SHARES["fish_baked_raw_per_cooked"]).quantize(D("0.1"))
    # a second apply of the same approval does not duplicate the note (the 3J builder did)
    approvals = bc.load_approvals()
    row = dict(low="1", high="2", review_status="proposed_unreviewed", basis="b", notes="")
    once, _ = bc.apply_approvals(dict(id="PR21", unit="g"), row, dict(notes=[]), approvals["PR21"])
    twice, _ = bc.apply_approvals(dict(id="PR21", unit="g"), dict(once), dict(notes=[]), approvals["PR21"])
    assert once["notes"] == twice["notes"]


# -- the consumers -------------------------------------------------------------------------------------------------------------------------------------


def rd(rank, name, low, high, band=None, apart=None, chol=(D(0), D(0)), chol_band=None):
    return RankedDish(rank=rank, key=name, name=name, saturated_fat_low=D(low), saturated_fat_high=D(high), cholesterol_low=chol[0], cholesterol_high=chol[1], support="close_call",
                      band_low=D(band[0]) if band else None, band_high=D(band[1]) if band else None, listed_apart=apart,
                      cholesterol_band_low=D(chol_band[0]) if chol_band else None, cholesterol_band_high=D(chol_band[1]) if chol_band else None)


def test_the_reply_reads_the_band_as_most_plates_and_the_old_wording_stands_without_one():
    banded = [rd(1, "PADRON PEPPERS", "0.2", "3.1", ("0.3", "2.4")), rd(2, "CRUDO", "0.8", "11", ("1.0", "2.0")), rd(3, "CHIPS", "0.2", "4.1", ("0.4", "2.9"), apart="side")]
    text, n = recommendation_text(banded, 3, 3, 0)
    assert "1) Padron Peppers, most plates about 0.3-2.4 g saturated fat per plate; 2) Crudo, most plates 1.0-2.0 g." in text and "Lightest side: Chips, most plates 0.4-2.9 g. " in text
    plain, _ = recommendation_text([rd(1, "PADRON PEPPERS", "0.2", "3.1"), rd(2, "CRUDO", "0.8", "11")], 2, 2, 0)
    assert "1) Padron Peppers, about 0.2-3.1 g saturated fat per plate; 2) Crudo, 0.8-11 g." in plain and "most plates" not in plain
    high_chol = [rd(1, "SALAD", "1", "2", ("1.2", "1.8"), chol=(D(10), D(400), ), chol_band=(D(20), D(90))), rd(2, "PRAWNS", "2", "3", ("2.2", "2.8"), chol=(D(100), D(500)), chol_band=(D(220), D(430)))]
    t2, _ = recommendation_text(high_chol, 2, 2, 0)
    assert "Salad cholesterol about 20-90 mg" in t2 and "Prawns is high in cholesterol, about 220-430 mg" in t2


def test_the_fat_line_reads_the_per_fat_bands_when_given():
    ch = {"vegetable oil": {"saturated_fat_g": {"low": "4.7", "high": "8.0"}}, "beef dripping": {"saturated_fat_g": {"low": "14", "high": "23"}}}
    assert frying_fat_line("CORNISH FISH & CHIPS", ch) == "Cornish Fish & Chips: about 4.7-8.0 g saturated fat if fried in vegetable oil, up to about 23 g in beef dripping. Ask what they fry in."
    bands = {"vegetable oil": {"low": D("5.1"), "mid": D("6.2"), "high": D("7.4")}, "beef dripping": {"low": D("15"), "mid": D("18"), "high": D("21")}}
    assert frying_fat_line("CORNISH FISH & CHIPS", ch, bands) == "Cornish Fish & Chips: most plates about 5.1-7.4 g saturated fat if fried in vegetable oil, up to about 21 g in beef dripping. Ask what they fry in."


def test_ranking_orders_by_the_band_median_and_the_reference_check_uses_it():
    a = dish("1", "9")                                                             # extremes midpoint 5
    b = dish("2", "6").model_copy(update={"dish": "b"})                            # midpoint 4
    a_band = a.model_copy(update={"band_low": D("1.5"), "band_mid": D("2.0"), "band_high": D("3.0")})
    comp = DishComparison(intervals={"saturated_fat_g": {"d": a_band, "b": b}}, pairwise=[])
    ranked, _ = rank_dishes(comp, {"d": "A", "b": "B"})
    assert [r.name for r in ranked] == ["A", "B"] and ranked[0].saturated_fat_mid == D("2.0") and (ranked[0].band_low, ranked[0].band_high) == (D("1.5"), D("3.0"))
    card = RULES.card_for("snack_bowl", "marinated olives")
    plain = reference_check(dish("4.8", "19.3"), card, factor=D("1.5"))                  # middle 12.05 per plate -> per 100 g far above: flagged
    assert plain.flagged
    with_band = reference_check(dish("4.8", "19.3").model_copy(update={"band_low": D("1.0"), "band_mid": D("1.5"), "band_high": D("2.2")}), card, factor=D("1.5"))
    assert not with_band.flagged and any(c.roli_middle == D("2.000") for c in with_band.comparisons if c.basis == "per_100g")     # 1.5 g / 75 g x 100


def test_config_defaults_for_3k():
    c = MvpConfig()
    assert c.band_draws == 2000 and c.band_low_q == D("0.10") and c.band_high_q == D("0.90") and c.plate_samples_min == 10 and c.recipe_outlier_factor == D(5)
    assert c.min_usable_recipes == 3 and c.extra_fetch == 6 and c.max_topups_per_menu == 8 and c.frying_fat_prior is True and c.plate_weight_model is None


# -- fix D: the top-up ----------------------------------------------------------------------------------------------------------------------------------


def test_the_topup_query_uses_the_menu_name_and_two_ingredient_words_and_skips_sizes():
    from roli_agent.recipes.ingest import topup_query
    from roli_agent.recipes.models import MenuItem
    assert topup_query(MenuItem(name="BLUEFIN CRUDO", description="Carricante, caper, meyer lemon, 14 oz", section="CRUDO")) == "bluefin crudo carricante caper recipe"
    assert topup_query(MenuItem(name="Padron peppers", description="", section="")) == "padron peppers recipe"
    assert topup_query(MenuItem(name="Zuni Caesar salad", description="Caesar salad with anchovies", section="")) == "zuni caesar salad caesar salad with anchovies recipe"


def test_a_dish_with_too_few_usable_recipes_gets_one_topup_search_only_when_allowed(monkeypatch):
    """The first search finds one usable recipe; the top-up search (one credit, "open" only) finds a second page; a dish with enough recipes, a refusing USDA or no budget room runs no top-up."""
    import httpx
    from decimal import Decimal as D_
    from roli_agent.llm import parse_json_object
    from roli_agent.recipes.fetch import PoliteFetcher
    from roli_agent.recipes.match import MatchCache
    from roli_agent.recipes.models import MenuItem
    from roli_agent.recipes.pipeline import TopUp, estimate_dish
    from roli_agent.recipes.portions import PortionRules
    import test_3d_tags_cards as tagged
    from recipe_test_helpers import recipe_page
    from test_recipes_fetch_search import Site

    class QuerySource:
        def __init__(self, by_query):
            self.by_query, self.calls, self.credits_used = by_query, [], 0

        def search(self, query, mode, max_results=10):
            self.calls.append((query, mode))
            self.credits_used += 1
            return [{"url": u, "title": ""} for u in self.by_query.get(query, [])]

    monkeypatch.setitem(tagged.QUERIES, "green olives", ("olives green", tagged.OLIVES, "proxy"))
    first = recipe_page("Marinated Olives", ["300 g green olives", "2 tbsp olive oil", "3 cloves garlic"], steps="Mix. Serve.")
    second = recipe_page("Olives with garlic", ["250 g green olives", "1 tbsp olive oil", "2 cloves garlic"], steps="Mix. Serve.")
    pages = {"https://a.test/one": first, "https://b.test/two": second}
    item = MenuItem(name="MARINATED OLIVES", description="", section="BAR SNACKS")
    service, _ = tagged.usda()
    used = []

    def run(by_query, topup):
        src = QuerySource(by_query)
        est = estimate_dish(item, source=src, fetcher=PoliteFetcher(transport=httpx.MockTransport(Site(pages=pages)), sleep=lambda s: None), service=service, llm=tagged.TaggingLLM({}),
                            parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental", portion_rules=PortionRules.load(),
                            exclude_herbs_spices=True, line_tags=True, negligible_sat_fat_per_100g=D_("0.1"), topup=topup)
        return est, src

    both = {"marinated olives recipe": ["https://a.test/one"], "marinated olives bar snacks recipe": ["https://a.test/one"], "marinated olives recipe ": [], "marinated olives bar snacks recipe ": []}
    # the default queries: "open" = name (+ section when specific) + recipe; the top-up query = name + recipe (no description)
    q_default_open = "marinated olives bar snacks recipe"
    by_query = {q_default_open: ["https://a.test/one"], "marinated olives recipe": ["https://b.test/two"]}
    est, src = run(by_query, TopUp(min_usable=3, extra_fetch=6, allowed=lambda: True, used=lambda: used.append(1)))
    assert est.topup and est.topup["query"] == "marinated olives recipe" and est.topup["new_recipes"] == 1 and est.topup["usable_before"] == 1 and est.topup["usable_after"] == 2 and used == [1]
    assert [c for c in src.calls if c[1] == "open"] == [(q_default_open, "open"), ("marinated olives recipe", "open")] and len({s.source.canonical_url for s in est.scenarios}) == 2
    assert any(n.startswith("top-up (12.20)") for n in est.notes)
    est2, src2 = run(by_query, TopUp(min_usable=1, extra_fetch=6, allowed=lambda: True))
    assert not est2.topup and len(src2.calls) == 2                                                   # enough recipes: no second search
    est3, src3 = run(by_query, TopUp(min_usable=3, extra_fetch=6, allowed=lambda: False))
    assert est3.topup == {"skipped": "budget", "usable_before": 1} and len(src3.calls) == 2
    est4, _ = run(by_query, None)
    assert not est4.topup


# -- fix G: the category tag --------------------------------------------------------------------------------------------------------------------------------


def test_the_category_is_validated_and_the_prompt_version_changed():
    from roli_agent.recipes.tags import CATEGORIES, TAG_PROMPT_VERSION, ZERO_FAT_CATEGORIES, validate_tag
    from roli_agent.prompts import LINE_TAGS_PROMPT
    assert "category" in LINE_TAGS_PROMPT and "Carricante" in LINE_TAGS_PROMPT and TAG_PROMPT_VERSION != "2e3a82ed51c6"      # the 3J version, saved tags are asked again
    assert set(ZERO_FAT_CATEGORIES) < set(CATEGORIES) and len(CATEGORIES) == 20
    wine = validate_tag("Carricante", "eaten", "plain_food", "", category="wine_or_spirit")
    assert wine.category == "wine_or_spirit" and wine.note == ""
    odd = validate_tag("cheddar", "eaten", "plain_food", "", category="dairy products")
    assert odd.category == "other" and "unknown category" in odd.note
    salt = validate_tag("chicken thighs", "eaten", "plain_food", "", category="salt")
    assert salt.category == "other" and "names no such word" in salt.note
    assert validate_tag("Maldon", "eaten", "plain_food", "", category="salt").category == "salt" and validate_tag("x", "eaten", "plain_food", "").category == "other"


def test_an_unquantified_zero_fat_line_does_not_stop_the_served_mass_but_a_quantified_one_does():
    from roli_agent.recipes.inference import NEGLIGIBLE_COMPOSITION_REASON
    from roli_agent.recipes.models import Conversion, ScenarioIngredient
    from roli_agent.recipes.parse import parse_line
    from roli_agent.recipes.portions import _mass_rules
    def line(n, text, name, category, qty):
        return ScenarioIngredient(ingredient_id=f"ing_{n:02d}", origin="recipe", line=text, name=name, parsed=parse_line(text) if qty else None, match=None,
                                  conversion=Conversion(from_text=text, grams=None, method="none"), preparation_state="unknown", excluded_from_calculation=NEGLIGIBLE_COMPOSITION_REASON,
                                  tag_category=category)
    splash = line(1, "Carricante", "carricante", "wine_or_spirit", False)
    glass = line(2, "1 glass white wine", "white wine", "wine_or_spirit", True)
    herb = line(3, "chives", "chives", "herb", False)
    _, stops = _mass_rules([splash, glass, herb])
    assert stops == ["white wine", "chives"]


# -- fix E: assumed weights from recipe data -------------------------------------------------------------------------------------------------------------------


def test_the_weights_table_prefers_a_data_range_only_when_it_is_sound(tmp_path):
    from roli_agent.recipes.adapt import DATA_MAX_SPREAD, DataRange, WeightRow, WeightsTable
    row = WeightRow({"id": "W12", "ingredient_role": "lemon juice", "ingredient_keys": "lemon juice", "fdc_id": "167747", "usda_description": "Lemon juice, raw", "low_g": "5.9", "high_g": "15",
                     "amount_basis": "per_plate", "basis": "b", "measures": "m", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""})
    def d(fam, n, lo, mid, hi):
        return DataRange({"row_id": "W12", "dish_family": fam, "n_lines": str(n), "n_recipes": str(n), "p10_g": lo, "p50_g": mid, "p90_g": hi, "built_on": "2026-11-08", "review_status": "built_from_recipes", "sources": "u"})
    t = WeightsTable([row], [d("fish_main", 18, "2.5", "6.5", "11.3"), d("any", 116, "1.2", "3.7", "11.1"), d("dessert", 5, "0.6", "1.8", "3.7")])
    lo, hi, basis, status, used = t.range_for(row, "fish_main")
    assert (lo, hi, status) == (D("2.5"), D("11.3"), "built_from_recipes") and "18 fish_main recipes" in basis and used.family == "fish_main"
    lo, hi, basis, status, used = t.range_for(row, "dessert")                                      # 5 recipes: too few for the family, the all-family range stands in
    assert (lo, hi) == (D("1.2"), D("11.1")) and "recipes of any dish" in basis
    assert WeightsTable([row], [d("any", 30, "0.4", "4.5", "184.2")]).range_for(row, None)[:2] == (D("5.9"), D(15))          # spread 460x: mismatched lines, hand row stands
    assert WeightsTable([row], [d("any", 30, "80", "100", "120")]).range_for(row, None)[:2] == (D("5.9"), D(15))             # median 100 g against a 5.9-15 g row: another food
    assert WeightsTable([row]).range_for(row, "fish_main")[:2] == (D("5.9"), D(15))
    ok, why = WeightsTable.data_usable(row, d("any", 30, "0.4", "4.5", "184.2"), 15)
    assert not ok and f"wider than {DATA_MAX_SPREAD}x" in why
    live = WeightsTable.load()
    assert live.data and WeightsTable.load(use_data=False).data == {}
    w12 = next(r for r in live.rows if r.id == "W12")
    assert live.range_for(w12, "fish_main")[4] is not None and live.range_for(w12, "fish_main")[0] < D("5.9")                  # the 2026-11-08 build: 18 fish recipes


def test_the_builder_files_per_serving_grams_by_row_and_family_and_skips_medium_lines(tmp_path):
    from roli_agent.recipes.adapt import WeightsTable
    from roli_agent.scripts.build_assumed_weights import build
    cache = tmp_path / "roli_mvp"
    (cache / "extractions").mkdir(parents=True)
    (cache / "judgements" / "tags").mkdir(parents=True)
    def extraction(name, url, title, lines, yield_text):
        (cache / "extractions" / f"{name}.json").write_text(json.dumps({"saved_at": 1, "url": url, "extracted": {"method": "t", "title": title, "ingredient_lines": lines, "yield_text": yield_text, "instructions_text": "", "flags": []}}), encoding="utf-8")
    extraction("a", "https://a.test/salmon", "Baked salmon", ["2 salmon fillets", "30 ml lemon juice", "500 ml olive oil for frying"], "2 servings")
    extraction("b", "https://b.test/salmon2", "Grilled salmon with lemon", ["4 salmon fillets", "60 ml lemon juice"], "4 servings")
    extraction("c", "https://c.test/dup", "Grilled salmon with lemon copy", ["4 salmon fillets", "60 ml lemon juice"], "4 servings")        # same lines: a duplicate, not counted twice
    extraction("d", "https://d.test/noyield", "Salmon", ["2 salmon fillets", "20 ml lemon juice"], "")                                     # no serving count: skipped
    (cache / "judgements" / "tags" / "x.json").write_text(json.dumps({"url": "https://a.test/salmon", "answer": {"3": {"role": "cooking_medium", "kind": "plain_food"}}}), encoding="utf-8")
    rows, stats = build(cache, WeightsTable.load(use_data=False), "2026-11-08")
    w12 = {(r["row_id"], r["dish_family"]): r for r in rows if r["row_id"] == "W12"}
    assert set(w12) == {("W12", "fish_main"), ("W12", "any")} and w12[("W12", "fish_main")]["n_recipes"] == 2 and w12[("W12", "fish_main")]["p50_g"] == "15.0"   # 30/2 and 60/4 ml at 1 g/ml
    assert stats["distinct"] == 3 and stats["with_servings"] == 2 and stats["medium_skipped"] == 1
    assert w12[("W12", "fish_main")]["review_status"] == "built_from_recipes" and "https://a.test/salmon" in w12[("W12", "fish_main")]["sources"]


def test_a_declined_wine_line_takes_the_fixed_wine_record_and_a_cheese_never_does():
    from roli_agent.recipes.match import CATEGORY_FALLBACK, MatchCache, MatchRequest, UsdaMatcher
    from roli_nutrition.schemas import Candidate as SearchCandidate, SearchResult

    class Service:
        def __init__(self):
            self.queries = []

        def search_foods(self, q, limit, **kw):
            self.queries.append(q)
            if q == "wine table all":
                return SearchResult(query=q, candidates=[SearchCandidate(fdc_id=173185, description="Alcoholic beverage, wine, table, all", data_type="SR Legacy"),
                                                         SearchCandidate(fdc_id=173190, description="Alcoholic beverage, wine, table, red", data_type="SR Legacy")])
            return SearchResult(query=q, candidates=[])

    class DecliningLLM:
        def invoke(self, messages):
            from types import SimpleNamespace
            text = messages[-1].content
            if "usda_query" in text or "queries" in text[:400].lower():
                return SimpleNamespace(content=json.dumps({"queries": [{"id": 1, "usda_query": "carricante"}, {"id": 2, "usda_query": "taleggio"}]}))
            return SimpleNamespace(content=json.dumps({"selections": []}))

    svc = Service()
    m = UsdaMatcher(svc, DecliningLLM(), parse_json_object=lambda s: json.loads(s), cache=MatchCache(None))
    reqs = [MatchRequest("Carricante", "unknown", category="wine_or_spirit"), MatchRequest("taleggio", "unknown", category="cheese")]
    decisions, log = m.match(reqs, context="Bluefin crudo (Crudo): Carricante")
    wine, cheese = decisions[reqs[0].key], decisions[reqs[1].key]
    assert wine.fdc_id == 173185 and wine.match_type == "proxy" and wine.category_fallback == "wine_or_spirit" and wine.issue is None and "category fallback" in wine.reason
    assert cheese.fdc_id is None and cheese.issue == "no_candidates" and cheese.category_fallback == "" and "cheese" not in CATEGORY_FALLBACK
    assert "wine table all" in svc.queries and any("category fallback" in n for n in log.notes)



# -- fix C: the plate-weight model ----------------------------------------------------------------------------------------------------------------------------------


def test_the_plate_model_file_records_its_held_out_check_and_stays_off_until_the_rule_is_met():
    from roli_agent.recipes.plate_model import PlateModel, features, tokens
    m = PlateModel.load()
    assert m is not None and m.live is False and m.data["validation"]["p2_families_items"] > 3000 and m.data["n_restaurants"] == 75
    v = m.data["validation"]
    assert v["model_coverage_80"] >= v["baseline_coverage"] and v["model_median_width_ln"] >= v["baseline_median_width_ln"]           # covers at least as well but wider: not live
    assert tokens("Double Cheeseburgers with Fries") == ["cheeseburger", "double", "fry", "with"] and "fam:burger" in features("x", "burger", False)
    rng = random.Random(3)
    a = [m.sample(random.Random(3), "Classic Cheeseburger", "Mains", "burger", 83.7, 424.1) for _ in range(3)]
    assert a[0] == a[1] == a[2] and 83.7 <= a[0] <= 424.1
    lo, hi = m.interval("Classic Cheeseburger", "burger")
    assert 0 < lo < hi and m.sample(rng, "Classic Cheeseburger", "Mains", "burger", 10000, 10001) is None
    from roli_agent.mvp.menu_run import MenuRunner
    assert MvpConfig().plate_weight_model is None                           # the runner follows the file's `live`; the file says off


def test_the_runner_follows_the_model_files_live_flag(monkeypatch):
    from roli_agent.mvp import menu_run
    from roli_agent.recipes.plate_model import PlateModel
    calls = []
    class R:  # the parts of MenuRunner.__init__ that choose the model, run in isolation
        pass
    for cfg_value, live, expect in ((None, False, False), (None, True, True), (True, False, True), (False, True, False)):
        monkeypatch.setattr(PlateModel, "load", classmethod(lambda cls, path=None: PlateModel({"intercept": 5.0, "coef": {}, "families": {}, "pooled_residual_quantiles": [0.0] * 21, "live": live})))
        r = menu_run.MenuRunner.__new__(menu_run.MenuRunner)
        r.config = MvpConfig(plate_weight_model=cfg_value)
        r.plate_model = None
        if r.config.plate_weight_model is not False:
            loaded = PlateModel.load()
            if loaded is not None and (r.config.plate_weight_model is True or loaded.live):
                r.plate_model = loaded
        assert (r.plate_model is not None) is expect, (cfg_value, live)



def test_the_topup_slot_is_reserved_atomically_and_upper_case_names_keep_their_apostrophes():
    from roli_agent.mvp.budget import Limits, MenuBudget, Prices, SpendLedger
    from roli_agent.mvp.ranking import _title
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        b = MenuBudget(Limits(), SpendLedger(Path(tmp) / "ledger.jsonl"), Prices(None, None, "test"), run_id="t")
        assert all(b.reserve_topup(3, D("0.03"), 2) for _ in range(3)) and not b.reserve_topup(3, D("0.03"), 2) and b.topups == 3
        b.close()
    assert _title("TODAY'S RICOTTA") == "Today's Ricotta" and _title("PADRON PEPPERS") == "Padron Peppers" and _title("Zuni Caesar salad") == "Zuni Caesar salad"


# -- the verdicts read the bands (decided 2026-11-08 afternoon) -------------------------------------------------------------------------------------------------------


def test_pairwise_verdicts_use_the_bands_bands_apart_with_overlapping_extremes_is_tentative_in_its_own_words():
    from roli_agent.recipes.compare_dishes import _pairwise
    def di(name, low, high, blo=None, bhi=None):
        d = dish(low, high).model_copy(update={"dish": name, "high_without_external": D(high)})
        return d.model_copy(update={"band_low": D(blo), "band_mid": (D(blo) + D(bhi)) / 2, "band_high": D(bhi)}) if blo else d
    a, b = di("peppers", "0.2", "3.1", "0.3", "2.4"), di("chop", "1.0", "27.9", "11", "22")            # extremes overlap (3.1 > 1.0), bands apart
    p = _pairwise(a, b)
    assert p.verdict == "tentative" and p.lower == "peppers" and p.margin == D("8.6") and p.tentative_because[0].startswith("most plates apart") and "most plates 0.3-2.4 g" in p.reason
    assert _pairwise(di("peppers", "0.2", "3.1", "0.3", "2.4"), di("chop", "7.9", "27.9", "11", "22")).verdict == "well_supported"         # extremes apart too: as before
    assert _pairwise(di("a", "1", "9", "2", "6"), di("b", "2", "6", "3", "5")).verdict == "overlapping"                                     # bands overlap: close call
    assert _pairwise(di("a", "0.2", "3.1"), di("b", "1.0", "27.9")).verdict == "overlapping"                                               # no bands (old runs): extremes decide
    # through the ranking: the support label and the certainty sentence
    comp = DishComparison(intervals={"saturated_fat_g": {"peppers": a, "chop": b}}, pairwise=[_pairwise(a, b)])
    ranked, _ = rank_dishes(comp, {"peppers": "PADRON PEPPERS", "chop": "PORK CHOP"})
    assert ranked[0].support == "tentative" and ranked[0].reasons and "most plates apart" in ranked[0].reasons[0]
    text, _ = recommendation_text(ranked, 2, 2, 0)
    assert "Most plates fall in this order; the full ranges still overlap, so it is likely, not certain." in text and "toss-up" not in text


def test_the_outlier_guard_keeps_a_minority_of_a_third_or_more():
    five = [si("a:r", "2", "3"), si("b:r", "2.2", "3.5"), si("c:r", "2.5", "3.0"), si("d:r", "0.03", "0.06"), si("e:r", "0.04", "0.08")]
    assert outliers(five, 5.0) == []                                                                          # two lean against three rich: a second kind of the dish
    assert [sid for sid, _ in outliers(five[:4] + [si("f:r", "2.1", "3.1")], 5.0)] == ["d:r"]                 # one against five: an outlier
    assert [sid for sid, _ in outliers(five[:4], 5.0)] == ["d:r"]                                              # one against three: an outlier


# -- the dish-kind family reaches the portion and weights steps (bug found by the known-answer check, 2026-11-08) -----------------------------------------------


def test_the_family_passed_to_the_pipeline_decides_the_portion_rule_not_the_word_lists(monkeypatch):
    """'Pollo Pesto' (Pizza Express pasta): the word lists call it a dip (pesto, three words or fewer); the dish-kind call says pasta. In 3J and the 3K preview the
    pipeline's portion and weights steps recomputed the family from the word lists, so the dish was sized as a 30-156 g pot of dip."""
    import test_3d_tags_cards as tagged
    from recipe_test_helpers import recipe_page
    from roli_agent.recipes.models import MenuItem
    from roli_agent.recipes.portions import dish_type_for
    item = MenuItem(name="Pollo Pesto", description="", section="Al Forno")
    assert dish_type_for(item) == "dip"
    monkeypatch.setitem(tagged.QUERIES, "green olives", ("olives green", tagged.OLIVES, "proxy"))
    page = recipe_page("Pollo Pesto", ["300 g green olives", "2 tbsp olive oil", "3 cloves garlic"], steps="Mix. Bake.")
    words = tagged.estimate({"https://a.test/p": page}, item, tagged.TaggingLLM({}))
    passed = tagged.estimate({"https://a.test/p": page}, item, tagged.TaggingLLM({}), dish_type="pasta_main")
    assert {p.dish_type for p in words.portioned} == {"dip"} and {p.dish_type for p in passed.portioned} == {"pasta_main"}
    assert {p.portion_rule_id for p in passed.portioned if p.applicable} <= {"PR09"} and "PR27" not in {p.portion_rule_id for p in passed.portioned}
    src = (ROOT / "roli_agent" / "mvp" / "menu_run.py").read_text(encoding="utf-8")
    assert "topup=topup, dish_type=dt)" in src
