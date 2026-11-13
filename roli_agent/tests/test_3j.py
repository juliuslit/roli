"""Checkpoint 3J (SPEC_3_mvp.md 12.18): the approved plate-size table, the dish-kind call on with logged fallbacks, non-main families listed apart, the reference check
flagging above the range only, the dish cap at 30, the coverage causes, and the match-cache fix found by the 3I repeatability check. No network."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from types import SimpleNamespace

from roli_agent.config import ROOT
from roli_agent.llm import parse_json_object
from roli_agent.mvp.dish_kind import DishKindCache, classify_menu
from roli_agent.mvp.models import MvpConfig, RankedDish
from roli_agent.mvp.ranking import APART_GROUPS, NOT_RESTAURANT, WORD_LIMIT, apart_lines, recommendation_text
from roli_agent.mvp.reference import BELOW_NOTE, reference_check
from roli_agent.mvp.selection import COURSE_OF, select_dishes
from roli_agent.recipes.match import MatchCache, MatchDecision
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.portions import FAMILIES, PortionRules
from roli_agent.scripts.build_cards import apply_approvals, load_approvals
from roli_agent.scripts.coverage import cause_of

from test_3d_reference_usda import dish
from test_3i import KindLLM, breakfast_menu

D = Decimal
RULES = PortionRules.load()


# -- 12.18: the approved table -------------------------------------------------------------------------------------------------------------


def test_every_row_carries_julius_approval_and_the_five_changed_rows_have_his_ranges():
    rows = {r.id: r for r in RULES.rows}
    assert all(r.approved_by == "Julius" for r in RULES.rows)
    raw = {r["id"]: r for r in csv.DictReader((ROOT / "roli_agent" / "recipes" / "portion_rules.csv").open(encoding="utf-8"))}
    assert all(r["approved_on"] == "2026-11-07" and r["notes"].startswith("Julius 2026-11-07 (12.18)") for r in raw.values())
    assert (rows["PR01"].low, rows["PR01"].high) == (D(171), D(385)) and raw["PR01"]["fndds_low"] == "83" and raw["PR01"]["range_source"] == "pizza express and avpn"
    for i, lo, hi in (("PR04", "96.6", "355.6"), ("PR16", "83.7", "424.1"), ("PR17", "128.0", "538.7"), ("PR18", "288.0", "474.0")):
        assert (rows[i].low, rows[i].high) == (D(lo), D(hi)) and raw[i]["range_source"] == "chain" and raw[i]["fndds_low"] and "approved: chain range" in raw[i]["sources_status"], i
    assert (rows["PR07"].low, rows["PR07"].high) == (D(139), D(300)) and "raw cut" in raw["PR07"]["notes"]
    assert {i for i, r in rows.items() if r.review_status == "unsourced"} == {"PR06", "PR08"} and all(r.review_status == "approved" for i, r in rows.items() if i not in ("PR06", "PR08"))
    assert rows["PR06"].confidence == "portion_proposed" and rows["PR01"].confidence == "portion_reviewed"


def test_approved_rows_run_and_the_approved_unsourced_rows_still_never_run():
    assert [r.id for r in RULES.for_dish_type("tomato_salad_starter", "heirloom tomatoes")] == ["PR05"] and [r.id for r in RULES.for_dish_type("pasta_main", "spaghetti")] == ["PR09"]
    assert [r.id for r in RULES.for_dish_type("burger", "cheeseburger")] == ["PR16"] and [r.id for r in RULES.unsourced()] == ["PR06", "PR08"]


def test_the_builder_copies_an_approval_and_keeps_the_figure_it_set_aside_as_a_note():
    approvals = load_approvals()
    assert len(approvals) == 33 and approvals["PR01"]["low"] == "171" and approvals["PR07"]["low"] == ""
    spec = dict(id="PR16", unit="g whole item, bun included")
    row = dict(low="123.0", high="171.0", range_source="fndds", review_status="sources_disagree", basis="FNDDS portions ...", sources_status="sources_disagree: ...", notes="")
    out, ev = apply_approvals(spec, row, dict(notes=[]), approvals["PR16"])
    assert (out["low"], out["high"], out["range_source"], out["review_status"], out["approved_by"]) == ("83.7", "424.1", "chain", "approved", "Julius")
    assert out["basis"].startswith("APPROVED RANGE (12.18, Julius, 2026-11-07): 83.7-424.1 g whole item, bun included") and "Range before approval: 123.0-171.0" in out["basis"] and ev["notes"]
    as_is, _ = apply_approvals(dict(id="PR07", unit="g"), dict(low="139", high="300", review_status="proposed_unreviewed", basis="b", notes="n"), dict(notes=[]), approvals["PR07"])
    assert (as_is["low"], as_is["high"], as_is["review_status"]) == ("139", "300", "approved") and as_is["notes"].endswith("; n")
    unsourced, _ = apply_approvals(dict(id="PR08", unit="g"), dict(low="90", high="140", review_status="unsourced", basis="b", notes=""), dict(notes=[]), approvals["PR08"])
    assert unsourced["review_status"] == "unsourced" and unsourced["approved_by"] == "Julius"
    untouched, _ = apply_approvals(spec, dict(low="123.0", high="171.0", range_source="fndds", review_status="sources_disagree", basis="b", notes=""), dict(notes=[]), None)   # no approval row: nothing changes
    assert untouched["review_status"] == "sources_disagree" and "approved_by" not in untouched


# -- 12.18: the dish-kind call is on; every fallback is logged ----------------------------------------------------------------------------------


def test_the_call_is_on_by_default_and_every_fallback_is_logged_with_the_item(tmp_path):
    assert MvpConfig().dish_kind_model is True and MvpConfig().max_dishes == 30
    items = breakfast_menu()["items"]
    food = [i for i, it in enumerate(items) if (it.get("category") or "food") == "food" and not it.get("belongs_to")]
    answers = {i: "breakfast_eggs" for i in food}
    answers[food[3]] = "a bowl of warmth"                                  # not on the list -> the word lists answer, and the log says so
    kinds, log = classify_menu(items, KindLLM(answers), parse_json_object, cache=DishKindCache(tmp_path, "test-model"))
    assert kinds[food[3]].source == "word_list" and log["fallback"] == 1 and log["fallbacks"][0]["name"] == items[food[3]]["name"] and "unknown kind" in log["fallbacks"][0]["why"]
    broken, log2 = classify_menu(items, KindLLM({}, fail=True), parse_json_object, cache=None)
    assert log2["error"] and log2["fallback"] == len(food) and {f["why"] for f in log2["fallbacks"]} == {"no model answer"} and all(broken[i].source == "word_list" for i in food)


# -- 12.18: non-main families listed apart ------------------------------------------------------------------------------------------------------


def rd(rank, name, low, high, apart=None):
    return RankedDish(rank=rank, key=name, name=name, saturated_fat_low=D(low), saturated_fat_high=D(high), cholesterol_low=D(0), cholesterol_high=D(0), support="close_call", listed_apart=apart)


def test_the_apart_groups_are_the_non_main_families_and_the_mains_stay_in_the_ranking():
    assert {f for f, g in APART_GROUPS.items() if g == "side"} == {"fried_potato_side", "side_salad", "side_vegetable", "side_rice", "side_bread"}
    assert APART_GROUPS["soup"] == "soup" and APART_GROUPS["dip"] == "dip" and APART_GROUPS["dessert"] == "dessert" and APART_GROUPS["snack_bowl"] == "snack" and APART_GROUPS["kids_dish"] == "kids"
    mains = {"fish_main", "meat_main", "fish_and_chips", "crudo_starter", "fish_starter", "vegetable_starter", "leaf_salad_starter", "tomato_salad_starter", "pizza_neapolitan", "pasta_main",
             "burger", "sandwich", "wrap", "taco", "burrito", "quesadilla", "breakfast_eggs", "breakfast_pancakes", "breakfast_cereal", "toast_plate"}
    assert not (mains & set(APART_GROUPS)) and set(APART_GROUPS) | mains == set(FAMILIES) == set(COURSE_OF)


def test_sides_soups_and_desserts_never_enter_the_top_three_and_each_group_gets_one_line():
    ranked = [rd(1, "CHIPS", "0.2", "4.1", "side"), rd(2, "MINESTRONE", "0.5", "2.0", "soup"), rd(3, "GREEN BEANS", "0.9", "3.0", "side"), rd(4, "SEA BASS", "1.0", "5.0"),
              rd(5, "ROAST CHICKEN", "3.0", "9.0"), rd(6, "APPLE CRUMBLE", "6.9", "16.9", "dessert"), rd(7, "KIDS PASTA", "2.0", "6.0", "kids"), rd(8, "LAMB CHOPS", "8.0", "20")]
    text, n = recommendation_text(ranked, 8, 8, 0, kids_section=True)
    assert "1) Sea Bass" in text and "2) Roast Chicken" in text and "3) Lamb Chops" in text and "Chips" not in text.split("Lightest side")[0]
    assert "Lightest side: Chips, 0.2-4.1 g. Lightest soup: Minestrone, 0.5-2.0 g. Lightest dessert: Apple Crumble, 6.9-17 g. Kids: Kids Pasta, 2.0-6.0 g. " in text and text.endswith(NOT_RESTAURANT)
    no_kids, _ = recommendation_text(ranked, 8, 8, 0, kids_section=False)
    assert "Kids:" not in no_kids and "Lightest dessert" in no_kids                  # children's dishes are listed only when the menu has a children's section
    assert apart_lines(ranked, kids_section=True)[0] == "Lightest side: Chips, 0.2-4.1 g. " and len(apart_lines(ranked, kids_section=False)) == 3


def test_the_apart_lines_are_dropped_first_under_the_word_limit_the_last_group_first():
    long = "Slow braised Cornish hake fennel saffron"
    picks = [rd(1, long, "1", "2").model_copy(update={"cholesterol_low": D(200), "cholesterol_high": D(400)}), rd(2, long + " two", "2", "3").model_copy(update={"cholesterol_low": D(200), "cholesterol_high": D(400)}),
             rd(3, long + " three", "3", "4")]
    apart = [rd(4, "HAND CUT CHIPS", "0.2", "4.1", "side"), rd(5, "SOUP OF THE DAY", "1", "2", "soup"), rd(6, "STICKY TOFFEE PUDDING", "9", "19", "dessert")]
    plain, n = recommendation_text(picks, 3, 30, 27, n_skipped=2)
    text, used = recommendation_text(picks + apart, 6, 30, 24, n_skipped=2)
    assert used <= WORD_LIMIT and n + 10 > WORD_LIMIT
    assert "Sticky Toffee" not in text and ("Lightest side" in text or "Lightest soup" not in text)      # the dessert goes before the soup, the soup before the side; the mains' sentences stay
    assert text.endswith(NOT_RESTAURANT) and "1) Slow Braised Cornish Hake" in text.title() or "1) Slow braised Cornish hake" in text


def test_a_menu_with_only_apart_dishes_says_so_and_still_names_the_lightest_of_each_group():
    text, _ = recommendation_text([rd(1, "SHOESTRING POTATOES", "0.5", "3", "side"), rd(2, "OLIVES", "1", "3", "snack")], 2, 5, 3)
    assert text.startswith("I couldn't estimate a main dish on this menu (5 tried). Lightest side: Shoestring Potatoes, 0.5-3.0 g. Lightest snack: Olives, 1.0-3.0 g. ") and text.endswith(NOT_RESTAURANT)


def test_the_runner_marks_the_apart_dishes_from_their_family(monkeypatch):
    from roli_agent.mvp import menu_run
    assert menu_run.APART_GROUPS is APART_GROUPS and menu_run.KIDS_SECTIONS.search("NIÑOS") and menu_run.KIDS_SECTIONS.search("Kids Menu") and not menu_run.KIDS_SECTIONS.search("Mains")


# -- 12.18: the reference check flags above the range only -----------------------------------------------------------------------------------------


def test_below_the_published_range_is_a_note_and_the_dish_ranks_above_still_flags():
    card = RULES.card_for("snack_bowl", "marinated olives")
    low = reference_check(dish("0.2", "0.4"), card, factor=D("1.5"))
    assert not low.flagged and low.below_published and low.checked and not low.failed
    c = next(c for c in low.comparisons if c.basis == "per_100g")
    assert c.direction == "below" and not c.failed and c.note == BELOW_NOTE == "below the published range for this kind of dish; plain recipe"
    high = reference_check(dish("4.8", "19.3"), card, factor=D("1.5"))
    assert high.flagged and not high.below_published and [x.direction for x in high.failed] == ["above"]
    tomatoes = RULES.card_for("tomato_salad_starter", "heirloom tomatoes")       # the 3I case: 1.9 g against a caprese range of 4.0-18.0 per plate
    check = reference_check(dish("1.0", "2.9", mass=(250, 300)), tomatoes, factor=D("1.5"))
    assert not check.flagged and check.below_published


# -- 12.18: the cap and the coverage causes -------------------------------------------------------------------------------------------------------


def test_the_cap_is_thirty_and_the_coverage_script_tells_the_cap_from_a_spending_limit():
    menu = {"items": [{"name": f"Dish {i} grilled fish", "section": "Mains", "category": "food"} for i in range(35)]}
    cands = select_dishes(menu, MvpConfig().max_dishes)
    assert sum(1 for c in cands if c.decision == "selected") == 30 and sum(1 for c in cands if c.decision == "skipped") == 5 and "cap of 30" in next(c.reason for c in cands if c.decision == "skipped")
    assert cause_of({"status": "skipped", "key": "a", "reason": "skipped: beyond the cap of 30 dishes", "item": {}}, {}, set()) == ("not tried", "the dish cap")
    assert cause_of({"status": "skipped", "key": "a", "reason": "skipped before it started, menu budget", "item": {}}, {}, set()) == ("not tried", "a spending limit")


# -- the 3I repeatability finding: a proxy match is one dish's reading -----------------------------------------------------------------------------


def decision(fdc_id, match_type, reason):
    return MatchDecision(name="whole milk", preparation_hint="unknown", query="milk", fdc_id=fdc_id, description="Soymilk, original and vanilla, unfortified" if match_type == "proxy" else "Milk, whole, 3.25% milkfat",
                         data_type="SR Legacy", record_state="unknown", match_type=match_type, reason=reason, source="llm")


def test_a_proxy_match_is_reused_only_for_the_dish_it_was_chosen_for_and_a_direct_match_everywhere(tmp_path):
    """The Greyhound crumble, 3I pass A against pass B: "whole milk" matched soy milk because another dish's context was vegan, and the cached proxy reached the crumble."""
    cache = MatchCache(tmp_path / "m.json", clock=lambda: 1000.0)
    vegan, crumble = "Vegan crumble (Desserts): oat milk, apples", "Apple and rhubarb crumble (Desserts): custard"
    cache.put("whole milk|unknown", decision(172446, "proxy", "the dish is vegan, so soy milk stands in"), vegan)
    assert cache.get("whole milk|unknown", vegan).fdc_id == 172446 and cache.get("whole milk|unknown", crumble) is None and cache.get("whole milk|unknown") is None
    cache.put("whole milk|unknown", decision(171265, "direct", "same food"), crumble)
    assert cache.get("whole milk|unknown", vegan).fdc_id == 172446 and cache.get("whole milk|unknown", crumble).fdc_id == 171265 and cache.get("whole milk|unknown", "Porridge (Breakfast): oats").fdc_id == 171265
    # a proxy saved by the earlier code under the bare key is not reused
    legacy = MatchCache(tmp_path / "old.json", clock=lambda: 1000.0)
    legacy._data["whole milk|unknown"] = {"saved_at": 1000.0, "decision": decision(172446, "proxy", "vegan").model_dump(exclude={"source"})}
    assert legacy.get("whole milk|unknown", crumble) is None
    again = MatchCache(tmp_path / "m.json", clock=lambda: 1000.0)
    assert again.get("whole milk|unknown", vegan).source == "cache" and again.get("whole milk|unknown", vegan).match_type == "proxy"


# -- the family the dish-kind call chose reaches the portion rules (bug found by the 3J reruns, 2026-11-08) ---------------------------------------------


def test_the_evaluation_uses_the_family_selection_decided_not_the_word_lists(monkeypatch):
    """In the first 3J pass the model's family decided selection but `evaluate_dish` recomputed the family from the word lists, so 30 dishes were tried under the wrong
    family and 15 with no portion rule at all (Mother's Tacos' loaded fries, Ren's quiche). The runner now passes the candidate's family through."""
    from roli_agent.mvp import menu_run as mr
    seen = {}

    def fake_estimate(item, **kw):
        seen["rules"] = kw.get("portion_rules")
        raise RuntimeError("stop here")                     # the dish fails after the family is fixed; the test reads the DishRun

    monkeypatch.setattr(mr, "estimate_dish", fake_estimate)
    runner = mr.MenuRunner.__new__(mr.MenuRunner)
    runner.config = MvpConfig(); runner.llm = object(); runner.rules = RULES; runner.weights = None; runner.evidence = None; runner.service = None; runner.match_cache = None
    runner.judgements = None; runner.parse_json = lambda s: None; runner.source_factory = lambda: object(); runner.fetcher_factory = lambda: None; runner.extraction_cache_factory = lambda: None
    item = MenuItem(name="AL PASTOR O.G.", description="waffle fries, al pastor pork, cheese", section="DIRTY FRIES")
    assert mr.dish_type_for(item) is None                   # the word lists know no family for it
    run = runner.evaluate_dish("al_pastor", 0, item, dish_type="fried_potato_side")
    assert run.dish_type == "fried_potato_side" and run.status == "error"
    assert runner.evaluate_dish("al_pastor", 0, item).dish_type is None          # without the argument the word lists decide, as before
    src = (ROOT / "roli_agent" / "mvp" / "menu_run.py").read_text(encoding="utf-8")
    assert "self.evaluate_dish(key, i, it, budget, dish_type=c.dish_type)" in src
