"""Line tags: is a recipe line eaten, a cooking medium or removed, and is it a plain food or a prepared product (SPEC_3_mvp.md 12.3; Julius, 2026-11-05).

One model call per dish covers every recipe that could be processed in the run and has no saved tags (12.9.5). The model answers with categories and a few words of reason;
Python checks every answer and keeps the stricter reading when the model and the text disagree:

- ``cooking_medium`` is accepted only for fats, oils, liquids (brine, stock, water, wine, vinegar, beer, milk) and salt (12.3.1). Anything else
  tagged medium is treated as eaten and logged.
- ``removed`` is accepted only for things that are lifted out (bay leaves, sprigs, rinds, bones, aromatics, shells, skewers) or a herb or spice
  (I03 already leaves those out). Anything else tagged removed is treated as eaten and logged. (A guard the spec does not ask for: a wrong
  "removed" on a main ingredient would empty the plate; stated in the checkpoint.)
- ``kind`` is overridden to ``prepared_product`` when the line's USDA record is itself a sauce, dressing, soup, gravy or baby food, whatever the
  model said: the near-zero rule (12.4) must never pass a prepared product.

The model never writes a nutrient value, a weight or a quantity; nothing here changes a gram. If the call fails or does not validate, the dish
falls back to the text patterns of Checkpoint 3C and the diagnostics say so (12.3.4).
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..prompts import LINE_TAGS_PROMPT
from .inference import is_herb_or_spice
from .judgements import JudgementCache, item_key, prompt_version
from .models import MenuItem, SourceRecipe
from .parse import parse_line

MENU_WORDS_TITLE = "Menu words no recipe lists"
TAG_BLOCK_VERSION = "method-sentences-3-category"       # part of the prompt version: what the model is shown of each recipe; 3K added the category tag (saved tags are asked again)
TAG_PROMPT_VERSION = prompt_version(LINE_TAGS_PROMPT, TAG_BLOCK_VERSION)
METHOD_WORDS = re.compile(r"\b(oil|fat|butter|lard|dripping|tallow|marinat\w*|brine|poach\w*|boil\w*|simmer\w*|confit|deep[- ]?fr\w*|fr(?:y|ied|ying)|saut\w*|sear\w*|blister\w*|"
                          r"grill\w*|roast\w*|drizzle\w*|dress\w*|submerge\w*|cover\w*|brush\w*|drain\w*|discard\w*|lift\w*|reserv\w*|spoon\w*|pour\w*|sauce|serve\w*)\b", re.I)
METHOD_SENTENCES, METHOD_SENTENCE_CHARS = 8, 150      # 12.10.2: what happens to a marinade comes late in a method ("Brush dough with the olive oil mixture")
ROLES = ("eaten", "cooking_medium", "removed")
KINDS = ("plain_food", "prepared_product")
# 3K (12.20): the kind of food a line names, so a line no USDA record matches can still be placed; code validates against this list
CATEGORIES = ("wine_or_spirit", "beer", "herb", "spice", "salt", "water_or_stock", "cheese", "oil_or_fat", "meat", "poultry", "fish_or_seafood", "egg", "dairy", "vegetable", "fruit",
              "grain_or_bread", "legume_or_nut", "sauce_or_condiment", "sweetener", "other")
ZERO_FAT_CATEGORIES = ("wine_or_spirit", "beer", "salt", "water_or_stock")     # categories whose USDA records carry no fat: a code-chosen record may stand in when the line matched nothing
# a category the line's own words must support: a wine needs no word (that is the point: "Carricante"), these do
CATEGORY_WORDS = {"salt": re.compile(r"\bsalt\b|\bmaldon\b|\bfleur de sel\b", re.I), "beer": re.compile(r"\b(beer|ale|lager|stout|porter|cider|pilsner|ipa)\b", re.I),
                  "water_or_stock": re.compile(r"\b(water|stock|broth|bouillon|dashi|court[- ]bouillon|consomm[eé])\b", re.I)}
# 12.3.1: only fats, oils, liquids and salt may be a cooking medium
MEDIUM_WORDS = re.compile(r"\b(oils?|butter|ghee|lard|dripping|tallow|shortening|fats?|margarine|brine|stock|broth|bouillon|water|wine|vinegar|beer|ale|lager|cider|"
                          r"milk|buttermilk|cream|juice|marinade|liquid|liquor|salt|syrup|dashi|court[- ]bouillon|sake|mirin|vermouth|sherry|brandy|rum|whisky|whiskey|soy sauce|tamari)\b", re.I)
# things that are lifted out before serving
REMOVABLE_WORDS = re.compile(r"\b(lemons?|bay lea(?:f|ves)|sprigs?|stems?|stalks?|rinds?|bones?|carcass|shells?|husks?|skins?|cheesecloth|muslin|twine|string|skewers?|toothpicks?|"
                             r"parchment|foil|cinnamon sticks?|star anise|cardamom pods?|kaffir|makrut|lemongrass|kombu|galangal|peppercorns?|aromatics?|peel|zest|"
                             r"strips? of (?:lemon|orange|lime)|(?:lemon|orange|lime) (?:peel|rind|zest)|vanilla pods?|vanilla beans?|tea bags?|ginger slices?|sliced ginger)\b", re.I)
# USDA record heads that are products made of several ingredients, whatever the model called the line
PREPARED_RECORD_HEADS = ("sauce", "salad dressing", "soup", "gravy", "babyfood", "snacks", "fast foods", "restaurant", "pizza", "candies", "cereals ready-to-eat")


class LineTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str                                   # the validated role (what Python kept)
    kind: str                                   # the validated kind
    category: str = "other"                     # 3K: the validated food category (CATEGORIES)
    reason: str = ""                            # the model's words, provenance only
    raw_role: str = ""                          # what the model said (the pipeline re-validates against the line's USDA record once it is matched)
    raw_kind: str = ""
    note: str = ""                              # why the answer was overridden


class _TagRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int
    role: str
    kind: str
    category: str = "other"
    reason: str = Field(default="", max_length=300)


class _TagRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    lines: list[_TagRow]


class _TagReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipes: list[_TagRecipe]


class LineTags:
    """The validated tags of one dish: ``get(canonical_url, line_number)``; ``available`` is False after a failed call (12.3.4 fallback)."""

    def __init__(self, tags: dict[tuple[str, int], LineTag] | None, log: dict[str, Any], menu: dict[str, LineTag] | None = None) -> None:
        self._tags = tags or {}
        self.available = tags is not None
        self.log = log
        self.menu = menu or {}                  # 12.14.12: the tags of menu-only words, by word

    def get(self, canonical_url: str, n: int) -> LineTag | None:
        return self._tags.get((canonical_url, n))

    def merge(self, other: "LineTags") -> None:
        """3K: the tags of a top-up's recipes join the dish's tags; an unavailable first call stays unavailable (12.3.4 fallback)."""
        if other is None or not other.available:
            return
        self._tags.update(other._tags)
        self.menu.update(other.menu)
        if not self.available:
            self._tags, self.available = dict(other._tags), True

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self._tags.values():
            out[t.role] = out.get(t.role, 0) + 1
            out[t.kind] = out.get(t.kind, 0) + 1
        return out


def validate_tag(name: str, role: str, kind: str, reason: str, *, record_description: str | None = None, match_type: str | None = None, category: str = "other") -> LineTag:
    """Python's reading of one answer: the stricter side wins; every override is noted. 3K: an unknown category reads as other; salt, beer and water need a word of their own."""
    notes: list[str] = []
    model_role, model_kind = role, kind
    if role not in ROLES:
        notes.append(f"unknown role '{role[:20]}' read as eaten")
        role = "eaten"
    if kind not in KINDS:
        notes.append(f"unknown kind '{kind[:20]}' read as plain_food")
        kind = "plain_food"
    text = name or ""
    category = (category or "other").strip().lower()
    if category not in CATEGORIES:
        notes.append(f"unknown category '{category[:20]}' read as other")
        category = "other"
    if category in CATEGORY_WORDS and not CATEGORY_WORDS[category].search(text):
        notes.append(f"category '{category}' rejected: the line names no such word; read as other")
        category = "other"
    if role == "cooking_medium" and not MEDIUM_WORDS.search(text) and not (record_description and re.match(r"^(oil|fat|butter|lard|shortening|water|beverages|alcoholic beverage|soup, stock|vinegar|salt)\b", record_description, re.I)):
        notes.append("medium tag rejected: not a fat, oil, liquid or salt; treated as eaten (12.3.1)")
        role = "eaten"
    if role == "removed" and not REMOVABLE_WORDS.search(text) and not is_herb_or_spice(text, record_description, match_type):
        notes.append("removed tag rejected: not an aromatic, rind, bone or herb; treated as eaten")
        role = "eaten"
    head = (record_description or "").split(",", 1)[0].strip().lower()
    if kind == "plain_food" and head and any(head == h or head.startswith(h) for h in PREPARED_RECORD_HEADS):
        notes.append(f"kind read as prepared_product: the USDA record is '{record_description}'")
        kind = "prepared_product"
    return LineTag(role=role, kind=kind, category=category, reason=reason[:200], raw_role=model_role, raw_kind=model_kind, note="; ".join(notes))


def method_sentences(text: str) -> list[str]:
    """The first few method sentences that name a fat, a liquid or how the food is cooked: what tells a frying bath from a skillet's tablespoon."""
    picked = [x.strip()[:METHOD_SENTENCE_CHARS] for x in re.split(r"(?<=[.!?])\s+", text or "") if METHOD_WORDS.search(x)]
    return picked[:METHOD_SENTENCES]


def _recipe_block(i: int, r: SourceRecipe) -> str:
    lines = "\n".join(f"   {n}. {ing.line.strip()[:160]}" for n, ing in enumerate(r.ingredients, start=1))
    method = " ".join(method_sentences(r.instructions_text))
    return f'{i}. "{r.title}" ({r.host})\n' + (f"   method: {method}\n" if method else "") + lines


def menu_words_block(item: MenuItem, words: list[str]) -> SourceRecipe:
    """12.14.12: the menu's words no recipe lists join the same call as one more block, so they get a role and a kind like any line."""
    url = f"menu://{item_key(item)}"
    return SourceRecipe(url=url, canonical_url=url, host="menu", title=MENU_WORDS_TITLE, found_by=["open"], fetched_at="", extraction="none", ingredient_lines=list(words),
                        ingredients=[parse_line(w) for w in words], content_hash=prompt_version(*words))


def menu_word_tag(tags: LineTags, item: MenuItem, word: str, match: Any | None) -> LineTag | None:
    raw = tags.menu.get(word)
    if raw is None:
        return None
    return validate_tag(word, raw.raw_role or raw.role, raw.raw_kind or raw.kind, raw.reason, record_description=match.description if match else None, match_type=match.match_type if match else None, category=raw.category)


def tag_lines(item: MenuItem, recipes: list[SourceRecipe], llm: Any, parse_json_object, *, cache: JudgementCache | None = None, menu_words: list[str] | None = None) -> LineTags:
    """One call for all the dish's recipes that have no saved tags, before USDA matching; none when every recipe has them (12.9.5). The text alone is
    checked here; the pipeline re-validates each tag with the line's USDA record once it is matched (``validate_tag(..., record_description=...)``),
    which can only make a tag stricter."""
    if not recipes:
        return LineTags({}, {"called": False})
    block = menu_words_block(item, menu_words) if menu_words else None
    recipes = recipes + ([block] if block is not None else [])
    answers: dict[str, dict[int, dict[str, str]]] = {}
    to_ask: list[SourceRecipe] = []
    for r in recipes:
        saved = cache.get("tags", item, r, TAG_PROMPT_VERSION) if cache is not None else None
        if saved is None:
            to_ask.append(r)
        else:
            answers[r.canonical_url] = {int(n): row for n, row in saved.items()}
    log: dict[str, Any] = {"called": bool(to_ask), "recipes": len(recipes), "from_saved": len(recipes) - len(to_ask)}
    if to_ask:
        listing = "\n".join(_recipe_block(i + 1, r) for i, r in enumerate(to_ask))
        prompt = LINE_TAGS_PROMPT.format(name=item.name, section=item.section or "none", description=item.description or "none printed", recipes=listing)
        try:
            reply = llm.invoke([HumanMessage(content=prompt)])
        except Exception as exc:  # noqa: BLE001
            return LineTags(None, {**log, "error": type(exc).__name__})
        content = getattr(reply, "content", reply)
        data = parse_json_object(content if isinstance(content, str) else str(content))
        try:
            parsed = _TagReply.model_validate(data or {})
        except ValidationError as exc:
            return LineTags(None, {**log, "error": f"invalid_reply:{len(exc.errors())}_problems"})
        by_index = {rec.index: rec for rec in parsed.recipes}
        for i, r in enumerate(to_ask, start=1):
            rec = by_index.get(i)
            rows = {row.n: {"role": row.role, "kind": row.kind, "category": row.category, "reason": row.reason} for row in rec.lines} if rec is not None else {}
            answers[r.canonical_url] = rows
            if rows and cache is not None:
                cache.put("tags", item, r, TAG_PROMPT_VERSION, {str(n): row for n, row in rows.items()})
    tags: dict[tuple[str, int], LineTag] = {}
    overridden = missing = 0
    for r in recipes:
        rows = answers.get(r.canonical_url, {})
        for n, ing in enumerate(r.ingredients, start=1):
            row = rows.get(n)
            if row is None:
                missing += 1
                continue
            tag = validate_tag(ing.name, row["role"], row["kind"], row.get("reason", ""), category=row.get("category", "other"))
            if tag.note:
                overridden += 1
            tags[(r.canonical_url, n)] = tag
    log.update({"tagged": len(tags), "missing": missing, "overridden": overridden})
    if not tags:
        return LineTags(None, {**log, "error": "no_line_tagged"})
    menu = {w: tags[(block.canonical_url, n)] for n, w in enumerate(menu_words or [], start=1) if (block.canonical_url, n) in tags} if block is not None else {}
    return LineTags(tags, log, menu)
