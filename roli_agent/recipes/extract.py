"""Turn a recipe page into verbatim ingredient lines, yield text and instructions (D2).

Order: recipe-scrapers (supported site or wild mode) -> schema.org Recipe JSON-LD parsed by hand
-> LLM fallback over the page's visible text, accepted only line by line where each returned
ingredient line is a verbatim substring of that text. The `nutrition` block of a page is never read.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .models import ExtractionMethod

NUTRITION_KEYS = {"nutrition", "calories", "fatContent", "saturatedFatContent", "cholesterolContent", "sodiumContent",
                  "carbohydrateContent", "proteinContent", "fiberContent", "sugarContent"}
LLM_TEXT_CAP = 12_000

EXTRACT_PROMPT = """Below is the visible text of a web page that may contain a recipe. Return ONE JSON object and nothing else:
{"ingredient_lines": ["...", "..."], "yield_text": "...", "instructions_text": "..."}
Rules: copy each ingredient line EXACTLY as it appears in the text (same words, same numbers, same order); copy the yield
or servings statement exactly if present, else ""; copy the method/instructions text as it appears, else "".
Never add, estimate or convert anything. If there is no recipe, return {"ingredient_lines": [], "yield_text": "", "instructions_text": ""}.

PAGE TEXT:
"""


class ExtractionCache:
    """Validated extraction results per page (ingredient lines, yield, title, method text) keyed by URL + page content,
    so the LLM fallback never re-reads an unchanged page. Lives beside the page cache (same material, same 30-day life,
    gitignored); a changed page gets a new key and is extracted again."""

    def __init__(self, directory, ttl: float = 30 * 24 * 3600, clock=None) -> None:
        import time as _time
        from pathlib import Path
        self.directory = Path(directory)
        self.ttl = ttl
        self.clock = clock or _time.time
        self.directory.mkdir(parents=True, exist_ok=True)
        self.hits = 0

    def _path(self, url: str, html: str):
        import hashlib
        return self.directory / (hashlib.sha256((url + "\n" + html).encode("utf-8", "replace")).hexdigest() + ".json")

    def get(self, url: str, html: str) -> "Extracted | None":
        path = self._path(url, html)
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        if self.clock() - entry["saved_at"] > self.ttl:
            return None
        self.hits += 1
        return Extracted(**entry["extracted"])

    def put(self, url: str, html: str, extracted: "Extracted") -> None:
        from dataclasses import asdict
        self._path(url, html).write_text(json.dumps({"saved_at": self.clock(), "url": url, "extracted": asdict(extracted)}), encoding="utf-8")


@dataclass
class Extracted:
    method: ExtractionMethod
    title: str = ""
    ingredient_lines: list[str] = field(default_factory=list)
    yield_text: str = ""
    instructions_text: str = ""
    flags: list[str] = field(default_factory=list)
    yield_source: str = "none"          # "structured" | "page_text" (D15) | "none"


# D15: an explicit serving count in the page's own words, used only when structured data has no yield.
# Only serving words count: "Serves 4", "4 servings", "Yield: 4 servings", "makes 6 servings". Never slices, pizzas or items.
YIELD_IN_TEXT = re.compile(r"\b(?:serves|serving size:?|yield:?|yields:?|makes)\s*(?:about\s+)?(\d{1,2}(?:\s*(?:-|–|to)\s*\d{1,2})?)(?:\s+(?:servings?|people|persons?|portions?))?\b"
                           r"|\b(\d{1,2}(?:\s*(?:-|–|to)\s*\d{1,2})?)\s+(?:servings|portions)\b", re.I)


def recover_yield_from_text(html: str) -> str:
    """The first explicit serving statement in the visible text, verbatim, or ''. A regex match is a substring by
    construction, so the verbatim rule holds. 'Makes 2 pizzas' does not match (no serving word)."""
    text = visible_text(html)
    for m in YIELD_IN_TEXT.finditer(text):
        snippet = m.group(0).strip()
        if m.group(1) is not None and not re.search(r"servings?|people|persons?|portions?", snippet, re.I) and snippet.lower().startswith("makes"):
            continue                                   # "makes 2" without a serving word: not evidence of servings
        return snippet
    return ""


# -- deterministic paths ---------------------------------------------------------


def _clean(text: Any) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(str(text))).strip()


def _instructions_from_ld(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _clean(value)
    parts: list[str] = []
    stack = [value]
    while stack:
        item = stack.pop(0)
        if isinstance(item, str):
            parts.append(_clean(item))
        elif isinstance(item, dict):
            if item.get("text"):
                parts.append(_clean(item["text"]))
            if item.get("itemListElement"):
                stack.extend(item["itemListElement"])
        elif isinstance(item, list):
            stack.extend(item)
    return " ".join(p for p in parts if p)


def find_json_ld_recipe(html: str) -> dict | None:
    """The first schema.org Recipe object in any ld+json block, with nutrition fields removed."""
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(match.group(1).strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                types = node.get("@type")
                types = types if isinstance(types, list) else [types]
                if "Recipe" in types:
                    return {k: v for k, v in node.items() if k not in NUTRITION_KEYS}
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return None


def extract_from_json_ld(html: str) -> Extracted | None:
    recipe = find_json_ld_recipe(html)
    if not recipe:
        return None
    lines = recipe.get("recipeIngredient") or []
    if not isinstance(lines, list):
        lines = []
    yield_value = recipe.get("recipeYield")
    if isinstance(yield_value, list):
        yield_value = " / ".join(_clean(v) for v in yield_value)
    return Extracted(method="json_ld", title=_clean(recipe.get("name", "")), ingredient_lines=[_clean(l) for l in lines if _clean(l)],
                     yield_text=_clean(yield_value or ""), instructions_text=_instructions_from_ld(recipe.get("recipeInstructions")))


def extract_with_scrapers(html: str, url: str) -> Extracted | None:
    try:
        from recipe_scrapers import scrape_html
    except ImportError:  # pragma: no cover
        return None
    try:
        scraper = scrape_html(html, org_url=url, supported_only=False)
        lines = [_clean(l) for l in (scraper.ingredients() or []) if _clean(l)]
    except Exception:
        return None
    if not lines:
        return None

    def safe(getter):
        try:
            return _clean(getter() or "")
        except Exception:
            return ""
    # D15: the yield text must be the page's own words. recipe_scrapers' yields() rewrites them ("One 12-inch pizza" -> "12 servings", a
    # dimension read as a serving count; found 2026-11-03 in a Phase 2D test), so the JSON-LD recipeYield is preferred when the page has one.
    ld = find_json_ld_recipe(html)
    raw_yield = (ld or {}).get("recipeYield")
    if isinstance(raw_yield, list):
        raw_yield = " / ".join(_clean(v) for v in raw_yield)
    yield_text = _clean(raw_yield) if isinstance(raw_yield, str) and _clean(raw_yield) else safe(scraper.yields)
    return Extracted(method="recipe_scrapers", title=safe(scraper.title), ingredient_lines=lines,
                     yield_text=yield_text, instructions_text=safe(scraper.instructions))


# -- LLM fallback, verified ----------------------------------------------------


def visible_text(html: str) -> str:
    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def extract_with_llm(html: str, llm: Any, parse_json_object) -> Extracted:
    """Only lines that appear verbatim in the page text are kept; the rest are dropped and flagged."""
    text = visible_text(html)[:LLM_TEXT_CAP]
    from langchain_core.messages import HumanMessage
    reply = llm.invoke([HumanMessage(content=EXTRACT_PROMPT + text)])
    content = getattr(reply, "content", reply)
    data = parse_json_object(content if isinstance(content, str) else str(content)) or {}
    proposed = [str(l).strip() for l in (data.get("ingredient_lines") or []) if str(l).strip()]
    folded = re.sub(r"\s+", " ", text).lower()
    kept = [l for l in proposed if re.sub(r"\s+", " ", l).lower() in folded]
    flags = []
    if len(kept) < len(proposed):
        flags.append(f"extraction_unverifiable:{len(proposed) - len(kept)}_lines_dropped")
    yield_text = str(data.get("yield_text") or "").strip()
    if yield_text and yield_text.lower() not in folded:
        yield_text, flags = "", flags + ["yield_unverifiable_dropped"]
    return Extracted(method="llm_text" if kept else "none", ingredient_lines=kept, yield_text=yield_text,
                     instructions_text=str(data.get("instructions_text") or "")[:4000], flags=flags)


def extract_recipe(html: str, url: str, *, llm: Any | None = None, parse_json_object=None, cache: ExtractionCache | None = None) -> Extracted:
    if cache is not None:
        cached = cache.get(url, html)
        if cached is not None:
            cached.flags = [f for f in cached.flags if f != "extraction_from_cache"] + ["extraction_from_cache"]
            return cached
    result = _extract_uncached(html, url, llm=llm, parse_json_object=parse_json_object)
    if cache is not None:
        cache.put(url, html, result)
    return result


def _extract_uncached(html: str, url: str, *, llm: Any | None = None, parse_json_object=None) -> Extracted:
    result = extract_with_scrapers(html, url)
    if result is None:
        result = extract_from_json_ld(html)
        if result is not None and not result.ingredient_lines:
            result = None
    if result is None and llm is not None and parse_json_object is not None:
        result = extract_with_llm(html, llm, parse_json_object)
    result = result or Extracted(method="none")
    if result.ingredient_lines:
        if result.yield_text:
            result.yield_source = "structured" if result.method != "llm_text" else "page_text"
        else:
            recovered = recover_yield_from_text(html)
            if recovered:
                result.yield_text, result.yield_source = recovered, "page_text"
                result.flags.append("yield_from_page_text")
    return result
