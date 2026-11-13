"""The D25 lender list (SPEC_3_mvp.md 12.12.4), from saved runs: every recipe line weighed by a lent cup, spoon or teaspoon measure, in the runs given, with the record that lent it.

    .venv/bin/python -m roli_agent.scripts.d25_lenders --runs <run id> [...] [--before <run id> ...] --out roli_agent/eval/....md

With --before, each line also shows the lender in those runs. Nothing is recomputed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from roli_agent.config import ROOT

LENT = re.compile(r"USDA (?:(Foundation|SR Legacy|Survey) )?(?:Survey )?record (\d+) '([^']*)'")


def lent_lines(run_id: str) -> dict[str, dict]:
    run = json.loads((ROOT / "roli_agent" / "runs" / run_id / "run.json").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for d in run["dishes"]:
        for s in (d.get("estimate") or {}).get("scenarios") or []:
            for l in s.get("ingredients") or []:
                ref = (l.get("conversion") or {}).get("reference") or ""
                m = LENT.search(ref[ref.find("measure lent by"):]) if "measure lent by" in ref else None
                if m and l.get("line"):
                    out[l["line"]] = {"dish": d["item"]["name"][:28], "record": (l.get("match") or {}).get("description", ""), "table": m.group(1) or "Survey", "lender_id": m.group(2), "lender": m.group(3),
                                      "grams": round(float(l["conversion"]["grams"]), 1), "class_level": "class_level_cup_weight" in (l["conversion"].get("flags") or l.get("flags") or []) or "class-level record" in ref}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--before", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    now = {k: v for r in args.runs for k, v in lent_lines(r).items()}
    was = {k: v for r in args.before for k, v in lent_lines(r).items()}
    wide, same = [(k, v) for k, v in now.items() if v["class_level"]], [(k, v) for k, v in now.items() if not v["class_level"]]
    moved = [(k, v) for k, v in same if k in was and was[k]["lender_id"] != v["lender_id"]]
    head = "| dish | line | matched record | lender | table | g | before |"
    rule = "|---|---|---|---|---|---|---|"
    row = lambda k, v: f"| {v['dish']} | {k[:58]} | {v['record'][:42]} | {v['lender'][:40]} | {v['table']} | {v['grams']} | {(was[k]['lender'][:24] + ' ' + str(was[k]['grams'])) if k in was else 'not lent'} |"
    lines = ["# D25 lender list", "", f"{len(now)} lines weighed by a lent measure: {len(same)} from a same-food record, {len(wide)} from a class-level record.", "",
             f"## Still class-level ({len(wide)}), labelled `class_level_cup_weight`", "", head, rule] + [row(k, v) for k, v in sorted(wide, key=lambda t: t[1]["lender"])]
    lines += ["", f"## Moved to a different same-food record ({len(moved)})", "", head, rule] + [row(k, v) for k, v in sorted(moved, key=lambda t: t[1]["lender"])]
    rest = [(k, v) for k, v in same if (k, v) not in moved]
    lines += ["", f"## Same-food, lender unchanged or new ({len(rest)})", "", head, rule] + [row(k, v) for k, v in sorted(rest, key=lambda t: t[1]["lender"])]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
