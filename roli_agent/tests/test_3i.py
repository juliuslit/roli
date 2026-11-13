"""Checkpoint 3I (SPEC_3_mvp.md 12.16): the plate-share ceiling, the empty-menu sentence, the 3 g line as a config value, the plate-size table, the new families and the
dish-kind call. No network."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from roli_agent.config import ROOT
from roli_agent.mvp.dish_kind import DishKindCache, classify_menu, validate_kind
from roli_agent.mvp.models import MvpConfig
from roli_agent.mvp.ranking import NOT_RESTAURANT, recommendation_text
from roli_agent.mvp.reference import reference_check
from roli_agent.mvp.selection import kind_label, select_dishes, unsized_kinds
from roli_agent.recipes.inference import LOW_FAT_G_PER_100G, NutrientFacts, near_zero, saturated_fat_ceiling
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.portions import FAMILIES, PortionRule, PortionRules

import test_3d_tags_cards as tagged
from recipe_test_helpers import recipe_page
from test_3d_reference_usda import dish
from test_3d_tags_cards import TaggingLLM, estimate

D = Decimal
RULES = PortionRules.load()
BREAKFAST_RUN = "20261106-223251-cbe070"          # The Shed, 3H wider run: 14 items, nothing tried


def record(sat=None, chol=None, fat=None):
    return SimpleNamespace(fdc_id=1, description="Onions, red, raw", food_category="Vegetables and Vegetable Products", saturated_fat_g=sat, cholesterol_mg=chol, total_fat_g=fat)


# -- 12.16.1 and 12.16.2: as built in 3H; the 3 g line is a config value --------------------------------------------------------------------


def test_the_count_line_reading_of_3h_stands():
    from roli_agent.recipes.convert import apply_embedded_weight, convert_weight
    from roli_agent.recipes.parse import parse_line
    weigh = lambda t: apply_embedded_weight(convert_weight(parse_line(t))).grams
    assert weigh("4 (6-ounce) fillets") == D(24) * D("28.349523125") and weigh("2 (400 g) cans tomatoes") == D(800)
    assert weigh("3 large (560 grams) potatoes") == D(560) and weigh("4 chops, about 6 ounces each") == D(24) * D("28.349523125")


def test_the_fatty_food_line_is_a_config_value_with_the_eu_limit_as_default():
    assert MvpConfig().low_fat_g_per_100g == D(3) == LOW_FAT_G_PER_100G
    assert saturated_fat_ceiling(record(fat=2.9)) == D("2.9") and saturated_fat_ceiling(record(fat=3.1)) is None
    assert saturated_fat_ceiling(record(fat=3.1), low_fat=D(5)) == D("3.1")
    assert near_zero(record(fat=0.1), D("0.1")) and not near_zero(record(fat=0.1), D("0.1"), low_fat=D("0.05"))
    facts = NutrientFacts(SimpleNamespace(get_nutrition=lambda fid: record(fat=4)), {"ing_01"}, low_fat=D(5))
    assert facts.rule(SimpleNamespace(ingredient_id="ing_01", usda=SimpleNamespace(fdc_id=1)), "saturated_fat_g", "high")["value_per_100g"] == D(4)


# -- 12.16.3: the plate-share ceiling ---------------------------------------------------------------------------------------------------------


def test_the_pizzaface_dip_is_not_portioned_at_more_than_one_recipe_a_plate(monkeypatch):
    """Pizzaface, 3H: 'Sundried tomato', a dip, was read as a tomato salad; the recipe's 22.5 g of sun-dried tomato against the card's 120-250 g made one plate 5-11 whole
    bowls of dip, 513-1076 g of saturated fat. One plate is never more than one whole recipe. In 3I the dip is filed as a dip (PR27, 30-163 g a pot), so the case is
    replayed on that row: a 60 g recipe against a pot of up to 163 g would be 2.7 recipes a plate, and the recipe is refused for portioning."""
    monkeypatch.setitem(tagged.QUERIES, "sun-dried tomatoes", ("tomatoes red ripe raw", tagged.TOMATO, "direct"))
    page = recipe_page("Sun-Dried Tomato Dip", ["22.5 g sun-dried tomatoes", "27 g olive oil", "10 g garlic"], steps="Mix. Serve.")
    est = estimate({"https://a.test/d": page}, MenuItem(name="Sundried tomato dip", description="(contains garlic)", section="DIPS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    assert s.calculation["status"] == "complete" and est.portioned
    for p in est.portioned:
        assert not p.applicable and "PR27: plate share" in p.not_applicable_reason and "exceed one whole recipe" in p.not_applicable_reason and "12.16.3" in p.not_applicable_reason
        assert p.fraction_high is None


def test_a_plate_within_the_recipe_still_portions(monkeypatch):
    monkeypatch.setitem(tagged.QUERIES, "sun-dried tomatoes", ("tomatoes red ripe raw", tagged.TOMATO, "direct"))
    page = recipe_page("Tomato Salad", ["600 g sun-dried tomatoes", "27 g olive oil"], steps="Mix. Serve.")
    est = estimate({"https://a.test/d": page}, MenuItem(name="Tomato salad", description="", section="STARTERS"), TaggingLLM({}))
    assert any(p.applicable and p.fraction_high.fraction <= 1 for p in est.portioned)


# -- 12.16.4: the empty-menu sentence ---------------------------------------------------------------------------------------------------------


def breakfast_menu() -> dict:
    return json.loads((ROOT / "roli_agent" / "runs" / BREAKFAST_RUN / "run.json").read_text(encoding="utf-8"))["menu"]


def test_kinds_a_tester_reads():
    assert kind_label(MenuItem(name="Poached Eggs on Toast", description="", section="")) == "toast"
    assert kind_label(MenuItem(name="Bacon Sandwich", description="", section="")) == "sandwiches"
    assert kind_label(MenuItem(name="Granola", description="", section="")) == "granola" and kind_label(MenuItem(name="Porridge", description="", section="")) == "porridge"
    assert kind_label(MenuItem(name="Pastor", description="", section="MEXICO CITY TACOS")) == "tacos"
    assert kind_label(MenuItem(name="Koshihikari Arancini", description="", section="")) == "arancini"


def test_the_breakfast_menu_reply_names_the_kinds_when_nothing_was_tried(monkeypatch):
    """The Shed, 3H: 'I couldn't estimate any of the 0 dishes I tried' was false. With no family for its dishes, the reply says what they are."""
    import roli_agent.mvp.selection as selection
    monkeypatch.setattr(selection, "dish_type_for", lambda item: None)         # as in 3H: no portion rule for any of them
    cands = select_dishes(breakfast_menu(), 14)
    assert sum(1 for c in cands if c.decision == "selected") == 0
    kinds = unsized_kinds(cands)
    assert kinds == ["toast", "sandwiches", "granola", "porridge", "kids menu"] or kinds[:4] == ["toast", "sandwiches", "granola", "porridge"]
    text, words = recommendation_text([], 0, 0, 0, unsized_kinds=kinds, n_food=8)
    assert text.startswith("I can't size the dishes on this menu yet: toast, sandwiches, granola, porridge") and "upper bound" not in text and text.endswith(NOT_RESTAURANT)


def test_a_drinks_only_menu_and_a_menu_where_estimates_were_tried():
    text, _ = recommendation_text([], 0, 0, 0, unsized_kinds=[], n_food=0)
    assert text.startswith("I found no food dishes on this menu") and "upper bound" not in text
    text, _ = recommendation_text([], 4, 4, 4)
    assert "no estimate had a defensible upper bound" in text and "4 dishes I tried" in text
    text, _ = recommendation_text([], 0, 3, 0, n_skipped=3)                   # held back by the cap or a reserve, not unsized
    assert "3 dishes were not tried" in text and "can't size" not in text


# -- 12.16.6-10: the plate-size table -----------------------------------------------------------------------------------------------------


def rows_by_id():
    return {r.id: r for r in RULES.rows}


def test_every_row_is_approved_or_unsourced_with_a_read_date():
    for r in RULES.rows:
        assert r.review_status in ("approved", "unsourced"), r.id      # 12.18: Julius approved every row on 2026-11-07; PR06 and PR08 stay unsourced (approved as such)
        assert r.approved_by == "Julius" and r.read_on == "2026-11-06", r.id


def test_the_families_of_12_16_9_have_rows_and_the_unsourced_rows_are_the_three_the_data_cannot_size():
    by = rows_by_id()
    families = {r.dish_type for r in RULES.rows if r.review_status != "unsourced"}
    assert {"burger", "sandwich", "wrap", "taco", "burrito", "quesadilla", "breakfast_eggs", "breakfast_pancakes", "breakfast_cereal", "toast_plate", "soup", "dip",
            "side_salad", "side_vegetable", "side_rice", "side_bread", "dessert", "kids_dish", "fried_potato_side"} <= families
    assert {r.id for r in RULES.rows if r.review_status == "unsourced"} == {"PR06", "PR08"}      # raw tomato and dry pasta have no USDA input share; fish mains, crudo and caprese came back with the chain sheets
    assert {r.id for r in RULES.rows if r.review_status in ("single_source", "sources_disagree", "proposed_unreviewed")} == set()   # 12.18: every sourced row is approved
    assert by["PR16"].n_items > 100 and by["PR32"].n_items > 100 and by["PR05"].n_items == 3 and by["PR03"].n_items == 3   # caprese: Pizza Express, Vapiano, Zizzi; sashimi: Wasabi, YO! Sushi


def test_an_unsourced_row_is_never_used_and_its_family_is_not_portioned():
    assert [r.id for r in RULES.for_dish_type("crudo_starter", "bluefin crudo")] == ["PR03"]              # sashimi weights from two businesses: crudo is ranked again
    assert [r.id for r in RULES.for_dish_type("pasta_main", "spaghetti")] == ["PR09"]                     # the P2 row stands; the dry-pasta share is unsourced
    assert [r.id for r in RULES.for_dish_type("tomato_salad_starter", "heirloom tomatoes")] == ["PR05"]    # the P2 row runs; the raw-tomato P3 row (PR06) stays unsourced and is left out


def test_measured_rows_cite_their_source_and_read_date_and_the_p3_rows_say_how_the_key_share_was_derived():
    by = rows_by_id()
    for rid in ("PR07", "PR11", "PR16", "PR26", "PR32"):
        assert "MenuStat" in by[rid].sources and "2026-11-06" in by[rid].sources, rid
    assert by["PR02"].basis.startswith("FNDDS portions (12.16.8a)") and (by["PR02"].low, by["PR02"].high) == (D(156), D(313)) and "Chain figure kept beside it: 211-317" in by["PR02"].basis and "Bonefish" in by["PR02"].sources   # FNDDS fillets set the range; O'Charley's and Bonefish's stated fish stay beside it
    assert [r.id for r in RULES.for_dish_type("fish_main", "grilled sea bass")] == ["PR02"]
    assert "sashimi" in by["PR03"].basis and (by["PR03"].low, by["PR03"].high) == (D(82), D(113)) and "Wasabi" in by["PR03"].sources and "YO! Sushi" in by["PR03"].sources
    assert "Zizzi" in by["PR05"].sources and "Vapiano" in by["PR05"].sources and by["PR06"].basis.startswith("UNSOURCED (12.16.8)") and by["PR08"].basis.startswith("UNSOURCED (12.16.8)")
    assert "USDA 2706334" in by["PR11"].basis and "USDA Table of Cooking Yields" in by["PR07"].sources
    assert "USDA 2708674" in by["PR01"].basis and "Pizza Express" in by["PR01"].sources
    assert by["PR13"].low == D(50) and by["PR15"].low == D("99.9")                                        # confirmed rows keep their cited figures


def test_the_reference_figures_count_the_chains_behind_an_aggregate_row():
    soup = RULES.card_for("soup", "tomato soup")
    figs = soup.figures_on("per_plate")
    assert soup.id == "PR26" and len(figs) == 2 and all(f.n_businesses >= 10 for f in figs)
    check = reference_check(dish("3", "9"), soup, factor=D("1.5"))
    plate = next(c for c in check.comparisons if c.basis == "per_plate")
    assert plate.checked and plate.independent_figures >= 10 and not plate.failed


def test_the_evidence_file_lists_every_row():
    text = (ROOT / "roli_agent" / "eval" / "card_evidence_2026-11-06.md").read_text(encoding="utf-8")
    assert all(f"## {r.id} " in text for r in RULES.rows) and "menustat_download" in text


# -- 12.16.11: the dish-kind call -----------------------------------------------------------------------------------------------------------


def test_validation_keeps_the_readers_filing_and_falls_back_on_an_unknown_kind():
    item = MenuItem(name="Bacon", description="", section="EXTRAS")
    assert validate_kind(item, "meat_main", "bacon", reader_category="add-on").family is None
    assert validate_kind(item, "meat_main", "", belongs_to="Eggs").source == "reader"
    soup = validate_kind(MenuItem(name="Tomato Soup", description="", section=""), "soup", "a soup")
    assert soup.family == "soup" and soup.source == "model"
    odd = validate_kind(MenuItem(name="Tomato Soup", description="", section=""), "bowl of warmth", "")
    assert odd.family == "soup" and odd.source == "word_list" and "unknown kind" in odd.note
    assert validate_kind(item, "not a dish", "a heading").family is None


class KindLLM:
    def __init__(self, answers: dict[int, str], *, fail: bool = False):
        self.answers, self.fail, self.calls = answers, fail, 0

    def invoke(self, messages):
        self.calls += 1
        if self.fail:
            return SimpleNamespace(content="not json")
        return SimpleNamespace(content=json.dumps({"items": [{"index": i, "kind": k, "reason": "test"} for i, k in self.answers.items()]}))


def test_one_call_per_menu_answers_are_saved_and_a_failed_call_leaves_the_word_lists(tmp_path):
    from roli_agent.llm import parse_json_object
    items = breakfast_menu()["items"]
    cache = DishKindCache(tmp_path, "test-model")
    llm = KindLLM({i: "breakfast_eggs" for i in range(len(items))})
    kinds, log = classify_menu(items, llm, parse_json_object, cache=cache)
    assert llm.calls == 1 and log["items"] == len(items) and kinds[0].family == "breakfast_eggs" and kinds[8].family is None and kinds[8].source == "reader"    # the Extras are add-ons
    kinds2, log2 = classify_menu(items, llm, parse_json_object, cache=cache)
    assert llm.calls == 1 and log2["called"] is False and kinds2[0].family == "breakfast_eggs"
    broken, log3 = classify_menu(items, KindLLM({}, fail=True), parse_json_object, cache=None)
    assert log3["error"] and broken[3].source == "word_list" and broken[3].family == "breakfast_cereal"


def test_selection_uses_the_call_when_given_and_the_call_is_on_by_default():
    menu = breakfast_menu()
    kinds = {i: validate_kind(MenuItem(name=it["name"], description=it.get("description", ""), section=it.get("section", "")), "not a dish", "test") for i, it in enumerate(menu["items"])}
    cands = select_dishes(menu, 14, kinds)
    assert all(c.decision == "excluded" and "dish-kind call" in c.reason for c in cands if c.item.name == "Granola")
    assert MvpConfig().dish_kind_model is True        # 12.18: on since 2026-11-07


def test_the_labelled_set_and_the_evaluation_exist_and_the_rule_was_applied():
    labels = list(csv.DictReader((ROOT / "roli_agent" / "eval" / "dish_kind_labels_2026-11-06.csv").open(encoding="utf-8")))
    assert len(labels) == 400 and all(r["proposed_family"] == "" or r["proposed_family"] in FAMILIES for r in labels)
    text = (ROOT / "roli_agent" / "eval" / "dish_kind_eval_2026-11-06.md").read_text(encoding="utf-8")
    assert "12.16.12" in text and ("not met" in text or "met" in text)


def rules_with_unsourced(*ids: str) -> PortionRules:
    """The table as it stood after the first 3I rebuild, when the fish-main and crudo rows had no measured source: the 12.16.8 refusals are tested against it."""
    import copy
    rows = []
    for r in RULES.rows:
        r = copy.copy(r)
        if r.id in ids:
            r.review_status, r.sources = "unsourced", "no measured source (test fixture)"
        rows.append(r)
    return PortionRules(rows)


def test_single_source_rows_run_and_unsourced_rows_do_not():
    """12.17 (Julius's decision of 2026-11-06): one business with a measured figure is `single_source`, which runs under the reference check; none is `unsourced`."""
    from roli_agent.scripts.build_cards import status_for
    assert (status_for(0), status_for(1), status_for(2), status_for(15)) == ("unsourced", "single_source", "proposed_unreviewed", "proposed_unreviewed")
    from roli_agent.recipes.portions import PortionRule
    single = PortionRule({"id": "PRX", "dish_type": "x_kind", "model": "P2", "low": "100", "high": "200", "review_status": "single_source", "sources": "one chain sheet, read 2026-11-06"})
    none = PortionRule({"id": "PRY", "dish_type": "x_kind", "model": "P3", "low": "10", "high": "20", "review_status": "unsourced", "sources": "no measured source"})
    t = PortionRules([single, none])
    assert single.sourced and not none.sourced and [r.id for r in t.for_dish_type("x_kind")] == ["PRX"] and [r.id for r in t.unsourced()] == ["PRY"]


def test_a_stated_weight_in_a_chain_sheet_item_name_feeds_the_key_share_and_a_sashimi_weight_is_the_raw_fish():
    """12.16.6 (b): 'Grilled Atlantic Salmon 7.5 oz' states the fish alone and goes to the P3 key share; a whole-plate weight stays a plate weight; sashimi's portion weight is the raw fish."""
    from roli_agent.scripts.build_cards import collect, OZ
    base = dict(serving_g="", sat_fat_g_per_plate="7", sat_fat_g_per_100g="", cholesterol_mg_per_plate="115", read_on="2026-11-06", notes="Test sheet", _file="t.csv")
    sheets = [dict(base, business="A", family="fish_main", item="Grilled Atlantic Salmon 7.5 oz"),
              dict(base, business="A", family="fish_main", item="8 oz Grilled Chicken & 5 Shrimp Skewer"),           # two proteins, one weight: left out
              dict(base, business="B", family="fish_main", item="Mediterranean Sea Bass", serving_g="543.4"),      # a whole plate: no stated fish weight
              dict(base, business="C", family="crudo_starter", item="Salmon sashimi (excl. dressing)", serving_g="120")]
    fams = collect([], sheets)
    assert [(b, g) for b, _, g in fams["fish_main"].key_weights] == [("A", Decimal("7.5") * OZ)]
    assert [(b, g) for b, _, g in fams["fish_main"].weights] == [("B", Decimal("543.4"))]
    assert [(b, g) for b, _, g in fams["crudo_starter"].weights] == [("C", Decimal("120"))] and fams["crudo_starter"].chains == 1
    assert any("Test sheet (data/chain_sheets/t.csv), read 2026-11-06" == s for s in fams["fish_main"].sources)


def test_the_usda_survey_route_does_not_portion_a_family_whose_row_is_unsourced():
    """12.16.8 by every route: a fried fish main would otherwise be sized from PR02 (or USDA's own serving measures) through the fried-food records. PR02 is sourced
    again since the second 3I rebuild, so the refusal is tested on a copy of the table with PR02 set back to unsourced."""
    from test_mvp_local import SurveyFakeService
    from roli_agent.recipes.survey import estimate_survey_dish
    from roli_agent.recipes.adapt import WeightsTable
    RULES = rules_with_unsourced("PR02")
    est = estimate_survey_dish(MenuItem(name="Crispy fried calamari", description="", section="MAINS"), "fish_main", service=SurveyFakeService(), rules=RULES, weights=WeightsTable.load())
    assert not est.applicable
    squid = next(c for c in est.components if c.description == "Calamari, fried")
    assert "unsourced, 12.16.8" in squid.problem and "PR02" in squid.problem and squid.grams_low is None
    starter = estimate_survey_dish(MenuItem(name="Crispy fried calamari", description="", section="STARTERS"), "fish_starter", service=SurveyFakeService(), rules=RULES, weights=WeightsTable.load())
    assert any(c.rule_id == "PR11" and c.grams_low is not None for c in starter.components)                                    # the sourced starter row still portions


def test_dishes_of_an_unsourced_family_are_not_tried_and_count_as_unsized(monkeypatch):
    """12.16.8 at selection: no model call or search credit goes on a fish main or crudo while PR02 and PR03 have no measured source (the seafood chalkboard, 3H run).
    Both rows are sourced again since the second 3I rebuild, so the table is set back for this test; the live table tries them (next test)."""
    from roli_agent.mvp import selection
    monkeypatch.setattr(selection, "RULES", rules_with_unsourced("PR02", "PR03"))
    menu = json.loads((ROOT / "roli_agent" / "runs" / "20261106-221648-2160ad" / "run.json").read_text(encoding="utf-8"))["menu"]
    cands = select_dishes(menu, 14)
    out = [c for c in cands if c.reason.startswith("excluded: no plate-size row")]
    assert len(out) >= 6 and all(c.dish_type in ("fish_main", "crudo_starter") for c in out) and all("12.16.8" in c.reason for c in out)
    assert any(k in unsized_kinds(cands) for k in ("crudo", "whiting", "prawns", "fish")) or unsized_kinds(cands)


def test_the_live_table_tries_fish_mains_and_crudo_again():
    """Second 3I rebuild: with Bonefish stating the fish alone and two sushi chains weighing sashimi, the chalkboard's fish mains and crudo are selected, not excluded under 12.16.8."""
    menu = json.loads((ROOT / "roli_agent" / "runs" / "20261106-221648-2160ad" / "run.json").read_text(encoding="utf-8"))["menu"]
    cands = select_dishes(menu, 14)
    assert not any(c.reason.startswith("excluded: no plate-size row") for c in cands)
    assert {c.dish_type for c in cands if c.decision == "selected"} >= {"fish_main", "crudo_starter"} and len(cands) == 9


# -- 12.16.8a: FNDDS portions as a plate-size source ---------------------------------------------------------------------------------------


def test_only_whole_dish_fillet_or_restaurant_portions_qualify():
    """A cup, spoon, slice, piece, 'Quantity not specified' or an extra-large sharing pizza never qualifies; size words count as a whole item only for item or cut families."""
    from roli_agent.scripts.fndds_portions import qualifies
    assert qualifies("1 small/regular fillet", None, sizes=True)[0] and qualifies("1 steak", None)[0] and qualifies("1 hamburger", None)[0] and qualifies("1 medium fast food order", None)[0]
    assert qualifies("1 Wendy's side salad", None)[0] and qualifies("1 medium pizza (11-12\" diameter)", None, sizes=True)[0]
    for label in ("1 cup", "1 tablespoon", "1 slice", "1 piece, NFS", "Quantity not specified", "1 oz yields", "1 cubic inch", "1 extra-large pizza (16-18\" diameter)", "1 large/jumbo shrimp"):
        assert not qualifies(label, None, sizes=True)[0], label
    assert not qualifies("1 small stick", None)[0] and qualifies("1 small stick", None, sizes=True)[0]            # a size word alone is a whole item only for item families
    assert not qualifies("1 medium/regular/sandwich size roll", None, deny=r"\b(roll|stick|knot)\b")[0]           # the bread family: a roll is not an order
    assert qualifies("1 piece (1/6 of 8\" square)", r"\b(piece)\b")[0]                                             # the dessert family allows a piece


def test_the_fndds_figure_fits_only_the_key_the_row_needs_and_is_converted_by_usda_shares():
    from roli_agent.scripts.build_cards import fndds_figure, apply_fndds, USDA_SHARES
    fam = dict(basis="protein alone (cooked fillet)", records=[dict(fdc_id=2706241, description="Fish, cod, baked or broiled",
               portions=[dict(label="1 small/regular fillet", gram_weight=140, qualifies=True), dict(label="1 large fillet", gram_weight=210, qualifies=True), dict(label="1 cup", gram_weight=135, qualifies=False)])])
    fig = fndds_figure(dict(id="PR02", key="fish_stated", model="P3", unit="g raw fish per plate"), fam)
    assert fig["fits"] and fig["n"] == 2 and fig["ids"] == [2706241] and (fig["low"], fig["high"]) == ((D(140) * USDA_SHARES["fish_baked_raw_per_cooked"]).quantize(D(1)), (D(210) * USDA_SHARES["fish_baked_raw_per_cooked"]).quantize(D(1)))
    whole = fndds_figure(dict(id="PR05", key="plate", model="P2", unit="g plated salad"), fam)
    assert not whole["fits"] and "not the key this row needs" in whole["how"]                                      # a fillet is not a whole plate
    assert fndds_figure(dict(id="PR06", key="none", model="P3", unit="g raw tomato per plate"), fam) is not None and not fndds_figure(dict(id="PR06", key="none", model="P3", unit="x"), fam)["fits"]
    assert fndds_figure(dict(id="PR03", key="raw_fish_plate", model="P3", unit="x"), dict(basis="protein alone (raw fish)", records=[])) is None   # nothing qualifies: no figure
    # apply: the chain figure stays beside the FNDDS range; a gap of more than a third marks sources_disagree and the row still runs
    spec = dict(id="PR16", key="plate", model="P2", unit="g whole item", family="burger")
    ev = dict(key_items=[], n_weighed=260, chains=16, notes=[])
    row = dict(low="83.7", high="424.1", review_status="proposed_unreviewed", basis="plate weight", sources="MenuStat")
    fam2 = dict(basis="whole dish (whole item)", records=[dict(fdc_id=2706927, description="Hamburger", portions=[dict(label="1 hamburger", gram_weight=g, qualifies=True) for g in (115, 145, 175)])])
    row, ev = apply_fndds(spec, row, ev, fam2, "2026-11-06")
    assert (row["low"], row["high"], row["chain_low"], row["chain_high"], row["range_source"]) == ("121.0", "169.0", "83.7", "424.1", "fndds")
    assert row["review_status"] == "sources_disagree" and row["sources_status"].startswith("sources_disagree") and PortionRule({"id": "x", "dish_type": "burger", "model": "P2", **row}).sourced
    close = apply_fndds(spec, dict(low="120", high="170", review_status="proposed_unreviewed", basis="b", sources="s"), dict(key_items=[], n_weighed=5, chains=2, notes=[]), fam2, "2026-11-06")[0]
    assert close["review_status"] == "proposed_unreviewed" and close["sources_status"].startswith("agree")
    none = apply_fndds(dict(id="PR09", key="plate", model="P2", unit="g", family="pasta_main"), dict(low="117.0", high="569.1", review_status="proposed_unreviewed", basis="b", sources="s"), dict(key_items=[], n_weighed=59, chains=13, notes=[]), None, "2026-11-06")[0]
    assert (none["range_source"], none["sources_status"], none["low"]) == ("chain", "chain only", "117.0")


def test_the_table_carries_both_figures_and_the_fndds_range_where_fndds_gives_the_key():
    rows = {r["id"]: r for r in csv.DictReader((ROOT / "roli_agent" / "recipes" / "portion_rules.csv").open(encoding="utf-8"))}
    assert rows["PR02"]["range_source"] == "fndds" and rows["PR02"]["fndds_records"] == "2706241, 2706286, 2706295" and (rows["PR02"]["chain_low"], rows["PR02"]["chain_high"]) == ("211", "317")
    assert rows["PR03"]["range_source"] == "chain" and rows["PR03"]["fndds_low"] == "" and rows["PR05"]["range_source"] == "chain"            # raw fish and caprese: FNDDS has only cups and the unspecified default
    assert rows["PR06"]["range_source"] == "record only" and rows["PR08"]["range_source"] == "record only"
    assert rows["PR15"]["range_source"] == "row as cited" and rows["PR15"]["fndds_low"] == "140" and rows["PR15"]["low"] == "99.9"              # a confirmed row only records the FNDDS figure
    # 12.18 (Julius, 2026-11-07): the four sources_disagree rows take the chain range and the mark is dropped; every row carries his approval
    assert {i for i, r in rows.items() if r["review_status"] == "sources_disagree"} == set()
    assert all(r["approved_by"] == "Julius" and r["approved_on"] == "2026-11-07" for r in rows.values())
    for i, lo, hi in (("PR04", "96.6", "355.6"), ("PR16", "83.7", "424.1"), ("PR17", "128.0", "538.7"), ("PR18", "288.0", "474.0")):
        assert (rows[i]["low"], rows[i]["high"], rows[i]["range_source"]) == (lo, hi, "chain") and rows[i]["fndds_low"] and rows[i]["basis"].startswith("APPROVED RANGE (12.18"), i
    assert (rows["PR01"]["low"], rows["PR01"]["high"], rows["PR01"]["fndds_low"], rows["PR01"]["fndds_high"]) == ("171", "385", "83", "448")


def test_a_section_heading_that_lists_several_kinds_does_not_decide_the_kind():
    """Found by the 3I reruns (Pizzaface, 2026-11-07): "STARTERS, SALADS, SIDES, DIPS" made every salad on the page a dip. A heading listing several kinds describes the
    page; the item's own words decide. A heading naming one kind still decides."""
    from roli_agent.recipes.portions import dish_type_for, section_lists_kinds
    sec = "STARTERS, SALADS, SIDES, DIPS"
    assert section_lists_kinds(sec) and not section_lists_kinds("Desserts & Coffee") and not section_lists_kinds("Kids Menu") and not section_lists_kinds("DIPS")
    assert dish_type_for(MenuItem(name="GARDEN SALAD", description="Rocket, spinach, sundried tomato, olives, cucumber & dressing.", section=sec)) in ("leaf_salad_starter", "side_salad")
    assert dish_type_for(MenuItem(name="HUMMUS", description="", section=sec)) == "dip" and dish_type_for(MenuItem(name="Tzatziki", description="", section="DIPS")) == "dip"
    assert dish_type_for(MenuItem(name="Tiramisu", description="", section="Desserts & Coffee")) == "dessert" and dish_type_for(MenuItem(name="Scrambled Eggs on Toast", description="", section="Kids Menu")) == "kids_dish"

