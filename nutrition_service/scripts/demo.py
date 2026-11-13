"""Print real results for the Checkpoint 1A report.

    nutrition_service/.venv/bin/python scripts/demo.py

Live USDA calls: 171999, 172001 (cache miss then hit, timed), the king salmon
search, not_found (99999999) and invalid_input (0). The id_mismatch case cannot
be produced by the real API (USDA always returns the ID asked for), so it uses
the saved 171999 reply with its fdcId edited to 172001, through the mock
transport, and says so.
"""

from __future__ import annotations

import copy
import json
import logging
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVICE_DIR.parent
FIXTURES = SERVICE_DIR / "tests" / "fixtures" / "usda"
sys.path.insert(0, str(SERVICE_DIR))

from roli_nutrition import NutritionService, Settings  # noqa: E402
from roli_nutrition.usda_client import UsdaClient  # noqa: E402


def show(title: str, result, note: str | None = None) -> None:
    print(f"\n### {title}")
    if note:
        print(f"_{note}_")
    print("```json")
    print(result.model_dump_json(indent=2))
    print("```")


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx's own request lines: off in scripts, untouched in the library
    load_dotenv(REPO_ROOT / ".env")
    service = NutritionService(Settings.from_env())

    r, miss_ms = timed(lambda: service.get_nutrition(171999))
    show("get_nutrition(171999), cache miss", r, f"{miss_ms:.0f} ms, {len(r.model_dump_json())} bytes")
    r, hit_ms = timed(lambda: service.get_nutrition(171999))
    show("get_nutrition(171999), cache hit", r, f"{hit_ms:.2f} ms")

    r, ms = timed(lambda: service.get_nutrition(172001))
    show("get_nutrition(172001)", r, f"{ms:.0f} ms, {len(r.model_dump_json())} bytes")

    r, ms = timed(lambda: service.search_foods("king salmon cooked dry heat", 10))
    show("search_foods('king salmon cooked dry heat', 10)", r, f"{ms:.0f} ms, {len(r.model_dump_json())} bytes")

    show("get_nutrition(99999999) -> not_found", service.get_nutrition(99999999))
    show("get_nutrition(0) -> invalid_input", service.get_nutrition(0))

    # id_mismatch: saved real reply for 171999 with fdcId edited to 172001.
    body = json.loads((FIXTURES / "food_171999.json").read_text(encoding="utf-8"))
    edited = copy.deepcopy(body)
    edited["fdcId"] = 172001
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=edited))
    offline = NutritionService(Settings.from_env(), client=UsdaClient("unused", transport=transport))
    show(
        "get_nutrition(171999) -> id_mismatch",
        offline.get_nutrition(171999),
        "saved food_171999.json with fdcId edited to 172001, served through the mock transport",
    )

    print(f"\nTimings: cache miss {miss_ms:.0f} ms, cache hit {hit_ms:.2f} ms", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
