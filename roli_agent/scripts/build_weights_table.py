"""Build the Phase 2C assumed-weights table with the assumption class COMPUTED from the USDA record and the upper-bound
weight (Julius, 2026-11-02: never trust a typed class label).

    .venv/bin/python -m roli_agent.scripts.build_weights_table [--portions roli_agent/eval/garnish_portions_2026-11-02.json]
        -> roli_agent/recipes/assumed_weights.csv and roli_agent/recipes/assumed_weights.md

Display-level class (spec 2C section 3): zero_nutrient = the record reports both nutrients and both are exactly 0;
low_impact = both reported and the high-bound contribution is below the Phase 2A display floor
(< 0.005 g saturated fat, so it displays as 0.00, and < 0.5 mg cholesterol); displayable = everything else
(the contribution shows in the display; it says nothing about how large it is).
Materiality (separate diagnostic, absolute high-bound contribution against common daily reference amounts of
20 g saturated fat and 300 mg cholesterol): negligible (below the display floor), minor (< 1 % of the reference:
< 0.2 g or < 3 mg), moderate (< 5 %: < 1 g or < 15 mg), major (at or above 5 %). The larger of the two nutrients' tiers wins.
A record missing a nutrient can never be zero_nutrient or low_impact (class "nutrient_missing").
Basis: usda_measure = the gram weight is a USDA household measure of the record (verified); proposed = the
restaurant-usage range is the agent's draft with no external reference (unverified); blocked = a questionable
physical or nutritional substitution that must not be a trusted input (W10 bottarga/roe, W20 shishito/chili, W28).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT
from roli_agent.recipes.adapt import display_class as _display_class, materiality as _materiality

FLOOR_SAT, FLOOR_CHOL = Decimal("0.005"), Decimal("0.5")
REFERENCE_SAT, REFERENCE_CHOL = Decimal("20"), Decimal("300")      # common daily reference amounts, for the materiality tiers only

# id, ingredient / role, low g, high g, basis for the range, portion label(s) the bounds come from, notes
ROWS = [
    ("W01", "chives, garnish on a starter", "chives", 1, 3, "usda_measure", "1 tsp chopped = 1 g; 1 tbsp chopped = 3 g", ""),
    ("W02", "basil leaves, garnish", "basil leaves", 2.5, 6, "usda_measure", "5 leaves = 2.5 g; 1/4 cup leaves = 6 g", ""),
    ("W03a", "mint leaves, garnish", "mint leaves", 0.3, 11.4, "usda_measure", "2 leaves = 0.3 g; 2 tbsp = 11.4 g", ""),
    ("W03b", "shiso leaves, garnish", None, None, None, "blocked", "no USDA shiso (perilla) record; a spearmint measure is not a shiso measure", "blocked: needs a reviewed weight and a reviewed composition proxy"),
    ("W04a", "parsley, garnish", "parsley", 3.8, 10, "usda_measure", "1 tbsp = 3.8 g; 10 sprigs = 10 g", ""),
    ("W04b", "cilantro, garnish", "cilantro", 4, 20, "usda_measure", "1/4 cup = 4 g; 9 sprigs = 20 g", ""),
    ("W05", "grated hard cheese finished over a salad or pasta", "parmesan grated", 5, 15, "proposed", "1 tbsp = 5 g (USDA); 1-3 tbsp is the proposed restaurant range", ""),
    ("W06", "fresh mozzarella / fior di latte on one pizza", "mozzarella (fior di latte)", 85, 170, "proposed", "1 oz = 28.35 g, 6 slices = 170 g (USDA); 3-6 oz per pizza is proposed", ""),
    ("W07", "sesame seeds, toasted, garnish", "sesame seeds toasted", 3, 9, "proposed", "USDA lists 1 oz only; 1-3 tsp is proposed", ""),
    ("W08", "tahini in a dressing, per serving", "tahini", 15, 30, "proposed", "1 tbsp = 15 g (USDA); 1-2 tbsp proposed", ""),
    ("W09", "olive oil, drizzle to finish", "olive oil", 4.5, 13.5, "proposed", "1 tsp = 4.5 g, 1 tbsp = 13.5 g (USDA); the drizzle range is proposed", ""),
    ("W10", "bottarga, shaved or grated over a starter", "fish roe (bottarga proxy)", 3, 10, "blocked", "no USDA bottarga; raw mixed roe is a questionable composition proxy for cured, dried roe", "blocked: physically and nutritionally questionable substitution; needs evidence"),
    ("W11", "grapes, halved, garnish", "grapes", 20, 49, "usda_measure", "10 grapes = 49 g; 4-10 grapes", ""),
    ("W12", "lemon juice, finishing", "lemon juice", 5.9, 15, "usda_measure", "1 wedge yields 5.9 g; 1 tbsp = 15.25 g", ""),
    ("W13", "lemon zest", "lemon zest", 1, 2, "usda_measure", "1 tsp = 2 g", ""),
    ("W14", "salt, to taste", "sea salt", 0.4, 6, "usda_measure", "1 dash = 0.4 g; 1 tsp = 6 g", ""),
    ("W15", "black pepper, to taste", "black pepper", 0.1, 2.3, "usda_measure", "1 dash = 0.1 g; 1 tsp ground = 2.3 g", ""),
    ("W16", "red pepper flakes, pinch", "red pepper flakes", 0.5, 1.8, "usda_measure", "1 tsp = 1.8 g", ""),
    ("W17", "sourdough croutons or torn bread on a salad", "sourdough croutons", 28, 60, "proposed", "1 oz = 28.35 g (USDA); 1-2 oz proposed", ""),
    ("W18", "corn kernels, side on a main", "corn kernels", 73, 145, "usda_measure", "1 small ear = 73 g; 1 cup = 145 g", ""),
    ("W19", "summer squash, side on a main", "zucchini / summer squash", 118, 196, "usda_measure", "1 small = 118 g; 1 medium = 196 g", ""),
    ("W20", "shishito peppers, side", "shishito (green chili proxy)", 45, 135, "blocked", "no USDA shishito; the hot-green-chili record is a questionable size and composition proxy", "blocked: needs evidence"),
    ("W21", "pluot, sliced, in a salad", "plum (pluot proxy)", 33, 66, "proposed", "1 plum = 66 g (USDA) as a size proxy for a pluot: D21 says a proxy's whole-item size is an assumption", "proxy size: treat as proposed"),
    ("W22", "pistachios, garnish", "pistachios", 7, 14, "proposed", "1 kernel = 0.7 g (USDA); 10-20 kernels proposed", ""),
    ("W23", "capers, garnish", "capers", 4.3, 8.6, "usda_measure", "1 tbsp drained = 8.6 g", ""),
    ("W24", "green olives (castelvetrano), garnish", "castelvetrano olives (green olives)", 8, 27, "proposed", "1 olive = 2.7 g (USDA); 3-10 olives proposed", ""),
    ("W25", "egg yolk, one", "egg yolk", 17, 17, "usda_measure", "1 large = 17 g", ""),
    ("W26", "pancetta or guanciale, cooked, in a pasta serving", "bacon / pancetta proxy", 16, 32, "proposed", "1 slice cooked bacon = 8.1 g (USDA, composition proxy); 2-4 slices proposed", "composition proxy (bacon for pancetta)"),
    ("W27", "heavy cream, finishing", "heavy cream", 15, 30, "proposed", "1 tbsp = 15 g (USDA); 1-2 tbsp proposed", ""),
    ("W28", "little gem lettuce, one head", None, None, None, "blocked", "no USDA record; romaine's head (626 g) must not be used (D21)", "blocked: needs a reviewed weight"),
]


# Words of a menu ingredient or a recipe line name that select a row (singular, lower case). Rows without keys are never auto-selected.
KEYS = {
    "W01": "chive, chives", "W02": "basil, basil leaves, genovese basil, thai basil", "W03a": "mint, mint leaves, spearmint", "W03b": "shiso, perilla",
    "W04a": "parsley", "W04b": "cilantro, coriander leaves", "W05": "pecorino, pecorino sardo, parmesan, parmigiano, grana, hard cheese, romano",
    "W06": "fior di latte, mozzarella, fresh mozzarella", "W07": "sesame, toasted sesame, sesame seeds", "W08": "tahini, tahini vinaigrette",
    "W09": "olive oil, extra virgin olive oil, extra-virgin olive oil", "W10": "bottarga", "W11": "grape, grapes, muscat grape", "W12": "lemon juice, juice of lemon, lemon wedge",
    "W13": "lemon zest, zest", "W14": "salt, sea salt, kosher salt, flaky salt, flaky sea salt", "W15": "black pepper, pepper, freshly ground black pepper",
    "W16": "red pepper flakes, chili flakes, chilli flakes, pepper flakes", "W17": "sourdough, croutons, bread", "W18": "corn, corn kernels, sweet corn",
    "W19": "squash, summer squash, zucchini", "W20": "shishito, shishito peppers", "W21": "pluot", "W22": "pistachios, pistachio",
    "W23": "capers", "W24": "olives, castelvetrano olives, green olives", "W25": "egg yolk", "W26": "pancetta, guanciale", "W27": "heavy cream, cream",
    "W28": "little gem, little gem lettuce, baby gem",
}


def materiality(sat_g: Decimal | None, chol_mg: Decimal | None) -> str:
    return _materiality(sat_g, chol_mg)             # one definition, in roli_agent/recipes/adapt.py


def classify(sat: float | None, chol: float | None, high_g: float | None) -> tuple[str, str, str]:
    """-> (class, high-bound saturated fat g, high-bound cholesterol mg) computed, never typed."""
    if sat is None or chol is None:
        return "nutrient_missing", "", ""
    if high_g is None:
        return "no_weight", "", ""
    s = Decimal(str(sat)) * Decimal(str(high_g)) / 100
    c = Decimal(str(chol)) * Decimal(str(high_g)) / 100
    cls = _display_class(sat, chol, Decimal(str(high_g)))      # one definition, in roli_agent/recipes/adapt.py
    return cls, f"{s:.4f}", f"{c:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portions", default=str(ROOT / "roli_agent" / "eval" / "garnish_portions_2026-11-02.json"))
    args = parser.parse_args()
    usda = {r["ingredient"]: r for r in json.loads(Path(args.portions).read_text(encoding="utf-8"))}
    out_rows = []
    for wid, role, key, low, high, basis, measures, note in ROWS:
        rec = usda.get(key) if key else None
        sat = rec.get("sat_fat_g_100g") if rec else None
        chol = rec.get("chol_mg_100g") if rec else None
        cls, s_high, c_high = classify(sat, chol, high)
        status = {"usda_measure": "verified_usda_measure; restaurant usage assumed", "proposed": "proposed_unreviewed", "blocked": "blocked_questionable_proxy"}[basis]
        s_low, c_low = ("", "")
        if sat is not None and chol is not None and low is not None:
            s_low, c_low = f"{Decimal(str(sat)) * Decimal(str(low)) / 100:.4f}", f"{Decimal(str(chol)) * Decimal(str(low)) / 100:.2f}"
        mat = materiality(Decimal(s_high), Decimal(c_high)) if s_high else "unknown"
        out_rows.append({"id": wid, "ingredient_role": role, "ingredient_keys": KEYS.get(wid, ""), "fdc_id": rec["fdc_id"] if rec else "",
                         "usda_description": rec["description"] if rec else "",
                         "sat_fat_g_per_100g": sat if sat is not None else "", "cholesterol_mg_per_100g": chol if chol is not None else "",
                         "low_g": low if low is not None else "", "high_g": high if high is not None else "", "basis": basis, "measures": measures,
                         "computed_class": cls, "low_bound_sat_fat_g": s_low, "low_bound_cholesterol_mg": c_low,
                         "high_bound_sat_fat_g": s_high, "high_bound_cholesterol_mg": c_high, "materiality_at_high": mat, "review_status": status,
                         "approved_by": "", "approved_on": "", "notes": note})
    csv_path = ROOT / "roli_agent" / "recipes" / "assumed_weights.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    md = ["| ID | Ingredient / role | USDA record | sat fat g/100 g | chol mg/100 g | Low g | High g | High-bound sat fat g | High-bound chol mg | Display class | Materiality | Basis | Review status |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
    for r in out_rows:
        md.append(f"| {r['id']} | {r['ingredient_role']} | {r['usda_description'][:40]} ({r['fdc_id']}) | {r['sat_fat_g_per_100g']} | {r['cholesterol_mg_per_100g']} | {r['low_g']} | {r['high_g']} | "
                  f"{r['high_bound_sat_fat_g']} | {r['high_bound_cholesterol_mg']} | {r['computed_class']} | {r['materiality_at_high']} | {r['basis']} | {r['review_status']} |")
    (ROOT / "roli_agent" / "recipes" / "assumed_weights.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for r in out_rows:
        print(f"{r['id']:5s} {r['computed_class']:16s} {r['materiality_at_high']:10s} sat@high {r['high_bound_sat_fat_g'] or '-':8s} chol@high {r['high_bound_cholesterol_mg'] or '-':7s} {r['basis']:13s} {r['ingredient_role'][:45]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
