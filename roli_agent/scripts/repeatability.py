"""Pass A against pass B (SPEC_3_mvp.md 12.9.5): the same photos, the same code, straight after. Reports every difference and its cause.

    .venv/bin/python -m roli_agent.scripts.repeatability --a <run id> --b <run id> [--a ... --b ...] --label "Flour + Water" [...] --out roli_agent/eval/....md

Compared per menu: what the reader read, the recommendation text, the ranking with its figures, each dish's status and range, grades and tags, the recipes calculated, the flags.
The cause given for a difference comes from the two run.json files; nothing is recomputed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from roli_agent.config import ROOT

RUNS = ROOT / "roli_agent" / "runs"


def load(run_id: str) -> dict:
    return json.loads((RUNS / run_id / "run.json").read_text(encoding="utf-8"))


def clean(name: str) -> str:
    """Dish names are paired ignoring case, punctuation and accents the reader wrote differently ("salad*", "aillade")."""
    plain = name.lower().replace("ï", "i").replace("é", "e")
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def menu_items(r: dict) -> list[tuple]:
    return [(i.get("section", ""), i.get("name", ""), i.get("description", "")) for i in (r.get("menu") or {}).get("items", [])]


def dish_state(d: dict) -> tuple:
    iv = (d.get("intervals") or {}).get("saturated_fat_g") or {}
    ch = (d.get("intervals") or {}).get("cholesterol_mg") or {}
    return d["status"], iv.get("low"), iv.get("high"), ch.get("low"), ch.get("high"), iv.get("band_low"), iv.get("band_high")      # 3K: the band is part of the state


def tags_of(d: dict) -> dict[tuple, tuple]:
    out = {}
    for s in (d.get("estimate") or {}).get("scenarios", []):
        for l in s.get("ingredients", []):
            if l.get("tag_role"):
                out[(s["source"]["canonical_url"], l["ingredient_id"])] = (l["tag_role"], l["tag_kind"])
    return out


def grades_of(d: dict) -> dict[str, tuple]:
    out = {}
    for s in (d.get("estimate") or {}).get("scenarios", []):
        rel = s.get("relevance") or {}
        out[s["source"]["canonical_url"]] = (rel.get("grade"), rel.get("dish_type"), rel.get("preparation"), rel.get("course_portion"))
    return out


def calculated(d: dict) -> set[str]:
    return {s["source"]["canonical_url"] for s in (d.get("estimate") or {}).get("scenarios", []) if s.get("status") == "calculated"}


def matches_of(d: dict) -> dict[tuple, int | None]:
    out = {}
    for s in (d.get("estimate") or {}).get("scenarios", []):
        for l in s.get("ingredients", []):
            out[(s["source"]["canonical_url"], l["ingredient_id"])] = (l.get("match") or {}).get("fdc_id")
    return out


def cause(a: dict, b: dict) -> str:
    """Why one dish differs between the passes, from the first thing upstream that differs."""
    if a["item"] != b["item"]:
        fields = [f"{k}: {str(a['item'].get(k))[-40:]!r} vs {str(b['item'].get(k))[-40:]!r}" for k in ("name", "description", "section") if a["item"].get(k) != b["item"].get(k)]
        return "the menu reader wrote the item differently (" + "; ".join(fields) + ")"
    if a.get("selection", {}).get("decision") != b.get("selection", {}).get("decision"):
        return "selection differed"
    ga, gb = grades_of(a), grades_of(b)
    if set(ga) != set(gb):
        return f"different pages read: {sorted(set(ga) ^ set(gb))[:2]}"
    if ga != gb:
        k = next(u for u in ga if ga[u] != gb[u])
        return f"grade differed on {k}: {ga[k]} vs {gb[k]}"
    ta, tb = tags_of(a), tags_of(b)
    if ta != tb:
        k = next((u for u in sorted(set(ta) | set(tb)) if ta.get(u) != tb.get(u)))
        return f"tag differed on {k}: {ta.get(k)} vs {tb.get(k)}"
    ma, mb = matches_of(a), matches_of(b)
    if ma != mb:
        k = next((u for u in sorted(set(ma) | set(mb), key=str) if ma.get(u) != mb.get(u)))
        return f"USDA match differed on {k}: {ma.get(k)} vs {mb.get(k)}"
    if calculated(a) != calculated(b):
        return "different recipes calculated from the same pages and grades"
    return "no upstream difference found: unexplained"


def compare(label: str, a: dict, b: dict) -> tuple[list[str], list[str]]:
    key = lambda r: (clean(r["name"]), r["saturated_fat_low"], r["saturated_fat_high"], r["support"], r.get("band_low"), r.get("band_high"))
    row_a, row_b = [key(r) for r in a["ranking"]], [key(r) for r in b["ranking"]]
    da, db = {clean(d["item"]["name"]): d for d in a["dishes"]}, {clean(d["item"]["name"]): d for d in b["dishes"]}
    diffs: list[str] = []
    same_menu = menu_items(a) == menu_items(b)
    if not same_menu:
        ia, ib = set(menu_items(a)), set(menu_items(b))
        diffs.append(f"menu read differently: {len(ia - ib)} item(s) only in A, {len(ib - ia)} only in B; e.g. A {sorted(ia - ib)[:1]}, B {sorted(ib - ia)[:1]}")
    for name in sorted(set(da) | set(db)):
        x, y = da.get(name), db.get(name)
        if x is None or y is None:
            if (x or y)["status"] not in ("excluded", "not_evaluated"):
                diffs.append(f"{name[:50]}: only in {'B' if x is None else 'A'} ({(x or y)['status']}): the menu reader wrote it differently")
            continue
        pages = lambda d: ((d.get("estimate") or {}).get("ingestion") or {}).get("fetch_ok")
        if pages(x) != pages(y):
            diffs.append(f"{name[:50]}: pages loaded {pages(x)} vs {pages(y)}")
        if dish_state(x) != dish_state(y):
            diffs.append(f"{name[:50]}: {dish_state(x)[:3]} band {dish_state(x)[5:]} vs {dish_state(y)[:3]} band {dish_state(y)[5:]}: {cause(x, y)}")
        elif tags_of(x) != tags_of(y) or grades_of(x) != grades_of(y) or x["item"] != y["item"]:
            diffs.append(f"{name[:50]}: same figures; {cause(x, y)}")
    flags_a = [(f.get("dish"), f.get("comparison"), f.get("roli_middle")) for f in a.get("flags", [])]
    flags_b = [(f.get("dish"), f.get("comparison"), f.get("roli_middle")) for f in b.get("flags", [])]
    if [f for f in flags_a if f[1]] != [f for f in flags_b if f[1]]:
        diffs.append(f"open flags differ: {flags_a} vs {flags_b}")
    sa, sb = a.get("spend") or {}, b.get("spend") or {}
    u = lambda r: (r.get("usda") or {}).get("requests")
    row = (f"| {label} | {'same' if same_menu else 'different'} | {'same' if a['recommendation'] == b['recommendation'] else 'different'} | {'same' if row_a == row_b else 'different'} | {len(diffs)} | "
           f"{sa.get('model_calls')} / {sb.get('model_calls')} | {str(sa.get('model_usd_total'))[:6]} / {str(sb.get('model_usd_total'))[:6]} | {u(a)} / {u(b)} |")
    return [row], diffs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", action="append", required=True)
    ap.add_argument("--b", action="append", required=True)
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--intro", default="The same photos, the same code, pass B straight after pass A.")
    args = ap.parse_args()
    lines = ["# Repeatability: pass A against pass B", "", args.intro, "",
             "| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |", "|---|---|---|---|---|---|---|---|"]
    details: list[str] = []
    for i, (x, y) in enumerate(zip(args.a, args.b)):
        label = args.label[i] if i < len(args.label) else x
        a, b = load(x), load(y)
        row, diffs = compare(label, a, b)
        lines += row
        details += ["", f"## {label} ({x} vs {y})", ""] + ([f"- {d}" for d in diffs] or ["No differences."])
        if a["recommendation"] != b["recommendation"]:
            details += ["", f"A: {a['recommendation']}", "", f"B: {b['recommendation']}"]
    Path(args.out).write_text("\n".join(lines + details) + "\n", encoding="utf-8")
    print("\n".join(lines + details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
