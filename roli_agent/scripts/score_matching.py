"""Score the USDA matcher on the relevance test set (spec 2B section 7; requirement 2 of 2B-2).

    .venv/bin/python -m roli_agent.scripts.score_matching [--set menu_reader_eval/usda_matching/matching_set.csv] [--out menu_reader_eval/usda_matching]

Live: the real model through OpenRouter writes queries and picks records; the real USDA search supplies the candidates.
Each row's chosen record is classified against the row's expected description pattern and accepted-proxy pattern:
  direct_correct       labelled direct and the description matches the expected pattern
  proxy_acceptable     labelled proxy and the description matches the expected or the accepted-proxy pattern
  mislabelled          a usable record with the wrong label (direct for a proxy, or proxy for the exact food)
  false_match          a record that matches neither pattern: the error that matters most
  unresolved           no record (no candidates, declined, guard, state conflict, USDA error)
The patterns are Julius's and the agent's expectations of USDA naming; the chosen descriptions are written out so they can be reviewed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import NutritionService, Settings

from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, ROOT
from roli_agent.llm import make_chat_model, parse_json_object
from roli_agent.recipes.match import MatchCache, MatchRequest, UsdaMatcher
from roli_agent.recipes.metrics import Meter, MeteredLLM


def classify(row: dict, decision) -> str:
    expected, proxy_ok = row["expected_pattern"].strip(), row["accepted_proxy_pattern"].strip()
    if decision.fdc_id is None:
        return "unresolved"
    desc = decision.description or ""
    hits_expected = bool(expected) and re.search(expected, desc, re.I) is not None
    hits_proxy = bool(proxy_ok) and re.search(proxy_ok, desc, re.I) is not None
    if decision.match_type == "direct":
        if hits_expected:
            return "direct_correct"
        if hits_proxy:
            return "mislabelled"
        return "false_match"
    if hits_expected or hits_proxy:
        return "proxy_acceptable" if hits_proxy or not expected else "mislabelled"
    return "false_match"


class _Saved:
    def __init__(self, row: dict) -> None:
        self.fdc_id, self.description, self.match_type, self.issue = row["fdc_id"], row["description"], row["match_type"], row["issue"]


def rescore(path: Path, rows: list[dict], out: Path) -> int:
    """Oracle patterns were corrected after the live run (USDA Foundation records are named differently from SR Legacy);
    this re-reads the saved live decisions and re-classifies them. The chosen records themselves are not touched."""
    saved = json.loads(path.read_text(encoding="utf-8"))
    by_name = {r["ingredient_text"]: r for r in rows}
    counts = Counter()
    for r in saved["rows"]:
        row = by_name[r["ingredient"]]
        r["expected"], r["accepted_proxy"] = row["expected_pattern"], row["accepted_proxy_pattern"]
        r["verdict_before_rescore"] = r.get("verdict_before_rescore", r["verdict"])
        r["verdict"] = classify(row, _Saved(r))
        counts[r["verdict"]] += 1
    n = len(saved["rows"])
    saved["summary"].update({k: counts.get(k, 0) for k in ("direct_correct", "proxy_acceptable", "mislabelled", "false_match", "unresolved")})
    saved["summary"]["false_match_rate"] = round(100 * counts.get("false_match", 0) / n, 1)
    saved["summary"]["unresolved_rate"] = round(100 * counts.get("unresolved", 0) / n, 1)
    saved["summary"]["rescored"] = f"patterns corrected and re-applied {date.today()}; live decisions unchanged"
    path.write_text(json.dumps(saved, indent=1, ensure_ascii=False), encoding="utf-8")
    md = out / (path.stem + ".md")
    lines = [f"# USDA matching evaluation, {saved['summary']['date']} (re-scored {date.today()} after pattern corrections; decisions unchanged)", "",
             f"Model: {saved['summary']['model']}. Rows: {n}. LLM calls: {saved['summary']['llm_calls']}; USDA searches: {saved['summary']['usda_searches']}; {saved['summary']['seconds']} s; cost {saved['summary']['llm_cost_usd']} USD.", "",
             "| Verdict | Count | Share |", "|---|---:|---:|"]
    for k in ("direct_correct", "proxy_acceptable", "mislabelled", "false_match", "unresolved"):
        lines.append(f"| {k} | {counts.get(k, 0)} | {100 * counts.get(k, 0) / n:.0f}% |")
    lines += ["", "| Ingredient | Hint | Query | Chosen (FDC) | Label | Verdict | Before re-score | Issue |", "|---|---|---|---|---|---|---|---|"]
    for r in saved["rows"]:
        chosen = f"{r['description']} ({r['fdc_id']})" if r["fdc_id"] else "none"
        lines.append(f"| {r['ingredient']} | {r['hint']} | {r['query']} | {chosen} | {r['match_type']} | {r['verdict']} | {r['verdict_before_rescore']} | {r['issue'] or ''} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(saved["summary"], indent=1))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default=str(ROOT / "menu_reader_eval" / "usda_matching" / "matching_set.csv"))
    parser.add_argument("--out", default=str(ROOT / "menu_reader_eval" / "usda_matching"))
    parser.add_argument("--rescore", help="re-classify the chosen records saved in this results JSON against the current patterns; no live calls")
    args = parser.parse_args()
    rows = list(csv.DictReader(open(args.set, encoding="utf-8")))
    if args.rescore:
        return rescore(Path(args.rescore), rows, Path(args.out))
    load_dotenv(ROOT / ".env")

    meter = Meter()
    llm = MeteredLLM(make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS), meter)
    service = NutritionService(Settings.from_env())
    matcher = UsdaMatcher(service, llm, parse_json_object=parse_json_object, cache=MatchCache(None))
    requests = [MatchRequest(name=r["ingredient_text"], preparation_hint=r["preparation_hint"] or "unknown") for r in rows]
    started = time.perf_counter()
    decisions, log = matcher.match(requests, context="ingredients from a Californian-Italian restaurant menu (Flour + Water style)")
    seconds = time.perf_counter() - started

    results, counts = [], Counter()
    for row, req in zip(rows, requests):
        d = decisions[req.key]
        verdict = classify(row, d)
        counts[verdict] += 1
        results.append({"ingredient": row["ingredient_text"], "context": row["menu_context"], "hint": row["preparation_hint"], "query": d.query,
                        "fdc_id": d.fdc_id, "description": d.description, "match_type": d.match_type, "issue": d.issue, "verdict": verdict,
                        "candidates_seen": d.candidates_seen, "reason": d.reason, "expected": row["expected_pattern"], "accepted_proxy": row["accepted_proxy_pattern"],
                        "consequence": row.get("consequence", ""), "candidates": [c["description"] for c in d.candidates]})
    n = len(rows)
    high = [r for r in results if r.get("consequence") == "high"]
    high_false = sum(1 for r in high if r["verdict"] == "false_match")
    summary = {"rows": n, **{k: counts.get(k, 0) for k in ("direct_correct", "proxy_acceptable", "mislabelled", "false_match", "unresolved")},
               "high_consequence_rows": len(high), "high_consequence_false_matches": high_false,
               "high_consequence_false_match_rate": round(100 * high_false / len(high), 1) if high else None,
               "false_match_rate": round(100 * counts.get("false_match", 0) / n, 1), "unresolved_rate": round(100 * counts.get("unresolved", 0) / n, 1),
               "llm_calls": log.llm_calls, "llm_failures": log.llm_failures, "usda_searches": log.usda_searches, "prompt_tokens": meter.llm_prompt_tokens,
               "completion_tokens": meter.llm_completion_tokens, "llm_cost_usd": str(meter.llm_cost_usd) if meter.llm_cost_usd is not None else None,
               "seconds": round(seconds, 1), "model": llm._inner.model_name, "date": str(date.today()), "notes": log.notes}
    out = Path(args.out)
    (out / f"results_{date.today()}.json").write_text(json.dumps({"summary": summary, "rows": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"# USDA matching evaluation, {date.today()}", "", f"Model: {summary['model']}. Rows: {n}. LLM calls: {log.llm_calls}; USDA searches: {log.usda_searches}; {seconds:.1f} s.", "",
             "| Verdict | Count | Share |", "|---|---:|---:|"]
    for k in ("direct_correct", "proxy_acceptable", "mislabelled", "false_match", "unresolved"):
        lines.append(f"| {k} | {counts.get(k, 0)} | {100 * counts.get(k, 0) / n:.0f}% |")
    lines += ["", "| Ingredient | Consequence | Hint | Query | Chosen (FDC) | Label | Verdict | Issue |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        chosen = f"{r['description']} ({r['fdc_id']})" if r["fdc_id"] else "none"
        lines.append(f"| {r['ingredient']} | {r['consequence']} | {r['hint']} | {r['query']} | {chosen} | {r['match_type']} | {r['verdict']} | {r['issue'] or ''} |")
    (out / f"results_{date.today()}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for n in log.notes:
        print("note:", n)
    for r in results:
        print(f"{r['verdict']:17s} {r['ingredient']:32s} -> {r['description']} ({r['fdc_id']}) [{r['match_type']}] {r['issue'] or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
