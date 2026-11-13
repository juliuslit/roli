"""3K (SPEC_3_mvp.md 12.20): fit and validate the plate-weight model on MenuStat's measured items; write recipes/plate_model.json and eval/plate_model_<date>.md.

    .venv/bin/python -m roli_agent.scripts.plate_model [--date YYYY-MM-DD] [--epochs 400]

Data: every MenuStat item (latest year per item) with a serving weight in g or oz outside Beverages, plus the chain-sheet items with a serving weight; kids' meals
and shareable items stay in with a flag. Target: ln(grams). Features: the item's name words (3+ letters, singularised, present in at least 5 training items), the Roli
family the builder's selector gives it (`build_cards.SELECT`; "none" otherwise) and the kids flag. No restaurant feature: it would not exist at run time and it leaks.
Model: ridge regression by full-batch gradient descent (pure Python; no numpy in Roli's environment), lambda chosen by grouped cross-validation. Validation: five folds
grouped by restaurant, so a chain's items are never in both halves; per fold and family the MAE in ln, the median ratio, and the coverage and width of the 80 %
interval built from the training folds' residual quantiles, against the baseline = the family's current approved plate range from recipes/portion_rules.csv applied to
the same held-out items. Switch rule (Julius, 2026-11-08): `live` is true when the held-out coverage of the model's 80 % interval is at least the baseline's and its
intervals are narrower, over the P2 families with a row. The chain sheets (UK) are reported apart as an external check.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT
from roli_agent.recipes.plate_model import features, tokens
from roli_agent.recipes.portions import PortionRules
from roli_agent.scripts import build_cards as bc

OUT = ROOT / "roli_agent" / "recipes" / "plate_model.json"
EVAL = ROOT / "roli_agent" / "eval"
LAMBDAS = (0.3, 1.0, 3.0, 10.0)
FOLDS = 5
MIN_DF = 5
QUANTILE_STEPS = [k / 20 for k in range(21)]
P2_ROWS = {r.dish_type: r for r in PortionRules.load().rows if r.model == "P2" and not r.review_status.startswith("unsourced")}
FAMILY_OF_ROW = {spec["family"]: spec["dish_type"] for spec in bc.ROWS}


def family_for(name: str, cat: str, kids: bool, share: bool) -> str:
    if kids and cat != "Toppings & Ingredients":
        return "kids_dish"
    for fam, (cats, inc, exc) in bc.SELECT.items():
        if cat in cats and (inc is None or bc.re.search(inc, name, bc.re.I)) and not (exc and bc.re.search(exc, name, bc.re.I)):
            return fam
    return "none"


def load_items() -> tuple[list[dict], list[dict]]:
    items, sheets = [], []
    for r in bc.load_menustat():
        if r["Food_Category"] == "Beverages":
            continue
        g = bc.grams(r)
        if not g or g <= 0:
            continue
        kids, share = r["Kids_Meal"] == "1", r["Shareable"] == "1"
        fam = family_for(r["Item_Name"], r["Food_Category"], kids, share)
        items.append({"name": r["Item_Name"], "group": r["restaurant"], "family": fam, "kids": kids, "shareable": share, "y": math.log(float(g)), "grams": float(g)})
    for r in bc.load_chain_sheets():
        g = bc.dec(r["serving_g"])
        if g and g > 0:
            fam = r["family"]
            sheets.append({"name": r["item"], "group": r["business"], "family": fam if fam in FAMILY_OF_ROW else "none", "kids": False, "shareable": False, "y": math.log(float(g)), "grams": float(g)})
    return items, sheets


def fold_of(group: str) -> int:
    return int(hashlib.sha1(group.encode("utf-8")).hexdigest()[:8], 16) % FOLDS


def fit_ridge(rows: list[dict], vocabulary: set[str], lam: float, epochs: int, lr: float = 0.05) -> tuple[float, dict[str, float]]:
    """Ridge regression on binary features by full-batch gradient descent with a per-feature step (Adagrad-style), intercept unpenalised."""
    feats = [features(r["name"], r["family"], r["kids"], vocabulary) for r in rows]
    n = len(rows)
    intercept = sum(r["y"] for r in rows) / n
    coef: dict[str, float] = defaultdict(float)
    g2: dict[str, float] = defaultdict(lambda: 1e-8)
    for _ in range(epochs):
        grads: dict[str, float] = defaultdict(float)
        gi = 0.0
        for r, fs in zip(rows, feats):
            pred = intercept + sum(coef[f] for f in fs)
            err = pred - r["y"]
            gi += err
            for f in fs:
                grads[f] += err
        intercept -= lr * gi / n
        for f, g in grads.items():
            g = g / n + lam * coef[f] / n
            g2[f] += g * g
            coef[f] -= lr * g / math.sqrt(g2[f]) * 10
    return intercept, dict(coef)


def vocabulary_of(rows: list[dict]) -> set[str]:
    df = Counter(t for r in rows for t in tokens(r["name"]))
    return {f"word:{t}" for t, n in df.items() if n >= MIN_DF}


def predict(intercept: float, coef: dict[str, float], vocabulary: set[str], r: dict) -> float:
    return intercept + sum(coef.get(f, 0.0) for f in features(r["name"], r["family"], r["kids"], vocabulary))


def quantiles(xs: list[float]) -> list[float]:
    xs = sorted(xs)
    if not xs:
        return []
    out = []
    for q in QUANTILE_STEPS:
        pos = q * (len(xs) - 1)
        i = min(int(pos), len(xs) - 1)
        j = min(i + 1, len(xs) - 1)
        out.append(xs[i] + (xs[j] - xs[i]) * (pos - i))
    return out


def q_at(qs: list[float], u: float) -> float:
    pos = u * (len(qs) - 1)
    i = min(int(pos), len(qs) - 2)
    return qs[i] + (qs[i + 1] - qs[i]) * (pos - i)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()))
    ap.add_argument("--epochs", type=int, default=300)
    args = ap.parse_args()
    items, sheets = load_items()
    folds = {k: [r for r in items if fold_of(r["group"]) == k] for k in range(FOLDS)}
    # lambda by grouped cross-validation (MAE in ln over the held-out folds)
    cv: dict[float, list[float]] = defaultdict(list)
    held: dict[float, list[tuple[dict, float]]] = defaultdict(list)       # lambda -> (item, prediction) on its held-out fold
    train_resid: dict[float, dict[int, dict[str, list[float]]]] = defaultdict(dict)   # lambda -> fold -> family -> training residuals
    for lam in LAMBDAS:
        for k in range(FOLDS):
            train = [r for j, rows in folds.items() if j != k for r in rows]
            vocab = vocabulary_of(train)
            b0, coef = fit_ridge(train, vocab, lam, args.epochs)
            res_by_fam: dict[str, list[float]] = defaultdict(list)
            for r in train:
                res_by_fam[r["family"]].append(r["y"] - predict(b0, coef, vocab, r))
            train_resid[lam][k] = res_by_fam
            errs = []
            for r in folds[k]:
                p = predict(b0, coef, vocab, r)
                held[lam].append((r, p, k))
                errs.append(abs(p - r["y"]))
            cv[lam].append(statistics.mean(errs) if errs else 0.0)
    best = min(LAMBDAS, key=lambda l: statistics.mean(cv[l]))
    # held-out evaluation with the chosen lambda: the 80 % interval of an item in fold k uses the quantiles of the HELD-OUT residuals of the other four folds (cross-fitted
    # calibration: a training fold's own residuals are tighter than the model's error on new restaurants and would promise more coverage than it delivers)
    by_fam: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    heldres: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r, p, k in held[best]:
        heldres[k][r["family"]].append(r["y"] - p)
    def calib(k: int, fam: str) -> list[float]:
        fam_res = [x for j in range(FOLDS) if j != k for x in heldres[j].get(fam, [])]
        pooled = [x for j in range(FOLDS) if j != k for f in heldres[j].values() for x in f]
        return quantiles(fam_res if len(fam_res) >= 30 else pooled)
    for r, p, k in held[best]:
        qs = calib(k, r["family"])
        lo, hi = math.exp(p + q_at(qs, 0.10)), math.exp(p + q_at(qs, 0.90))
        d = by_fam[r["family"]]
        d["err"].append(abs(p - r["y"]))
        d["ratio"].append(math.exp(p - r["y"]))
        d["cover"].append(1 if lo <= r["grams"] <= hi else 0)
        d["width"].append(math.log(hi / lo))
        d["resid"].append(r["y"] - p)
        row = P2_ROWS.get(FAMILY_OF_ROW.get(r["family"], ""))
        if row is not None:
            d["base_cover"].append(1 if float(row.low) <= r["grams"] <= float(row.high) else 0)
            d["base_width"].append(math.log(float(row.high) / float(row.low)))
    # the final model on every item
    vocab_all = vocabulary_of(items)
    b0, coef = fit_ridge(items, vocab_all, best, args.epochs)
    families = {}
    for fam, d in by_fam.items():
        families[fam] = {"n": len(d["resid"]), "residual_quantiles": quantiles(d["resid"]) if len(d["resid"]) >= 30 else [], "held_out_mae_ln": round(statistics.mean(d["err"]), 4),
                         "coverage_80": round(statistics.mean(d["cover"]), 3), "width_ln": round(statistics.mean(d["width"]), 3),
                         "baseline_coverage": round(statistics.mean(d["base_cover"]), 3) if d["base_cover"] else None, "baseline_width_ln": round(statistics.mean(d["base_width"]), 3) if d["base_width"] else None}
    pooled = quantiles([x for d in by_fam.values() for x in d["resid"]])
    # the switch rule over the P2 families with a row
    cov_m, cov_b, w_m, w_b, n_cmp = [], [], [], [], 0
    for fam, d in by_fam.items():
        if d["base_cover"]:
            cov_m += d["cover"]; cov_b += d["base_cover"]; w_m += d["width"]; w_b += d["base_width"]; n_cmp += len(d["base_cover"])
    model_cov, base_cov = statistics.mean(cov_m), statistics.mean(cov_b)
    model_w, base_w = statistics.median(w_m), statistics.median(w_b)
    live = model_cov >= base_cov and model_w < base_w
    # external check: the UK chain sheets
    ext = defaultdict(list)
    for r in sheets:
        p = predict(b0, coef, vocab_all, r)
        qs = families.get(r["family"], {}).get("residual_quantiles") or pooled
        lo, hi = math.exp(p + q_at(qs, 0.10)), math.exp(p + q_at(qs, 0.90))
        ext["err"].append(abs(p - r["y"])); ext["cover"].append(1 if lo <= r["grams"] <= hi else 0); ext["width"].append(math.log(hi / lo))
        row = P2_ROWS.get(FAMILY_OF_ROW.get(r["family"], ""))
        if row is not None:
            ext["base_cover"].append(1 if float(row.low) <= r["grams"] <= float(row.high) else 0)
    model = {"version": f"3k-{args.date}", "trained_on": args.date, "n_items": len(items), "n_restaurants": len({r["group"] for r in items}), "lambda": best, "epochs": args.epochs,
             "cv_mae_ln_by_lambda": {str(l): round(statistics.mean(cv[l]), 4) for l in LAMBDAS}, "intercept": b0, "coef": {k: round(v, 6) for k, v in coef.items() if abs(v) > 1e-6},
             "pooled_residual_quantiles": pooled, "families": families,
             "validation": {"held_out_mae_ln": round(statistics.mean([abs(p - r["y"]) for r, p, _ in held[best]]), 4), "p2_families_items": n_cmp, "model_coverage_80": round(model_cov, 3),
                            "baseline_coverage": round(base_cov, 3), "model_median_width_ln": round(model_w, 3), "baseline_median_width_ln": round(base_w, 3),
                            "model_median_width_ratio": round(math.exp(model_w), 2), "baseline_median_width_ratio": round(math.exp(base_w), 2),
                            "external_uk_sheets": {"n": len(sheets), "mae_ln": round(statistics.mean(ext["err"]), 4) if ext["err"] else None, "coverage_80": round(statistics.mean(ext["cover"]), 3) if ext["cover"] else None,
                                                   "baseline_coverage": round(statistics.mean(ext["base_cover"]), 3) if ext["base_cover"] else None}},
             "live": live, "switch_rule": "live when held-out 80 % coverage >= the family range's coverage and the median interval is narrower, over the P2 families with a row (Julius, 2026-11-08)",
             "sources": "MenuStat (NYC DOHMH, NYC Open Data qgc5-ecnb, 2017-2018 items; data/menustat_download/SOURCE_AND_LICENCE.md) and data/chain_sheets/*.csv (training excludes the UK sheets, reported as the external check)"}
    OUT.write_text(json.dumps(model, indent=1), encoding="utf-8")
    v = model["validation"]
    L = [f"# Plate-weight model, {args.date}", "", f"{len(items)} MenuStat items with a weight, {model['n_restaurants']} restaurants, {FOLDS} folds grouped by restaurant; ridge on name words (vocabulary {len(vocab_all)}), family and the kids flag; "
         f"lambda {best} (CV MAE in ln by lambda: {model['cv_mae_ln_by_lambda']}); {args.epochs} gradient steps. Interval quantiles are cross-fitted: an item's interval uses the held-out residuals of the other folds.", "",
         f"**Held-out:** MAE {v['held_out_mae_ln']} in ln (a factor of {math.exp(v['held_out_mae_ln']):.2f}). Over the {n_cmp} held-out items of P2 families with a row: the model's 80 % interval covers "
         f"{100 * model_cov:.0f} % (the family range covers {100 * base_cov:.0f} %), median width {math.exp(model_w):.1f}x against {math.exp(base_w):.1f}x. **Switch rule: {'met, the model is live' if live else 'not met, the model stays off'}.**",
         f"External check, the UK chain sheets ({len(sheets)} items): MAE {v['external_uk_sheets']['mae_ln']} in ln, 80 % interval coverage {v['external_uk_sheets']['coverage_80']}, family range coverage {v['external_uk_sheets']['baseline_coverage']}.", "",
         "| family | held-out items | MAE ln | median ratio | model 80 % coverage | model width | family range coverage | family range width |", "|---|---|---|---|---|---|---|---|"]
    for fam, f in sorted(families.items(), key=lambda t: -t[1]["n"]):
        d = by_fam[fam]
        L.append(f"| {fam} | {f['n']} | {f['held_out_mae_ln']} | {statistics.median(d['ratio']):.2f} | {f['coverage_80']} | {math.exp(f['width_ln']):.1f}x | {f['baseline_coverage'] if f['baseline_coverage'] is not None else ''} | {math.exp(f['baseline_width_ln']):.1f}x |" if f["baseline_width_ln"] else
                 f"| {fam} | {f['n']} | {f['held_out_mae_ln']} | {statistics.median(d['ratio']):.2f} | {f['coverage_80']} | {math.exp(f['width_ln']):.1f}x | | |")
    top = sorted(coef.items(), key=lambda t: -abs(t[1]))[:30]
    L += ["", "## The thirty largest coefficients (ln grams)", ""] + [f"- {k}: {v:+.3f}" for k, v in top]
    out = EVAL / f"plate_model_{args.date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    print("written", OUT, out, "live:", live)
    return 0


if __name__ == "__main__":
    sys.exit(main())
