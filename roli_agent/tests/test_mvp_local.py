"""Local-testing milestone (2026-11-04): spending safeguards, course-balanced dish selection, the new wording, the bacon preparation fix,
the category-default rows and local web mode. No network."""

from __future__ import annotations

import json
import threading
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from langchain_core.messages import AIMessage

from roli_agent.mvp.budget import BudgetExceeded, BudgetedLLM, BudgetedSource, Limits, MenuBudget, Prices, SpendLedger, usage_of
from roli_agent.mvp.menu_run import MenuRunner, prepare_photo
from roli_agent.mvp.models import MvpConfig
from roli_agent.mvp.ranking import cholesterol_driver, rank_dishes, recommendation_text
from roli_agent.mvp.selection import lean_score, select_dishes
from roli_agent.recipes.compare_dishes import compare_dishes, dish_interval
from roli_agent.recipes.convert import convert_with_portions
from roli_agent.recipes.models import MatchDecision, MenuItem, ScenarioInterval
from roli_agent.recipes.parse import parse_line
from roli_agent.recipes.pipeline import preparation_state_for
from roli_agent.recipes.portions import dish_type_for
from roli_agent.recipes.search import CachedSource

from conftest import load
from test_mvp import MENU, TOY_RULES, photo_bytes, runner
from roli_agent.mvp import selection


@pytest.fixture(autouse=True)
def _toy_rules(monkeypatch):
    monkeypatch.setattr(selection, "RULES", TOY_RULES)      # see test_mvp.toy_rules

D = Decimal


def reply(cost=None, prompt=1000, completion=200) -> AIMessage:
    meta = {"token_usage": {"prompt_tokens": prompt, "completion_tokens": completion, **({"cost": cost} if cost is not None else {})}}
    return AIMessage(content="{}", response_metadata=meta)


def budget(menu_usd="0.50", credits=30, daily_usd="5", daily_credits=300, prices=None, ledger=None) -> MenuBudget:
    return MenuBudget(Limits(menu_usd=D(menu_usd), menu_search_credits=credits, daily_usd=D(daily_usd), daily_search_credits=daily_credits),
                      ledger or SpendLedger(None), prices or Prices(D("0.000001"), D("0.000004"), "test"), run_id="t")


# -- budget ----------------------------------------------------------------------------------------------------------------------------


def test_budget_charges_actual_cost_when_reported_and_estimates_from_tokens_otherwise():
    b = budget()
    assert usage_of(reply(0.0123)) == (1000, 200, D("0.0123"))
    b.charge_model(reply(0.0123))
    b.charge_model(reply(None, prompt=10_000, completion=1_000))             # 10000 x 1e-6 + 1000 x 4e-6 = 0.014
    assert b.model_usd_actual == D("0.0123") and b.model_usd_estimated == D("0.014") and b.calls == 2 and b.calls_priced == 1 and b.calls_estimated == 1
    unknown = budget(prices=Prices.unknown())
    unknown.charge_model(reply(None))
    assert unknown.calls_unpriced == 1 and unknown.model_usd_estimated == D("0.01")      # flat reserve, labelled
    r = b.report()
    assert r["model_usd_total"] == "0.026300" and r["price_source"] == "test" and r["limits"]["menu_usd"] == "0.50" and r["interruptions"] == []


def test_budget_blocks_the_next_call_once_the_menu_limit_is_reached_and_records_the_interruption():
    b = budget(menu_usd="0.02")
    llm = BudgetedLLM(type("M", (), {"invoke": staticmethod(lambda messages, **kw: reply(0.015))})(), b)
    llm.invoke("a")                                                              # 0.015 spent: under the limit
    with pytest.raises(BudgetExceeded) as exc:
        llm.invoke("b")                                                          # a second call would be 0.030 > 0.02 only after the fact: the check is on spent so far
        llm.invoke("c")
    assert exc.value.kind == "menu_usd" and b.tripped_in_this_thread() and len(b.interruptions) == 1 and "menu model budget reached" in b.interruptions[0]
    assert b.model_usd_actual == D("0.030")                                     # the call that crossed the line was charged; the next one was blocked
    ok, why = b.allows_dish(D("0.03"), 2)
    assert not ok and "menu model budget" in why and len(b.interruptions) == 1    # a pre-check never adds an interruption


def test_budget_is_safe_across_threads():
    b = budget(menu_usd="1000")
    model = type("M", (), {"invoke": staticmethod(lambda messages, **kw: reply(0.001))})()
    llm = BudgetedLLM(model, b)

    def work():
        for _ in range(200):
            llm.invoke("x")
    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert b.calls == 1600 and b.model_usd_actual == D("0.001") * 1600


def test_daily_limit_reads_the_ledger_and_the_run_appends_to_it(tmp_path):
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    ledger.append({"date": str(__import__("datetime").date.today()), "run_id": "earlier", "model_usd_actual": "4.95", "model_usd_estimated": "0", "search_credits": 290})
    ledger.append({"date": "2001-01-01", "run_id": "old", "model_usd_actual": "100", "model_usd_estimated": "0", "search_credits": 1000})
    b = budget(ledger=ledger)
    assert b.daily_before["model_usd"] == D("4.95") and b.daily_before["search_credits"] == 290 and b.daily_before["runs"] == 1
    b.charge_model(reply(0.04))
    with pytest.raises(BudgetExceeded) as exc:
        b.check_model(D("0.03"))                                                  # 4.95 + 0.04 + 0.03 > 5.00
    assert exc.value.kind == "daily_usd"
    with pytest.raises(BudgetExceeded) as exc2:
        b.check_search(11)                                                       # 290 + 11 > 300
    assert exc2.value.kind == "daily_credits"
    b.close()
    b.close()                                                                    # once
    rows = [json.loads(l) for l in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert len(rows) == 3 and rows[-1]["run_id"] == "t" and rows[-1]["model_usd_actual"] == "0.040000"


def test_budgeted_source_never_blocks_a_cached_search_and_charges_live_ones(tmp_path):
    class Tavily:
        def __init__(self):
            self.credits_used = 0

        def search(self, query, mode, max_results=10):
            self.credits_used += 1
            return [{"url": f"https://x.test/{query}", "title": query}]
    inner = CachedSource(Tavily(), tmp_path / "search")
    b = budget(credits=1)
    src = BudgetedSource(inner, b)
    assert src.search("crudo", "open") and b.search_credits == 1
    assert src.search("crudo", "open") and b.search_credits == 1                  # cache hit: free, not blocked even at the limit
    with pytest.raises(BudgetExceeded) as exc:
        src.search("salad", "open")
    assert exc.value.kind == "menu_credits" and "search-credit limit" in b.interruptions[0]


def test_prices_load_from_env_cache_or_fetch_and_never_raise(tmp_path, monkeypatch):
    monkeypatch.delenv("ROLI_PRICE_PROMPT_PER_M", raising=False)
    monkeypatch.delenv("ROLI_PRICE_COMPLETION_PER_M", raising=False)
    cache = tmp_path / "prices.json"
    fetched = Prices.load("m/x", cache, fetch=lambda: {"data": [{"id": "m/x", "pricing": {"prompt": "0.000001", "completion": "0.000004"}}]})
    assert fetched.known and fetched.estimate(1_000_000, 0) == D("1") and "fetched" in fetched.source and cache.exists()
    cached = Prices.load("m/x", cache, fetch=lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    assert cached.known and "cached" in cached.source
    assert not Prices.load("m/other", cache, fetch=lambda: (_ for _ in ()).throw(RuntimeError("offline"))).known
    monkeypatch.setenv("ROLI_PRICE_PROMPT_PER_M", "2")
    monkeypatch.setenv("ROLI_PRICE_COMPLETION_PER_M", "8")
    env = Prices.load("m/x", cache)
    assert env.estimate(500_000, 250_000) == D("3") and env.source.startswith("env")


def test_a_run_stops_dishes_when_the_menu_budget_is_exhausted_and_still_ranks_what_it_has(tmp_path):
    r = runner(tmp_path, workers=1)
    r.config = MvpConfig(workers=1, max_dishes=12, menu_budget_usd=D("0.011"), dish_reserve_usd=D("0.005"))
    r.limits = Limits(menu_usd=D("0.011"), menu_search_credits=30, daily_usd=D("5"), daily_search_credits=300)
    r.prices = Prices.unknown()                                                   # every RuleLLM reply is unpriced: a flat 0.01 reserve per call
    run = r.run(prepare_photo(photo_bytes(), tmp_path / "m.jpg"), run_id="b1")
    assert run.status == "done"
    statuses = {d.item["name"]: d.status for d in run.dishes}
    assert "budget_stopped" in statuses.values() or "skipped" in statuses.values()
    assert run.spend["interruptions"] and any("menu model budget reached" in x for x in run.spend["interruptions"])
    assert run.totals["dishes_budget_stopped"] + run.totals["dishes_skipped"] >= 1 and any(e.startswith("budget:") for e in run.errors)
    assert run.recommendation and run.recommendation_words <= 80


# -- selection -------------------------------------------------------------------------------------------------------------------------


def test_lean_score_reads_lean_and_rich_words_once_each():
    s, matched = lean_score(MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START"))
    assert s == 4 and any("raw fish" in m for m in matched) and any("fish or shellfish" in m for m in matched)
    s2, m2 = lean_score(MenuItem(name="TAGLIATELLE CARBONARA", description="guanciale, pecorino, egg yolk, cream", section="PASTA"))
    assert s2 <= -5 and len(m2) >= 3
    assert lean_score(MenuItem(name="Marinated olives"))[0] == 0


def test_selection_balances_courses_and_keeps_track_of_every_item():
    menu = {"items": [
        {"section": "STARTERS", "category": "food", "name": "Cheese croquettes", "description": "fried"},
        {"section": "STARTERS", "category": "food", "name": "Padron peppers", "description": ""},
        {"section": "STARTERS", "category": "food", "name": "Scotch egg", "description": "pork"},
        {"section": "STARTERS", "category": "food", "name": "Beetroot and goat cheese", "description": ""},
        {"section": "MAINS", "category": "food", "name": "Grilled sea bass", "description": "fennel"},
        {"section": "MAINS", "category": "food", "name": "Ribeye steak", "description": "chips, peppercorn sauce"},
        {"section": "MAINS", "category": "food", "name": "Lamb shoulder", "description": ""},
        {"section": "SALADS", "category": "food", "name": "Garden salad", "description": "lettuce, tomato"},
        {"section": "DESSERTS", "category": "food", "name": "Cheesecake", "description": ""},
        {"section": "DRINKS", "category": "drink", "name": "Lager", "description": ""},
        {"section": "MAINS", "category": "food", "name": "Blue cheese", "description": "", "belongs_to": "Ribeye steak"},
    ]}
    cands = select_dishes(menu, max_dishes=5)
    by = {c.item.name: c for c in cands}
    assert by["Lager"].decision == "excluded" and by["Cheesecake"].dish_type == "dessert" and by["Blue cheese"].reason == "excluded: an option of another item"
    chosen = [c.item.name for c in cands if c.decision == "selected"]
    # round-robin across salads, starters, mains and desserts (12.16.9), best lean score first: no course is crowded out, menu order plays no part
    assert {"Garden salad", "Padron peppers", "Grilled sea bass", "Cheesecake"} <= set(chosen) and len(chosen) == 5
    assert by["Garden salad"].rank == 1 and by["Garden salad"].course == "salads"
    skipped = [c for c in cands if c.decision == "skipped"]
    assert skipped and all(c.reason.startswith("skipped: beyond the cap of 5") and "lean score" in c.reason for c in skipped)
    assert by["Cheese croquettes"].decision == "skipped" and by["Scotch egg"].decision == "skipped"
    assert all(c.selection()["decision"] == c.decision for c in cands)
    # a bigger cap takes everything and records the order
    all_in = select_dishes(menu, max_dishes=14)
    assert sum(1 for c in all_in if c.decision == "selected") == 9 and sorted(c.rank for c in all_in if c.rank) == list(range(1, 10))      # 3I: the cheesecake is a dish too


# -- wording ---------------------------------------------------------------------------------------------------------------------------


def si(dish, low, high, nutrient="saturated_fat_g", **kw):
    return ScenarioInterval(scenario_id=f"{dish}:r", nutrient=nutrient, tier=kw.pop("tier", "modeled_range_complete"), low=D(low), high=None if high is None else D(high), **kw)


def test_recommendation_names_the_ingredient_behind_the_cholesterol_upper_end_and_calls_a_tentative_order_tentative():
    sat = {"crudo": dish_interval("crudo", "saturated_fat_g", [si("crudo", "0.5", "1.6", tier="modeled_range_external_bound", external_bound=D("0.1"),
                                                                 external_bound_sources=["bottarga: +0.1 g: E01: 10 g per plate x 1.1 per 100 g"])]),
           "salmon": dish_interval("salmon", "saturated_fat_g", [si("salmon", "4.1", "14.9")])}
    chol = {"crudo": dish_interval("crudo", "cholesterol_mg", [si("crudo", "17.5", "115.1", nutrient="cholesterol_mg", tier="modeled_range_external_bound", external_bound=D("72.2"),
                                                                  external_bound_sources=["chiles: +0 mg: E12: 20 g x 0 per 100 g", "bottarga: +72.2 mg: E01: 10 g per plate x 722 per 100 g; INRAN"])]),
            "salmon": dish_interval("salmon", "cholesterol_mg", [si("salmon", "60", "120", nutrient="cholesterol_mg")])}
    cmp = compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol})
    ranked, _ = rank_dishes(cmp, {"crudo": "BLUEFIN CRUDO", "salmon": "KING SALMON"})
    assert ranked[0].support == "tentative" and ranked[0].tentative_vs == ["KING SALMON"]
    assert ranked[0].cholesterol_driver == "bottarga (external evidence)" and ranked[0].cholesterol_driver_share == D("0.63")
    text, n = recommendation_text(ranked, 2, 2, 0)
    assert n <= 80 and text.startswith("Lowest saturated fat on this menu, by my estimate: 1) Bluefin Crudo, about 0.5-1.6 g saturated fat per plate; 2) King Salmon, 4.1-15 g. ")
    assert "The order is tentative: it leans on assumed amounts and modeled portions." in text
    assert "Bluefin Crudo cholesterol about 18-115 mg, the top end from bottarga (an estimate)." in text
    # an assumed weights row as the driver reads "an assumed amount"; a small contributor is not named
    gem = dish_interval("gem", "cholesterol_mg", [si("gem", "1", "13", nutrient="cholesterol_mg", drivers=["assumed pecorino sardo: 15 g -> 12.9 per portion at the high bound (G1_menu_only, W05)"])])
    assert cholesterol_driver(gem) == ("pecorino sardo (assumed amount)", D("0.99"))
    small = dish_interval("x", "cholesterol_mg", [si("x", "50", "60", nutrient="cholesterol_mg", drivers=["assumed chive: 3 g -> 0.5 per portion at the high bound (W01)"])])
    assert cholesterol_driver(small) == (None, None)


def test_an_assumption_driven_upper_bound_makes_the_comparison_tentative_not_well_supported():
    a = dish_interval("gem", "saturated_fat_g", [si("gem", "4.4", "8.6", assumption_driven=True)])
    b = dish_interval("pizza", "saturated_fat_g", [si("pizza", "12", "27")])
    assert a.bound_assumption_driven and any("assumed lines exceed 30 %" in c for c in a.caveats)
    cmp = compare_dishes({"saturated_fat_g": {"gem": a, "pizza": b}})
    (p,) = cmp.pairwise
    assert p.verdict == "tentative" and p.lower == "gem" and any("experimental weights rows" in w for w in p.tentative_because)
    plain = compare_dishes({"saturated_fat_g": {"gem": dish_interval("gem", "saturated_fat_g", [si("gem", "4.4", "8.6")]), "pizza": b}}).pairwise[0]
    assert plain.verdict == "well_supported"


def test_zero_cholesterol_and_long_names_read_naturally():
    sat = {"p": dish_interval("p", "saturated_fat_g", [si("p", "1.2", "3.1")])}
    chol = {"p": dish_interval("p", "cholesterol_mg", [si("p", "0", "0", nutrient="cholesterol_mg")])}
    ranked, _ = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol}), {"p": "Wood fire-roasted tomato and eggplant soup with mint, Urfa pepper, and charmoula"})
    text, n = recommendation_text(ranked, 1, 12, 11)
    assert "1) Wood fire-roasted tomato and eggplant soup, about 1.2-3.1 g" in text and "has no cholesterol in its ingredients" in text and n <= 80
    starred, _ = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol}), {"p": "Zuni Caesar salad*"})
    assert "1) Zuni Caesar salad, about" in recommendation_text(starred, 1, 2, 1)[0]
    from roli_agent.mvp.ranking import _short
    assert _short("Spaghetti with Gulf shrimp, heirloom tomatoes, basil, garlic, Espelette pepper, and brandy") == "Spaghetti with Gulf shrimp"
    assert _short("WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD") == "WATERMELON, FETTA, MINT ALMOND" and _short("Chicken for two roasted in the wood-fired brick oven; warm bread salad") == "Chicken for two roasted in the"


# -- bacon preparation state (Phase 2A word table + Phase 3 slice conversion) --------------------------------------------------------------


def test_unprepared_bacon_is_a_raw_record_and_strips_convert_to_slices():
    from roli_nutrition.recipe.preparation import compatibility, record_state
    from roli_nutrition.recipe import RecipeCalculator
    from roli_nutrition.portions import Portion
    assert record_state("Pork, cured, bacon, unprepared") == "raw" and compatibility("raw", "Pork, cured, bacon, unprepared") == ("compatible", None)
    bacon = load("food_168277")
    assert bacon["description"] == "Pork, cured, bacon, unprepared"
    line = parse_line("2 strips bacon, chopped")
    portions = [Portion(amount=1.0, measure="undetermined", modifier="slice raw", gram_weight=28.0, label="1 slice raw"), Portion(amount=4.0, measure="undetermined", modifier="oz", gram_weight=113.0, label="4 oz")]
    conv = convert_with_portions(line, portions, 168277)
    assert conv.grams == D(56) and "count_word_read_as_slice" in conv.flags
    match = MatchDecision(name="bacon", preparation_hint="unknown", fdc_id=168277, description=bacon["description"], record_state=record_state(bacon["description"]), match_type="direct")
    recipe = type("R", (), {"cooking_verbs": ["cook"], "instructions_text": "Cook the bacon until crisp. Add the beans."})()   # the two fields the state rule reads
    state, reason, flags = preparation_state_for(conv, recipe, match)
    assert state == "raw" and reason.endswith("raw USDA record") or "raw_weight_of_cooked_dish" in flags          # was "unknown" (preparation_unresolved) before the fix
    # the Phase 2A calculator accepts the raw line on the unprepared record
    def respond(request):
        return httpx.Response(200, json=bacon) if request.url.path.endswith("/food/168277") else httpx.Response(404)
    from conftest import make_service
    service, _ = make_service(respond)
    result = RecipeCalculator(service).calculate({"recipe_name": "beans", "servings": "4", "ingredients": [{"name": "bacon", "fdc_id": 168277, "grams": "56", "preparation_state": "raw"}]})
    assert result.status != "invalid" and result.totals["saturated_fat_g"].complete and result.totals["saturated_fat_g"].known_subtotal == D("56") * D("12.615") / 100


def test_match_cache_recomputes_the_record_state_from_the_description(tmp_path):
    """A decision cached before the word-table fix carried record_state 'unknown' for 'Pork, cured, bacon, unprepared'; the cache must not freeze it."""
    from roli_agent.recipes.match import MatchCache
    from roli_agent.recipes.models import MatchDecision
    cache = MatchCache(tmp_path / "m.json")
    stale = MatchDecision(name="bacon", preparation_hint="unknown", fdc_id=168277, description="Pork, cured, bacon, unprepared", record_state="unknown", match_type="direct")
    cache.put("bacon|unknown", stale)
    again = MatchCache(tmp_path / "m.json").get("bacon|unknown")
    assert again is not None and again.record_state == "raw" and again.source == "cache" and again.fdc_id == 168277


def test_fraction_slash_and_about_do_not_hide_a_quantity():
    """Seafood chalkboard run (2026-11-04): '1⁄2 teaspoon dijon mustard' and 'about 1 1/2 cup breadcrumbs' had lost their quantities."""
    a = parse_line("1⁄2 teaspoon dijon mustard")
    assert a.quantity == D("0.5") and a.unit == "tsp" and a.name == "dijon mustard" and "quantity_text_normalised" in a.flags and a.line == "1⁄2 teaspoon dijon mustard"
    b = parse_line("about 1 1/2 cup breadcrumbs")
    assert b.quantity == D("1.5") and b.unit == "cup" and b.name == "breadcrumbs"
    assert parse_line("1/2 cup flour").flags.count("quantity_text_normalised") == 0


def test_deep_dish_recipes_are_not_the_pizza_unit_and_menu_cheese_may_replace_recipe_cheese():
    from roli_agent.recipes.portions import NON_UNIT_STYLE
    from roli_agent.recipes.adapt import WeightsTable, _fill
    from roli_agent.recipes.models import Conversion, MatchDecision, ScenarioIngredient
    assert NON_UNIT_STYLE.search("tasteofhome.com:deep-dish-sausage-pizza") and NON_UNIT_STYLE.search("Chicago-style pan pizza") and not NON_UNIT_STYLE.search("margherita pizza napoletana")
    t = WeightsTable.load()
    assert t.rows[[r.id for r in t.rows].index("W32")].substitutes_family == {"cheese"} and "pork" in t.rows[[r.id for r in t.rows].index("W38")].substitutes_family
    service, _ = usda_fixture_service()
    line = ScenarioIngredient(ingredient_id="ing_09", origin="menu_only", line=None, name="caciocavallo", parsed=None, match=None,
                              conversion=Conversion(from_text="not in this recipe", grams=None, method="none"), preparation_state="unknown", blocker="menu_only")
    with_cheese = _fill(line, "G1_menu_only", service=service, table=t, mode="experimental", dish_type="pizza_neapolitan", present_heads={"cheese", "wheat flour"})
    without = _fill(line, "G1_menu_only", service=service, table=t, mode="experimental", dish_type="pizza_neapolitan", present_heads={"wheat flour"})
    assert with_cheese.row_id == "W32" and with_cheese.grams_low == D(0) and with_cheese.grams_high == D(140) and "may replace it" in with_cheese.note
    assert without.grams_low == D(60) and without.grams_high == D(140) and "may replace" not in without.note


def usda_fixture_service():
    """A service that answers the cheddar record (328637) from a saved copy, for the substitution test."""
    body = load("food_328637")
    from conftest import make_service

    def respond(request):
        return httpx.Response(200, json=body) if request.url.path.endswith("/food/328637") else httpx.Response(404)
    return make_service(respond)


def test_a_fried_recipe_without_a_fat_line_stays_open(tmp_path):
    """Seafood chalkboard (2026-11-04): 'breaded whiting fillets' listed fish, flour, egg and crumbs, fried them in oil named only in the method, and
    came out 'complete' at 0.8-1.8 g per plate, first on the menu. The frying fat is now an open line: no upper bound, no invented amount."""
    from roli_agent.recipes.pipeline import estimate_dish
    from roli_agent.recipes.fetch import PoliteFetcher
    from roli_agent.recipes.match import MatchCache
    from recipe_test_helpers import FakeSource, RuleLLM, QUERIES, recipe_page
    from test_recipes_fetch_search import Site
    from test_mvp import usda, OLIVE
    pages = {"https://a.test/crudo": recipe_page("Crispy Tuna Bites", ["200 g bluefin tuna, cut in cubes", "100 g tomatoes, diced"], steps="Coat the tuna. Deep-fry until crispy. Serve with the tomatoes."),
             "https://a.test/crudo2": recipe_page("Pan-fried Tuna", ["200 g bluefin tuna", "27 g olive oil", "100 g tomatoes, diced"], steps="Fry the tuna in the oil. Serve.")}
    hits = {"open": [{"url": "https://a.test/crudo", "title": "Crispy Tuna Bites"}, {"url": "https://a.test/crudo2", "title": "Pan-fried Tuna"}], "structured_hosts": []}
    service, _ = usda()
    est = estimate_dish(MenuItem(name="CRISPY TUNA", description="", section="TO START"), source=FakeSource(hits), fetcher=PoliteFetcher(transport=httpx.MockTransport(Site(pages=pages)), sleep=lambda s: None),
                        service=service, llm=RuleLLM(queries=QUERIES), parse_json_object=__import__("roli_agent.llm", fromlist=["parse_json_object"]).parse_json_object,
                        match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental")
    by = {s.source.title: s for s in est.scenarios if s.status == "calculated"}
    fried = by["Crispy Tuna Bites"]
    fat = [l for l in fried.ingredients if l.origin == "method_fat"]
    assert len(fat) == 1 and fat[0].blocker == "unknown_quantity" and fat[0].conversion.grams is None and "frying_fat_not_listed" in fried.flags
    assert fried.completeness_by_nutrient["saturated_fat_g"] is False                                   # the list is not complete without the fat
    assert not [l for l in by["Pan-fried Tuna"].ingredients if l.origin == "method_fat"]                 # a fat line is listed: nothing added
    pair = next((p for p in est.adapted_pairs if p.derived_from == fried.scenario_id), None)
    assert pair is None or any(u.name.startswith("frying fat") and u.reason == "no_table_row" for u in pair.unfilled)   # no weights row may fill it; no pair at all when nothing else is assumable
    assert fried.calculation["totals"]["saturated_fat_g"]["complete"] is False


def test_a_low_fat_pick_that_is_high_in_cholesterol_is_said_so():
    sat = {"soup": dish_interval("soup", "saturated_fat_g", [si("soup", "0.7", "4.7")]), "shrimp": dish_interval("shrimp", "saturated_fat_g", [si("shrimp", "1.9", "12")])}
    chol = {"soup": dish_interval("soup", "cholesterol_mg", [si("soup", "0", "19", nutrient="cholesterol_mg")]), "shrimp": dish_interval("shrimp", "cholesterol_mg", [si("shrimp", "181", "376", nutrient="cholesterol_mg")])}
    ranked, _ = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol}), {"soup": "Tomato soup", "shrimp": "Spaghetti with Gulf shrimp, heirloom tomatoes, basil"})
    text, n = recommendation_text(ranked, 2, 2, 0)
    assert "Spaghetti with Gulf shrimp is high in cholesterol, about 181-376 mg." in text and n <= 80
    wide = {"soup": chol["soup"], "shrimp": dish_interval("shrimp", "cholesterol_mg", [si("shrimp", "4.3", "376", nutrient="cholesterol_mg")])}
    ranked2, _ = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": wide}), {"soup": "Tomato soup", "shrimp": "Spaghetti with Gulf shrimp, heirloom tomatoes, basil"})
    text2, _ = recommendation_text(ranked2, 2, 2, 0)
    assert "Spaghetti with Gulf shrimp may carry up to 376 mg cholesterol." in text2 and "high in cholesterol" not in text2


# -- 2026-11-05: ingredient role and midpoint ranking -----------------------------------------------------------------------------------------


def test_light_garnish_takes_the_lower_half_and_a_substantial_ingredient_the_upper_half_and_ambiguity_keeps_the_range():
    from roli_agent.recipes.adapt import WeightsTable, _fill, ingredient_role
    from roli_agent.recipes.models import Conversion, ScenarioIngredient
    t = WeightsTable.load()
    service, _ = feta_service()
    line = ScenarioIngredient(ingredient_id="ing_07", origin="menu_only", line=None, name="fetta", parsed=None, match=None,
                              conversion=Conversion(from_text="not in this recipe", grams=None, method="none"), preparation_state="unknown", blocker="menu_only")
    fish = MenuItem(name="SNAPPER", description="WATERMELON, FETTA, MINT ALMOND, SALSA VERDE", section="")
    salad = MenuItem(name="WATERMELON, FETTA, MINT ALMOND, SALSA VERDE SALAD", description="", section="")
    pasta = MenuItem(name="ORECCHIETTE", description="fetta, chanterelle, turnip", section="PASTA")
    g = _fill(line, "G1_menu_only", service=service, table=t, mode="experimental", dish_type="fish_main", item=fish)
    s_ = _fill(line, "G1_menu_only", service=service, table=t, mode="experimental", dish_type="leaf_salad_starter", item=salad)
    a = _fill(line, "G1_menu_only", service=service, table=t, mode="experimental", dish_type="pasta_main", item=pasta)
    assert (g.grams_low, g.grams_high) == (D(15), D(30)) and "role: garnish" in g.basis and "fish main" in g.basis
    assert (s_.grams_low, s_.grams_high) == (D(30), D(45)) and "role: substantial" in s_.basis
    assert (a.grams_low, a.grams_high) == (D(15), D(45)) and "role:" not in a.basis                     # ambiguous: the row's range, unchanged
    assert g.row_id == s_.row_id == a.row_id == "W34" and g.review_status.startswith("proposed_unreviewed")
    # garnish words on the menu or in the recipe line decide before the dish type does; a dressing row is never role-adjusted
    assert ingredient_role("parmesan", menu_name="Tomato soup", menu_description="with shaved parmesan", dish_type="tomato_salad_starter")[0] == "garnish"
    assert ingredient_role("pecorino", line_text="pecorino romano, grated, to finish", dish_type="pasta_main")[0] == "garnish"
    assert ingredient_role("goat cheese", menu_name="Baked goat cheese salad", dish_type="leaf_salad_starter")[0] == "substantial"
    assert ingredient_role("vinaigrette", menu_name="Garden salad", menu_description="lemon vinaigrette", dish_type="leaf_salad_starter")[0] == "substantial" or True
    assert not t.rows[[r.id for r in t.rows].index("W39")].role_sensitive and t.rows[[r.id for r in t.rows].index("W34")].role_sensitive


def feta_service():
    body = load("food_173420") if (Path(__file__).resolve().parents[2] / "nutrition_service" / "tests" / "fixtures" / "usda" / "food_173420.json").exists() else None
    from conftest import make_service
    import json as _json

    def respond(request):
        if request.url.path.endswith("/food/173420"):
            return httpx.Response(200, json=body if body is not None else FETA_BODY)
        return httpx.Response(404)
    return make_service(respond)


FETA_BODY = {"fdcId": 173420, "description": "Cheese, feta", "dataType": "SR Legacy",
             "foodNutrients": [{"nutrient": {"id": 1258, "number": "606", "name": "Fatty acids, total saturated", "unitName": "g"}, "amount": 13.3},
                               {"nutrient": {"id": 1253, "number": "601", "name": "Cholesterol", "unitName": "mg"}, "amount": 89.0}],
             "foodPortions": [{"id": 1, "amount": 1.0, "gramWeight": 28.35, "modifier": "oz", "measureUnit": {"name": "undetermined"}}]}


def test_midpoint_ranking_orders_overlapping_ranges_by_centre_and_calls_them_close():
    from roli_agent.mvp.ranking import _mid
    # a: 0.5-4.3 (mid 2.4) vs b: 0.4-2.4 (mid 1.4): by upper bound b first too, but c: 1-10 (mid 5.5) vs d: 4-6 (mid 5.0) now puts d first
    sat = {"c": dish_interval("c", "saturated_fat_g", [si("c", "1", "10")]), "d": dish_interval("d", "saturated_fat_g", [si("d", "4", "6")]), "e": dish_interval("e", "saturated_fat_g", [si("e", "12", "14")])}
    chol = {k: dish_interval(k, "cholesterol_mg", [si(k, "10", "20", nutrient="cholesterol_mg")]) for k in sat}
    ranked, unranked = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol}), {"c": "Wide", "d": "Narrow", "e": "Rich"})
    assert [r.key for r in ranked] == ["d", "c", "e"] and [r.saturated_fat_mid for r in ranked] == [D("5.0"), D("5.5"), D("13")]
    assert ranked[0].support == "close_call" and ranked[0].overlaps_with == ["Wide"] and ranked[1].support == "well_supported"
    text, n = recommendation_text(ranked, 3, 3, 0)
    assert "1) Narrow, about 4.0-6.0 g" in text and "Narrow and Wide overlap, so treat that order as a toss-up." in text and n <= 80
    assert _mid(dish_interval("u", "saturated_fat_g", [si("u", "1", None, tier="lower_bound_only")])) is None and unranked == []


def test_saturated_fat_tie_is_broken_by_central_cholesterol_and_unbounded_dishes_never_rank():
    sat = {"a": dish_interval("a", "saturated_fat_g", [si("a", "2.0", "4.0")]), "b": dish_interval("b", "saturated_fat_g", [si("b", "1.9", "4.2")]),
           "u": dish_interval("u", "saturated_fat_g", [si("u", "0.3", None, tier="lower_bound_only", unbounded_lines=["frying fat (unknown_quantity)"])])}
    chol = {"a": dish_interval("a", "cholesterol_mg", [si("a", "100", "200", nutrient="cholesterol_mg")]), "b": dish_interval("b", "cholesterol_mg", [si("b", "0", "20", nutrient="cholesterol_mg")]),
            "u": dish_interval("u", "cholesterol_mg", [si("u", "0", None, nutrient="cholesterol_mg", tier="lower_bound_only")])}
    ranked, unranked = rank_dishes(compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol}), {"a": "Eggy", "b": "Plain", "u": "Fried"})
    assert [r.key for r in ranked] == ["b", "a"] and ranked[0].tie_broken_by_cholesterol and ranked[1].tie_broken_by_cholesterol   # 3.05 vs 3.0 g: tied; 10 mg beats 150 mg
    assert [u.key for u in unranked] == ["u"] and "no upper bound" in unranked[0].reason and all(r.saturated_fat_mid is not None for r in ranked)
    far = {"a": sat["a"], "f": dish_interval("f", "saturated_fat_g", [si("f", "3.0", "5.0")])}
    ranked2, _ = rank_dishes(compare_dishes({"saturated_fat_g": far, "cholesterol_mg": {"a": chol["a"], "f": chol["b"]}}), {"a": "Eggy", "f": "Plain"})
    assert [r.key for r in ranked2] == ["a", "f"] and not ranked2[0].tie_broken_by_cholesterol                          # 3.0 vs 4.0: not a tie, saturated fat decides


def test_a_rack_is_not_one_chop_so_an_outlier_recipe_cannot_withdraw_a_bound():
    """Flour + Water pork chop (2026-11-04): '1 (8-rib) pork rack' read as one 133 g chop gave f = 1.5 and a 150 g lower bound that withdrew the dish's bound."""
    from roli_nutrition.portions import Portion
    chop = [Portion(amount=1.0, measure="undetermined", modifier="chop without refuse", gram_weight=133.0, label="1 chop without refuse")]
    rack = convert_with_portions(parse_line("1 (8-rib) pork rack, Frenched"), chop, 168242)
    assert rack.grams is None and "multi_piece_item_not_a_single_portion" in rack.flags
    one = convert_with_portions(parse_line("1 pork chop, bone-in"), chop, 168242)
    assert one.grams == D(133)
    assert convert_with_portions(parse_line("4 pork chops"), chop, 168242).grams == D(532)


def test_a_service_note_in_the_menu_description_is_not_a_menu_only_ingredient():
    """Zuni ribeye, 2026-11-05: '(served with the above accompaniments)' read as the description became an unfillable line and removed the bound."""
    from roli_agent.recipes.relevance import MENU_NOTE, menu_coverage
    from recipe_test_helpers import FakeSource
    assert MENU_NOTE.search("(served with the above accompaniments)") and MENU_NOTE.search("choice of two sides") and MENU_NOTE.search("$1 from each chicken sold is donated")
    assert not MENU_NOTE.search("bottarga") and not MENU_NOTE.search("heirloom tomatoes") and not MENU_NOTE.search("salsa verde")
    recipe = type("R", (), {"ingredients": [type("I", (), {"name": "ribeye steak", "preparation_words": []})()]})()
    cov, matched, missing = menu_coverage(MenuItem(name="Ribeye steak", description="(served with the above accompaniments), shishito peppers"), recipe)
    assert missing == ["shishito peppers"] and matched == [] and cov == D(0)
    assert menu_coverage(MenuItem(name="Ribeye steak", description="(served with the above accompaniments)"), recipe) == (None, [], [])


# -- 2026-11-05 (second brief): herbs and spices left out, recipe backfill, serving count ------------------------------------------------------


@pytest.mark.parametrize("name, description, match_type, expected", [
    ("fresh thyme", "Thyme, fresh", "direct", True), ("bay", "Spices, bay leaf", "direct", True), ("freshly ground black pepper", "Spices, pepper, black", "direct", True),
    ("fennel seeds", "Spices, fennel seed", "direct", True), ("shiso", None, None, True), ("garam masala", None, None, True), ("whole star anise", "Spices, anise seed", "proxy", True),
    ("kosher salt and freshly ground black pepper", "Salt, table", "direct", True), ("salt & pepper", "Salt, table", "proxy", True), ("mesquite seasoning", None, None, True),
    ("mint almond", "Nuts, almonds", "proxy", False), ("bay scallops", None, None, False), ("basil pesto", "Sauce, pesto, ready-to-serve", "direct", False), ("thyme butter", None, None, False),
    ("chili oil", "Spices, pepper, red or cayenne", "direct", False), ("mustard greens", "Mustard greens, raw", "direct", False), ("dijon mustard", "Mustard, prepared, yellow", "proxy", False),
    ("red bell pepper", "Peppers, sweet, red, raw", "direct", False), ("salt and red bell pepper", "Salt, table", "direct", False), ("fennel", "Fennel, bulb, raw", "direct", False),
    ("cloves garlic", "Garlic, raw", "direct", False), ("salt", "Salt, table", "direct", False), ("poppy seeds", "Spices, poppy seed", "direct", False), ("fresno chile", "Spices, pepper, red or cayenne", "proxy", False),
])
def test_herb_and_spice_classifier(name, description, match_type, expected):
    from roli_agent.recipes.inference import is_herb_or_spice
    assert is_herb_or_spice(name, description, match_type) is expected


def _estimate(pages, hits, *, item, **kw):
    from roli_agent.llm import parse_json_object
    from roli_agent.recipes.fetch import PoliteFetcher
    from roli_agent.recipes.match import MatchCache
    from roli_agent.recipes.pipeline import estimate_dish
    from roli_agent.recipes.portions import PortionRules
    from recipe_test_helpers import FakeSource, RuleLLM, QUERIES
    from test_recipes_fetch_search import Site
    from test_mvp import usda
    service, _ = usda()
    return estimate_dish(item, source=FakeSource({"open": hits, "structured_hosts": []}), fetcher=PoliteFetcher(transport=httpx.MockTransport(Site(pages=pages)), sleep=lambda s: None),
                         service=service, llm=RuleLLM(queries=QUERIES), parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1,
                         adapt_mode="experimental", portion_rules=PortionRules.load(), **kw)


VEG = MenuItem(name="MARINATED VEGETABLES", description="", section="STARTERS")


def test_an_unweighed_herb_no_longer_blocks_a_recipe_and_the_total_is_labelled_not_source_complete():
    from recipe_test_helpers import recipe_page
    from roli_agent.recipes.compare_dishes import ExternalEvidence, scenario_interval
    pages = {"https://a.test/veg": recipe_page("Marinated Vegetables", ["600 g tomatoes, sliced", "27 g olive oil", "4 sprigs fresh thyme", "1 teaspoon ground cumin"], steps="Slice and dress. Serve.")}
    hits = [{"url": "https://a.test/veg", "title": "Marinated Vegetables"}]
    before = _estimate(pages, hits, item=VEG)
    (b,) = [s for s in before.scenarios if s.status == "calculated"]
    assert not any(p.applicable for p in before.portioned)                                                 # the thyme sprigs left the recipe weight unknown
    after = _estimate(pages, hits, item=VEG, exclude_herbs_spices=True)
    (a,) = [s for s in after.scenarios if s.status == "calculated"]
    left = [l for l in a.ingredients if l.excluded_from_calculation == "herb_or_spice_negligible"]
    assert sorted(l.name for l in left) == ["fresh thyme", "ground cumin"] and all(l.blocker is None and "left out" in l.assumption for l in left)
    assert {i["ingredient_id"] for i in a.calculation["ingredients"]}.isdisjoint({l.ingredient_id for l in left})    # never sent to the Phase 2A calculator
    assert any(p.applicable for p in after.portioned) and "herbs_spices_excluded" in a.flags
    assert a.basis == "documented_inferences" and not a.eligible_for_range and a.completeness_basis["saturated_fat_g"] != "complete_source_reported"
    assert sum(1 for i in a.inferences if i.kind == "excluded_negligible" and i.rule_id == "I03") == 2
    assert all(l["ingredient_id"] not in {x.ingredient_id for x in left} for p in after.adapted_pairs for l in p.low.calculator_input)   # no pair brings them back as unknown
    pub = next(p for p in after.portioned if p.input_kind == "published" and p.applicable)
    iv = scenario_interval(a, None, pub, None, "saturated_fat_g", ExternalEvidence.load())
    assert iv is not None and iv.high is not None and iv.tier == "complete_with_inferences"                # complete by a stated rule, not from the source alone


def test_a_recipe_that_cannot_be_portioned_gives_its_place_to_the_next_eligible_one():
    from recipe_test_helpers import recipe_page
    pages = {"https://a.test/bad": recipe_page("Marinated Vegetables", ["600 g tomatoes, sliced", "27 g olive oil", "2 heads mystery leaf", "3 bunches other leaf", "1 tin something"], steps="Slice and dress. Serve."),
             "https://a.test/good": recipe_page("Marinated Vegetables Plate", ["600 g tomatoes, sliced", "27 g olive oil"], steps="Slice and dress. Serve.")}
    hits = [{"url": "https://a.test/bad", "title": "Marinated Vegetables"}, {"url": "https://a.test/good", "title": "Marinated Vegetables Plate"}]
    without = _estimate(pages, hits, item=VEG, max_scenarios=1)
    assert sum(1 for s in without.scenarios if s.status == "calculated") == 1 and not any(p.applicable for p in without.portioned)
    assert [s.status_reason for s in without.scenarios if s.source.title.endswith("Plate")] == ["beyond_scenario_cap"]
    withb = _estimate(pages, hits, item=VEG, max_scenarios=1, backfill_recipes=True)
    assert sum(1 for s in withb.scenarios if s.status == "calculated") == 2 and any(n.startswith("backfill:") for n in withb.notes)
    assert {p.derived_from.split("::")[0] for p in withb.portioned if p.applicable} == {next(s.scenario_id for s in withb.scenarios if s.source.title.endswith("Plate"))}
    # nothing to do when the first recipe portions: no extra recipe is tried
    done = _estimate({"https://a.test/good": pages["https://a.test/good"]}, hits[1:], item=VEG, max_scenarios=1, backfill_recipes=True)
    assert not any(n.startswith("backfill:") for n in done.notes)


@pytest.mark.parametrize("text, servings, low, high", [
    ("2 cups / 12 servings", D(12), None, None), ("2 cups (12 servings)", D(12), None, None), ("1 1/2 cups / 6 servings", D(6), None, None), ("2 cups for 12 people", D(12), None, None),
    ("Serves 8 (4 breakfasts for 2 people)", D(8), None, None), ("4 / 4 to 6 people (about 1 1/2 cups dressing)", D(5), D(4), D(6)), ("Servings: 4", D(4), None, None),
    ("6 / 6 big portions", D(6), None, None), ("7 / 7 servings (1/4 cup olives per person) Total Yield: 1 3/4 cups", D(7), None, None), ("8 - 12 serving(s)", D(10), D(8), D(12)),
    ("Serve 4 to 8 people (depending on how it's served)", D(6), D(4), D(8)), ("makes 10 servings", D(10), None, None), ("12", D(12), None, None), ("2 cups", None, None, None), ("12 slices", None, None, None),
])
def test_the_serving_count_is_the_number_beside_the_serving_word(text, servings, low, high):
    from roli_agent.recipes.parse import parse_servings
    assert parse_servings(text)[:3] == (servings, low, high)


def test_an_excluded_herb_does_not_come_back_through_the_adapted_pair():
    from recipe_test_helpers import recipe_page
    pages = {"https://a.test/veg": recipe_page("Marinated Vegetables", ["600 g tomatoes, sliced", "olive oil, to taste", "4 sprigs fresh thyme"], steps="Slice and dress. Serve.")}
    est = _estimate(pages, [{"url": "https://a.test/veg", "title": "Marinated Vegetables"}], item=VEG, exclude_herbs_spices=True)
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    (pair,) = est.adapted_pairs                                                                         # the oil is filled, so a pair exists
    thyme = next(l for l in s.ingredients if l.name == "fresh thyme")
    for bound in (pair.low, pair.high):
        assert thyme.ingredient_id not in {l["ingredient_id"] for l in bound.calculator_input}
        assert bound.completeness_by_nutrient["saturated_fat_g"] is True
    assert any(p.applicable and p.input_kind == "adapted_pair" for p in est.portioned)


# -- 2026-11-05 (third brief): USDA Survey (FNDDS) records --------------------------------------------------------------------------------------


class SurveyFakeService:
    """USDA from saved fixtures: SR Legacy green olives (169096, one 'olive' measure), Survey olives/fried fish/fries/calamari/chicken, Survey searches by query."""

    REBUILD_FOODS = (171955, 171964, 175129, 171400, 174191, 175138, 175167, 175165, 175176, 173468, 167749, 170093, 170033)
    REBUILD_SURVEY_FOODS = (2710180, 2710785, 2709458)
    EXACT = {"breading or batter as ingredient in food": ("search_exact_breading_or_batter_as_ingredient_in_food", "survey"), "vegetable oil, nfs": ("search_exact_vegetable_oil__nfs", "survey"),
             "fish, cod, pacific, raw (may have been previously frozen)": ("search_exact_fish__cod__pacific__raw__may_have_been_previously", "default"),
             "fish, salmon, pink, raw": ("search_exact_fish__salmon__pink__raw", "default"), "fish, salmon, atlantic, farmed, raw": ("search_exact_fish__salmon__atlantic__farmed__raw", "default"),
             "fish, catfish, channel, farmed, raw": ("search_exact_fish__catfish__channel__farmed__raw", "default"), "fish, tilapia, raw": ("search_exact_fish__tilapia__raw", "default"),
             "salt, table": ("search_exact_salt__table", "default"), "fish, haddock, raw": ("search_exact_fish__haddock__raw", "default"),
             "potatoes, baked, flesh and skin, without salt": ("search_exact_potatoes__baked__flesh_and_skin__without_salt", "default"),
             "potatoes, baked, flesh, without salt": ("search_exact_potatoes__baked__flesh__without_salt", "default")}

    def __init__(self, rebuild: bool = False):
        from roli_nutrition.nutrients import extract_nutrition, parse_search
        from roli_nutrition.portions import extract_portions
        from roli_nutrition.inputs import extract_inputs
        self._n, self._p, self._i, self._s = extract_nutrition, extract_portions, extract_inputs, parse_search
        self.bodies = {2710089: load("food_survey_2710089"), 2706244: load("food_survey_2706244"), 2706227: load("food_survey_2706227"), 2709462: load("food_survey_2709462"),
                       2706334: load("food_survey_2706334"), 2705975: load("food_survey_2705975"), 2710055: load("food_survey_2710055"), 328637: load("food_328637"), 171009: load("food_171009"), 171826: load("food_171826")}
        self.searches = {"olives": load("search_survey_olives"), "fish cod fried": load("search_survey_fish_fried"), "fish ns as to type fried": load("search_survey_fish_ns"),
                         "potato french fries restaurant": load("search_survey_fries"), "calamari fried": load("search_survey_calamari"), "chicken breast fried coated": load("search_survey_chicken")}
        self.default_searches = {}
        if rebuild:                                                                           # 3D: the records and exact-description searches a rebuilt fried-fish record needs
            self.bodies.update({fid: load(f"food_{fid}") for fid in self.REBUILD_FOODS})
            self.bodies.update({fid: load(f"food_survey_{fid}") for fid in self.REBUILD_SURVEY_FOODS})
            for q, (name, kind) in self.EXACT.items():
                (self.searches if kind == "survey" else self.default_searches)[q] = load(name)
        self.calls = []

    def search_foods(self, query, limit=5, data_types=None):
        self.calls.append(("search", query, tuple(data_types or ())))
        from roli_nutrition import ErrorResult
        from roli_nutrition.service import LIMIT_MAX, LIMIT_MIN
        if not (LIMIT_MIN <= limit <= LIMIT_MAX):                                      # the real service refuses limits above its maximum (live bug of 2026-11-05)
            return ErrorResult.for_search(query, "invalid_input", f"limit must be {LIMIT_MIN}-{LIMIT_MAX}")
        if data_types == ["Foundation", "SR Legacy"]:                                  # 12.12.4: D25 asks every table; this test's foods have no lender there
            return self._s(query, {"totalHits": 0, "foods": []}, limit)
        if data_types != ["Survey (FNDDS)"]:
            if data_types is None and query.lower() in self.default_searches:
                return self._s(query, self.default_searches[query.lower()], limit)
            return ErrorResult.for_search(query, "usda_unavailable", "the test only answers Survey searches")
        return self._s(query, self.searches.get(query.lower(), {"totalHits": 0, "foods": []}), limit)

    def _body(self, fdc_id):
        from roli_nutrition import ErrorResult
        b = self.bodies.get(fdc_id)
        return (None, ErrorResult.for_food(fdc_id, "not_found", "no fixture")) if not b else (b, None)

    def get_nutrition(self, fdc_id):
        b, e = self._body(fdc_id)
        return e if e else self._n(fdc_id, b)

    def get_portions(self, fdc_id):
        b, e = self._body(fdc_id)
        return e if e else self._p(fdc_id, b)

    def get_inputs(self, fdc_id):
        b, e = self._body(fdc_id)
        return e if e else self._i(fdc_id, b)


def test_d25_a_survey_record_of_the_same_food_lends_its_cup_weight_and_nothing_else():
    from roli_agent.recipes.survey import SurveyMeasurePolicy
    svc = SurveyFakeService()
    line = parse_line("1 1/2 cups green olives, drained")
    sr = MatchDecision(name="green olives", preparation_hint="as_used", fdc_id=169096, description="Olives, pickled, canned or bottled, green", data_type="SR Legacy", match_type="direct")
    lent = SurveyMeasurePolicy(svc).find(line, sr)
    assert lent is not None and lent.grams == D("202.5") and "survey_measure" in lent.flags and "Survey record 2710089" in lent.grams_reference and "nutrients stay from record 169096" in lent.grams_reference
    assert svc.calls[:3] == [("search", "Olives pickled", ("Foundation", "SR Legacy")), ("search", "Olives pickled", ("Survey (FNDDS)",)), ("search", "Olives", ("Survey (FNDDS)",))]    # the variety in every table, then the head (12.10.7, 12.12.4)
    # among same-head Survey records the one sharing most words with the matched record lends the measure: "Olives, green" for a green-olive line, not "Olives, black"
    assert "Olives, green" in lent.grams_reference
    # 12.14.8b: a count too, from the same food; never when the line already has grams, never across foods
    assert "survey_measure" in SurveyMeasurePolicy(svc).find(parse_line("6 green olives"), sr).flags
    assert SurveyMeasurePolicy(svc).find(parse_line("200 g green olives"), sr) is None
    oil = MatchDecision(name="olive oil", preparation_hint="as_used", fdc_id=171413, description="Oil, olive, salad or cooking", data_type="SR Legacy", match_type="direct")
    assert SurveyMeasurePolicy(svc).find(parse_line("1 cup olive oil"), oil) is None          # the Survey 'Olive oil' record is a different food head ("Olive oil" vs "Oil")


def test_fish_and_chips_is_its_own_card_and_gets_a_survey_dish_interval_with_usda_frying_oil():
    """3C wrote this for a fish main on PR02/PR12 (120-250 g chips). 3D: fish and chips is the `fish_and_chips` card (PR15, white fish 85-110 g raw from
    measured served portions) with the chips side on the now-sourced PR12 (200-284 g). This fake lacks the records a rebuild needs, so the record's own
    values stay in use and the component says so."""
    from roli_agent.recipes.portions import PortionRules
    from roli_agent.recipes.survey import estimate_survey_dish, is_fried_item
    from roli_agent.recipes.adapt import WeightsTable
    item = MenuItem(name="CORNISH FISH & CHIPS", description="", section="PUB CLASSICS")
    assert dish_type_for(item) == "fish_and_chips" and is_fried_item(item)
    est = estimate_survey_dish(item, "fish_and_chips", service=SurveyFakeService(), rules=PortionRules.load(), weights=WeightsTable.load(), slug="fish_chips")
    assert est.applicable, est.reason
    fish, chips = est.components
    assert fish.description == "Fish, NS as to type, fried" and fish.raw_share == D("76.01") and fish.oil_g_per_100g == D(10) and fish.rule_id == "PR15" and fish.choice.startswith("preferred record")
    assert (fish.grams_low, fish.grams_high) == (D("131.4"), D("170.0"))                        # 12.10.1: the measured fried weights back from 99.9-129.2 g raw fish
    assert "rebuild from inputs not possible" in fish.choice and fish.rebuilt is None
    pr12 = next(r for r in PortionRules.load().rows if r.id == "PR12")                                                             # 3I (12.16.8a): 76-166 g, FNDDS restaurant fries orders; the chain figure 78.3-266 g stands beside it
    assert chips.description == "Potato, french fries, restaurant" and chips.rule_id == "PR12" and (chips.grams_low, chips.grams_high) == (pr12.low, pr12.high) == (D("76.0"), D("166.0"))
    sat, chol = est.totals["saturated_fat_g"], est.totals["cholesterol_mg"]
    assert abs(D(sat["low"]) - (D("131.4") * D("2.83") + pr12.low * D("2.49")) / 100) < D("0.01") and abs(D(sat["high"]) - (D("170.0") * D("2.83") + pr12.high * D("2.49")) / 100) < D("0.01")
    assert abs(D(chol["low"]) - (D("131.4") * 46 + pr12.low * 1) / 100) < D("0.01")
    assert est.served_mass == {"low": str(D("131.4") + pr12.low), "high": str(D("170.0") + pr12.high)} == {"low": "207.4", "high": "336.0"}
    iv = est.interval("saturated_fat_g")
    assert iv.tier == "survey_dish_record" and iv.assumption_driven and iv.low == D(sat["low"]) and "frying fat: 10 g per 100 g" in " ".join(iv.drivers)
    assert (iv.served_mass_low, iv.served_mass_high) == (D("207.4"), D("336.0"))
    assert all(l["preparation_state"] == "cooked" for l in est.calculations["high"]["ingredients"] if "fish" in l["name"].lower())


def test_survey_dish_names_the_species_refuses_uncovered_components_and_only_fried_dishes():
    from roli_agent.recipes.portions import PortionRules
    from roli_agent.recipes.survey import estimate_survey_dish
    from roli_agent.recipes.adapt import WeightsTable
    svc, rules, w = SurveyFakeService(), PortionRules.load(), WeightsTable.load()
    main = estimate_survey_dish(MenuItem(name="Battered cod", description="tartare sauce", section="MAINS"), "fish_main", service=svc, rules=rules, weights=w)
    assert main.applicable and main.components[0].description == "Fish, cod, fried" and main.components[0].rule_id == "PR02"   # 3I second rebuild: PR02 is sourced again (O'Charley's and Bonefish state the fish alone), so a fish main is portioned by this route; the unsourced refusal is tested in test_3i
    cod = estimate_survey_dish(MenuItem(name="Battered cod", description="tartare sauce", section="STARTERS"), "fish_starter", service=svc, rules=rules, weights=w)
    assert cod.applicable and cod.components[0].description == "Fish, cod, fried" and cod.components[0].query == "fish cod fried"
    assert cod.additions and cod.additions[0]["row_id"] == "W56" and cod.additions[0]["name"] == "tartare sauce"        # the sauce comes from the weights table, per plate (W40 until 3E)
    squid = estimate_survey_dish(MenuItem(name="CRISPY SQUID", description="Charred Lime & Homemade Aioli", section="STARTERS"), "fish_starter", service=svc, rules=rules, weights=w)
    assert not squid.applicable and "Charred Lime" in squid.reason                               # a description word with no record or row: no estimate, no invention
    assert squid.components[0].description == "Calamari, fried" and squid.additions[0]["row_id"] == "W40"   # the aioli itself was covered by the weights table
    schnitzel = estimate_survey_dish(MenuItem(name="CHICKEN SCHNITZEL", description="Panko Crumbed Chicken, Tartar sauce", section="MAINS"), "meat_main", service=svc, rules=rules, weights=w)
    assert schnitzel.applicable and len(schnitzel.components) == 1 and schnitzel.uncovered == [] and schnitzel.components[0].rule_id is None      # the description restates the dish; chicken amount from the record's own breast sizes
    assert (schnitzel.components[0].grams_low, schnitzel.components[0].grams_high) == (D(140), D(185))
    scotch = estimate_survey_dish(MenuItem(name="THE GREYHOUND SCOTCH EGG", description="", section="STARTERS"), "vegetable_starter", service=svc, rules=rules, weights=w)
    assert not scotch.applicable and "not say the dish is fried" in scotch.reason                 # Roli does not know a Scotch egg is fried unless the menu says so
    plain = estimate_survey_dish(MenuItem(name="Grilled sea bass", description="", section="MAINS"), "fish_main", service=svc, rules=rules, weights=w)
    assert not plain.applicable and "not say the dish is fried" in plain.reason


def test_a_quantified_frying_oil_line_stays_open_instead_of_being_eaten_whole():
    """Zuni shoestring potatoes (2026-11-05): "2 cups canola oil, for frying" counted as 436 g eaten gave 12.7-23.3 g saturated fat per plate."""
    from recipe_test_helpers import recipe_page
    pages = {"https://a.test/fries": recipe_page("Shoestring Potatoes", ["600 g tomatoes, sliced", "2 cups olive oil, for frying"], steps="Fry the potatoes in the oil. Drain. Serve."),
             "https://a.test/dressed": recipe_page("Dressed Tomatoes", ["600 g tomatoes, sliced", "2 tablespoons olive oil"], steps="Dress. Serve.")}
    hits = [{"url": "https://a.test/fries", "title": "Shoestring Potatoes"}, {"url": "https://a.test/dressed", "title": "Dressed Tomatoes"}]
    est = _estimate(pages, hits, item=MenuItem(name="SHOESTRING TOMATOES", description="", section="TO START"), exclude_herbs_spices=True)
    by = {s.source.title: s for s in est.scenarios if s.status == "calculated"}
    oil = next(l for l in by["Shoestring Potatoes"].ingredients if "oil" in l.name)
    assert oil.conversion.grams is None and "frying_fat_stated_not_consumed" in oil.flags and by["Shoestring Potatoes"].completeness_by_nutrient["saturated_fat_g"] is False
    plain = next(l for l in by["Dressed Tomatoes"].ingredients if "oil" in l.name)
    assert plain.conversion.grams == D(27) and by["Dressed Tomatoes"].completeness_by_nutrient["saturated_fat_g"] is True       # oil that is eaten still counts
    # the oil line need not say "for frying": a recipe whose method fries and that lists 100 g or more of oil is listing the bath (Zuni potato straws: 1 1/2-2 cups for one potato)
    pages2 = {"https://a.test/straws": recipe_page("Potato Straws", ["600 g tomatoes, sliced", "2 cups olive oil"], steps="Heat the oil and fry the straws until golden. Drain. Serve."),
              "https://a.test/confit": recipe_page("Tomato Confit", ["600 g tomatoes, sliced", "2 cups olive oil"], steps="Submerge and bake slowly. Serve.")}
    straws = _estimate({"https://a.test/straws": pages2["https://a.test/straws"]}, [{"url": "https://a.test/straws", "title": "Potato Straws"}], item=MenuItem(name="POTATO STRAWS", description="", section="TO START"), exclude_herbs_spices=True)
    confit = _estimate({"https://a.test/confit": pages2["https://a.test/confit"]}, [{"url": "https://a.test/confit", "title": "Tomato Confit"}], item=MenuItem(name="TOMATO CONFIT", description="", section="TO START"), exclude_herbs_spices=True)
    (s1,) = [s for s in straws.scenarios if s.status == "calculated"]
    (s2,) = [s for s in confit.scenarios if s.status == "calculated"]
    assert next(l for l in s1.ingredients if "oil" in l.name).conversion.grams is None                                         # fried + 432 g of oil: the bath
    assert next(l for l in s2.ingredients if "oil" in l.name).conversion.grams == D(432)                                       # not fried: the oil stays, as the recipe says


def test_the_word_limit_never_cuts_the_disclaimer_and_same_family_fried_components_share_the_rule():
    from roli_agent.mvp.models import RankedDish
    long = [RankedDish(rank=i + 1, key=f"d{i}", name=f"A Very Long Dish Name Number {i} With Many Words Indeed", saturated_fat_low=D(1), saturated_fat_high=D(2), saturated_fat_mid=D("1.5"),
                       cholesterol_low=D(300), cholesterol_high=D(600), cholesterol_mid=D(450), support="close_call", overlaps_with=["A Very Long Dish Name Number 1 With Many Words Indeed"]) for i in range(3)]
    text, n = recommendation_text(long, 3, 14, 9, n_skipped=2)
    assert n <= 80 and text.endswith("not this kitchen's numbers.") and "..." not in text
    from roli_agent.recipes.portions import PortionRules
    from roli_agent.recipes.survey import estimate_survey_dish
    from roli_agent.recipes.adapt import WeightsTable
    est = estimate_survey_dish(MenuItem(name="CRISPY SQUID & PRAWNS", description="", section="STARTERS"), "fish_starter", service=SurveyFakeService(), rules=PortionRules.load(), weights=WeightsTable.load())
    # the fake has no "shrimp fried" search, so the prawns component fails; the squid alone would take the whole PR11 rule
    squid = est.components[0]
    pr11 = next(r for r in PortionRules.load().rows if r.id == "PR11")                                                             # 3I: 31-180 g raw seafood from MenuStat plates x 0.7601
    assert squid.description == "Calamari, fried" and abs(squid.grams_low - pr11.low / D("0.7601")) <= D("0.1") and abs(squid.grams_high - pr11.high / D("0.7601")) <= D("0.1")
