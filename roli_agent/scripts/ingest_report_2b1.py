"""Phase 2B-1 live report: ingest the five Flour + Water dishes, print statistics, save fixtures of the extracted facts.

    .venv/bin/python -m roli_agent.scripts.ingest_report_2b1 [--out roli_agent/tests/fixtures/recipes]

Uses Tavily (2 credits per dish) and fetches recipe pages politely (disk cache under .cache/). Fixtures store
only facts: URL, title, host, found_by, fetched_at, extraction method, verbatim ingredient lines, yield text,
cooking verbs detected, and the parsed values. Instructions prose is not saved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from roli_agent.config import ROOT
from roli_agent.recipes import ingest_dish
from roli_agent.recipes.fetch import FetchCache, PoliteFetcher
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.search import TavilySource

DISHES = [
    MenuItem(name="BLUEFIN CRUDO", description="bottarga, muscat grape, chive", section="TO START"),
    MenuItem(name="LITTLE GEM LETTUCES", description="tahini vinaigrette, pecorino sardo, toasted sesame", section="TO START"),
    MenuItem(name="HEIRLOOM TOMATOES", description="pluot, shiso, genovese basil, sourdough", section="TO START"),
    MenuItem(name="MARGHERITA", description="tomato, fior di latte, basil", section="PIZZA"),
    MenuItem(name="KING SALMON", description="squash, corn, basil, shishito", section="ENTREE"),
]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "roli_agent" / "tests" / "fixtures" / "recipes"))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    source = TavilySource()
    fetcher = PoliteFetcher(cache=FetchCache(ROOT / ".cache" / "roli_recipes"))
    summary = []
    for item in DISHES:
        result = ingest_dish(item, source=source, fetcher=fetcher)
        s = result.stats
        summary.append((item.name, s))
        print(f"\n## {item.name} ({item.description})  queries: {result.queries['open']!r}")
        print(f"hits: open {s.hits_open}, structured {s.hits_structured}, after URL dedup {s.hits_after_url_dedup} (in both modes {s.hits_in_both_modes}; blocked skipped {s.blocked_hosts_skipped})")
        print(f"fetched {s.fetched}: ok {s.fetch_ok} (cache {s.fetch_from_cache}), robots {s.robots_disallowed}, 429 {s.rate_limited}, other errors {s.http_errors}")
        print(f"extracted {s.extracted} by {s.extracted_by}; content duplicates {s.content_duplicates}; distinct {s.distinct_recipes}; with servings {s.with_servings}")
        print(f"lines quantified {s.pct_lines_quantified}%, grams known now {s.pct_lines_grams_known}%, recipes fully quantified {s.recipes_with_all_lines_quantified}; {s.seconds}s")
        for note in result.notes:
            print("note:", note)
        for r in result.recipes:
            dup = f" DUPLICATE of {r.duplicate_of}" if r.duplicate_of else ""
            print(f"  - [{','.join(r.found_by)}] {r.host} | {r.title[:50]!r} | {r.extraction} | yield={r.yield_text[:20]!r} -> servings={r.servings} | "
                  f"lines={r.n_lines} quantified={r.n_quantified} grams={r.n_grams_known} | verbs={r.cooking_verbs[:6]}{dup}")
        # fixtures: facts only
        fixture = {"menu_item": item.model_dump(), "queries": result.queries, "stats": s.model_dump(),
                   "recipes": [r.model_dump(mode="json", exclude={"instructions_text"}) for r in result.recipes]}
        (out / f"{slug(item.name)}.json").write_text(json.dumps(fixture, indent=1, ensure_ascii=False), encoding="utf-8")

    print("\n## Totals")
    tot = Counter()
    for _, s in summary:
        for k in ("hits_after_url_dedup", "hits_in_both_modes", "fetched", "fetch_ok", "robots_disallowed", "rate_limited", "http_errors",
                  "extracted", "content_duplicates", "distinct_recipes", "with_servings", "recipes_with_all_lines_quantified", "search_credits"):
            tot[k] += getattr(s, k)
    print(dict(tot))
    print("tavily credits used:", source.credits_used)
    return 0


if __name__ == "__main__":
    sys.exit(main())
