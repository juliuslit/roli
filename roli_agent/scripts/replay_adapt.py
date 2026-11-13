"""Re-run Phase 2C adaptation offline on the published scenarios saved by a live run (no search, no LLM; USDA live for
records). Produces the same JSON shape with `adapted_pairs`/`internal_summary` (approved) and `experimental` replaced.

    .venv/bin/python -m roli_agent.scripts.replay_adapt roli_agent/eval/2b2_live_2026-11-02_2c.json --tag _v2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import NutritionService, Settings

from roli_agent.config import ROOT
from roli_agent.recipes.adapt import WeightsTable, adapt_pairs
from roli_agent.recipes.models import Scenario


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_json")
    parser.add_argument("--tag", default="_v2")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    service = NutritionService(Settings.from_env())
    table = WeightsTable.load()
    data = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    for name, est in data["cold"].items():
        scenarios = [Scenario(**sc) for sc in est["scenarios"]]
        frozen = [s.model_dump_json() for s in scenarios]
        for mode in ("approved", "experimental"):
            pairs, summary = adapt_pairs(scenarios, service=service, table=table, mode=mode)
            block = {"adapted_pairs": [p.model_dump(mode="json") for p in pairs], "internal_summary": summary.model_dump(mode="json")}
            if mode == "approved":
                est["adapted_pairs"], est["internal_summary"], est["adapt_mode"] = block["adapted_pairs"], block["internal_summary"], "approved"
            else:
                est["experimental"] = block
            print(f"{est['menu_item']['name']:20s} {mode:12s} {summary.statement}")
        assert [s.model_dump_json() for s in scenarios] == frozen
    out = Path(args.run_json).with_name(Path(args.run_json).stem + args.tag + ".json")
    data["replayed_adaptation"] = {"from": args.run_json, "note": "adaptation re-run offline on the saved published scenarios after table/key fixes"}
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
