"""USDA record matching for recipe ingredients (spec 2B section 7, D7): the Phase 1E path, batched.

Per batch of ingredient names: one LLM call writes USDA-style queries, Python runs `service.search_foods`
for each, one LLM call picks a record per ingredient from *its own* candidate list, Python applies the
structural guard (an ID not in that list is rejected) and the state check (a raw hint may not take a cooked
record and vice versa). Accepted decisions are cached on disk by (name, preparation hint); a cached proxy
stays a proxy. Numbers never pass through here: only FDC IDs and descriptions.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, ValidationError

from roli_nutrition import ErrorResult, NutritionService, SearchResult
from roli_nutrition.recipe.preparation import record_state

from ..prompts import QUERY_BATCH_PROMPT, SELECT_BATCH_PROMPT
from ..selection import accept_proposed_id
from .models import MatchDecision, PreparationHint

SEARCH_LIMIT = 10
BATCH_SIZE = 12          # 12 ingredients x 10 candidates keeps one selection prompt around 10K characters
CACHE_TTL_SECONDS = 30 * 24 * 3600


def normalise_name(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zà-ü0-9 ]+", " ", name.lower())).strip()


@dataclass
class MatchRequest:
    name: str
    preparation_hint: PreparationHint = "unknown"
    category: str = ""                          # 3K (12.20): the line's food category from the tag call; not part of the cache key

    @property
    def key(self) -> str:
        return f"{normalise_name(self.name)}|{self.preparation_hint}"


# 3K (12.20): when a line in a zero-fat category matches no USDA record (no candidates, the model declined, the guard refused), code searches once for the category's
# fixed record and accepts only the exact description. Only categories whose record carries no fat: the record then bounds the line at zero saturated fat whatever its
# amount (12.14.12), which is the whole point. A composition category (cheese, meat) never gets a code-chosen record: that would be a guess no model made (D7).
CATEGORY_FALLBACK = {"wine_or_spirit": ("wine table all", "Alcoholic beverage, wine, table, all"), "beer": ("beer regular all", "Alcoholic beverage, beer, regular, all"),
                     "salt": ("salt table", "Salt, table"), "water_or_stock": ("water tap drinking", "Beverages, water, tap, drinking")}
FALLBACK_ISSUES = ("no_candidates", "llm_declined", "selection_missing", "guard_rejected")


class MatchCache:
    """Validated (name, hint) -> record decisions, 30 days, on disk (D7). Unresolved decisions are never cached.

    3J (2026-11-07, found by the 3I repeatability check): a PROXY decision is the model's reading of one dish's context ("the dish is vegan, so soy milk stands in for
    whole milk"), so it is saved under the dish's context and reused only for that dish; a direct match of the same food is reused everywhere. A proxy saved without a
    context (the files written before this change) is not reused."""

    @staticmethod
    def context_key(key: str, context: str) -> str:
        return f"{key}|dish:{hashlib.sha1(context.encode('utf-8')).hexdigest()[:12]}"

    def __init__(self, path: Path | None, ttl: float = CACHE_TTL_SECONDS, clock: Callable[[], float] = time.time) -> None:
        import threading
        self.path = path
        self.ttl = ttl
        self.clock = clock
        self._lock = threading.Lock()               # Phase 3: several dishes of one menu are matched in parallel threads
        self._data: dict[str, dict] = {}
        if path is not None and path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                self._data = {}

    def get(self, key: str, context: str = "") -> MatchDecision | None:
        entry = self._data.get(self.context_key(key, context))      # a proxy is saved under the dish's context, the empty context included
        if entry is None:
            entry = self._data.get(key)
            if entry and entry.get("decision", {}).get("match_type") == "proxy":
                return None                                 # a proxy chosen in another dish's context is not this dish's match
        if not entry or self.clock() - entry.get("saved_at", 0) > self.ttl:
            return None
        decision = dict(entry["decision"])
        if decision.get("description"):
            # the record's raw/cooked state is a classification of its description, not a fact to cache: recompute it so a word-table fix
            # (Phase 3: "unprepared" bacon is raw) reaches decisions matched before the fix
            decision["record_state"] = record_state(decision["description"])
        return MatchDecision(**decision, source="cache")

    def put(self, key: str, decision: MatchDecision, context: str = "") -> None:
        if decision.match_type == "unresolved":
            return
        stored = decision.model_dump(exclude={"source"})
        if decision.match_type == "proxy":
            key = self.context_key(key, context)
        with self._lock:
            self._data[key] = {"saved_at": self.clock(), "decision": stored}
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self._data, indent=0), encoding="utf-8")

    def __len__(self) -> int:
        return len(self._data)


class _QueryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    usda_query: str


class _SelectRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    fdc_id: Any = None
    match_type: str | None = "direct"       # the model writes null when it declines
    reason: str | None = ""


@dataclass
class MatchLog:
    llm_calls: int = 0
    llm_failures: int = 0
    usda_searches: int = 0
    cache_hits: int = 0
    requested: int = 0
    distinct: int = 0
    notes: list[str] = field(default_factory=list)


class UsdaMatcher:
    def __init__(self, service: NutritionService, llm: Any, *, parse_json_object: Callable[[str], dict | None],
                 cache: MatchCache | None = None, batch_size: int = BATCH_SIZE) -> None:
        self._service = service
        self._llm = llm
        self._parse = parse_json_object
        self._cache = cache if cache is not None else MatchCache(None)
        self._batch = batch_size

    def match(self, requests: list[MatchRequest], *, context: str = "") -> tuple[dict[str, MatchDecision], MatchLog]:
        """Decisions keyed by `MatchRequest.key`. Duplicates across recipes are resolved once."""
        log = MatchLog(requested=len(requests))
        distinct: dict[str, MatchRequest] = {}
        for r in requests:
            distinct.setdefault(r.key, r)
        log.distinct = len(distinct)
        decisions: dict[str, MatchDecision] = {}
        pending: list[MatchRequest] = []
        for key, req in distinct.items():
            cached = self._cache.get(key, context)
            if cached is not None:
                decisions[key] = cached
                log.cache_hits += 1
            else:
                pending.append(req)
        for start in range(0, len(pending), self._batch):
            chunk = pending[start:start + self._batch]
            for key, decision in self._match_chunk(chunk, context, log).items():
                decisions[key] = decision
                self._cache.put(key, decision, context)
        return decisions, log

    # -- one chunk -------------------------------------------------------------

    def _llm_rows(self, prompt: str, key: str, row_model: type[BaseModel], log: MatchLog) -> list[BaseModel] | None:
        """One LLM call -> the validated rows under `key`. Rows are validated one by one (strict, extra keys refused),
        so a malformed row loses only its own ingredient; an unusable reply loses the batch and is recorded."""
        log.llm_calls += 1
        try:
            reply = self._llm.invoke([HumanMessage(content=prompt)])
        except Exception as exc:
            log.llm_failures += 1
            log.notes.append(f"llm call failed: {type(exc).__name__}: {str(exc)[:120]}")
            return None
        content = getattr(reply, "content", reply)
        text = content if isinstance(content, str) else str(content)
        data = self._parse(text)
        rows = (data or {}).get(key)
        if not isinstance(rows, list):
            log.llm_failures += 1
            log.notes.append(f"llm reply had no '{key}' list; reply started: {text[:160]!r}")
            return None
        valid: list[BaseModel] = []
        for row in rows:
            try:
                valid.append(row_model.model_validate(row))
            except ValidationError as exc:
                log.notes.append(f"{row_model.__name__} row rejected: {exc.errors()[0].get('loc')} {exc.errors()[0].get('msg')}")
        return valid

    def _match_chunk(self, chunk: list[MatchRequest], context: str, log: MatchLog) -> dict[str, MatchDecision]:
        ids = {i + 1: req for i, req in enumerate(chunk)}
        # 1. queries (LLM); fallback: the ingredient name itself, which is deterministic and still a USDA search
        items = "\n".join(f'- id {i}: "{req.name}" (preparation: {req.preparation_hint})' for i, req in ids.items())
        rows = self._llm_rows(QUERY_BATCH_PROMPT.format(context=context or "a restaurant dish", items=items), "queries", _QueryRow, log)
        queries: dict[int, str] = {}
        if rows is not None:
            for row in rows:
                q = row.usda_query.strip()
                if row.id in ids and q and not re.search(r"\d", q):      # a query with digits could smuggle an ID; use the name instead
                    queries[row.id] = q[:200]
        for i, req in ids.items():
            queries.setdefault(i, normalise_name(req.name)[:200])

        # 2. search (Python); one bounded retry with the plain ingredient name when the model's query returns nothing
        candidates: dict[int, list[dict]] = {}
        errors: dict[int, str] = {}
        retried: dict[int, str] = {}
        for i, q in queries.items():
            log.usda_searches += 1
            result = self._service.search_foods(q, SEARCH_LIMIT)
            if isinstance(result, ErrorResult):
                errors[i] = f"usda_error:{result.error_code}"
                candidates[i] = []
                continue
            assert isinstance(result, SearchResult)
            candidates[i] = [c.model_dump() for c in result.candidates]
            plain = normalise_name(ids[i].name)[:200]
            if not candidates[i] and plain and plain != q.lower():
                log.usda_searches += 1
                again = self._service.search_foods(plain, SEARCH_LIMIT)
                if not isinstance(again, ErrorResult) and again.candidates:
                    candidates[i] = [c.model_dump() for c in again.candidates]
                    retried[i] = plain
                    queries[i] = plain

        # 3. selection (LLM), only for ingredients with candidates
        with_candidates = {i: c for i, c in candidates.items() if c}
        selections: dict[int, _SelectRow] = {}
        if with_candidates:
            blocks = []
            for i, cands in with_candidates.items():
                req = ids[i]
                listing = "\n".join(f"   - fdc_id {c['fdc_id']}: {c['description']} [{c['data_type']}]" for c in cands)
                blocks.append(f'Ingredient id {i}: "{req.name}" (preparation hint: {req.preparation_hint}; query used: "{queries[i]}")\n{listing}')
            sel = self._llm_rows(SELECT_BATCH_PROMPT.format(context=context or "a restaurant dish", blocks="\n\n".join(blocks)), "selections", _SelectRow, log)
            if sel is not None:
                for row in sel:
                    if row.id in with_candidates and row.id not in selections:
                        selections[row.id] = row

        # 4. guard + state check (Python)
        out: dict[str, MatchDecision] = {}
        for i, req in ids.items():
            base = dict(name=normalise_name(req.name), preparation_hint=req.preparation_hint, query=queries[i], candidates_seen=len(candidates[i]), source="llm",
                        candidates=[{"fdc_id": c["fdc_id"], "description": c["description"], "data_type": c["data_type"]} for c in candidates[i]],
                        retried_with_plain_name=i in retried)
            if i in errors:
                out[req.key] = MatchDecision(**base, issue=errors[i])
                continue
            if not candidates[i]:
                out[req.key] = MatchDecision(**base, issue="no_candidates")
                continue
            row = selections.get(i)
            if row is None:
                out[req.key] = MatchDecision(**base, issue="selection_missing")
                continue
            reason = str(row.reason)[:300]
            if row.fdc_id is None:
                out[req.key] = MatchDecision(**base, reason=reason, issue="llm_declined")
                continue
            accepted = accept_proposed_id(row.fdc_id, [c["fdc_id"] for c in candidates[i]])
            if accepted is None:
                out[req.key] = MatchDecision(**base, reason=reason, issue="guard_rejected")
                continue
            chosen = next(c for c in candidates[i] if c["fdc_id"] == accepted)
            state = record_state(chosen["description"])
            if (req.preparation_hint == "raw" and state == "cooked") or (req.preparation_hint == "cooked" and state == "raw"):
                out[req.key] = MatchDecision(**base, reason=reason, issue=f"state_conflict:{req.preparation_hint}_vs_{state}",
                                             description=chosen["description"], fdc_id=None)
                continue
            match_type = "proxy" if str(row.match_type).lower() == "proxy" else "direct"
            out[req.key] = MatchDecision(**base, fdc_id=accepted, description=chosen["description"], data_type=chosen["data_type"],
                                         record_state=state, match_type=match_type, reason=reason)
        # 5. 3K (12.20): a line in a zero-fat category that matched nothing takes the category's fixed record, found by one code-run search and accepted only on the exact description
        for i, req in ids.items():
            d = out.get(req.key)
            if d is None or d.issue not in FALLBACK_ISSUES or req.category not in CATEGORY_FALLBACK:
                continue
            q, preferred = CATEGORY_FALLBACK[req.category]
            log.usda_searches += 1
            found = self._service.search_foods(q, SEARCH_LIMIT)
            if isinstance(found, ErrorResult):
                continue
            hit = next((c for c in found.candidates if c.description == preferred), None)
            if hit is None:
                log.notes.append(f"category fallback: '{preferred}' not among USDA's candidates for '{q}'; {req.name!r} stays {d.issue}")
                continue
            out[req.key] = MatchDecision(name=normalise_name(req.name), preparation_hint=req.preparation_hint, query=q, fdc_id=hit.fdc_id, description=hit.description, data_type=hit.data_type,
                                         record_state=record_state(hit.description), match_type="proxy", source="llm", candidates_seen=d.candidates_seen, candidates=d.candidates,
                                         reason=f"category fallback (12.20): the line matched no record ({d.issue}); the tag call read it as {req.category}, so the fixed zero-fat record "
                                                f"'{preferred}' stands in; it bounds the line at no saturated fat whatever its amount", category_fallback=req.category)
            log.notes.append(f"category fallback: {req.name!r} -> {preferred} ({req.category})")
        return out
