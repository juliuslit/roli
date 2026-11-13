"""The wider menu run (SPEC_3_mvp.md 12.14.13): every photo of the test set on the final code, split across days so no cap is ever reached.

    .venv/bin/python -m roli_agent.scripts.wider_run --skip menu_01 menu_03 menu_08 menu_23 --state roli_agent/eval/wider_run_state_3h.json

One photo at a time. A photo starts only when a whole menu's limit still fits under today's caps (its model budget and search credits, on top of today's ledger); otherwise the script waits for the
next local day. The caps are never raised. It also waits when USDA's remaining allowance is low. The state file lists each finished photo with its run id, so a stopped run resumes where it was.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import ROOT
from roli_agent.mvp.budget import Limits, SpendLedger
from roli_agent.mvp.menu_run import MenuRunner
from roli_agent.mvp.models import MvpConfig

PHOTOS = ROOT / "menu_test_set" / "telegram_1280"
USDA_MIN_REMAINING = 600


def say(text: str) -> None:
    print(f"{datetime.now().isoformat(timespec='seconds')} {text}", flush=True)


def wait_for_tomorrow() -> None:
    now = datetime.now()
    wake = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    say(f"waiting for the next day's caps, until {wake.isoformat(timespec='minutes')}")
    while datetime.now() < wake:
        time.sleep(60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument("--state", required=True)
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    limits = Limits.from_env()
    ledger = SpendLedger(ROOT / "roli_agent" / "runs" / "spend_ledger.jsonl")
    photos = [p for p in sorted(PHOTOS.glob("*.jpg")) if not any(p.name.startswith(s) for s in args.skip)]
    say(f"{len(photos)} photos, {len(state)} done already; limits {limits.as_dict()}")
    runner = MenuRunner(MvpConfig())
    for photo in photos:
        if photo.name in state:
            continue
        while True:
            today = ledger.today()
            spent, credits = today["model_usd"], today["search_credits"]
            if spent + limits.menu_usd <= limits.daily_usd and credits + limits.menu_search_credits <= limits.daily_search_credits:
                break
            say(f"today so far ${spent}, {credits} credits: another menu might not fit under ${limits.daily_usd} and {limits.daily_search_credits} credits")
            wait_for_tomorrow()
        status = runner.usda_status()
        if status.get("halted") or (status.get("remaining") is not None and status["remaining"] < USDA_MIN_REMAINING):
            say(f"USDA remaining {status.get('remaining')}: waiting an hour")
            time.sleep(3600)
        say(f"start {photo.name}; today ${spent}, {credits} credits; USDA remaining {status.get('remaining')}")
        run = runner.run(str(photo.relative_to(ROOT)))
        state[photo.name] = run.run_id
        state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
        say(f"done {photo.name}: {run.run_id} {run.status}; ranked {len(run.ranking)}, model ${(run.spend or {}).get('model_usd_total')}, credits {(run.spend or {}).get('search_credits')}, USDA {(run.usda or {}).get('requests')}")
    say("all photos done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
