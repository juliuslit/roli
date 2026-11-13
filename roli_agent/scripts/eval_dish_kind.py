"""Dish kind: the model against the word lists, on the labelled set (SPEC_3_mvp.md 12.16.12).

    .venv/bin/python -m roli_agent.scripts.eval_dish_kind --labels roli_agent/eval/dish_kind_labels_2026-11-06.csv --out roli_agent/eval/dish_kind_eval_2026-11-06.md [--no-model]

One model call per menu, exactly as a live run would make it (same prompt, same model, same validation), through the budget and the ledger; since 12.18 the per-item cache under
.cache/roli_mvp/judgements/dish_kind/ is read first, so items a live run has already classified cost nothing. Accuracy overall, per family and on the 3H failure cases,
for the word lists and for the model; the rule of 12.16.12 applied. The word lists need no call.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, MODEL_ID, ROOT
from roli_agent.llm import RateLimitedLLM, make_chat_model, parse_json_object
from roli_agent.mvp.budget import BudgetedLLM, Limits, MenuBudget, Prices, SpendLedger
from roli_agent.mvp.dish_kind import PROMPT_VERSION, DishKindCache, classify_menu
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.portions import dish_type_for

RUNS = {"03": "20261106-221052-90e28f", "08": "20261106-221235-39f92e", "01": "20261106-221426-4145ed", "23": "20261106-221648-2160ad", "02": "20261106-222042-28cf0d", "04": "20261106-222203-6e973e",
        "05": "20261106-222418-0e0548", "06": "20261106-222809-004812", "07": "20261106-223235-fdff2b", "09": "20261106-223251-cbe070", "10": "20261106-223259-ea627f", "11": "20261106-224041-98f98b",
        "19": "20261106-224057-8f069b"}


def accuracy(rows: list[dict], col: str) -> tuple[int, int]:
    return sum(1 for r in rows if (r[col] or "") == (r["proposed_family"] or "")), len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-model", action="store_true")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    labels = list(csv.DictReader(open(args.labels, encoding="utf-8")))
    for r in labels:
        r["word_list"] = dish_type_for(MenuItem(name=r["name"], section=r["section"], description=r["description"])) or ""
        r["model"] = ""
        r["model_raw"] = ""
    spend = None
    if not args.no_model:
        llm = RateLimitedLLM(make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS))
        prices = Prices.load(MODEL_ID, ROOT / ".cache" / "roli_mvp" / "openrouter_prices.json")
        budget = MenuBudget(Limits.from_env(), SpendLedger(ROOT / "roli_agent" / "runs" / "spend_ledger.jsonl"), prices, run_id="dish-kind-eval")
        logs = {}
        cache = DishKindCache(ROOT / ".cache" / "roli_mvp" / "judgements", MODEL_ID)      # 12.18: the per-item cache is read first; only unsaved items go to the model
        try:
            for menu, rid in RUNS.items():
                run = json.loads((ROOT / "roli_agent" / "runs" / rid / "run.json").read_text(encoding="utf-8"))
                items = (run.get("menu") or {}).get("items", [])
                kinds, log = classify_menu(items, BudgetedLLM(llm, budget), parse_json_object, cache=cache)
                logs[menu] = log
                for r in labels:
                    if r["menu"] == menu and int(r["index"]) in kinds:
                        k = kinds[int(r["index"])]
                        r["model"], r["model_raw"], r["model_source"] = k.family or "", k.model_kind, k.source
        finally:
            budget.close()
        spend = budget.report()
    cols = [("word lists (3I)", "word_list"), ("word lists (3H)", "word_list_3h")] + ([("model", "model")] if not args.no_model else [])
    lines = [f"# Dish kind: the model against the word lists, {Path(args.labels).name}", "", f"Model {MODEL_ID}, prompt version {PROMPT_VERSION}. {len(labels)} food items on 13 menus, labelled by hand (proposal); {sum(1 for r in labels if r['unsure'])} marked unsure.", ""]
    if spend:
        lines.append(f"Spend: ${spend['model_usd_total']}, {spend['model_calls']} calls; {sum(l.get('from_saved', 0) for l in logs.values())} items answered from the saved per-item cache (12.18). Fallbacks to the word lists: {sum(l.get('fallback', 0) for l in logs.values())}; failed calls: {[m for m, l in logs.items() if l.get('error')]}.")
        lines.append("")
    lines += ["## Overall", "", "| classifier | correct | of | accuracy |", "|---|---|---|---|"]
    for name, col in cols:
        c, n = accuracy(labels, col)
        lines.append(f"| {name} | {c} | {n} | {100 * c / n:.1f} % |")
    sure = [r for r in labels if not r["unsure"]]
    lines += ["", "On the items not marked unsure:", "", "| classifier | correct | of | accuracy |", "|---|---|---|---|"]
    for name, col in cols:
        c, n = accuracy(sure, col)
        lines.append(f"| {name} | {c} | {n} | {100 * c / n:.1f} % |")
    lines += ["", "## The 3H failure cases", "", "| case | items | " + " | ".join(n for n, _ in cols) + " |", "|---|---|" + "---|" * len(cols)]
    by_case = defaultdict(list)
    for r in labels:
        if r["failure_case_3h"]:
            by_case[r["failure_case_3h"]].append(r)
    for case, rows in sorted(by_case.items()):
        lines.append(f"| {case} | {len(rows)} | " + " | ".join(f"{accuracy(rows, col)[0]}" for _, col in cols) + " |")
    lines += ["", "## Per family (the label's family)", "", "| family | items | " + " | ".join(n for n, _ in cols) + " |", "|---|---|" + "---|" * len(cols)]
    by_fam = defaultdict(list)
    for r in labels:
        by_fam[r["proposed_family"] or "(none)"].append(r)
    for fam, rows in sorted(by_fam.items(), key=lambda t: -len(t[1])):
        lines.append(f"| {fam} | {len(rows)} | " + " | ".join(f"{accuracy(rows, col)[0]}" for _, col in cols) + " |")
    if not args.no_model:
        wl, md = accuracy(labels, "word_list"), accuracy(labels, "model")
        cases_ok = all(accuracy(rows, "model")[0] >= accuracy(rows, "word_list")[0] for rows in by_case.values())
        verdict = md[0] >= wl[0] and cases_ok
        lines += ["", f"**12.16.12: the model goes live only if it is at least as accurate overall ({md[0]} vs {wl[0]}) and on every 3H failure case ({'yes' if cases_ok else 'no'}): {'met' if verdict else 'not met'}.**", ""]
        lines += ["## Where the model and the label disagree", "", "| menu | item | section | label | model | model said | unsure |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {r['menu']} | {r['name'][:40]} | {r['section'][:20]} | {r['proposed_family'] or '(none)'} | {r['model'] or '(none)'} | {r['model_raw']} | {r['unsure']} |" for r in labels if (r["model"] or "") != (r["proposed_family"] or "")]
    lines += ["", "## Where the word lists and the label disagree", "", "| menu | item | section | label | word lists | unsure |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['menu']} | {r['name'][:40]} | {r['section'][:20]} | {r['proposed_family'] or '(none)'} | {r['word_list'] or '(none)'} | {r['unsure']} |" for r in labels if (r["word_list"] or "") != (r["proposed_family"] or "")]
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(args.labels, "w", encoding="utf-8", newline="") as f:
        fields = [k for k in labels[0].keys() if k != "model_source"]
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(labels)
    print("\n".join(lines[:45]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
