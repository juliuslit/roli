"""Refresh saved USDA answers by release, never on a timer (spec v2.3, section 18.4; SPEC_3_mvp.md 12.5 item 4).

    nutrition_service/.venv/bin/python scripts/refresh_usda.py --status            inventory of the store, the allowance, the known release
    nutrition_service/.venv/bin/python scripts/refresh_usda.py --check             two requests: is there a newer Foundation or Survey release?
    nutrition_service/.venv/bin/python scripts/refresh_usda.py --stage             re-fetch the refreshable answers into staging, paced under the allowance
    nutrition_service/.venv/bin/python scripts/refresh_usda.py --stage --stale-only    only answers older than the stale limit (the 7-month safety net)
    nutrition_service/.venv/bin/python scripts/refresh_usda.py --promote --yes     Julius's approval: snapshot the live answers, make the staged ones live
    nutrition_service/.venv/bin/python scripts/refresh_usda.py --discard           throw the staged answers away

Staging stops by itself when the hourly allowance is down to the reserve (ROLI_USDA_RESERVE_REQUESTS, default 200) or at the first refusal;
run it again in the next hour and it continues where it left off (entries already staged are skipped). Nothing here touches the live answers
except --promote, and --promote refuses to run without --yes. The store directory comes from ROLI_USDA_STORE_DIR (Roli uses
roli/.cache/usda_store) or --store.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
SERVICE_DIR = HERE.parent
REPO_ROOT = SERVICE_DIR.parent
sys.path.insert(0, str(SERVICE_DIR))
from roli_nutrition import AnswerStore, NutritionService, Settings  # noqa: E402
from roli_nutrition.nutrients import extract_nutrition, parse_search  # noqa: E402
from roli_nutrition.store import REFRESHABLE_TYPES  # noqa: E402
from roli_nutrition.usda_client import UsdaClient, UsdaError  # noqa: E402


def stage(service: NutritionService, store: AnswerStore, client: UsdaClient, *, stale_only: bool, reserve: int, limit: int | None) -> dict:
    entries = store.stale_entries() if stale_only else store.entries_of_types(REFRESHABLE_TYPES)
    done = skipped = failed = 0
    stopped = None
    staged_paths = {p.relative_to(store.dir / "staging") for p, _ in store.entries("staging")}
    for path, entry in entries:
        if limit is not None and done >= limit:
            stopped = f"stopped at --limit {limit}"
            break
        if path.relative_to(store.dir) in staged_paths:
            skipped += 1
            continue
        ok, why = service.allowance_ok(reserve)
        if not ok:
            stopped = why
            break
        req = entry.get("request") or {}
        try:
            if req.get("call") == "food":
                reply = client.get_food(int(req["fdc_id"]))
                extract_nutrition(int(req["fdc_id"]), reply.body)                       # a reply that does not validate is not staged
                store.put_food(int(req["fdc_id"]), reply.body, area="staging")
            else:
                types = tuple(req["data_types"]) if req.get("data_types") else None
                reply = client.search(req["query"], int(req["limit"]), types)
                parse_search(req["query"], reply.body, int(req["limit"]))
                store.put_search(req["query"], int(req["limit"]), types, reply.body, area="staging")
            done += 1
        except UsdaError as exc:
            failed += 1
            if exc.code == "rate_limited":
                stopped = "USDA refused a request: staging stops for this hour"
                break
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  not staged {path.name}: {type(exc).__name__}")
    # the staged set carries the pending release as its live label, so promotion records which release the answers came from
    release = store.release()
    staged_release = {t: {"latest_publication_date": (v.get("pending_publication_date") or v.get("latest_publication_date")), "checked_at": v.get("checked_at")}
                      for t, v in release.items()}
    (store.dir / "staging").mkdir(parents=True, exist_ok=True)
    (store.dir / "staging" / "release.json").write_text(json.dumps(staged_release, indent=1), encoding="utf-8")
    return {"candidates": len(entries), "staged_now": done, "already_staged": skipped, "failed": failed, "stopped": stopped, "staged_total": store.staged_count(),
            "allowance": service.usda_status()["remaining"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store", default=None, help="store directory (default ROLI_USDA_STORE_DIR, else roli/.cache/usda_store)")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--stale-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="stage at most this many answers in this run")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--yes", action="store_true", help="required with --promote: Julius has approved the new release data")
    parser.add_argument("--discard", action="store_true")
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    settings = Settings.from_env()
    store_dir = Path(args.store) if args.store else Path(settings.store_dir) if settings.store_dir else REPO_ROOT / ".cache" / "usda_store"
    store = AnswerStore(store_dir, stale_days=settings.stale_days)
    client = UsdaClient(settings.api_key, halt_seconds=settings.halt_seconds)
    service = NutritionService(settings, client=client, store=store)
    if args.status or not any([args.check, args.stage, args.promote, args.discard]):
        print(json.dumps({"store": store.stats(), "usda": service.usda_status()}, indent=1, default=str))
    if args.check:
        print(json.dumps(service.check_release(), indent=1))
    if args.stage:
        print(json.dumps(stage(service, store, client, stale_only=args.stale_only, reserve=settings.reserve_requests, limit=args.limit), indent=1))
    if args.promote:
        if not args.yes:
            print("refusing: --promote needs --yes (the new release data goes live only after Julius approves it)")
            return 2
        print(json.dumps(store.promote_staging(), indent=1))
    if args.discard:
        print(json.dumps({"discarded": store.discard_staging()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
