"""The plate-size table from measured restaurant data (SPEC_3_mvp.md 12.16.6-10). Reads MenuStat (`data/menustat_download/`) and the chain sheets (`data/chain_sheets/`), groups the items by
dish family, and writes:

    roli_agent/eval/card_evidence_<date>.md        per family: the items counted, the serving-weight percentiles, the saturated-fat and cholesterol ranges, the key-ingredient share, the sources
    roli_agent/recipes/portion_rules.csv           every row rebuilt or confirmed (PR01-PR15) plus the new families (PR16+); approved_by, approved_on and any approved range copied last from recipes/portion_approvals.csv (12.18)
    roli_agent/recipes/reference_figures.csv       the earlier chain and label figures kept, plus one aggregate low and high row per family and basis, with the chains behind them

    .venv/bin/python -m roli_agent.scripts.build_cards [--date 2026-11-06]

Method, one pass for every family (12.16.7): the plate weight is the 10th-90th percentile of the items' serving weights; the reference figures are the 10th-90th percentiles of saturated fat and
cholesterol per plate (and per 100 g where the data has them); a P3 family keeps its key-ingredient share by converting a measured component weight with USDA's own input shares, as the fish and
chips card does. Kids' meals and shareable items are left out of every family but the children's one. Nothing is adjusted by hand. Status by the number of businesses behind the
figure (Julius's decision of 2026-11-06, SPEC 12.17): none -> `unsourced` (the row is never used); one -> `single_source` (the row runs, its dishes are ranked under the reference check);
two or more -> `proposed_unreviewed`. A stated protein weight in a chain-sheet item name ("Grilled Atlantic Salmon 7.5 oz") feeds the P3 key share; a whole-plate weight feeds the plate
range and the reference figures only. Nothing here enters a total: the rows size a plate and check a result.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT

MENUSTAT = ROOT / "data" / "menustat_download" / "menustat_historical.csv"
CHAIN_SHEETS = ROOT / "data" / "chain_sheets"
RULES = ROOT / "roli_agent" / "recipes" / "portion_rules.csv"
FIGURES = ROOT / "roli_agent" / "recipes" / "reference_figures.csv"
APPROVALS = ROOT / "roli_agent" / "recipes" / "portion_approvals.csv"   # 12.18: Julius's decisions per row, applied last so a rebuild keeps them
PLATE_WEIGHTS = ROOT / "roli_agent" / "recipes" / "plate_weights.csv"   # 3K (12.20): one row per measured item or FNDDS portion behind each rule, for the band sampler
EVAL = ROOT / "roli_agent" / "eval"
OZ = Decimal("28.349523125")
MENUSTAT_CITE = ("MenuStat (NYC DOHMH), 2017-2018 items, DOHMH MenuStat (Historical) on NYC Open Data (qgc5-ecnb), downloaded 2026-11-06; "
                 "data/menustat_download/SOURCE_AND_LICENCE.md")
PE_CITE = "Pizza Express nutrition sheet, England, Wales & Scotland, November 2026 (data/chain_sheets/pizzaexpress_2026-11.csv), read 2026-11-06"


def sheet_cite(row: dict) -> str:
    """One citation per chain sheet: the business, the sheet's own description (the first clause of the row's notes), the CSV it was transcribed to and the read date."""
    if row["business"] == "Pizza Express":
        return PE_CITE
    head = (row.get("notes") or "").split(";")[0].strip()
    return f"{head} (data/chain_sheets/{row['_file']}), read {row['read_on']}"

# USDA's own input shares, read from the Survey (FNDDS) records on 2026-11-06 through the nutrition service (recipe weight before cooking, moisture change):
#   2706241 Fish, cod, baked or broiled: 96 g raw cod + 4 g fat + 0.4 g salt per 100.4 g of inputs, moisture -23 %  -> 96 / (100.4 x 0.77) = 1.2418 g raw fish per g cooked (salmon 2706286 is the same)
#   2706334 Calamari, fried: 65 g raw squid in 100.6 g of inputs, moisture -15 %                                        -> 65 / (100.6 x 0.85) = 0.7601 g raw per g fried (shrimp 2706364 the same)
#   2708674 Pizza, no cheese, thin crust: dough inputs flour 187.5 + water 118.5 + olive oil 13.5 + yeast 4.5 + sugar 18.75 + salt 3 = 345.75 g of 759 g, moisture -20 % -> 345.75 / 607.2 = 0.5694 of the pizza
#   beef, pork and chicken records (2705831, 2705867, 2705968, 2705855) are built from COOKED inputs, so they give no raw share; see the yield note on the meat row
USDA_SHARES = {
    "fish_baked_raw_per_cooked": Decimal("96") / (Decimal("100.4") * Decimal("0.77")),
    "fried_seafood_raw_per_fried": Decimal("65") / (Decimal("100.6") * Decimal("0.85")),
    "pizza_dough_share": Decimal("345.75") / (Decimal("759") * Decimal("0.80")),
}
# USDA Table of Cooking Yields for Meat and Poultry (ARS, December 2012; USDA_CookingYields_MeatPoultry.pdf, read 2026-11-06): cooked weight as % of raw
USDA_YIELDS = "top sirloin steak broiled or grilled 80 %, rib eye steak grilled 82-86 %, pork center loin chop broiled or grilled 82 %, pork top loin chop 79 %, chicken breast roasted 72 %, ground beef patty pan-broiled 69-77 %"

MEAL = r"\b(meals?|combos?|platters?|munchie|whatameal|value pack|family)\b"
SALAD_EXTRAS = r"\b(chicken|shrimp|prawns?|tuna|salmon|steak|beef|turkey|ham|bacon|eggs?|crab|lobster|pork|sandwich|wrap|panini|flatbread)\b"   # a salad with a protein or a sandwich named after a salad is another kind of dish
# family -> (MenuStat categories, name words that put an item in, name words that keep it out)
SELECT: dict[str, tuple[tuple[str, ...], str | None, str | None]] = {
    # a meal, combo or platter is the item plus sides or a drink, not the dish; its name says so and it is left out of the item families
    "burger": (("Burgers",), None, MEAL),
    "sandwich": (("Sandwiches",), None, r"\b(wraps?|tacos?|burritos?|quesadillas?)\b|" + MEAL),
    "wrap": (("Sandwiches", "Entrees"), r"\bwraps?\b", MEAL),
    "taco": (("Sandwiches", "Entrees"), r"\btacos?\b", MEAL),
    "burrito": (("Sandwiches", "Entrees"), r"\bburritos?\b", MEAL),
    "quesadilla": (("Sandwiches", "Entrees"), r"\bquesadillas?\b", MEAL),
    "breakfast_eggs": (("Entrees",), r"\b(eggs?|omelet\w*|scramble\w*|benedict|skillet|frittata)\b", r"\b(sandwich|burrito|wrap|taco)\b"),
    "breakfast_pancakes": (("Entrees", "Baked Goods", "Desserts"), r"\b(pancakes?|waffles?|french toast|crepes?)\b", None),
    "breakfast_cereal": (("Entrees", "Desserts", "Appetizers & Sides"), r"\b(granola|oatmeal|porridge|grits|cereal|muesli)\b", None),
    "toast_plate": (("Entrees", "Baked Goods", "Appetizers & Sides", "Sandwiches"), r"\btoast\b", r"french toast"),
    "soup": (("Soup",), None, None),
    "dip": (("Appetizers & Sides", "Toppings & Ingredients"), r"\b(dips?|hummus|guacamole|salsa|queso|spread|tapenade)\b", None),
    "side_salad": (("Salads", "Appetizers & Sides"), r"\b(side salad|house salad|garden salad|caesar salad|side caesar)\b", SALAD_EXTRAS),
    "leaf_salad_starter": (("Salads", "Appetizers & Sides"), r"\b(side salad|house salad|garden salad|caesar salad|side caesar)\b", SALAD_EXTRAS),
    "side_vegetable": (("Appetizers & Sides",), r"\b(broccoli|green beans|vegetables?|asparagus|corn|spinach|carrots?|coleslaw|slaw|beans|peas|greens|squash|onion rings?)\b", r"\b(fries|chips|rice|dip|soup)\b"),
    "side_rice": (("Appetizers & Sides", "Entrees"), r"\b(rice|pilaf)\b", r"\b(bowl|burrito|chicken|beef|shrimp|pork|steak|salmon)\b"),
    "side_bread": (("Appetizers & Sides", "Baked Goods"), r"\b(bread|breadsticks?|garlic knots?|rolls?|biscuits?|cornbread|naan|pita)\b", r"\b(sandwich|pudding|cinnamon|sweet)\b"),
    "fried_potato_side": (("Fried Potatoes",), None, None),
    "dessert": (("Desserts",), None, None),
    "vegetable_starter": (("Appetizers & Sides",), None, r"\b(fries|chips|dips?|hummus|guacamole|salsa|queso|bread|breadsticks?|rolls?|biscuits?|rice|soup|salad|calamari|shrimp|crab|scallops?|mussels?|clams?|oysters?|lobster)\b"),
    "fish_starter": (("Appetizers & Sides",), r"\b(calamari|shrimp|crab|scallops?|mussels?|clams?|oysters?|lobster|prawns?)\b", r"\b(dip|cocktail sauce)\b"),
    "fish_main": (("Entrees",), r"\b(salmon|tilapia|cod|trout|halibut|mahi|fish|swordfish|tuna|grouper|flounder|catfish|shrimp|scallops?|lobster|crab|mussels?|clams?)\b", r"\b(sandwich|taco|wrap|burrito|salad|soup|pasta|fettuccine|linguine)\b"),
    "meat_main": (("Entrees",), r"\b(steak|sirloin|ribeye|rib eye|filet|t-bone|t bone|strip|porterhouse|prime rib|chicken|pork|chops?|lamb|turkey|duck|brisket|ribs?)\b",
                  r"\b(sandwich|taco|wrap|burrito|salad|soup|pasta|fettuccine|linguine|pizza|quesadilla|nachos|bowl|tenders?|fingers?|wings?|nuggets?|strips?)\b"),
    "pasta_main": (("Entrees",), r"\b(pasta|spaghetti|fettuccine|penne|lasagna|ravioli|linguine|alfredo|macaroni|noodles?|rigatoni|tortellini|ziti|lo mein)\b", r"\b(soup|salad|side|cup)\b"),
    "tomato_salad_starter": (("Salads", "Appetizers & Sides"), r"\b(caprese|tomato salad|tomatoes? (and|&) mozzarella)\b", SALAD_EXTRAS),
    "crudo_starter": (("Entrees", "Appetizers & Sides", "Salads"), r"\b(crudo|ceviche|tartare|sashimi|poke|carpaccio|tataki)\b", None),
    "fish_and_chips": (("Entrees",), r"\bfish\b.{0,20}\b(chips|fries)\b", None),
    "pizza_neapolitan": (("Pizza",), r"\b(personal|individual|whole)\b", None),
    "snack_bowl": (("Appetizers & Sides",), r"\b(olives|almonds|nuts|peanuts|cashews)\b", r"\b(salad|dip|bar|crust)\b"),
}
OZ_IN_NAME = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*oz\b", re.I)
PROTEIN = {"fish_main": r"\b(salmon|tilapia|cod|trout|halibut|mahi|fish|swordfish|tuna|grouper|flounder|catfish|shrimp|scallops?|lobster|crab)\b",
           "meat_main": r"\b(steak|sirloin|ribeye|rib eye|filet|t-bone|t bone|strip|porterhouse|prime rib|chop|chops|pork|chicken)\b"}


def grams(r: dict) -> Decimal | None:
    try:
        v = Decimal(r["Serving_Size"])
    except Exception:  # noqa: BLE001
        return None
    return v if r["Serving_Size_Unit"] == "g" else v * OZ if r["Serving_Size_Unit"] == "oz" else None


def dec(text: str) -> Decimal | None:
    try:
        return Decimal(text)
    except Exception:  # noqa: BLE001
        return None


def pct(values: list[Decimal], q: Decimal) -> Decimal | None:
    if not values:
        return None
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(v) - 1)
    return (v[lo] + (v[hi] - v[lo]) * (pos - lo)).quantize(Decimal("0.1"))


def load_menustat() -> list[dict]:
    rows = list(csv.DictReader(MENUSTAT.open(encoding="utf-8")))
    latest: dict[str, dict] = {}
    for r in rows:                                   # one row per item: the latest year
        k = r["Menu_Item_ID"]
        if k not in latest or r["Year"] > latest[k]["Year"]:
            latest[k] = r
    return list(latest.values())


def load_chain_sheets() -> list[dict]:
    out = []
    for path in sorted(CHAIN_SHEETS.glob("*.csv")):
        for r in csv.DictReader(path.open(encoding="utf-8")):
            r["_file"] = path.name
            out.append(r)
    return out


class Family:
    def __init__(self, name: str) -> None:
        self.name = name
        self.weights: list[tuple[str, str, Decimal]] = []        # (business, item, serving g)
        self.sat_plate: list[tuple[str, Decimal]] = []
        self.chol_plate: list[tuple[str, Decimal]] = []
        self.sat_100: list[tuple[str, Decimal]] = []
        self.sources: list[str] = []
        self.notes: list[str] = []
        self.key_weights: list[tuple[str, str, Decimal]] = []    # (business, item, stated protein g)

    @property
    def chains(self) -> int:
        return len({b for b, _, _ in self.weights})

    def businesses(self, rows) -> int:
        return len({b for b, *_ in rows})


def collect(menustat: list[dict], sheets: list[dict]) -> dict[str, Family]:
    fams = {name: Family(name) for name in list(SELECT) + ["kids_dish", "snack_bowl_nuts"]}
    for r in menustat:
        if r["Food_Category"] == "Beverages":
            continue
        kids, share = r["Kids_Meal"] == "1", r["Shareable"] == "1"
        name, cat = r["Item_Name"], r["Food_Category"]
        g = grams(r)
        sat, chol, sat100 = dec(r["Saturated_Fat"]), dec(r["Cholesterol"]), dec(r["Saturated_Fat_100g"])
        targets = []
        if kids:
            if cat != "Toppings & Ingredients":
                targets.append("kids_dish")
        elif not share:
            for fam, (cats, inc, exc) in SELECT.items():
                if cat in cats and (inc is None or re.search(inc, name, re.I)) and not (exc and re.search(exc, name, re.I)):
                    targets.append(fam)
        for fam in targets:
            f = fams[fam]
            if g:
                f.weights.append((r["restaurant"], name, g))
                if fam in PROTEIN and not any(re.search(PROTEIN[o], name, re.I) for o in PROTEIN if o != fam):   # "Crab Cake Filet, 6 oz": the ounces are the steak's; an item naming two proteins states one weight, so it is left out of both
                    m = OZ_IN_NAME.search(name)
                    if m:
                        stated = Decimal(m.group(1)) * OZ
                        if abs(g - stated) <= stated * Decimal("0.1"):      # the serving IS the stated protein, nothing else on the plate
                            f.key_weights.append((r["restaurant"], name, stated))
            if sat is not None:
                f.sat_plate.append((r["restaurant"], sat))
            if chol is not None:
                f.chol_plate.append((r["restaurant"], chol))
            if sat100 is not None:
                f.sat_100.append((r["restaurant"], sat100))
    sheet_businesses = {r["business"] for r in sheets}
    for r in sheets:
        fam = r["family"]
        f = fams.setdefault(fam, Family(fam))
        g = dec(r["serving_g"])
        if g:
            f.weights.append((r["business"], r["item"], g))
        if fam in PROTEIN and not any(re.search(PROTEIN[o], r["item"], re.I) for o in PROTEIN if o != fam):
            m = OZ_IN_NAME.search(r["item"])
            if m:                                                        # "Grilled Atlantic Salmon 7.5 oz": the chain states the protein portion in the item name
                stated = Decimal(m.group(1)) * OZ
                if g is None or abs(g - stated) <= stated * Decimal("0.1"):    # no plate weight on the sheet, or the serving IS the stated protein
                    f.key_weights.append((r["business"], r["item"], stated))
        if dec(r["sat_fat_g_per_plate"]) is not None:
            f.sat_plate.append((r["business"], dec(r["sat_fat_g_per_plate"])))
        if dec(r["sat_fat_g_per_100g"]) is not None:
            f.sat_100.append((r["business"], dec(r["sat_fat_g_per_100g"])))
        if dec(r["cholesterol_mg_per_plate"]) is not None:
            f.chol_plate.append((r["business"], dec(r["cholesterol_mg_per_plate"])))
        cite = sheet_cite(r)
        if cite not in f.sources:
            f.sources.append(cite)
    for f in fams.values():
        if any(b not in sheet_businesses for b, *_ in f.weights + f.sat_plate + f.chol_plate + f.sat_100) and MENUSTAT_CITE not in f.sources:
            f.sources.insert(0, MENUSTAT_CITE)
    return fams


def status_for(n_businesses: int) -> str:
    """12.17: none -> unsourced, one -> single_source, two or more -> proposed_unreviewed."""
    return "unsourced" if n_businesses == 0 else "single_source" if n_businesses == 1 else "proposed_unreviewed"



# the rows: id, dish_type, model, what the low/high mean, and how the key share is derived
ROWS: list[dict] = [
    dict(id="PR01", dish_type="pizza_neapolitan", model="P1", unit="g dough per restaurant pizza", key="dough", family="pizza_neapolitan"),
    dict(id="PR02", dish_type="fish_main", model="P3", unit="g raw fish per plate", key="fish_stated", family="fish_main"),
    dict(id="PR03", dish_type="crudo_starter", model="P3", unit="g raw fish per plate", key="raw_fish_plate", family="crudo_starter"),
    dict(id="PR04", dish_type="leaf_salad_starter", model="P2", unit="g plated salad", key="plate", family="leaf_salad_starter"),
    dict(id="PR05", dish_type="tomato_salad_starter", model="P2", unit="g plated salad", key="plate", family="tomato_salad_starter"),
    dict(id="PR06", dish_type="tomato_salad_starter", model="P3", unit="g raw tomato per plate", key="none", family="tomato_salad_starter"),
    dict(id="PR07", dish_type="meat_main", model="P3", unit="g raw meat per plate", key="meat_stated", family="meat_main"),
    dict(id="PR08", dish_type="pasta_main", model="P3", unit="g dry pasta per plate", key="none", family="pasta_main"),
    dict(id="PR09", dish_type="pasta_main", model="P2", unit="g plated pasta", key="plate", family="pasta_main"),
    dict(id="PR10", dish_type="vegetable_starter", model="P2", unit="g plated starter", key="plate", family="vegetable_starter"),
    dict(id="PR11", dish_type="fish_starter", model="P3", unit="g raw fish per plate", key="fried_seafood_plate", family="fish_starter"),
    dict(id="PR12", dish_type="fried_potato_side", model="P2", unit="g cooked chips or fries per plate", key="plate", family="fried_potato_side"),
    dict(id="PR13", dish_type="snack_bowl", model="P2", unit="g plated snack", key="keep", family="snack_bowl"),
    dict(id="PR14", dish_type="snack_bowl", model="P2", unit="g plated snack", key="keep", family="snack_bowl_nuts"),
    dict(id="PR15", dish_type="fish_and_chips", model="P3", unit="g raw fish per plate", key="keep", family="fish_and_chips"),
    dict(id="PR16", dish_type="burger", model="P2", unit="g whole item, bun included", key="plate", family="burger"),
    dict(id="PR17", dish_type="sandwich", model="P2", unit="g whole item, bread included", key="plate", family="sandwich"),
    dict(id="PR18", dish_type="wrap", model="P2", unit="g whole item", key="plate", family="wrap"),
    dict(id="PR19", dish_type="taco", model="P2", unit="g per order", key="plate", family="taco"),
    dict(id="PR20", dish_type="burrito", model="P2", unit="g whole item", key="plate", family="burrito"),
    dict(id="PR21", dish_type="quesadilla", model="P2", unit="g whole item", key="plate", family="quesadilla"),
    dict(id="PR22", dish_type="breakfast_eggs", model="P2", unit="g plated breakfast", key="plate", family="breakfast_eggs"),
    dict(id="PR23", dish_type="breakfast_pancakes", model="P2", unit="g plated", key="plate", family="breakfast_pancakes"),
    dict(id="PR24", dish_type="breakfast_cereal", model="P2", unit="g per bowl", key="plate", family="breakfast_cereal"),
    dict(id="PR25", dish_type="toast_plate", model="P2", unit="g plated", key="plate", family="toast_plate"),
    dict(id="PR26", dish_type="soup", model="P2", unit="g per bowl", key="plate", family="soup"),
    dict(id="PR27", dish_type="dip", model="P2", unit="g per pot", key="plate", family="dip"),
    dict(id="PR28", dish_type="side_salad", model="P2", unit="g plated side", key="plate", family="side_salad"),
    dict(id="PR29", dish_type="side_vegetable", model="P2", unit="g plated side", key="plate", family="side_vegetable"),
    dict(id="PR30", dish_type="side_rice", model="P2", unit="g plated side", key="plate", family="side_rice"),
    dict(id="PR31", dish_type="side_bread", model="P2", unit="g per order", key="plate", family="side_bread"),
    dict(id="PR32", dish_type="dessert", model="P2", unit="g per dessert", key="plate", family="dessert"),
    dict(id="PR33", dish_type="kids_dish", model="P2", unit="g per children's dish", key="plate", family="kids_dish"),
]
KEEP = {"PR13", "PR14", "PR15"}          # chain-sheet and lab figures already cited on the row; confirmed, not rebuilt
FNDDS_COLUMNS = ("fndds_low", "fndds_high", "fndds_n", "fndds_basis", "fndds_records", "chain_low", "chain_high", "chain_n", "chain_businesses", "range_source", "sources_status")
DISAGREE = Decimal("1") / Decimal("3")   # 12.16.8a: FNDDS and the chain figures disagree when their midpoints differ by more than a third of the larger


def load_fndds(today: str) -> dict:
    """The qualifying FNDDS portions written by scripts/fndds_portions.py for the date, or the latest file; {} when none exists."""
    path = EVAL / f"fndds_portions_{today}.json"
    if not path.exists():
        files = sorted(EVAL.glob("fndds_portions_*.json"))
        if not files:
            return {}
        path = files[-1]
    return json.loads(path.read_text(encoding="utf-8"))


def fndds_figure(spec: dict, fam: dict | None) -> dict | None:
    """12.16.8a: the FNDDS key figure for a row, converted to the row's unit by the same USDA shares the chain figure uses. ``fits`` says whether the portions
    stand for the key the family needs (the protein alone for a P3 row, the whole plate for a P1 or P2 row); a row whose key no USDA share can give (PR06,
    PR08) is never fitted. None when no portion qualifies."""
    if not fam:
        return None
    ws = [Decimal(str(p["gram_weight"])) for r in fam["records"] for p in r["portions"] if p["qualifies"]]
    if not ws:
        return None
    basis, key = fam["basis"], spec["key"]
    protein_alone, whole = basis.startswith("protein alone"), basis.startswith("whole dish")
    if key in ("fish_stated",) and protein_alone:
        share, fits, how = USDA_SHARES["fish_baked_raw_per_cooked"], True, "cooked fillet x USDA 2706241 raw share"
    elif key == "meat_stated" and protein_alone:
        share, fits, how = Decimal(1) / Decimal("0.80"), True, "cooked cut / 0.80 (USDA Table of Cooking Yields, top sirloin broiled or grilled)"
    elif key == "raw_fish_plate" and protein_alone:
        share, fits, how = Decimal(1), True, "raw fish portion as USDA states it"
    elif key == "dough" and whole:
        share, fits, how = USDA_SHARES["pizza_dough_share"], True, "whole pizza x USDA 2708674 dough share"
    elif key == "fried_seafood_plate" and whole:
        share, fits, how = USDA_SHARES["fried_seafood_raw_per_fried"], True, "fried plate x USDA 2706334 raw share"
    elif key in ("plate", "keep") and whole:
        share, fits, how = Decimal(1), key == "plate", "whole-dish portion as USDA states it"
    else:
        share, fits, how = Decimal(1), False, f"the portions are '{basis}', not the key this row needs"
    conv = [w * share for w in ws]
    q = Decimal("1") if spec["model"] == "P3" or key == "dough" else Decimal("0.1")
    lo, hi = (pct(conv, Decimal("0.1")), pct(conv, Decimal("0.9"))) if len(conv) >= 3 else (min(conv), max(conv))
    ids = sorted({r["fdc_id"] for r in fam["records"] if any(p["qualifies"] for p in r["portions"])})
    return dict(low=lo.quantize(q), high=hi.quantize(q), n=len(ws), basis=basis, how=how, fits=fits, ids=ids,
                portions="; ".join(f"{r['fdc_id']} {p['label']} {Decimal(str(p['gram_weight'])):.0f} g" for r in fam["records"] for p in r["portions"] if p["qualifies"]))


def apply_fndds(spec: dict, row: dict, ev: dict, fam: dict | None, today: str) -> tuple[dict, dict]:
    """12.16.8a: record the FNDDS figure and the chain figure side by side; until Julius approves the row its range is the FNDDS figure when FNDDS gives the key
    the family needs, otherwise the chain figure; mark `sources_disagree` when the two midpoints differ by more than a third. A `keep` row only records."""
    chain_has = row.get("review_status") != "unsourced" and row.get("low") not in ("", None) and spec["key"] != "keep"
    row["chain_low"], row["chain_high"] = (row["low"], row["high"]) if chain_has else ("", "")
    row["chain_n"] = str(len(ev["key_items"])) if spec["key"] in ("fish_stated", "meat_stated") else str(ev["n_weighed"])
    row["chain_businesses"] = str(len({b for b, _, _ in ev["key_items"]})) if spec["key"] in ("fish_stated", "meat_stated") else str(ev["chains"])
    fig = fndds_figure(spec, fam)
    for c in ("fndds_low", "fndds_high", "fndds_n", "fndds_basis", "fndds_records"):
        row[c] = ""
    if fig is None:
        row["range_source"] = "chain" if chain_has else "record only"
        row["sources_status"] = "chain only" if chain_has else "none"
        ev["notes"].append("FNDDS: no whole-dish, fillet or restaurant portion on the records searched (eval/fndds_portions_%s.md)" % today)
        return row, ev
    row.update(fndds_low=str(fig["low"]), fndds_high=str(fig["high"]), fndds_n=str(fig["n"]), fndds_basis=f"{fig['basis']}; {fig['how']}" + ("" if fig["fits"] else " (does not give the key this row needs)"),
               fndds_records=", ".join(str(i) for i in fig["ids"]))
    ev["fndds"] = fig
    if spec["key"] == "keep":
        row["range_source"], row["sources_status"] = "row as cited", "fndds recorded"
        ev["notes"].append(f"FNDDS portions recorded beside the cited row: {fig['low']}-{fig['high']} {spec['unit']} from {fig['n']} portions ({fig['portions'][:160]})")
        return row, ev
    status = "proposed_unreviewed"
    if chain_has and fig["fits"]:
        a = (Decimal(row["chain_low"]) + Decimal(row["chain_high"])) / 2
        b = (fig["low"] + fig["high"]) / 2
        if abs(a - b) > max(a, b) * DISAGREE:
            status = "sources_disagree"
            row["sources_status"] = f"sources_disagree: FNDDS midpoint {b:.0f} against chain midpoint {a:.0f}"
            ev["notes"].append(f"sources_disagree (12.16.8a): FNDDS {fig['low']}-{fig['high']} against chain {row['chain_low']}-{row['chain_high']} {spec['unit']}; the row still runs")
        else:
            row["sources_status"] = f"agree: FNDDS midpoint {b:.0f}, chain midpoint {a:.0f}"
    elif fig["fits"]:
        row["sources_status"] = "fndds only" if not chain_has else "fndds and chain"
    else:
        row["sources_status"] = "chain only (FNDDS portions do not give the key)" if chain_has else "none (FNDDS portions do not give the key)"
    if fig["fits"]:
        row["range_source"] = "fndds"
        row["low"], row["high"] = str(fig["low"]), str(fig["high"])
        row["review_status"] = status
        row["basis"] = (f"FNDDS portions (12.16.8a): {fig['low']}-{fig['high']} {spec['unit']} = {fig['how']}; the 10th-90th percentile of {fig['n']} qualifying portions on USDA records {', '.join(str(i) for i in fig['ids'])} "
                        f"({fig['portions'][:220]}{'...' if len(fig['portions']) > 220 else ''}). Chain figure kept beside it: {row['chain_low'] or 'none'}-{row['chain_high'] or ''} from {row['chain_n']} items, {row['chain_businesses']} businesses. "
                        f"Chain basis: {row.get('basis', '')}")
        row["sources"] = f"USDA FNDDS portions, records {', '.join(str(i) for i in fig['ids'])}, read {today} through the nutrition service (eval/fndds_portions_{today}.md); " + (row.get("sources") or "")
        ev["notes"].append(f"range from FNDDS (12.16.8a): {fig['low']}-{fig['high']} {spec['unit']}; chain figure {row['chain_low'] or 'none'}-{row['chain_high']} kept beside it")
    else:
        row["range_source"] = "chain" if chain_has else "record only"
        ev["notes"].append(f"FNDDS recorded but not used for the range: {fig['low']}-{fig['high']} g, {fig['basis']} ({fig['how']})")
    return row, ev
def load_approvals(path: Path = APPROVALS) -> dict[str, dict]:
    """{row id: Julius's decision}. Only he writes this file (12.16.10, 12.18); the builder copies it onto the rows."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def apply_approvals(spec: dict, row: dict, ev: dict, a: dict | None) -> tuple[dict, dict]:
    """12.18: the approval columns and, where Julius chose another range, that range. The figure he set aside stays on the row as a note. An unsourced row keeps its
    status (the approval approves that it stays unsourced); every other approved row reads `approved`, which runs like any sourced status."""
    if not a or not a.get("approved_by"):
        return row, ev
    row["approved_by"], row["approved_on"] = a["approved_by"], a["approved_on"]
    if a.get("low") and a.get("high"):
        prior = f"{row['low']}-{row['high']} {spec['unit']} (range from {row.get('range_source') or 'the build'})"
        row["low"], row["high"], row["range_source"] = a["low"], a["high"], a["range_source"]
        row["basis"] = f"APPROVED RANGE ({a['spec']}, {a['approved_by']}, {a['approved_on']}): {a['low']}-{a['high']} {spec['unit']}; {a['decision']}. Range before approval: {prior}. " + row.get("basis", "")
        if row.get("review_status") == "sources_disagree":
            row["sources_status"] = f"approved: chain range; FNDDS figure kept as a note ({row.get('sources_status', '')})"
        ev["notes"].append(f"approved range ({a['spec']}): {a['low']}-{a['high']} {spec['unit']} replaces {prior}; {a['decision']}")
    else:
        ev["notes"].append(f"approved as it stands ({a['spec']}, {a['approved_on']}): {a['decision']}")
    if row.get("review_status") != "unsourced":
        row["review_status"] = "approved"
    prefix = f"{a['approved_by']} {a['approved_on']} ({a['spec']}): {a['decision']}"
    notes = row.get("notes") or ""
    if not notes.startswith(prefix):                              # a rebuild starts from the saved row, which already carries the note: never write it twice (3K fix)
        row["notes"] = prefix + (f"; {notes}" if notes else "")
    return row, ev


SHEET_BUSINESSES: set[str] = set()       # filled in main() from the chain sheets; the evidence file lists their items apart from MenuStat's


def build_row(spec: dict, f: Family, old: dict | None, today: str) -> tuple[dict, dict]:
    """(the CSV row, the evidence block). The evidence says what every figure rests on."""
    row = dict(old or {})
    row.update(id=spec["id"], dish_type=spec["dish_type"], model=spec["model"], unit=spec["unit"], approved_by="", approved_on="", read_on=today)
    weights = [g for _, _, g in f.weights]
    w10, w50, w90 = pct(weights, Decimal("0.1")), pct(weights, Decimal("0.5")), pct(weights, Decimal("0.9"))
    ev = dict(family=f.name, n_weighed=len(weights), chains=f.chains, w10=w10, w50=w50, w90=w90, items=f.weights, sat=f.sat_plate, chol=f.chol_plate, sat100=f.sat_100, key_items=f.key_weights,
              sources=list(f.sources), notes=[], row_id=spec["id"])
    sources = "; ".join(f.sources)
    if spec["key"] == "keep":
        ev["notes"].append("row confirmed: its chain-sheet or lab sources stay as cited on the row; MenuStat has no such items")
        row["review_status"] = "proposed_unreviewed"
        row["n_items"] = row.get("n_items") or ""
        return row, ev
    row["n_items"] = str(len(weights))
    row["plate_low_g"], row["plate_high_g"] = (str(w10), str(w90)) if w10 is not None else ("", "")
    status = status_for(f.chains)
    single = " SINGLE SOURCE (12.17): one business measured; the row runs under the reference check." if status == "single_source" else ""
    if not weights:
        row.update(review_status="unsourced", low=row.get("low", ""), high=row.get("high", ""), sources=f"no measured chain or label figure found for this family in MenuStat or the chain sheets on {today}",
                   basis=f"UNSOURCED (12.16.8): the earlier range {row.get('low', '')}-{row.get('high', '')} {row.get('unit', '')} is kept for the record only; dishes of this family are not ranked until a measured source is found")
        ev["notes"].append("unsourced: no chain with a serving weight")
        return row, ev
    if status == "single_source":
        ev["notes"].append("single_source: one business with a serving weight; the row runs and its dishes are ranked under the reference check (12.17)")
    if spec["key"] == "plate":
        row.update(low=str(w10), high=str(w90), basis=f"plate weight: the 10th-90th percentile of {len(weights)} chain items' serving weights ({f.chains} chains); raw = served.{single}",
                   sources=sources, review_status=status, key_record_head="" if spec["id"] != "PR09" else row.get("key_record_head", ""))
    elif spec["key"] == "raw_fish_plate":
        row.update(low=str(w10.quantize(Decimal("1"))), high=str(w90.quantize(Decimal("1"))),
                   basis=f"raw fish per plate = the chain's sashimi portion weight, {w10}-{w90} g (the 10th-90th percentile of {len(weights)} items, {f.chains} businesses): sashimi is raw fish served raw, dressing excluded where the sheet "
                         f"separates it, so the portion weight is the raw fish; a crudo, ceviche or tartare with other ingredients on the plate is read with the same fish weight.{single}",
                   review_status=status, sources=sources)
        ev["notes"].append("the key share is the sashimi weight itself: no USDA input share is needed for raw fish served raw")
    elif spec["key"] == "dough":
        share = USDA_SHARES["pizza_dough_share"]
        row.update(low=str((w10 * share).quantize(Decimal("1"))), high=str((w90 * share).quantize(Decimal("1"))),
                   basis=f"one plate is one restaurant pizza: its dough as a share of the recipe's dough, capped at the whole recipe (12.14.10). Dough = whole-pizza weight x USDA's dough share "
                         f"{share:.4f} (USDA 2708674 'Pizza, no cheese, thin crust': dough inputs 345.75 g of 759 g, moisture -20 %); whole pizzas {w10}-{w90} g, the 10th-90th percentile of {len(weights)} chain pizzas",
                   sources=sources + "; AVPN Disciplinare 2024: dough ball 200 g for a 22-24 cm pizza, 280 g for 28-35 cm (read 2026-11-03), which the derived range brackets", review_status=status)
        ev["notes"].append(f"dough share {share:.4f} from USDA 2708674; MenuStat's pizza items are slices (1/8 of a 14-inch chain pizza) and are not used for a whole pizza")
    elif spec["key"] in ("fish_stated", "meat_stated"):
        stated = [g for _, _, g in f.key_weights]
        n_stated_chains = len({b for b, _, _ in f.key_weights})
        key_status = status_for(n_stated_chains)
        if key_status == "unsourced":
            row.update(review_status="unsourced", basis=f"UNSOURCED (12.16.8): no chain states the protein weight alone (the earlier range {row.get('low', '')}-{row.get('high', '')} {row.get('unit', '')} is kept for the record only)", sources=sources)
            ev["notes"].append("key share unsourced: no chain states the protein weight alone")
            return row, ev
        single = " SINGLE SOURCE (12.17): one business states the protein weight; the row runs under the reference check." if key_status == "single_source" else ""
        if single:
            ev["notes"].append("single_source: one business states the protein weight alone; the row runs and its dishes are ranked under the reference check (12.17)")
        k10, k90 = pct(stated, Decimal("0.1")), pct(stated, Decimal("0.9"))
        if spec["key"] == "fish_stated":
            share = USDA_SHARES["fish_baked_raw_per_cooked"]
            row.update(low=str((k10 * share).quantize(Decimal("1"))), high=str((k90 * share).quantize(Decimal("1"))),
                       basis=f"raw fish per plate = the chain's stated fish portion x {share:.4f} g raw per g cooked (USDA 2706241 'Fish, cod, baked or broiled': 96 g raw in 100.4 g of inputs, moisture -23 %); stated portions {k10}-{k90} g "
                             f"(the 10th-90th percentile of {len(stated)} items whose serving weight is the stated fish alone, {n_stated_chains} chains); whole fish plates {w10}-{w90} g across {len(weights)} items.{single}",
                       review_status=key_status, sources=sources)
            ev["notes"].append("the stated weight is read as the cooked portion as served and converted to raw by USDA's baked-fish inputs")
        else:
            row.update(low=str(k10.quantize(Decimal("1"))), high=str(k90.quantize(Decimal("1"))),
                       basis=f"raw meat per plate = the chain's stated cut weight, {k10}-{k90} g (the 10th-90th percentile of {len(stated)} items whose serving weight is the stated cut alone, {len({b for b, _, _ in f.key_weights})} chains). "
                             f"A stated steak or chop weight is the raw cut by menu custom and no yield is applied; if a chain states cooked weights the raw figure is higher by USDA's yields ({USDA_YIELDS}). "
                             f"USDA's Survey meat records are built from cooked inputs and give no raw share. Whole meat plates {w10}-{w90} g across {len(weights)} items.{single}",
                       review_status=key_status, sources=sources + "; USDA Table of Cooking Yields for Meat and Poultry (ARS, December 2012), read 2026-11-06")
            ev["notes"].append("the stated cut weight is taken as the raw weight; the USDA yield table is cited so the cooked reading can be checked")
    elif spec["key"] == "fried_seafood_plate":
        share = USDA_SHARES["fried_seafood_raw_per_fried"]
        row.update(low=str((w10 * share).quantize(Decimal("1"))), high=str((w90 * share).quantize(Decimal("1"))),
                   basis=f"raw seafood per plate = the seafood starter's plate weight x {share:.4f} g raw per g fried (USDA 2706334 'Calamari, fried': 65 g raw squid in 100.6 g of inputs, moisture -15 %, as the fish and chips card); "
                         f"plates {w10}-{w90} g, the 10th-90th percentile of {len(weights)} chain items ({f.chains} chains); the plate weight includes any sauce served with it.{single}",
                   review_status=status, sources=sources)
    elif spec["key"] == "none":
        row.update(review_status="unsourced", sources=sources, basis=f"UNSOURCED (12.16.8): no USDA input share gives this key ingredient's share of a measured plate (the earlier range {row.get('low', '')}-{row.get('high', '')} {row.get('unit', '')} is kept for the record only)")
        ev["notes"].append("key share unsourced: USDA has no record with raw inputs for this family")
    return row, ev


def _fndds_share(spec: dict, fam: dict | None) -> Decimal | None:
    """The USDA share that turns an FNDDS portion into the row's unit, when the portions stand for the key the row needs (the same reading as `fndds_figure`); None otherwise."""
    if not fam:
        return None
    basis, key = fam["basis"], spec["key"]
    protein_alone, whole = basis.startswith("protein alone"), basis.startswith("whole dish")
    if key == "fish_stated" and protein_alone:
        return USDA_SHARES["fish_baked_raw_per_cooked"]
    if key == "meat_stated" and protein_alone:
        return Decimal(1) / Decimal("0.80")
    if key == "raw_fish_plate" and protein_alone:
        return Decimal(1)
    if key == "dough" and whole:
        return USDA_SHARES["pizza_dough_share"]
    if key == "fried_seafood_plate" and whole:
        return USDA_SHARES["fried_seafood_raw_per_fried"]
    if key in ("plate", "keep") and whole:
        return Decimal(1)
    return None


def plate_weight_rows(spec: dict, f: Family | None, fam_fndds: dict | None, today: str) -> list[dict]:
    """3K (12.20): the measured samples behind one row, in the row's unit: chain items (as the plate, or converted by the USDA share the row uses), the chain's stated
    protein weights for P3 rows, the AVPN dough balls for PR01, and every qualifying FNDDS portion converted the same way. Nothing is adjusted; each row names its item."""
    out: list[dict] = []
    row = lambda source, business, item, g, kind: out.append({"rule_id": spec["id"], "source": source, "business": business, "item": item[:80], "grams": str(Decimal(g).quantize(Decimal("0.1"))), "kind": kind, "read_on": today})
    key = spec["key"]
    if f is not None and key != "keep":
        if key == "plate":
            for b, i, g in f.weights:
                row("chain", b, i, g, "chain_plate")
        elif key == "raw_fish_plate":
            for b, i, g in f.weights:
                row("chain", b, i, g, "sashimi_portion")
        elif key == "dough":
            for b, i, g in f.weights:
                row("chain", b, i, g * USDA_SHARES["pizza_dough_share"], "derived_dough")
            row("standard", "AVPN", "Disciplinare 2024: dough ball for a 22-24 cm pizza", 200, "standard")
            row("standard", "AVPN", "Disciplinare 2024: dough ball for a 28-35 cm pizza", 280, "standard")
        elif key == "fish_stated":
            for b, i, g in f.key_weights:
                row("chain", b, i, g * USDA_SHARES["fish_baked_raw_per_cooked"], "stated_protein_raw")
        elif key == "meat_stated":
            for b, i, g in f.key_weights:
                row("chain", b, i, g, "stated_cut")
        elif key == "fried_seafood_plate":
            for b, i, g in f.weights:
                row("chain", b, i, g * USDA_SHARES["fried_seafood_raw_per_fried"], "derived_raw_seafood")
    share = _fndds_share(spec, fam_fndds)
    if share is not None:
        for rec in fam_fndds["records"]:
            for p in rec["portions"]:
                if p["qualifies"]:
                    row("fndds", f"USDA FNDDS {rec['fdc_id']}", f"{rec['description']}: {p['label']}", Decimal(str(p["gram_weight"])) * share, "fndds_portion")
    return out


def write_plate_weights(fams: dict[str, Family], rows: list[dict], fndds: dict, today: str) -> int:
    out: list[dict] = []
    for spec in rows:
        out += plate_weight_rows(spec, fams.get(spec["family"]), fndds.get(spec["family"]), today)
    with PLATE_WEIGHTS.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["rule_id", "source", "business", "item", "grams", "kind", "read_on"], lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    return len(out)


def write_figures(fams: dict[str, Family], rows: list[dict], today: str) -> int:
    old = list(csv.DictReader(FIGURES.open(encoding="utf-8")))
    fields = list(old[0].keys()) + (["n_businesses"] if "n_businesses" not in old[0] else [])
    kept = [r for r in old if not r["id"].startswith("MS")]
    new = []
    for spec in rows:
        f = fams.get(spec["family"])
        if f is None or spec["id"] in ("PR06", "PR08", "PR09", "PR14", "PR28"):   # one card per family carries the figures (12.1): the first row of the type
            continue
        for basis, values in (("per_plate", f.sat_plate), ("per_100g", f.sat_100)):
            chains = {b for b, _ in values}
            if len(values) < 10 or len(chains) < 2:
                continue
            lo, hi = pct([v for _, v in values], Decimal("0.1")), pct([v for _, v in values], Decimal("0.9"))
            group = f"MenuStat and chain sheets ({len(chains)} businesses)"
            for tag, val in (("p10", lo), ("p90", hi)):
                new.append({"id": f"MS-{spec['id']}-{basis}-{tag}", "card": spec["id"], "group": group, "business": group, "product": f"{f.name}: {tag} of {len(values)} items' saturated fat {basis}",
                            "basis": basis, "sat_fat_g": str(val), "total_fat_g": "", "stated_choice": "", "source_kind": "chain_sheet_aggregate", "provenance": "built by scripts/build_cards.py",
                            "read_on": today, "url": "data/menustat_download/SOURCE_AND_LICENCE.md; data/chain_sheets/", "notes": f"10th-90th percentile; the two rows stand for {len(chains)} businesses", "n_businesses": str(len(chains))})
    with FIGURES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in kept + new:
            w.writerow({k: r.get(k, "") for k in fields})
    return len(new)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()))
    args = ap.parse_args()
    menustat, sheets = load_menustat(), load_chain_sheets()
    SHEET_BUSINESSES.update(r["business"] for r in sheets)
    fams = collect(menustat, sheets)
    old = {r["id"]: r for r in csv.DictReader(RULES.open(encoding="utf-8"))}
    fields = list(next(iter(old.values())).keys())
    for col in ("plate_low_g", "plate_high_g", "n_items", "read_on", *FNDDS_COLUMNS):
        if col not in fields:
            fields.append(col)
    fndds = load_fndds(args.date)
    approvals = load_approvals()
    out_rows, evidence = [], []
    for spec in ROWS:
        row, ev = build_row(spec, fams[spec["family"]], old.get(spec["id"]), args.date)
        row, ev = apply_fndds(spec, row, ev, fndds.get(spec["family"]), args.date)
        row, ev = apply_approvals(spec, row, ev, approvals.get(spec["id"]))
        out_rows.append({k: row.get(k, "") for k in fields})
        evidence.append(ev)
    with RULES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    n_fig = write_figures(fams, ROWS, args.date)
    n_pw = write_plate_weights(fams, ROWS, fndds, args.date)
    lines = [f"# Plate-size table evidence, {args.date}", "", f"MenuStat: {len(menustat)} distinct items, {len({r['restaurant'] for r in menustat})} chains, years {sorted({r['Year'] for r in menustat})}; "
             f"kids' meals and shareable items left out of every family but the children's. Chain sheets: {len(sheets)} rows from {len(SHEET_BUSINESSES)} businesses ({', '.join(sorted(SHEET_BUSINESSES))}). Serving weights in g or oz only. Percentiles are the 10th, 50th and 90th. "
             f"Status: no business -> unsourced; one -> single_source (runs under the reference check); two or more -> proposed_unreviewed (12.17).", "",
             f"USDA input shares: baked fish {USDA_SHARES['fish_baked_raw_per_cooked']:.4f} g raw per g cooked; fried seafood {USDA_SHARES['fried_seafood_raw_per_fried']:.4f} g raw per g fried; pizza dough {USDA_SHARES['pizza_dough_share']:.4f} of the pizza. USDA yields: {USDA_YIELDS}.", "",
             f"FNDDS portions (12.16.8a): {len(fndds)} families looked up in eval/fndds_portions_{args.date}.md; a row's range is the FNDDS figure when FNDDS gives the key the family needs, otherwise the chain figure; both stand on the row.", "",
             f"Approvals (12.18): {sum(1 for r in out_rows if r.get('approved_by'))} of {len(out_rows)} rows carry Julius's approval from recipes/portion_approvals.csv; where he chose another range the row's basis starts with APPROVED RANGE and the build's figure stays as a note.", "",
             "| row | family | model | low-high (unit) | range from | FNDDS key figure (n) | chain key figure (n, businesses) | plate p10 / p50 / p90 g | n items | chains | sat fat per plate p10-p90 g (n) | cholesterol per plate p10-p90 mg (n) | sat fat per 100 g p10-p90 (n) | status |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row, ev in zip(out_rows, evidence):
        sat = f"{pct([v for _, v in ev['sat']], Decimal('0.1'))}-{pct([v for _, v in ev['sat']], Decimal('0.9'))} ({len(ev['sat'])})" if ev["sat"] else "none"
        chol = f"{pct([v for _, v in ev['chol']], Decimal('0.1'))}-{pct([v for _, v in ev['chol']], Decimal('0.9'))} ({len(ev['chol'])})" if ev["chol"] else "none"
        s100 = f"{pct([v for _, v in ev['sat100']], Decimal('0.1'))}-{pct([v for _, v in ev['sat100']], Decimal('0.9'))} ({len(ev['sat100'])})" if ev["sat100"] else "none"
        fn = f"{row['fndds_low']}-{row['fndds_high']} ({row['fndds_n']})" if row["fndds_low"] else "none"
        ch = f"{row['chain_low']}-{row['chain_high']} ({row['chain_n']}, {row['chain_businesses']})" if row["chain_low"] else "none"
        lines.append(f"| {row['id']} | {row['dish_type']} | {row['model']} | {row['low']}-{row['high']} {row['unit']} | {row['range_source']} | {fn} | {ch} | {ev['w10']} / {ev['w50']} / {ev['w90']} | {ev['n_weighed']} | {ev['chains']} | {sat} | {chol} | {s100} | {row['review_status']} |")
    lines += ["", f"Reference figures written: {n_fig} aggregate rows (a low and a high per family and basis, each standing for the chains behind it); the earlier chain and label rows are kept.",
              f"Plate-weight samples written (3K, 12.20): {n_pw} rows in recipes/plate_weights.csv, one per measured chain item, stated protein weight, AVPN dough ball or qualifying FNDDS portion, in each row's unit; the band sampler draws from them inside the approved range.", ""]
    for row, ev in zip(out_rows, evidence):
        lines += [f"## {row['id']} {row['dish_type']} ({row['model']})", "", f"- basis: {row['basis']}", f"- sources: {row['sources']}"]
        lines += [f"- note: {n}" for n in ev["notes"]]
        if ev["key_items"]:
            lines.append(f"- stated protein items ({len(ev['key_items'])}): " + "; ".join(f"{b}: {i[:40]} {g:.0f} g" for b, i, g in ev["key_items"][:12]) + (" ..." if len(ev["key_items"]) > 12 else ""))
        sheet_items = [(b, i, g) for b, i, g in ev["items"] if b in SHEET_BUSINESSES]
        if sheet_items:
            lines.append(f"- chain-sheet items with a weight ({len(sheet_items)}): " + "; ".join(f"{b}: {i[:40]} {g:.0f} g" for b, i, g in sheet_items[:16]) + (" ..." if len(sheet_items) > 16 else ""))
        if ev["items"]:
            by = Counter(b for b, _, _ in ev["items"])
            lines.append(f"- items counted by business: " + ", ".join(f"{b} {n}" for b, n in by.most_common(12)) + (f", and {len(by) - 12} more" if len(by) > 12 else ""))
            sample = sorted(ev["items"], key=lambda t: t[2])
            picks = [sample[0], sample[len(sample) // 2], sample[-1]] if len(sample) >= 3 else sample
            lines.append("- lightest / middle / heaviest: " + "; ".join(f"{b}: {i[:45]} {g:.0f} g" for b, i, g in picks))
        lines.append("")
    out = EVAL / f"card_evidence_{args.date}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:len(ROWS) + 10]))
    print("written:", out, RULES, FIGURES, PLATE_WEIGHTS, f"({n_pw} plate-weight rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
