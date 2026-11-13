"""Phase 2C: menu-adapted pairs on fixture USDA records. Published scenarios byte-identical; assumptions explicit;
classes computed; approved mode rejects unapproved rows; missing nutrients stay missing; the reply never changes."""

from __future__ import annotations

import csv
import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from roli_agent.llm import parse_json_object
from roli_agent.recipes.adapt import WeightRow, WeightsTable, adapt_pairs, display_class, materiality
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.pipeline import estimate_dish
from roli_agent.responses import dish_reply

from conftest import load, make_service
from recipe_test_helpers import BLUEFIN, OLIVE, ROMANO, TOMATO, FakeSource, RuleLLM, SEARCHES, QUERIES, recipe_page, numbers_in, numbers_in_json
from test_recipes_fetch_search import Site

SALT, CHIVES, BASIL, PEPPER = 173468, 169994, 172232, 170931
D = Decimal


def table(**overrides) -> WeightsTable:
    rows = [
        {"id": "W01", "ingredient_role": "chives, garnish", "ingredient_keys": "chive, chives", "fdc_id": str(CHIVES), "usda_description": "Chives, raw",
         "low_g": "1", "high_g": "3", "basis": "usda_measure", "measures": "1 tsp chopped = 1 g; 1 tbsp chopped = 3 g", "review_status": "verified_usda_measure; restaurant usage assumed",
         "approved_by": "", "notes": ""},
        {"id": "W02", "ingredient_role": "basil leaves, garnish", "ingredient_keys": "basil, genovese basil", "fdc_id": str(BASIL), "usda_description": "Basil, fresh",
         "low_g": "2.5", "high_g": "6", "basis": "usda_measure", "measures": "5 leaves = 2.5 g", "review_status": "verified_usda_measure; restaurant usage assumed", "approved_by": "", "notes": ""},
        {"id": "W05", "ingredient_role": "grated hard cheese", "ingredient_keys": "pecorino, pecorino sardo, romano", "fdc_id": str(ROMANO), "usda_description": "Cheese, romano",
         "low_g": "5", "high_g": "15", "basis": "proposed", "measures": "1 tbsp = 5 g (USDA); 1-3 tbsp proposed", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""},
        {"id": "W09", "ingredient_role": "olive oil, drizzle", "ingredient_keys": "olive oil, oil", "fdc_id": str(OLIVE), "usda_description": "Oil, olive, salad or cooking",
         "low_g": "4.5", "high_g": "13.5", "basis": "proposed", "measures": "1 tsp = 4.5 g, 1 tbsp = 13.5 g", "review_status": "proposed_unreviewed", "approved_by": "", "notes": ""},
        {"id": "W10", "ingredient_role": "bottarga", "ingredient_keys": "bottarga", "fdc_id": "", "usda_description": "", "low_g": "3", "high_g": "10", "basis": "blocked", "measures": "",
         "review_status": "blocked_questionable_proxy", "approved_by": "", "notes": "blocked"},
        {"id": "W15", "ingredient_role": "black pepper, to taste", "ingredient_keys": "black pepper, pepper", "fdc_id": str(PEPPER), "usda_description": "Spices, pepper, black",
         "low_g": "0.1", "high_g": "2.3", "basis": "usda_measure", "measures": "1 dash = 0.1 g; 1 tsp ground = 2.3 g", "review_status": "verified_usda_measure; restaurant usage assumed", "approved_by": "", "notes": ""},
    ]
    for r in rows:
        r.update(overrides.get(r["id"], {}))
    return WeightsTable([WeightRow(r) for r in rows])


def usda():
    foods = {fid: load(f"food_{fid}") for fid in (BLUEFIN, OLIVE, ROMANO, TOMATO, SALT, CHIVES, BASIL, PEPPER)}
    searches = dict(SEARCHES, **{"salt table": [SALT], "chives raw": [CHIVES], "basil fresh": [BASIL], "spices pepper black": [PEPPER]})

    def respond(request):
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = [f for f in searches.get(q, []) if f in foods]
            return httpx.Response(200, json={"foods": [{"fdcId": f, "description": foods[f]["description"], "dataType": foods[f]["dataType"]} for f in ids]})
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=foods[fid]) if fid in foods else httpx.Response(404, content=b"")
    return make_service(respond)


CRUDO = MenuItem(name="BLUEFIN CRUDO", description="bottarga, chive, genovese basil", section="TO START")
PAGES = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "2 tablespoons extra-virgin olive oil",
                                                            "4 tomatoes", "Flaky salt, to taste", "freshly ground black pepper", "olive oil, for drizzling"])}
RESULTS = {"open": [{"url": "https://a.test/crudo", "title": "Crudo"}], "structured_hosts": []}
QUERIES2 = dict(QUERIES, **{"flaky salt": ("salt table", SALT, "direct"), "chive": ("chives raw", CHIVES, "direct"), "genovese basil": ("basil fresh", BASIL, "direct"),
                           "freshly ground black pepper": ("spices pepper black", PEPPER, "direct"), "bottarga": ("fish roe", None, "direct")})


def estimate(mode: str, tbl: WeightsTable | None = None):
    site = Site(pages=PAGES)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, rec = usda()
    est = estimate_dish(CRUDO, source=FakeSource(RESULTS), fetcher=fetcher, service=service, llm=RuleLLM(queries=QUERIES2), parse_json_object=parse_json_object,
                        match_cache=MatchCache(None), prefetch_workers=1, adapt_mode=mode, weights_table=tbl or table())
    return est, service, rec


def test_computed_classes_and_materiality_not_typed_labels():
    assert display_class(0.0, 0.0, D(6)) == "zero_nutrient"
    assert display_class(0.146, 0.0, D(3)) == "low_impact" and display_class(0.146, 0.0, D(4)) == "displayable"      # chives: 0.0044 g vs 0.0058 g
    assert display_class(1.392, 0.0, D("2.3")) == "displayable"                                                      # black pepper: 0.032 g
    assert display_class(None, 0.0, D(3)) == "nutrient_missing" and display_class(0.0, None, D(3)) == "nutrient_missing"
    assert materiality(D("0.004"), D(0)) == "negligible" and materiality(D("0.032"), D(0)) == "minor"
    assert materiality(D("0.6"), D(0)) == "moderate" and materiality(D("2.3"), D("12.9")) == "major" and materiality(None, D(0)) == "unknown"


def test_table_lookup_prefers_the_longest_key():
    t = table()
    assert t.find("pecorino sardo").id == "W05" and t.find("extra virgin olive oil").id == "W09" and t.find("freshly ground black pepper").id == "W15"
    assert t.find("chive").id == "W01" and t.find("genovese basil").id == "W02" and t.find("bottarga").id == "W10" and t.find("saku tuna") is None


def test_approved_mode_fills_only_zero_nutrient_and_record_sizes_and_publishes_nothing_else():
    est, service, _ = estimate("approved")
    assert est.adapt_mode == "approved" and est.internal_summary is not None
    (pair,) = est.adapted_pairs
    published = next(s for s in est.scenarios if s.scenario_id == pair.derived_from)
    sources = {a.name: (a.source, a.display_class, str(a.grams_low), str(a.grams_high)) for a in pair.assumptions}
    assert sources == {"flaky salt": ("zero_nutrient_nominal", "zero_nutrient", "0.4", "0.4"),
                       "tomatoes": ("record_size_labels", "displayable", "364", "728")}                     # 4 x small 91 g .. 4 x large 182 g
    reasons = {u.name: u.reason for u in pair.unfilled}
    assert reasons == {"freshly ground black pepper": "row_unapproved", "olive oil": "row_unapproved", "bottarga": "blocked_row",
                       "chive": "row_unapproved", "genovese basil": "row_unapproved"}
    assert pair.low.calculation_status == "incomplete" and pair.high.calculation_status == "incomplete"
    assert pair.servings_basis == "recipe" and pair.representativeness == "assumed" and "not a verified restaurant total" in pair.note
    # the published scenario is untouched and still incomplete
    assert published.calculation_status == "incomplete" and published.calculation["totals"]["saturated_fat_g"]["total"] is None
    salt = next(a for a in pair.assumptions if a.name == "flaky salt")
    assert salt.grams_declared is None and salt.contribution_high == {"saturated_fat_g": D(0), "cholesterol_mg": D(0)} and "USDA reports 0" in salt.basis


def test_experimental_mode_fills_table_rows_without_changing_their_status_and_stays_internal():
    est, service, _ = estimate("experimental")
    (pair,) = est.adapted_pairs
    filled = {a.name: a for a in pair.assumptions}
    assert set(filled) == {"flaky salt", "tomatoes", "freshly ground black pepper", "olive oil", "chive", "genovese basil"}
    assert [u.name for u in pair.unfilled] == ["bottarga"] and pair.unfilled[0].reason == "blocked_row"   # blocked rows are never used
    oil = filled["olive oil"]
    assert (oil.row_id, oil.review_status, str(oil.grams_low), str(oil.grams_high), oil.materiality_at_high) == ("W09", "proposed_unreviewed", "4.5", "13.5", "major")
    assert oil.note.startswith("the line's matched record 748608") or oil.note == "" or "differs" in oil.note
    pepper = filled["freshly ground black pepper"]
    # per-plate rows enter a 4-serving recipe as per-serving amounts (2D): the whole-recipe contribution is 4 x the plate's
    assert pepper.display_class == "displayable" and pepper.materiality_at_high == "minor" and pepper.contribution_high["saturated_fat_g"] == D("1.392") * D("2.3") / 100 * 4
    assert pepper.amount_basis == "per_plate"
    chives = filled["chive"]
    assert chives.gap == "G1_menu_only" and chives.display_class == "low_impact" and chives.materiality_at_high == "negligible"
    # bottarga keeps the pair incomplete; everything else is modeled
    assert pair.high.calculation_status == "incomplete" and pair.high.calculation["totals"]["cholesterol_mg"]["excludes"][0]["name"] == "bottarga"
    # sensitivity and shares are reported on the known subtotal
    assert pair.sensitivity_per_serving["saturated_fat_g"] > 0
    assert abs(pair.sensitivity_per_serving["saturated_fat_g"] - pair.sensitivity_total["saturated_fat_g"] / pair.servings) <= D("0.000001")  # per-serving values are quantised to 6 places
    assert pair.high.assumed_share["saturated_fat_g"] is not None and 0 < pair.high.assumed_share["saturated_fat_g"] < 1
    assert pair.high.assumed_share_percent["saturated_fat_g"] == int(pair.high.assumed_share["saturated_fat_g"] * 100)
    # every assumed line says so in the calculator's own assumption text
    oil_line = next(i for i in pair.high.calculation["ingredients"] if i["name"] == "olive oil")
    assert oil_line["assumption"].startswith("ASSUMED (G2_unquantified, table_row, W09, high): 13.5 g per plate") and oil_line["grams_in_recipe"] == "54.0"
    assert oil_line["grams_declared"] == "13.5" and oil_line["quantity_basis"] == "per_serving"
    # internal summary, internal wording
    s = est.internal_summary
    assert s.mode == "experimental" and s.n_pairs == 1 and s.n_lines_filled == 6 and s.unfilled_by_reason == {"blocked_row": 1}
    assert s.statement.startswith("INTERNAL (experimental)") and "not for users" in s.statement
    # the user-facing reply is byte-identical to the one without adaptation
    off, _, _ = estimate("off")
    assert dish_reply(est.model_dump(mode="json")) == dish_reply(off.model_dump(mode="json"))
    assert "ASSUMED" not in dish_reply(est.model_dump(mode="json")) and est.summary.statement == off.summary.statement


def test_published_scenarios_are_byte_identical_and_phase_2a_untouched():
    off, _, _ = estimate("off")
    exp, _, _ = estimate("experimental")
    for a, b in zip(off.scenarios, exp.scenarios):
        assert a.model_dump_json() == b.model_dump_json()
    import inspect
    import roli_nutrition.recipe.calculator as calc
    assert "adapt" not in inspect.getsource(calc)


def test_assumption_driven_warning_never_discards_and_zero_denominator_is_null():
    est, _, _ = estimate("experimental")
    (pair,) = est.adapted_pairs
    # cholesterol: the only known contributor is tuna (38 mg per 100 g); assumed lines contribute 0 mg -> share 0, not null.
    # saturated fat: the assumed drizzle (13.5 g oil) is 36 % of the known subtotal at the high bound -> the warning is set and nothing is discarded
    assert pair.high.assumed_share["cholesterol_mg"] == 0
    assert pair.high.assumption_driven and "assumption_driven" in pair.high.flags and pair.high.calculation_status == "incomplete"
    assert pair.low.assumed_share["saturated_fat_g"] < pair.high.assumed_share["saturated_fat_g"]
    # force a scenario where assumed lines dominate: a table with a huge cheese range and a recipe line for it
    big = table(W05={"high_g": "500", "low_g": "200"})
    pages = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "pecorino romano, for grating"])}
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, _ = usda()
    e2 = estimate_dish(MenuItem(name="BLUEFIN CRUDO", description="", section="TO START"), source=FakeSource(RESULTS), fetcher=fetcher, service=service,
                       llm=RuleLLM(queries=QUERIES2), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1,
                       adapt_mode="experimental", weights_table=big)
    (p2,) = e2.adapted_pairs
    assert p2.high.assumption_driven and "assumption_driven" in p2.flags and p2.high.calculation_status == "complete"
    assert p2.high.assumed_share["saturated_fat_g"] > D("0.9") and e2.internal_summary.n_complete_high == 1 and e2.internal_summary.n_assumption_driven == 1


def test_missing_nutrient_on_a_record_stays_missing_and_is_counted():
    """D23 not approved: a record without a cholesterol row stays incomplete for cholesterol in both the published and the adapted scenario."""
    evoo = load("food_748608")
    pages = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "2 tablespoons extra virgin olive oil"])}
    foods = {BLUEFIN: load(f"food_{BLUEFIN}"), 748608: evoo}

    def respond(request):
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = {"tuna bluefin raw": [BLUEFIN], "oil olive": [748608]}.get(q, [])
            return httpx.Response(200, json={"foods": [{"fdcId": f, "description": foods[f]["description"], "dataType": foods[f]["dataType"]} for f in ids]})
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=foods[fid]) if fid in foods else httpx.Response(404, content=b"")
    service, _ = make_service(respond)
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    q = dict(QUERIES2, **{"extra virgin olive oil": ("oil olive", 748608, "direct")})
    est = estimate_dish(MenuItem(name="BLUEFIN CRUDO", description="", section="TO START"), source=FakeSource(RESULTS), fetcher=fetcher, service=service,
                        llm=RuleLLM(queries=q), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental", weights_table=table())
    (sc,) = [s for s in est.scenarios if s.status == "calculated"]
    assert sc.completeness_by_nutrient == {"saturated_fat_g": True, "cholesterol_mg": False} and est.summary.n_saturated_fat_only_complete == 1
    oil = next(i for i in sc.ingredients if "olive" in i.name)
    assert oil.conversion.grams is not None and oil.blocker == "nutrient_not_reported"
    assert est.adapted_pairs == [] and est.internal_summary.unfilled_by_reason == {"no_pair:nutrient_not_reported": 1}


def test_the_generated_table_loads_and_has_no_approvals_and_three_blocked_rows():
    t = WeightsTable.load()
    assert len(t.rows) == 63 and all(r.approved_by == "" for r in t.rows)                 # 34 + the Phase 3 category-default rows W30-W55 + the 3E rows W56, W57
    assert sorted(r.id for r in t.rows if r.blocked) == ["W03b", "W10", "W20", "W28"]
    # 2D: the evidence-backed experimental rows sit beside the blocked ones; a usable row wins a key tie, a blocked row stays blocked
    assert t.find("muscat grape").id == "W11" and t.find("toasted sesame").id == "W07" and t.find("shiso").id == "W03c" and t.find("bottarga").id == "W10"
    assert t.find("heads little gem lettuce").id == "W28b" and t.find("shishito").id == "W20b"
    assert {r.id: r.amount_basis for r in t.rows if r.id in ("W25", "W28b", "W20b", "W09")} == {"W25": "per_count_unit", "W28b": "per_count_unit", "W20b": "per_plate", "W09": "per_plate"}
    assert all(r.review_status.startswith("proposed_from_evidence_2c1") for r in t.rows if r.id in ("W28b", "W20b", "W03c"))
    rows = {r.id: r for r in t.rows}
    assert rows["W03a"].fdc_id == 173475 and rows["W04b"].fdc_id == 169997 and rows["W04a"].fdc_id == 170416
    # Phase 3 category defaults: experimental only, composition proxies flagged, dish-typed rows apply only to their dish types
    assert all(r.review_status.startswith("proposed_unreviewed; category default") and r.usable("approved") == (False, "row_unapproved") for r in t.rows if r.id >= "W30" and r.id <= "W40")
    assert t.find("caciocavallo", "pasta_main").id == "W31" and t.find("caciocavallo", "pizza_neapolitan").id == "W32" and t.find("caciocavallo") is None
    assert t.find("burrata").id == "W30" and t.find("ricotta salata").id == "W34" and t.find("ricotta").id == "W36" and t.find("pecorino romano").id == "W05"
    assert t.find("'nduja").id == "W38" and t.find("prosciutto di parma").id == "W37" and t.find("lemon vinaigrette", "leaf_salad_starter").id == "W39" and t.find("aioli").id == "W40"
    assert t.find("bacon").id == "W26" and t.find("vegetable oil for frying") is None and t.find("peppercorn sauce") is None       # frying oil and butter sauces stay open
    assert t.find("ROASTED PEPPERS").id == "W48" and t.find("freshly ground black pepper").id == "W15" and t.find("pepper").id == "W15"   # exclude_pattern: vegetable peppers are not black pepper
    assert t.find("padron peppers") is None or t.find("padron peppers").id != "W15"
    assert t.find("WATERMELON").id == "W42" and t.find("FETTA").id == "W34" and t.find("mint almond").id == "W41" and t.find("chanterelle") is None


def test_compound_salt_and_pepper_line_is_not_a_zero_nutrient_fill():
    pages = {"https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "kosher salt and freshly ground black pepper"])}
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, _ = usda()
    q = dict(QUERIES2, **{"kosher salt and freshly ground black pepper": ("salt table", SALT, "direct")})
    est = estimate_dish(MenuItem(name="BLUEFIN CRUDO", description="", section="TO START"), source=FakeSource(RESULTS), fetcher=fetcher, service=service,
                        llm=RuleLLM(queries=q), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental", weights_table=table())
    (pair,) = est.adapted_pairs
    (a,) = pair.assumptions
    assert a.source == "table_row" and a.row_id == "W15" and a.display_class == "displayable"     # the pepper row, not a nominal salt weight
    assert a.note.startswith("the line's matched record 173468 differs")


def test_generated_keys_do_not_catch_unrelated_lines():
    t = WeightsTable.load()
    assert t.find("fresh lemon thyme") is None and t.find("canola or safflower oil") is None
    assert t.find("grated zest of 1 small lemon").id == "W13" and t.find("juice of lemon").id == "W12" and t.find("extra-virgin olive oil").id == "W09"
