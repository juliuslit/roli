"""Orchestration for one menu item: search both modes, merge, fetch, extract, parse, convert, dedup, count."""

from __future__ import annotations

from decimal import Decimal

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any

from .convert import apply_embedded_weight, convert_weight
from .extract import ExtractionCache, extract_recipe
from .fetch import PoliteFetcher
from .models import FetchOutcome, IngestionResult, IngestionStats, MenuItem, SearchMode, SourceRecipe
from .parse import parse_lines, parse_servings
from .search import RecipeSource, host_of, merge_hits

MAX_FETCH_PER_DISH = 12
GENERIC_SECTIONS = {"to start", "starters", "starter", "appetizers", "appetizer", "antipasti", "small plates", "entree", "entrees", "entrée", "entrées",
                    "mains", "main", "main courses", "large plates", "sides", "side", "dessert", "desserts", "bread", "no section", "", "menu", "specials"}
COOKING_VERBS = re.compile(r"\b(roast|roasted|bake|baked|grill|grilled|broil|broiled|fry|fried|saute|sauté|sautéed|sear|seared|boil|boiled|"
                           r"steam|steamed|braise|braised|toast|toasted|simmer|poach|poached|char|charred|smoke|smoked|raw|uncooked)\b", re.I)


# 12.10.4: a price with its sign, a size or weight, or a bare number closing the text (the price of a section heading, "DESSERTS 8")
SIZE_OR_PRICE = re.compile(r"[£$€]\s*\d+(?:[.,]\d+)?|\b\d+(?:[.,]\d+)?\s*(?:oz|ounces?|g|grams?|kg|lbs?|pounds?|ml|cl|litres?|liters?|inch(?:es)?|cm)\b|(?:^|\s)\d+(?:[.,]\d+)?\s*$")


def clean_query(text: str) -> str:
    """12.10.4, one rule for every dish: lower case; sizes, weights and prices dropped; punctuation, asterisks and footnote marks removed. What the reader
    writes reaches the search, so "FISH OF THE DAY." and "FISH OF THE DAY" must be one search."""
    return " ".join(re.sub(r"[^\w\s]|_", " ", SIZE_OR_PRICE.sub(" ", text.lower())).split())


def default_queries(item: MenuItem) -> dict[SearchMode, str]:
    """Deterministic queries from the menu text (2B-1 experiment, 2026-11-02, 15 searches on the five dishes):
    the dish name alone finds recipes *for the dish* (crudo, little gem salad, king salmon), while adding every
    menu ingredient drifts to recipes about the ingredients (bottarga pasta instead of crudo). The first listed
    ingredient helps on the structured-host search (margherita, salmon with squash). An LLM query writer is
    an option for 2B-2; nothing here calls one."""
    words = [w for w in (clean_query(x) for x in item.description.split(",")) if w]
    section = clean_query(item.section)
    # A specific section word disambiguates the dish ("margherita recipe" finds cocktails; "margherita pizza recipe" does not).
    # Generic course headings add nothing and are skipped.
    dish = clean_query(item.name)
    if section and section not in GENERIC_SECTIONS and section not in dish:
        dish = f"{dish} {section}"
    base = f"{dish} recipe"
    return {"open": base, "structured_hosts": f"{base} {words[0]}".strip() if words else base}


def topup_query(item: MenuItem) -> str:
    """3K (12.20): the second search for a dish that ended on too few usable recipes: the dish name plus the first two printed ingredients not already in the
    name, then "recipe". Deterministic, from the menu's own words, like `default_queries`."""
    dish = clean_query(item.name)
    extra = []
    for seg in item.description.split(","):
        w = clean_query(seg)
        if w and w not in dish and w not in extra and not SIZE_OR_PRICE.search(seg):
            extra.append(w)
        if len(extra) == 2:
            break
    return " ".join([dish, *extra, "recipe"]).strip()


def content_hash(lines: list[str]) -> str:
    norm = sorted(re.sub(r"[^a-z0-9]+", " ", l.lower()).strip() for l in lines)
    return hashlib.sha256("\n".join(norm).encode()).hexdigest()[:16]


def ingest_dish(item: MenuItem, *, source: RecipeSource, fetcher: PoliteFetcher, queries: dict[SearchMode, str] | None = None,
                llm: Any | None = None, parse_json_object=None, max_fetch: int = MAX_FETCH_PER_DISH,
                extraction_cache: ExtractionCache | None = None, modes: tuple[str, ...] = ("open", "structured_hosts"), skip_urls: set[str] | None = None) -> IngestionResult:
    """3K: ``modes`` limits the searches (the top-up runs "open" only, one credit); ``skip_urls`` are canonical URLs already read for the dish, left out before the fetch cap."""
    started = time.perf_counter()
    queries = queries or default_queries(item)
    notes: list[str] = []

    # 1. search, both modes (D12)
    results_by_mode: dict[SearchMode, list[dict]] = {}
    credits = 0
    credits_before = getattr(source, "credits_used", None)
    for mode in modes:
        if mode not in queries:
            continue
        try:
            results_by_mode[mode] = source.search(queries[mode], mode)
            credits += 1
        except Exception as exc:
            results_by_mode[mode] = []
            notes.append(f"search failed in mode {mode}: {type(exc).__name__}")
    if credits_before is not None:
        credits = getattr(source, "credits_used", credits_before) - credits_before   # a cached source spends nothing
    hits, blocked = merge_hits(results_by_mode)
    if skip_urls:
        hits = [h for h in hits if h.canonical_url not in skip_urls]
    hits_both = sum(1 for h in hits if len(h.found_by) == 2)

    # 2. fetch (politely) and 3–5. extract, parse, convert
    fetches: list[FetchOutcome] = []
    recipes: list[SourceRecipe] = []
    extracted_by: dict[str, int] = {}
    extracted_from_cache = 0
    for hit in hits[:max_fetch]:
        outcome, html = fetcher.fetch(hit.url)
        fetches.append(outcome)
        if outcome.status != "ok":
            continue
        ex = extract_recipe(html, hit.url, llm=llm, parse_json_object=parse_json_object, cache=extraction_cache)
        extracted_by[ex.method] = extracted_by.get(ex.method, 0) + 1
        if "extraction_from_cache" in ex.flags:
            extracted_from_cache += 1
        if not ex.ingredient_lines:
            continue
        servings, low, high, note = parse_servings(ex.yield_text)
        flags = list(ex.flags)
        if servings is None and ex.yield_text:
            # Approved 2026-11-03: an explicit unit yield ("One 12-inch pizza", "makes two pizzas") gives the recipe basis one serving per unit.
            # A diameter or a slice count is never read as a unit count (unit_count_from_text matches unit words only).
            from .portions import unit_count_from_text
            units = unit_count_from_text(ex.yield_text, "")
            if units["k"] and units["source"] == "yield_text":
                servings, note = Decimal(units["k"]), f"unit yield '{ex.yield_text}': {units['k']} unit(s); recipe basis is per unit, not per person (servings_from_unit_yield)"
                flags.append("servings_from_unit_yield")
        parsed = [apply_embedded_weight(convert_weight(p)) for line in ex.ingredient_lines for p in parse_lines(line)]
        if len(parsed) >= 5 and not any(i.quantity is not None for i in parsed):
            flags.append("no_quantities_listicle_suspect")   # e.g. "21 Heirloom Tomato Recipes": names, no amounts
        recipes.append(SourceRecipe(
            url=hit.url, canonical_url=hit.canonical_url, host=host_of(hit.url), title=ex.title or hit.title, found_by=list(hit.found_by),
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), extraction=ex.method,
            yield_text=ex.yield_text, servings=servings, servings_note=note, servings_low=low, servings_high=high,
            ingredient_lines=list(ex.ingredient_lines), instructions_text=ex.instructions_text,
            cooking_verbs=sorted({m.lower() for m in COOKING_VERBS.findall(ex.instructions_text)}),
            ingredients=parsed, content_hash=content_hash(ex.ingredient_lines), flags=flags, yield_source=ex.yield_source,
        ))

    # 6. content dedup: same normalised ingredient lines under different URLs (print views, syndication)
    seen: dict[str, str] = {}
    for r in recipes:
        if r.content_hash in seen:
            r.duplicate_of = seen[r.content_hash]
            r.flags.append("content_duplicate")
        else:
            seen[r.content_hash] = r.canonical_url
    distinct = [r for r in recipes if r.duplicate_of is None]

    # 7. statistics (requirement 6: usable quantities and yields, not only extraction)
    total_lines = sum(r.n_lines for r in distinct)
    stats = IngestionStats(
        searches=len(results_by_mode), search_credits=credits,
        hits_open=len(results_by_mode.get("open", [])), hits_structured=len(results_by_mode.get("structured_hosts", [])),
        hits_after_url_dedup=len(hits), hits_in_both_modes=hits_both, blocked_hosts_skipped=blocked,
        fetched=len(fetches), fetch_ok=sum(1 for f in fetches if f.status == "ok"), fetch_from_cache=sum(1 for f in fetches if f.from_cache),
        robots_disallowed=sum(1 for f in fetches if f.status == "robots_disallowed"),
        rate_limited=sum(1 for f in fetches if f.status == "rate_limited"),
        http_errors=sum(1 for f in fetches if f.status in ("http_error", "network_error", "too_large", "not_html")),
        refused_hosts_skipped=sum(1 for f in fetches if f.status == "host_refused"),
        extracted=len(recipes), extracted_by=extracted_by, extracted_from_cache=extracted_from_cache, content_duplicates=len(recipes) - len(distinct), distinct_recipes=len(distinct),
        with_servings=sum(1 for r in distinct if r.servings is not None),
        pct_lines_quantified=round(100 * sum(r.n_quantified for r in distinct) / total_lines, 1) if total_lines else 0.0,
        pct_lines_grams_known=round(100 * sum(r.n_grams_known for r in distinct) / total_lines, 1) if total_lines else 0.0,
        recipes_with_all_lines_quantified=sum(1 for r in distinct if r.n_lines and r.n_quantified == r.n_lines),
        seconds=round(time.perf_counter() - started, 1),
    )
    return IngestionResult(menu_item=item, queries=queries, hits=hits, fetches=fetches, recipes=recipes, stats=stats, notes=notes)
