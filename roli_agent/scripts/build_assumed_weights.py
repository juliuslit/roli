"""3K (SPEC_3_mvp.md 12.20): assumed-weight ranges built from the recipes Roli has already read, the way the plate-size table was built from MenuStat.

    .venv/bin/python -m roli_agent.scripts.build_assumed_weights [--date YYYY-MM-DD] [--cache <roli/.cache/roli_mvp>]

For every stored recipe extraction (ingredient lines as the page printed them), the lines whose amount the text itself states in grams, or in a weight the converter
reads without USDA (explicit g/oz/lb, an embedded weight in brackets, a water-like liquid at 1 g per ml), are divided by the recipe's serving count and filed under the
assumed-weights row their name matches (`adapt.WeightsTable.find`) and the dish family the recipe's title names (`portions.dish_type_for`). Lines a saved tag calls a
cooking medium or removed are skipped, as are the clinging-medium row W09 and per-count rows. The 10th-90th percentile per (row, family) and per (row, any family), with
the recipe count and up to twelve source URLs, go to `recipes/assumed_weights_data.csv`; `eval/assumed_weights_data_<date>.md` shows each hand range beside the data.
No network, no model call; every figure is a number a recipe writer printed, read by code.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from roli_agent.config import ROOT
from roli_agent.recipes.adapt import DATA_MIN_ANY, DATA_MIN_FAMILY, DataRange, WeightsTable
from roli_agent.recipes.convert import apply_embedded_weight, convert_weight
from roli_agent.recipes.ingest import content_hash
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.parse import parse_line, parse_servings
from roli_agent.recipes.portions import dish_type_for, unit_count_from_text

OUT = ROOT / "roli_agent" / "recipes" / "assumed_weights_data.csv"
EVAL = ROOT / "roli_agent" / "eval"
SKIP_ROWS = {"W09"}
MIN_FAMILY, MIN_ANY = DATA_MIN_FAMILY, DATA_MIN_ANY   # 12.20: recipes needed before a data range replaces the hand row (family level / any family); the table's guards decide
UNIT_FAMILIES = {"pizza_neapolitan"}            # a plate is one whole unit: divide by the recipe's unit count, not its serving (slice) count
COLUMNS = ["row_id", "dish_family", "n_lines", "n_recipes", "p10_g", "p50_g", "p90_g", "min_g", "max_g", "n_density", "n_embedded", "n_range_midpoint", "sources", "built_on", "review_status"]


def pct(values: list[Decimal], q: Decimal) -> Decimal:
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(v) - 1)
    return (v[lo] + (v[hi] - v[lo]) * (pos - lo)).quantize(Decimal("0.1"))


def saved_tags(cache: Path) -> dict[str, dict[str, str]]:
    """{url: {line number: role}} from every saved tag answer, whatever its prompt version (a cooking medium is a cooking medium under every prompt so far)."""
    out: dict[str, dict[str, str]] = {}
    for f in (cache / "judgements" / "tags").glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        ans = d.get("answer") or {}
        roles = {n: (t.get("role") or "") for n, t in ans.items() if isinstance(t, dict)}
        if d.get("url"):
            out.setdefault(d["url"], {}).update(roles)
    return out


def build(cache: Path, table: WeightsTable, today: str) -> tuple[list[dict], dict]:
    tags = saved_tags(cache)
    groups: dict[tuple[str, str], list[tuple[str, Decimal, list[str]]]] = defaultdict(list)
    seen_hashes: set[str] = set()
    stats = {"files": 0, "with_lines": 0, "distinct": 0, "with_servings": 0, "lines": 0, "weighed": 0, "medium_skipped": 0, "filed": 0}
    for f in sorted((cache / "extractions").glob("*.json")):
        stats["files"] += 1
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        ex = d.get("extracted") or {}
        lines = ex.get("ingredient_lines") or []
        if not lines:
            continue
        stats["with_lines"] += 1
        h = content_hash(lines)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        stats["distinct"] += 1
        servings = parse_servings(ex.get("yield_text") or "")[0]
        if not servings or servings <= 0:
            continue
        stats["with_servings"] += 1
        url = d.get("url") or ""
        family = dish_type_for(MenuItem(name=ex.get("title") or "", description="", section="")) or "any"
        if family in UNIT_FAMILIES:                                     # one plate is one pizza: the amount per unit, not per slice
            units = unit_count_from_text(ex.get("yield_text") or "", ex.get("instructions_text") or "")
            servings = Decimal(units["k"]) if units.get("k") else Decimal(1)
        roles = tags.get(url, {})
        for n, line in enumerate(lines, start=1):
            stats["lines"] += 1
            if roles.get(str(n)) in ("cooking_medium", "removed"):
                stats["medium_skipped"] += 1
                continue
            try:
                p = apply_embedded_weight(convert_weight(parse_line(line)))
            except Exception:  # noqa: BLE001
                continue
            if p.grams is None or p.grams <= 0:
                continue
            stats["weighed"] += 1
            row = table.find(p.name, family if family != "any" else None) or table.find(p.name, None)
            if row is None or row.id in SKIP_ROWS or row.amount_basis != "per_plate":
                continue
            per_serving = (p.grams / servings).quantize(Decimal("0.01"))
            flags = [x for x in p.flags if x in ("density_assumed_1", "embedded_weight", "range_midpoint", "embedded_weight_total_assumed")]
            groups[(row.id, family)].append((url, per_serving, flags))
            if family != "any":
                groups[(row.id, "any")].append((url, per_serving, flags))
            stats["filed"] += 1
    rows = []
    for (rid, fam), entries in sorted(groups.items()):
        urls = sorted({u for u, _, _ in entries})
        vals = [g for _, g, _ in entries]
        rows.append({"row_id": rid, "dish_family": fam, "n_lines": len(entries), "n_recipes": len(urls), "p10_g": str(pct(vals, Decimal("0.1"))), "p50_g": str(pct(vals, Decimal("0.5"))),
                     "p90_g": str(pct(vals, Decimal("0.9"))), "min_g": str(min(vals)), "max_g": str(max(vals)), "n_density": sum(1 for _, _, fl in entries if "density_assumed_1" in fl),
                     "n_embedded": sum(1 for _, _, fl in entries if any(x.startswith("embedded_weight") for x in fl)), "n_range_midpoint": sum(1 for _, _, fl in entries if "range_midpoint" in fl),
                     "sources": " ".join(urls[:12]), "built_on": today, "review_status": "built_from_recipes"})
    return rows, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()))
    ap.add_argument("--cache", default=str(ROOT / ".cache" / "roli_mvp"))
    args = ap.parse_args()
    table = WeightsTable.load(use_data=False)
    rows, stats = build(Path(args.cache), table, args.date)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    hand = {r.id: r for r in table.rows}
    L = [f"# Assumed weights built from recipe data, {args.date}", "",
         f"Stored extractions: {stats['files']} files, {stats['with_lines']} with ingredient lines, {stats['distinct']} distinct recipes, {stats['with_servings']} with a serving count; "
         f"{stats['lines']} lines read, {stats['weighed']} with a weight stated in the text (explicit grams, an embedded weight, or a water-like liquid at 1 g per ml), "
         f"{stats['medium_skipped']} skipped as cooking medium or removed by a saved tag, {stats['filed']} filed under a weights row. Per-serving grams = the line's grams / the recipe's serving count.",
         f"A data range replaces the hand row at run time when it rests on at least {MIN_FAMILY} recipes of the dish family, or {MIN_ANY} recipes across families (12.20), its spread (p90 / p10) is under 20x and "
         f"its median lies within 4x of the hand row's range (`adapt.WeightsTable.data_usable`); otherwise the hand row stands and the last column says why. Pizza recipes are divided by their unit count (one plate is one pizza), other recipes by their serving count.", "",
         "| row | hand range g | family | recipes | lines | p10-p90 g (data) | median | min-max | density lines | embedded | live? |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["row_id"], r["dish_family"] != "any", r["dish_family"])):
        h = hand.get(r["row_id"])
        d = DataRange(r)
        if h is None:
            live, why = False, "no hand row"
        elif r["dish_family"] == "any":
            live, why = WeightsTable.data_usable(h, d, MIN_ANY) if not h.dish_types else (False, "hand row limited to dish types")
        else:
            live, why = WeightsTable.data_usable(h, d, MIN_FAMILY)
        L.append(f"| {r['row_id']} {h.role[:28] if h else ''} | {h.low if h else ''}-{h.high if h else ''} | {r['dish_family']} | {r['n_recipes']} | {r['n_lines']} | {r['p10_g']}-{r['p90_g']} | {r['p50_g']} | {r['min_g']}-{r['max_g']} | {r['n_density']} | {r['n_embedded']} | {'yes' if live else why} |")
    out = EVAL / f"assumed_weights_data_{args.date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:8]))
    print(f"rows written: {len(rows)}; live at run time: {sum(1 for l in L if l.endswith('| yes |'))}; {OUT}; {out}")
    print("\n".join(l for l in L if l.endswith("| yes |")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
