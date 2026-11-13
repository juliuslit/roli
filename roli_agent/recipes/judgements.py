"""Saved model judgements (SPEC_3_mvp.md 12.9.5; Julius, 2026-11-06): relevance grades and line tags are saved like pages and reused on a rerun.

Seen in 3D: with the same saved pages the grader called one poke recipe "same dish" on one run and "variant" on the next, which changed which recipes were
processed and moved the top dish's low from 0.3 to 2.9 g. A judgement is keyed by the page (its canonical URL and the hash of its ingredient lines),
the menu item, the prompt version and the model, so a changed page, a changed prompt or another model asks again. The menu item's key ignores case and
punctuation, because the menu reader writes footnote marks differently between runs ("Caesar salad*", "Caesar salad‡").

What is saved is the model's answer as it gave it (categories and its few words). Code still validates it on every load, so a change to the validators
applies to saved answers too. Failed calls save nothing. Files are written atomically; a corrupt file reads as absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .models import MenuItem, SourceRecipe

TTL_SECONDS = 30 * 24 * 3600                    # the same life as a saved page


def prompt_version(*parts: str) -> str:
    """A prompt's version is the hash of its text, so editing a prompt can never reuse answers given to the old one."""
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def item_key(item: MenuItem) -> str:
    clean = lambda t: " ".join(re.findall(r"[a-z0-9à-ü]+", (t or "").lower()))
    return f"{clean(item.name)}|{clean(item.description)}|{clean(item.section)}"


class JudgementCache:
    def __init__(self, directory: str | Path, model_id: str, *, ttl: float = TTL_SECONDS, clock: Callable[[], float] = time.time) -> None:
        self.dir, self.model_id, self.ttl, self._clock = Path(directory), model_id, ttl, clock
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _path(self, kind: str, item: MenuItem, recipe: SourceRecipe, version: str) -> Path:
        raw = json.dumps([recipe.canonical_url, recipe.content_hash, item_key(item), version, self.model_id])
        return self.dir / kind / f"{hashlib.sha1(raw.encode('utf-8')).hexdigest()}.json"

    def get(self, kind: str, item: MenuItem, recipe: SourceRecipe, version: str) -> Any | None:
        path = self._path(kind, item, recipe, version)
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            with self._lock:
                self.misses += 1
            return None
        if not isinstance(entry, dict) or "answer" not in entry or self._clock() - float(entry.get("saved_at", 0)) > self.ttl:
            with self._lock:
                self.misses += 1
            return None
        with self._lock:
            self.hits += 1
        return entry["answer"]

    def put(self, kind: str, item: MenuItem, recipe: SourceRecipe, version: str, answer: Any) -> None:
        path = self._path(kind, item, recipe, version)
        entry = {"saved_at": self._clock(), "kind": kind, "url": recipe.canonical_url, "content_hash": recipe.content_hash, "item": item_key(item),
                 "prompt_version": version, "model": self.model_id, "answer": answer}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
