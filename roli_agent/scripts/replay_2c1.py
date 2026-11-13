"""Phase 2C.1 controlled evaluation, step 2: before/after on frozen inputs.

Inputs: `roli_agent/eval/frozen_inputs_2c1.json` (recipes re-ingested offline, frozen USDA matching decisions per verbatim line, the
saved relevance outcomes) and the saved run `2b2_live_2026-11-02_2c_v2.json` (the BEFORE: the old code's published scenarios and
experimental adaptation on the same recipes). No Tavily, no page fetch, no LLM. USDA records are read live (deterministic data).

AFTER = the current code: parse -> convert (frozen decision per line) -> Phase 2A calculator (unchanged) -> adaptation in approved and
experimental mode. Variants: D24 observed at the D22 tolerance (5 %) and applied at a wider tolerance, reported separately.

    .venv/bin/python -m roli_agent.scripts.replay_2c1 [--d24-tolerance 0.15] [--tag _2026-11-03]

Writes `roli_agent/eval/2c1_controlled<tag>.json` and prints the comparison tables.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import ErrorResult, NutritionService, Settings
from roli_nutrition.recipe import RecipeCalculator

from roli_agent.config import ROOT
from roli_agent.recipes.adapt import WeightsTable, adapt_pairs
from roli_agent.recipes.completeness import CompleteRecordPolicy
from roli_agent.recipes.equivalence import EquivalentRecordPolicy
from roli_agent.recipes.match import MatchRequest
from roli_agent.recipes.models import MatchDecision, MenuItem, Relevance, Scenario, SourceRecipe
from roli_agent.recipes.pipeline import _build_scenario, _source_of
from roli_agent.recipes.relevance import gate


REFRESHED: dict[int, list[dict]] = {}


def with_candidates(dec: dict, service) -> MatchDecision:
    """A frozen decision from the older match cache carries no candidate list; D22/D24 may only choose from USDA's own list for the
    saved query, so the list is re-read from USDA (deterministic data, no model) and recorded as refreshed."""
    d = MatchDecision(**dec).model_copy(update={"source": "cache"})
    if not d.candidates and d.query and d.fdc_id is not None:
        if d.fdc_id not in REFRESHED:
            r = service.search_foods(d.query, 10)
            REFRESHED[d.fdc_id] = [] if isinstance(r, ErrorResult) else [{"fdc_id": c.fdc_id, "description": c.description, "data_type": c.data_type} for c in r.candidates]
        d = d.model_copy(update={"candidates": REFRESHED[d.fdc_id], "candidates_seen": len(REFRESHED[d.fdc_id])})
    return d


def decisions_for(recipe: SourceRecipe, frozen: dict[str, dict], menu_missing: list[str], service) -> tuple[dict[str, MatchDecision], list[str]]:
    """Frozen decisions re-keyed for the current parser. A line whose parsed name changed (typo units, 'garlic cloves') keeps its
    decision by verbatim line; the second part of a split compound line has none and is reported."""
    out, unmatched = {}, []
    for p in recipe.ingredients:
        dec = frozen.get(p.line)
        if dec is None or "compound_split:part_2_of_2" in p.flags:
            unmatched.append(p.line if dec is None else f"{p.line} [part 2: {p.name}]")
            continue
        out[MatchRequest(name=p.name, preparation_hint=p.preparation_hint).key] = with_candidates(dec, service)
    for w in menu_missing:
        dec = frozen.get(f"menu_only:{w}")
        if dec is not None:
            out[MatchRequest(name=w, preparation_hint="unknown").key] = with_candidates(dec, service)
    return out, unmatched


def line_key(l: dict) -> str:
    base = l["line"] or f"menu_only:{l['name']}"
    part = next((f for f in l.get("flags", []) if f.startswith("compound_split")), "")
    return f"{base}|{part}" if part else base


def line_state(l: dict) -> str:
    """One word per line: resolved, or the blocker category."""
    if l.get("excluded_from_calculation"):
        return "not_an_ingredient"
    return l["blocker"] or "resolved"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", default=str(ROOT / "roli_agent" / "eval" / "frozen_inputs_2c1.json"))
    parser.add_argument("--before", default=str(ROOT / "roli_agent" / "eval" / "2b2_live_2026-11-02_2c_v2.json"))
    parser.add_argument("--d24-tolerance", default="0.15")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    service = NutritionService(Settings.from_env())
    frozen = json.loads(Path(args.frozen).read_text(encoding="utf-8"))
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    table = WeightsTable.load()
    report = {"frozen_inputs": args.frozen, "before": args.before, "d24_tolerance_variant": args.d24_tolerance, "dishes": {}}
    totals = {"before": Counter(), "after": Counter(), f"after_d24_{args.d24_tolerance}": Counter()}
    completeness = {k: Counter() for k in totals}
    grams_changes, new_lines, gate_changes = [], [], []

    for dish, data in frozen["dishes"].items():
        item = MenuItem(**data["menu_item"])
        saved_est = before["cold"][dish]
        saved_by_id = {sc["scenario_id"]: sc for sc in saved_est["scenarios"]}
        recipes = [SourceRecipe(**{k: v for k, v in r.items() if not k.startswith("saved_")}) for r in data["recipes"]]
        saved_meta = {r["canonical_url"]: r for r in data["recipes"]}
        variants = {"after": CompleteRecordPolicy(service, enabled=False, observe=True, tolerance=Decimal("0.05")),
                    f"after_d24_{args.d24_tolerance}": CompleteRecordPolicy(service, enabled=True, tolerance=Decimal(args.d24_tolerance))}
        dish_out = {"scenarios": {}, "gate_now": {}}
        for r in recipes:
            meta = saved_meta[r.canonical_url]
            passed, reason = gate(item, r)
            if meta["saved_status"] and meta["saved_status"][0] == "calculated" and not passed:
                gate_changes.append((dish, r.title, reason))
            dish_out["gate_now"][r.canonical_url] = reason
            if not meta["saved_status"] or meta["saved_status"][0] != "calculated":
                continue
            saved_sc = saved_by_id[meta["saved_scenario_id"]]
            rel = Relevance(**meta["saved_relevance"])
            decisions, unmatched = decisions_for(r, data["frozen_decisions_by_line"], rel.menu_missing, service)
            new_lines.extend((dish, r.title, u) for u in unmatched)
            per_variant = {}
            for name, complete_policy in variants.items():
                s = Scenario(scenario_id=meta["saved_scenario_id"], source=_source_of(r), relevance=rel, status="not_processed")
                notes: list[str] = []
                complete_policy.log.clear()
                _build_scenario(s, r, decisions, service, {}, RecipeCalculator(service), notes, EquivalentRecordPolicy(service), complete_policy)
                notes.extend(f"D24 ({'applied' if e['applied'] else 'not applied: policy off'}): {e['line'][:60]!r}: {e['from']} -> {e['to']} (sat fat delta {e['delta']} g/100 g)"
                             for e in complete_policy.log if "to" in e)
                notes.extend(f"D24 rejected {e['rejected']} for {e['line'][:50]!r}: {e['why']}" for e in complete_policy.log if "rejected" in e and "delta" in e)
                pairs_a, summ_a = adapt_pairs([s], service=service, table=table, mode="approved")
                pairs_x, summ_x = adapt_pairs([s], service=service, table=table, mode="experimental")
                per_variant[name] = {"scenario": s.model_dump(mode="json"), "notes": notes,
                                     "approved": {"pairs": [p.model_dump(mode="json") for p in pairs_a], "summary": summ_a.model_dump(mode="json")},
                                     "experimental": {"pairs": [p.model_dump(mode="json") for p in pairs_x], "summary": summ_x.model_dump(mode="json")}}
            dish_out["scenarios"][meta["saved_scenario_id"]] = {"before": saved_sc, **per_variant}

            # line-level comparison: before (saved) vs after, matched by verbatim line
            before_lines = {line_key(l): l for l in saved_sc["ingredients"]}
            for l in saved_sc["ingredients"]:
                totals["before"][line_state(l)] += 1
            for name, v in per_variant.items():
                for l in v["scenario"]["ingredients"]:
                    key = line_key(l)
                    b = before_lines.get(key) or before_lines.get(key.split("|")[0])
                    state = line_state(l)
                    totals[name][state] += 1
                    if name == "after" and b is not None and "compound_split:part_2" not in key:
                        gb, ga = b["conversion"]["grams"], l["conversion"]["grams"]
                        if gb is not None and ga is not None and Decimal(str(gb)) != Decimal(str(ga)):
                            grams_changes.append((dish, r.title, key, gb, ga, l["conversion"]["reference"]))
                        if gb is not None and ga is None:
                            grams_changes.append((dish, r.title, key, gb, None, "LOST"))
                completeness[name][json.dumps(v["scenario"]["completeness_by_nutrient"], sort_keys=True)] += 1
                if name == "after":
                    completeness["before"][json.dumps(saved_sc["completeness_by_nutrient"], sort_keys=True)] += 1
        report["dishes"][dish] = dish_out

    # -- tables --------------------------------------------------------------------------------------------------
    print("\n=== LINE STATES, all calculated published scenarios (before = saved run; after = current code, frozen decisions) ===")
    states = sorted(set().union(*[set(c) for c in totals.values()]))
    print(f"{'state':32s}" + "".join(f"{k:>22s}" for k in totals))
    for st in states:
        print(f"{st:32s}" + "".join(f"{c[st]:>22d}" for c in totals.values()))
    print(f"{'TOTAL lines':32s}" + "".join(f"{sum(c.values()):>22d}" for c in totals.values()))
    print("\n=== PUBLISHED SCENARIO COMPLETENESS BY NUTRIENT (count of scenarios) ===")
    for k, c in completeness.items():
        print(f"  {k:22s} " + "; ".join(f"{json.loads(j)} x{n}" for j, n in sorted(c.items())))
    print("\n=== ADAPTATION (experimental / approved), after ===")
    for name in [k for k in totals if k != "before"]:
        for mode in ("approved", "experimental"):
            agg = Counter()
            for d in report["dishes"].values():
                for sc in d["scenarios"].values():
                    s = sc[name][mode]["summary"]
                    agg["pairs"] += s["n_pairs"]; agg["filled"] += s["n_lines_filled"]; agg["unfilled_in_pairs"] += s["n_unfilled_in_pairs"]
                    agg["unfilled_no_pair"] += s["n_unfilled_no_pair"]; agg["blocked"] += s["n_blocked_lines"]
                    agg["complete_low"] += s["n_complete_low"]; agg["complete_high"] += s["n_complete_high"]; agg["sat_only_high"] += s["n_saturated_fat_only_complete_high"]
                    agg["driven"] += s["n_assumption_driven"]
                    for g, n in s["filled_by_gap"].items(): agg[f"gap:{g}"] += n
                    for g, n in s["unfilled_by_reason"].items(): agg[f"unfilled:{g}"] += n
            print(f"  {name:22s} {mode:12s} " + ", ".join(f"{k}={v}" for k, v in sorted(agg.items())))
    print("\n=== GRAMS CHANGES on lines resolved before (quantity-error check) ===")
    for row in grams_changes:
        print("  ", row)
    print("   (none)" if not grams_changes else "")
    print("\n=== LINES WITHOUT A FROZEN DECISION (new parser output) ===")
    for row in new_lines:
        print("  ", row)
    print("\n=== GATE NOW REJECTS a scenario that was calculated before ===")
    for row in gate_changes:
        print("  ", row)
    print("\n=== D24 LOG (observe at 5 %; applied at the variant tolerance) ===")
    for dish, d in report["dishes"].items():
        for sid, sc in d["scenarios"].items():
            for name in [k for k in totals if k != "before"]:
                for n in sc[name]["notes"]:
                    if n.startswith("D24"):
                        print(f"  [{name}] {sid[:40]}: {n[:170]}")
    print("\n=== SCENARIOS COMPLETE OR SATURATED-FAT-ONLY COMPLETE AT THE HIGH BOUND (experimental) ===")
    for dish, d in report["dishes"].items():
        for sid, sc in d["scenarios"].items():
            for name in [k for k in totals if k != "before"]:
                for pr in sc[name]["experimental"]["pairs"]:
                    hi = pr["high"]
                    if hi["calculation_status"] == "complete" or hi["completeness_by_nutrient"].get("saturated_fat_g"):
                        disp = hi["calculation"]["display"]
                        print(f"  [{name}] {sid[:45]}: high {hi['calculation_status']} {hi['completeness_by_nutrient']} sat {disp['saturated_fat_g'][:28]} chol {disp['cholesterol_mg'][:24]} "
                              f"| low sat {pr['low']['calculation']['display']['saturated_fat_g'][:28]} | assumptions {[a['name'][:18] for a in pr['assumptions']]} | unfilled {[u['name'][:18] for u in pr['unfilled']]}")
    report["totals"] = {k: dict(v) for k, v in totals.items()}
    report["candidates_refreshed_for"] = sorted(REFRESHED)
    report["completeness"] = {k: dict(v) for k, v in completeness.items()}
    report["grams_changes"] = grams_changes
    report["lines_without_frozen_decision"] = new_lines
    report["gate_changes"] = gate_changes
    out = ROOT / "roli_agent" / "eval" / f"2c1_controlled{args.tag}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nwritten:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
