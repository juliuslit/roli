"""Save real USDA replies as test fixtures (spec 13.1). Run once, with the real key.

    nutrition_service/.venv/bin/python scripts/capture_fixtures.py

Writes JSON bodies to tests/fixtures/usda/ and a manifest.json with, per file:
method, path with parameters (never the key), status, capture time, byte size and
SHA-256. Response headers are not saved. The key is never printed or written.

About 15 USDA calls. The first call confirms that the X-Api-Key header is
accepted; on 403 the script stops (spec A.5, 5.1).
"""

from __future__ import annotations

import hashlib
import json
import logging
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
from roli_nutrition.config import ConfigError, Settings  # noqa: E402
from roli_nutrition.usda_client import BASE_URL, DETAIL_QUERY, TIMEOUT  # noqa: E402

DETAIL_PARAMS = DETAIL_QUERY  # "format=full&nutrients=606,601"


class Capture:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.Client(base_url=BASE_URL, headers={"X-Api-Key": api_key}, timeout=TIMEOUT)
        self.manifest: dict[str, dict] = {}
        FIXTURES.mkdir(parents=True, exist_ok=True)

    # -- requests -----------------------------------------------------------

    def get(self, path: str, *, with_key: bool = True) -> httpx.Response:
        headers = {} if with_key else {"X-Api-Key": ""}  # empty header value = no key
        response = self._client.get(path, headers=headers)
        print(f"  GET  {path}  ->  {response.status_code}  ({len(response.content)} bytes)")
        return response

    def post_search(self, query: str, data_types: list[str], page_size: int) -> httpx.Response:
        body = {"query": query, "dataType": data_types, "pageSize": page_size}
        response = self._client.post("/foods/search", json=body)
        print(f"  POST /foods/search {json.dumps(body)}  ->  {response.status_code}  ({len(response.content)} bytes)")
        return response

    # -- saving -------------------------------------------------------------

    def save_body(self, name: str, response: httpx.Response, request_desc: str) -> dict:
        body = response.json()
        self._write(name, body, response.status_code, request_desc)
        return body

    def save_error(self, name: str, response: httpx.Response, request_desc: str) -> None:
        try:
            body = response.json()
        except ValueError:
            body = response.text
        self._write(name, {"status": response.status_code, "body": body}, response.status_code, request_desc)

    def _write(self, name: str, data, status: int, request_desc: str) -> None:
        path = FIXTURES / f"{name}.json"
        text = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")
        raw = text.encode("utf-8")
        self.manifest[path.name] = {
            "request": request_desc,
            "status": status,
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        print(f"       saved {path.name}")

    def write_manifest(self) -> None:
        (FIXTURES / "manifest.json").write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")
        print(f"\nManifest: {len(self.manifest)} files -> {FIXTURES / 'manifest.json'}")


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv(REPO_ROOT / ".env")
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Cannot capture: {exc}")
        return 2

    cap = Capture(settings.api_key)

    # 1. Chinook salmon, filtered. Also confirms the X-Api-Key header.
    print("1. food 171999 (filtered)")
    r = cap.get(f"/food/171999?{DETAIL_PARAMS}")
    if r.status_code == 403:
        print("USDA answered 403 with the key in the X-Api-Key header. Stopping (spec A.5).")
        return 1
    if r.status_code != 200:
        print(f"Unexpected status {r.status_code} on the first call. Stopping.")
        return 1
    cap.save_body("food_171999", r, f"GET /food/171999?{DETAIL_PARAMS}")

    # 2. Pink salmon, filtered.
    print("2. food 172001 (filtered)")
    cap.save_body("food_172001", cap.get(f"/food/172001?{DETAIL_PARAMS}"), f"GET /food/172001?{DETAIL_PARAMS}")

    # 3. Both, unfiltered full format.
    print("3. unfiltered full replies")
    for fid in (171999, 172001):
        cap.save_body(f"food_{fid}_unfiltered", cap.get(f"/food/{fid}?format=full"), f"GET /food/{fid}?format=full")

    # 4 + 5. The two searches from spec 13.1.
    print("4. search: king salmon cooked dry heat")
    cap.save_body(
        "search_king_salmon",
        cap.post_search("king salmon cooked dry heat", ["Foundation", "SR Legacy"], 10),
        'POST /foods/search {"query":"king salmon cooked dry heat","dataType":["Foundation","SR Legacy"],"pageSize":10}',
    )
    print("5. search: salmon chinook cooked dry heat")
    cap.save_body(
        "search_salmon_chinook",
        cap.post_search("salmon chinook cooked dry heat", ["Foundation", "SR Legacy"], 10),
        'POST /foods/search {"query":"salmon chinook cooked dry heat","dataType":["Foundation","SR Legacy"],"pageSize":10}',
    )

    # 6 + 7. A Foundation animal food and a Foundation plant food (no cholesterol row expected).
    for step, query, slug in ((6, "salmon", "salmon"), (7, "broccoli raw", "broccoli_raw")):
        print(f"{step}. Foundation search: {query}")
        body = cap.save_body(
            f"search_foundation_{slug}",
            cap.post_search(query, ["Foundation"], 5),
            f'POST /foods/search {{"query":"{query}","dataType":["Foundation"],"pageSize":5}}',
        )
        foods = body.get("foods") or []
        if not foods:
            print(f"   no Foundation result for '{query}'; skipping its detail")
            continue
        fid = foods[0]["fdcId"]
        print(f"   first result: {fid}  {foods[0]['description']!r}")
        cap.save_body(f"food_foundation_{fid}", cap.get(f"/food/{fid}?{DETAIL_PARAMS}"), f"GET /food/{fid}?{DETAIL_PARAMS}")

    # 8. A Branded food: must come back as unsupported_data_type.
    print("8. Branded search: salmon")
    body = cap.save_body(
        "search_branded_salmon",
        cap.post_search("salmon", ["Branded"], 1),
        'POST /foods/search {"query":"salmon","dataType":["Branded"],"pageSize":1}',
    )
    foods = body.get("foods") or []
    if foods:
        fid = foods[0]["fdcId"]
        print(f"   first result: {fid}  {foods[0]['description']!r}")
        cap.save_body(f"food_branded_{fid}", cap.get(f"/food/{fid}?{DETAIL_PARAMS}"), f"GET /food/{fid}?{DETAIL_PARAMS}")
    else:
        print("   no Branded result; skipping its detail")

    # 9. Error replies, saved as {status, body}.
    print("9. error replies")
    cap.save_error("error_404", cap.get("/food/99999999"), "GET /food/99999999")
    cap.save_error("error_400", cap.get("/food/abc"), "GET /food/abc")
    cap.save_error("error_403", cap.get(f"/food/171999?{DETAIL_PARAMS}", with_key=False), f"GET /food/171999?{DETAIL_PARAMS} (no key)")

    cap.write_manifest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
