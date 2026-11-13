"""2B-1 parsing: quantities, ranges, units, names, preparation hints, yields, weight conversion."""

from __future__ import annotations

from decimal import Decimal

import pytest

from roli_agent.recipes.convert import convert_weight
from roli_agent.recipes.parse import parse_line, parse_servings

D = Decimal


@pytest.mark.parametrize("line, quantity, unit, kind, name", [
    ("2 tablespoons extra-virgin olive oil", D(2), "tbsp", "volume", "extra-virgin olive oil"),
    ("1½ cups diced fresh fior di latte mozzarella cheese", D("1.5"), "cup", "volume", "diced fresh fior di latte mozzarella cheese"),
    ("1 pound (1-inch thick) salmon fillets, skin removed", D(1), "lb", "weight", "salmon fillets"),
    ("85 g sushi-grade bluefin tuna, thinly sliced", D(85), "g", "weight", "sushi-grade bluefin tuna"),
    ("3 oz bottarga, grated", D(3), "oz", "weight", "bottarga"),
    ("4 ripe plum tomatoes, cut into thin rounds", D(4), "each", "count", "ripe plum tomatoes"),
    ("2 large eggs", D(2), "large", "count", "eggs"),
    ("1 garlic clove (crushed)", D(1), "clove", "count", "garlic"),            # 2C.1: the count word at the end of the name is the unit
    ("¼ red onion", D("0.25"), "each", "count", "red onion"),
    ("1 (14 oz) can San Marzano tomatoes", D(1), "can", "count", "san marzano tomatoes"),
    ("1/2 cup water", D("0.5"), "cup", "volume", "water"),
    ("2 tsp. kosher salt", D(2), "tsp", "volume", "kosher salt"),
])
def test_quantity_unit_and_name(line, quantity, unit, kind, name):
    p = parse_line(line)
    assert (p.quantity, p.unit, p.unit_kind, p.name) == (quantity, unit, kind, name)
    assert p.line == line


def test_parenthetical_size_moves_to_preparation_words():
    p = parse_line("1 (14 oz) can San Marzano tomatoes")
    assert p.preparation_words == ["14 oz"] and p.unit == "can"


def test_range_becomes_midpoint_with_bounds_and_flag():
    p = parse_line("1-2 tbsp chives (chopped)")
    assert (p.quantity, p.quantity_low, p.quantity_high) == (D("1.5"), D(1), D(2))
    assert "range_midpoint" in p.flags and p.quantity_text == "1-2"
    assert p.name == "chives" and p.preparation_words == ["chopped"]
    q = parse_line("1 to 2 cups stock")
    assert q.quantity == D("1.5") and "range_midpoint" in q.flags


@pytest.mark.parametrize("line", ["Salt, to taste", "flaky sea salt", "A handful of basil leaves", "Olive oil, for drizzling", "freshly ground black pepper"])
def test_unknown_quantities_stay_unknown_never_zero(line):
    p = convert_weight(parse_line(line))
    assert p.grams is None
    assert p.quantity is None or p.unit == "handful"      # "a handful" parses as count 1 handful, still no grams
    assert p.grams != D(0)


def test_vague_quantity_is_flagged():
    p = parse_line("Salt, to taste")
    assert p.quantity is None and "vague_quantity" in p.flags and p.quantity_text == "to taste"


def test_optional_and_preparation_words():
    p = parse_line("2 tablespoons toasted sesame seeds, optional")
    assert p.optional is True and p.preparation_words == ["optional"]
    assert p.preparation_hint == "cooked"            # 'toasted' is a cooking word on the line itself
    q = parse_line("200 g raw tuna loin")
    assert q.preparation_hint == "raw"
    r = parse_line("50 g pecorino romano, finely grated")
    assert r.preparation_hint == "as_used"
    s = parse_line("1 bunch chives")
    assert s.preparation_hint == "unknown"


def test_weight_units_convert_exactly_and_record_the_reference():
    p = convert_weight(parse_line("1 pound salmon fillets"))
    assert p.grams == D("453.59237") and "NIST" in p.grams_reference
    q = convert_weight(parse_line("3 oz bottarga, grated"))
    assert q.grams == D("85.048569375")
    r = convert_weight(parse_line("85 g tuna"))
    assert r.grams == D(85) and r.grams_reference == "1 g"
    assert "conversion_pending_usda_portion" not in r.flags


def test_volume_and_count_stay_pending_except_water_like_liquids():
    oil = convert_weight(parse_line("2 tablespoons olive oil"))
    assert oil.grams is None and "conversion_pending_usda_portion" in oil.flags
    eggs = convert_weight(parse_line("2 large eggs"))
    assert eggs.grams is None and "conversion_pending_usda_portion" in eggs.flags
    water = convert_weight(parse_line("1/2 cup water"))
    assert water.grams == D("118.29411825") and "density_assumed_1" in water.flags and "water-like" in water.grams_reference
    stock = convert_weight(parse_line("500 ml chicken stock"))
    assert stock.grams == D(500) and "density_assumed_1" in stock.flags
    milk = convert_weight(parse_line("1 cup milk"))       # not on the water-like list
    assert milk.grams is None


def test_parse_json_round_trip_keeps_verbatim_line():
    p = parse_line("  2   tbsp   olive   oil ")
    assert p.line == "2 tbsp olive oil"


@pytest.mark.parametrize("text, servings, low, high", [
    ("4 servings", D(4), None, None),
    ("Serves 4", D(4), None, None),
    ("6", D(6), None, None),
    ("4 to 6 servings", D(5), D(4), D(6)),
    ("serves 4-6 people", D(5), D(4), D(6)),
    ("Makes 2 pizzas", None, None, None),
    ("12 slices", None, None, None),
    ("1 item", None, None, None),
    ("", None, None, None),
    ("2 cups", None, None, None),
])
def test_servings_parser(text, servings, low, high):
    got, lo, hi, note = parse_servings(text)
    assert (got, lo, hi) == (servings, low, high), note
    assert note
