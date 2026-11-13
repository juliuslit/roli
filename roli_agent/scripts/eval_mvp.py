"""Phase 3 evaluation: run the MVP end to end on menu photos, twice each when asked, and report time, cost, errors and consistency.

    .venv/bin/python -m roli_agent.scripts.eval_mvp --photos menu_test_set/telegram_1280/menu_03_own_IMG_5185.jpg [...] [--repeat 2] [--max-dishes 12] [--tag _2026-11-03]

Writes `roli_agent/eval/mvp_eval<tag>.json` and `.md`; every run is also saved under `roli_agent/runs/` like a tester's run.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import ROOT
from roli_agent.mvp.menu_run import MenuRunner
from roli_agent.mvp.models import MvpConfig


def flag_text(f: dict) -> str:
    if f["status"] == "closed":
        return f"closed {f['dish']} ({f.get('note')})"
    return f"{f['status']} {f['dish']} ({f.get('comparison')}; Roli {f.get('roli_middle')} vs {f.get('published_low')}-{f.get('published_high')}; top {[t['line'] for t in f.get('top_contributors', [])]})"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos", nargs="+", required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-dishes", type=int, default=None, help="dishes evaluated per menu (default: MvpConfig.max_dishes, 30 since 12.18)")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--menu-budget-usd", default="0.50", help="model-call budget per menu, the menu-reading call included")
    parser.add_argument("--menu-credits", type=int, default=30, help="Tavily credits per menu")
    parser.add_argument("--daily-budget-usd", default=None, help="daily model-call budget (default from MvpConfig, 5.00)")
    parser.add_argument("--tag", default="")
    parser.add_argument("--reuse-saved-reading", action="store_true", help="reuse the reader's saved answer for each photo (12.10.5)")
    parser.add_argument("--cache-dir", default=None, help="a separate cache directory (two evaluations may then run at the same time)")
    parser.add_argument("--usda-min-remaining", type=int, default=600, help="do not start a photo when USDA's remaining hourly allowance is under this (3D)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    extra = {"cache_dir": Path(args.cache_dir)} if args.cache_dir else {}
    cfg = dict(reuse_saved_reading=args.reuse_saved_reading, workers=args.workers, menu_budget_usd=Decimal(args.menu_budget_usd), menu_search_credits=args.menu_credits)
    if args.max_dishes is not None:
        cfg["max_dishes"] = args.max_dishes
    if args.daily_budget_usd:
        cfg["daily_budget_usd"] = Decimal(args.daily_budget_usd)
    runner = MenuRunner(MvpConfig(**cfg), **extra)
    report = {"date": str(date.today()), "runs": []}
    status = runner.usda_status()
    print("USDA before the pass:", {k: status.get(k) for k in ("limit", "remaining", "halted", "release")})
    for photo in args.photos:
        for rep in range(args.repeat):
            st = runner.usda_status()
            if st.get("halted") or (st.get("remaining") is not None and st["remaining"] < args.usda_min_remaining):
                print(f"\nstopping before {photo}: USDA remaining {st.get('remaining')} (halted {st.get('halted')}), under --usda-min-remaining {args.usda_min_remaining}")
                break
            t0 = time.perf_counter()
            run = runner.run(photo, progress=lambda m: print("   ", m))
            seconds = round(time.perf_counter() - t0, 1)
            row = {"photo": photo, "repeat": rep + 1, "run_id": run.run_id, "status": run.status, "seconds": seconds, "timings": run.timings, "totals": run.totals, "spend": run.spend,
                   "ranking": [(r.rank, r.name, str(r.saturated_fat_low), str(r.saturated_fat_high), r.support) for r in run.ranking],
                   "unranked": [(u.name, u.reason[:120]) for u in run.unranked], "fat_lines": [x.fat_line for x in (*run.ranking, *run.unranked) if x.fat_line], "reading": run.reading, "errors": run.errors, "recommendation": run.recommendation, "usda": run.usda, "flags": run.flags,
                   "words": run.recommendation_words, "menu_items": len((run.menu or {}).get("items", [])),
                   "dish_status": {d.item["name"]: (d.status, d.dish_type, d.n_scenarios, d.n_portioned, d.seconds) for d in run.dishes},
                   "top3": [(r.rank, r.name, str(r.saturated_fat_low), str(r.saturated_fat_high), str(r.cholesterol_low), str(r.cholesterol_high), r.support, r.cholesterol_driver) for r in run.ranking[:3]]}
            report["runs"].append(row)
            print(f"\n## {Path(photo).name} run {rep + 1}: {run.status} in {seconds} s | {run.totals}\n   spend: {run.spend}\n   usda: {run.usda}\n   flags: {run.flags}\n   {run.recommendation}\n   ranking: {row['ranking']}\n   unranked: {row['unranked']}\n   errors: {run.errors}")
    # consistency: same photo, repeated runs
    cons = []
    by_photo: dict[str, list[dict]] = {}
    for r in report["runs"]:
        by_photo.setdefault(r["photo"], []).append(r)
    for photo, runs in by_photo.items():
        if len(runs) > 1:
            orders = [[x[1] for x in r["ranking"]] for r in runs]
            top3 = [o[:3] for o in orders]
            cons.append({"photo": photo, "same_order": all(o == orders[0] for o in orders), "same_top3": all(t == top3[0] for t in top3), "orders": orders,
                         "same_recommendation": all(r["recommendation"] == runs[0]["recommendation"] for r in runs)})
    report["consistency"] = cons
    out = ROOT / "roli_agent" / "eval" / f"mvp_eval{args.tag}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    lines = [f"# MVP evaluation ({report['date']})", "", "| photo | run | status | s | menu items | candidates | selected | evaluated | ranked | unranked | no recipes | errors | skipped | budget-stopped | credits | model calls | model $ (actual+est.) | USDA req | words |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["runs"]:
        t, sp = r["totals"], r.get("spend", {})
        lines.append(f"| {Path(r['photo']).name} | {r['repeat']} | {r['status']} | {r['seconds']} | {r['menu_items']} | {t.get('dishes_candidates')} | {t.get('dishes_selected')} | {t.get('dishes_evaluated')} | {t.get('dishes_ranked')} | {t.get('dishes_unranked')} | "
                     f"{t.get('dishes_no_recipes')} | {t.get('dishes_error')} | {t.get('dishes_skipped')} | {t.get('dishes_budget_stopped')} | {t.get('search_credits')} | {t.get('llm_calls')} | "
                     f"{str(sp.get('model_usd_total', ''))[:6]} ({str(sp.get('model_usd_actual', ''))[:6]}+{str(sp.get('model_usd_estimated', ''))[:6]}) | {t.get('usda_http_requests')} | {r['words']} |")
    for r in report["runs"]:
        lines += ["", f"## {Path(r['photo']).name} run {r['repeat']}", "", f"> {r['recommendation']}", "", "| # | dish | sat fat g | support |", "|---|---|---|---|"]
        lines += [f"| {x[0]} | {x[1]} | {x[2][:5]}–{x[3][:5]} | {x[4]} |" for x in r["ranking"]]
        if r.get("spend", {}).get("interruptions"):
            lines += ["", "Budget interruptions: " + "; ".join(r["spend"]["interruptions"])]
        if r["unranked"]:
            lines += ["", "Unranked: " + "; ".join(f"{n} ({why})" for n, why in r["unranked"])]
        if r["errors"]:
            lines += ["", "Errors: " + "; ".join(r["errors"])]
        if r.get("usda"):
            u = r["usda"]
            lines += ["", f"USDA: {u.get('requests')} requests; remaining {u.get('remaining_before')} -> {u.get('remaining_after')} of {u.get('limit')}; halted {u.get('halted')}; flagged {u.get('dishes_flagged')}; USDA-unavailable dishes {u.get('dishes_usda_unavailable')}"]
        if r.get("flags"):
            lines += ["", "Flags: " + "; ".join(flag_text(f) for f in r["flags"])]
        if r.get("fat_lines"):
            lines += ["", "Frying-fat line: " + " ".join(r["fat_lines"])]
    if cons:
        lines += ["", "## Consistency (same photo, repeated)", ""] + [f"- {Path(c['photo']).name}: same order {c['same_order']}, same top 3 {c['same_top3']}, same text {c['same_recommendation']}; orders {c['orders']}" for c in cons]
    (ROOT / "roli_agent" / "eval" / f"mvp_eval{args.tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwritten:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
