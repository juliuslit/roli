"""Checkpoint 3H (SPEC_3_mvp.md 12.14): reading fixes, count lines, millilitres, same-food measures, the two nutrient facts, one near-zero rule, one rule for cooking media, external bounds
on their line, the pizza rule, shellfish as seafood, snack bowls apart, tag scoring and the photo 23 key. No network."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from roli_nutrition.portions import Portion

from roli_agent.config import ROOT
from roli_agent.mvp.models import RankedDish
from roli_agent.mvp.ranking import NOT_RESTAURANT, WORD_LIMIT, recommendation_text
from roli_agent.recipes.adapt import DEFAULT_TABLE, WeightsTable
from roli_agent.recipes.compare_dishes import ExternalEvidence, scenario_interval
from roli_agent.recipes.convert import apply_embedded_weight, convert_weight, convert_with_portions
from roli_agent.recipes.equivalence import same_food
from roli_agent.recipes.inference import NutrientFacts, is_plant_record, near_zero, saturated_fat_ceiling
from roli_agent.recipes.models import MatchDecision, MenuItem
from roli_agent.recipes.parse import parse_line
from roli_agent.recipes.portions import PortionRules, dough_weight
from roli_agent.recipes.survey import SurveyMeasurePolicy, fried_record_covers
from roli_agent.scripts.eval_line_tags import moves_a_figure, score

import test_3d_tags_cards as tagged
from recipe_test_helpers import recipe_page
from test_3d_tags_cards import OLIVE_PAGE, OLIVES_ITEM, TaggingLLM, estimate
from test_3g import Lenders

D = Decimal
RULES = PortionRules.load()
THRESHOLD = D("0.1")


def weighed(line: str):
    return apply_embedded_weight(convert_weight(parse_line(line)))


def portion(label, grams, amount=1, measure="undetermined", modifier=""):
    return Portion(amount=amount, measure=measure, modifier=modifier or label, gram_weight=grams, label=label)


# -- 12.14.8a and 12.14.6: reading --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("line, grams, name", [
    ("17-ounce log goat cheese, cut into 12 slices", D(17) * D("28.349523125"), "goat cheese"),
    ("5-ounce package soft fresh goat cheese, coarsely crumbled", D(5) * D("28.349523125"), "soft fresh goat cheese"),
    ("1 kilo cooked tiger prawns (chilled on ice)", D(1000), "cooked tiger prawns"),
])
def test_a_weight_written_in_the_line_is_read_and_the_container_leaves_the_name(line, grams, name):
    p = weighed(line)
    assert p.grams == grams and p.name == name


@pytest.mark.parametrize("line, quantity, unit, name", [
    ("3 Tb. olive oil", D(3), "tbsp", "olive oil"), ("2 fl. oz. Heavy Whipping Cream", D(2), "fl_oz", "heavy whipping cream"), ("2 + 2 tbsp olive oil", D(4), "tbsp", "olive oil"),
    ("1-3/4 to 2 cups all-purpose flour", D("1.875"), "cup", "all-purpose flour"), ("2 handfuls of rocket, washed", D(2), "handful", "rocket"), ("1 ea Yellow Squash, whole", D(1), "each", "yellow squash"),
    ("4 whole cloves", D(4), "each", "whole cloves"), ("4 cloves garlic", D(4), "clove", "garlic"), ("3/4C. peeled, chopped tomatoes", D("0.75"), "cup", "chopped tomatoes"),
])
def test_units_and_names_the_audit_found_misread(line, quantity, unit, name):
    p = parse_line(line)
    assert (p.quantity, p.unit, p.name) == (quantity, unit, name)


@pytest.mark.parametrize("line, grams", [
    ("3 large (560 grams) Russet potatoes (peeled)", D(560)), ("5 red chilis (125g)", D(125)), ("4 medium tomatoes (1 pound), halved", D("453.59237")),
    ("4 (1-inch-thick) slices country-style bread (8 ounces), crust removed", D(8) * D("28.349523125")),
])
def test_a_weight_on_a_count_line_is_the_total(line, grams):
    assert weighed(line).grams == grams


@pytest.mark.parametrize("line, grams", [
    ("4 pork chops, about 6 ounces each, 1-inch thick", D(24) * D("28.349523125")), ("3 chops (10 to 12 ounces each)", D(33) * D("28.349523125")),
    ("2 fillets (6 oz per fillet)", D(12) * D("28.349523125")),
    ("4 (6-ounce) skin-on snapper fillets", D(24) * D("28.349523125")), ("2 (400 g) cans chopped tomatoes", D(800)), ("2 (6- to 8-oz.) ahi tuna steaks", D(14) * D("28.349523125")),
])
def test_each_per_and_an_adjective_weight_are_per_item(line, grams):
    assert weighed(line).grams == grams


def test_four_bone_in_chops_are_not_a_rack():
    chops = [portion("1 chop without refuse", 199)]
    assert convert_with_portions(parse_line("4 bone-in pork chops"), chops, 1).grams == D(796)
    assert convert_with_portions(parse_line("1 (8-rib) pork rack, Frenched"), chops, 1).grams is None


EGGS = [portion("1 cup (4.86 large eggs)", 243), portion("1 medium", 44), portion("1 extra large", 56), portion("1 small", 38), portion("1 jumbo", 63), portion("1 large", 50)]


@pytest.mark.parametrize("line, grams", [("2 Eggland’s Best eggs (large)", 100), ("2 cold large eggs, well beaten", 100), ("1 very fresh large egg (see note)", 50)])
def test_a_size_word_anywhere_in_the_line_picks_the_size(line, grams):
    assert convert_with_portions(parse_line(line), EGGS, 1).grams == D(grams)


AUBERGINE = [portion("1 eggplant, unpeeled (approx 1-1/4 lb)", 548), portion("1 eggplant, peeled (yield from 1-1/4 lb)", 458), portion("1 cup, cubes", 82)]


def test_a_measure_in_the_records_own_word_is_one_item_when_the_line_names_no_size():
    p = convert_with_portions(parse_line("4 aubergines"), AUBERGINE, 1, record="Eggplant, raw")
    assert p.grams == D(2192) and "portion_own_word_item" in p.flags


@pytest.mark.parametrize("line", ["4 small aubergine", "1 large aubergine", "6 Chinese or Japanese eggplants, halved lengthwise"])
def test_a_size_no_record_has_is_never_stretched(line):
    assert convert_with_portions(parse_line(line), AUBERGINE, 1, record="Eggplant, raw").grams is None


def test_a_named_size_the_record_lacks_is_not_taken_from_its_other_sizes():
    onions = [portion("1 medium", 110), portion("1 large", 150)]
    p = convert_with_portions(parse_line("2 small onions"), onions, 1)
    assert p.grams is None


# -- 12.14.9: millilitres -----------------------------------------------------------------------------------------------------------------


def test_millilitres_go_through_the_records_spoon_or_cup():
    oil = [portion("1 tablespoon", 13.5), portion("1 tsp", 4.5), portion("1 cup", 216)]
    p = convert_with_portions(parse_line("200ml rapeseed oil"), oil, 1)
    assert abs(p.grams - D("182.6")) < D("0.3") and "portion_derived_volume" in p.flags
    assert abs(convert_with_portions(parse_line("1 l milk"), [portion("1 cup", 244)], 1).grams - D("1031")) < D(1)


def test_a_spoon_follows_from_a_record_whose_measures_round_apart_but_not_from_one_that_disagrees():
    paste = [portion("1 tbsp", 16), portion("1 cup", 262)]
    assert abs(convert_with_portions(parse_line("1 teaspoon tomato paste"), paste, 1).grams - D("5.33")) < D("0.01")
    assert convert_with_portions(parse_line("1 teaspoon honey"), [portion("1 tbsp", 21), portion("1 cup", 100)], 1).grams is None


# -- 12.14.8b: same-food measures ---------------------------------------------------------------------------------------------------------

ROMA = MatchDecision(name="roma tomatoes", preparation_hint="as_used", fdc_id=1999634, description="Tomato, roma", data_type="Foundation", match_type="direct")


class Measures(Lenders):
    def __init__(self, tables, portions):
        super().__init__(tables, {})
        self.portions = portions

    def get_portions(self, fdc_id):
        return SimpleNamespace(portions=self.portions.get(fdc_id, []))


def lenders(portions, desc="Tomatoes, raw", table="Survey (FNDDS)"):
    return Measures({"Foundation": [], "Survey (FNDDS)": [(1, desc, table)]}, {1: portions})


def test_a_same_food_record_lends_a_whole_item_size_and_a_slice():
    svc = lenders([portion("1 medium", 123), portion("1 slice", 20), portion("Quantity not specified", 99)])
    assert SurveyMeasurePolicy(svc).find(parse_line("4 medium Roma tomatoes"), ROMA).grams == D(492)
    assert SurveyMeasurePolicy(svc).find(parse_line("3 slices tomato"), ROMA).grams == D(60)


def test_no_size_is_stretched_and_a_default_serving_is_not_an_item():
    assert SurveyMeasurePolicy(lenders([portion("1 medium", 123), portion("1 large", 180)])).find(parse_line("2 small tomatoes"), ROMA) is None
    assert SurveyMeasurePolicy(lenders([portion("Quantity not specified", 21)])).find(parse_line("1 tomato"), ROMA) is None


def test_a_lent_item_must_be_one_the_line_names_or_a_size():
    tuna = MatchDecision(name="tuna", preparation_hint="raw", fdc_id=175159, description="Fish, tuna, fresh, yellowfin, raw", data_type="SR Legacy", match_type="direct")
    svc = lenders([portion("0.5 fillet", 198, amount=0.5)], "Fish, tuna, fresh, skipjack, raw", "SR Legacy")
    assert SurveyMeasurePolicy(svc).find(parse_line("1 saku tuna"), tuna) is None


def test_class_level_records_lend_cups_not_items_and_a_substitute_keeps_d21():
    assert SurveyMeasurePolicy(lenders([portion("1 medium", 123)], "Fish, canned")).find(parse_line("2 medium anchovies"), MatchDecision(name="x", preparation_hint="raw", fdc_id=9, description="Fish, anchovy, european, raw", data_type="SR Legacy", match_type="direct")) is None
    assert SurveyMeasurePolicy(lenders([portion("1 medium", 123)])).find(parse_line("4 medium Roma tomatoes"), ROMA.model_copy(update={"match_type": "proxy"})) is None


def test_a_negated_word_does_not_make_a_same_food():
    assert not same_food("Potatoes, raw, skin", "Potatoes, gold, without skin, raw")
    assert same_food("Tomatoes, raw", "Tomato, roma")


# -- 12.14.7: the two facts ---------------------------------------------------------------------------------------------------------------


def record(description="Onions, red, raw", category="Vegetables and Vegetable Products", sat=None, chol=None, fat=None):
    return SimpleNamespace(fdc_id=1, description=description, food_category=category, saturated_fat_g=sat, cholesterol_mg=chol, total_fat_g=fat)


@pytest.mark.parametrize("nut, plant", [
    (record(), True), (record("Vinegar, red wine", "Spices and Herbs"), True), (record("Oil, olive, extra virgin", "Fats and Oils"), True), (record("Flour, wheat", "Cereal Grains and Pasta"), True),
    (record("Butter, salted", "Fats and Oils"), False), (record("Fat, beef tallow", "Fats and Oils"), False), (record("Salad dressing, Italian", "Fats and Oils"), False), (record("Pork, belly", "Pork Products"), False),
])
def test_plant_records_by_usda_category(nut, plant):
    assert is_plant_record(nut) is plant


def facts_for(nut, plain=True):
    return NutrientFacts(SimpleNamespace(get_nutrition=lambda fid: _real(nut)), {"ing_01"} if plain else set())


def _real(nut):
    return nut


LINE = SimpleNamespace(ingredient_id="ing_01", usda=SimpleNamespace(fdc_id=1))


def test_a_plain_plant_food_has_no_cholesterol_and_a_prepared_or_animal_one_stays_missing():
    assert facts_for(record()).rule(LINE, "cholesterol_mg", "high")["value_per_100g"] == 0
    assert facts_for(record(), plain=False).rule(LINE, "cholesterol_mg", "high") is None
    assert facts_for(record("Squid (calamari), frozen", "Finfish and Shellfish Products")).rule(LINE, "cholesterol_mg", "high") is None


def test_saturated_fat_is_between_zero_and_total_fat():
    nut = record(fat=1.7)
    assert saturated_fat_ceiling(nut) == D("1.7")
    assert facts_for(nut).rule(LINE, "saturated_fat_g", "low")["value_per_100g"] == 0 and facts_for(nut).rule(LINE, "saturated_fat_g", "high")["value_per_100g"] == D("1.7")
    assert facts_for(record(fat=None)).rule(LINE, "saturated_fat_g", "high") is None                 # no total fat reported


def test_a_fatty_food_whose_saturated_fat_is_unreported_stays_missing():
    belly = record("Pork, belly, with skin, raw", "Pork Products", chol=66.62, fat=35.83)
    assert saturated_fat_ceiling(belly) is None and facts_for(belly).rule(LINE, "saturated_fat_g", "high") is None


def test_i01_and_i02_are_gone():
    import roli_agent.recipes.inference as inference
    assert not hasattr(inference, "INFERENCE_RULES") and not hasattr(inference, "rule_for")


# -- 12.14.12: one near-zero rule ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("nut, passes", [
    (record(sat=0.04, chol=0), True), (record(fat=0.1), True), (record("Vinegar, red wine", "Spices and Herbs", sat=0.0), True), (record(sat=0.2, chol=0), False), (record(sat=0.05), True),
    (record(fat=0.2), False), (record("Squid", "Finfish and Shellfish Products", sat=0.05), False), (record(), False),
])
def test_near_zero_counts_reported_values_and_the_two_facts(nut, passes):
    assert near_zero(nut, THRESHOLD) is passes


def test_a_counted_line_of_peel_never_holds_up_the_recipe(monkeypatch):
    monkeypatch.setitem(tagged.QUERIES, "thin strips lemon peel", ("lemon peel raw", tagged.LEMON_PEEL, "direct"))
    page = recipe_page("Sicilian Olives", ["300 g green olives", "4 (2 inch) thin strips lemon peel", "Maldon sea salt"], steps="Toss. Serve.")
    est = estimate({"https://a.test/s": page}, MenuItem(name="SICILIAN OLIVES", description="", section="BAR SNACKS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    peel = next(l for l in s.ingredients if "peel" in l.name)
    assert peel.excluded_from_calculation == "negligible_composition" and peel.mass_gap is None and s.calculation["totals"]["saturated_fat_g"]["complete"] is True


def test_the_little_gem_case_keeps_its_weight_the_rule_sets_nutrients_only(monkeypatch):
    monkeypatch.setitem(tagged.QUERIES, "little gem lettuce", ("tomatoes red ripe raw", tagged.TOMATO, "proxy"))
    monkeypatch.setitem(tagged.FOODS, 169247, {**tagged.FOODS[tagged.TOMATO], "fdcId": 169247, "description": "Lettuce, cos or romaine, raw"})      # row W28b's record
    page = recipe_page("Little Gem Salad", ["4 heads little gem lettuce", "300 g tomatoes"], steps="Toss. Serve.")
    est = estimate({"https://a.test/s": page}, MenuItem(name="LITTLE GEM SALAD", description="", section="STARTERS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    gem = next(l for l in s.ingredients if "gem" in l.name)
    assert gem.excluded_from_calculation == "negligible_composition" and gem.mass_gap == "proxy_portion_refused" and s.completeness_by_nutrient["saturated_fat_g"] is True
    (pair,) = est.adapted_pairs
    (a,) = [x for x in pair.assumptions if x.ingredient_id == gem.ingredient_id]
    assert a.mass_only and a.grams_high > a.grams_low > 0                                             # the weighing step still ran
    ps = next(p for p in est.portioned if p.derived_from == pair.pair_id)
    assert ps.applicable and ps.model == "P2" and D(ps.fraction_low.inputs["M_served_g"]) > D(300)   # and the plate weight counts it
    published = next(p for p in est.portioned if p.derived_from == s.scenario_id)
    assert not published.applicable and "little gem" in published.not_applicable_reason               # the published list has no weight for it, so P2 stops there


def test_a_whole_vegetable_with_no_row_stops_the_plate_weight_but_not_the_recipe():
    page = recipe_page("Onion Salad", ["2 heads red onion", "300 g tomatoes"], steps="Slice. Serve.")
    est = estimate({"https://a.test/s": page}, MenuItem(name="ONION SALAD", description="", section="STARTERS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    onion = next(l for l in s.ingredients if "onion" in l.name)
    assert onion.excluded_from_calculation == "negligible_composition" and onion.mass_gap == "no_usda_portion"
    assert all(not p.applicable for p in est.portioned)


def test_menu_only_lines_join_the_tag_call_and_a_near_zero_one_holds_nothing_up(monkeypatch):
    llm = TaggingLLM({})
    page = recipe_page("Tomato Salad", ["300 g tomatoes", "2 tablespoons olive oil"], steps="Toss. Serve.")
    est = estimate({"https://a.test/t": page}, MenuItem(name="TOMATO SALAD", description="red onion", section="STARTERS"), llm)
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    onion = next(l for l in s.ingredients if l.origin == "menu_only")
    assert llm.tag_calls == 1 and "Menu words no recipe lists" in next(p for p in llm.prompts if isinstance(p, str) and p.startswith("You tag"))
    assert onion.tag_kind == "plain_food" and onion.excluded_from_calculation == "negligible_composition" and onion.blocker is None


def test_a_prepared_product_never_passes():
    page = recipe_page("Olives", ["300 g green olives", "salsa verde"], steps="Mix.")
    est = estimate({"https://a.test/o": page}, OLIVES_ITEM, TaggingLLM(tagged.TAGS))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    assert next(l for l in s.ingredients if l.name == "salsa verde").excluded_from_calculation is None


# -- 12.14.2: cooking media ---------------------------------------------------------------------------------------------------------------


def test_w57_and_the_olive_setting_are_gone():
    rows = list(csv.DictReader(DEFAULT_TABLE.open(encoding="utf-8")))
    assert "W57" not in {r["id"] for r in rows} and "gaps" not in rows[0] and "key_record_head" not in rows[0]
    assert not hasattr(RULES, "medium_head") and "medium_record_head" not in RULES.rows[0].__dict__


def test_every_medium_gets_w09s_amount_on_its_own_record(monkeypatch):
    monkeypatch.setitem(tagged.QUERIES, "sunflower oil", ("oil olive", tagged.OLIVE_OIL, "proxy"))
    page = recipe_page("Tomatoes in Oil", ["300 g tomatoes", "1 cup sunflower oil"], steps="Pack the tomatoes in a jar and cover with the oil. Serve from the jar.")
    est = estimate({"https://a.test/t": page}, MenuItem(name="TOMATOES IN OIL", description="", section="STARTERS"), TaggingLLM({"sunflower oil": ("cooking_medium", "plain_food")}))
    (pair,) = est.adapted_pairs
    (a,) = [x for x in pair.assumptions if x.gap == "G6_cooking_medium"]
    assert a.row_id == "W09" and (a.grams_low, a.grams_high) == (D("4.5"), D("13.5")) and a.amount_basis == "per_plate" and a.fdc_id == tagged.OLIVE_OIL


def test_a_deep_fried_dish_a_usda_record_covers_keeps_its_oil_open():
    assert fried_record_covers(MenuItem(name="CRISPY SQUID", description="", section="STARTERS")) and not fried_record_covers(MenuItem(name="PORK CHOP", description="", section="MAINS"))
    page = recipe_page("Fried Squid", ["300 g tomatoes", "1 cup olive oil"], steps="Deep fry. Serve.")
    est = estimate({"https://a.test/f": page}, MenuItem(name="CRISPY SQUID", description="", section="STARTERS"), TaggingLLM({"olive oil": ("cooking_medium", "plain_food")}))
    assert all(a.gap != "G6_cooking_medium" for p in est.adapted_pairs for a in p.assumptions)


# -- 12.14.3: external bounds -------------------------------------------------------------------------------------------------------------


def test_an_external_bound_attaches_to_its_line_with_no_adapted_pair():
    """The crudo of 3D and the Margherita of 3G: the one assumption that made a pair went away, and the line's external bound went with it."""
    page = recipe_page("Tomato Salad", ["600 g tomatoes", "27 g olive oil"], steps="Toss. Serve.")       # larger than the card's plate, so the 12.16.3 ceiling does not refuse it
    est = estimate({"https://a.test/t": page}, MenuItem(name="TOMATO SALAD", description="bottarga", section="STARTERS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    assert est.adapted_pairs == []
    pp = next(p for p in est.portioned if p.derived_from == s.scenario_id)
    pp = pp if pp.applicable else None
    assert pp is not None
    iv = scenario_interval(s, None, pp, None, "saturated_fat_g", ExternalEvidence.load())
    assert iv.tier == "modeled_range_external_bound" and iv.high is not None and iv.external_bound >= 0 and any("bottarga" in x for x in iv.external_bound_sources)


# -- 12.14.10 and 12.14.11 ----------------------------------------------------------------------------------------------------------------

PIZZA = MenuItem(name="MARGHERITA", description="", section="PIZZA")


def pizza(lines, **kw):
    est = estimate({"https://a.test/p": recipe_page("Margherita Pizza", lines, steps=kw.pop("steps", "Top the dough. Bake."), yield_text=kw.pop("yield_text", "4 servings"))}, PIZZA, TaggingLLM({}))
    return next(p for p in est.portioned if p.applicable)


def line(name, grams, quantity=1, text=None):
    return SimpleNamespace(origin="recipe", name=name, line=text or name, parsed=SimpleNamespace(quantity=quantity), conversion=SimpleNamespace(grams=grams))


def test_the_dough_weight_is_stated_a_crust_or_the_sum_of_every_dough_line():
    assert dough_weight([line("pizza dough", D(500)), line("tomatoes", D(100))])[0] == D(500)
    assert dough_weight([line("thin pizza crust", D(283))])[0] == D(283)
    assert dough_weight([line("all-purpose flour", D(300)), line("water", D(200)), line("yeast", D(5)), line("salt", D(7))])[0] == D(512)
    assert dough_weight([line("flour", D(300)), line("water", None)])[0] is None                     # all must be weighed
    assert dough_weight([line("flour", D(300))])[0] is None                                          # no water: not a dough list
    assert dough_weight([line("flour", D(300)), line("water", D(200)), line("semolina", None, None, "semolina, for dusting")])[0] == D(500)


def test_one_plate_is_one_restaurant_pizza_when_the_dough_is_known_capped_at_the_recipe(monkeypatch):
    monkeypatch.setitem(tagged.QUERIES, "pizza dough", ("tomatoes red ripe raw", tagged.TOMATO, "proxy"))
    pr01 = next(r for r in RULES.rows if r.id == "PR01")
    p = pizza(["1000 g pizza dough", "300 g tomatoes"])
    assert (p.fraction_low.fraction, p.fraction_high.fraction) == (pr01.low / 1000, pr01.high / 1000) and p.model == "P1"
    small = pizza([f"{pr01.low + 40} g pizza dough", "300 g tomatoes"])
    assert small.fraction_high.fraction == D(1) and small.fraction_low.fraction == pr01.low / (pr01.low + 40)


def test_the_rule_row_is_a_cited_dough_ball_range():
    row = next(r for r in RULES.rows if r.id == "PR01")
    assert row.low < row.high and "AVPN" in row.sources and "USDA 2708674" in row.basis                 # 12.16: rebuilt from chain pizzas and USDA's dough share; AVPN cited beside it


def test_shellfish_count_as_seafood_on_the_fish_cards():
    for rule_id in ("PR02", "PR03", "PR11"):
        heads = next(r for r in RULES.rows if r.id == rule_id).key_record_heads
        assert {"fish", "crustaceans", "mollusks", "shrimp", "scallops", "crab", "lobster", "mussels", "clams", "oysters"} <= set(heads)
    assert next(r for r in RULES.rows if r.id == "PR15").key_record_heads == ("fish",)


# -- 12.14.4: snack bowls -----------------------------------------------------------------------------------------------------------------


def ranked(rank, name, low="1", high="2", snack=False):
    return RankedDish(rank=rank, key=name, name=name, saturated_fat_low=D(low), saturated_fat_high=D(high), cholesterol_low=D(0), cholesterol_high=D(0), support="close_call", overlaps_with=[], snack=snack)


def test_a_snack_bowl_is_never_in_the_top_three_and_gets_one_line():
    text, words = recommendation_text([ranked(1, "SOUP"), ranked(2, "SALAD", "2", "3"), ranked(3, "FISH", "3", "4"), ranked(4, "SICILIAN OLIVES", "1.0", "3.0", True)], 4, 4, 0)
    assert "Lightest snack: Sicilian Olives, 1.0-3.0 g. " in text and "1) Soup" in text and "4)" not in text and "3) Fish" in text and text.endswith(NOT_RESTAURANT)   # 12.18 wording


def test_the_light_snack_line_goes_first_under_the_word_limit():
    words = "Slow braised Cornish hake fennel saffron"
    picks = [ranked(1, words).model_copy(update={"cholesterol_low": D(200), "cholesterol_high": D(400)}), ranked(2, words + " two").model_copy(update={"cholesterol_low": D(200), "cholesterol_high": D(400)}),
             ranked(3, words + " three")]
    with_snack = picks + [ranked(4, "SIX WORD BOWL OF GREEN OLIVES", snack=True)]
    plain, n = recommendation_text(picks, 3, 14, 11, n_skipped=2)
    text, words_used = recommendation_text(with_snack, 4, 14, 10, n_skipped=2)
    assert n + 9 > WORD_LIMIT and "snack" not in text and words_used <= WORD_LIMIT


def test_a_menu_with_only_snacks_says_so():
    text, _ = recommendation_text([ranked(1, "OLIVES", snack=True)], 1, 5, 4)
    assert "Lightest snack: Olives" in text and "couldn't estimate a main dish" in text


# -- 12.14.5: tag scoring -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text, moves", [("6-8 black peppercorns", False), ("2 sprigs fresh rosemary", False), ("4 strips lemon peel", False), ("Kosher salt", False), ("1/2 cup olive oil", True), ("3 cloves garlic", True), ("300 g olives", True)])
def test_a_line_that_cannot_move_a_figure(text, moves):
    assert moves_a_figure(text) is moves


def test_either_answer_passes_on_such_a_line_and_harmful_counts_only_figures():
    doc = {"recipes": [{"dish": "OLIVES", "title": "Olives", "method": "", "lines": [{"line": "6-8 black peppercorns", "role": "eaten", "kind": "plain_food", "rule": "x"}, {"line": "1 cup olive oil", "role": "eaten", "kind": "plain_food", "rule": "y"}]}]}
    result = score(doc, TaggingLLM({"peppercorn": ("removed", "plain_food"), "olive oil": ("cooking_medium", "plain_food")}))
    assert result["role_correct"] == 1 and len(result["no_figure_moved"]) == 1 and [m["line"] for m in result["harmful_misses"]] == ["1 cup olive oil"]


# -- 12.14.1: the key ---------------------------------------------------------------------------------------------------------------------


def test_the_chalkboards_key_attaches_the_shared_line_to_each_fish():
    record_ = json.loads((ROOT / "menu_reader_eval" / "expected" / "menu_23.json").read_text(encoding="utf-8"))["expected"]
    names = {i["name"]: i for i in record_["items"]}
    assert not any(n.startswith("Watermelon") for n in names)
    assert all("watermelon" in names[f]["description"] for f in ("Ocean Trout", "North Qld Barramundi", "Cobia", "Snapper"))
    assert (ROOT / "menu_test_set" / "answer_key_backup_before_23_garnish_edit_2026-11-06.csv").exists()
