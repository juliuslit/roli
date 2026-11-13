"""3K (SPEC_3_mvp.md 12.20): the band against the extremes, recomputed offline from saved runs. No network, no model call: the saved Phase 2A calculations are
re-read, the intervals re-formed (`scenario_interval`) and the band drawn (`sampling`), so runs saved before 3K get a band too and the widths can be compared.

    .venv/bin/python -m roli_agent.scripts.band_report --runs <run id> [...] [--label ...] --out roli_agent/eval/band_report_<date>.md [--draws 2000]

Per dish: extremes, band, their widths (top / bottom), the plate-weight source, recipes set aside, the recipe weights. Per menu and overall: median widths before
(extremes) and after (band), the share of dishes narrower than 2x and 3x, and the width decomposition (plate size, recipes, assumed amounts, frying fat) by
holding each factor at its middle.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT
from roli_agent.mvp.models import MvpConfig
from roli_agent.recipes.compare_dishes import ExternalEvidence, dish_interval, scenario_interval
from roli_agent.recipes.models import DishEstimate, DishInterval
from roli_agent.recipes.plate_weights import PlateWeights
from roli_agent.recipes.sampling import PlateSampler, load_frying_fat_prior, make_sampler
from roli_agent.recipes.survey import SurveyDishEstimate

RUNS = ROOT / "roli_agent" / "runs"
NUTRIENT = "saturated_fat_g"


def rebuild(d: dict, *, evidence: ExternalEvidence, plate_weights: PlateWeights, fat_prior, cfg: MvpConfig, draws: int) -> DishInterval | None:
    """The saturated-fat interval of one saved dish, re-formed with the band."""
    if not d.get("estimate"):
        return None
    est = DishEstimate.model_validate(d["estimate"])
    pairs = {p.derived_from: p for p in est.adapted_pairs}
    pub = {p.derived_from: p for p in est.portioned if p.input_kind == "published"}
    pr = {p.derived_from.removesuffix("::adapted"): p for p in est.portioned if p.input_kind == "adapted_pair"}
    item = d["item"]
    grade_of = {s.scenario_id: s.relevance.grade for s in est.scenarios}
    coverage_of = {s.scenario_id: s.relevance.menu_coverage for s in est.scenarios}
    plates = PlateSampler(plate_weights, n_min=cfg.plate_samples_min, dish_words=f"{item.get('name', '')} {item.get('description', '')}", section=item.get("section", ""), family=d.get("dish_type"))
    sampler = make_sampler(plates, draws=draws, grade_of=grade_of, coverage_of=coverage_of, outlier_factor=float(cfg.recipe_outlier_factor), fat_prior=fat_prior,
                           medium_weight=float(cfg.grade_weight_medium), q_low=float(cfg.band_low_q), q_high=float(cfg.band_high_q))
    ivs, no_portion = [], 0
    for s in est.scenarios:
        if s.status != "calculated":
            continue
        iv = scenario_interval(s, pairs.get(s.scenario_id), pub.get(s.scenario_id), pr.get(s.scenario_id), NUTRIENT, evidence)
        if iv is None:
            no_portion += 1
        else:
            ivs.append(iv)
    if d.get("survey_dish"):
        sv = SurveyDishEstimate.model_validate(d["survey_dish"])
        if sv.applicable and sv.interval(NUTRIENT) is not None:
            ivs.append(sv.interval(NUTRIENT))
    return dish_interval(d["key"], NUTRIENT, ivs, no_portion, sampler=sampler)


def ratio(lo, hi) -> float | None:
    lo, hi = float(lo), float(hi)
    return hi / lo if lo > 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--draws", type=int, default=None)
    ap.add_argument("--intro", default="")
    args = ap.parse_args()
    cfg = MvpConfig()
    draws = args.draws or cfg.band_draws
    evidence, pw, prior = ExternalEvidence.load(), PlateWeights.load(), load_frying_fat_prior() if cfg.frying_fat_prior else None
    rows = []
    for k, rid in enumerate(args.runs):
        label = args.label[k] if k < len(args.label) else rid
        r = json.loads((RUNS / rid / "run.json").read_text(encoding="utf-8"))
        ranked = {x["key"] for x in r["ranking"]}
        for d in r["dishes"]:
            if d["status"] not in ("evaluated", "flagged"):
                continue
            iv = rebuild(d, evidence=evidence, plate_weights=pw, fat_prior=prior, cfg=cfg, draws=draws)
            if iv is None or iv.high is None or iv.low is None:
                continue
            rows.append({"menu": label, "run": rid, "dish": d["item"]["name"], "family": d.get("dish_type"), "ranked": d["key"] in ranked, "low": iv.low, "high": iv.high,
                         "band_low": iv.band_low, "band_mid": iv.band_mid, "band_high": iv.band_high, "x_ratio": ratio(iv.low, iv.high),
                         "b_ratio": ratio(iv.band_low, iv.band_high) if iv.band_low is not None else None, "plate_source": iv.plate_source, "set_aside": iv.set_aside,
                         "n_bounded": iv.n_bounded, "weights": iv.recipe_weights, "old_mid": (iv.low + iv.high) / 2})
    def med(xs):
        xs = [x for x in xs if x is not None]
        return statistics.median(xs) if xs else None
    L = [f"# Band against extremes ({Path(args.out).stem})", ""] + ([args.intro, ""] if args.intro else [])
    L += [f"{len(rows)} bounded dishes from {len(args.runs)} runs; {draws} draws per dish; band = {int(cfg.band_low_q * 100)}th-{int(cfg.band_high_q * 100)}th percentile; plate samples minimum {cfg.plate_samples_min}; "
          f"outlier factor {cfg.recipe_outlier_factor}; frying-fat prior {'on' if prior else 'off'}.", ""]
    xr, br = [x["x_ratio"] for x in rows], [x["b_ratio"] for x in rows]
    L += ["## Width (top divided by bottom)", "", "| | extremes | band |", "|---|---|---|",
          f"| median | {med(xr):.1f}x | {med(br):.1f}x |",
          f"| 75th percentile | {sorted(x for x in xr if x)[3 * len([x for x in xr if x]) // 4]:.1f}x | {sorted(x for x in br if x)[3 * len([x for x in br if x]) // 4]:.1f}x |",
          f"| dishes under 2x | {sum(1 for x in xr if x and x < 2)} | {sum(1 for x in br if x and x < 2)} |",
          f"| dishes under 3x | {sum(1 for x in xr if x and x < 3)} | {sum(1 for x in br if x and x < 3)} |",
          f"| dishes over 5x | {sum(1 for x in xr if x and x > 5)} | {sum(1 for x in br if x and x > 5)} |", ""]
    src = Counter(x["plate_source"].split("(")[0] for x in rows)
    L += ["## Where the plate weights came from", ""] + [f"- {k}: {v} dishes" for k, v in src.most_common()] + [""]
    aside = [x for x in rows if x["set_aside"]]
    L += [f"## Recipes set aside as outliers: {len(aside)} dishes", ""] + [f"- {x['menu']}: {x['dish'][:40]}: {', '.join(s.split(':')[0] for s in x['set_aside'])}" for x in aside[:40]] + [""]
    moved = sorted(rows, key=lambda x: -abs(math.log(float(x["band_mid"]) / float(x["old_mid"]))) if x["band_mid"] and x["old_mid"] > 0 else 0)[:15]
    L += ["## Middles that moved most (band median against the old midpoint)", "", "| menu | dish | old midpoint | band middle |", "|---|---|---|---|"]
    L += [f"| {x['menu']} | {x['dish'][:40]} | {float(x['old_mid']):.2f} | {float(x['band_mid']):.2f} |" for x in moved if x["band_mid"] is not None]
    L += ["", "## Per menu", "", "| menu | dishes | median extremes | median band | under 3x before / after |", "|---|---|---|---|---|"]
    for label in dict.fromkeys(x["menu"] for x in rows):
        xs = [x for x in rows if x["menu"] == label]
        L.append(f"| {label} | {len(xs)} | {med([x['x_ratio'] for x in xs]):.1f}x | {med([x['b_ratio'] for x in xs]):.1f}x | {sum(1 for x in xs if x['x_ratio'] and x['x_ratio'] < 3)} / {sum(1 for x in xs if x['b_ratio'] and x['b_ratio'] < 3)} |")
    L += ["", "## Every dish", "", "| menu | dish | family | extremes g | band g (middle) | extremes x | band x | plate source | recipes | set aside |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        L.append(f"| {x['menu']} | {x['dish'][:36]} | {x['family']} | {float(x['low']):.2f}-{float(x['high']):.2f} | {float(x['band_low']):.2f}-{float(x['band_high']):.2f} ({float(x['band_mid']):.2f}) | "
                 f"{x['x_ratio']:.1f} | {x['b_ratio']:.1f} | {x['plate_source'][:40]} | {x['n_bounded']} | {len(x['set_aside'])} |")
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:30]))
    print("... written", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
