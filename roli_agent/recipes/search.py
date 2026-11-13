"""Recipe discovery: the `RecipeSource` interface, the Tavily implementation, URL canonicalisation and dedup (D1, D12)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .models import SearchHit, SearchMode

TAVILY_URL = "https://api.tavily.com/search"

# Hosts that are not recipe pages we can use: video, social, retail, paywalled recipe apps, press archives.
BLOCKED_HOST_PARTS = ("youtube.", "youtu.be", "tiktok.", "instagram.", "pinterest.", "facebook.", "reddit.", "twitter.", "x.com",
                      "amazon.", "ebay.", "etsy.", "ckbk.com", "pressreader.", "scribd.", "goodreads.")

# Publishers known to carry schema.org Recipe data (all supported by recipe-scrapers). Used by the restricted mode.
STRUCTURED_HOSTS = ["seriouseats.com", "bonappetit.com", "epicurious.com", "foodandwine.com", "food52.com", "thekitchn.com",
                    "simplyrecipes.com", "allrecipes.com", "bbcgoodfood.com", "foodnetwork.com", "delish.com", "myrecipes.com",
                    "tasteofhome.com", "eatingwell.com", "cooking.nytimes.com", "jamieoliver.com", "greatbritishchefs.com",
                    "greatitalianchefs.com", "lacucinaitaliana.com", "saveur.com"]

TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|source$|igshid)", re.I)
PRINT_PATHS = re.compile(r"/(print|wprm_print|easyrecipe-print)(/|$)", re.I)


def canonical_url(url: str) -> str:
    """Same recipe, same key: lower-case host without 'www.', no tracking parameters, no fragment,
    no trailing slash, print-view paths folded onto the article path where the pattern is known."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", parts.path) or "/"
    path = PRINT_PATHS.sub("/", path)
    path = re.sub(r"/+$", "", path) or "/"
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not TRACKING_PARAMS.match(k)])
    return urlunsplit(("https", host, path, query, ""))


def host_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_blocked(url: str) -> bool:
    return any(part in url.lower() for part in BLOCKED_HOST_PARTS)


class RecipeSource(Protocol):
    """One method: search for recipe pages. Implementations: Tavily now; others later without pipeline changes."""

    def search(self, query: str, mode: SearchMode, max_results: int = 10) -> list[dict]: ...


class TavilySource:
    def __init__(self, api_key: str | None = None, *, transport: httpx.BaseTransport | None = None, timeout: float = 30.0) -> None:
        key = api_key or os.environ.get("TAVILY_API_KEY", "")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is missing")
        self._client = httpx.Client(headers={"Authorization": f"Bearer {key}"}, timeout=timeout, transport=transport)
        self.credits_used = 0

    def search(self, query: str, mode: SearchMode, max_results: int = 10) -> list[dict]:
        body = {"query": query, "max_results": max_results, "search_depth": "basic", "include_answer": False}
        if mode == "structured_hosts":
            body["include_domains"] = STRUCTURED_HOSTS
        response = self._client.post(TAVILY_URL, json=body)
        response.raise_for_status()
        self.credits_used += 1   # basic search = 1 credit
        return response.json().get("results", []) or []


def merge_hits(results_by_mode: dict[SearchMode, list[dict]]) -> tuple[list[SearchHit], int]:
    """Deduplicate by canonical URL across modes; record every mode and rank that found each page.
    Returns (hits in first-seen order, number of blocked results skipped)."""
    merged: dict[str, SearchHit] = {}
    skipped = 0
    for mode, results in results_by_mode.items():
        for rank, item in enumerate(results, start=1):
            url = (item.get("url") or "").strip()
            if not url or is_blocked(url):
                skipped += 1
                continue
            key = canonical_url(url)
            if key in merged:
                hit = merged[key]
                if mode not in hit.found_by:
                    hit.found_by.append(mode)
                hit.ranks[mode] = min(rank, hit.ranks.get(mode, rank))
            else:
                merged[key] = SearchHit(url=url, canonical_url=key, title=(item.get("title") or "")[:200], host=host_of(url),
                                        found_by=[mode], ranks={mode: rank}, snippet=(item.get("content") or "")[:300])
    return list(merged.values()), skipped


class CachedSource:
    """Search results cached on disk (default 7 days) so a warm re-run spends no credits. Tavily's terms place no
    restriction on its output; the cache holds only URLs, titles and snippets."""

    def __init__(self, inner: RecipeSource, directory: Path, ttl: float = 7 * 24 * 3600, clock=time.time) -> None:
        self._inner = inner
        self._dir = directory
        self._ttl = ttl
        self._clock = clock
        directory.mkdir(parents=True, exist_ok=True)
        self.hits = 0

    @property
    def credits_used(self) -> int:
        return getattr(self._inner, "credits_used", 0)

    def _path(self, query: str, mode: SearchMode, max_results: int) -> Path:
        key = hashlib.sha256(f"{mode}|{max_results}|{query.lower().strip()}".encode()).hexdigest()
        return self._dir / f"{key}.json"

    def has(self, query: str, mode: SearchMode, max_results: int = 10) -> bool:
        """True when the cache would answer this search without spending a credit (Phase 3 budget: a cached search is never blocked)."""
        path = self._path(query, mode, max_results)
        if not path.exists():
            return False
        try:
            return self._clock() - json.loads(path.read_text(encoding="utf-8"))["saved_at"] <= self._ttl
        except (ValueError, KeyError):
            return False

    def search(self, query: str, mode: SearchMode, max_results: int = 10) -> list[dict]:
        path = self._path(query, mode, max_results)
        if path.exists():
            entry = json.loads(path.read_text(encoding="utf-8"))
            if self._clock() - entry["saved_at"] <= self._ttl:
                self.hits += 1
                return entry["results"]
        results = self._inner.search(query, mode, max_results)
        path.write_text(json.dumps({"saved_at": self._clock(), "query": query, "mode": mode, "results": results}), encoding="utf-8")
        return results
