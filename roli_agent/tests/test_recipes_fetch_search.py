"""2B-1 search merge/dedup and polite fetching (cache, robots, bounded 429 back-off), all on mock transports."""

from __future__ import annotations

import json

import httpx
import pytest

from roli_agent.recipes.fetch import BACKOFF_SECONDS, FetchCache, PoliteFetcher
from roli_agent.recipes.search import STRUCTURED_HOSTS, TavilySource, canonical_url, is_blocked, merge_hits


# -- canonical URLs and merge ------------------------------------------------------------


@pytest.mark.parametrize("a, b", [
    ("https://www.example.com/recipe/crudo/", "https://example.com/recipe/crudo"),
    ("https://example.com/recipe/crudo?utm_source=x&utm_medium=y", "https://example.com/recipe/crudo"),
    ("https://example.com/recipe/crudo#ingredients", "https://example.com/recipe/crudo"),
    ("https://example.com/recipe/crudo/print/123", "https://example.com/recipe/crudo/123"),
    ("http://Example.com/recipe/crudo", "https://example.com/recipe/crudo"),
])
def test_canonical_url(a, b):
    assert canonical_url(a) == canonical_url(b)


def test_canonical_keeps_meaningful_query():
    assert canonical_url("https://example.com/r?id=42&utm_source=x") == "https://example.com/r?id=42"


def test_merge_hits_dedups_across_modes_and_records_found_by():
    open_results = [{"url": "https://www.site-a.com/crudo/", "title": "A"}, {"url": "https://youtube.com/watch?v=1", "title": "video"},
                    {"url": "https://site-b.com/salad", "title": "B"}]
    structured = [{"url": "https://site-a.com/crudo?utm_source=tavily", "title": "A again"}, {"url": "https://site-c.com/x", "title": "C"}]
    hits, blocked = merge_hits({"open": open_results, "structured_hosts": structured})
    assert blocked == 1
    assert [h.host for h in hits] == ["site-a.com", "site-b.com", "site-c.com"]
    a = hits[0]
    assert a.found_by == ["open", "structured_hosts"] and a.ranks == {"open": 1, "structured_hosts": 1}
    assert hits[1].found_by == ["open"] and hits[2].found_by == ["structured_hosts"]
    assert is_blocked("https://www.pinterest.com/pin/1") and not is_blocked("https://seriouseats.com/x")


def test_tavily_source_sends_domains_only_in_structured_mode_and_counts_credits():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.headers["authorization"].startswith("Bearer ")
        return httpx.Response(200, json={"results": [{"url": "https://a.com/1", "title": "t", "content": "c"}]})
    src = TavilySource("test-tavily-key", transport=httpx.MockTransport(handler))
    assert len(src.search("q", "open")) == 1 and "include_domains" not in seen[0]
    src.search("q", "structured_hosts")
    assert seen[1]["include_domains"] == STRUCTURED_HOSTS and src.credits_used == 2


# -- polite fetcher -----------------------------------------------------------------------


class Site:
    """A fake web: robots.txt per host, pages, programmable 429s; records every request."""

    def __init__(self, robots: dict[str, str] | None = None, pages: dict[str, str] | None = None, rate_limit_first: int = 0):
        self.robots = robots or {}
        self.pages = pages or {}
        self.rate_limit_first = rate_limit_first
        self.requests: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            body = self.robots.get(request.url.host)
            return httpx.Response(200, text=body) if body is not None else httpx.Response(404)
        if self.rate_limit_first > 0:
            self.rate_limit_first -= 1
            return httpx.Response(429)
        page = self.pages.get(str(request.url))
        if page is None:
            return httpx.Response(404)
        return httpx.Response(200, text=page, headers={"content-type": "text/html"})


def make_fetcher(site: Site, tmp_path=None, **kw):
    sleeps: list[float] = []
    cache = FetchCache(tmp_path / "cache") if tmp_path else None
    fetcher = PoliteFetcher(cache=cache, transport=httpx.MockTransport(site), sleep=sleeps.append, **kw)
    return fetcher, sleeps


def test_robots_disallow_is_respected_and_not_bypassed():
    site = Site(robots={"blocked.test": "User-agent: *\nDisallow: /recipes/"}, pages={"https://blocked.test/recipes/x": "<html>r</html>"})
    fetcher, _ = make_fetcher(site)
    outcome, html = fetcher.fetch("https://blocked.test/recipes/x")
    assert outcome.status == "robots_disallowed" and html == ""
    assert all(u.endswith("/robots.txt") for u in site.requests)        # the page itself was never requested


def test_robots_allow_and_missing_robots_both_fetch():
    site = Site(robots={"ok.test": "User-agent: *\nAllow: /"}, pages={"https://ok.test/r": "<html>ok</html>", "https://norobots.test/r": "<html>nr</html>"})
    fetcher, _ = make_fetcher(site)
    assert fetcher.fetch("https://ok.test/r")[0].status == "ok"
    assert fetcher.fetch("https://norobots.test/r")[0].status == "ok"


def test_429_backoff_is_bounded_then_host_cools_down():
    site = Site(pages={"https://busy.test/r1": "<html>1</html>", "https://busy.test/r2": "<html>2</html>"}, rate_limit_first=5)
    fetcher, sleeps = make_fetcher(site)
    outcome, _ = fetcher.fetch("https://busy.test/r1")
    assert outcome.status == "rate_limited" and outcome.http_status == 429
    assert sleeps == list(BACKOFF_SECONDS)                              # exactly two retries, 2 s then 4 s
    page_requests = [u for u in site.requests if not u.endswith("robots.txt")]
    assert len(page_requests) == 3                                      # 1 attempt + 2 retries, never more
    outcome2, _ = fetcher.fetch("https://busy.test/r2")
    assert outcome2.status == "rate_limited" and "cool-down" in outcome2.detail
    assert len([u for u in site.requests if not u.endswith("robots.txt")]) == 3   # no request during cool-down


def test_429_then_success_within_budget():
    site = Site(pages={"https://flaky.test/r": "<html>ok</html>"}, rate_limit_first=1)
    fetcher, sleeps = make_fetcher(site)
    outcome, html = fetcher.fetch("https://flaky.test/r")
    assert outcome.status == "ok" and html == "<html>ok</html>" and sleeps == [BACKOFF_SECONDS[0]]


def test_cache_hit_avoids_network(tmp_path):
    site = Site(pages={"https://c.test/r": "<html>cached</html>"})
    fetcher, _ = make_fetcher(site, tmp_path)
    first, _ = fetcher.fetch("https://c.test/r")
    n = len(site.requests)
    second, html = fetcher.fetch("https://c.test/r")
    assert first.from_cache is False and second.from_cache is True and html == "<html>cached</html>"
    assert len(site.requests) == n


def test_cache_expires(tmp_path):
    now = [1_000.0]
    cache = FetchCache(tmp_path / "c", ttl=100, clock=lambda: now[0])
    cache.put("u", 200, "x")
    assert cache.get("u")["text"] == "x"
    now[0] += 101
    assert cache.get("u") is None


def test_http_error_and_non_html_are_reported():
    site = Site(pages={})
    fetcher, _ = make_fetcher(site)
    assert fetcher.fetch("https://e.test/missing")[0].status == "http_error"

    def pdf(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})
    f2 = PoliteFetcher(transport=httpx.MockTransport(pdf), sleep=lambda s: None)
    assert f2.fetch("https://e.test/file.pdf")[0].status == "not_html"
