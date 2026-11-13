"""Phase 3 local-testing milestone: which dishes of a menu to evaluate when there are more than the cap (Julius, 2026-11-04).

Deterministic Python, from the menu's own words. Every food item with a portion rule is a candidate; each gets a course (starters, salads,
mains, pasta, pizza) from its dish type and a LEAN SCORE from words that usually mean less or more saturated fat (raw fish, salad, vegetables,
grilled, fish -> higher; cream, cheese, cured or fatty meat, fried, pastry -> lower). The shortlist is filled round-robin across courses, the
best score of each course first, so a leaner starter is never crowded out by mains and menu order plays no part. Every item keeps a decision
(selected / skipped / excluded) with the reason and the words that scored, so the run can say exactly what it did not look at and why.
The score chooses what to EVALUATE; it never ranks, never produces a number a tester sees, and the pipeline's own estimate decides the rest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..recipes.models import MenuItem
from ..recipes.portions import PortionRules, dish_type_for

RULES = PortionRules.load()      # 12.16.8: a kind whose rows are all unsourced is not tried, so no model call or search credit goes on a dish that cannot rank

COURSE_OF = {"crudo_starter": "starters", "vegetable_starter": "starters", "fish_starter": "starters", "soup": "starters", "dip": "starters", "snack_bowl": "starters",
             "leaf_salad_starter": "salads", "tomato_salad_starter": "salads", "side_salad": "salads",
             "fish_main": "mains", "meat_main": "mains", "fish_and_chips": "mains", "pasta_main": "pasta", "pizza_neapolitan": "pizza",
             "burger": "handheld", "sandwich": "handheld", "wrap": "handheld", "taco": "handheld", "burrito": "handheld", "quesadilla": "handheld",
             "breakfast_eggs": "breakfast", "breakfast_pancakes": "breakfast", "breakfast_cereal": "breakfast", "toast_plate": "breakfast",
             "side_vegetable": "sides", "side_rice": "sides", "side_bread": "sides", "fried_potato_side": "sides", "dessert": "desserts", "kids_dish": "kids"}   # 12.16.9
COURSE_ORDER = ("salads", "starters", "mains", "pasta", "pizza", "handheld", "breakfast", "sides", "desserts", "kids")   # tie-break between courses with the same best score

# (pattern, weight, label). Each pattern counts once per dish; the words come from name, description and section.
LEAN_WORDS: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"\b(crudo|ceviche|tartare|sashimi|carpaccio|poke|aguachile)\b", re.I), 2, "raw fish or vegetable plate"),
    (re.compile(r"\b(salads?|lettuces?|greens|leaves|slaw|gems?)\b", re.I), 2, "salad"),
    (re.compile(r"\b(tomato(es)?|cucumbers?|beets?|beetroot|asparagus|artichokes?|peppers|padr[oó]n|zucchini|courgettes?|aubergines?|eggplant|broccoli|"
                r"cauliflower|beans|peas|fennel|radish(es)?|citrus|melon|persimmon|pears?|apples?|figs?|grapes?|turnips?|carrots?|squash|mushrooms?|chanterelles?)\b", re.I), 1, "vegetables or fruit"),
    (re.compile(r"\b(grilled|roasted|steamed|poached|seared|wood[- ]?fired|wood fire-roasted|baked|al vapore|alla griglia)\b", re.I), 1, "lean cooking method"),
    (re.compile(r"\b(fish|salmon|tuna|halibut|cod|bass|branzino|snapper|trout|swordfish|mackerel|hamachi|fluke|sole|prawns?|shrimp|squid|octopus|scallops?|"
                r"clams?|mussels?|crab|lobster|anchov\w*|sardines?|bream|seabass|sea bass|yellowfin|bluefin)\b", re.I), 1, "fish or shellfish"),
    (re.compile(r"\b(soup|broth|consomm[eé]|minestrone|zuppa|gazpacho)\b", re.I), 1, "soup or broth"),
]
RICH_WORDS: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"\b(cream|creamy|cr[eè]me|butter|buttered|beurre|hollandaise|b[eé]arnaise|alfredo|carbonara|mac and cheese|mac ?n ?cheese|burro)\b", re.I), -2, "cream or butter"),
    (re.compile(r"\b(cheeses?|burrata|mozzarella|fior di latte|taleggio|pecorino|parmesan|parmigiano|gorgonzola|stilton|cheddar|camembert|brie|fontina|gruy[eè]re|"
                r"provolone|halloumi|feta|goat'?s? cheese|ricotta|mascarpone|caciocavallo|stracciatella|raclette|fondue|queso|emmental|wagon wheel|sheep cheese)\b", re.I), -2, "cheese"),
    (re.compile(r"\b(bacon|pancetta|guanciale|lardo|lardons|sausages?|salsiccia|chorizo|'?nduja|salami|soppressata|pepperoni|mortadella|prosciutto|speck|coppa|ham|"
                r"pork belly|belly|ribs?|spare ?ribs|brisket|short ?ribs?|ribeye|rib-eye|wagyu|lamb|duck|foie|p[aâ]t[eé]|confit|merguez|meatballs?|crackling|pigs? in blankets?)\b", re.I), -2, "fatty or cured meat"),
    (re.compile(r"\b(fried|deep[- ]fried|crispy|crisp|battered|tempura|fritto|fritti|fritters?|croquettes?|arancini|schnitzel|katsu|chips|fries|frites|shoestring|"
                r"scotch eggs?|doughnuts?|donuts?)\b", re.I), -2, "fried"),
    (re.compile(r"\b(steak|sirloin|beef|pork|chops?|veal|venison|burgers?|hamburger|bavette|fillet steak)\b", re.I), -1, "red meat"),
    (re.compile(r"\b(eggs?|yolks?|aioli|a[iï]oli|mayo|mayonnaise)\b", re.I), -1, "egg or egg-based sauce"),
    (re.compile(r"\b(pizza|margherita|marinara|calzone|puttanesca|salsiccia bianca)\b", re.I), -1, "pizza (cheese)"),
    (re.compile(r"\b(pies?|pastry|puff|tarts?|quiche|gratin|dauphinoise|pudding|cheesecake|brownie)\b", re.I), -2, "pastry or gratin"),
]


@dataclass
class Candidate:
    index: int
    item: MenuItem
    dish_type: str | None
    course: str | None
    score: int = 0
    matched: list[str] = field(default_factory=list)
    decision: str = "excluded"                  # selected | skipped | excluded
    reason: str = ""
    rank: int | None = None                     # position in the course-balanced order (1 = first chosen), candidates only
    kind: dict[str, Any] | None = None          # 12.16.11: the dish-kind call's answer, when the call is on

    def selection(self) -> dict[str, Any]:
        return {"decision": self.decision, "course": self.course, "lean_score": self.score, "matched": list(self.matched), "rank": self.rank, "reason": self.reason, **({"kind": self.kind} if self.kind else {})}


def lean_score(item: MenuItem) -> tuple[int, list[str]]:
    text = f"{item.name} {item.description} {item.section}"
    score, matched = 0, []
    for pattern, weight, label in LEAN_WORDS + RICH_WORDS:
        m = pattern.search(text)
        if m:
            score += weight
            matched.append(f"{'+' if weight > 0 else ''}{weight} {label} ('{m.group(0).lower()}')")
    return score, matched


def select_dishes(menu: dict[str, Any], max_dishes: int, kinds: dict[int, Any] | None = None) -> list[Candidate]:
    """Every menu item with its decision. Selected dishes come out in menu order; `rank` records the balanced order they were chosen in. ``kinds`` (12.16.11) is the dish-kind call's answer
    per menu index; without it the word lists decide."""
    out: list[Candidate] = []
    for i, raw in enumerate(menu.get("items") or []):
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            continue
        item = MenuItem(name=str(raw.get("name", "")).strip(), description=str(raw.get("description") or "").strip(), section=str(raw.get("section") or "").strip())
        cat = str(raw.get("category") or "food")
        kind = kinds.get(i) if kinds else None
        dt = kind.family if kind is not None else dish_type_for(item)
        c = Candidate(index=i, item=item, dish_type=dt, course=COURSE_OF.get(dt or ""))
        if cat != "food":
            c.reason = f"excluded: not a dish ({cat})"
        elif str(raw.get("belongs_to") or "").strip():
            c.reason = "excluded: an option of another item"
        elif kind is not None and kind.family is None and kind.source == "model":
            c.reason = f"excluded: the dish-kind call read it as '{kind.model_kind}' ({kind.reason[:60]})"
        elif dt is None:
            c.reason = "excluded: no portion rule for this kind of item"
        elif not RULES.for_dish_type(dt, f"{item.name} {item.description}"):
            c.reason = "excluded: no plate-size row with a measured source applies to this kind of item (12.16.8)"
        else:
            c.score, c.matched = lean_score(item)
            c.decision = "candidate"
        out.append(c)
    candidates = [c for c in out if c.decision == "candidate"]
    by_course: dict[str, list[Candidate]] = {}
    for c in sorted(candidates, key=lambda c: (-c.score, c.index)):
        by_course.setdefault(c.course or "other", []).append(c)
    # round-robin: the course with the best remaining score goes first; ties follow COURSE_ORDER
    order: list[Candidate] = []
    while any(by_course.values()):
        courses = [k for k, v in by_course.items() if v]
        courses.sort(key=lambda k: (-by_course[k][0].score, COURSE_ORDER.index(k) if k in COURSE_ORDER else 99))
        for k in courses:
            if by_course[k]:
                order.append(by_course[k].pop(0))
    n = len(order)
    for pos, c in enumerate(order, start=1):
        c.rank = pos
        words = "; ".join(c.matched) if c.matched else "no scoring words"
        if pos <= max_dishes:
            c.decision, c.reason = "selected", f"selected: {c.course} candidate, lean score {c.score:+d} ({words}); chosen {pos} of {n} across courses"
        else:
            c.decision, c.reason = "skipped", f"skipped: beyond the cap of {max_dishes} dishes (chosen {pos} of {n}; {c.course}, lean score {c.score:+d}: {words})"
    return out


# 12.16.4: the kind a tester reads for a dish Roli cannot size yet, from the dish's own words; the last word of the name otherwise.
KIND_WORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(sandwich|sandwiches|sub|subs|panini|bap|baps|toastie|toasties)\b", re.I), "sandwiches"), (re.compile(r"\b(burgers?|hamburgers?|cheeseburgers?)\b", re.I), "burgers"),
    (re.compile(r"\btoast\b", re.I), "toast"), (re.compile(r"\b(wraps?)\b", re.I), "wraps"), (re.compile(r"\b(tacos?)\b", re.I), "tacos"), (re.compile(r"\b(burritos?)\b", re.I), "burritos"),
    (re.compile(r"\b(quesadillas?|mulitas?)\b", re.I), "quesadillas"), (re.compile(r"\b(granola|muesli)\b", re.I), "granola"), (re.compile(r"\b(porridge|oatmeal)\b", re.I), "porridge"),
    (re.compile(r"\b(pancakes?|waffles?|crepes?)\b", re.I), "pancakes"), (re.compile(r"\b(eggs?|omelett?es?)\b", re.I), "egg dishes"), (re.compile(r"\b(soups?|broth)\b", re.I), "soups"),
    (re.compile(r"\b(dips?|hummus|guacamole|salsa)\b", re.I), "dips"), (re.compile(r"\b(breads?|focaccia|flatbread|sourdough|baguette|ciabatta|naan|roti)\b", re.I), "bread"),
    (re.compile(r"\b(fries|chips)\b", re.I), "fries"), (re.compile(r"\b(cakes?|brownies?|cheesecake|tarts?|pies?|ice cream|gelato|sorbet|puddings?|desserts?|tiramisu|budino)\b", re.I), "desserts"),
    (re.compile(r"\b(nachos|platters?|boards?)\b", re.I), "platters"), (re.compile(r"\b(bowls?)\b", re.I), "bowls"),
]


def kind_label(item: MenuItem) -> str:
    """"Poached Eggs on Toast" -> toast; "Granola" -> granola; an unknown dish -> its last word."""
    text = f"{item.name} {item.section}"
    for pattern, label in KIND_WORDS:
        if pattern.search(text):
            return label
    words = re.findall(r"[a-zà-ü]+", item.name.lower())
    return words[-1] if words else "dishes"


def unsized_kinds(cands: list[Candidate]) -> list[str]:
    """The kinds of the food dishes no portion rule covers, in menu order, each once."""
    out: list[str] = []
    for c in cands:
        if c.decision == "excluded" and (c.reason.startswith("excluded: no portion rule") or c.reason.startswith("excluded: no plate-size row")):
            k = kind_label(c.item)
            if k not in out:
                out.append(k)
    return out


def candidate_items(menu: dict[str, Any], max_dishes: int) -> tuple[list[tuple[int, MenuItem]], list[tuple[int, MenuItem, str]]]:
    """(items to evaluate in menu order, items set aside with the reason). Kept for the Phase 3 callers and tests."""
    cands = select_dishes(menu, max_dishes)
    chosen = [(c.index, c.item) for c in cands if c.decision == "selected"]
    aside = [(c.index, c.item, c.reason) for c in cands if c.decision != "selected"]
    return chosen, aside
