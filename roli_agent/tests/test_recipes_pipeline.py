"""2B-2 end to end on a fake web, the saved real USDA records and a rule-driven LLM: menu item -> DishEstimate -> reply.

Covers spec 2B section 13: omission (bottarga), proxies, incomplete estimates, relevance rejection, reliability, the
reply-number guard, and the D5 measurement of scenarios blocked only by seasonings.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal

import httpx
import pytest

from roli_agent.graph import build_graph, run_roli
from roli_agent.llm import parse_json_object
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.pipeline import estimate_dish

from recipe_test_helpers import BLUEFIN, OLIVE, ROMANO, TOMATO, FakeSource, RuleLLM, make_usda, numbers_in, numbers_in_json, recipe_page
from test_recipes_fetch_search import Site

CRUDO = MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START")
TOMATOES = MenuItem(name="HEIRLOOM TOMATOES", description="tomatoes, sourdough", section="TO START")

CRUDO_PAGES = {
    "https://a.test/crudo": recipe_page("Tuna Crudo", ["85 g sushi-grade bluefin tuna, thinly sliced", "2 tablespoons extra-virgin olive oil", "Flaky salt, to taste"]),
    "https://b.test/seared": recipe_page("Seared Tuna Steaks", ["2 (6-ounce) bluefin tuna steaks", "1 tablespoon olive oil"], steps="Sear the tuna 2 minutes per side."),
    "https://c.test/spaghetti": recipe_page("Spaghetti with bottarga sauce", ["200 g spaghetti", "40 g bottarga", "2 tablespoons olive oil"]),
    "https://d.test/tartare": recipe_page("Tuna Tartare", ["200 g bluefin tuna, diced", "1 tablespoon olive oil"], yield_text=""),
}
CRUDO_RESULTS = {"open": [{"url": u, "title": t} for u, t in [("https://a.test/crudo", "Crudo"), ("https://b.test/seared", "Seared"),
                                                                ("https://c.test/spaghetti", "Spaghetti"), ("https://d.test/tartare", "Tartare")]],
                 "structured_hosts": []}

TOMATO_PAGES = {
    "https://f.test/salad": recipe_page("Heirloom Tomato Salad", ["4 ripe plum tomatoes, cut into thin rounds", "2 tablespoons extra-virgin olive oil",
                                                                  "2 slices sourdough bread, torn", "1 oz pecorino romano, grated"]),
    "https://g.test/salad-salt": recipe_page("Tomato and Bread Salad", ["3 medium heirloom tomatoes", "1 tablespoon olive oil", "2 slices sourdough bread", "Salt, to taste"]),
    "https://h.test/burrata": recipe_page("Tomatoes with Burrata and Sourdough", ["2 large heirloom tomatoes", "8 oz burrata", "2 slices sourdough bread"]),
    "https://i.test/panzanella": recipe_page("Panzanella with Heirloom Tomatoes", ["6 ripe plum tomatoes", "3 tablespoons olive oil", "4 slices sourdough bread"],
                                             yield_text="6 servings"),
}
TOMATO_RESULTS = {"open": [{"url": u, "title": ""} for u in TOMATO_PAGES], "structured_hosts": []}


def run(item, pages, results, grades=None, searches=None, max_scenarios=4, llm=None, match_cache=None):
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, rec = make_usda(searches)
    llm = llm or RuleLLM(grades=grades or {})
    estimate = estimate_dish(item, source=FakeSource(results), fetcher=fetcher, service=service, llm=llm, parse_json_object=parse_json_object,
                             max_scenarios=max_scenarios, match_cache=match_cache or MatchCache(None), prefetch_workers=1)
    return estimate, llm, rec


def by_title(estimate, title):
    return next(s for s in estimate.scenarios if s.source.title == title)


# -- the crudo: omission, gate, hard exclusion, D15 -------------------------------------------------------


def test_crudo_bottarga_never_vanishes_and_no_total_is_stated():
    est, llm, rec = run(CRUDO, CRUDO_PAGES, CRUDO_RESULTS, grades={"Tuna Tartare": ("same", "similar", "different")})
    crudo = by_title(est, "Tuna Crudo")
    assert crudo.relevance.gate == "passed" and crudo.relevance.grade == "high" and crudo.status == "calculated"
    assert crudo.relevance.menu_missing == ["bottarga", "muscat grape", "chive"]
    menu_only = [i for i in crudo.ingredients if i.origin == "menu_only"]
    assert [i.name for i in menu_only] == ["bottarga", "muscat grape", "chive"] and all(i.conversion.grams is None for i in menu_only)
    assert crudo.calculation_status == "incomplete" and crudo.eligible_for_range is False
    assert "bottarga" in crudo.ineligible_reason
    calc = crudo.calculation
    assert calc["totals"]["saturated_fat_g"]["total"] is None                      # Phase 2A: a partial subtotal is never a total
    tuna = next(i for i in calc["ingredients"] if i["name"] == "sushi-grade bluefin tuna")
    assert tuna["usda"]["fdc_id"] == BLUEFIN and tuna["preparation_state"] == "raw" and tuna["grams_in_recipe"] == "85"
    oil = next(i for i in calc["ingredients"] if "olive oil" in i["name"])
    assert Decimal(oil["grams_in_recipe"]) == 27 and "USDA 171413 portion '1 tablespoon' = 13.5 g" in oil["assumption"]
    assert crudo.blockers == {"menu_only": 3, "seasoning_unknown_quantity": 1}
    assert crudo.complete_except_seasonings is False and crudo.complete_except_menu_only is False
    # the statement names the omission and gives no total
    st = est.summary.statement
    assert "do not include bottarga, muscat grape, chive" in st and "not totals for the dish" in st
    assert est.comparison is None and est.summary.n_eligible == 0 and est.summary.n_calculated == 1
    # gate and rubric
    assert by_title(est, "Spaghetti with bottarga sauce").status_reason.startswith("dish_word_absent")
    assert by_title(est, "Seared Tuna Steaks").status_reason.startswith("hard_exclusion:cooked_title_for_raw_dish")
    tartare = by_title(est, "Tuna Tartare")
    assert tartare.relevance.grade == "medium" and tartare.status_reason == "servings_unknown"     # no yield: not calculated, kept in the output
    assert est.summary.exclusion_reasons == {"dish_word_absent": 1, "hard_exclusion": 1, "servings_unknown": 1, "incomplete": 1}
    # efficiency: one relevance call, one query call, one selection call; rejected pages cost no USDA search
    assert est.cost.llm_calls == 3 and est.cost.llm_calls_by_stage == {"relevance": 1, "match": 2}
    assert est.cost.usda_searches == 10                                              # tuna, oil, salt + bottarga, grape, chive, plus 4 plain-name retries that also find nothing
    assert not any("spaghetti" in json.loads(r.content).get("query", "") for r in rec.requests if r.method == "POST")
    assert est.cost.usda_portion_lookups == 1 and est.cost.usda_lookups == 2       # oil portions; tuna + oil nutrition (service dedupes)


def test_page_nutrition_block_never_reaches_the_estimate():
    est, _, _ = run(CRUDO, CRUDO_PAGES, CRUDO_RESULTS)
    blob = est.model_dump_json()
    assert "999 kcal" not in blob and "777 mg" not in blob and "cholesterolContent" not in blob and "calories" not in blob


# -- the tomato salad: complete, proxy-dependent, seasoning-blocked, range ---------------------------------


def test_complete_proxy_and_seasoning_scenarios_are_told_apart_and_only_eligible_ones_enter_the_range():
    est, llm, _ = run(TOMATOES, TOMATO_PAGES, TOMATO_RESULTS, grades={"Panzanella with Heirloom Tomatoes": ("same", "similar", "different")})
    salad = by_title(est, "Heirloom Tomato Salad")
    assert salad.calculation_status == "complete" and salad.eligible_for_range and salad.representativeness == "high"
    assert salad.relevance.menu_coverage == Decimal(1) and salad.match_counts == {"direct": 4, "proxy": 0, "unresolved": 0}
    tomatoes = next(i for i in salad.ingredients if i.name == "ripe plum tomatoes")
    assert tomatoes.conversion.grams == Decimal(248) and tomatoes.conversion.method == "usda_portion" and tomatoes.preparation_state == "raw"
    bread = next(i for i in salad.ingredients if "sourdough" in i.name)
    assert bread.conversion.grams == Decimal(278) and bread.preparation_state == "as_used"

    salted = by_title(est, "Tomato and Bread Salad")
    assert salted.calculation_status == "incomplete" and salted.blockers == {"seasoning_unknown_quantity": 1}
    assert salted.complete_except_seasonings is True and salted.eligible_for_range is False
    salt_line = next(i for i in salted.ingredients if i.name == "salt")
    assert salt_line.conversion.grams is None and salt_line.blocker == "seasoning_unknown_quantity"       # unknown stays unknown (D5)

    burrata = by_title(est, "Tomatoes with Burrata and Sourdough")
    assert burrata.calculation_status == "complete" and burrata.representativeness == "proxy_dependent"
    assert burrata.eligible_for_range is False and burrata.ineligible_reason.startswith("proxy_dependent")
    assert burrata.proxy_share["cholesterol_mg"] == Decimal(1) and burrata.proxy_share["saturated_fat_g"] > Decimal("0.9")
    assert burrata.proxies == ["burrata -> Cheese, romano (171249)"]
    assert burrata.largest_contributor_is_proxy == {"saturated_fat_g": True, "cholesterol_mg": True} and "proxy_largest_contributor" in burrata.flags
    assert burrata.proxy_share_basis == "known_subtotal" and burrata.proxy_share_percent["cholesterol_mg"] == 100
    assert burrata.proxy_contribution["cholesterol_mg"] == Decimal("8") * Decimal("28.349523125") * Decimal(104) / Decimal(100)

    pan = by_title(est, "Panzanella with Heirloom Tomatoes")
    assert pan.eligible_for_range and pan.representativeness == "medium" and pan.relevance.grade == "medium"

    assert est.summary.n_eligible == 2 and est.summary.range_meaningful is True
    assert est.summary.blocked_only_by_seasonings == 1 and est.summary.blocked_only_by_menu_only == 0
    cmp = est.comparison
    assert cmp["basis"] == "per_serving" and cmp["nutrients"]["saturated_fat_g"]["n_complete"] == 2
    assert set(cmp["nutrients"]["cholesterol_mg"]["values"]) == {salad.scenario_id, pan.scenario_id}
    st = est.summary.statement
    assert st.startswith("Range across 2 modeled recipes for HEIRLOOM TOMATOES, per serving: saturated fat")
    assert "Not a verified value for the restaurant's dish." in st
    assert "Substitute USDA records" not in st                                   # the proxy scenario is not in the range


def test_single_eligible_scenario_is_not_a_range():
    pages = {k: v for k, v in TOMATO_PAGES.items() if "panzanella" not in k}
    results = {"open": [{"url": u, "title": ""} for u in pages], "structured_hosts": []}
    est, _, _ = run(TOMATOES, pages, results)
    assert est.summary.n_eligible == 1 and est.summary.range_meaningful is False
    assert est.summary.statement.startswith("Only 1 of 3 comparable recipes for HEIRLOOM TOMATOES could be calculated completely")
    assert est.comparison["nutrients"]["saturated_fat_g"]["range_meaningful"] is False


def test_scenario_cap_and_ordering():
    est, _, _ = run(TOMATOES, TOMATO_PAGES, TOMATO_RESULTS, grades={"Panzanella with Heirloom Tomatoes": ("same", "similar", "different")}, max_scenarios=2)
    processed = [s.source.title for s in est.scenarios if s.status == "calculated"]
    assert len(processed) == 2 and "Panzanella with Heirloom Tomatoes" not in processed       # medium grade sorts after high
    assert by_title(est, "Panzanella with Heirloom Tomatoes").status_reason == "beyond_scenario_cap"


# -- reliability ---------------------------------------------------------------------------------------------


def test_all_rejected_means_no_numbers_and_no_usda_calls():
    grades = {t: ("different", "different", "same") for t in ["Heirloom Tomato Salad", "Tomato and Bread Salad", "Tomatoes with Burrata and Sourdough",
                                                              "Panzanella with Heirloom Tomatoes"]}
    est, _, rec = run(TOMATOES, TOMATO_PAGES, TOMATO_RESULTS, grades=grades)
    assert est.summary.n_relevant == 0 and est.summary.n_calculated == 0 and rec.requests == []
    assert est.summary.statement.startswith("No comparable published recipe was found for HEIRLOOM TOMATOES: 4 recipes were read")
    assert "Roli does not estimate them from other sources" in est.summary.statement
    assert est.cost.llm_calls == 1


def test_rubric_failure_leaves_recipes_ungraded_and_uncalculated():
    est, _, rec = run(TOMATOES, TOMATO_PAGES, TOMATO_RESULTS, llm=RuleLLM(break_relevance=True))
    assert all(s.status == "not_processed" and s.status_reason == "relevance_ungraded" for s in est.scenarios)
    assert est.summary.n_calculated == 0 and rec.requests == [] and any("relevance grading failed" in n for n in est.notes)


def test_usda_search_outage_leaves_lines_unresolved_and_the_scenario_incomplete():
    def down(request):
        if request.method == "POST":
            return httpx.Response(503, content=b"")
        return httpx.Response(404, content=b"")
    from conftest import make_service
    site = Site(pages=TOMATO_PAGES)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, _ = make_service(down)
    est = estimate_dish(TOMATOES, source=FakeSource(TOMATO_RESULTS), fetcher=fetcher, service=service, llm=RuleLLM(), parse_json_object=parse_json_object,
                        match_cache=MatchCache(None))
    salad = by_title(est, "Heirloom Tomato Salad")
    assert salad.calculation_status == "incomplete" and set(salad.blockers) == {"usda_error"}
    assert all(i.match.issue == "usda_error:usda_unavailable" for i in salad.ingredients)
    assert est.summary.n_eligible == 0 and "could not be matched to a USDA record" in est.summary.statement


def test_guard_rejection_inside_the_pipeline():
    est, _, rec = run(TOMATOES, TOMATO_PAGES, TOMATO_RESULTS, llm=RuleLLM(foreign_id=424242))
    salad = by_title(est, "Heirloom Tomato Salad")
    assert all(i.match.issue == "guard_rejected" for i in salad.ingredients) and salad.calculation_status == "incomplete"
    assert not any("424242" in str(r.url) for r in rec.requests)


# -- the graph path and the reply --------------------------------------------------------------------------


def make_dish_graph(pages, results, grades=None, llm=None):
    site = Site(pages=pages)
    fetcher = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None)
    service, rec = make_usda()
    llm = llm or RuleLLM(grades=grades or {})
    graph = build_graph(llm=llm, service=service, load_prompt=lambda v: "x", recipe_source=FakeSource(results), fetcher=fetcher, match_cache=MatchCache(None))
    return graph, llm, rec


def test_dish_path_reply_numbers_all_come_from_the_estimate():
    graph, _, _ = make_dish_graph(TOMATO_PAGES, TOMATO_RESULTS, grades={"Panzanella with Heirloom Tomatoes": ("same", "similar", "different")})
    out = run_roli(menu_item=TOMATOES.model_dump(), graph=graph)
    state, reply = out["state"], out["response"]
    assert state["intent"] == "dish" and state["numbers_allowed"] is True and state["dish_error"] is None
    assert reply.startswith("Dish: HEIRLOOM TOMATOES (tomatoes, sourdough)\nRange across 2 modeled recipes")
    assert "Recipes: 4 read, 4 comparable, 4 calculated, 3 complete, 2 in the range." in reply
    assert "- Heirloom Tomato Salad (f.test, 4 servings; relevance high, representativeness high; in range)" in reply
    assert "not in range (proxy_dependent" in reply and "substitute USDA records: burrata -> Cheese, romano (171249) (their share of the total: saturated fat 9" in reply
    assert "not in range (incomplete: salt)" in reply
    allowed = numbers_in_json(state["dish_estimate"])
    assert numbers_in(reply) <= allowed, numbers_in(reply) - allowed


def test_dish_path_with_nothing_comparable_has_no_nutrition_numbers():
    grades = {t: ("different", "same", "same") for t in ["Tuna Crudo", "Tuna Tartare"]}
    graph, _, _ = make_dish_graph(CRUDO_PAGES, CRUDO_RESULTS, grades=grades)
    out = run_roli(menu_item=CRUDO.model_dump(), graph=graph)
    reply = out["response"]
    assert out["state"]["numbers_allowed"] is False
    assert "No comparable published recipe was found for BLUEFIN CRUDO" in reply
    assert not re.search(r"\d+(\.\d+)? ?(g|mg)\b", reply)                        # no quantity-looking number anywhere
    assert "Not comparable:" in reply


def test_dish_path_setup_failure_is_reported_not_invented():
    def boom():
        raise RuntimeError("TAVILY_API_KEY is missing")
    service, _ = make_usda()
    import roli_agent.graph as g
    original = g._default_source
    g._default_source = boom                                       # no TAVILY key: the default source cannot be built
    try:
        graph = build_graph(llm=RuleLLM(), service=service, load_prompt=lambda v: "x", recipe_source=None, fetcher=None, match_cache=MatchCache(None))
        out = run_roli(menu_item=CRUDO.model_dump(), graph=graph)
    finally:
        g._default_source = original
    assert out["state"]["dish_error"].startswith("recipe search unavailable") and out["state"]["numbers_allowed"] is False
    assert "Roli does not estimate them from other sources" in out["response"] and not re.search(r"\d", out["response"])


def test_menu_item_wins_over_recipe_and_text_and_invalid_item_is_reported():
    graph, llm, rec = make_dish_graph(TOMATO_PAGES, TOMATO_RESULTS)
    out = run_roli(text="hello", recipe={"recipe_name": "x", "servings": 1, "ingredients": []}, menu_item={"name": "HEIRLOOM TOMATOES", "description": "tomatoes, sourdough"}, graph=graph)
    assert out["state"]["intent"] == "dish"
    bad = run_roli(menu_item={"name": "X", "unexpected": 1}, graph=graph)
    assert bad["state"]["dish_error"].startswith("menu item invalid") and "could not build recipe scenarios" in bad["response"]
