"""Save the USDA replies Checkpoint 3D's tests replay (spec v2.3). Run once, with the real key; about 25 requests.

    nutrition_service/.venv/bin/python scripts/capture_fixtures_3d.py

Adds to tests/fixtures/usda/: the ``POST /foods/list`` replies used for release detection (newest publication date per table, one row), the
records a rebuilt "Fish, NS as to type, fried" needs (its inputs resolved by exact description, plus the cod / haddock / pollock and vegetable
oil / beef tallow choices of the fish_and_chips card), and the exact-description searches that resolve them. Manifest entries are appended.
Headers are not saved; the key is never printed or written.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
SERVICE_DIR = HERE.parent
REPO_ROOT = SERVICE_DIR.parent
FIXTURES = SERVICE_DIR / "tests" / "fixtures" / "usda"
sys.path.insert(0, str(SERVICE_DIR))
from roli_nutrition.config import Settings  # noqa: E402
from roli_nutrition.usda_client import BASE_URL, DETAIL_QUERY, TIMEOUT  # noqa: E402

FOODS = {174191: "cod Pacific raw (input of the US fried-fish mix)", 171955: "cod Atlantic raw (card choice)", 171964: "haddock raw (card choice)",
         175129: "pollock Atlantic raw (card choice)", 171400: "beef tallow (card choice)", 2710180: "Vegetable oil, NFS (Survey input)",
         2710785: "Breading or batter as ingredient in food (Survey input)", 175138: "pink salmon raw (input)", 175167: "Atlantic salmon farmed raw (input)",
         175165: "catfish channel farmed raw (input)", 175176: "tilapia raw (input)", 167749: "lemon peel raw (near-zero rule)",
         2709458: "Potato, french fries, from fresh, fried (3E: inputs include the oil)", 170093: "Potatoes, baked, flesh and skin (3E chips input)", 170033: "Potatoes, baked, flesh (3E chips input)", 171826: "Sauce, tartar, ready-to-serve (3E tartare row)", 169096: "Olives, green, SR Legacy (3E olive row)",
         2705730: "Cheese, Parmesan, hard (3F D25 test)", 2705778: "Cheese, cottage cheese, with gelatin dessert (3F D25 test)", 2709614: "Spinach, raw (3F D25 test)", 2709628: "Spinach, creamed (3F D25 test)",
         2709395: "Potato, boiled, peel eaten, no added fat (3F new potatoes row)", 2709397: "Potato, boiled, peel eaten, made with butter (3F buttered new potatoes row)"}
EXACT_SEARCHES = {"Breading or batter as ingredient in food": ["Survey (FNDDS)"], "Vegetable oil, NFS": ["Survey (FNDDS)"],
                  "Fish, cod, Pacific, raw (may have been previously frozen)": ["Foundation", "SR Legacy"], "Fish, salmon, pink, raw": ["Foundation", "SR Legacy"],
                  "Fish, salmon, Atlantic, farmed, raw": ["Foundation", "SR Legacy"], "Fish, catfish, channel, farmed, raw": ["Foundation", "SR Legacy"],
                  "Fish, tilapia, raw": ["Foundation", "SR Legacy"], "Salt, table": ["Foundation", "SR Legacy"], "Fish, haddock, raw": ["Foundation", "SR Legacy"],
                  "Potatoes, baked, flesh and skin, without salt": ["Foundation", "SR Legacy"], "Potatoes, baked, flesh, without salt": ["Foundation", "SR Legacy"],
                  "Cheese parmesan": ["Survey (FNDDS)"], "Cheese": ["Survey (FNDDS)"], "Spinach baby": ["Survey (FNDDS)"], "Spinach": ["Survey (FNDDS)"]}
LISTS = {"list_foundation_newest": ["Foundation"], "list_survey_newest": ["Survey (FNDDS)"], "list_sr_legacy_newest": ["SR Legacy"]}


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    settings = Settings.from_env()
    client = httpx.Client(base_url=BASE_URL, headers={"X-Api-Key": settings.api_key}, timeout=TIMEOUT)
    manifest_path = FIXTURES / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    def save(name: str, data, request_desc: str, status: int) -> None:
        path = FIXTURES / f"{name}.json"
        text = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")
        manifest[path.name] = {"request": request_desc, "status": status, "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "bytes": len(text.encode("utf-8")), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        print(f"  saved {path.name} ({len(text)} chars)")

    for fid, why in FOODS.items():
        if (FIXTURES / f"food_{fid}.json").exists() or (FIXTURES / f"food_survey_{fid}.json").exists():
            print(f"  have food_{fid} already ({why})")
            continue
        r = client.get(f"/food/{fid}?{DETAIL_QUERY}")
        print(f"  GET /food/{fid}  ->  {r.status_code}  ({why})")
        if r.status_code == 200:
            body = r.json()
            save(f"food_survey_{fid}" if body.get("dataType") == "Survey (FNDDS)" else f"food_{fid}", body, f"GET /food/{fid}?{DETAIL_QUERY}", 200)
    for q, types in EXACT_SEARCHES.items():
        if (FIXTURES / ("search_exact_" + "".join(c if c.isalnum() else "_" for c in q.lower())[:50].strip("_") + ".json")).exists():
            continue
        body = {"query": q, "dataType": types, "pageSize": 10}
        r = client.post("/foods/search", json=body)
        print(f"  POST /foods/search {q!r}  ->  {r.status_code}")
        if r.status_code == 200:
            name = "search_exact_" + "".join(c if c.isalnum() else "_" for c in q.lower())[:50].strip("_")
            save(name, r.json(), f"POST /foods/search {json.dumps(body)}", 200)
    for name, types in LISTS.items():
        if (FIXTURES / f"{name}.json").exists():
            continue
        body = {"dataType": types, "pageSize": 1, "pageNumber": 1, "sortBy": "publishedDate", "sortOrder": "desc"}
        r = client.post("/foods/list", json=body)
        print(f"  POST /foods/list {types}  ->  {r.status_code}  remaining {r.headers.get('x-ratelimit-remaining')}")
        if r.status_code == 200:
            save(name, r.json(), f"POST /foods/list {json.dumps(body)}", 200)
    # the ascending order of the same table proves the sort is honoured (its date must be older than the descending one)
    if not (FIXTURES / "list_foundation_oldest.json").exists():
        body = {"dataType": ["Foundation"], "pageSize": 1, "pageNumber": 1, "sortBy": "publishedDate", "sortOrder": "asc"}
        r = client.post("/foods/list", json=body)
        if r.status_code == 200:
            save("list_foundation_oldest", r.json(), f"POST /foods/list {json.dumps(body)}", 200)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
