"""The reader measured on its own (SPEC_3_mvp.md 12.10.5): read one photo twice, fresh, and report what changed between the two readings.

    .venv/bin/python -m roli_agent.scripts.reader_check --photo menu_test_set/telegram_1280/menu_23_en_boardwalk_bistro_chalkboard.jpg [--out roli_agent/eval/....md]

Neither reading is saved, so the saved reading of a test rerun is left alone. Spending goes through the same budget and ledger as a menu run. With --out, the report is added at the end of that file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import ROOT
from roli_agent.mvp.menu_run import MenuRunner
from roli_agent.mvp.models import MvpConfig

FIELDS = ("name", "description", "section", "price")


def compare_readings(a: dict, b: dict) -> list[str]:
    """Every difference between two readings, item by item; items are paired by their place on the menu, then what is left over is listed."""
    ia, ib = a.get("items", []), b.get("items", [])
    out = [f"item count: {len(ia)} vs {len(ib)}"] if len(ia) != len(ib) else []
    for n, (x, y) in enumerate(zip(ia, ib), start=1):
        out += [f"item {n} ({str(x.get('name'))[:40]}), {k}: {x.get(k)!r} vs {y.get(k)!r}" for k in FIELDS if x.get(k) != y.get(k)]
    longer, label = (ia, "first") if len(ia) > len(ib) else (ib, "second")
    out += [f"only in the {label} reading: {x.get('name')!r}" for x in longer[min(len(ia), len(ib)):]]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    runner = MenuRunner(MvpConfig())
    budget = runner.new_budget(f"reader-check-{Path(args.photo).stem}")
    try:
        (first, err1, _), (second, err2, _) = runner.read_menu(args.photo, budget, save=False), runner.read_menu(args.photo, budget, save=False)
    finally:
        budget.close()
    if first is None or second is None:
        print("a reading failed:", err1, err2)
        return 1
    diffs = compare_readings(first, second)
    spend = budget.report()
    lines = ["", f"## Reader check: {Path(args.photo).name}, read twice, fresh", "", f"{len(first.get('items', []))} and {len(second.get('items', []))} items; {len(diffs)} differences; ${spend['model_usd_total']}, {spend['model_calls']} calls.", ""]
    lines += [f"- {d}" for d in diffs] or ["The two readings are identical."]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
