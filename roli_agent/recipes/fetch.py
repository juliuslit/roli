"""Fetch recipe pages politely: robots.txt, bounded per-host back-off on 429, size cap, on-disk cache.

Failed pages (SPEC_3_mvp.md 12.12.7): a live run retries every failed page and keeps a note of the ones that failed. A test rerun with `reuse_saved_reading` on is sealed: a page that failed
in the saved pass stays failed, so the rerun reads the same pages. In 3F a page that failed in pass A loaded in pass B, the one difference between the passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Callable
from urllib import robotparser
from urllib.parse import urlsplit

import httpx

from .models import FetchOutcome

USER_AGENT = "Mozilla/5.0 (compatible; RoliRecipeBot/0.1; nutrition research; contact via repository)"
MAX_BYTES = 1_000_000
TIMEOUT = 10.0
BACKOFF_SECONDS = (2.0, 4.0)        # at most two retries on 429, then the host is left alone for this run
HOST_COOLDOWN_SECONDS = 600.0       # after exhausting retries, skip that host for the rest of the run
CACHE_TTL_SECONDS = 30 * 24 * 3600
REFUSAL_STATUSES = {401, 403, 451}
REFUSAL_WINDOW_SECONDS = 7 * 24 * 3600
REFUSALS_BEFORE_SKIP = 2            # D17: a host that refused twice in a week is not asked again this week


class RefusalMemory:
    """Hosts that refuse scripted clients (403 and the like), remembered across runs so they are not hammered (D17).
    Stored next to the page cache. A single refusal is retried on a later run; repeated ones are skipped."""

    def __init__(self, path: Path | None, clock: Callable[[], float] = time.time) -> None:
        self.path = path
        self.clock = clock
        self._data: dict[str, dict] = {}
        if path is not None and path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                self._data = {}

    def record(self, host: str, status: int) -> None:
        entry = self._data.setdefault(host, {"count": 0, "last": 0.0, "status": status})
        if self.clock() - entry["last"] > REFUSAL_WINDOW_SECONDS:
            entry["count"] = 0
        entry.update(count=entry["count"] + 1, last=self.clock(), status=status)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=0), encoding="utf-8")

    def should_skip(self, host: str) -> bool:
        entry = self._data.get(host)
        return bool(entry) and entry["count"] >= REFUSALS_BEFORE_SKIP and self.clock() - entry["last"] <= REFUSAL_WINDOW_SECONDS

    def count(self, host: str) -> int:
        return self._data.get(host, {}).get("count", 0)


class FetchCache:
    """Page bodies cached on disk by URL hash for 30 days (spec 3.2). Not part of the repo."""

    def __init__(self, directory: Path, ttl: float = CACHE_TTL_SECONDS, clock: Callable[[], float] = time.time) -> None:
        self.directory = directory
        self.ttl = ttl
        self.clock = clock
        directory.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        return self.directory / (hashlib.sha256(url.encode()).hexdigest() + ".json")

    def get(self, url: str) -> dict | None:
        path = self._path(url)
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        if self.clock() - entry["fetched_at_epoch"] > self.ttl:
            return None
        return entry

    def put(self, url: str, status: int, text: str) -> None:
        self._path(url).write_text(json.dumps({"url": url, "status": status, "text": text, "fetched_at_epoch": self.clock()}), encoding="utf-8")


class FailedPages:
    """The pages that failed in the latest live pass, by URL, with the outcome. Live: a failure is noted, a success clears it. Sealed: read only."""

    def __init__(self, path: Path, *, sealed: bool = False) -> None:
        self.path, self.sealed = Path(path), sealed
        self._lock = threading.Lock()
        try:
            self._data: dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._data = {}

    def kept(self, url: str) -> FetchOutcome | None:
        entry = self._data.get(url) if self.sealed else None
        return FetchOutcome(**{**entry, "detail": f"failed in the saved pass and kept failed (12.12.7): {entry.get('detail') or entry['status']}"[:200]}) if entry else None

    def note(self, outcome: FetchOutcome) -> None:
        if self.sealed or (outcome.status == "ok" and outcome.url not in self._data):
            return
        with self._lock:
            if outcome.status == "ok":
                del self._data[outcome.url]
            else:
                self._data[outcome.url] = outcome.model_dump(mode="json")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(self._data, indent=0), encoding="utf-8")
            os.replace(tmp, self.path)


class PoliteFetcher:
    def __init__(self, *, cache: FetchCache | None = None, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
                 respect_robots: bool = True, refusals: RefusalMemory | None = None, failed_pages: FailedPages | None = None) -> None:
        self._client = httpx.Client(headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                                    timeout=TIMEOUT, follow_redirects=True, transport=transport)
        self._cache = cache
        self._failed = failed_pages
        self._sleep = sleep
        self._clock = clock
        self._respect_robots = respect_robots
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self._cooldown_until: dict[str, float] = {}
        self._refusals = refusals if refusals is not None else RefusalMemory(cache.directory / "refused_hosts.json" if cache is not None else None)

    # -- robots ----------------------------------------------------------------

    def _allowed(self, url: str) -> bool:
        if not self._respect_robots:
            return True
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if host not in self._robots:
            parser = robotparser.RobotFileParser()
            try:
                r = self._client.get(f"{parts.scheme}://{parts.netloc}/robots.txt")
                if r.status_code == 200:
                    parser.parse(r.text.splitlines())
                    self._robots[host] = parser
                else:
                    self._robots[host] = None     # no usable robots file: allowed
            except httpx.HTTPError:
                self._robots[host] = None
        parser = self._robots[host]
        return True if parser is None else parser.can_fetch(USER_AGENT, url)

    # -- fetch -------------------------------------------------------------------

    def fetch(self, url: str) -> tuple[FetchOutcome, str]:
        """Returns (outcome, html). html is '' unless outcome.status == 'ok'."""
        kept = self._failed.kept(url) if self._failed is not None else None
        if kept is not None:
            return kept, ""
        outcome, html = self._fetch(url)
        if self._failed is not None:
            self._failed.note(outcome)
        return outcome, html

    def _fetch(self, url: str) -> tuple[FetchOutcome, str]:
        host = urlsplit(url).netloc.lower()
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None and cached["status"] == 200:
                return FetchOutcome(url=url, status="ok", http_status=200, from_cache=True, seconds=0.0), cached["text"]
        if self._cooldown_until.get(host, 0.0) > self._clock():
            return FetchOutcome(url=url, status="rate_limited", detail="host in cool-down after repeated 429"), ""
        if self._refusals.should_skip(host):
            return FetchOutcome(url=url, status="host_refused", detail=f"host refused scripted access {self._refusals.count(host)} times this week; not asked again (D17)"), ""
        if not self._allowed(url):
            return FetchOutcome(url=url, status="robots_disallowed"), ""

        started = self._clock()
        attempt = 0
        while True:
            try:
                response = self._client.get(url)
            except httpx.HTTPError as exc:
                return FetchOutcome(url=url, status="network_error", seconds=self._clock() - started, detail=type(exc).__name__), ""
            if response.status_code == 429:
                if attempt < len(BACKOFF_SECONDS):
                    self._sleep(BACKOFF_SECONDS[attempt])
                    attempt += 1
                    continue
                self._cooldown_until[host] = self._clock() + HOST_COOLDOWN_SECONDS
                return FetchOutcome(url=url, status="rate_limited", http_status=429, seconds=self._clock() - started,
                                    detail=f"429 after {attempt} retries; host cooled down"), ""
            break

        elapsed = self._clock() - started
        if response.status_code != 200:
            if response.status_code in REFUSAL_STATUSES:
                self._refusals.record(host, response.status_code)
            return FetchOutcome(url=url, status="http_error", http_status=response.status_code, seconds=elapsed), ""
        if len(response.content) > MAX_BYTES:
            return FetchOutcome(url=url, status="too_large", http_status=200, seconds=elapsed), ""
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type and "<html" not in response.text[:2000].lower():
            return FetchOutcome(url=url, status="not_html", http_status=200, seconds=elapsed, detail=content_type[:60]), ""
        if self._cache is not None:
            self._cache.put(url, 200, response.text)
        return FetchOutcome(url=url, status="ok", http_status=200, seconds=elapsed), response.text
