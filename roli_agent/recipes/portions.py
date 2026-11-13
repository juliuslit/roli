"""Phase 2D: restaurant portion-size normalisation (SPEC_2D_restaurant_portions.md; built 2026-11-03, internal only).

A scenario's whole-recipe figures are mapped onto one restaurant plate as a FRACTION f of the recipe, with f stated as a low/high range,
the rule that produced it named, and the recipe-basis figures preserved untouched beside the result. Three models:

    P1 unit dish        f = dough ball / recipe dough, capped at 1  when the dough weight is known; else f = 1 / k, k = pizzas the recipe makes (one unless the page says otherwise)
    P2 plate weight     f = W / M_served                            W = plate-weight range (rule row); M_served = the recipe's own mass (raw = served)
    P3 key ingredient   f = K / K_recipe                            K = raw fish per plate (rule row); K_recipe = the recipe's fish weight
    12.16.3: a plate is never more than one whole recipe; a recipe whose share would exceed 1 is not used for portioning, and the reason says so.

The per-portion figures come from the UNCHANGED Phase 2A calculator re-run with `servings = 1 / f` on the same line list (a per-plate
assumption, marked `quantity_basis: per_serving`, then counts once per plate; a recipe line scales with f). Completeness is inherited: a
subtotal scaled is still a subtotal. f is never derived from the recipe's serving count. Every rule row is `proposed_unreviewed` until
Julius approves it, so every output is `portion_proposed` and internal.
"""

from __future__ import annotations

import csv
import re
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

from roli_nutrition.recipe import RecipeCalculator, RecipeResult

from .inference import LOW_FAT_G_PER_100G, ZERO_WEIGHT_WORDS, NutrientFacts, apply_inference_layer, completeness_basis
from .models import (AdaptedPair, AdaptedScenario, MenuItem, PortionedBound, PortionedScenario, PortionFraction, Scenario)
from .relevance import RAW_DISH_TYPES, raw_family

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
DEFAULT_RULES = Path(__file__).resolve().parent / "portion_rules.csv"
DEFAULT_FIGURES = Path(__file__).resolve().parent / "reference_figures.csv"
FISH_WORDS = re.compile(r"\b(salmon|tuna|halibut|cod|bass|seabass|sea bass|branzino|snapper|trout|swordfish|mackerel|hamachi|fluke|fish|scallops?|barramundi|baramundi|cobia|whiting|"
                        r"sole|turbot|monkfish|hake|haddock|prawns?|shrimp|squid|calamari|octopus|mussels?|clams?|lobster|crab|oysters?|sardines?|bream|kingfish|mahi|grouper|tilapia|catfish)\b", re.I)
MEAT_WORDS = re.compile(r"\b(beef|steak|sirloin|ribeye|rib-eye|fillet steak|bavette|tenderloin|pork|chop|lamb|chicken|duck|veal|venison|burger|hamburger|cheeseburger|"
                        r"schnitzel|sausages?|merguez|short rib|brisket|turkey|quail|rabbit)\b", re.I)
PASTA_WORDS = re.compile(r"\b(pasta|spaghetti|spaghettini|tagliatelle|pappardelle|linguine|rigatoni|penne|orecchiette|cappelletti|triangoli|scarpinocc|ravioli|tortelli|"
                         r"tortellini|agnolotti|gnocchi|lasagn[ae]|fettuccine|bucatini|carbonara|cacio e pepe|macaroni|soprese|strozzapreti|noodles?|chow mein|lo mein|chop suey|pad thai)\b", re.I)
SALAD_WORDS = re.compile(r"\b(salad|lettuces?|gems?|greens|leaves|caesar|slaw)\b", re.I)
VEG_WORDS = re.compile(r"\b(beans?|broccoli|brocolli|aubergine|eggplant|cauliflower|peppers?|asparagus|artichokes?|squash|zucchini|courgette|mushrooms?|beets?|beetroot|"
                       r"carrots?|potato(es)?|cabbage|kale|spinach|chard|fennel|ricotta|burrata|olives|hummus|arancini|croquettes?)\b", re.I)
EXCLUDED_SECTIONS = re.compile(r"\b(desserts?|dolci|sweets?|puddings?|bread|breads|drinks?|beverages?|wine|wines|beer|cocktails?|coffee|tea|kids|ni[nñ]os|children|sides?|add[- ]ons?|extras?|"
                               r"sauces?|breakfast|platters?|to share|sharing|boards?)\b", re.I)
MAIN_SECTIONS = re.compile(r"\b(entr[eé]es?|mains?|main course|plates?|large plates?|secondi|classics|grill|from the grill|specials?)\b", re.I)
FISH_AND_CHIPS = re.compile(r"\b(fish|cod|haddock|pollock|plaice|scampi)\b[^,;]{0,25}\b(&|and|n'?|\+)\s*chips\b|\bfish\s*(&|and|n'?)\s*chips\b", re.I)
SNACK_BOWL = re.compile(r"\b(olives?|nocellara|castelvetrano|kalamata|gordal|nuts|almonds|cashews|peanuts|pistachios|walnuts|hazelnuts|pecans|macadamias?)\b", re.I)
STARTER_SECTIONS = re.compile(r"\b(to start|starters?|appetizers?|antipast[io]|small plates?|first|primi|snacks?|bar snacks)\b", re.I)

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "eight": 8, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "8": 8, "half": 2}
_N = r"(one|two|three|four|five|six|eight|\d{1,2})"
YIELD_UNITS = re.compile(rf"^\s*{_N}\s+(?:\d{{1,2}}[- ]inch\s+)?(?:pizzas?|pies?|crusts?|flatbreads?)\b", re.I)
MAKES_UNITS = re.compile(rf"\b(?:makes?|yields?|enough for|for)\s+{_N}\s+(?:\d{{1,2}}[- ]inch\s+)?(?:pizzas?|pies?|crusts?)\b", re.I)
DIVIDE_DOUGH = re.compile(rf"\b(?:divide|separate|cut|split|portion)\b[^.]{{0,60}}?\bdough\b[^.]{{0,40}}?\b(?:in (half)|into (?:halves|{_N}\b(?:\s+equal(?:-sized|ly| sized)?)?\s*(?:pieces|portions|balls|parts|rounds|equal)?))", re.I)
RESERVE = re.compile(r"\breserve[sd]?\b[^.]{0,40}?\b(?:for another use|for later|for another)", re.I)
SHAPE_ONE = re.compile(r"\b(?:roll|stretch|shape|press|form|pat)\b[^.]{0,40}?\b(?:it|the dough|dough|ball)\b[^.]{0,30}?\binto (?:a|an|one)\s+(?:roughly\s+)?(?:\d{1,2}[- ]inch\s+)?(?:circle|round|disc|disk|pizza|oval|rectangle)", re.I)
DIAMETER = re.compile(r"(\d{1,2})[- ]inch\s+(circle|round|disc|disk|pizza|pie|oval)\b", re.I)
PER_SERVING_PLACES = Decimal("0.000001")
DOUGH_LINE = re.compile(r"\b(dough|crust|pizza base)\b", re.I)
FLOUR = re.compile(r"\b(flour|semolina)\b", re.I)
DOUGH_PARTS = re.compile(r"\b(flour|semolina|water|yeast|salt)\b", re.I)
DUSTING = re.compile(r"\b(dust\w*|for the peel|sprinkl\w*|for rolling|for shaping)\b", re.I)
NON_UNIT_STYLE = re.compile(r"deep[- ]?dish|chicago[- ]style|detroit[- ]style|sheet[- ]pan|pan[- ]pizza|stuffed[- ]crust|calzone|grandma[- ]pie|sicilian[- ]pizza|focaccia", re.I)


# -- the rules table ---------------------------------------------------------------------------------------


class PortionRule:
    def __init__(self, row: dict[str, str]) -> None:
        self.id = row["id"]
        self.dish_type = row["dish_type"]
        self.model = row["model"]
        self.low = Decimal(row["low"])
        self.high = Decimal(row["high"])
        self.unit = row.get("unit", "")
        # P3: the first word(s) of the USDA description of the key lines ("fish"; "beef, pork, lamb, ..."), several allowed, comma-separated
        self.key_record_heads = tuple(h.strip().lower() for h in (row.get("key_record_head") or "").split(",") if h.strip())
        self.key_record_head = self.key_record_heads[0] if self.key_record_heads else ""
        self.basis = row.get("basis", "")
        self.sources = row.get("sources", "")
        self.review_status = row.get("review_status", "")
        # 12.16.7: the measured plate behind the row, how many chain items it rests on and when they were read; P3 rows keep the plate weight beside the key share
        self.plate_low = Decimal(row["plate_low_g"]) if (row.get("plate_low_g") or "").strip() else None
        self.plate_high = Decimal(row["plate_high_g"]) if (row.get("plate_high_g") or "").strip() else None
        self.n_items = int(row["n_items"]) if (row.get("n_items") or "").strip() else 0
        self.read_on = (row.get("read_on") or "").strip()
        self.approved_by = row.get("approved_by", "").strip()
        self.notes = row.get("notes", "")
        # 3D (SPEC_3_mvp.md 12.2): the row is a dish-family CARD. menu_words limits it to dishes whose words match (olives vs nuts in a snack bowl);
        # typical_choices names the records swapped into a USDA Survey record's inputs when the menu does not name the species or fat.
        # 3E (12.9.6-7): the PUBLISHED figures are rows of reference_figures.csv, one per figure, because the check needs each figure's business, basis and
        # total fat. They are used only by the reference check, never in a total.
        pat = (row.get("menu_words") or "").strip()
        self.menu_words = re.compile(pat, re.I) if pat else None
        self.figures: list[ReferenceFigure] = []
        self.choices = parse_choices(row.get("typical_choices") or "")

    @property
    def confidence(self) -> str:
        return "portion_reviewed" if self.approved_by and self.sourced else "portion_proposed"     # 12.18: an approved, sourced row; an unsourced row stays proposed even when its unsourced status is approved

    @property
    def sourced(self) -> bool:
        """12.2.2 and 12.16.8: a row whose status is `unsourced`, or whose sources say 'no source', has no measured figure behind it; its dishes are not ranked."""
        return not self.review_status.startswith("unsourced") and not re.search(r"\bno (?:measured )?source\b", self.sources or "", re.I)

    @property
    def has_reference(self) -> bool:
        return bool(self.figures)

    def figures_on(self, basis: str) -> list["ReferenceFigure"]:
        return [f for f in self.figures if f.basis == basis]

    @property
    def ref_sources(self) -> str:
        return "; ".join(f"{f.business}, {f.product}: {f.sat_fat_g} g ({f.basis}; {f.source_kind}; {f.provenance}; {f.read_on})" for f in self.figures)

    def applies_to(self, menu_text: str | None) -> bool:
        return self.menu_words is None or (menu_text is not None and bool(self.menu_words.search(menu_text)))


class ReferenceFigure:
    """One published figure. `group` is what makes two figures independent (12.9.6): the owning business, or the brand for a retail label."""

    def __init__(self, row: dict[str, str]) -> None:
        self.id, self.card, self.group, self.business, self.product = row["id"], row["card"], row["group"], row["business"], row["product"]
        self.n_businesses = int(row["n_businesses"]) if (row.get("n_businesses") or "").strip() else 1   # 12.16.7: an aggregate row (MenuStat) stands for this many chains
        self.basis = row["basis"]                                   # per_plate | per_100g
        self.sat_fat_g = Decimal(row["sat_fat_g"])
        self.total_fat_g = Decimal(row["total_fat_g"]) if (row.get("total_fat_g") or "").strip() else None
        self.stated_choice = (row.get("stated_choice") or "").strip()   # the choice the business itself states (12.9.7)
        self.source_kind, self.provenance, self.read_on, self.url, self.notes = row["source_kind"], row["provenance"], row["read_on"], row["url"], row.get("notes", "")

    def choice(self, vegetable_max: Decimal, animal_min: Decimal) -> tuple[str, str]:
        """(the frying fat this figure represents, the basis of that label), '' when it carries none. 12.9.7: stated by the business, or shown by the figure's
        saturated share of total fat: below `vegetable_max` a liquid vegetable oil, above `animal_min` beef dripping or palm."""
        if self.stated_choice:
            return self.stated_choice, "stated by the business"
        if self.total_fat_g:
            share = self.sat_fat_g / self.total_fat_g
            if share < vegetable_max:
                return VEGETABLE_OIL, f"shown by the figure: saturated share {share:.0%}"
            if share > animal_min:
                return BEEF_DRIPPING, f"shown by the figure: saturated share {share:.0%}"
        return "", ""


class Choice:
    """One option of a card's choice group: the USDA record swapped in and the menu words that name it ("cod")."""

    def __init__(self, fdc_id: int, description: str, keywords: list[str]) -> None:
        self.fdc_id, self.description, self.keywords = fdc_id, description, keywords
        self.label = keywords[0] if keywords else description

    def named_in(self, text: str) -> bool:
        return any(re.search(rf"\b{re.escape(k)}\b", text, re.I) for k in self.keywords)


def parse_choices(text: str) -> dict[str, list[Choice]]:
    """``fish: 171955 Fish, cod, Atlantic, raw [cod] | 171964 Fish, haddock, raw [haddock]; oil: 2710180 Vegetable oil, NFS [vegetable oil] | ...``"""
    out: dict[str, list[Choice]] = {}
    for group in filter(None, (g.strip() for g in text.split(";"))):
        name, _, options = group.partition(":")
        choices = []
        for opt in filter(None, (o.strip() for o in options.split("|"))):
            m = re.match(r"(\d+)\s+(.*?)\s*(?:\[(.*)\])?$", opt)
            if not m:
                continue
            keywords = [k.strip() for k in (m.group(3) or "").split(",") if k.strip()]
            if not keywords:
                parts = [x.strip() for x in m.group(2).split(",")]
                keywords = [parts[1] if len(parts) > 1 else parts[0]]       # "Fish, haddock, raw" -> "haddock"
            choices.append(Choice(int(m.group(1)), m.group(2).strip(), keywords))
        if choices:
            out[name.strip().lower()] = choices
    return out


class PortionRules:
    def __init__(self, rows: list[PortionRule]) -> None:
        self.rows = rows

    @classmethod
    def load(cls, path: Path = DEFAULT_RULES, figures: Path = DEFAULT_FIGURES) -> "PortionRules":
        with Path(path).open(encoding="utf-8") as f:
            rules = cls([PortionRule(r) for r in csv.DictReader(f)])
        by_id = {r.id: r for r in rules.rows}
        with Path(figures).open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                by_id[row["card"]].figures.append(ReferenceFigure(row))
        return rules

    def for_dish_type(self, dish_type: str, menu_text: str | None = None, *, allow_unsourced: bool = True) -> list[PortionRule]:
        """Rows for the dish type in the spec's preference order: P1 (the page's own unit count), then P3 (a resolved key ingredient), then P2.
        3D: a row with menu_words applies only when the menu text matches; with ``allow_unsourced`` False (the reference check is off) rows whose
        sources say 'no source' are left out (12.2.2)."""
        order = {"P1": 0, "P3": 1, "P2": 2}
        rows = [r for r in self.rows if r.dish_type == dish_type and r.applies_to(menu_text) and (allow_unsourced or r.sourced) and not r.review_status.startswith("unsourced")]
        return sorted(rows, key=lambda r: order.get(r.model, 9))

    def plate_card(self, dish_type: str | None) -> "PortionRule | None":
        """The card whose choices apply to every fried component of the plate (12.9.8)."""
        return next((r for r in self.rows if r.dish_type == dish_type and r.choices), None) if dish_type else None

    def card_for(self, dish_type: str | None, menu_text: str | None = None) -> "PortionRule | None":
        """The dish-family card the reference check reads: the first row of the type whose words match and that carries a published figure."""
        if dish_type is None:
            return None
        return next((r for r in self.rows if r.dish_type == dish_type and r.applies_to(menu_text) and r.has_reference), None)

    def unsourced(self) -> list[PortionRule]:
        return [r for r in self.rows if not r.sourced]


# -- dish type and the page's own unit count -------------------------------------------------------------


FAMILIES: dict[str, str] = {
    # the card families (12.16.9-11): what each is, in the words the dish-kind call also reads
    "pizza_neapolitan": "a pizza (whole, thin round)", "fish_and_chips": "battered white fish with chips", "crudo_starter": "a raw fish or vegetable plate (crudo, ceviche, tartare, sashimi, poke, carpaccio)",
    "fish_main": "a fish or shellfish main course", "fish_starter": "a fish or shellfish starter", "meat_main": "a meat or poultry main course (steak, chops, sausages, roast, a plated schnitzel)",
    "pasta_main": "a pasta or noodle dish", "leaf_salad_starter": "a leaf salad as a starter or side", "tomato_salad_starter": "a composed tomato salad",
    "vegetable_starter": "any other starter or small plate (vegetable, cheese, grain, fried bites, dumplings)", "snack_bowl": "a bowl of olives or nuts as a bar snack",
    "burger": "a burger in a bun", "sandwich": "a sandwich, sub, panini, bap or toastie", "wrap": "a wrap", "taco": "tacos", "burrito": "a burrito", "quesadilla": "a quesadilla or mulita",
    "breakfast_eggs": "an egg plate: eggs any style, omelette, benedict, shakshuka, a cooked breakfast", "breakfast_pancakes": "pancakes, waffles, French toast or crepes",
    "breakfast_cereal": "granola, muesli, porridge, oatmeal or cereal", "toast_plate": "toast or something on toast (avocado, beans, butter and jam)",
    "soup": "a soup or broth", "dip": "a dip, spread, sauce or butter sold on its own", "side_salad": "a side salad", "side_vegetable": "a vegetable side (greens, beans, slaw, onion rings)",
    "side_rice": "rice or a rice dish", "side_bread": "bread, garlic bread, focaccia, tortillas", "fried_potato_side": "fries, chips, shoestring or roast potatoes", "dessert": "a dessert, cake, pastry or ice cream",
    "kids_dish": "a children's menu dish",
}
KIDS_SECTIONS = re.compile(r"\b(kids?|children|ni[nñ]os|little ones|junior)\b", re.I)
DESSERT_SECTIONS = re.compile(r"\b(desserts?|dolci|sweets?|puddings?|something sweet|bakery|pies|cakes)\b", re.I)
DESSERT_WORDS = re.compile(r"\b(cakes?|brownies?|cheesecake|tarts?|pies?|ice cream|gelato|sorbet|puddings?|doughnuts?|donuts?|flapjacks?|cinnamon buns?|budino|tiramisu|crumble|cookies?|"
                           r"panna cotta|mousse|sundae|affogato|cannoli|profiteroles?|meringue|brûlée|brulee|custard|cobbler|half moon)\b", re.I)
DIP_SECTIONS = re.compile(r"\b(dips?|sauces?|only sauces|condiments?|spreads?)\b", re.I)
DIP_WORDS = re.compile(r"\b(dips?|hummus|houmous|guacamole|salsa|tapenade|tzatziki|raita|baba ganoush|queso|aioli|a[iï]oli|mayo|mayonnaise|chutney|jam|pesto|butter|oil|ketchup)\b", re.I)
SOUP_WORDS = re.compile(r"\b(soups?|broth|chowder|bisque|minestrone|consomm[eé]|zuppa|gazpacho|ramen|pho)\b", re.I)
BURGER_WORDS = re.compile(r"\b(burgers?|hamburgers?|cheeseburgers?|grillburger)\b", re.I)
SANDWICH_WORDS = re.compile(r"\b(sandwich|sandwiches|sandwhich|panini|paninis|subs?|baps?|toasties?|hoagies?|po'? ?boys?|sliders?|ciabatta sandwich|club)\b", re.I)
WRAP_WORDS, TACO_WORDS, BURRITO_WORDS, QUESADILLA_WORDS = re.compile(r"\bwraps?\b", re.I), re.compile(r"\btacos?\b", re.I), re.compile(r"\bburritos?\b", re.I), re.compile(r"\b(quesadillas?|mulitas?)\b", re.I)
BREAKFAST_SECTIONS = re.compile(r"\b(breakfast|brunch|all day breakfast)\b", re.I)
EGG_WORDS = re.compile(r"\b(eggs?|omelett?es?|benedict|royale|florentine|shakshuka|scrambles?|frittata|full house|full english|fry[- ]up|skillet)\b", re.I)
EGG_DISH_WORDS = re.compile(r"\b(omelett?es?|benedict|royale|florentine|shakshuka|scrambles?|scrambled eggs?|fried eggs?|poached eggs?|boiled eggs?|frittata|full house|full english|fry[- ]up|skillet)\b", re.I)   # a bare "egg" counts only in a breakfast section (scotch egg, egg fried rice are not breakfast plates)
PANCAKE_WORDS = re.compile(r"\b(pancakes?|waffles?|french toast|crepes?|cr[eê]pes?)\b", re.I)
CEREAL_WORDS = re.compile(r"\b(granola|muesli|porridge|oatmeal|oats|cereal|bircher|yoghurt bowl|yogurt bowl|acai)\b", re.I)
TOAST_WORDS = re.compile(r"\btoast\b", re.I)
RICE_WORDS = re.compile(r"\b(rice|risotto|pilaf|biryani|paella)\b", re.I)
BREAD_WORDS = re.compile(r"\b(bread|breads|focaccia|flatbread|sourdough|baguette|levain|ciabatta|grissini|naan|roti|tortillas?|garlic knots?|breadsticks?|sticks & dip|dough balls)\b", re.I)
FRIES_WORDS = re.compile(r"\b(fries|chips|frites|shoestring potatoes?|papas fritas|wedges|roast potatoes|hash browns?)\b", re.I)
SIDE_SECTIONS = re.compile(r"\b(sides?|side dishes|extras?|add[- ]ons?|accompaniments)\b", re.I)
PLATTER_WORDS = re.compile(r"\b(platters?|boards?|to share|sharing|slate|charcuterie)\b", re.I)


SECTION_KIND_WORDS = (KIDS_SECTIONS, DESSERT_SECTIONS, DIP_SECTIONS, SIDE_SECTIONS, re.compile(r"\b(salads?|starters?|appetizers?|antipasti|soups?|pizz[ae]s?|pastas?|mains?|burgers?|sandwiches)\b", re.I))


def section_lists_kinds(section: str) -> bool:
    """3I reruns (2026-11-07): a heading that lists several kinds ("STARTERS, SALADS, SIDES, DIPS") describes a page, not a dish, so it must not decide the kind; the item's
    own words do. A heading naming one kind ("Desserts & Coffee", "Kids Menu") still decides."""
    return sum(1 for pat in SECTION_KIND_WORDS if pat.search(section)) >= 2


def dish_type_for(item: MenuItem) -> str | None:
    """Deterministic, from the menu's own words, one of FAMILIES or None (12.16.9: desserts, sides and children's dishes have families now; drinks and add-ons are set aside by
    selection before this is asked). The order is the order of the tests below; the first match wins."""
    name, section = item.name.lower(), item.section.lower()
    if section_lists_kinds(section):
        section = ""
    text = f"{name} {item.description.lower()}"
    if KIDS_SECTIONS.search(section) or re.search(r"\b(kids?|children'?s?) (meal|menu|pizza|portion)\b", name):
        return "kids_dish"
    if DESSERT_SECTIONS.search(section) or (DESSERT_WORDS.search(name) and not PANCAKE_WORDS.search(name)):
        return "dessert"
    if DIP_SECTIONS.search(section) or (DIP_WORDS.search(name) and len(name.split()) <= 3 and not FRIES_WORDS.search(name)):
        return "dip"
    if re.search(r"\bpizz[ae]s?\b", section) or re.search(r"\b(pizza|margherita|marinara)\b", name):
        return "pizza_neapolitan"
    if SOUP_WORDS.search(name) or re.search(r"\bsoups?\b", section):
        return "soup"
    if FISH_AND_CHIPS.search(name):
        return "fish_and_chips"
    if BURGER_WORDS.search(name) or (BURGER_WORDS.search(section) and not re.search(r"\b(sandwich|salad|wrap)\b", name)):
        return "burger"
    if TACO_WORDS.search(name) or (TACO_WORDS.search(section) and not QUESADILLA_WORDS.search(name)):
        return "taco"
    if BURRITO_WORDS.search(name):
        return "burrito"
    if QUESADILLA_WORDS.search(name) or QUESADILLA_WORDS.search(section):
        return "quesadilla"
    if WRAP_WORDS.search(name):
        return "wrap"
    if SANDWICH_WORDS.search(name) or SANDWICH_WORDS.search(section):
        return "sandwich"
    if PANCAKE_WORDS.search(name):
        return "breakfast_pancakes"
    if CEREAL_WORDS.search(name):
        return "breakfast_cereal"
    if EGG_DISH_WORDS.search(name) or (BREAKFAST_SECTIONS.search(section) and EGG_WORDS.search(text)):
        return "breakfast_eggs"
    if TOAST_WORDS.search(name):
        return "toast_plate"
    if FRIES_WORDS.search(name) and not MEAT_WORDS.search(name) and not FISH_WORDS.search(name):
        return "fried_potato_side"
    if BREAD_WORDS.search(name) and not MEAT_WORDS.search(name) and not FISH_WORDS.search(name) and not SALAD_WORDS.search(name):
        return "side_bread"
    if SIDE_SECTIONS.search(section) and not MAIN_SECTIONS.search(section):
        if SALAD_WORDS.search(name):
            return "side_salad"
        if RICE_WORDS.search(name):
            return "side_rice"
        return "side_vegetable"
    if PLATTER_WORDS.search(section) or PLATTER_WORDS.search(name):
        return None                                                        # a shared board is not one plate; no family
    snack_head = re.split(r",|;|:|\bwith\b|\band\b", name)[0].strip()
    if SNACK_BOWL.search(snack_head) and len(snack_head.split()) <= 4 and not MEAT_WORDS.search(name) and not FISH_WORDS.search(name) and not SALAD_WORDS.search(name) \
            and not PASTA_WORDS.search(name) and not re.search(r"\banchov", name):
        return "snack_bowl"                                                # 3D card: a bowl of olives or nuts named as the dish; "anchovies with ... olives" is not one
    head = name.split(";")[0].split(":")[0]
    if MEAT_WORDS.search(head) and SALAD_WORDS.search(name) and not SALAD_WORDS.search(head):
        return "meat_main"                                                 # "chicken for two ...; warm bread salad": the salad is the side, the meat the dish (Phase 3)
    family = raw_family(item)
    if family == "raw_fish" or any(re.search(rf"\b{w}\b", name) for w in RAW_DISH_TYPES):
        return "crudo_starter"
    if PASTA_WORDS.search(name) or re.search(r"\b(pasta|paste|primi|noodles?)\b", section):
        return "pasta_main"                                                # "spaghetti with shrimp" is a pasta, not a fish main
    if FISH_WORDS.search(name):
        return "fish_starter" if STARTER_SECTIONS.search(section) else "fish_main"
    if family == "leaf_salad" or SALAD_WORDS.search(name):
        return "leaf_salad_starter"
    if re.search(r"\btomato(es)?\b", name) and not RICE_WORDS.search(name):
        return "tomato_salad_starter"
    if RICE_WORDS.search(name) or re.search(r"\brice\b", section):
        return "side_rice"
    if STARTER_SECTIONS.search(section):
        return "vegetable_starter"                                        # any other starter: a plated starter weight (P2), meat word or not
    if MEAT_WORDS.search(name):
        return "meat_main"
    if VEG_WORDS.search(name) and not MAIN_SECTIONS.search(section):
        return "vegetable_starter"
    return None


def unit_count_from_text(yield_text: str, method_text: str) -> dict[str, Any]:
    """How many unit dishes (pizzas) the recipe makes, from the page's own words, never from its serving count. Returns k, the evidence
    sentence, the stated diameter (inches) when any, and whether part of the dough is reserved for another use (then the list does not
    describe one unit and P1 does not apply)."""
    out: dict[str, Any] = {"k": None, "evidence": "", "diameter_in": None, "reserved": False, "source": None}
    text = method_text or ""
    m = YIELD_UNITS.match(yield_text or "")
    if m:
        out.update(k=NUMBER_WORDS.get(m.group(1).lower(), None) or int(m.group(1)), evidence=f"yield text: {yield_text.strip()!r}", source="yield_text")
    if out["k"] is None:
        m = MAKES_UNITS.search(text)
        if m:
            out.update(k=NUMBER_WORDS.get(m.group(1).lower()) or int(m.group(1)), evidence=f"method text: {_sentence(text, m.start())!r}", source="method_makes")
    if out["k"] is None:
        m = DIVIDE_DOUGH.search(text)
        if m:
            word = (m.group(1) or m.group(2) or "").lower()
            k = 2 if word in ("half", "halves") or m.group(1) else NUMBER_WORDS.get(word)
            if k is None and word.isdigit():
                k = int(word)
            if k:
                out.update(k=k, evidence=f"method text: {_sentence(text, m.start())!r}", source="method_divide")
    if out["k"] is None:
        m = SHAPE_ONE.search(text)
        if m and not DIVIDE_DOUGH.search(text):
            out.update(k=1, evidence=f"method text shapes the whole dough into one round: {_sentence(text, m.start())!r}", source="method_shape_one")
    r = RESERVE.search(text)
    if r:
        out.update(reserved=True, evidence=(out["evidence"] + "; " if out["evidence"] else "") + f"reserved: {_sentence(text, r.start())!r}")
    d = DIAMETER.search(text) or DIAMETER.search(yield_text or "")
    if d:
        out["diameter_in"] = Decimal(d.group(1))
    return out


def plain(d: Decimal) -> str:
    """A Decimal without exponent notation: 200, 0.5, 198.446661875."""
    return format(d.normalize(), "f")


def _sentence(text: str, pos: int) -> str:
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos)) + 1
    end = text.find(".", pos)
    return text[start: end + 1 if end != -1 else None].strip()[:160]


# -- inputs: a published scenario or one bound of an adapted pair --------------------------------------------


VEGETABLE_OIL, BEEF_DRIPPING = "vegetable oil", "beef dripping"     # the first keyword of the card's oil choices


class PortionInput:
    def __init__(self, *, kind: str, ident: str, bound: str, servings: Decimal, calculator_input: list[dict], result: RecipeResult,
                 adapt_mode: str = "off", menu_only_ids: set[str] | None = None, not_served_ids: set[str] | None = None, mass_stops: list[str] | None = None,
                 facts: NutrientFacts | None = None, dough: tuple[Decimal | None, str] = (None, "")) -> None:
        self.kind, self.ident, self.bound, self.servings = kind, ident, bound, servings
        self.calculator_input, self.result, self.adapt_mode = calculator_input, result, adapt_mode
        self.menu_only_ids = menu_only_ids or set()                 # D8 lines: on the restaurant plate, never part of the recipe's own mass or key weight
        self.not_served_ids = not_served_ids or set()               # 3D (12.3.2): cooking media are not part of the served mass
        self.mass_stops = list(mass_stops or [])                    # 3D (12.4.4): unweighed plain foods left out of the calculation that still have mass
        self.facts = facts                                          # 12.14.7: what the two nutrient facts need about these lines
        self.dough_grams, self.dough_basis = dough                  # 12.14.10: the recipe's dough weight and how it is known

    @property
    def per_plate_ids(self) -> set[str]:
        return {l["ingredient_id"] for l in self.calculator_input if l.get("quantity_basis") == "per_serving"} | self.menu_only_ids

    def key_ingredient_grams(self, head: str | tuple[str, ...] = "fish") -> tuple[Decimal | None, list[str]]:
        """The recipe's own weight of the key ingredient (recipe lines whose USDA description starts with one of `head`): the sum when every such
        line is weighed, else None. Menu-only lines (a bottarga proxied to a caviar record) are never key lines."""
        heads = (head,) if isinstance(head, str) else tuple(head)
        key = [i for i in self.result.ingredients if i.usda is not None and i.usda.description.split(",")[0].strip().lower().replace("\xa0", " ") in heads
               and i.ingredient_id not in self.per_plate_ids]
        names = [i.name for i in key]
        if not key or any(i.grams_in_recipe is None for i in key):
            return None, names
        return sum((i.grams_in_recipe for i in key), Decimal(0)), names

    def recipe_mass(self) -> tuple[Decimal | None, list[str]]:
        """Mass of the recipe's own lines (not per-plate additions, not menu-only lines, not cooking media); None when any line is unweighed, with
        the names. A plain food left out of the calculation by the composition rule still stops the mass unless it is weightless (12.4.4)."""
        own = [i for i in self.result.ingredients if i.ingredient_id not in self.per_plate_ids and i.ingredient_id not in self.not_served_ids]
        missing = [i.name for i in own if i.grams_in_recipe is None] + list(self.mass_stops)
        if missing:
            return None, missing
        return sum((i.grams_in_recipe for i in own), Decimal(0)), []


def _mass_rules(ingredients) -> tuple[set[str], list[str]]:
    """(ids that are not served, names that stop P2) from a scenario's lines (3D)."""
    from .inference import NEGLIGIBLE_COMPOSITION_REASON
    from .tags import ZERO_FAT_CATEGORIES
    not_served = {l.ingredient_id for l in ingredients if "cooking_medium" in l.flags}
    # 3K (12.20): a line in a zero-fat category (wine, beer, salt, water or stock) with NO quantity is a splash, not part of the plate's mass; with a quantity and no
    # weight it still stops P2, as before
    splash = {l.ingredient_id for l in ingredients if getattr(l, "tag_category", "") in ZERO_FAT_CATEGORIES and (l.parsed is None or l.parsed.quantity is None)}
    stops = [l.name for l in ingredients if l.excluded_from_calculation == NEGLIGIBLE_COMPOSITION_REASON and l.origin == "recipe" and not ZERO_WEIGHT_WORDS.search(l.name) and l.ingredient_id not in splash]
    return not_served, stops


def facts_of(s: Scenario, service: Any | None, low_fat: Decimal = LOW_FAT_G_PER_100G) -> NutrientFacts | None:
    return NutrientFacts(service, {l.ingredient_id for l in s.ingredients if l.tag_kind == "plain_food"}, low_fat) if service is not None else None


def published_input(s: Scenario, service: Any | None = None, low_fat: Decimal = LOW_FAT_G_PER_100G) -> PortionInput | None:
    if s.status != "calculated" or s.calculation is None or s.source.servings is None:
        return None
    lines = [{"name": l.name[:200] or "ingredient", "fdc_id": l.match.fdc_id if l.match else None,
              "grams": str(l.conversion.grams) if l.conversion.grams is not None else None, "preparation_state": l.preparation_state,
              "assumption": l.assumption, "ingredient_id": l.ingredient_id} for l in s.ingredients if l.excluded_from_calculation is None]
    menu_only = {l.ingredient_id for l in s.ingredients if l.origin == "menu_only"}
    not_served, stops = _mass_rules(s.ingredients)
    return PortionInput(kind="published", ident=s.scenario_id, bound="published", servings=s.source.servings, calculator_input=lines,
                        result=RecipeResult.model_validate(s.calculation), menu_only_ids=menu_only, not_served_ids=not_served, mass_stops=stops, facts=facts_of(s, service, low_fat), dough=dough_weight(s.ingredients))


def pair_inputs(pair: AdaptedPair, scenario: Scenario, service: Any | None = None, low_fat: Decimal = LOW_FAT_G_PER_100G) -> dict[str, PortionInput] | None:
    menu_only = {l.ingredient_id for l in scenario.ingredients if l.origin == "menu_only"}
    not_served, stops = _mass_rules(scenario.ingredients)
    filled = {a.ingredient_id for a in pair.assumptions if a.gap == "G6_cooking_medium"}       # a filled medium has left the "not served" set: W09 enters per plate
    weighed = {a.name for a in pair.assumptions if a.mass_only}                                # 12.14.12: the pair found these lines' weight
    stops = [n for n in stops if n not in weighed]
    out = {}
    for bound in ("low", "high"):
        a: AdaptedScenario = getattr(pair, bound)
        if a.calculation_status == "invalid" or not a.calculator_input:
            return None
        out[bound] = PortionInput(kind="adapted_pair", ident=pair.pair_id, bound=bound, servings=pair.servings, calculator_input=a.calculator_input,
                                  result=RecipeResult.model_validate(a.calculation), adapt_mode=pair.mode, menu_only_ids=menu_only, not_served_ids=not_served - filled, mass_stops=stops,
                                  facts=facts_of(scenario, service, low_fat), dough=dough_weight(scenario.ingredients))
    return out


# -- the fraction f per model ---------------------------------------------------------------------------------


def dough_weight(lines: list) -> tuple[Decimal | None, str]:
    """12.14.10: the recipe's dough weight and how it is known: a line that states the dough or the crust, or the recipe's own flour, water, yeast and salt when every one with a quantity is weighed."""
    recipe = [l for l in lines if l.origin == "recipe" and l.parsed is not None]
    stated = [l for l in recipe if DOUGH_LINE.search(l.name) and l.conversion.grams is not None]
    if stated:
        return sum((l.conversion.grams for l in stated), Decimal(0)), f"stated on the line: {stated[0].name[:50]}"
    parts = [l for l in recipe if DOUGH_PARTS.search(l.name) and l.parsed.quantity is not None and not DUSTING.search(l.line or "")]
    if not any(FLOUR.search(l.name) for l in parts) or not any(re.search(r"\bwater\b", l.name, re.I) for l in parts) or any(l.conversion.grams is None for l in parts):
        return None, ""
    return sum((l.conversion.grams for l in parts), Decimal(0)), f"sum of the recipe's dough lines: {', '.join(l.name[:20] for l in parts)}"[:120]


def fraction_p1(rule: PortionRule, units: dict[str, Any], inp: PortionInput) -> tuple[PortionFraction | None, PortionFraction | None, str | None, list[str]]:
    """12.14.10: a pizza recipe makes one pizza unless the page says otherwise. With the dough weight known, one plate is one restaurant pizza: the rule's dough ball over the recipe's dough, capped
    at the whole recipe. Without it, one plate is the recipe's pizza."""
    if units["reserved"]:
        return None, None, f"P1 not applicable: the recipe reserves part of the dough for another use, so the ingredient list does not describe one unit ({units['evidence']})", []
    k = units["k"] or 1
    source = units["evidence"][:200] if units["k"] else "the page states no count: one pizza"
    out = {}
    if inp.dough_grams:
        for bound, ball in (("low", rule.low), ("high", rule.high)):
            f = min(ball / inp.dough_grams, Decimal(1))
            out[bound] = PortionFraction(bound=bound, fraction=f, arithmetic=f"restaurant dough ball / recipe dough = {plain(ball)} g / {plain(inp.dough_grams)} g, capped at 1",
                                         inputs={"dough_ball_g": plain(ball), "recipe_dough_g": plain(inp.dough_grams), "dough_basis": inp.dough_basis, "k": str(k), "unit_count_source": source})
        return out["low"], out["high"], None, [f"recipe dough {plain(inp.dough_grams)} g ({inp.dough_basis}); toppings are assumed to scale with the dough"]
    for bound in ("low", "high"):
        out[bound] = PortionFraction(bound=bound, fraction=Decimal(1) / k, arithmetic=f"one of the recipe's {k} pizza(s)", inputs={"k": str(k), "unit_count_source": source})
    return out["low"], out["high"], None, ["the recipe's dough weight is not known: one plate is the recipe's pizza"]


def fraction_p3(rule: PortionRule, inp: PortionInput) -> tuple[PortionFraction | None, PortionFraction | None, str | None, list[str]]:
    heads = rule.key_record_heads or ("fish",)
    head = "/".join(heads) if len(heads) <= 3 else f"{heads[0]}/... ({len(heads)} kinds)"
    k_recipe, names = inp.key_ingredient_grams(heads)
    if k_recipe is None:
        why = f"no '{head}' line among the recipe's USDA records" if not names else f"the recipe's {head} weight is unknown ({', '.join(names)[:80]})"
        return None, None, f"P3 not applicable: {why}", []
    if k_recipe == 0:
        return None, None, "P3 not applicable: the recipe's fish weight is 0", []
    out = {}
    mass, _ = inp.recipe_mass()
    for bound, grams in (("low", rule.low), ("high", rule.high)):
        f = grams / k_recipe
        out[bound] = PortionFraction(bound=bound, fraction=f, arithmetic=f"K / K_recipe = {plain(grams)} g / {plain(k_recipe)} g",
                                     inputs={"K_plate_g": plain(grams), "K_recipe_g": plain(k_recipe), "key_lines": "; ".join(names)[:200],
                                             **({"M_recipe_g": plain(mass)} if mass is not None else {})})
    limits = [f"P3 scales every recipe line by the {head} ratio: sauces, dressings and sides are assumed to scale with it; menu-only additions are counted once per plate",
              f"raw weights (D6): no cooking yield applied; the rule's grams are raw {head} per plate"]
    return out["low"], out["high"], None, limits


def fraction_p2(rule: PortionRule, inp: PortionInput) -> tuple[PortionFraction | None, PortionFraction | None, str | None, list[str]]:
    mass, missing = inp.recipe_mass()
    if mass is None:
        return None, None, f"P2 not applicable: the recipe's served mass is incomplete ({len(missing)} unweighed: {', '.join(missing)[:100]}); a partial mass would overstate f", []
    if mass == 0:
        return None, None, "P2 not applicable: the recipe's mass is 0", []
    out = {}
    for bound, w in (("low", rule.low), ("high", rule.high)):
        f = w / mass
        out[bound] = PortionFraction(bound=bound, fraction=f, arithmetic=f"W / M_served = {plain(w)} g / {plain(mass)} g",
                                     inputs={"W_plate_g": plain(w), "M_served_g": plain(mass), "yield_option": "raw = served (no cooking loss for a salad)"})
    limits = ["served mass = the recipe's raw ingredient mass (yield option 2: no cooking loss); dressings and garnishes already in the recipe are inside that mass",
              "menu-only additions are counted once per plate on top of the plate weight", "experimental: plate-weight evidence is the weakest of the three models"]
    return out["low"], out["high"], None, limits


# -- the portioned scenario -------------------------------------------------------------------------------------


def _bound(inp: PortionInput, f: PortionFraction, calc: RecipeCalculator, label: str) -> PortionedBound:
    servings = (Decimal(1) / f.fraction)
    result = calc.calculate({"recipe_name": f"{inp.ident}::portion_{f.bound}", "servings": str(servings), "ingredients": inp.calculator_input})
    if not isinstance(result, RecipeResult):
        return PortionedBound(input_bound=label, fraction=f.fraction, servings_for_calculator=servings, calculation=result.model_dump(mode="json"), calculation_status="invalid")
    median_ids = {l["ingredient_id"]: l.get("assumption") or "" for l in inp.calculator_input if "assumed_size_median" in (l.get("assumption") or "")}
    class_ids = {l["ingredient_id"]: l.get("assumption") or "" for l in inp.calculator_input if "class_level_cup_weight" in (l.get("assumption") or "")}
    inferences, inferred = apply_inference_layer(result, median_ids, class_ids, inp.facts, f.bound)
    per_portion = {}
    for n in NUTRIENTS:
        ps = result.per_serving[n]
        with_inf = inferred[n].per_serving_total
        per_portion[n] = {"known_subtotal": ps.known_subtotal, "total": ps.total, "total_with_inferences": with_inf}
    return PortionedBound(input_bound=label, fraction=f.fraction, servings_for_calculator=servings, calculation=result.model_dump(mode="json"),
                          calculation_status=result.status, completeness_by_nutrient={n: result.totals[n].complete for n in NUTRIENTS},
                          inferences=inferences, inferred_totals=inferred, per_portion=per_portion)


def portion_scenario(inputs: PortionInput | dict[str, PortionInput], *, item: MenuItem, rules: PortionRules, calculator: RecipeCalculator,
                     yield_text: str = "", method_text: str = "", allow_unsourced: bool = True, dish_type: Any = ...) -> PortionedScenario:
    """One PortionedScenario for a published scenario (`inputs` is one PortionInput) or an adapted pair (`inputs` = {"low": ..., "high": ...}).
    The first rule row of the dish type whose model applies is used; the others are not averaged in."""
    single = isinstance(inputs, PortionInput)
    low_in, high_in = (inputs, inputs) if single else (inputs["low"], inputs["high"])
    dish_type = dish_type_for(item) if dish_type is ... else dish_type          # 3K bug fix: the family the dish-kind call chose, when the caller passes it
    base = dict(derived_from=low_in.ident, input_kind=low_in.kind, adapt_mode=low_in.adapt_mode, dish_type=dish_type or "unknown",
                recipe_basis={"servings_basis": "recipe", "servings": str(low_in.servings),
                              "per_serving": {b: {n: {"known_subtotal": str(i.result.per_serving[n].known_subtotal), "total": str(i.result.per_serving[n].total) if i.result.per_serving[n].total is not None else None}
                                                  for n in NUTRIENTS} for b, i in (("published", low_in),) if single} if single else
                                             {b: {n: {"known_subtotal": str(i.result.per_serving[n].known_subtotal), "total": str(i.result.per_serving[n].total) if i.result.per_serving[n].total is not None else None}
                                                  for n in NUTRIENTS} for b, i in (("low", low_in), ("high", high_in))}})
    if dish_type is None:
        return PortionedScenario(**base, model="P2", applicable=False, not_applicable_reason="no portion rule for this dish type")
    reasons = []
    menu_text = f"{item.name} {item.description}"
    candidates = rules.for_dish_type(dish_type, menu_text, allow_unsourced=allow_unsourced)
    if not candidates and rules.for_dish_type(dish_type, menu_text):
        return PortionedScenario(**base, model="P2", applicable=False, not_applicable_reason=f"the only rule rows for {dish_type} have no measured source and the reference check is off (12.2.2)")
    for rule in candidates:
        if rule.model == "P1":
            style = NON_UNIT_STYLE.search(f"{low_in.ident} {yield_text} {method_text[:600]}")
            if style:
                # Phase 3 (2026-11-04): a deep-dish sausage pizza passed the relevance gate for a Neapolitan salsiccia pizza and gave 47-111 g
                # saturated fat per plate; a pan, deep-dish or sheet pizza is not the thin round unit the rule's diameters describe
                fl, fh, why, limits = None, None, f"P1 not applicable: '{style.group(0)}' names a deep-dish, pan, sheet or stuffed pizza, not the thin round unit the rule describes", []
            else:
                units = unit_count_from_text(yield_text, method_text)
                fl, fh, why, limits = fraction_p1(rule, units, low_in)
        elif rule.model == "P3":
            fl, _, why, limits = fraction_p3(rule, low_in)
            if why is None and not single:
                _, fh, why2, _ = fraction_p3(rule, high_in)      # K_recipe can differ between the bounds only if a fish line was assumed; it never is
                why = why or why2
            else:
                fh = fraction_p3(rule, low_in)[1]
        else:
            fl, _, why, limits = fraction_p2(rule, low_in)
            if why is None:
                _, fh, why2, _ = fraction_p2(rule, high_in)
                why = why or why2
        if why is None and fh is not None and fh.fraction > 1:
            # 12.16.3: one plate is never more than one whole recipe. A dip read as a tomato salad gave 18.5 recipes a plate (513-1076 g); squid 6.9; soups 3.3.
            why = f"plate share {fh.fraction.quantize(Decimal('0.01'))} would exceed one whole recipe ({fh.arithmetic}); the recipe is not used for portioning (12.16.3)"
        if why is not None:
            reasons.append(f"{rule.id}: {why}")
            continue
        low = _bound(low_in, fl, calculator, "published" if single else "low")
        high = _bound(high_in, fh, calculator, "published" if single else "high")
        unc: dict[str, Any] = {"fraction_ratio_high_over_low": str((fh.fraction / fl.fraction).quantize(Decimal("0.001")))}
        for n in NUTRIENTS:
            lo, hi = low.per_portion[n]["total_with_inferences"], high.per_portion[n]["total_with_inferences"]
            unc[f"{n}_spread_per_portion"] = str(hi - lo) if lo is not None and hi is not None else None
            unc[f"{n}_known_subtotal_spread_per_portion"] = str(high.per_portion[n]["known_subtotal"] - low.per_portion[n]["known_subtotal"])
        limits = limits + ["the restaurant serving size is not verified: f is a modeled range from an unreviewed rule row" if not rule.approved_by else "rule row approved"]
        return PortionedScenario(**base, model=rule.model, portion_rule_id=rule.id, rule_basis=f"{rule.basis}; {rule.low}-{rule.high} {rule.unit}; sources: {rule.sources}"[:900],
                                 review_status=rule.review_status, confidence=rule.confidence, applicable=True, fraction_low=fl, fraction_high=fh, low=low, high=high,
                                 limitations=limits, uncertainty=unc)
    model = candidates[0].model if candidates else "P2"
    return PortionedScenario(**base, model=model, applicable=False, not_applicable_reason="; ".join(reasons) or f"no rule row for dish type {dish_type}")
