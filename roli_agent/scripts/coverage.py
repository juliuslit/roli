"""Coverage (SPEC_3_mvp.md 12.14.13): the share of a menu's food dishes that are ranked, and every other dish by cause, read from saved runs. Nothing is recomputed.

    .venv/bin/python -m roli_agent.scripts.coverage --runs <run id> [...] [--label ...] --out roli_agent/eval/coverage_....md

A food dish is any menu item but the ones selection set aside as not a dish (drinks, add-ons, notes). A dish is `ranked` when it is in the ranking (a light snack counts, and is shown apart). Every other dish gets one cause.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from roli_agent.config import ROOT

SIDE = re.compile(r"\b(sides?|extras?|add[- ]ons?)\b", re.I)


def load(run_id: str) -> dict:
    return json.loads((ROOT / "roli_agent" / "runs" / run_id / "run.json").read_text(encoding="utf-8"))


def line_cause(reason: str) -> str:
    """What holds an unbounded dish, from the reason a tester reads."""
    kinds = []
    for word, label in (("missing_grams", "a line with no weight"), ("nutrient_not_reported", "a nutrient USDA does not report"), ("preparation_unresolved", "a raw or cooked state not resolved"),
                        ("missing_fdc_id", "a line with no USDA record")):
        if word in reason:
            kinds.append(label)
    return ", ".join(kinds) or "other line"


def cause_of(d: dict, unranked: dict[str, str], ranked: set[str]) -> tuple[str, str]:
    """(group, cause)"""
    status, key = d["status"], d["key"]
    if key in ranked:
        return "ranked", "ranked"
    if status == "flagged":
        return "not ranked", "known limit of the data" if (d.get("reference") or {}).get("known_limit") else "flagged: disagrees with published figures"
    if status == "evaluated":
        reason = unranked.get(key, d.get("reason") or "")
        if "could be portioned" in reason:
            return "not ranked", "no recipe could be portioned"
        if "no upper bound" in reason:
            return "not ranked", f"no upper bound: {line_cause(reason)}"
        return "not ranked", reason[:60] or "evaluated, not ranked"
    if status == "no_recipes":
        return "not ranked", "no usable recipe found"
    if status == "skipped":
        return "not tried", "a spending limit" if "before it started" in (d.get("reason") or "") else "the dish cap"     # 12.18: the cap is a config value (30)
    if status == "budget_stopped":
        return "not tried", "a spending limit"
    if status in ("error", "usda_unavailable"):
        return "not ranked", status
    item = d["item"]
    reason = (d.get("selection") or {}).get("reason") or d.get("reason") or ""
    text = f"{item.get('name', '')} {item.get('section', '')}".lower()
    if "12.16.8" in reason:                                           # 3I: the kind has a family but its rows are unsourced
        return "outside what Roli ranks", "no measured plate size: the family's rows are unsourced (12.16.8)"
    if "no portion rule" in reason:
        return "outside what Roli ranks", "no portion rule for this kind of item"
    if "option of another item" in reason:
        return "outside what Roli ranks", "an option of another item"
    if "dish-kind call" in reason:
        return "outside what Roli ranks", "the dish-kind call read it as not a dish"
    if re.search(r"\b(burger|sandwich|sandwiches|panini|wrap|toastie|toasties|sub|hot dog|taco|tacos|burrito|quesadilla)\b", text):
        return "outside what Roli ranks", "sandwich, burger, wrap or taco: no portion rule"
    if re.search(r"\b(dessert|desserts|sweets?|pudding|cake|ice cream)\b", text):
        return "outside what Roli ranks", "dessert"
    if re.search(r"\bbreakfast\b", text):
        return "outside what Roli ranks", "breakfast section"
    if SIDE.search(text):
        return "outside what Roli ranks", "side or extra"
    if re.search(r"\b(kids?|children|ni[nñ]os)\b", text):
        return "outside what Roli ranks", "children's menu"
    if "no portion rule" in reason:
        return "outside what Roli ranks", "no portion rule for this kind of item"
    return "outside what Roli ranks", f"other: {reason[:44]}" if reason else "other"


def study(run_id: str, label: str) -> dict:
    r = load(run_id)
    ranked = {x["key"] for x in r["ranking"]}
    unranked = {u["key"]: u["reason"] for u in r["unranked"]}
    rows = []
    for d in r["dishes"]:
        if ((d.get("selection") or {}).get("reason") or d.get("reason") or "").startswith("excluded: not a dish"):
            continue
        group, cause = cause_of(d, unranked, ranked)
        rows.append({"name": d["item"]["name"], "section": d["item"].get("section", ""), "type": d.get("dish_type"), "group": group, "cause": cause})
    import statistics
    ratios, bands, topups, aside = [], [], 0, 0
    for d in r["dishes"]:
        iv = (d.get("intervals") or {}).get("saturated_fat_g") or {}
        if iv.get("high") and iv.get("low") and float(iv["low"]) > 0:
            ratios.append(float(iv["high"]) / float(iv["low"]))
            if iv.get("band_low") and float(iv["band_low"]) > 0:
                bands.append(float(iv["band_high"]) / float(iv["band_low"]))
            if iv.get("set_aside"):
                aside += 1
        if (d.get("estimate") or {}).get("topup", {}).get("query"):
            topups += 1
    width = {"extremes_median": round(statistics.median(ratios), 1) if ratios else None, "band_median": round(statistics.median(bands), 1) if bands else None, "topups": topups, "set_aside": aside}   # 3K
    return {"run": run_id, "label": label, "rows": rows, "ranking": r["ranking"], "unranked": r["unranked"], "recommendation": r["recommendation"], "spend": r.get("spend") or {}, "usda": r.get("usda") or {},
            "menu_read": len((r.get("menu") or {}).get("items", [])), "status": r["status"], "width": width}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--intro", default="")
    args = ap.parse_args()
    menus = [study(r, args.label[i] if i < len(args.label) else r) for i, r in enumerate(args.runs)]
    lines = ["# Coverage", ""] + ([args.intro, ""] if args.intro else [])
    lines += ["| menu | food dishes | ranked | share | tried, not ranked | not tried | outside what Roli ranks | model $ | credits | USDA requests |", "|---|---|---|---|---|---|---|---|---|---|"]
    total = Counter()
    causes: Counter = Counter()
    where: dict[str, set] = defaultdict(set)
    for m in menus:
        c = Counter(x["group"] for x in m["rows"])
        n = len(m["rows"])
        total.update(c)
        total["all"] += n
        for x in m["rows"]:
            if x["group"] != "ranked":
                causes[(x["group"], x["cause"])] += 1
                where[(x["group"], x["cause"])].add(m["label"])
        lines.append(f"| {m['label']} | {n} | {c['ranked']} | {100 * c['ranked'] / n if n else 0:.0f} % | {c['not ranked']} | {c['not tried']} | {c['outside what Roli ranks']} | {str(m['spend'].get('model_usd_total'))[:6]} | {m['spend'].get('search_credits')} | {m['usda'].get('requests')} |")
    n = total["all"]
    lines.append(f"| **all** | {n} | {total['ranked']} | {100 * total['ranked'] / n if n else 0:.0f} % | {total['not ranked']} | {total['not tried']} | {total['outside what Roli ranks']} | | | |")
    lines += ["", "## Causes, by dishes affected", "", "| group | cause | dishes | menus |", "|---|---|---|---|"]
    lines += [f"| {g} | {c} | {k} | {len(where[(g, c)])} |" for (g, c), k in causes.most_common()]
    lines += ["", "## What a tester sees, per menu", ""]
    for m in menus:
        lines += [f"### {m['label']} ({m['run']})", "", m["recommendation"], ""]
        if m["unranked"]:
            lines += ["Could not be ranked:", ""] + [f"- {u['name'][:70]}: {u['reason'][:150]}" for u in m["unranked"]] + [""]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:len(menus) + 8 + (2 if args.intro else 0)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
