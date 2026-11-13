"""USDA Survey (FNDDS) portions as a plate-size source (SPEC_3_mvp.md 12.16.8a, Julius 2026-11-06). For every dish family in the plate-size table this reads the
portions USDA attaches to a fitting FNDDS food record, through the nutrition service's existing portions call, and keeps only gram weights of a whole-dish,
fillet or restaurant portion: never a spoon, cup, slice or "quantity not specified". It writes

    roli_agent/eval/fndds_portions_<date>.md     per family: the records searched, every portion on each record, which portions qualify and why not the others
    roli_agent/eval/fndds_portions_<date>.json   the qualifying portions, read by scripts/build_cards.py into the rows' FNDDS columns

    .venv/bin/python -m roli_agent.scripts.fndds_portions [--date 2026-11-06] [--explore]     (--explore: print the search candidates only, read no portions)

The USDA requests count against the hourly allowance; the remaining count is printed first and the script stops when it is at or under the reserve (200).
A model never writes a figure here: every gram weight is USDA's own, read from one record and shown with its id.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from roli_nutrition import AnswerStore, NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

from roli_agent.config import ROOT

SURVEY = "Survey (FNDDS)"
EVAL = ROOT / "roli_agent" / "eval"
STORE = ROOT / ".cache" / "usda_store"
RESERVE = 200

# a portion qualifies when its words name a whole dish, a fillet or steak, or a restaurant order; a measure of volume, a slice, a piece or USDA's unspecified default never does.
# Size words alone ("1 small", "1 thick") count as a whole item only for families whose key weight is one item or one cut (sizes=True): a small breadstick is not an order of bread
ALLOW = re.compile(r"\b(fillet|steak|whole|restaurant|order|bowl|plate|dinner|meal|hamburger|cheeseburger|sandwich|burger|wrap|taco|burrito|quesadilla|pizza|salad)\b", re.I)
SIZES = re.compile(r"\b(small|regular|medium|large|thick|thin|breast)\b", re.I)
DENY = re.compile(r"\b(cup|cups|tablespoon|teaspoon|tbsp|tsp|slice|slices|oz|ounce|inch|cubic|not specified|item|items|ring|rings|strip|strips|nugget|nuggets|patty|patties|egg|eggs|pancake|pancakes|waffle|cookie|cracker|olive|olives|nut|nuts|shrimp|prawn|piece|pieces|each|fl|quarter|extra-large)\b", re.I)

# family -> the FNDDS search queries, the regex that picks the records meant (on the description), what the portion stands for, and extra portion words allowed for that family
FAMILIES: dict[str, dict] = {
    "fish_main":            dict(queries=["fish cod baked or broiled", "fish salmon baked or broiled"], ids=[2706241, 2706286, 2706295], basis="protein alone (cooked fillet)", cooked_to_raw="fish", sizes=True),
    "crudo_starter":        dict(queries=["sashimi", "fish tuna raw", "fish salmon raw"], ids=[2706284, 2706308], basis="protein alone (raw fish)"),
    "tomato_salad_starter": dict(queries=["tomato and mozzarella salad", "caprese salad", "tomato salad"], ids=[2705818], basis="whole dish"),
    "pasta_main":           dict(queries=["spaghetti with tomato sauce", "pasta with meat sauce", "lasagna with meat"], ids=[2708837, 2708861, 2708752], basis="whole dish (plated pasta)"),
    "fish_starter":         dict(queries=["calamari fried", "shrimp breaded fried", "crab cake"], ids=[2706334, 2706364, 2706549], basis="whole dish (fried seafood plate)", cooked_to_raw="fried_seafood"),
    "pizza_neapolitan":     dict(queries=["pizza cheese regular crust", "pizza cheese thin crust", "pizza cheese", "pizza pepperoni"], ids=[2708674, 2708622, 2708623], pick=r"^Pizza, (cheese|pepperoni), (thin|thick|regular) crust$", basis="whole dish (whole pizza)", dough_share=True, sizes=True),
    "leaf_salad_starter":   dict(queries=["caesar salad", "lettuce salad with assorted vegetables"], ids=[2709591, 2709822], basis="whole dish"),
    "meat_main":            dict(queries=["steak beef broiled", "chicken breast grilled", "pork chop broiled"], ids=[2705824, 2705829, 2705841, 2705968, 2705866], basis="protein alone (cooked cut)", cooked_to_raw="meat", sizes=True),
    "vegetable_starter":    dict(queries=["vegetables grilled", "bruschetta"], ids=[2707652], basis="whole dish"),
    "fried_potato_side":    dict(queries=["potato french fries restaurant"], ids=[2709462], basis="whole dish (an order of fries)"),
    "snack_bowl":           dict(queries=["olives", "almonds roasted"], ids=[2710088, 2707487], basis="whole dish"),
    "fish_and_chips":       dict(queries=["fish and chips", "fish battered fried"], ids=[2706244, 2706258], basis="protein alone (fried fillet)", sizes=True),
    "burger":               dict(queries=["hamburger on bun", "cheeseburger on bun"], ids=[2706927, 2706932, 2706934, 2706895, 2706901], basis="whole dish (whole item)", sizes=True),
    "sandwich":             dict(queries=["chicken sandwich", "turkey sandwich", "ham and cheese sandwich"], ids=[2706988, 2706985, 2706969, 2707000], basis="whole dish (whole item)", sizes=True),
    "wrap":                 dict(queries=["chicken wrap", "wrap sandwich"], ids=[2706881, 2707017, 2706987], basis="whole dish (whole item)", sizes=True),
    "taco":                 dict(queries=["taco with chicken", "taco with beef"], ids=[2708514, 2708526, 2708522, 2708529], basis="whole dish (one taco)", sizes=True),
    "burrito":              dict(queries=["burrito with beef and beans", "burrito chicken"], ids=[2708534, 2708537, 2708543, 2708546], basis="whole dish (whole item)", sizes=True),
    "quesadilla":           dict(queries=["quesadilla with chicken", "quesadilla cheese"], ids=[2708590, 2708593, 2708591], basis="whole dish (whole item)", sizes=True),
    "breakfast_eggs":       dict(queries=["egg omelet with cheese", "eggs benedict", "scrambled eggs"], ids=[2707212, 2707205, 2707180], basis="whole dish"),
    "breakfast_pancakes":   dict(queries=["pancakes plain", "waffle plain", "french toast"], ids=[2708299, 2708320, 2708333], basis="whole dish"),
    "breakfast_cereal":     dict(queries=["oatmeal cooked", "granola"], ids=[2708380, 2708461], basis="whole dish (a bowl)"),
    "toast_plate":          dict(queries=["bread toasted", "toast with butter"], ids=[2707599, 2707776], basis="whole dish"),
    "soup":                 dict(queries=["soup chicken noodle", "soup tomato", "soup vegetable"], ids=[2709149, 2709757, 2710113], basis="whole dish (a bowl)"),
    "dip":                  dict(queries=["hummus", "guacamole", "dip cheese"], ids=[2707402, 2709307, 2705618], basis="whole dish (a pot)"),
    "side_salad":           dict(queries=["lettuce salad with assorted vegetables", "garden salad"], ids=[2709822, 2709823], basis="whole dish"),
    "side_vegetable":       dict(queries=["broccoli cooked", "green beans cooked", "vegetables mixed cooked"], ids=[2709644, 2709851, 2710012], basis="whole dish (a side)"),
    "side_rice":            dict(queries=["rice white cooked", "rice pilaf"], ids=[2708403, 2709077], basis="whole dish (a side)"),
    "side_bread":           dict(queries=["garlic bread", "bread roll", "breadsticks"], ids=[2707627, 2707693, 2707662], basis="whole dish (an order)", deny=r"\b(roll|stick|knot|baguette)\b"),
    "dessert":              dict(queries=["cake chocolate with icing", "cheesecake", "brownie", "ice cream"], ids=[2707866, 2707861, 2707904, 2705630], basis="whole dish (one dessert)", allow=r"\b(piece|brownie|serving|individual|sundae|scoop)\b"),
    "kids_dish":            dict(queries=["chicken nuggets", "macaroni and cheese"], ids=[2706094, 2708811], basis="whole dish"),
}
COOKED_TO_RAW = {"fish": Decimal("96") / (Decimal("100.4") * Decimal("0.77")),          # USDA 2706241 inputs, as build_cards
                 "fried_seafood": Decimal("65") / (Decimal("100.6") * Decimal("0.85")),  # USDA 2706334 inputs
                 "meat": Decimal("1") / Decimal("0.80")}                                   # USDA Table of Cooking Yields: top sirloin broiled or grilled 80 %
DOUGH_SHARE = Decimal("345.75") / (Decimal("759") * Decimal("0.80"))                      # USDA 2708674, as build_cards


def qualifies(label: str, extra: str | None, sizes: bool = False, deny: str | None = None) -> tuple[bool, str]:
    if deny and re.search(deny, label, re.I):
        return False, "a single roll, stick or knot is not an order"
    if DENY.search(label) and not (extra and re.search(extra, label, re.I)):
        return False, "a measure, slice, piece, sharing size or unspecified default"
    if ALLOW.search(label) or (extra and re.search(extra, label, re.I)) or (sizes and SIZES.search(label)):
        return True, "whole dish, fillet, steak or restaurant order"
    return False, "not a whole-dish, fillet or restaurant portion"


def make_service() -> tuple[NutritionService, UsdaClient]:
    settings = Settings.from_env()
    client = UsdaClient(settings.api_key)
    return NutritionService(settings, client=client, store=AnswerStore(STORE, stale_days=settings.stale_days)), client


def remaining(client: UsdaClient) -> int | None:
    a = client.allowance
    return getattr(a, "remaining", None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()))
    ap.add_argument("--explore", action="store_true")
    args = ap.parse_args()
    service, client = make_service()
    report, found = [], {}
    for fam, spec in FAMILIES.items():
        cands = []
        for q in spec["queries"]:
            left = remaining(client)
            if left is not None and left <= RESERVE:
                print(f"stopping: USDA remaining {left} is at the reserve {RESERVE}"); break
            res = service.search_foods(q, 10, data_types=[SURVEY])
            if getattr(res, "status", "") != "complete":
                report.append((fam, q, f"search failed: {getattr(res, 'code', '')} {getattr(res, 'message', '')}", [])); continue
            for c in res.candidates:
                if c.fdc_id not in {x.fdc_id for x in cands}:
                    cands.append(c)
        picked = [c for c in cands if c.fdc_id in spec.get("ids", [])] + [c for c in cands if "pick" in spec and re.search(spec["pick"], c.description, re.I) and c.fdc_id not in spec.get("ids", [])]
        picked = picked[:6]
        if args.explore:
            print(f"\n## {fam}: {len(cands)} candidates, {len(picked)} picked")
            for c in cands:
                print(f"   {'*' if c in picked else ' '} {c.fdc_id} {c.description}")
            continue
        rows = []
        for c in picked:
            pr = service.get_portions(c.fdc_id)
            if getattr(pr, "status", "") != "complete":
                rows.append(dict(fdc_id=c.fdc_id, description=c.description, portions=[], error=f"{getattr(pr, 'code', '')} {getattr(pr, 'message', '')}")); continue
            plist = []
            for p in pr.portions:
                ok, why = qualifies(p.label, spec.get("allow"), bool(spec.get("sizes")), spec.get("deny"))
                plist.append(dict(label=p.label, gram_weight=p.gram_weight, qualifies=ok, why=why))
            rows.append(dict(fdc_id=c.fdc_id, description=c.description, portions=plist))
        found[fam] = dict(basis=spec["basis"], cooked_to_raw=spec.get("cooked_to_raw"), dough_share=bool(spec.get("dough_share")), records=rows,
                          searched=[c.description for c in cands], queries=spec["queries"])
    if args.explore:
        print("\nUSDA remaining:", remaining(client)); return 0
    # the markdown report
    lines = [f"# FNDDS portions as a plate-size source, {args.date} (SPEC_3_mvp.md 12.16.8a)", "",
             "Read through the nutrition service's portions call from USDA Survey (FNDDS) records found by a Survey-only search; the disk store answers repeats. A portion qualifies when its words name a whole dish, a fillet or steak, or a restaurant order; a cup, spoon, slice, piece or USDA's 'Quantity not specified' default never does. Gram weights are USDA's own.",
             "", f"USDA remaining after this pass: {remaining(client) if remaining(client) is not None else 'no request was needed (every answer came from the disk store)'} of the hourly allowance (reserve {RESERVE}).", ""]
    for fam, d in found.items():
        q = [(r["description"], p) for r in d["records"] for p in r["portions"] if p["qualifies"]]
        lines += [f"## {fam}: {d['basis']}", "", f"- searched: {'; '.join(d['queries'])}; candidates: {', '.join(d['searched'][:12])}{' ...' if len(d['searched']) > 12 else ''}"]
        if not d["records"]:
            lines.append("- no FNDDS record fits this family: nothing qualifies"); lines.append(""); continue
        for r in d["records"]:
            if r.get("error"):
                lines.append(f"- {r['fdc_id']} {r['description']}: {r['error']}"); continue
            lines.append(f"- **{r['fdc_id']} {r['description']}**: " + "; ".join(f"{p['label']} {p['gram_weight']:.0f} g{' (qualifies)' if p['qualifies'] else ''}" for p in r["portions"]))
        if q:
            ws = sorted(p["gram_weight"] for _, p in q)
            lines.append(f"- qualifying: {len(q)} portions, {ws[0]:.0f}-{ws[-1]:.0f} g ({d['basis']})" + (f"; converted to raw by x{COOKED_TO_RAW[d['cooked_to_raw']]:.4f}" if d.get("cooked_to_raw") else "") + (f"; dough = x{DOUGH_SHARE:.4f}" if d.get("dough_share") else ""))
        else:
            lines.append("- qualifying: none; the records carry only measures, pieces or the unspecified default")
        lines.append("")
    (EVAL / f"fndds_portions_{args.date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (EVAL / f"fndds_portions_{args.date}.json").write_text(json.dumps(found, indent=1, default=float), encoding="utf-8")
    print("\n".join(lines[:6])); print("written:", EVAL / f"fndds_portions_{args.date}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
