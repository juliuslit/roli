"""Controlled comparison for D22 on identical saved inputs (no search, no LLM): the recipes, parsed lines and USDA
record choices saved by a live run are replayed through conversion and the Phase 2A calculator under several policies,
so the effect of each rule is measured without model or search variability.

    .venv/bin/python -m roli_agent.scripts.replay_d22 roli_agent/eval/2b2_live_2026-11-02.json [--out roli_agent/eval/d22_replay_<date>.json]

Policies compared: A = run-4 rules with millilitre measures ignored (the 2B-2.1 behaviour); B = the record's own millilitre
measure accepted as a density source (D4, no new record); C = B plus D22 strict (same food, same state, both nutrients
reported and equivalent within 5 % / 0.1 g / 1 mg); D = B plus D22 with a relaxed tolerance (15 %) and a missing nutrient
on the original tolerated when the replacement reports it. Only C is proposed; D exists to show what the relaxations would buy.
USDA is live (deterministic data; service cache); candidate lists come from re-running each saved query.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import ErrorResult, NutritionService, Settings
from roli_nutrition.recipe import RecipeCalculator

from roli_agent.config import ROOT
from roli_agent.recipes import convert as convert_mod
from roli_agent.recipes import equivalence
from roli_agent.recipes.equivalence import EquivalentRecordPolicy
from roli_agent.recipes.match import MatchRequest
from roli_agent.recipes.models import MatchDecision, ParsedIngredient, Scenario, SourceRecipe
from roli_agent.recipes.pipeline import _build_scenario


def rebuild(sc: dict) -> tuple[SourceRecipe, Scenario, dict[str, MatchDecision]]:
    src = sc["source"]
    parsed = [ParsedIngredient(**i["parsed"]) for i in sc["ingredients"] if i["origin"] == "recipe"]
    recipe = SourceRecipe(url=src["url"], canonical_url=src["canonical_url"], host=src["host"], title=src["title"], found_by=src["found_by"], fetched_at="replay",
                          extraction=src["extraction"], yield_text=src["yield_text"], servings=Decimal(str(src["servings"])), servings_note=src["servings_note"],
                          ingredient_lines=[p.line for p in parsed], cooking_verbs=[], ingredients=parsed, content_hash="replay", flags=list(src["flags"]),
                          yield_source=src["yield_source"] if src["yield_source"] in ("structured", "page_text", "none") else "none")
    decisions = {}
    for i in sc["ingredients"]:
        if i["match"] is None:
            continue
        hint = i["parsed"]["preparation_hint"] if i["parsed"] else "unknown"
        decisions[MatchRequest(name=i["name"], preparation_hint=hint).key] = MatchDecision(**i["match"])
    scenario = Scenario(**{**sc, "ingredients": [], "calculation": None, "status": "not_processed", "status_reason": None, "flags": []})
    return recipe, scenario, decisions


def fill_candidates(decisions: dict[str, MatchDecision], service: NutritionService) -> None:
    for key, d in decisions.items():
        if d.fdc_id is not None and not d.candidates and d.query:
            res = service.search_foods(d.query, 10)
            if not isinstance(res, ErrorResult):
                decisions[key] = d.model_copy(update={"candidates": [c.model_dump() for c in res.candidates]})


def run_policy(label: str, scenarios, service, *, ml_density: bool, d22: EquivalentRecordPolicy | None) -> dict:
    calc = RecipeCalculator(service)
    saved_words = dict(convert_mod.VOLUME_WORDS_TO_UNIT)
    if not ml_density:
        for w in ("milliliter", "milliliters", "millilitre", "ml", "liter", "litre"):
            convert_mod.VOLUME_WORDS_TO_UNIT.pop(w, None)
    out = {"label": label, "scenarios": []}
    try:
        for recipe, scenario, decisions in scenarios:
            sc = scenario.model_copy(deep=True)
            _build_scenario(sc, recipe, decisions, service, {}, calc, [], d22)
            lines = [{"line": i.line, "grams": str(i.conversion.grams) if i.conversion.grams is not None else None, "method": i.conversion.method,
                      "fdc_id": i.match.fdc_id if i.match else None, "substituted_for": i.match.substituted_for if i.match else None, "blocker": i.blocker}
                     for i in sc.ingredients if i.origin == "recipe"]
            out["scenarios"].append({"title": sc.source.title, "host": sc.source.host, "status": sc.calculation_status, "blockers": sc.blockers, "lines": lines,
                                     "resolved": sum(1 for l in lines if l["blocker"] is None), "total": len(lines)})
    finally:
        convert_mod.VOLUME_WORDS_TO_UNIT.clear()
        convert_mod.VOLUME_WORDS_TO_UNIT.update(saved_words)
    return out


class RelaxedPolicy(EquivalentRecordPolicy):
    """Policy D: 15 % tolerance; a nutrient the original does not report is tolerated when the replacement reports it."""

    def find(self, parsed, match):
        saved = (dict(equivalence.ABS_TOLERANCE), equivalence.REL_TOLERANCE, equivalence.equivalent_values)
        equivalence.REL_TOLERANCE = Decimal("0.15")

        def relaxed(a, b):
            for nutrient in ("saturated_fat_g", "cholesterol_mg"):
                va, vb = getattr(a, nutrient), getattr(b, nutrient)
                if vb is None:
                    return False
                if va is None:
                    continue
                da, db = Decimal(str(va)), Decimal(str(vb))
                if abs(da - db) > max(equivalence.ABS_TOLERANCE[nutrient], equivalence.REL_TOLERANCE * max(da, db)):
                    return False
            return True
        equivalence.equivalent_values = relaxed
        try:
            return super().find(parsed, match)
        finally:
            equivalence.ABS_TOLERANCE.update(saved[0]); equivalence.REL_TOLERANCE = saved[1]; equivalence.equivalent_values = saved[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json")
    parser.add_argument("--out", default=str(ROOT / "roli_agent" / "eval" / f"d22_replay_{date.today()}.json"))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    data = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    service = NutritionService(Settings.from_env())
    scenarios = []
    for est in data["cold"].values():
        for sc in est["scenarios"]:
            if sc["status"] == "calculated":
                recipe, scenario, decisions = rebuild(sc)
                fill_candidates(decisions, service)
                scenarios.append((recipe, scenario, decisions))
    print(f"replaying {len(scenarios)} calculated scenarios from {args.run_json}")
    results = {
        "A_no_ml_no_d22": run_policy("A", scenarios, service, ml_density=False, d22=None),
        "B_ml_density": run_policy("B", scenarios, service, ml_density=True, d22=None),
        "C_ml_plus_d22_strict": run_policy("C", scenarios, service, ml_density=True, d22=EquivalentRecordPolicy(service)),
        "D_ml_plus_d22_relaxed": run_policy("D", scenarios, service, ml_density=True, d22=RelaxedPolicy(service)),
    }
    summary = {}
    base = results["A_no_ml_no_d22"]["scenarios"]
    for key, res in results.items():
        resolved = sum(s["resolved"] for s in res["scenarios"]); total = sum(s["total"] for s in res["scenarios"])
        complete = sum(1 for s in res["scenarios"] if s["status"] == "complete")
        subs = sum(1 for s in res["scenarios"] for l in s["lines"] if l["substituted_for"])
        changed = sum(1 for s, b in zip(res["scenarios"], base) for l, lb in zip(s["lines"], b["lines"]) if l["grams"] != lb["grams"] or l["fdc_id"] != lb["fdc_id"])
        blockers = Counter(); [blockers.update(s["blockers"]) for s in res["scenarios"]]
        summary[key] = {"resolved_lines": resolved, "total_lines": total, "complete_scenarios": complete, "substitutions": subs, "lines_changed_vs_A": changed,
                        "blockers": dict(blockers)}
        print(f"{key:24s} resolved {resolved}/{total} complete {complete} substitutions {subs} changed vs A {changed} blockers {dict(blockers)}")
    for key in ("B_ml_density", "C_ml_plus_d22_strict", "D_ml_plus_d22_relaxed"):
        print(f"\n== lines changed under {key} (vs A) ==")
        for s, b in zip(results[key]["scenarios"], base):
            for l, lb in zip(s["lines"], b["lines"]):
                if l["grams"] != lb["grams"] or l["fdc_id"] != lb["fdc_id"]:
                    print(f"   {s['title'][:28]:28s} | {l['line'][:48]:48s} | {lb['grams'] and lb['grams'][:8]} -> {l['grams'] and l['grams'][:8]} | {lb['fdc_id']} -> {l['fdc_id']}{' (sub for ' + str(l['substituted_for']) + ')' if l['substituted_for'] else ''}")
    Path(args.out).write_text(json.dumps({"source_run": args.run_json, "date": str(date.today()), "summary": summary, "results": results}, indent=1, default=str), encoding="utf-8")
    print("\nwritten:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
