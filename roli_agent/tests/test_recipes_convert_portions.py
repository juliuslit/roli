"""2B-2 conversions (D4, requirement 3): embedded weights, USDA portion weights, D15 yield recovery, D17 refusal memory."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from roli_nutrition import Portion
from roli_nutrition.portions import extract_portions

from roli_agent.recipes.convert import apply_embedded_weight, convert_weight, convert_with_portions
from roli_agent.recipes.extract import extract_recipe, recover_yield_from_text
from roli_agent.recipes.fetch import PoliteFetcher, RefusalMemory
from roli_agent.recipes.parse import parse_line

from conftest import load
from recipe_test_helpers import BREAD, LETTUCE, OLIVE, ROMANO, TAHINI, TOMATO, recipe_page
from test_recipes_fetch_search import Site

D = Decimal


def portions_of(fixture: str, fdc_id: int):
    return extract_portions(fdc_id, load(fixture)).portions


def line(text: str):
    return apply_embedded_weight(convert_weight(parse_line(text)))


# -- embedded weights -----------------------------------------------------------------------------


@pytest.mark.parametrize("text, grams, total", [
    ("1 (14 oz) can San Marzano tomatoes", D("14") * D("28.349523125"), False),
    ("2 (6-ounce) salmon fillets", D("12") * D("28.349523125"), False),            # per item x 2
    ("2 (400 g) cans chopped tomatoes", D(800), False),
    ("4 salmon fillets (about 1.5 pounds)", D("1.5") * D("453.59237"), True),       # "about" with a count > 1: total
    ("1 whole chicken (about 4 pounds)", D(4) * D("453.59237"), False),             # count 1: same either way
    ("3 fillets (6 oz each)", D(18) * D("28.349523125"), False),
])
def test_embedded_weight_is_read_explicitly_not_lost(text, grams, total):
    p = line(text)
    assert p.grams == grams and "embedded_weight" in p.flags and "conversion_pending_usda_portion" not in p.flags
    assert ("embedded_weight_total_assumed" in p.flags) is total
    assert "embedded weight" in p.grams_reference and ("NIST" in p.grams_reference or "(400 g)" in text)


def test_embedded_non_weight_parenthetical_is_ignored():
    p = line("1 pound (1-inch thick) salmon fillets, skin removed")
    assert p.grams == D("453.59237") and "embedded_weight" not in p.flags          # the explicit pound wins; the inch note is not a weight
    q = line("4 tomatoes (cut into wedges)")
    assert q.grams is None and "conversion_pending_usda_portion" in q.flags


# -- USDA portions ----------------------------------------------------------------------------------


def test_tablespoon_of_olive_oil_uses_the_records_portion():
    p = convert_with_portions(line("2 tablespoons extra-virgin olive oil"), portions_of("food_171413", OLIVE), OLIVE)
    assert p.grams == D(27) and p.grams_reference == "USDA 171413 portion '1 tablespoon' = 13.5 g"
    assert "usda_portion" in p.flags and "conversion_pending_usda_portion" not in p.flags
    tsp = convert_with_portions(line("1/2 tsp olive oil"), portions_of("food_171413", OLIVE), OLIVE)
    assert tsp.grams == D("2.25")
    cup = convert_with_portions(line("1/4 cup olive oil"), portions_of("food_171413", OLIVE), OLIVE)
    assert cup.grams == D(54)


def test_count_portions_use_the_lines_own_words_or_stated_size_never_a_default():
    tomato = portions_of("food_170457", TOMATO)
    plum = convert_with_portions(line("4 ripe plum tomatoes, cut into thin rounds"), tomato, TOMATO)
    assert plum.grams == D(248) and "plum tomato" in plum.grams_reference                 # 4 x 62 g
    cherry = convert_with_portions(line("10 cherry tomatoes, halved"), tomato, TOMATO)
    assert cherry.grams == D(170)                                                          # 10 x 17 g
    plain = convert_with_portions(line("3 tomatoes"), tomato, TOMATO)
    assert plain.grams is None and "portion_size_unspecified" in plain.flags               # D20: sizes exist, the line names none -> unresolved
    medium = convert_with_portions(line("3 medium tomatoes"), tomato, TOMATO)
    assert medium.grams == D(369)                                                          # the source names the size
    large = convert_with_portions(line("2 large tomatoes"), tomato, TOMATO)
    assert large.grams == D(364)                                                           # 2 x 182 g via the 'large' unit


def test_cup_with_modifier_matches_the_right_cup_portion():
    tomato = portions_of("food_170457", TOMATO)
    chopped = convert_with_portions(line("1 cup chopped tomatoes"), tomato, TOMATO)
    assert chopped.grams == D(180) and "cup, chopped or sliced" in chopped.grams_reference
    cherry_cup = convert_with_portions(line("2 cups cherry tomatoes"), tomato, TOMATO)
    assert cherry_cup.grams == D(298)
    ambiguous = convert_with_portions(line("1 cup tomatoes"), tomato, TOMATO)            # two cup portions, nothing to choose by
    assert ambiguous.grams is None and "portion_ambiguous" in ambiguous.flags
    lettuce = convert_with_portions(line("2 cups shredded lettuce"), portions_of("food_169249", LETTUCE), LETTUCE)
    assert lettuce.grams == D(72)
    lettuce_plain = convert_with_portions(line("2 cups lettuce"), portions_of("food_169249", LETTUCE), LETTUCE)
    assert lettuce_plain.grams == D(72) and "portion_modifier_unmatched" in lettuce_plain.flags   # the only cup portion is 'cup shredded'


def test_slices_tbsp_and_missing_units():
    bread = convert_with_portions(line("2 slices sourdough bread, torn"), portions_of("food_172675", BREAD), BREAD)
    assert bread.grams == D(278)
    tahini = convert_with_portions(line("3 tablespoons tahini"), portions_of("food_170189", TAHINI), TAHINI)
    assert tahini.grams == D(45)
    romano_cup = convert_with_portions(line("1/2 cup grated pecorino romano"), portions_of("food_171249", ROMANO), ROMANO)
    assert romano_cup.grams is None and "portion_none_for_unit" in romano_cup.flags       # romano lists oz and package only
    eggs = convert_with_portions(line("2 large eggs"), [Portion(amount=1, measure="undetermined", modifier="large", gram_weight=50.0, label="1 large"),
                                                        Portion(amount=1, measure="undetermined", modifier="extra large", gram_weight=56.0, label="1 extra large")], 1)
    assert eggs.grams == D(100)


def test_portion_conversion_never_touches_known_grams_or_unknown_quantities():
    weight = convert_with_portions(line("85 g sushi-grade bluefin tuna"), portions_of("food_173706", 173706), 173706)
    assert weight.grams == D(85) and "usda_portion" not in weight.flags
    vague = convert_with_portions(line("Salt, to taste"), portions_of("food_171413", OLIVE), OLIVE)
    assert vague.grams is None and vague.grams != D(0)


# -- D15 yield recovery -------------------------------------------------------------------------------


@pytest.mark.parametrize("text, expected", [
    ("<p>This tuna crudo serves 4 as a starter.</p>", "serves 4"),
    ("<p>Yield: 6 servings</p>", "Yield: 6 servings"),
    ("<p>Makes 8 servings of soup.</p>", "Makes 8 servings"),
    ("<p>Makes 2 pizzas. Enjoy.</p>", ""),                                 # no serving word: no evidence
    ("<p>Cut into 8 slices.</p>", ""),
    ("<p>Serves 4-6 people</p>", "Serves 4-6 people"),
])
def test_yield_recovered_from_page_text_only_with_serving_words(text, expected):
    assert recover_yield_from_text(f"<html><body>{text}</body></html>") == expected


def test_yield_fallback_is_used_only_when_structured_yield_is_missing():
    page = recipe_page("Crudo", ["85 g tuna", "1 tbsp oil"], yield_text="")
    page = page.replace("<body>", "<body><p>This recipe serves 4.</p>")
    ex = extract_recipe(page, "https://x.test/r")
    assert ex.yield_text == "serves 4" and ex.yield_source == "page_text" and "yield_from_page_text" in ex.flags
    structured = extract_recipe(recipe_page("Crudo", ["85 g tuna", "1 tbsp oil"], yield_text="2 servings").replace("<body>", "<body><p>serves 9</p>"), "https://x.test/r")
    assert structured.yield_text == "2 servings" and structured.yield_source == "structured"


# -- D17 refusal memory -------------------------------------------------------------------------------


def test_host_refusing_twice_is_skipped_but_one_refusal_is_retried(tmp_path):
    def site(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(403)
    memory = RefusalMemory(tmp_path / "refused.json", clock=lambda: 1000.0)
    f = PoliteFetcher(transport=httpx.MockTransport(site), sleep=lambda s: None, refusals=memory)
    assert f.fetch("https://wall.test/a")[0].status == "http_error"
    assert f.fetch("https://wall.test/b")[0].status == "http_error"            # second refusal still tried
    third = f.fetch("https://wall.test/c")[0]
    assert third.status == "host_refused" and "D17" in third.detail             # now skipped without a request
    reloaded = RefusalMemory(tmp_path / "refused.json", clock=lambda: 1000.0 + 8 * 24 * 3600)
    assert reloaded.should_skip("wall.test") is False                           # memory expires after a week


def test_foundation_measure_names_and_whole_items_median_only_for_comparable_sizes():
    garlic = [Portion(amount=1, measure="clove", modifier="", gram_weight=3.0, label="1 clove"), Portion(amount=1, measure="RACC", modifier="", gram_weight=2.0, label="1 RACC")]
    p = convert_with_portions(line("2 cloves garlic"), garlic, 1104647)
    assert p.grams == D(6) and "1 clove" in p.grams_reference
    q = convert_with_portions(line("2 garlic cloves"), garlic, 1104647)                       # "cloves" at the end of the name is the unit (2C.1)
    assert q.grams == D(6) and "unit_from_name" in q.flags and q.name == "garlic"
    w = convert_with_portions(line("2 garlics"), garlic, 1104647)                             # a true bare count on a clove-only record
    assert w.grams == D(6) and "portion_whole_item" in w.flags
    lemon = [Portion(amount=1, measure="undetermined", modifier='fruit (2-1/8" dia)', gram_weight=58.0, label='1 fruit (2-1/8" dia)'),
             Portion(amount=1, measure="undetermined", modifier="wedge or slice (1/8 of one 2-1/8\" dia lemon)", gram_weight=7.0, label="1 wedge or slice")]
    assert convert_with_portions(line("1 lemon (zested)"), lemon, 167746).grams == D(58)
    assert convert_with_portions(line("1 medium lemon"), lemon, 167746).grams == D(58)        # size word with no size portion -> whole item
    orange = [Portion(amount=1, measure="undetermined", modifier="fruit (2-5/8\" dia)", gram_weight=131.0, label="1 fruit (2-5/8\" dia)"),
              Portion(amount=1, measure="undetermined", modifier="large (3-1/16\" dia)", gram_weight=184.0, label="1 large (3-1/16\" dia)"),
              Portion(amount=1, measure="undetermined", modifier="small (2-3/8\" dia)", gram_weight=96.0, label="1 small (2-3/8\" dia)")]
    o = convert_with_portions(line("1/2 orange (juiced)"), orange, 169097)
    # D20 revised (2026-11-03): three comparable sized labels (96, 131, 184 g) -> the median 131 g, flagged as an assumption, options kept
    assert o.grams == D("65.5") and "assumed_size_median" in o.flags and "portion_size_unspecified" not in o.flags
    assert o.grams_reference.startswith("ASSUMED size: median of 3 comparable whole-item sizes") and {x["grams_per_unit"] for x in o.portion_options} == {"96", "131", "184"}
    mixed = orange + [Portion(amount=1, measure="undetermined", modifier="fruit", gram_weight=140.0, label="1 fruit")]
    m = convert_with_portions(line("1/2 orange (juiced)"), mixed, 169097)
    assert m.grams is None and "portion_size_unspecified" in m.flags                        # an unsized "1 fruit" beside sizes: kinds differ, no median
    assert convert_with_portions(line("1 large orange"), orange, 169097).grams == D(184)


def test_volume_derived_from_another_volume_portion_of_the_same_record():
    tamari = [Portion(amount=1, measure="undetermined", modifier="tbsp", gram_weight=18.0, label="1 tbsp"), Portion(amount=1, measure="undetermined", modifier="cup", gram_weight=288.0, label="1 cup")]
    cup = convert_with_portions(line("1/4 cup tamari"), tamari, 174278)
    assert cup.grams == D(72) and "portion_derived_volume" not in cup.flags                    # a cup portion exists: used directly
    honey = [Portion(amount=1, measure="undetermined", modifier="tbsp", gram_weight=21.0, label="1 tbsp")]
    tsp = convert_with_portions(line("1/2 teaspoon honey"), honey, 169640)
    assert tsp.grams == D("0.5") * D("4.92892159375") * (D(21) / D("14.78676478125")) and "portion_derived_volume" in tsp.flags
    assert "g/ml" in tsp.grams_reference and "1 tbsp" in tsp.grams_reference
    tomato = portions_of("food_170457", TOMATO)
    pint = convert_with_portions(line("1 pint cherry tomatoes (halved)"), tomato, TOMATO)     # 'cup cherry tomatoes' names the line's own word (2C.1)
    assert pint.grams == D(2) * D(149) and "portion_derived_volume" in pint.flags and "cup cherry tomatoes" in pint.grams_reference
    plain_pint = convert_with_portions(line("1 pint tomatoes"), tomato, TOMATO)               # no plain cup, no label matching the line: unknown
    assert plain_pint.grams is None and "portion_none_for_unit" in plain_pint.flags
    chopped_only = [Portion(amount=1, measure="undetermined", modifier="cup, chopped", gram_weight=180.0, label="1 cup, chopped")]
    assert convert_with_portions(line("2 tbsp tomatoes"), chopped_only, TOMATO).grams is None   # a modified cup is not a density source


@pytest.mark.parametrize("text, grams", [
    ("One 8-ounce loin sushi-grade yellowfin tuna, cut into 1-inch cubes", D(8) * D("28.349523125")),
    ("two 6 oz salmon fillets, skin on", D(12) * D("28.349523125")),
    ("1 8-oz block feta", D(8) * D("28.349523125")),
    ("2 400 g cans chopped tomatoes", D(800)),
])
def test_inline_weight_after_the_count_wins_over_the_count(text, grams):
    p = line(text)
    assert p.grams == grams and "inline_weight" in p.flags and "embedded_weight" in p.flags
    assert p.unit in ("each", "can") and p.quantity in (D(1), D(2))
    tuna = convert_with_portions(line("One 8-ounce loin sushi-grade yellowfin tuna, cut into 1-inch cubes"),
                                 [Portion(amount=1, measure="undetermined", modifier="cubic inch, boneless", gram_weight=16.0, label="1 cubic inch, boneless")], 175159)
    assert tuna.grams == D(8) * D("28.349523125")                                            # the weight stands; no portion is consulted
    assert line("1 cup 2% milk").grams is None                                              # a number followed by % is not a weight


def test_cubic_inch_and_slice_labels_never_serve_a_bare_count():
    cubes = [Portion(amount=1, measure="undetermined", modifier="cubic inch, boneless", gram_weight=16.0, label="1 cubic inch, boneless")]
    p = convert_with_portions(line("1 saku tuna block"), cubes, 175159)
    assert p.grams is None and "portion_none_for_unit" in p.flags


def test_proxy_records_lend_volume_measures_only():
    romaine = [Portion(amount=1, measure="undetermined", modifier="head", gram_weight=626.0, label="1 head"),
               Portion(amount=1, measure="undetermined", modifier="cup shredded", gram_weight=47.0, label="1 cup shredded")]
    heads = convert_with_portions(line("3 baby gem lettuce, leaves separated"), romaine, 169247, proxy=True)
    assert heads.grams is None and "proxy_count_portion_refused" in heads.flags             # D21: a romaine head is not a little gem head
    cups = convert_with_portions(line("2 cups shredded little gem"), romaine, 169247, proxy=True)
    assert cups.grams == D(94) and "proxy_volume_portion" in cups.flags and "approximation" in cups.grams_reference
    direct = convert_with_portions(line("3 romaine lettuce"), romaine, 169247)
    assert direct.grams == D(1878)                                                           # the record's own food: the head applies


def test_derived_volume_tolerates_rounded_usda_measures_within_two_percent():
    honey = [Portion(amount=1, measure="undetermined", modifier="cup", gram_weight=339.0, label="1 cup"), Portion(amount=1, measure="undetermined", modifier="tbsp", gram_weight=21.0, label="1 tbsp")]
    p = convert_with_portions(line("1/2 teaspoon honey"), honey, 169640)      # 1.433 vs 1.420 g/ml: USDA rounding, not a different food
    assert p.grams is not None and "portion_derived_volume" in p.flags
    odd = [Portion(amount=1, measure="undetermined", modifier="cup", gram_weight=100.0, label="1 cup"), Portion(amount=1, measure="undetermined", modifier="tbsp", gram_weight=21.0, label="1 tbsp")]
    assert convert_with_portions(line("1/2 teaspoon honey"), odd, 169640).grams is None
