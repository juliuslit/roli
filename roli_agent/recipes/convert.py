"""Deterministic conversions available before USDA matching (D4, 2B-1 part).

Explicit weight units convert exactly. Water-like liquids by volume convert with density 1.0 g/ml,
flagged as an approximation. Everything else (cups of flour, '2 large eggs', 'a handful') stays
`grams: None` with `conversion_pending_usda_portion`, to be resolved in 2B-2 from the matched USDA
record's portion weights. Unknown never becomes zero.
"""

from __future__ import annotations

import re
from decimal import Decimal

from .models import ParsedIngredient

# Exact definitions (NIST SP 811 / SI).
WEIGHT_TO_GRAMS: dict[str, tuple[Decimal, str]] = {
    "g": (Decimal(1), "1 g"),
    "kg": (Decimal(1000), "1 kg = 1000 g"),
    "mg": (Decimal("0.001"), "1 mg = 0.001 g"),
    "oz": (Decimal("28.349523125"), "1 oz = 28.349523125 g (NIST SP 811)"),
    "lb": (Decimal("453.59237"), "1 lb = 453.59237 g (NIST SP 811)"),
}
# US customary volumes in millilitres (NIST Handbook 44).
VOLUME_TO_ML: dict[str, tuple[Decimal, str]] = {
    "ml": (Decimal(1), "1 ml"),
    "l": (Decimal(1000), "1 l = 1000 ml"),
    "tsp": (Decimal("4.92892159375"), "1 US tsp = 4.92892159375 ml (NIST HB 44)"),
    "tbsp": (Decimal("14.78676478125"), "1 US tbsp = 14.78676478125 ml (NIST HB 44)"),
    "fl_oz": (Decimal("29.5735295625"), "1 US fl oz = 29.5735295625 ml (NIST HB 44)"),
    "cup": (Decimal("236.5882365"), "1 US cup = 236.5882365 ml (NIST HB 44)"),
    "pint": (Decimal("473.176473"), "1 US pint = 473.176473 ml (NIST HB 44)"),
    "quart": (Decimal("946.352946"), "1 US quart = 946.352946 ml (NIST HB 44)"),
}
# Only liquids whose density is close enough to water that assuming 1.0 g/ml is defensible (D4).
WATER_LIKE = re.compile(r"\b(water|stock|broth|vinegar|lemon juice|lime juice|wine|coffee|tea)\b", re.I)


def convert_weight(ingredient: ParsedIngredient) -> ParsedIngredient:
    """Fill `grams` for explicit weight units and water-like volumes; leave everything else pending."""
    if ingredient.quantity is None:
        return ingredient
    if ingredient.unit_kind == "weight" and ingredient.unit in WEIGHT_TO_GRAMS:
        factor, reference = WEIGHT_TO_GRAMS[ingredient.unit]
        grams = ingredient.quantity * factor
        return ingredient.model_copy(update={"grams": grams, "grams_reference": reference,
                                             "flags": [f for f in ingredient.flags if f != "conversion_pending_usda_portion"]})
    if ingredient.unit_kind == "volume" and ingredient.unit in VOLUME_TO_ML and WATER_LIKE.search(ingredient.name):
        factor, reference = VOLUME_TO_ML[ingredient.unit]
        grams = ingredient.quantity * factor          # x 1.0 g/ml
        flags = [f for f in ingredient.flags if f != "conversion_pending_usda_portion"] + ["density_assumed_1"]
        return ingredient.model_copy(update={"grams": grams, "grams_reference": f"{reference}; density 1.0 g/ml assumed (water-like liquid)",
                                             "flags": flags})
    return ingredient


# ---------------------------------------------------------------------------
# Phase 2B-2: embedded weights ("1 (14 oz) can") and USDA portion weights (D4)
# ---------------------------------------------------------------------------

from typing import Iterable   # noqa: E402

EMBEDDED_WEIGHT = re.compile(
    r"^(?P<about>about |approx\.? |approximately |roughly |~\s*)?(?P<q>\d+(?:[.,]\d+)?(?:\s+\d/\d)?|\d/\d)\s*-?\s*"
    r"(?P<u>oz|ounce|ounces|g|gram|grams|lb|lbs|pound|pounds|kg|kilogram|kilograms)\b\.?"
    r"(?P<tail>\s+(?:each|per\s+\w+|total|in total|cans?|packages?|package|jar|jars|container|containers|bag|bags|block|blocks|piece|pieces))?$",
    re.I)
# 12.12.5: a note may hold more than the weight: a price ("80g, $0.09"), a second system ("100g/3.5oz", "1 oz; 33g"), a word ("grated, (65g) $1.78"), or a range
# ("5 to 6 ounces"). The note is read piece by piece, and a piece counts only when it is a weight and nothing else, so "from a 14 oz can" stays ignored.
PRICE = re.compile(r"[$£€]\s*\d+(?:[.,]\d+)?\**")
NOTE_PIECES = re.compile(r"[,;]|(?<=[a-z.])\s*/\s*(?=\d)", re.I)
_Q = r"\d+(?:[.,]\d+)?(?:\s+\d/\d)?|\d/\d"
WEIGHT_RANGE = re.compile(rf"^(?:about |approx\.? |approximately |roughly |~\s*)?(?P<lo>{_Q})\s*-?\s*(?:-|–|—|to)\s*(?P<hi>{_Q})\s*-?\s*(?P<u>oz|ounce|ounces|g|gram|grams|lb|lbs|pound|pounds|kg|kilogram|kilograms)\b\.?"
                          r"(?P<tail>\s+(?:each|per\s+\w+))?$", re.I)
# A hyphenated weight is an adjective on one item ("4 (6-ounce) fillets", "2 (6- to 8-oz.) steaks"): the hyphen says "each" (12.14.6, as 12.15 reads it).
ADJECTIVE_WEIGHT = re.compile(r"\d\s*-\s*(?:oz|ounces?|lbs?|pounds?|g|grams?|kg|kilograms?)\b", re.I)
WEIGHT_WORDS = {"oz": "oz", "ounce": "oz", "ounces": "oz", "g": "g", "gram": "g", "grams": "g", "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
                "kg": "kg", "kilogram": "kg", "kilograms": "kg"}


def _dec(text: str) -> Decimal:
    text = text.strip().replace(",", ".")
    if " " in text:
        whole, frac = text.split()
        return Decimal(whole) + _dec(frac)
    if "/" in text:
        a, b = text.split("/")
        return Decimal(a) / Decimal(b)
    return Decimal(text)


def stated_weights(note: str) -> tuple[re.Match | None, re.Match | None]:
    """-> (the weight the note states, its range). A note that is a weight as a whole is read as before; otherwise each piece is tested and, when two systems are
    given, the metric one wins: the recipe's own grams."""
    whole = EMBEDDED_WEIGHT.match(note.strip())
    if whole:
        return whole, None
    pieces = [piece.strip(" ()*") for piece in NOTE_PIECES.split(PRICE.sub(" ", note))]
    found = [m for m in (EMBEDDED_WEIGHT.match(piece) for piece in pieces) if m]
    metric = [m for m in found if WEIGHT_WORDS[m.group("u").lower()] in ("g", "kg")]
    if metric or found:
        return (metric or found)[0], None
    return None, next((m for m in (WEIGHT_RANGE.match(piece) for piece in pieces) if m and _dec(m.group("lo")) < _dec(m.group("hi"))), None)


def apply_embedded_weight(ingredient: ParsedIngredient) -> ParsedIngredient:
    """'1 (14 oz) can tomatoes' -> 14 oz; '3 large (560 grams) potatoes' -> 560 g in total; '4 pork chops, about 6 ounces each' -> 6 oz x 4; '2 (6-ounce) fillets' -> 6 oz x 2.

    12.14.6, recorded in the reference: a weight on a count line is the line's total; only "each" or "per", or the hyphen of "6-ounce", or a bracket straight after the count, makes it a weight per item. Applies to count-like
    and volume lines without grams from the page (a volume of water-like liquid, weighed at 1 g/ml, gives way to the page's own weight), and to a weight line whose note gives the metric
    weight: 12.12.5."""
    if ingredient.quantity is None or ingredient.unit_kind not in ("count", "none", "volume", "weight"):
        return ingredient
    if ingredient.unit_kind == "weight":
        if ingredient.unit in ("g", "kg"):
            return ingredient
    elif ingredient.grams is not None and "density_assumed_1" not in ingredient.flags:
        return ingredient
    for position, note in enumerate(ingredient.preparation_words):
        m, span = stated_weights(note)
        if ingredient.unit_kind == "weight":
            if m is None or WEIGHT_WORDS[m.group("u").lower()] not in ("g", "kg") or m.group("tail"):
                continue
            factor, reference = WEIGHT_TO_GRAMS[WEIGHT_WORDS[m.group("u").lower()]]
            return ingredient.model_copy(update={"grams": _dec(m.group("q")) * factor, "grams_reference": f"metric weight stated on the line '({note.strip()})' used; {reference}",
                                                 "flags": ingredient.flags + ["embedded_weight", "embedded_weight_metric"]})
        flags = [f for f in ingredient.flags if f not in ("conversion_pending_usda_portion", "density_assumed_1")]
        if span is not None:
            # "1 1/2 cups sliced mushrooms (5 to 6 ounces)", "3 chops (10 to 12 ounces each)": the page's own range, read at its midpoint like a quantity range (D3)
            factor, reference = WEIGHT_TO_GRAMS[WEIGHT_WORDS[span.group("u").lower()]]
            grams = (_dec(span.group("lo")) + _dec(span.group("hi"))) / 2 * factor
            per_item = ingredient.unit_kind != "volume" and (bool(span.group("tail")) or bool(ADJECTIVE_WEIGHT.search(note)) or (position == 0 and "note_follows_count" in ingredient.flags))
            how = f"midpoint per item x {ingredient.quantity}" if per_item else "midpoint used as the line's total"
            return ingredient.model_copy(update={"grams": grams * ingredient.quantity if per_item else grams, "grams_reference": f"weight range stated on the line '({note.strip()})', {how}; {reference}",
                                                 "flags": flags + ["embedded_weight", "embedded_weight_on_volume_line" if ingredient.unit_kind == "volume" else "embedded_weight_range", "range_midpoint"]})
        if m is None:
            continue
        unit = WEIGHT_WORDS[m.group("u").lower()]
        factor, reference = WEIGHT_TO_GRAMS[unit]
        weight = _dec(m.group("q")) * factor
        tail = (m.group("tail") or "").strip().lower()
        if ingredient.unit_kind == "volume":
            # "2 cups (232g) flour", "1 cup walnuts (4 oz)": a bare weight in parentheses on a volume line is the page's own weight for the
            # line, the total (2C.1). A note with other words ("from a 14 oz can") does not match and is ignored.
            if tail:
                continue
            beside = position == 0 and "note_follows_measure" in ingredient.flags
            ref = f"weight stated {'beside the measure' if beside else 'on the line'} '({note.strip()})' used as the line's total; {reference}"
            flags = flags + ["embedded_weight", "embedded_weight_after_measure" if beside else "embedded_weight_on_volume_line"]
            if m.group("about"):
                flags.append("embedded_weight_approximate")                # "(about 6 oz)": the page's own figure, marked approximate
            return ingredient.model_copy(update={"grams": weight, "grams_reference": ref, "flags": flags})
        is_total = not tail.startswith(("each", "per")) and not ADJECTIVE_WEIGHT.search(note) and not (position == 0 and "note_follows_count" in ingredient.flags)    # 12.14.6
        grams = weight if is_total else weight * ingredient.quantity
        how = "total for the line" if is_total else f"per item x {ingredient.quantity}"
        ref = f"embedded weight '({note.strip()})' read as {how}; {reference}"
        flags = flags + ["embedded_weight"]
        if is_total and ingredient.quantity > 1:
            flags.append("embedded_weight_total_assumed")
        return ingredient.model_copy(update={"grams": grams, "grams_reference": ref, "flags": flags})
    return ingredient


# USDA portion labels use these words for our normalised units.
PORTION_UNIT_WORDS: dict[str, tuple[str, ...]] = {
    "tbsp": ("tablespoon", "tablespoons", "tbsp"), "tsp": ("teaspoon", "teaspoons", "tsp"), "cup": ("cup", "cups"),
    "fl_oz": ("fl oz", "fluid ounce"), "pint": ("pint",), "quart": ("quart",),
    "clove": ("clove", "cloves"), "slice": ("slice", "slices"), "piece": ("piece", "pieces"), "head": ("head",), "sprig": ("sprig", "sprigs"),
    "leaf": ("leaf", "leaves"), "bunch": ("bunch",), "stalk": ("stalk", "stalks"), "fillet": ("fillet", "fillets"), "can": ("can",),
    "large": ("large",), "medium": ("medium",), "small": ("small",),
}
# Labels that never describe a bare count ("4 tomatoes"): weights, volumes, servings, packages, fractions of a thing.
NOT_A_WHOLE_ITEM = re.compile(r"\b(quantity not specified|oz|cup|cups|tbsp|tablespoon|tsp|teaspoon|fl oz|lb|g|ml|serving|nlea|racc|package|slice|wedge|leaf|"
                              r"inner|outer|piece|chopped|diced|sliced|shredded|grated|cubed|cubic|inch|strip|strips|stick|sticks|mashed|pureed|puree|"
                              r"juice|quart|pint|fluid|half|quarter|section|sections|segment|segments|floret|florets|sprig|sprigs|ring|rings)\b", re.I)
SIZE_WORDS = {"small", "medium", "large", "extra", "jumbo", "baby", "mini", "giant"}
SIZED_VARIETIES = {"japanese", "chinese", "thai", "indian"}     # a kind of the food that comes in its own size (12.14.8b: never stretched from another size)
STRIP_WORDS = {"strip", "strips", "rasher", "rashers", "slice", "slices"}        # count words that mean one slice of the record (bacon)
RACK_WORDS = re.compile(r"\b(racks?|crown roast|\d+[- ]?(?:rib|bone)(?!-in)|whole (?:chicken|duck|fish|side)|side of)\b", re.I)    # "4 bone-in chops" is four chops
# A whole-item label that states a size by dimension rather than by word: '1 fruit (2-3/8" dia)', '1 small (5-1/2" long)' (2C.1).
DIMENSION_LABEL = re.compile(r"\d\s*(?:-\d+/\d+)?\s*\"\s*(?:dia|long|wide|thick)|\b(?:dia|diameter)\b|\d\s*(?:inch|inches|in)\b", re.I)
WEIGHT_TIE_TOLERANCE = Decimal("0.005")       # labels whose per-unit weights agree within 0.5 % are the same measure ("1 clove" = 3 g, "3 cloves" = 9 g)


def is_sized_label(label: str) -> bool:
    """Does this whole-item label name a size, by word or by dimension? Such labels need the line to state the size (D20)."""
    words = _label_tokens(label) - {w for w in _label_tokens(label) if w.isdigit()}
    return bool(words & SIZE_WORDS) or bool(DIMENSION_LABEL.search(label))


def per_unit(p) -> Decimal:
    return Decimal(str(p.gram_weight)) / Decimal(str(p.amount))


def same_weight(ps) -> bool:
    """Several labels, one weight per unit: not an ambiguity, whichever label is taken (2C.1)."""
    weights = [per_unit(p) for p in ps]
    return len(weights) > 1 and (max(weights) - min(weights)) <= WEIGHT_TIE_TOLERANCE * max(weights)


def median_of(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def median_whole_item(ingredient: ParsedIngredient, sized, fdc_id: int) -> ParsedIngredient:
    """D20 (revised 2026-11-03): weigh a bare count at the median of the record's comparable whole-item sizes. The source stated no size, so
    the grams are an assumption: flagged `assumed_size_median` (and `single_labelled_size` when the record lists one size only), the labels
    and their weights recorded, the reference naming every label. Source-stated weights never carry this flag."""
    per = {p.label: per_unit(p) for p in sized}
    med = median_of(list(per.values()))
    labels = "; ".join(f"'{p.label}' = {per[p.label]:.4g} g" for p in sorted(sized, key=lambda p: per[p.label]))
    grams = ingredient.quantity * med
    flags = [f for f in ingredient.flags if f != "conversion_pending_usda_portion"] + ["usda_portion", "assumed_size_median"]
    if len(sized) == 1:
        flags.append("single_labelled_size")
    how = "the record's only listed size" if len(sized) == 1 else f"median of {len(sized)} comparable whole-item sizes"
    ref = (f"ASSUMED size: {how} of USDA {fdc_id} ({labels}) -> {med:.4g} g per item x {ingredient.quantity}; the line names no size "
           f"(D20 revised 2026-11-03: assumed_size_median; range {min(per.values()):.4g}-{max(per.values()):.4g} g per item kept in portion_options)")
    return ingredient.model_copy(update={"grams": grams, "grams_reference": ref, "flags": flags, "portion_options": _options(ingredient, sized)})


def _options(ingredient: ParsedIngredient, ps) -> list[dict[str, str]]:
    """The labels an ambiguous line could not choose between, with the grams each would give (recorded for Phase 2C, never chosen here)."""
    return [{"label": p.label, "grams_per_unit": str(per_unit(p)), "grams": str(ingredient.quantity * per_unit(p))} for p in ps]
VOLUME_LABEL_WORDS = {"cup", "cups", "tbsp", "tablespoon", "tablespoons", "tsp", "teaspoon", "teaspoons", "fl", "pint", "quart"}
# Words in a recipe line that name the same thing as a USDA portion modifier.
MODIFIER_SYNONYMS = {"plum": {"plum", "italian"}, "roma": {"plum", "italian"}, "cherry": {"cherry"}, "grape": {"cherry"}, "whole": {"whole"},
                     "chopped": {"chopped"}, "diced": {"diced", "chopped"}, "sliced": {"sliced", "slice"}, "shredded": {"shredded"}, "grated": {"grated"},
                     "minced": {"chopped", "minced"}, "cubed": {"cubed", "diced"}, "halves": {"half", "halves"}, "jumbo": {"jumbo"}, "extra": {"extra"}}


def _sing(word: str) -> str:
    w = word.lower()
    if len(w) <= 3:
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("oes"):
        return w[:-2]
    if w.endswith(("ses", "xes", "shes", "ches")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _label_tokens(label: str) -> set[str]:
    return {_sing(t) for t in re.findall(r"[a-z]+", label.lower())}


def _line_tokens(ingredient: ParsedIngredient) -> tuple[set[str], set[str]]:
    """(literal words, literal words plus synonyms) of the line that can pick a portion: everything but the food's
    own head noun ("tomatoes" in "ripe plum tomatoes"), singularised; synonyms add plum -> italian and the like."""
    name_words = re.findall(r"[a-z]+", ingredient.name.lower())
    head = {_sing(name_words[-1])} if name_words else set()
    literal = {_sing(t) for t in re.findall(r"[a-z]+", (ingredient.name + " " + " ".join(ingredient.preparation_words)).lower())} - head
    expanded = set(literal)
    for w in list(literal):
        expanded |= {_sing(x) for x in MODIFIER_SYNONYMS.get(w, set())}
    return literal, expanded


def _best_by_overlap(cands, extra_words, line_words):
    """Portions whose extra words overlap the line most (the line's own words count before synonyms);
    several winners are fine when they weigh the same."""
    literal, expanded = line_words
    scored = [((len(extra_words(p) & literal), len(extra_words(p) & expanded)), p) for p in cands]
    top = max((n for n, _ in scored), default=(0, 0))
    if top == (0, 0):
        return []
    winners = [p for n, p in scored if n == top]
    if len(winners) > 1:
        exact = [p for p in winners if extra_words(p) <= expanded]      # "2 cold large eggs": "1 large" says all of its words on the line, "1 extra large" does not
        winners = exact or winners
    if len(winners) > 1 and same_weight(winners):
        return winners[:1]
    return winners


def own_word_items(plist: list, record: str) -> list:
    """12.14.8a: a measure named in the record's own word is one whole item, whatever else its label says ("1 eggplant, unpeeled (approx 1-1/4 lb)"). A yield from an item is not the item."""
    head = {_sing(w) for w in re.findall(r"[a-z]+", record.split(",")[0].lower())}
    return [p for p in plist if head & _label_tokens(p.label) and p.measure.upper() != "RACC" and not re.search(r"\byield\b", p.label, re.I) and not (_label_tokens(p.label) & VOLUME_LABEL_WORDS)]


def convert_with_portions(ingredient: ParsedIngredient, portions: Iterable[Any], fdc_id: int, *, proxy: bool = False, record: str = "") -> ParsedIngredient:
    """Fill grams for a volume or count unit from the matched USDA record's own household measures.

    Choice rule (deterministic, recorded in `grams_reference`):
    1. keep portions whose label names the line's unit (tbsp <-> "tablespoon"; a bare count <-> whole-item labels);
    2. prefer one whose other words match the line ("cup, chopped" for "chopped tomatoes"; "plum tomato" for "plum tomatoes");
    3. else, if one plain portion exists (just the unit, or "medium" for a bare count), use it;
    4. else, with several candidates and nothing to choose by, leave grams unknown and flag `portion_ambiguous`.
    Unknown never becomes zero."""
    if ingredient.grams is not None or ingredient.quantity is None or ingredient.unit_kind not in ("volume", "count"):
        return ingredient
    unit = ingredient.unit or ""
    plist = list(portions)
    line_words = _line_tokens(ingredient)
    if proxy:
        # D21: a substitute record's whole-item weights describe a different food's size and are never used; only its
        # volume measures (cups, spoons) may stand in, flagged as an approximation.
        if ingredient.unit_kind != "volume":
            return ingredient.model_copy(update={"flags": ingredient.flags + ["proxy_count_portion_refused"]})
        plist = [p for p in plist if _label_tokens(p.label) & VOLUME_LABEL_WORDS]

    def finish(portion, flag: str | None) -> ParsedIngredient:
        grams = ingredient.quantity * Decimal(str(portion.gram_weight)) / Decimal(str(portion.amount))
        flags = [f for f in ingredient.flags if f != "conversion_pending_usda_portion"] + ["usda_portion"] + ([flag] if flag else [])
        if (line_words[0] & SIZE_WORDS) and not is_sized_label(portion.label):
            flags.append("portion_size_word_unmatched")                # "1 small garlic clove" on a record with one clove weight
        ref = f"USDA {fdc_id} portion '{portion.label}' = {portion.gram_weight:g} g"
        if proxy:
            flags.append("proxy_volume_portion")
            ref += " (volume measure of the substitute record; approximation)"
        return ingredient.model_copy(update={"grams": grams, "grams_reference": ref, "flags": flags})

    def whole_item(ingredient: ParsedIngredient) -> ParsedIngredient:
        """A bare count ("4 tomatoes", "1 lemon", "2 cloves garlic" on a record whose portion is 'clove'). SR Legacy puts the
        words in the modifier; Foundation puts them in the measure name ("clove", "fruit")."""
        whole = [p for p in plist if not NOT_A_WHOLE_ITEM.search(p.label) and p.measure.upper() != "RACC" and (p.modifier or p.measure != "undetermined")]
        named_size = (line_words[0] & (SIZE_WORDS | SIZED_VARIETIES)) | ({ingredient.unit} if ingredient.unit in SIZE_WORDS else set())
        if not whole and record and not named_size:
            own = own_word_items(plist, record)
            if own:
                return finish(own[0], "portion_own_word_item")
        if RACK_WORDS.search(ingredient.line or ingredient.name):
            # "1 (8-rib) pork rack, Frenched" is not one chop: a rack, crown, side or whole bird/fish is a different item from the record's
            # single-piece label; the weight stays unknown (2026-11-05, after a 150 g lower bound from one such recipe withdrew a dish's bound)
            return ingredient.model_copy(update={"flags": ingredient.flags + ["multi_piece_item_not_a_single_portion"]})
        if not whole and line_words[0] & STRIP_WORDS:
            # "2 strips bacon", "4 rashers streaky bacon": the count names a slice, and the record's slice label is the measure (Phase 3, 2026-11-04)
            slices = [p for p in plist if "slice" in _label_tokens(p.label) and not (_label_tokens(p.label) & VOLUME_LABEL_WORDS)]
            if len(slices) == 1:
                return finish(slices[0], "count_word_read_as_slice")
            if len(slices) > 1:
                return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_ambiguous"], "portion_options": _options(ingredient, slices)})
        words_of = lambda p: _label_tokens(p.label) - {w for w in _label_tokens(p.label) if w.isdigit()}
        overlapping = _best_by_overlap(whole, words_of, line_words)
        if len(overlapping) == 1:
            return finish(overlapping[0], None)
        if len(overlapping) > 1:
            return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_ambiguous"], "portion_options": _options(ingredient, overlapping)})
        # D20: no size assumption. A record that lists sizes (small/medium/large, or '2-3/8" dia') needs the line to name one; a record
        # whose only whole-item label is unsized ("1 fruit", "1 clove", "1 pepper") matches a bare count unambiguously.
        # A dimension ('2-3/8" dia') marks a size only when the record offers more than one whole item to choose from; a lone
        # '1 fruit (2-1/8" dia)' is simply the record's one item weight.
        sized = [p for p in whole if is_sized_label(p.label) and (len(whole) > 1 or (words_of(p) & SIZE_WORDS))]
        unsized = [p for p in whole if p not in sized]
        if sized and named_size and any(words_of(p) & SIZE_WORDS for p in sized) and not any(named_size & words_of(p) for p in sized):
            # 12.14.8b: "2 small aubergines" on a record that lists other sizes: a size no record has is never stretched from another size
            return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_size_not_in_record"]})
        if sized and not unsized:
            # D20, revised (Julius, 2026-11-03): the record lists the same item in several sizes and the line names none -> the MEDIAN of
            # those comparable whole-item weights, flagged `assumed_size_median`, with every label kept in `portion_options`. Only labels
            # of the same item (size words or dimensions) are combined; a wedge, a slice or a cup never enters (NOT_A_WHOLE_ITEM).
            return median_whole_item(ingredient, sized, fdc_id)
        if sized:
            # sized labels beside a different kind of label ("1 fruit" next to "1 large"; "1 cherry", "1 Italian tomato" next to sizes): the
            # kinds are not comparable, so no median; the line stays unknown and the pair may bound it from the sized labels (G3).
            return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_size_unspecified"], "portion_options": _options(ingredient, whole)})
        if len(unsized) == 1 or same_weight(unsized):
            return finish(unsized[0], "portion_whole_item")
        if whole:
            return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_ambiguous"], "portion_options": _options(ingredient, whole)})
        return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_none_for_unit"]})

    if unit == "each":
        return whole_item(ingredient)

    words = PORTION_UNIT_WORDS.get(unit)
    if not words:
        # 12.14.9: millilitres and litres have no measure of their own in USDA: they go through the record's spoon or cup
        derived = _derive_volume(ingredient, plist, fdc_id, proxy=proxy) if unit in VOLUME_TO_ML else None
        return derived if derived is not None else ingredient.model_copy(update={"flags": ingredient.flags + ["portion_none_for_unit"]})
    matched = []
    unit_words_sing = {_sing(w) for w in words}                    # compare singularised forms on both sides ("leaves" -> "leave" on both)
    for p in plist:
        lt = _label_tokens(p.label)
        if (lt & unit_words_sing) or (p.measure.lower() in words) or (_sing(p.measure) in unit_words_sing):
            matched.append(p)
    if unit in ("large", "medium", "small"):                       # a size names a whole item, never a slice or a cup
        matched = [p for p in matched if not NOT_A_WHOLE_ITEM.search(p.label)]
        if not matched:
            return whole_item(ingredient)                            # "1 medium lemon" on a record that only lists "1 fruit"
    if not matched:
        derived = _derive_volume(ingredient, plist, fdc_id, proxy=proxy)
        if derived is not None:
            return derived
        return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_none_for_unit"]})
    unit_tokens = {_sing(w) for w in words} | {"undetermined", "or", "and"} | set(re.findall(r"[a-z]+", unit))
    def extra(p) -> set[str]:
        return (_label_tokens(p.label) - unit_tokens) - {w for w in _label_tokens(p.label) if w.isdigit()}
    overlapping = _best_by_overlap(matched, extra, line_words)
    if len(overlapping) == 1:
        return finish(overlapping[0], None)
    if len(overlapping) > 1:
        return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_ambiguous"], "portion_options": _options(ingredient, overlapping)})
    plain = [p for p in matched if not extra(p)]
    if len(plain) == 1 or same_weight(plain):                       # "1 tsp" and "0.5 tsp" of thyme: one weight, no ambiguity
        return finish(plain[0], None)
    if len(matched) == 1:
        return finish(matched[0], "portion_modifier_unmatched")
    if same_weight(matched):
        return finish(matched[0], "portion_modifier_unmatched")
    return ingredient.model_copy(update={"flags": ingredient.flags + ["portion_ambiguous"], "portion_options": _options(ingredient, matched)})


VOLUME_WORDS_TO_UNIT = {"tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp", "cup": "cup",
                        "cups": "cup", "pint": "pint", "quart": "quart", "floz": "fl_oz", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "ml": "ml",
                        "liter": "l", "litre": "l"}


def _derive_volume(ingredient: ParsedIngredient, plist: list, fdc_id: int, *, proxy: bool = False) -> ParsedIngredient | None:
    """No portion for the line's volume unit, but the record lists another plain volume measure: use that measure's
    density (grams per millilitre, from the record itself) and the exact US-customary volume ratio. "1/4 cup tamari"
    with only "1 tbsp = 18 g" -> 18 g / 14.787 ml x 236.588 ml. Flagged; the source portion is the reference."""
    if ingredient.unit_kind != "volume" or ingredient.unit not in VOLUME_TO_ML:
        return None
    literal, expanded = _line_tokens(ingredient)
    head_words = {_sing(w) for w in re.findall(r"[a-z]+", ingredient.name.lower())}
    allowed_extra = expanded | head_words                               # "cup cherry tomatoes" may serve "1 pint cherry tomatoes"
    sources, matched_sources = [], []
    for p in plist:
        tokens_ = [t for t in re.findall(r"[a-z]+", re.sub(r"\bfl\.?\s*oz\b", "floz", p.label.lower()))]
        unit_words = [w for w in tokens_ if w in VOLUME_WORDS_TO_UNIT]
        extra = [w for w in tokens_ if w not in VOLUME_WORDS_TO_UNIT and w not in ("undetermined", "drained") and not w.isdigit()]
        if len(unit_words) != 1:
            continue
        src_unit = VOLUME_WORDS_TO_UNIT[unit_words[0]]
        if src_unit not in VOLUME_TO_ML:
            continue
        if not extra:                                                 # a plain "1 tbsp", "1 cup", "1 fl oz": no "chopped", no "packed"
            sources.append((p, src_unit))
        elif all(_sing(w) in allowed_extra for w in extra):           # every extra word is one the line itself uses
            matched_sources.append((p, src_unit))
    if matched_sources and not sources:
        sources = matched_sources
    if not sources:
        return None
    densities = [Decimal(str(p.gram_weight)) / Decimal(str(p.amount)) / VOLUME_TO_ML[u][0] for p, u in sources]
    spread = max(densities) - min(densities)
    if spread > Decimal("0.05") * max(densities):
        return None                                                   # the record's own measures disagree on density by more than rounding can explain
    portion, src_unit = sources[0]
    if spread > Decimal("0.02") * max(densities):
        # 12.14.8b: a record's spoon and cup can round apart ("1 tbsp" 16 g, "1 cup" 262 g): the measure nearest in size answers (1 cup = 16 tbsp = 48 tsp)
        wanted = ingredient.quantity * VOLUME_TO_ML[ingredient.unit][0]
        portion, src_unit = min(sources, key=lambda t: abs(Decimal(str(t[0].amount)) * VOLUME_TO_ML[t[1]][0] - wanted))
    density = Decimal(str(portion.gram_weight)) / Decimal(str(portion.amount)) / VOLUME_TO_ML[src_unit][0]      # g per ml
    grams = ingredient.quantity * VOLUME_TO_ML[ingredient.unit][0] * density
    ref = (f"USDA {fdc_id} portion '{portion.label}' = {portion.gram_weight:g} g, i.e. {density.quantize(Decimal('0.0001'))} g/ml; "
           f"{VOLUME_TO_ML[ingredient.unit][1]}")
    if (portion, src_unit) in matched_sources:
        ref += " (the measure's own words match the line)"
    flags = [f for f in ingredient.flags if f != "conversion_pending_usda_portion"] + ["usda_portion", "portion_derived_volume"]
    if proxy:
        flags.append("proxy_volume_portion")
        ref += " (volume measure of the substitute record; approximation)"
    return ingredient.model_copy(update={"grams": grams, "grams_reference": ref, "flags": flags})
