"""Run the fixed line-tag test set (SPEC_3_mvp.md 12.9.3) against the live tag call.

    .venv/bin/python -m roli_agent.scripts.eval_line_tags [--tag _2026-11-06] [--repeat 2]

Each test recipe goes through `tag_lines` exactly as a live dish does (same prompt, same model, same validators), one call per dish name, with no saved tags.
Spending goes through the same budget and ledger as a menu run. Writes `roli_agent/eval/line_tag_test<tag>.json` and `.md`: accuracy on the role and on the
kind, every miss, harmful-direction misses (an eaten line tagged medium or removed) counted separately, and the unclear lines for Julius.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, MODEL_ID, ROOT
from roli_agent.llm import RateLimitedLLM, make_chat_model, parse_json_object
from roli_agent.mvp.budget import BudgetedLLM, Limits, MenuBudget, Prices, SpendLedger
from roli_agent.recipes.inference import ZERO_WEIGHT_WORDS, is_herb_or_spice
from roli_agent.recipes.models import MenuItem, ParsedIngredient, SourceRecipe
from roli_agent.recipes.parse import parse_line
from roli_agent.recipes.tags import TAG_PROMPT_VERSION, tag_lines

SET = ROOT / "roli_agent" / "tests" / "fixtures" / "line_tag_test_set.json"


def source_recipe(i: int, r: dict) -> SourceRecipe:
    lines = [l["line"] for l in r["lines"]]
    return SourceRecipe(url=f"https://test.set/{i}", canonical_url=f"https://test.set/{i}", host="test.set", title=r["title"], found_by=["open"], fetched_at="2026-11-06", extraction="json_ld",
                        ingredient_lines=lines, instructions_text=r.get("method", ""), ingredients=[parse_line(x) for x in lines], content_hash=f"test-{i}")


def moves_a_figure(line: str) -> bool:
    """12.14.5: a herb or spice is left out by I03, and salt, zest, peel and citrus juice carry no weight or nutrient to speak of: whichever tag such a line gets, no figure moves."""
    name = parse_line(line).name
    return not (is_herb_or_spice(name) or ZERO_WEIGHT_WORDS.search(name) or re.search(r"\b(sprigs?|peppercorns?|bay lea(?:f|ves))\b", line, re.I))


def score(doc: dict, llm, parse=parse_json_object, *, keep_method: bool = True) -> dict:
    """Pure scoring around one tag call per dish name; `llm` may be a fake. `keep_method=False` hides the method text: the harder case of a page without one."""
    if not keep_method:
        doc = {**doc, "recipes": [{**r, "method": ""} for r in doc["recipes"]]}
    by_dish: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, r in enumerate(doc["recipes"]):
        by_dish[r["dish"]].append((i, r))
    rows, failed = [], []
    for dish, group in by_dish.items():
        item = MenuItem(name=dish, section=group[0][1].get("section", ""))
        recipes = [source_recipe(i, r) for i, r in group]
        tags = tag_lines(item, recipes, llm, parse)
        if not tags.available:
            failed.append({"dish": dish, "log": tags.log})
            continue
        for (i, r), rec in zip(group, recipes):
            for n, l in enumerate(r["lines"], start=1):
                t = tags.get(rec.canonical_url, n)
                row = {"dish": dish, "recipe": r["title"], "real_page": r.get("source") == "real_page", "line": l["line"], "got_role": t.role if t else None, "got_kind": t.kind if t else None, "model_role": t.raw_role if t else None,
                       "reason": t.reason if t else "", "note": t.note if t else "no tag returned"}
                if "unclear" in l:
                    row["question"] = l["unclear"]
                else:
                    row.update(expected_role=l["role"], expected_kind=l["kind"], rule=l["rule"])
                rows.append(row)
    scored = [r for r in rows if "expected_role" in r]
    free = [r for r in scored if r["got_role"] != r["expected_role"] and not moves_a_figure(r["line"])]        # 12.14.5: either answer passes
    role_misses = [r for r in scored if r["got_role"] != r["expected_role"] and moves_a_figure(r["line"])]
    kind_scored = [r for r in scored if r["expected_kind"] is not None]              # 12.10.3 decides some lines' role only
    kind_misses = [r for r in kind_scored if r["got_kind"] != r["expected_kind"]]
    harmful = [r for r in role_misses if r["expected_role"] == "eaten" and r["got_role"] in ("cooking_medium", "removed")]
    raw_harmful = [r for r in scored if r["expected_role"] == "eaten" and r["model_role"] in ("cooking_medium", "removed") and moves_a_figure(r["line"])]
    real = [r for r in scored if r["real_page"]]
    real_harmful = [r for r in harmful if r["real_page"]]
    return {"real_page": {"scored": len(real), "role_correct": len(real) - sum(1 for r in role_misses if r["real_page"]), "harmful": len(real_harmful)}, "no_figure_moved": free, "scored": len(scored), "role_correct": len(scored) - len(role_misses), "kind_scored": len(kind_scored), "kind_correct": len(kind_scored) - len(kind_misses), "role_misses": role_misses, "kind_misses": kind_misses,
            "harmful_misses": harmful, "model_harmful_before_code": raw_harmful, "unclear": [r for r in rows if "question" in r], "failed_calls": failed, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--no-method", action="store_true", help="hide every recipe's method text (a harder test)")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    doc = json.loads(SET.read_text(encoding="utf-8"))
    runs_dir = ROOT / "roli_agent" / "runs"
    model = RateLimitedLLM(make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS))
    prices = Prices.load(MODEL_ID, ROOT / ".cache" / "roli_mvp" / "openrouter_prices.json")
    report = {"model": MODEL_ID, "prompt_version": TAG_PROMPT_VERSION, "runs": []}
    for k in range(args.repeat):
        budget = MenuBudget(Limits.from_env(), SpendLedger(runs_dir / "spend_ledger.jsonl"), prices, run_id=f"line-tag-test{args.tag}-{k + 1}")
        try:
            result = score(doc, BudgetedLLM(model, budget), keep_method=not args.no_method)
        finally:
            budget.close()
        result["spend"] = budget.report()
        report["runs"].append(result)
    out = ROOT / "roli_agent" / "eval" / f"line_tag_test{args.tag}"
    out.with_suffix(".json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    md = [f"# Line-tag test set{args.tag}", "", f"Model {MODEL_ID}; prompt version {TAG_PROMPT_VERSION}; set `{SET.relative_to(ROOT)}`.", ""]
    for k, r in enumerate(report["runs"], start=1):
        made_up = r["scored"] - r["real_page"]["scored"]
        md += [f"## Run {k}", "", f"- Role correct: {r['role_correct']} of {r['scored']}", f"- Real pages (12.12.9): role correct {r['real_page']['role_correct']} of {r['real_page']['scored']}, harmful {r['real_page']['harmful']}",
               f"- Made-up cases: role correct {r['role_correct'] - r['real_page']['role_correct']} of {made_up}", f"- Kind correct: {r['kind_correct']} of {r['kind_scored']}",
               f"- Different answers on lines that cannot move a figure, passed (12.14.5): {len(r['no_figure_moved'])}",
               f"- Harmful direction (an eaten line tagged medium or removed, moving a figure), after code's checks: {len(r['harmful_misses'])}",
               f"- Harmful direction in the model's own answer, before code's checks: {len(r['model_harmful_before_code'])}", f"- Failed calls: {len(r['failed_calls'])}",
               f"- Cost: ${r['spend']['model_usd_total']}, {r['spend']['model_calls']} calls", ""]
        if r["role_misses"]:
            md += ["Role misses:", "", "| dish | recipe | real page | line | expected | got | model said | harmful | rule |", "|---|---|---|---|---|---|---|---|---|"]
            md += [f"| {m['dish']} | {m['recipe']} | {'yes' if m['real_page'] else 'no'} | {m['line']} | {m['expected_role']} | {m['got_role']} | {m['model_role']} | {'yes' if m in r['harmful_misses'] else 'no'} | {m['rule']} |" for m in r["role_misses"]]
            md.append("")
        if r["kind_misses"]:
            md += ["Kind misses:", "", "| dish | line | expected | got | rule |", "|---|---|---|---|---|"]
            md += [f"| {m['dish']} | {m['line']} | {m['expected_kind']} | {m['got_kind']} | {m['rule']} |" for m in r["kind_misses"]]
            md.append("")
    if report["runs"][-1]["unclear"]:
        md += ["## Unclear lines for Julius (not scored)", "", "| dish | line | model's tag | question |", "|---|---|---|---|"]
        md += [f"| {u['dish']} | {u['line']} | {u['got_role']} / {u['got_kind']} | {u['question']} |" for u in report["runs"][-1]["unclear"]]
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
