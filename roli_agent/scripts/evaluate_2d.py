"""Phase 2D: measure the comparison prototype against the human-reviewed expectations (`roli_agent/eval/expectations_2d_v1.csv`).

Three questions, per nutrient: (1) does each dish's modeled interval overlap the expected range (plausible magnitude)? (2) do the pairwise
verdicts agree with the expected order (a `clear` verdict in the expected direction = agree; `clear` the other way = contradiction; `overlapping`
or `insufficient_evidence` = undecided, neither right nor wrong)? (3) how many of the ten dish pairs does the prototype decide at all?

    .venv/bin/python -m roli_agent.scripts.evaluate_2d [--run roli_agent/eval/2d_controlled_2026-11-03.json] [--expectations roli_agent/eval/expectations_2d_v1.csv]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=str(ROOT / "roli_agent" / "eval" / "2d_controlled_2026-11-03.json"))
    parser.add_argument("--expectations", default=str(ROOT / "roli_agent" / "eval" / "expectations_2d_v1.csv"))
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    run = json.loads(Path(args.run).read_text(encoding="utf-8"))
    exp_rows = list(csv.DictReader(Path(args.expectations).open(encoding="utf-8")))
    exp = {(r["dish"], r["nutrient"]): r for r in exp_rows}
    comparison = run["comparison"]
    report = {"run": args.run, "expectations": args.expectations, "expectations_sha256": hashlib.sha256(Path(args.expectations).read_bytes()).hexdigest(),
              "magnitude": [], "pairwise": [], "summary": {}}
    print(f"expectations {args.expectations} (sha256 {report['expectations_sha256'][:16]}...), reviewer: {exp_rows[0]['reviewer']}, status: {exp_rows[0]['review_status']}\n")
    print("=== MAGNITUDE: modeled interval per portion vs expected range ===")
    overlap_n, total_n = 0, 0
    for n in NUTRIENTS:
        for dish, iv in comparison["intervals"][n].items():
            e = exp.get((dish, n))
            if e is None:
                continue
            total_n += 1
            lo, hi = (Decimal(iv["low"]) if iv["low"] is not None else None), (Decimal(iv["high"]) if iv["high"] is not None else None)
            elo, ehi = Decimal(e["expected_low_per_portion"]), Decimal(e["expected_high_per_portion"])
            if lo is None:
                verdict = "no_interval"
            elif hi is None:
                verdict = "lower_bound_only:" + ("consistent" if lo <= ehi else "above_expected")
            else:
                overlaps = lo <= ehi and hi >= elo
                verdict = "overlaps_expected" if overlaps else ("below_expected" if hi < elo else "above_expected")
            if verdict.startswith("overlaps") or verdict.endswith("consistent"):
                overlap_n += 1
            wider = (hi - lo) > (ehi - elo) if lo is not None and hi is not None else None
            report["magnitude"].append({"dish": dish, "nutrient": n, "modeled_low": str(lo), "modeled_high": str(hi), "expected_low": str(elo), "expected_high": str(ehi),
                                        "verdict": verdict, "modeled_wider_than_expected": wider, "n_bounded": iv["n_bounded"], "n_scenarios": iv["n_scenarios"]})
            print(f"  {n:16s} {dish:20s} modeled {str(lo)[:6]:>6s}-{str(hi)[:6]:>6s}  expected {elo}-{ehi}  -> {verdict}{'  (modeled range wider than expected)' if wider else ''}")
    print(f"\n  {overlap_n}/{total_n} dish-nutrient intervals overlap or are consistent with the expected range")

    print("\n=== PAIRWISE: verdicts vs the expected order ===")
    agree, contradict, undecided = 0, 0, 0
    for pw in comparison["pairwise"]:
        n = pw["nutrient"]
        ea, eb = exp.get((pw["dish_a"], n)), exp.get((pw["dish_b"], n))
        if ea is None or eb is None:
            continue
        ra, rb = int(ea["expected_rank_1_lowest_to_5"]), int(eb["expected_rank_1_lowest_to_5"])
        expected_lower = pw["dish_a"] if ra < rb else pw["dish_b"] if rb < ra else None
        # the expectation says whether the two expected ranges are themselves disjoint
        ranges_disjoint = Decimal(ea["expected_high_per_portion"]) < Decimal(eb["expected_low_per_portion"]) or Decimal(eb["expected_high_per_portion"]) < Decimal(ea["expected_low_per_portion"])
        if pw["verdict"] in ("well_supported", "tentative"):
            status = ("agrees" if pw["lower"] == expected_lower else "CONTRADICTS") + ("" if pw["verdict"] == "well_supported" else " (tentative)")
            if status.startswith("agrees"):
                agree += 1
            else:
                contradict += 1
        else:
            status = "undecided (expected " + ("a clear order" if ranges_disjoint else "overlap") + ")"
            undecided += 1
        report["pairwise"].append({**pw, "expected_lower": expected_lower, "expected_ranges_disjoint": ranges_disjoint, "status": status})
        print(f"  {n:16s} {pw['dish_a']:20s} vs {pw['dish_b']:20s} {pw['verdict']:22s} lower={str(pw['lower']):20s} expected lower={expected_lower}  -> {status}"
              + (f"  [{'; '.join(c[:60] for c in pw['caveats'])}]" if pw.get("caveats") else ""))
    decided = agree + contradict
    print(f"\n  decided {decided} of {decided + undecided} pairs; {agree} agree with the expected order, {contradict} contradict it, {undecided} undecided")
    report["summary"] = {"magnitude_consistent": overlap_n, "magnitude_total": total_n, "pairs_decided": decided, "pairs_agree": agree, "pairs_contradict": contradict, "pairs_undecided": undecided}
    out = ROOT / "roli_agent" / "eval" / f"2d_evaluation{args.tag}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
