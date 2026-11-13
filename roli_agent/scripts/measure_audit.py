"""The measure audit (SPEC_3_mvp.md 12.14.8c): every `no_usda_portion` line in the given runs, with what is known about it, and how the lines compare between two sets of runs.

    .venv/bin/python -m roli_agent.scripts.measure_audit --before <run id> [...] --after <run id> [...] --out roli_agent/eval/measure_audit_<date>_3h.md

A line of the before runs is sorted by what happened to it in the after runs: weighed by a same-food record, weighed by the record or the page (a reading bug), or still unweighed (a real gap).
Nothing is recomputed; a hand review of the remaining lines belongs in the checkpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from roli_agent.config import ROOT


def lines_of(run_id: str) -> dict[tuple[str, str], dict]:
    run = json.loads((ROOT / "roli_agent" / "runs" / run_id / "run.json").read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict] = {}
    for d in run["dishes"]:
        for s in (d.get("estimate") or {}).get("scenarios") or []:
            if s.get("status") != "calculated":
                continue
            for l in s.get("ingredients") or []:
                if l.get("line"):
                    filled = next((a.get("row_id") or a.get("source") for p in (d.get("estimate") or {}).get("adapted_pairs") or [] if p.get("derived_from") == s["scenario_id"]
                                   for a in p.get("assumptions") or [] if a.get("ingredient_id") == l.get("ingredient_id")), None)
                    out[(s["source"]["canonical_url"], l["line"])] = {"filled": filled, "dish": d["item"]["name"][:26], "host": s["source"]["host"], "line": l["line"], "blocker": l.get("blocker"), "excluded": l.get("excluded_from_calculation"),
                                                                     "record": (l.get("match") or {}).get("description") or "", "grams": (l.get("conversion") or {}).get("grams"), "reference": (l.get("conversion") or {}).get("reference") or "",
                                                                     "flags": l.get("flags") or []}
    return out


def verdict(after: dict | None) -> str:
    if after is None:
        return "recipe not processed in the after runs"
    if after["grams"] is None:
        held = after["blocker"] is not None
        how = f"; the pair weighs it ({after['filled']})" if after["filled"] else ""
        if after["excluded"] == "negligible_composition":
            return f"real gap, near-zero: holds nothing up{how}"
        if after["excluded"]:
            return f"left out by another rule ({after['excluded']})"
        return f"real gap{how}" if held else f"no longer blocking{how}"
    if "measure lent by" in after["reference"]:
        return "measure in a same-food record"
    return "reading bug: the line or the record had it"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", nargs="+", required=True)
    ap.add_argument("--after", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    before = {k: v for r in args.before for k, v in lines_of(r).items() if v["blocker"] == "no_usda_portion"}
    after = {k: v for r in args.after for k, v in lines_of(r).items()}
    rows = [(verdict(after.get(k)) if args.after else "before only", v, after.get(k)) for k, v in before.items()]
    counts: dict[str, int] = {}
    for kind, _, _ in rows:
        counts[kind.split(";")[0].split(" (")[0]] = counts.get(kind.split(";")[0].split(" (")[0], 0) + 1
    new = [v for k, v in after.items() if v["blocker"] == "no_usda_portion" and k not in before]
    lines = ["# Measure audit", "", f"{len(before)} `no_usda_portion` lines in the before runs; {sum(1 for v in after.values() if v['blocker'] == 'no_usda_portion')} in the after runs.", "", "| what happened | lines |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in sorted(counts.items(), key=lambda t: -t[1])]
    lines += ["", "| result | dish | line | record | grams after | how |", "|---|---|---|---|---|---|"]
    for kind, v, a in sorted(rows, key=lambda t: (t[0], t[1]["dish"])):
        g = (a or {}).get("grams")
        lines.append(f"| {kind} | {v['dish']} | {v['line'][:70]} | {v['record'][:44]} | {round(float(g), 1) if g is not None else ''} | {((a or {}).get('reference') or '')[:90]} |")
    if new:
        lines += ["", f"## New in the after runs ({len(new)}): recipes or lines the before runs did not process", "", "| dish | line | record |", "|---|---|---|"]
        lines += [f"| {v['dish']} | {v['line'][:70]} | {v['record'][:44]} |" for v in new]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
