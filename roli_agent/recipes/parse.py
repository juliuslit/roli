"""Deterministic parsing of ingredient lines and yield text (spec 2B section 4). No LLM."""

from __future__ import annotations

import re
from decimal import Decimal

from .models import ParsedIngredient, PreparationHint, UnitKind

FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8"}
WORD_NUMBERS = {"a": "1", "an": "1", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "half": "1/2", "dozen": "12"}

UNITS: dict[str, tuple[str, UnitKind]] = {
    # weight
    "g": ("g", "weight"), "gram": ("g", "weight"), "grams": ("g", "weight"), "gr": ("g", "weight"),
    "kg": ("kg", "weight"), "kilogram": ("kg", "weight"), "kilograms": ("kg", "weight"), "kilo": ("kg", "weight"), "kilos": ("kg", "weight"),
    "mg": ("mg", "weight"),
    "oz": ("oz", "weight"), "ounce": ("oz", "weight"), "ounces": ("oz", "weight"),
    "lb": ("lb", "weight"), "lbs": ("lb", "weight"), "pound": ("lb", "weight"), "pounds": ("lb", "weight"),
    # volume
    "ml": ("ml", "volume"), "milliliter": ("ml", "volume"), "milliliters": ("ml", "volume"), "millilitre": ("ml", "volume"), "millilitres": ("ml", "volume"),
    "l": ("l", "volume"), "liter": ("l", "volume"), "liters": ("l", "volume"), "litre": ("l", "volume"), "litres": ("l", "volume"),
    "tsp": ("tsp", "volume"), "teaspoon": ("tsp", "volume"), "teaspoons": ("tsp", "volume"),
    "tbsp": ("tbsp", "volume"), "tbs": ("tbsp", "volume"), "tb": ("tbsp", "volume"), "tablespoon": ("tbsp", "volume"), "tablespoons": ("tbsp", "volume"),
    "cup": ("cup", "volume"), "cups": ("cup", "volume"), "c": ("cup", "volume"),
    "fl oz": ("fl_oz", "volume"), "fluid ounce": ("fl_oz", "volume"), "fluid ounces": ("fl_oz", "volume"),
    "pint": ("pint", "volume"), "pints": ("pint", "volume"), "quart": ("quart", "volume"), "quarts": ("quart", "volume"),
    # count-like
    "clove": ("clove", "count"), "cloves": ("clove", "count"), "slice": ("slice", "count"), "slices": ("slice", "count"),
    "piece": ("piece", "count"), "pieces": ("piece", "count"), "head": ("head", "count"), "heads": ("head", "count"),
    "sprig": ("sprig", "count"), "sprigs": ("sprig", "count"), "leaf": ("leaf", "count"), "leaves": ("leaf", "count"),
    "bunch": ("bunch", "count"), "bunches": ("bunch", "count"), "stalk": ("stalk", "count"), "stalks": ("stalk", "count"),
    "can": ("can", "count"), "cans": ("can", "count"), "fillet": ("fillet", "count"), "fillets": ("fillet", "count"),
    "large": ("large", "count"), "medium": ("medium", "count"), "small": ("small", "count"),
    "pinch": ("pinch", "count"), "pinches": ("pinch", "count"), "dash": ("dash", "count"), "handful": ("handful", "count"), "handfuls": ("handful", "count"), "handfull": ("handful", "count"),
}
# Common misspellings seen on recipe pages (2C.1, requirement A): read as the unit they obviously mean, flagged `unit_typo_corrected`.
UNIT_TYPOS: dict[str, str] = {
    "tabelspoon": "tbsp", "tabelspoons": "tbsp", "tabespoon": "tbsp", "tabespoons": "tbsp", "tablespon": "tbsp", "tablespons": "tbsp",
    "tablspoon": "tbsp", "tablspoons": "tbsp", "tbps": "tbsp", "tbsps": "tbsp", "tbl": "tbsp", "tbls": "tbsp",
    "teaspon": "tsp", "teaspons": "tsp", "teasppon": "tsp", "tsps": "tsp", "teaspoonful": "tsp", "teaspoonfuls": "tsp",
    "ounzes": "oz", "ounze": "oz", "onces": "oz", "pounds.": "lb", "gramm": "g", "gramms": "g",
}
for _typo, _unit in UNIT_TYPOS.items():
    UNITS.setdefault(_typo, (_unit, next(k for _, (u, k) in UNITS.items() if u == _unit)))
# Words at the end of a food name that are really the unit of count: "2 garlic cloves" = 2 cloves of garlic.
COUNT_WORDS_IN_NAME = {"clove", "cloves", "sprig", "sprigs", "head", "heads", "stalk", "stalks", "bunch", "bunches", "slice", "slices", "leaf", "leaves"}
SUB_RECIPE_TAIL = re.compile(r"\b(recipe follows|recipe below|see recipe below|see recipe|recipe above|see below)\b", re.I)
SUB_RECIPE_HEAD = re.compile(r"^\s*(?:\d+\s+)?(?:recipe|batch)\s+(?:of\s+)?(?P<name>.+)$", re.I)
PLUS_SPLIT = re.compile(r",?\s+plus\s+(?=\d)", re.I)
UNIT_PATTERN = "|".join(sorted((re.escape(u) for u in UNITS), key=len, reverse=True))

VAGUE = re.compile(r"\b(to taste|as needed|as desired|for serving|for garnish|optional|a few|some|a little|a splash|a drizzle|drizzle)\b", re.I)
OPTIONAL = re.compile(r"\b(optional|for serving|for garnish|to serve|if desired)\b", re.I)
COOKED_WORDS = re.compile(r"\b(cooked|roasted|roast|baked|grilled|broiled|fried|sauteed|sautéed|toasted|steamed|boiled|braised|seared|charred|smoked)\b", re.I)
RAW_WORDS = re.compile(r"\b(raw|sashimi[- ]grade|sushi[- ]grade|uncooked)\b", re.I)
AS_USED_CLASSES = re.compile(r"\b(oil|olive oil|butter|ghee|vinegar|lemon juice|lime juice|cheese|pecorino|parmesan|parmigiano|romano|mozzarella|"
                             r"burrata|ricotta|feta|yogurt|cream|mayonnaise|mustard|honey|sugar|salt|pepper|tahini|sesame seeds|seeds|nuts|"
                             r"bread|sourdough|croutons|breadcrumbs|panko|flour|passata|sauce|anchov|caper|olive|bottarga)\w*", re.I)
# Non-flesh products whose name may carry a cooking word that names the product, not a step the recipe performs: the USDA record is the product as sold.
PRODUCT_NAMED_BY_METHOD = re.compile(r"\b(paprika|cumin|coriander|cardamom|caraway|spices?|powder|flakes|sauce|paste|pur[eé]e|pesto|dressing|vinaigrette|"
                                     r"stock|broth|salts?|sugar|syrup|cheese|mozzarella|provola|scamorza|gouda|cheddar|tofu|tomato sauce)\b", re.I)
# (toasted nuts and seeds keep the cooked hint: the word rightly steers the matcher to the roasted/toasted USDA record)
NUMBER = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)"
QTY_RE = re.compile(rf"^\s*(?P<q>{NUMBER}(?:\s*(?:-|–|—|to)\s*{NUMBER})?)\s*(?P<rest>.*)$", re.S)
# 12.14.8a: "17-ounce log goat cheese" states the line's weight; the container word is not part of the food's name.
HYPHEN_WEIGHT = re.compile(r"^-(?=(?:oz|ounces?|lbs?|pounds?|g|grams?|kg|kilograms?)\b)", re.I)
CONTAINER_WORDS = re.compile(r"^(?:logs?|packages?|packs?|pkgs?|blocks?|containers?|tubs?|bags?|jars?|cartons?|wedges?)\s+(?:of\s+)?(?=\S)", re.I)
# A first comma piece that only describes the food: "crisp, fresh romaine lettuce", "peeled, chopped tomatoes". The food's name is in the next piece.
ONLY_DESCRIBES = re.compile(r"^(?:(?:very|extra|fresh|freshly|crisp|cold|ripe|whole|peeled|trimmed|washed|chopped|sliced|diced|minced|good|small|medium|large|thin|thick)\s*)+$", re.I)
# "1 ea Shallot": "each" written as a word, no unit of its own
EACH_WORD = re.compile(r"^\s*(?:ea\.?|each)\s+(?=\S)", re.I)
# A count unit followed only by a description: "4 whole cloves" are the spice, not cloves of something called "whole".
UNIT_IS_THE_FOOD = re.compile(r"^(?:whole|ground)$", re.I)
# A second measure after a slash: "4 oz / 113 g feta", "2 Tablespoons/30g oil", "1 cup / 240 ml milk". It is a note on the line, not part of the food's name (12.12.5).
SLASH_MEASURE = re.compile(rf"^\s*/\s*(?P<m>{NUMBER}(?:\s*(?:-|–|—|to)\s*{NUMBER})?\s*-?\s*(?:{UNIT_PATTERN})\b\.?)\s*(?P<rest>.*)$", re.I | re.S)
# A weight written right after the count, per item: "One 8-ounce loin", "two 6 oz fillets", "1 8-oz block". The weight wins over the count.
INLINE_WEIGHT = re.compile(r"^\s*(?P<q>\d+(?:[.,]\d+)?(?:\s+\d/\d)?|\d/\d)\s*-?\s*(?P<u>oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg|kilogram|kilograms)\b\.?\s+(?=[a-zA-Z])(?P<rest>.*)$", re.I | re.S)


def _to_decimal(token: str) -> Decimal:
    token = token.strip().replace(",", ".")
    if " " in token:                       # mixed number "1 1/2"
        whole, frac = token.split()
        return Decimal(whole) + _to_decimal(frac)
    if "/" in token:
        num, den = token.split("/")
        return Decimal(num) / Decimal(den)
    return Decimal(token)


def _normalise_numbers(text: str) -> str:
    for glyph, ascii_frac in FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{glyph}", rf"\1 {ascii_frac}", text)   # "1½" -> "1 1/2"
        text = text.replace(glyph, ascii_frac)
    text = re.sub(r"^\s*(a|an|one|two|three|four|five|six|half)\s+(?=\w)", lambda m: WORD_NUMBERS[m.group(1).lower()] + " ", text, flags=re.I)
    text = re.sub(r"(?<![\d/])(\d+)-(\d/\d)", r"\1 \2", text)                                       # "1-3/4 cups" is one and three quarters
    return re.sub(r"\bfl\.\s*oz\b\.?", "fl oz", text, flags=re.I)                                    # "2 fl. oz."


def parse_quantity(text: str) -> tuple[Decimal | None, Decimal | None, Decimal | None, str | None, str, list[str]]:
    """-> (quantity, low, high, quantity_text, remainder, flags). A range gives its midpoint plus bounds (D3)."""
    flags: list[str] = []
    norm = _normalise_numbers(text)
    m = QTY_RE.match(norm)
    if not m:
        return None, None, None, None, text, flags
    qtext = m.group("q")
    plus = re.match(rf"^\s*\+\s*(?P<q>{NUMBER})\s*(?P<rest>.*)$", m.group("rest"), re.S)
    if plus:                                    # "2 + 2 tbsp olive oil": two amounts of one unit
        try:
            return _to_decimal(qtext) + _to_decimal(plus.group("q")), None, None, f"{qtext} + {plus.group('q')}", plus.group("rest"), flags
        except Exception:
            pass
    parts = re.split(r"\s*(?:-|–|—|to)\s*", qtext)
    try:
        values = [_to_decimal(p) for p in parts if p.strip()]
    except Exception:
        return None, None, None, None, text, flags
    if len(values) == 2 and values[0] <= values[1]:
        low, high = values
        flags.append("range_midpoint")
        return (low + high) / 2, low, high, qtext.strip(), m.group("rest"), flags
    return values[0], None, None, qtext.strip(), m.group("rest"), flags


def parse_unit(rest: str) -> tuple[str | None, str | None, UnitKind, str]:
    """-> (unit, unit_raw, kind, remainder). Units are matched as whole words at the start of the remainder."""
    m = re.match(rf"^\s*(?:\(([^)]*)\)\s*)?(?P<u>{UNIT_PATTERN})\b\.?\s*(?:of\s+)?(?P<rest>.*)$", rest, re.I | re.S)
    if not m:
        return None, None, "none", rest
    unit, kind = UNITS[m.group("u").lower()]
    remainder = m.group("rest")
    if m.group(1):   # a parenthetical before the unit, e.g. "1 (14 oz) can": keep it as a note
        remainder = f"({m.group(1)}) {remainder}"
    return unit, m.group("u"), kind, remainder


def split_parentheses(text: str) -> tuple[list[str], str]:
    """-> (top-level notes, text without them). Brackets inside a note stay in it: "((33g), or parmesan cheese)" is one note; a bracket left open runs to the end of the line."""
    notes: list[str] = []
    kept: list[str] = []
    depth, start = 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i + 1
                kept.append(" ")
            depth += 1
        elif ch == ")":
            if depth == 1:
                notes.append(text[start:i])
            depth = max(depth - 1, 0)
        elif depth == 0:
            kept.append(ch)
    if depth > 0:
        notes.append(text[start:])
    return notes, "".join(kept)


def split_name_and_preparation(rest: str) -> tuple[str, list[str]]:
    notes, rest = split_parentheses(rest)
    prep = [note.strip() for note in notes]
    pieces = [p.strip() for p in re.split(r",|;| - | – ", rest) if p.strip()]
    if not pieces:
        return rest.strip().lower(), prep
    while len(pieces) > 1 and ONLY_DESCRIBES.match(pieces[0]):
        prep.append(pieces.pop(0))
    name, extras = pieces[0], pieces[1:]
    prep.extend(extras)
    name = re.sub(r"\s+", " ", name).strip(" .").lower()
    return name, prep


def preparation_hint(name: str, prep: list[str], line: str) -> PreparationHint:
    """Conservative, line-level only. Dish-level inference (a crudo's fish is raw) is Phase 2B-2."""
    text = " ".join([name, *prep, line])
    if RAW_WORDS.search(text):
        return "raw"
    if re.search(r"\boils?$", name.strip()):
        return "as_used"                        # "toasted sesame oil": the cooking word names the product, not a step (2C.1)
    if PRODUCT_NAMED_BY_METHOD.search(name):
        return "as_used"                        # "smoked paprika", "toasted coriander seeds", "no-cook tomato sauce": a product as sold, whatever the word (Phase 3)
    if COOKED_WORDS.search(text):
        return "cooked"
    if AS_USED_CLASSES.search(name):
        return "as_used"
    return "unknown"


# List glyphs some pages keep in front of every ingredient line ("• ½ lb Bluefin Tuna", "▢ 6-8 oz bluefin", "- 2 cups flour"). Found 2026-11-03 by the
# independent relevance review: two crudo pages were rejected as "no quantities" because the glyph hid the number from the quantity parser.
LEADING_BULLET = re.compile(r"^[\s\u2022\u25a2\u25a1\u25aa\u25ab\u25cf\u25cb\u25e6\u2023\u2043\u00b7\u2013\u2014\-\*\u2713\u2714\u2610\u2611\u2756\u27a2]+\s*(?=\S)")


APPROX_LEAD = re.compile(r"^(?:about|approx\.?|approximately|roughly|around)\s+(?=[\d\u00bc-\u00be\u2150-\u215e])", re.I)


def parse_line(line: str) -> ParsedIngredient:
    verbatim = original = re.sub(r"\s+", " ", line).strip()
    flags: list[str] = []
    stripped = LEADING_BULLET.sub("", original)
    if stripped != original and stripped:
        flags.append("leading_bullet_stripped")
        original = stripped                         # parsed without the glyph; `line` below keeps the page's own text
    # Phase 3 (2026-11-04): a typographic fraction slash ("1⁄2 cup") is a slash; a leading "about"/"approximately" does not hide the quantity
    normalised = APPROX_LEAD.sub("", original.replace("\u2044", "/"))
    if normalised != original:
        flags.append("quantity_text_normalised")
        original = normalised
    optional = bool(OPTIONAL.search(original))
    quantity, low, high, qtext, rest, qflags = parse_quantity(original)
    flags.extend(qflags)
    inline_weight = None
    if quantity is not None:
        rest = HYPHEN_WEIGHT.sub("", EACH_WORD.sub("", rest))
        if rest.lstrip().startswith("("):
            flags.append("note_follows_count")  # "2 (400 g) cans": a weight standing where an adjective stands describes one item (12.14.6, as 12.15 reads it)
        m = INLINE_WEIGHT.match(rest)
        if m:                                   # "8-ounce" becomes a per-item note the weight converter reads; the count stays
            inline_weight = f"{m.group('q')} {m.group('u')} each"
            rest = m.group("rest")
    unit, unit_raw, kind, rest = parse_unit(rest)
    if unit_raw and unit_raw.lower() in UNIT_TYPOS:
        flags.append("unit_typo_corrected")
    if unit is not None:
        m = SLASH_MEASURE.match(rest)
        if m:                                   # "4 oz / 113 g feta" reads as "4 oz (113 g) feta"
            rest = f"({m.group('m')}) {m.group('rest')}"
    if unit is not None and rest.lstrip().startswith("("):
        flags.append("note_follows_measure")   # "2 cups (232g) flour": the first note sits right after the measure
    if unit is not None:                        # "2 tsp tsp pepper": the unit written twice
        m = re.match(rf"^\s*(?P<u>{UNIT_PATTERN})\b\.?\s+(?=[a-zA-Z])", rest, re.I)
        if m and UNITS[m.group("u").lower()][0] == unit:
            rest = rest[m.end():]
            flags.append("unit_repeated")
    if kind == "weight" or inline_weight:
        rest = CONTAINER_WORDS.sub("", rest.lstrip())
    name, prep = split_name_and_preparation(rest)
    if quantity is not None and (unit is None or unit in ("large", "medium", "small")):
        words = name.split()
        if len(words) >= 2 and words[-1] in COUNT_WORDS_IN_NAME and not (len(words) == 2 and UNIT_IS_THE_FOOD.match(words[0])):      # "2 garlic cloves", "1 small garlic clove": the last word is the unit
            if unit is not None:
                prep.insert(0, unit)                                   # the size word stays as a note the portion chooser can read
            unit, kind = UNITS[words[-1]]
            unit_raw = words[-1]
            name = " ".join(words[:-1])
            flags.append("unit_from_name")
    if inline_weight:
        prep.insert(0, inline_weight)
        flags.append("inline_weight")
    sub = SUB_RECIPE_HEAD.match(rest) if quantity is not None and unit is None else None
    if sub or SUB_RECIPE_TAIL.search(original):
        # "1 recipe fresh pizza dough, recipe follows": a reference to another recipe, not an ingredient line (2C.1)
        name = re.sub(r"^(?:recipe|batch)\s+(?:of\s+)?", "", name).strip()
        name = SUB_RECIPE_TAIL.sub("", name).strip(" ,.") or name
        prep = [x for x in prep if not SUB_RECIPE_TAIL.search(x)]
        flags.append("sub_recipe_reference")
        flags.append("sub_recipe_components_on_page" if SUB_RECIPE_TAIL.search(original) else "sub_recipe_components_elsewhere")
        quantity, qtext, unit, unit_raw, kind = None, qtext, None, None, "none"
    if quantity is None and VAGUE.search(original):
        qtext = VAGUE.search(original).group(1).lower()
        flags.append("vague_quantity")
    if quantity is not None and unit is None:
        # "2 eggs", "4 ripe plum tomatoes": a bare count; recorded as a count with the name as the unit of count.
        kind = "count"
        unit = "each"
    if kind in ("volume", "count"):
        flags.append("conversion_pending_usda_portion")
    if not name:
        name = original.lower()
    return ParsedIngredient(line=verbatim, quantity_text=qtext, quantity=quantity, quantity_low=low, quantity_high=high,
                            unit_raw=unit_raw, unit=unit, unit_kind=kind, name=name, preparation_words=prep,
                            preparation_hint=preparation_hint(name, prep, original), optional=optional, flags=flags)


def parse_lines(line: str) -> list[ParsedIngredient]:
    """One page line -> one or two ingredients. "Grated zest of 1 small lemon, plus 1 tablespoon lemon juice" names two foods with
    their own quantities; both keep the verbatim line and a `compound_split` flag. "plus more for drizzling" (no number) is not split."""
    parts = PLUS_SPLIT.split(line, maxsplit=1)
    if len(parts) == 2:
        tail = parse_line(parts[1])
        if tail.quantity is not None and tail.unit_kind != "none" and tail.name and not re.match(r"^(for|to|more|extra)\b", tail.name):
            head = parse_line(parts[0])
            original = re.sub(r"\s+", " ", line).strip()
            return [head.model_copy(update={"line": original, "flags": head.flags + ["compound_split:part_1_of_2"]}),
                    tail.model_copy(update={"line": original, "flags": tail.flags + ["compound_split:part_2_of_2"]})]
    return [parse_line(line)]


# -- yield -----------------------------------------------------------------------

SERVING_WORDS = re.compile(r"\b(serving|servings|serves|portion|portions|people|person)\b", re.I)   # 'makes 2 pizzas' is not a serving count
NON_SERVING_UNITS = re.compile(r"\b(slice|slices|piece|pieces|cookie|cookies|item|items|cup|cups|loaf|loaves|pizza|pizzas|tart|tarts|dozen|quart|pint|liter|litre|ml|g)\b", re.I)


_RANGE = rf"(?P<lo>{NUMBER})(?:\s*(?:-|–|—|to)\s*(?P<hi>{NUMBER}))?"
SERVES_FIRST = re.compile(rf"\b(?:serves?|servings?|portions?|feeds?)\b\s*:?\s*(?:about\s+)?{_RANGE}", re.I)                # "Serves 8 (4 breakfasts for 2 people)", "Servings: 4"
SERVING_COUNT = re.compile(rf"{_RANGE}\s+(?:(?!cups?\b|tbsp\b|tsp\b|oz\b|g\b|ml\b)[a-z-]+\s+)?(?:servings?|portions?|people|persons?)\b", re.I)   # "12 servings", "6 big portions"


def parse_servings(yield_text: str) -> tuple[Decimal | None, Decimal | None, Decimal | None, str]:
    """-> (servings, low, high, note). Only serving-like yields count; '12 slices' or '2 cups' give None."""
    text = _normalise_numbers(yield_text or "").strip()
    if not text:
        return None, None, None, "no yield stated"
    beside = SERVES_FIRST.search(text) or SERVING_COUNT.search(text)
    if beside:                                  # Julius, 2026-11-05: the number beside the serving word, whatever else the yield states ("2 cups / 12 servings")
        low, high = _to_decimal(beside.group("lo")), _to_decimal(beside.group("hi")) if beside.group("hi") else None
        if low > 0 and high is not None and low <= high:
            return (low + high) / 2, low, high, f"range '{yield_text}' -> midpoint (range_midpoint)"
        if low > 0:
            return low, None, None, f"parsed from '{yield_text}'"
    nums = re.findall(rf"{NUMBER}", text)
    if not nums:
        return None, None, None, f"yield '{yield_text}' has no number"
    try:
        values = [_to_decimal(n) for n in nums[:2]]
    except Exception:
        return None, None, None, f"yield '{yield_text}' could not be read"
    if NON_SERVING_UNITS.search(text) and not SERVING_WORDS.search(text):
        return None, None, None, f"yield '{yield_text}' is not a serving count"
    if re.search(r"\d\s*(?:-|–|to)\s*\d", text) and len(values) == 2 and values[0] <= values[1]:
        return (values[0] + values[1]) / 2, values[0], values[1], f"range '{yield_text}' -> midpoint (range_midpoint)"
    if values[0] <= 0:
        return None, None, None, f"yield '{yield_text}' is not positive"
    return values[0], None, None, f"parsed from '{yield_text}'"
