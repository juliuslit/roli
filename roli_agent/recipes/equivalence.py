"""D22: when the chosen USDA record cannot weigh the line's household measure, use an equivalent record that can.

Constrained, deterministic policy (Julius, 2026-11-02), applied after the model's selection and only when a
conversion actually needs a household measure:

1. the replacement must come from the same USDA search's candidate list (never from memory);
2. it must name the same food: identical first two comma-separated words of the description ("Oil, olive");
3. it must be in the same preparation state (raw / cooked / unknown, by the Phase 2A classifier) and in the same
   physical form: descriptor words that change what is weighed ("with peel", "without skin", "drained", "canned",
   "dried", "shredded", ...) must be the same on both descriptions (found by the first live replay: "Oranges, raw,
   all commercial varieties" must not become "Oranges, raw, with peel", equivalent nutrients or not);
4. both records must report BOTH tracked nutrients, and the values must be equivalent per 100 g:
   |difference| <= max(absolute tolerance, 5 % of the larger value); saturated fat 0.1 g, cholesterol 1 mg;
5. the replacement must actually convert the line (it has a usable measure for that unit);
6. by default only VOLUME lines are eligible (`allow_whole_items=False`): a sibling record's single "1 fruit" label would
   otherwise resolve a count that D20 left unresolved on the chosen record (seen in the replay: "1/2 orange" moving from
   "all commercial varieties", which lists sizes, to a valencia record with one typical fruit). Whole-item weights stay
   a D20/2C matter.

Grade or varietal words ("extra virgin", "year round average") are not assumed irrelevant: rule 4 decides, on
the numbers. The substitution is recorded on the decision (`substituted_for`) and the line (`d22_equivalent_record`).
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from roli_nutrition import ErrorResult, NutritionResult
from roli_nutrition.recipe.preparation import record_state

from .convert import _sing, convert_with_portions
from .models import MatchDecision, ParsedIngredient

ABS_TOLERANCE = {"saturated_fat_g": Decimal("0.1"), "cholesterol_mg": Decimal("1")}
REL_TOLERANCE = Decimal("0.05")
# Words that change the physical thing being weighed, even when nutrients per 100 g are equivalent.
FORM_WORDS = ("with peel", "without peel", "peeled", "with skin", "without skin", "skinless", "skin on", "with bone", "boneless", "bone-in",
              "drained", "solids and liquids", "solids and liquid", "with salt", "without salt", "unsalted", "canned", "frozen", "dried", "dehydrated",
              "cooked", "raw", "roasted", "toasted", "shredded", "grated", "chopped", "sliced", "whole", "ground", "powder", "paste", "juice",
              "concentrate", "with seeds", "without seeds", "seeded", "shelled", "in oil", "in water", "in brine", "smoked", "sweetened", "unsweetened")


def form_words(description: str) -> frozenset[str]:
    d = description.lower()
    return frozenset(w for w in FORM_WORDS if w in d)


def same_food_head(a: str, b: str, words: int = 2) -> bool:
    ha = [t.strip().lower() for t in a.split(",")][:words]
    hb = [t.strip().lower() for t in b.split(",")][:words]
    return len(ha) == words and ha == hb


# Words that say how a food is sold or stated, not which food it is. "NFS" and "NS" are USDA's "not further specified": the plain food.
NOT_A_VARIETY = frozenset({"raw", "cooked", "fresh", "nfs", "ns", "plain", "as", "to", "of", "or", "and", "with", "in", "from", "for", "the", "a"})
# USDA first segments that name a class of foods, not one food: "Fish, canned" is no particular fish (12.12.4). A record filed under one may be filed under its own name in
# another table ("Nuts, walnuts, english" and the Survey's "Walnuts"; "Sausage, Italian" and "Italian sausage").
CLASS_HEADS = frozenset({"fish", "shellfish", "seafood", "nuts", "seeds", "pork", "beef", "lamb", "veal", "meat", "sausage", "poultry", "chicken", "turkey", "cheese",
                         "mushrooms", "seaweed", "vegetables", "fruit"})
# A second segment that says how the food is kept or cooked, so two records sharing it need not be the same food ("Pork, cured, bacon" and "Pork, cured, ham"; "Cream, fluid, heavy whipping" and
# "Cream, fluid, half and half").
STATE_SEGMENTS = frozenset({"raw", "cooked", "fresh", "cured", "canned", "frozen", "dried", "fluid", "nfs", "ns"})
# Classes the Survey table files under the food's own name. Not cheese: a Survey record called "Goat" is goat meat, and "Cheese, goat" is filed under Cheese in every table.
OWN_NAME_HEADS = frozenset({"nuts", "seeds", "sausage"})
COLOURS = frozenset({"black", "white", "red", "green", "yellow", "brown", "golden"})


def _segments(description: str) -> list[str]:
    return [t.strip().lower() for t in description.split(",")]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def variety_words(description: str) -> set[str]:
    """The words after the first segment that name which food it is; an "excluding ..." clause names what it is not."""
    _, _, rest = description.lower().partition(",")
    return _words(re.sub(r"\bexcluding\b.*", "", rest)) - NOT_A_VARIETY


def same_food(lender: str, record: str) -> bool:
    """D25, 12.10.7 and 12.12.4: may ``lender`` lend ``record`` a cup weight? True in three cases:
    Never raw against cooked, and never a colour the record does not have. Otherwise:
    1. same first segment, and every word naming the lender's variety is in the record: "Cheese, Parmesan, hard" lends to "Cheese, parmesan, hard"; "Cheese, cottage cheese, with gelatin
       dessert" does not, and "Spinach, creamed" does not lend to "Spinach, baby". A lender naming no variety ("Onions, raw", "Olives, NFS") is the plain food and may lend to any variety;
    2. same first two segments, the second naming the food, with no form the record lacks: "Nuts, walnuts, english" lends to "Nuts, walnuts, dry roasted, with salt added";
    3. a record filed under a class the Survey table files by name, and a lender so filed: "Italian sausage" lends to "Sausage, Italian, pork, mild, raw"."""
    head, record_head = _segments(lender)[0], _segments(record)[0]
    words = _words(re.sub(r"\bwithout\s+\w+", " ", record, flags=re.I))      # "Potatoes, gold, without skin" does not name skin
    variety = variety_words(lender)
    if len({record_state(lender), record_state(record)} & {"raw", "cooked"}) == 2 or (_words(lender) & COLOURS) - words:
        return False                                    # a cooked cup is not a raw one (240 g against 180 g of tomatoes); white pepper is not black
    if _sing(head) == _sing(record_head):
        if variety <= words:
            return True
        return same_food_head(lender, record) and _segments(lender)[1] not in STATE_SEGMENTS and form_words(lender) <= form_words(record)
    return record_head in OWN_NAME_HEADS and {_sing(w) for w in _words(head)} <= {_sing(w) for w in words} and variety <= words


def class_level(lender: str) -> bool:
    """12.12.4: a record that names a whole class ("Nuts, NFS", "Fish, canned", "Mushrooms, raw"), not one food. It lends only when no same-food record has the measure, and the line is labelled."""
    if variety_words(lender) - set(FORM_WORDS):
        return False
    return _segments(lender)[0] in CLASS_HEADS or bool(re.search(r"\b(nfs|ns)\b", lender, re.I))


def equivalent_values(a: NutritionResult, b: NutritionResult) -> bool:
    for nutrient in ("saturated_fat_g", "cholesterol_mg"):
        va, vb = getattr(a, nutrient), getattr(b, nutrient)
        if va is None or vb is None:
            return False
        da, db = Decimal(str(va)), Decimal(str(vb))
        if abs(da - db) > max(ABS_TOLERANCE[nutrient], REL_TOLERANCE * max(da, db)):
            return False
    return True


class EquivalentRecordPolicy:
    def __init__(self, service: Any, *, enabled: bool = True, allow_whole_items: bool = False) -> None:
        self._service = service
        self.enabled = enabled
        self.allow_whole_items = allow_whole_items
        self.log: list[dict] = []

    def find(self, parsed: ParsedIngredient, match: MatchDecision) -> tuple[MatchDecision, ParsedIngredient] | None:
        """(replacement decision, converted line) when an equivalent candidate converts the line; else None."""
        if not self.enabled or match.fdc_id is None or match.description is None:
            return None
        if parsed.grams is not None or parsed.quantity is None or parsed.unit_kind not in ("volume", "count"):
            return None
        if parsed.unit_kind == "count" and not self.allow_whole_items:
            return None
        original = self._service.get_nutrition(match.fdc_id)
        if isinstance(original, ErrorResult):
            return None
        state = record_state(match.description)
        for cand in match.candidates:
            if cand["fdc_id"] == match.fdc_id or not same_food_head(cand["description"], match.description):
                continue
            if record_state(cand["description"]) != state:
                self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "preparation state differs"})
                continue
            if form_words(cand["description"]) != form_words(match.description):
                self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "physical form differs"})
                continue
            other = self._service.get_nutrition(cand["fdc_id"])
            if isinstance(other, ErrorResult) or not equivalent_values(original, other):
                self.log.append({"line": parsed.line, "rejected": cand["fdc_id"], "why": "nutrient values not equivalent or not both reported"})
                continue
            portions = self._service.get_portions(cand["fdc_id"])
            if isinstance(portions, ErrorResult) or not portions.portions:
                continue
            converted = convert_with_portions(parsed, portions.portions, cand["fdc_id"], proxy=(match.match_type == "proxy"))
            if converted.grams is None:
                continue
            replacement = match.model_copy(update={
                "fdc_id": cand["fdc_id"], "description": cand["description"], "data_type": cand["data_type"],
                "record_state": record_state(cand["description"]), "substituted_for": match.fdc_id, "source": "d22",
                "reason": f"D22: {match.description} ({match.fdc_id}) has no usable measure for this line; {cand['description']} ({cand['fdc_id']}) "
                          f"names the same food and state and reports equivalent values per 100 g",
            })
            converted = converted.model_copy(update={"flags": converted.flags + ["d22_equivalent_record"]})
            self.log.append({"line": parsed.line, "from": match.fdc_id, "to": cand["fdc_id"]})
            return replacement, converted
        return None
