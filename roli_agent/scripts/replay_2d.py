"""Phase 2D controlled run: portion models and the dish comparison on the frozen five-dish inputs (no Tavily, no page fetch, no LLM).

Inputs: `roli_agent/eval/frozen_inputs_2c1.json` (recipes re-ingested offline, frozen USDA decisions per verbatim line, saved relevance).
USDA records are read live (deterministic data). Steps per dish: current gate (a recipe the gate now rejects is dropped) -> build the published
scenario with the current code (D20 median sizes, inference layer) -> adapted pairs in approved and experimental mode -> portion models on the
published scenario and on both pairs -> scenario intervals -> dish intervals -> pairwise comparison. Timing per stage is recorded.

    .venv/bin/python -m roli_agent.scripts.replay_2d [--tag _2026-11-03] [--mode experimental]

Writes `roli_agent/eval/2d_controlled<tag>.json` and `roli_agent/eval/2d_controlled<tag>.md` and prints the tables.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import NutritionService, Settings
from roli_nutrition.recipe import RecipeCalculator

from roli_agent.config import ROOT
from roli_agent.recipes.adapt import WeightsTable, adapt_pairs
from roli_agent.recipes.compare_dishes import ExternalEvidence, compare_dishes, dish_interval, scenario_interval
from roli_agent.recipes.completeness import CompleteRecordPolicy
from roli_agent.recipes.equivalence import EquivalentRecordPolicy
from roli_agent.recipes.models import MenuItem, Relevance, Scenario, SourceRecipe
from roli_agent.recipes.pipeline import _build_scenario, _source_of
from roli_agent.recipes.portions import PortionRules, pair_inputs, portion_scenario, published_input
from roli_agent.recipes.relevance import gate
from roli_agent.scripts.replay_2c1 import decisions_for

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")


def fmt(v, places="0.01"):
    return "-" if v is None else str(Decimal(str(v)).quantize(Decimal(places)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", default=str(ROOT / "roli_agent" / "eval" / "frozen_inputs_2c1.json"))
    parser.add_argument("--tag", default="")
    parser.add_argument("--mode", default="experimental", choices=["approved", "experimental"], help="which adaptation mode feeds the comparison")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    service = NutritionService(Settings.from_env())
    calc = RecipeCalculator(service)
    frozen = json.loads(Path(args.frozen).read_text(encoding="utf-8"))
    table, rules, evidence = WeightsTable.load(), PortionRules.load(), ExternalEvidence.load()
    report: dict = {"frozen_inputs": args.frozen, "comparison_mode": args.mode, "dishes": {}, "timing_seconds": {}}
    per_dish_intervals: dict[str, dict] = {n: {} for n in NUTRIENTS}
    t_all = time.perf_counter()

    for dish, data in frozen["dishes"].items():
        t0 = time.perf_counter()
        item = MenuItem(**data["menu_item"])
        recipes = [SourceRecipe(**{k: v for k, v in r.items() if not k.startswith("saved_")}) for r in data["recipes"]]
        meta = {r["canonical_url"]: r for r in data["recipes"]}
        scenarios, recipe_of, dropped = [], {}, []
        for r in recipes:
            m = meta[r.canonical_url]
            if not m["saved_status"] or m["saved_status"][0] != "calculated":
                continue
            passed, reason = gate(item, r)
            if not passed:
                dropped.append((r.title, reason))
                continue
            rel = Relevance(**m["saved_relevance"])
            decisions, _ = decisions_for(r, data["frozen_decisions_by_line"], rel.menu_missing, service)
            s = Scenario(scenario_id=m["saved_scenario_id"], source=_source_of(r), relevance=rel, status="not_processed")
            _build_scenario(s, r, decisions, service, {}, calc, [], EquivalentRecordPolicy(service), CompleteRecordPolicy(service, enabled=False))
            scenarios.append(s)
            recipe_of[s.scenario_id] = r
        t_build = time.perf_counter()
        pairs_by_mode, summaries = {}, {}
        for mode in ("approved", "experimental"):
            pairs, summ = adapt_pairs(scenarios, service=service, table=table, mode=mode)
            pairs_by_mode[mode], summaries[mode] = {p.derived_from: p for p in pairs}, summ
        t_adapt = time.perf_counter()
        portioned_pub, portioned_pair = {}, {m: {} for m in pairs_by_mode}
        for s in scenarios:
            r = recipe_of[s.scenario_id]
            inp = published_input(s)
            if inp is not None:
                portioned_pub[s.scenario_id] = portion_scenario(inp, item=item, rules=rules, calculator=calc, yield_text=r.yield_text, method_text=r.instructions_text)
            for mode, pairs in pairs_by_mode.items():
                p = pairs.get(s.scenario_id)
                inputs = pair_inputs(p, s) if p is not None else None
                if inputs is not None:
                    portioned_pair[mode][s.scenario_id] = portion_scenario(inputs, item=item, rules=rules, calculator=calc, yield_text=r.yield_text, method_text=r.instructions_text)
        t_portion = time.perf_counter()
        intervals = {n: [] for n in NUTRIENTS}
        no_portion = 0
        for s in scenarios:
            for n in NUTRIENTS:
                iv = scenario_interval(s, pairs_by_mode[args.mode].get(s.scenario_id), portioned_pub.get(s.scenario_id), portioned_pair[args.mode].get(s.scenario_id), n, evidence)
                if iv is None:
                    if n == NUTRIENTS[0]:
                        no_portion += 1
                    continue
                intervals[n].append(iv)
        for n in NUTRIENTS:
            per_dish_intervals[n][dish] = dish_interval(dish, n, intervals[n], no_portion)
        t_cmp = time.perf_counter()
        report["timing_seconds"][dish] = {"build_scenarios": round(t_build - t0, 2), "adapt_both_modes": round(t_adapt - t_build, 2), "portion": round(t_portion - t_adapt, 2),
                                          "intervals": round(t_cmp - t_portion, 3)}
        report["dishes"][dish] = {
            "menu_item": data["menu_item"], "dropped_by_gate": dropped,
            "scenarios": {s.scenario_id: s.model_dump(mode="json") for s in scenarios},
            "pairs": {mode: {k: v.model_dump(mode="json") for k, v in pairs.items()} for mode, pairs in pairs_by_mode.items()},
            "adapt_summaries": {mode: s.model_dump(mode="json") for mode, s in summaries.items()},
            "portioned_published": {k: v.model_dump(mode="json") for k, v in portioned_pub.items()},
            "portioned_pairs": {mode: {k: v.model_dump(mode="json") for k, v in d.items()} for mode, d in portioned_pair.items()},
            "intervals": {n: per_dish_intervals[n][dish].model_dump(mode="json") for n in NUTRIENTS},
        }
    t_compare = time.perf_counter()
    comparison = compare_dishes(per_dish_intervals)
    report["comparison"] = comparison.model_dump(mode="json")
    report["timing_seconds"]["compare_dishes"] = round(time.perf_counter() - t_compare, 3)
    report["timing_seconds"]["total"] = round(time.perf_counter() - t_all, 1)

    # -- tables --------------------------------------------------------------------------------------------------
    lines = [f"# Phase 2D controlled run ({args.mode} pairs feed the comparison)", ""]
    lines += ["## Published scenarios: completeness basis, inferences", "", "| dish | scenario | 2A status | completeness basis (sat / chol) | inferences | blockers |", "|---|---|---|---|---|---|"]
    for dish, d in report["dishes"].items():
        for sid, sc in d["scenarios"].items():
            cb = sc["completeness_basis"]
            infs = ", ".join(i["kind"].split("_")[-1] + ":" + i["name"][:18] for i in sc["inferences"])[:90] or "-"
            lines.append(f"| {dish} | {sid[:48]} | {sc['calculation_status']} | {cb.get('saturated_fat_g','-')} / {cb.get('cholesterol_mg','-')} | {infs} | {sc['blockers']} |")
    lines += ["", "## Adapted pairs (experimental): completeness at both bounds, with inferences", "", "| dish | scenario | low | high | low+inf | high+inf | unfilled (high) |", "|---|---|---|---|---|---|---|"]
    for dish, d in report["dishes"].items():
        for sid, p in d["pairs"]["experimental"].items():
            def ok(b):
                it = p[b]["inferred_totals"]
                return "complete" if it and all(t["complete_with_inferences"] for t in it.values()) else "incomplete"
            lines.append(f"| {dish} | {sid[:48]} | {p['low']['calculation_status']} | {p['high']['calculation_status']} | {ok('low')} | {ok('high')} | "
                         f"{', '.join(u['name'][:20] + ' (' + u['reason'] + ')' for u in p['unfilled'])[:120] or '-'} |")
    lines += ["", f"## Portion models ({args.mode} pairs)", "", "| dish | scenario | model / rule | applicable | f low-high | sat fat per portion low-high (+inf) | chol per portion low-high (+inf) | recipe basis per serving (sat known) | reason / limits |", "|---|---|---|---|---|---|---|---|---|"]
    for dish, d in report["dishes"].items():
        for sid, ps in d["portioned_pairs"][args.mode].items():
            if ps["applicable"]:
                lo, hi = ps["low"]["per_portion"], ps["high"]["per_portion"]
                sat = f"{fmt(lo['saturated_fat_g']['known_subtotal'])}-{fmt(hi['saturated_fat_g']['known_subtotal'])} ({fmt(lo['saturated_fat_g']['total_with_inferences'])}-{fmt(hi['saturated_fat_g']['total_with_inferences'])})"
                chol = f"{fmt(lo['cholesterol_mg']['known_subtotal'], '1')}-{fmt(hi['cholesterol_mg']['known_subtotal'], '1')} ({fmt(lo['cholesterol_mg']['total_with_inferences'], '1')}-{fmt(hi['cholesterol_mg']['total_with_inferences'], '1')})"
                rb = ps["recipe_basis"]["per_serving"]
                lines.append(f"| {dish} | {sid[:40]} | {ps['model']} {ps['portion_rule_id']} | yes | {Decimal(ps['fraction_low']['fraction']):.3g}-{Decimal(ps['fraction_high']['fraction']):.3g} | {sat} | {chol} | "
                             f"{fmt(rb['low']['saturated_fat_g']['known_subtotal'])}-{fmt(rb['high']['saturated_fat_g']['known_subtotal'])} / {ps['recipe_basis']['servings']} servings | {ps['limitations'][0][:70]} |")
            else:
                lines.append(f"| {dish} | {sid[:40]} | {ps['model']} | no | - | - | - | - | {ps['not_applicable_reason'][:120]} |")
    for n in NUTRIENTS:
        lines += ["", f"## Dish intervals per restaurant portion: {n}", "", "| dish | low | high | bounded | recipes (bounded) | tiers | caveats |", "|---|---|---|---|---|---|---|"]
        for dish, iv in report["comparison"]["intervals"][n].items():
            tiers = Counter(s["tier"] for s in iv["scenarios"])
            lines.append(f"| {dish} | {fmt(iv['low'])} | {fmt(iv['high'])} | {iv['bounded']} | {iv['n_scenarios']} ({iv['n_bounded']}) | {dict(tiers)} | {' / '.join(iv['caveats'])[:200]} |")
    lines += ["", "## Pairwise verdicts", "", "| nutrient | A | B | verdict | lower | reason |", "|---|---|---|---|---|---|"]
    for pw in report["comparison"]["pairwise"]:
        lines.append(f"| {pw['nutrient']} | {pw['dish_a']} | {pw['dish_b']} | {pw['verdict']} | {pw['lower'] or '-'} | {pw['reason'][:140]} |")
    lines += ["", "## Drivers (highest bounded recipe per dish, saturated fat)", ""]
    for dish, iv in report["comparison"]["intervals"]["saturated_fat_g"].items():
        lines.append(f"- **{dish}**: " + " | ".join(iv["drivers"][:5]))
    lines += ["", f"Statement: {comparison.statement}", "", f"Timing (s): {json.dumps(report['timing_seconds'])}"]
    text = "\n".join(lines)
    print(text)
    out = ROOT / "roli_agent" / "eval" / f"2d_controlled{args.tag}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (ROOT / "roli_agent" / "eval" / f"2d_controlled{args.tag}.md").write_text(text + "\n", encoding="utf-8")
    print("\nwritten:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
