"""Phase 2A: capture the extra real USDA records the recipe-calculator tests use (spec 2A, section 11).

    nutrition_service/.venv/bin/python scripts/capture_recipe_fixtures.py

Reuses the Phase 1A capture class; adds files to tests/fixtures/usda/ and merges them into
manifest.json without touching the Phase 1A files. About 9 USDA calls. Never prints the key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from capture_fixtures import FIXTURES, DETAIL_PARAMS, Capture  # noqa: E402
from roli_nutrition.config import ConfigError, Settings  # noqa: E402

# Records chosen from the Phase 1D traces (Flour + Water ingredients) plus the two salmon records already saved.
RECIPE_RECORDS = {
    173706: "Fish, tuna, fresh, bluefin, raw",
    170189: "Seeds, sesame butter, tahini, from roasted and toasted kernels (most common type)",
    171249: "Cheese, romano",
    170151: "Seeds, sesame seeds, whole, roasted and toasted",
    169249: "Lettuce, green leaf, raw",
    170457: "Tomatoes, red, ripe, raw, year round average",
    172675: "Bread, french or vienna (includes sourdough)",
}
OLIVE_OIL_DESCRIPTION = "Oil, olive, salad or cooking"


def main() -> int:
    load_dotenv(HERE.parent.parent / ".env")
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Cannot capture: {exc}")
        return 2
    cap = Capture(settings.api_key)
    manifest_path = FIXTURES / "manifest.json"
    if manifest_path.exists():
        cap.manifest = json.loads(manifest_path.read_text())

    print("1. olive oil: search, then detail")
    body = cap.save_body("search_oil_olive", cap.post_search("oil olive", ["SR Legacy", "Foundation"], 10),
                         'POST /foods/search {"query":"oil olive","dataType":["SR Legacy","Foundation"],"pageSize":10}')
    foods = body.get("foods") or []
    match = next((f for f in foods if f["description"] == OLIVE_OIL_DESCRIPTION), None)
    if match is None:
        print(f"   no candidate described exactly as {OLIVE_OIL_DESCRIPTION!r}; candidates were:")
        for f in foods:
            print(f"     {f['fdcId']}  {f['description']!r}  [{f['dataType']}]")
        print("   stopping: pick the record by hand and add it to RECIPE_RECORDS")
        cap.write_manifest()
        return 1
    print(f"   olive oil = {match['fdcId']}  {match['description']!r}")
    records = {match["fdcId"]: match["description"], **RECIPE_RECORDS}

    print("2. detail records (filtered, spec 5.3)")
    for fid, expected_desc in records.items():
        r = cap.get(f"/food/{fid}?{DETAIL_PARAMS}")
        if r.status_code != 200:
            print(f"   {fid}: status {r.status_code}, skipped")
            continue
        saved = cap.save_body(f"food_{fid}", r, f"GET /food/{fid}?{DETAIL_PARAMS}")
        flag = "" if saved.get("description") == expected_desc else f"   (description differs: {saved.get('description')!r})"
        print(f"   {fid}: {saved.get('description')!r} [{saved.get('dataType')}]{flag}")

    cap.write_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
