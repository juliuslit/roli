"""Reader prompts side by side (SPEC_3_mvp.md 12.12.3): reads two `results/full_*` folders written by `code/full_run.py`; no model calls, nothing recomputed.

    .venv/bin/python -m roli_agent.scripts.reader_compare --a results/full_..._v5_t0 --b results/full_..._v6_t0 --out results/reader_v5_v6_<date>.md

Every pass bar of `menu_reader_eval/scoring_rules.md`, invented first, compared at the precision the harness prints, with the verdict of the rule "no worse on any pass bar";
then the photos whose scores moved, and what each prompt did on a chosen photo (default 23, the seafood chalkboard).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load(folder: Path) -> dict:
    return json.loads((folder / "summary.json").read_text(encoding="utf-8"))


def scores(folder: Path) -> dict[tuple[str, int], dict]:
    return {(p.stem.split("_")[1], int(p.parent.name[3:])): json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("run*/menu_*_scores.json")}


def pct(x) -> float:
    return round(100 * (x or 0), 1)


def caught(v: dict) -> dict:
    return {r: int(c.split("/")[0]) for r, c in v["partly_caught_by_run"].items()}


# (bar, how to read it from a verdict, True when a higher figure is better)
def bars(v: dict) -> list[tuple[str, object, bool]]:
    by_run = lambda d: [d[k] for k in sorted(d)]
    return [("2 invented, run 1", by_run(v["invented_total_by_run"])[0], False), ("2 invented, run 2", by_run(v["invented_total_by_run"])[1], False),
            ("1 dishes found, average %", pct(v["dishes_found_avg"]), True), ("1 worst photo found %", round(100 * v["dishes_found_min_photo"]), True),
            ("2b cut-off lines listed, run 1", by_run(v["cut_off_listed_by_run"])[0], False), ("2b cut-off lines listed, run 2", by_run(v["cut_off_listed_by_run"])[1], False),
            ("3 prices %", pct(v["prices_right_avg"]), True), ("4 descriptions %", pct(v["descriptions_right_avg"]), True), ("6 format %", pct(v["format_right_avg"]), True),
            ("7 partly photos caught of 7, run 1", by_run(caught(v))[0], True), ("7 partly photos caught of 7, run 2", by_run(caught(v))[1], True),
            ("7 false alarms, run 1", by_run(v["false_alarms_by_run"])[0], False), ("7 false alarms, run 2", by_run(v["false_alarms_by_run"])[1], False),
            ("8 speed, seconds per photo", round(v["seconds_avg"]), False)]


def items(folder: Path, photo: str, run: int) -> list[dict]:
    raw = (folder / f"run{run}" / f"menu_{photo}_raw.txt").read_text(encoding="utf-8")
    return json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M))["items"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--photo", default="23")
    args = ap.parse_args()
    fa, fb = Path(args.a), Path(args.b)
    sa, sb = load(fa), load(fb)
    va, vb = sa["as_written"], sb["as_written"]
    a_name, b_name = sa["prompt_version"], sb["prompt_version"]
    lines = [f"# Reader {a_name} against {b_name}", "", f"Model {sa['model']}, temperature {sa['temperature']}, 25 photos each sent twice, `{sa['rules']}`. Folders: `{fa.name}`, `{fb.name}`.", "",
             f"| pass bar | {a_name} | {b_name} | {b_name} is |", "|---|---|---|---|"]
    worse = []
    for (bar, x, higher), (_, y, _h) in zip(bars(va), bars(vb)):
        verdict = "same" if x == y else "better" if (y > x) == higher else "worse"
        if verdict == "worse":
            worse.append(bar)
        lines.append(f"| {bar} | {x} | {y} | {verdict} |")
    lines += ["", f"Passes every bar: {a_name} {va['passes']}, {b_name} {vb['passes']}. Reported, no bar: garbled {va['garbled_total']} / {vb['garbled_total']}, fenced {va['fenced_total']} / {vb['fenced_total']}, "
              f"cost ${va['cost_total_usd']:.2f} / ${vb['cost_total_usd']:.2f} per 50 answers.", "",
              f"**Rule, no worse on any pass bar: {'met' if not worse else 'not met; worse on ' + '; '.join(worse)}.**", "", "## Photos whose scores moved", "",
              f"| photo | run | found {a_name} | found {b_name} | invented {a_name} | invented {b_name} | only missed by {b_name} | only invented by {b_name} |", "|---|---|---|---|---|---|---|---|"]
    ca, cb = scores(fa), scores(fb)
    for key in sorted(ca):
        x, y = ca[key], cb.get(key)
        if y is None or (x["found_items"], x["invented"]) == (y["found_items"], y["invented"]):
            continue
        lines.append(f"| {key[0]} | {key[1]} | {x['found_items']}/{x['expected_items']} | {y['found_items']}/{y['expected_items']} | {x['invented']} | {y['invented']} | "
                     f"{'; '.join(n for n in y['unmatched_expected_names'] if n not in x['unmatched_expected_names'])[:90]} | {'; '.join(n for n in y['invented_names'] if n not in x['invented_names'])[:90]} |")
    lines += ["", f"## Photo {args.photo}: where each prompt put the lines", ""]
    for name, folder in ((a_name, fa), (b_name, fb)):
        for run in (1, 2):
            lines += [f"{name} run {run}:", ""] + [f"- {i['name']}" + (f": {i['description']}" if i.get("description") else "") for i in items(folder, args.photo, run)] + [""]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
