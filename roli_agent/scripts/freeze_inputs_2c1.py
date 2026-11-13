"""Phase 2C.1 controlled evaluation, step 1: freeze the inputs.

Re-ingests the five Flour + Water dishes OFFLINE from the 2B-2 caches (search results, page bodies, extraction results): no Tavily,
no page fetch, no LLM. Joins every recipe with the saved run's relevance outcome and frozen USDA matching decisions (per verbatim line,
from `roli_agent/eval/2b2_live_2026-11-02_2c_v2.json`). Writes `roli_agent/eval/frozen_inputs_2c1.json` and prints its SHA-256.

    .venv/bin/python -m roli_agent.scripts.freeze_inputs_2c1 [--run roli_agent/eval/2b2_live_2026-11-02_2c_v2.json]

A search-cache or extraction-cache miss is an error; a page-cache miss answers 404 (only successful pages were cached), never a network call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import httpx

from roli_agent.config import ROOT
from roli_agent.recipes.extract import ExtractionCache
from roli_agent.recipes.fetch import FetchCache, PoliteFetcher
from roli_agent.recipes.ingest import ingest_dish
from roli_agent.recipes.search import CachedSource
from roli_agent.scripts.ingest_report_2b1 import DISHES, slug


class NoNetworkSource:
    credits_used = 0

    def search(self, query, mode, max_results=10):
        raise RuntimeError(f"search cache miss for {mode!r} {query!r}: the frozen inputs must come from the caches only")


def no_network(request: httpx.Request) -> httpx.Response:
    # Only 200 HTML pages are cached; a miss is a page that failed before (video, 403, not HTML). Answer 404 so it fails the same way now.
    return httpx.Response(404, content=b"")


class NoLLM:
    def invoke(self, messages):
        raise RuntimeError("extraction cache miss: an LLM extraction would be needed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=str(ROOT / "roli_agent" / "eval" / "2b2_live_2026-11-02_2c_v2.json"))
    parser.add_argument("--cache-dir", default=str(ROOT / ".cache" / "roli_recipes_2b2"))
    parser.add_argument("--out", default=str(ROOT / "roli_agent" / "eval" / "frozen_inputs_2c1.json"))
    args = parser.parse_args()
    cache_dir = Path(args.cache_dir)
    saved = json.loads(Path(args.run).read_text(encoding="utf-8"))
    source = CachedSource(NoNetworkSource(), cache_dir / "search")
    fetcher = PoliteFetcher(cache=FetchCache(cache_dir / "pages"), transport=httpx.MockTransport(no_network), sleep=lambda s: None, respect_robots=False)
    extraction_cache = ExtractionCache(cache_dir / "extractions")
    out = {"source_run": args.run, "dishes": {}}
    for item in DISHES:
        result = ingest_dish(item, source=source, fetcher=fetcher, llm=NoLLM(), parse_json_object=lambda t: None, extraction_cache=extraction_cache)
        est = saved["cold"][slug(item.name)]
        by_url = {sc["source"]["canonical_url"]: sc for sc in est["scenarios"]}
        recipes, decisions = [], {}
        for r in result.recipes:
            sc = by_url.get(r.canonical_url)
            dump = r.model_dump(mode="json")
            dump["saved_relevance"] = sc["relevance"] if sc else None
            dump["saved_status"] = (sc["status"], sc.get("status_reason")) if sc else None
            dump["saved_scenario_id"] = sc["scenario_id"] if sc else None
            recipes.append(dump)
            if sc and sc["status"] == "calculated":
                for l in sc["ingredients"]:
                    if l["origin"] == "recipe" and l.get("match"):
                        decisions[l["line"]] = l["match"]
                    elif l["origin"] == "menu_only" and l.get("match"):
                        decisions[f"menu_only:{l['name']}"] = l["match"]
        out["dishes"][slug(item.name)] = {"menu_item": item.model_dump(), "recipes": recipes, "frozen_decisions_by_line": decisions,
                                          "ingestion_stats": result.stats.model_dump(mode="json")}
        print(f"{item.name:22s} recipes {len(result.recipes):2d} (distinct {result.stats.distinct_recipes}), from cache: pages {result.stats.fetch_from_cache}, "
              f"extractions {result.stats.extracted_from_cache}; frozen decisions {len(decisions)}; search credits {result.stats.search_credits}")
    text = json.dumps(out, indent=1, ensure_ascii=False, default=str)
    Path(args.out).write_text(text, encoding="utf-8")
    print("written:", args.out, "sha256:", hashlib.sha256(text.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
