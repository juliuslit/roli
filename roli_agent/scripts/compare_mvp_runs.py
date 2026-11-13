"""Before/after comparison of saved menu runs (local-testing milestone, 2026-11-04).

    .venv/bin/python -m roli_agent.scripts.compare_mvp_runs --before 20261104-010950-f71751 --after <run id> [--before ... --after ...] [--out roli_agent/eval/mvp_before_after.md]

Pairs the i-th --before with the i-th --after. For each pair: totals side by side, the top three, the recommendation text, every dish whose status
or boundedness changed, with a reading of WHY it changed: a code fix (a line that was open is now filled by a named weights row, a bacon line
that was unresolved is now raw, a seasoning line now bounded), selection (the dish was or was not tried), or the recipes themselves differing
(search results, cache) which is variability, not improvement. Everything comes from the two run.json files; nothing is recomputed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from roli_agent.config import ROOT

RUNS = ROOT / "roli_agent" / "runs"
NEW_ROWS = {"W29", "W30", "W31", "W32", "W33", "W34", "W35", "W36", "W37", "W38", "W39", "W40", "W56"}


def load(run_id: str) -> dict:
    return json.loads((RUNS / run_id / "run.json").read_text(encoding="utf-8"))


def by_name(run: dict) -> dict[str, dict]:
    return {d["item"]["name"].strip().lower(): d for d in run["dishes"]}


def bounded(d: dict) -> bool | None:
    iv = (d.get("intervals") or {}).get("saturated_fat_g")
    return None if iv is None else bool(iv.get("bounded"))


def recipes_of(d: dict) -> set[str]:
    est = d.get("estimate") or {}
    return {s["scenario_id"] for s in est.get("scenarios", []) if s.get("status") == "calculated"}


def judged(d: dict) -> dict[str, tuple]:
    """Page -> the grader's answer for this dish in this run, for every page it graded (12.9.5)."""
    est = d.get("estimate") or {}
    out = {}
    for s in est.get("scenarios", []):
        rel = s.get("relevance") or {}
        if rel.get("grade") not in (None, "ungraded"):
            out[s["source"]["canonical_url"]] = (rel.get("grade"), rel.get("dish_type"), rel.get("preparation"), rel.get("course_portion"), rel.get("hard_exclusion"))
    return out


def pages_read(d: dict) -> set[str]:
    return {s["source"]["canonical_url"] for s in (d.get("estimate") or {}).get("scenarios", [])}


def rows_used(d: dict) -> set[str]:
    est = d.get("estimate") or {}
    return {a.get("row_id") for p in est.get("adapted_pairs", []) for a in p.get("assumptions", []) if a.get("row_id")}


def unfilled_of(d: dict) -> set[str]:
    est = d.get("estimate") or {}
    return {u["name"] for p in est.get("adapted_pairs", []) for u in p.get("unfilled", [])}


def bacon_fixed(d: dict) -> bool:
    est = d.get("estimate") or {}
    for s in est.get("scenarios", []):
        for l in s.get("ingredients", []):
            desc = ((l.get("match") or {}).get("description") or "").lower()
            if "unprepared" in desc and l.get("preparation_state") == "raw":
                return True
    return False


def why_changed(b: dict | None, a: dict | None) -> str:
    if b is None:
        return "new on the after run (menu read differently or newly selected)"
    if a is None:
        return "absent from the after run (menu read differently)"
    if b["status"] != a["status"] and a["status"] in ("skipped", "excluded", "not_evaluated") or b["status"] in ("skipped", "not_evaluated", "excluded") and a["status"] == "evaluated":
        return f"selection: {b['status']} -> {a['status']}"
    if a["status"] == "budget_stopped":
        return "budget: stopped by a spending limit"
    if a["status"] == "error" or b["status"] == "error":
        return f"error path: {(a.get('reason') or b.get('reason') or '')[:80]}"
    rb, ra = recipes_of(b), recipes_of(a)
    same_recipes = rb == ra
    reasons = []
    if b["status"] != a["status"] and "flagged" in (b["status"], a["status"]):
        reasons.append(f"reference check: {b['status']} -> {a['status']}")
    gained = rows_used(a) - rows_used(b)
    if gained & NEW_ROWS:
        reasons.append(f"code fix: new weights row(s) {sorted(gained & NEW_ROWS)} filled lines that were open")
    if bacon_fixed(a) and not bacon_fixed(b):
        reasons.append("code fix: an 'unprepared' bacon/pancetta record is now a raw record")
    closed = unfilled_of(b) - unfilled_of(a)
    if closed and not (gained & NEW_ROWS):
        reasons.append(f"lines no longer open: {sorted(closed)[:4]}")
    if not same_recipes:
        jb, ja = judged(b), judged(a)
        changed = sorted(u for u in set(jb) & set(ja) if jb[u] != ja[u])
        if changed:
            first = changed[0]
            others = [f"{n} {x} -> {y}" for n, x, y in zip(("preparation", "course portion", "hard exclusion"), jb[first][2:], ja[first][2:]) if x != y]
            reasons.append(f"grading changed on {len(changed)} page(s), e.g. {first.split('/')[2]}: {jb[first][1]}/{jb[first][0]} -> {ja[first][1]}/{ja[first][0]}" + (f" ({'; '.join(others)})" if others else ""))
        if pages_read(b) != pages_read(a):
            reasons.append(f"different recipes calculated ({len(rb)} before, {len(ra)} after, {len(rb & ra)} shared): search results or cache, not a code change")
        elif not changed:
            reasons.append(f"different recipes calculated from the same pages ({len(rb)} before, {len(ra)} after, {len(rb & ra)} shared): a code change decided which were processed")
    return "; ".join(reasons) or ("same recipes, same rows: model variability in grading or matching" if bounded(b) != bounded(a) else "no material change")


def totals_table(pairs: list[tuple[str, dict, dict]]) -> list[str]:
    keys = [("menu items", "dishes_on_menu"), ("candidates", "dishes_candidates"), ("selected", "dishes_selected"), ("evaluated", "dishes_evaluated"), ("ranked", "dishes_ranked"),
            ("unranked", "dishes_unranked"), ("no recipes", "dishes_no_recipes"), ("errors", "dishes_error"), ("skipped", "dishes_skipped"), ("budget-stopped", "dishes_budget_stopped"),
            ("flagged", "dishes_flagged"), ("known limit", "dishes_known_limit"), ("USDA-unavailable", "dishes_usda_unavailable"),
            ("search credits", "search_credits"), ("model calls", "llm_calls"), ("USDA requests", "usda_http_requests"), ("rate-limit waits", "rate_limit_waits")]
    out = ["| menu | run | " + " | ".join(k for k, _ in keys) + " | USDA left after | model $ | total s | words |", "|---|---|" + "---|" * (len(keys) + 4)]
    for label, b, a in pairs:
        for tag, r in (("before", b), ("after", a)):
            t = r["totals"]
            cost = (r.get("spend") or {}).get("model_usd_total") or str(t.get("llm_cost_usd", ""))
            left = (r.get("usda") or {}).get("remaining_after", "")
            out.append(f"| {label} | {tag} {r['run_id']} | " + " | ".join(str(t.get(k, "")) for _, k in keys) + f" | {left} | {str(cost)[:6]} | {r['timings'].get('total')} | {r.get('recommendation_words')} |")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--before", action="append", required=True)
    p.add_argument("--after", action="append", required=True)
    p.add_argument("--label", action="append", default=None)
    p.add_argument("--out", default=str(ROOT / "roli_agent" / "eval" / "mvp_before_after_2026-11-04.md"))
    args, _ = p.parse_known_args()
    if len(args.before) != len(args.after):
        print("give the same number of --before and --after run ids")
        return 2
    pairs = []
    for i, (b, a) in enumerate(zip(args.before, args.after)):
        rb, ra = load(b), load(a)
        label = (args.label or [])[i] if args.label and i < len(args.label) else Path(ra.get("photo") or "").name
        pairs.append((label, rb, ra))
    p.add_argument("--title", default="MVP before/after")
    p.add_argument("--intro", default="Before and after: the same photos through the code of each checkpoint.")
    args = p.parse_args()
    lines = [f"# {args.title}", "", args.intro, ""]
    lines += totals_table(pairs)
    for label, b, a in pairs:
        lines += ["", f"## {label}", "", "**Before:** " + b["recommendation"], "", "**After:** " + a["recommendation"], ""]
        lines += ["| | before | after |", "|---|---|---|"]
        for k in range(3):
            rb = b["ranking"][k] if k < len(b["ranking"]) else None
            ra = a["ranking"][k] if k < len(a["ranking"]) else None
            f = lambda r: "" if r is None else f"{r['name'][:40]}: sat {float(r['saturated_fat_low']):.1f}-{float(r['saturated_fat_high']):.1f} g, chol {float(r['cholesterol_low']):.0f}-{float(r['cholesterol_high']):.0f} mg ({r['support']}{', driver ' + r['cholesterol_driver'] if r.get('cholesterol_driver') else ''})" if r.get("cholesterol_high") is not None else f"{r['name'][:40]}: sat {float(r['saturated_fat_low']):.1f}-{float(r['saturated_fat_high']):.1f} g ({r['support']})"
            lines.append(f"| #{k + 1} | {f(rb)} | {f(ra)} |")
        nb, na = by_name(b), by_name(a)
        lines += ["", "| dish | before | after | why |", "|---|---|---|---|"]
        for name in sorted(set(nb) | set(na), key=lambda n: (nb.get(n) or na.get(n))["menu_index"]):
            db, da = nb.get(name), na.get(name)
            sb = "" if db is None else db["status"] + ("" if bounded(db) is None else (" bounded" if bounded(db) else " unbounded"))
            sa = "" if da is None else da["status"] + ("" if bounded(da) is None else (" bounded" if bounded(da) else " unbounded"))
            if sb == sa and (db is None or da is None or recipes_of(db) == recipes_of(da)):
                continue
            if (db or da)["status"] in ("excluded", "not_evaluated") and (da or db)["status"] in ("excluded", "not_evaluated"):
                continue
            lines.append(f"| {(db or da)['item']['name'][:45]} | {sb} | {sa} | {why_changed(db, da)} |")
        unr = {u["name"]: u["reason"] for u in a.get("unranked", [])}
        if unr:
            lines += ["", "Unranked after, with reasons:"] + [f"- {n}: {r[:170]}" for n, r in unr.items()]
        if (a.get("spend") or {}).get("interruptions"):
            lines += ["", "Budget interruptions after: " + "; ".join(a["spend"]["interruptions"])]
        flags = a.get("flags") or []
        if flags:
            lines += ["", "Flags after:"]
            for f in flags:
                if f["status"] == "closed":
                    lines.append(f"- closed: {f['dish']} ({f.get('card')}): {f.get('note')}")
                else:
                    top = "; ".join(f"{t['line'][:50]} {t['sat_fat_g']} g ({t['share_of_middle']})" for t in f.get("top_contributors", []))
                    lines.append(f"- {f['status'].replace('_', ' ')}: {f['dish']} ({f.get('card')}, {f.get('comparison')}; Roli's middle {f.get('roli_middle')} vs published {f.get('published_low')}-{f.get('published_high')}; top contributors: {top})")
        checks = [(d["item"]["name"], d["reference"]) for d in a["dishes"] if (d.get("reference") or {}).get("comparisons")]
        if checks:
            lines += ["", "Reference checks after:"]
            for name, c in checks:
                lines.append(f"- {name[:45]} ({c.get('card_id')}): {'flagged' if c.get('flagged') else 'no failing check'}")
                for x in c["comparisons"]:
                    state = ("FAILED " + x["direction"]) if x.get("failed") else ("passed" if x.get("checked") else "shown only")
                    lines.append(f"  - {x['basis']}{' (' + x['choice'] + ')' if x.get('choice') else ''}: Roli's middle {x.get('roli_middle')} vs published {x.get('published_low')}-{x.get('published_high')}, {x.get('independent_figures')} independent; {state}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\nwritten:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
