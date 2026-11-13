"""Saved USDA answers on disk (spec v2.3, section 18; Julius, 2026-11-05: "saved answers on disk; refresh by USDA release, never on a timer").

What is saved: the raw JSON body USDA returned for one food (``GET /food/{id}``) or one search (``POST /foods/search``), with the time it was saved,
the food's data type and ``publicationDate`` as USDA states them, and the FoodData Central release label the store knew at the time. The service
re-parses a saved body exactly as it parses a fresh one, so a saved answer can never carry a number USDA did not. Refused or failed answers are
never saved (there is nothing to save: the service only calls ``put_*`` after a successful parse).

Layout under ``<dir>``::

    food/<fdc_id>.json          one file per food record
    search/<key>.json           one file per search (query, limit, tables), key = sha1 of the request
    release.json                the newest publicationDate per data type, as detected by the service (section 18.4)
    staging/                    a refresh in progress (same layout); becomes live only when promoted
    snapshots/<label>/          the live answers as they were before a promotion

Writes are atomic (write to a temporary file, then rename) and guarded by one lock, so threads and two processes sharing a store cannot
leave a half-written file. Reads tolerate a corrupt file (it is treated as absent).

Stale answers (section 18.4 safety net): SR Legacy is a final release and never stale; a Foundation or Survey answer, or a saved search, older
than ``stale_days`` is reported by ``stale_entries`` and refreshed by ``scripts/refresh_usda.py`` into staging. The live answer stays in use
until Julius promotes the staging set; the store never swaps data on its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SR_LEGACY = "SR Legacy"
REFRESHABLE_TYPES = ("Foundation", "Survey (FNDDS)")          # SR Legacy (April 2018) is final and is never refreshed
DEFAULT_STALE_DAYS = 213                                      # 7 months (proposal in SPEC_3_mvp.md 12.5); a setting, not a constant, see Settings


FOOD_NUTRIENTS = "606,601,204"                                # what a saved food was asked for (spec v2.5); entries saved earlier have no such key and no total fat


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def search_key(query: str, limit: int, data_types: tuple[str, ...] | None) -> str:
    """One key per distinct search request: lower-cased trimmed query, the limit and the table set, hashed so it is a safe file name."""
    raw = json.dumps([query.strip().lower(), int(limit), list(data_types) if data_types else None])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class AnswerStore:
    def __init__(self, directory: str | Path, *, stale_days: int = DEFAULT_STALE_DAYS, clock=_now) -> None:
        self.dir = Path(directory)
        self.stale_days = int(stale_days)
        self._clock = clock
        self._lock = threading.Lock()
        self._release: dict[str, Any] | None = None

    # -- paths -------------------------------------------------------------------------------------------------------------------

    def _food_path(self, fdc_id: int, area: str = "") -> Path:
        return self.dir / area / "food" / f"{int(fdc_id)}.json" if area else self.dir / "food" / f"{int(fdc_id)}.json"

    def _search_path(self, key: str, area: str = "") -> Path:
        return self.dir / area / "search" / f"{key}.json" if area else self.dir / "search" / f"{key}.json"

    # -- read ---------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) and "body" in data else None

    def get_food(self, fdc_id: int) -> dict[str, Any] | None:
        """The saved entry (``body`` plus its metadata) for a food, or None. The caller parses ``body`` as it would a fresh reply."""
        return self._read(self._food_path(fdc_id))

    def get_search(self, query: str, limit: int, data_types: tuple[str, ...] | None) -> dict[str, Any] | None:
        return self._read(self._search_path(search_key(query, limit, data_types)))

    # -- write ---------------------------------------------------------------------------------------------------------------------

    def _write(self, path: Path, entry: dict[str, Any]) -> None:
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)

    def _entry(self, body: Any, request: dict[str, Any], data_type: str | None, publication_date: str | None) -> dict[str, Any]:
        release = self.release()
        return {"saved_at": _iso(self._clock()), "data_type": data_type, "publication_date": publication_date,
                "release": {t: (release.get(t) or {}).get("latest_publication_date") for t in release} if release else {},
                "request": request, "body": body}

    def put_food(self, fdc_id: int, body: dict[str, Any], *, area: str = "") -> None:
        """Save one successfully parsed food reply. Never called for an error: the service saves only what it could validate."""
        entry = self._entry(body, {"call": "food", "fdc_id": int(fdc_id), "nutrients": FOOD_NUTRIENTS}, body.get("dataType") if isinstance(body, dict) else None,
                            body.get("publicationDate") if isinstance(body, dict) else None)
        self._write(self._food_path(fdc_id, area), entry)

    def put_search(self, query: str, limit: int, data_types: tuple[str, ...] | None, body: Any, *, area: str = "") -> None:
        types = list(data_types) if data_types else None
        entry = self._entry(body, {"call": "search", "query": query.strip().lower(), "limit": int(limit), "data_types": types}, None, None)
        entry["data_type"] = "search:" + ",".join(types or ["Foundation", SR_LEGACY])
        self._write(self._search_path(search_key(query, limit, data_types), area), entry)

    # -- release (section 18.4) -------------------------------------------------------------------------------------------------

    def release(self) -> dict[str, Any]:
        """``{data_type: {"latest_publication_date": "2026-10-29", "checked_at": iso}}`` as last detected; empty when never checked."""
        if self._release is None:
            self._release = self._read_release()
        return dict(self._release)

    def _read_release(self) -> dict[str, Any]:
        path = self.dir / "release.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def write_release(self, release: dict[str, Any]) -> None:
        with self._lock:
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.dir / f"release.{os.getpid()}.tmp"
            tmp.write_text(json.dumps(release, indent=1), encoding="utf-8")
            os.replace(tmp, self.dir / "release.json")
        self._release = dict(release)

    # -- inventory ------------------------------------------------------------------------------------------------------------------

    def entries(self, area: str = "") -> Iterable[tuple[Path, dict[str, Any]]]:
        base = self.dir / area if area else self.dir
        for sub in ("food", "search"):
            folder = base / sub
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.json")):
                entry = self._read(path)
                if entry is not None:
                    yield path, entry

    def stats(self) -> dict[str, Any]:
        foods = searches = 0
        by_type: dict[str, int] = {}
        oldest: str | None = None
        for _, entry in self.entries():
            kind = (entry.get("request") or {}).get("call")
            if kind == "food":
                foods += 1
                t = entry.get("data_type") or "unknown"
                by_type[t] = by_type.get(t, 0) + 1
            else:
                searches += 1
            saved = entry.get("saved_at")
            if saved and (oldest is None or saved < oldest):
                oldest = saved
        stale = self.stale_entries()
        return {"dir": str(self.dir), "foods": foods, "searches": searches, "foods_by_type": by_type, "oldest_saved_at": oldest,
                "stale": len(stale), "stale_days": self.stale_days, "release": self.release(),
                "staging": sum(1 for _ in self.entries("staging")), "snapshots": sorted(p.name for p in (self.dir / "snapshots").iterdir()) if (self.dir / "snapshots").is_dir() else []}

    def stale_entries(self, now: datetime | None = None) -> list[tuple[Path, dict[str, Any]]]:
        """Foundation and Survey foods and saved searches older than ``stale_days``. SR Legacy answers are never stale (final release)."""
        now = now or self._clock()
        cutoff = _iso(now - timedelta(days=self.stale_days))
        out = []
        for path, entry in self.entries():
            t = entry.get("data_type") or ""
            if t == SR_LEGACY:
                continue
            if (entry.get("saved_at") or "") < cutoff:
                out.append((path, entry))
        return out

    def entries_of_types(self, data_types: Iterable[str]) -> list[tuple[Path, dict[str, Any]]]:
        """Foods of the given data types plus every saved search (a new release can change which record a search picks)."""
        wanted = set(data_types)
        out = []
        for path, entry in self.entries():
            t = entry.get("data_type") or ""
            if t in wanted or t.startswith("search:"):
                out.append((path, entry))
        return out

    # -- staging and snapshots (section 18.4: new data goes live only when promoted) -----------------------------------------------

    def staged_count(self) -> int:
        return sum(1 for _ in self.entries("staging"))

    def snapshot(self, label: str | None = None) -> Path:
        """Copy the live answers to ``snapshots/<label>/`` (label = the current UTC time when not given)."""
        label = label or self._clock().strftime("%Y%m%d-%H%M%S")
        dest = self.dir / "snapshots" / label
        with self._lock:
            dest.mkdir(parents=True, exist_ok=True)
            for sub in ("food", "search"):
                src = self.dir / sub
                if src.is_dir():
                    shutil.copytree(src, dest / sub, dirs_exist_ok=True)
            rel = self.dir / "release.json"
            if rel.exists():
                shutil.copy2(rel, dest / "release.json")
        return dest

    def promote_staging(self, *, snapshot_label: str | None = None) -> dict[str, Any]:
        """Make the staged answers live: snapshot the live set first, then move each staged file over its live counterpart.
        Only ever called by a person's explicit command (``scripts/refresh_usda.py --promote``); the service never calls it."""
        staged = list(self.entries("staging"))
        if not staged:
            return {"promoted": 0, "snapshot": None}
        snap = self.snapshot(snapshot_label)
        moved = 0
        with self._lock:
            for path, _ in staged:
                target = self.dir / path.relative_to(self.dir / "staging")
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, target)
                moved += 1
            staged_release = self.dir / "staging" / "release.json"
            if staged_release.exists():
                os.replace(staged_release, self.dir / "release.json")
                self._release = None
        return {"promoted": moved, "snapshot": str(snap)}

    def discard_staging(self) -> int:
        n = self.staged_count()
        with self._lock:
            shutil.rmtree(self.dir / "staging", ignore_errors=True)
        return n
