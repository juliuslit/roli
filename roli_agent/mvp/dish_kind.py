"""Dish kind by model (SPEC_3_mvp.md 12.16.11): one call per menu classifies every food item into a card family, or "not a dish", "drink" or "add-on", with a one-line reason.

Code checks every answer: the family must exist (`portions.FAMILIES`); the reader's own add-on rules win (an item the reader filed as an add-on, a drink or an option of another item keeps
that, whatever the model says); an unknown or missing answer falls back to the word lists (`portions.dish_type_for`) and is logged. The model never writes a number. Answers are saved like
tags (12.9.5), keyed by the item's words, the prompt version and the model, so a rerun repeats. On since 12.18 (Julius, 2026-11-07): `MvpConfig.dish_kind_model` is True; the word
lists are the fallback when the call fails or returns a kind that is not on the list, and every fallback is logged (`log["fallbacks"]`, one entry per item with the reason).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..recipes.judgements import item_key, prompt_version
from ..recipes.models import MenuItem
from ..recipes.portions import FAMILIES, dish_type_for

NOT_DISHES = ("not a dish", "drink", "add-on")
TTL_SECONDS = 30 * 24 * 3600

DISH_KIND_PROMPT = """You sort the items of one restaurant menu into kinds of dish, so that each can be given a typical plate size. You do not estimate nutrition and you never write a number.

Kinds (use the key on the left, exactly):
{families}
- "not a dish": a heading, a note, a set-menu line, a platter or board to share
- "drink": a drink
- "add-on": an extra sold to go with another item (a side of bacon, extra cheese)

Rules:
- Judge from the item's own words and its section. A section that lists several kinds at once ("Starters, Salads, Sides, Dips") says nothing on its own; the item's name decides.
- A soup is "soup" whatever is in it. A dip, sauce, dressing or butter sold alone is "dip". A dish served in a bun is a burger or sandwich even when it names the meat.
- A plated main course of vegetables, rice or noodles with no family of its own takes the nearest kind: "vegetable_starter" for vegetable or paneer mains, "side_rice" for a rice main, "pasta_main" for noodles.
- When in doubt between two kinds, choose the one whose plate is smaller.

Menu items (index, section, name, printed ingredients):
{items}

Answer with ONE JSON object and nothing else:
{{"items": [{{"index": 0, "kind": "soup", "reason": "a few words"}}, ...]}}
Include every index exactly once."""
PROMPT_VERSION = prompt_version(DISH_KIND_PROMPT, "families-1")


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    kind: str
    reason: str = Field(default="", max_length=200)


class _Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[_Row]


class DishKind(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: str | None                          # the family used (validated), None for no family
    source: str                                 # model | word_list | reader
    model_kind: str = ""                        # what the model said
    reason: str = ""
    note: str = ""


class DishKindCache:
    """One file per item under ``<dir>/dish_kind/``: the model's own answer, re-validated on every load."""

    def __init__(self, directory: str | Path, model_id: str, *, ttl: float = TTL_SECONDS, clock: Callable[[], float] = time.time) -> None:
        self.dir, self.model_id, self.ttl, self._clock = Path(directory) / "dish_kind", model_id, ttl, clock
        self._lock = threading.Lock()

    def _path(self, item: MenuItem) -> Path:
        raw = json.dumps([item_key(item), PROMPT_VERSION, self.model_id])
        return self.dir / f"{hashlib.sha1(raw.encode('utf-8')).hexdigest()}.json"

    def get(self, item: MenuItem) -> dict[str, str] | None:
        try:
            entry = json.loads(self._path(item).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(entry, dict) or "answer" not in entry or self._clock() - float(entry.get("saved_at", 0)) > self.ttl:
            return None
        return entry["answer"]

    def put(self, item: MenuItem, answer: dict[str, str]) -> None:
        path = self._path(item)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps({"saved_at": self._clock(), "item": item_key(item), "prompt_version": PROMPT_VERSION, "model": self.model_id, "answer": answer}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def _families_text() -> str:
    return "\n".join(f'- "{k}": {v}' for k, v in FAMILIES.items())


def validate_kind(item: MenuItem, kind: str, reason: str, *, reader_category: str = "food", belongs_to: str = "") -> DishKind:
    """Python's reading of one answer. The reader's filing wins for add-ons, drinks and options; an unknown kind falls back to the word lists and says so."""
    if reader_category != "food":
        return DishKind(family=None, source="reader", model_kind=kind, reason=reason, note=f"the reader filed it as {reader_category}")
    if belongs_to:
        return DishKind(family=None, source="reader", model_kind=kind, reason=reason, note="an option of another item (reader)")
    k = (kind or "").strip().lower().replace(" ", "_") if kind not in NOT_DISHES else kind
    if kind in NOT_DISHES:
        return DishKind(family=None, source="model", model_kind=kind, reason=reason)
    if k in FAMILIES:
        return DishKind(family=k, source="model", model_kind=kind, reason=reason)
    fallback = dish_type_for(item)
    return DishKind(family=fallback, source="word_list", model_kind=kind, reason=reason, note=f"unknown kind '{kind[:30]}': the word lists answered")


def classify_menu(items: list[dict[str, Any]], llm: Any, parse_json_object, *, cache: DishKindCache | None = None) -> tuple[dict[int, DishKind], dict[str, Any]]:
    """{menu index: DishKind} for every item of the reader's menu. One call for the items with no saved answer; a failed call leaves every unsaved item to the word lists."""
    out: dict[int, DishKind] = {}
    menu_items: dict[int, MenuItem] = {}
    to_ask: list[int] = []
    answers: dict[int, dict[str, str]] = {}
    for i, raw in enumerate(items):
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            continue
        item = MenuItem(name=str(raw.get("name", "")).strip(), description=str(raw.get("description") or "").strip(), section=str(raw.get("section") or "").strip())
        menu_items[i] = item
        saved = cache.get(item) if cache is not None else None
        if saved is None:
            to_ask.append(i)
        else:
            answers[i] = saved
    log: dict[str, Any] = {"called": bool(to_ask), "items": len(menu_items), "from_saved": len(menu_items) - len(to_ask), "fallback": 0, "fallbacks": []}
    if to_ask:
        listing = "\n".join(f"{i}. [{menu_items[i].section or 'no section'}] {menu_items[i].name}" + (f": {menu_items[i].description[:120]}" if menu_items[i].description else "") for i in to_ask)
        prompt = DISH_KIND_PROMPT.format(families=_families_text(), items=listing)
        try:
            reply = llm.invoke([HumanMessage(content=prompt)])
            content = getattr(reply, "content", reply)
            parsed = _Reply.model_validate(parse_json_object(content if isinstance(content, str) else str(content)) or {})
        except (ValidationError, Exception) as exc:  # noqa: BLE001
            log["error"] = type(exc).__name__ if not isinstance(exc, ValidationError) else f"invalid_reply:{len(exc.errors())}_problems"
            parsed = None
        if parsed is not None:
            for row in parsed.items:
                if row.index in to_ask:
                    answers[row.index] = {"kind": row.kind, "reason": row.reason}
                    if cache is not None:
                        cache.put(menu_items[row.index], answers[row.index])
    for i, item in menu_items.items():
        raw = items[i]
        a = answers.get(i)
        if a is None and (str(raw.get("category") or "food") != "food" or str(raw.get("belongs_to") or "").strip()):
            out[i] = DishKind(family=None, source="reader", note=f"the reader filed it as {raw.get('category') or 'an option of another item'}; no model answer needed")
        elif a is None:
            out[i] = DishKind(family=dish_type_for(item), source="word_list", note="no model answer")
        else:
            out[i] = validate_kind(item, a.get("kind", ""), a.get("reason", ""), reader_category=str(raw.get("category") or "food"), belongs_to=str(raw.get("belongs_to") or "").strip())
        if out[i].source == "word_list":                  # 12.18: every fallback is logged: a failed or missing answer, or a kind that is not on the list
            log["fallback"] += 1
            log["fallbacks"].append({"index": i, "name": item.name[:60], "why": out[i].note or "no model answer", "word_lists_said": out[i].family})
    return out, log
