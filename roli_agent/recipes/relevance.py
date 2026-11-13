"""Relevance of a published recipe to the menu dish (spec 2B section 3.3, D10, D16; requirement 1 of 2B-2).

Three layers, cheapest first:
1. `gate` (Python, free): listicles and non-recipe collections out (D16); recipes that do not even name the dish
   out (pasta with bottarga for a crudo); hard exclusion when the title says the dish is cooked and the menu dish
   is a raw preparation. Everything rejected here never reaches USDA matching or the LLM.
2. `menu_coverage` (Python, free): which printed menu ingredients the recipe contains (Measure A).
3. `grade_batch` (one LLM call per dish): dish type, preparation and course for every recipe that passed the gate
   (Measure B). Python combines the categorical answers; the LLM's sentences stay in provenance only.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..prompts import RELEVANCE_PROMPT
from .judgements import JudgementCache, prompt_version
from .models import MenuItem, Relevance, SourceRecipe

GRADE_PROMPT_VERSION = prompt_version(RELEVANCE_PROMPT)
RAW_DISH_TYPES = {"crudo", "carpaccio", "tartare", "ceviche", "sashimi", "poke", "tataki"}
# Leaf-salad dish heads: the menu names raw leaves unless its own words say otherwise ("grilled little gems").
LEAF_SALAD_HEADS = {"lettuce", "lettuces", "gem", "gems", "salad", "greens", "leaves"}
COOKED_TITLE_WORDS = re.compile(r"\b(seared|pan-seared|grilled|roasted|roast|baked|fried|deep-fried|poached|braised|smoked|steak|stew|soup|chowder|"
                                r"casserole|confit|sous[- ]vide|charred)\b", re.I)
# Method sentences that cook the main ingredient of a raw dish (2C.1, requirement C): base-form cooking verbs only, so "top the
# lettuce with toasted seeds" (a cooked garnish) is not read as cooking the lettuce.
METHOD_COOK_VERBS = re.compile(r"\b(grill|char|roast|bake|sear|fry|broil|saut[eé]|cook|blister|smoke|poach|braise|steam|boil)\b", re.I)
MAIN_WORDS_BY_FAMILY = {
    "leaf_salad": re.compile(r"\b(lettuces?|gems?|romaine|heads?|leaves)\b", re.I),
    "raw_fish": re.compile(r"\b(tuna|fish|salmon|scallops?|hamachi|yellowtail|fluke|snapper|bass|halibut|crudo|carpaccio|tartare|ceviche)\b", re.I),
}
LISTICLE_TITLE = re.compile(r"^\s*\d{1,3}\+?\s+.*\b(recipes|ideas|ways|dishes|things)\b", re.I)
GENERIC_WORDS = {"the", "with", "and", "of", "little", "baby", "fresh", "house", "our", "style", "grilled", "roasted", "local", "farm", "heirloom",
                 "wild", "king", "bluefin", "organic", "seasonal", "market", "sea", "day", "boat"}
# Dish head word -> other words that name the same dish family in recipe titles.
DISH_SYNONYMS = {
    "crudo": {"crudo", "carpaccio", "sashimi", "tartare", "raw"},
    "lettuce": {"lettuce", "salad", "gem", "gems", "wedge"},
    "lettuces": {"lettuce", "salad", "gem", "gems", "wedge"},
    "tomato": {"tomato", "tomatoes", "caprese", "panzanella"},
    "tomatoes": {"tomato", "tomatoes", "caprese", "panzanella"},
    "salmon": {"salmon"},
    "pizza": {"pizza", "pizzas", "margherita"},
    "margherita": {"margherita", "pizza"},
}
# Printed menu words -> tokens that count as the same ingredient in a recipe line (Measure A).
MENU_SYNONYMS = {
    "muscat grape": ["grape"], "grape": ["grape"], "chive": ["chive"], "chives": ["chive"],
    "fior di latte": ["mozzarella", "fior di latte", "fiordilatte"], "mozzarella": ["mozzarella", "fior di latte"],
    "pecorino sardo": ["pecorino", "romano", "sardo"], "pecorino": ["pecorino", "romano"],
    "toasted sesame": ["sesame"], "sesame": ["sesame"], "tahini vinaigrette": ["tahini"], "tahini": ["tahini"],
    "genovese basil": ["basil"], "basil": ["basil"], "sourdough": ["sourdough", "bread", "crouton", "breadcrumb"],
    "shishito": ["shishito"], "squash": ["squash", "zucchini", "courgette"], "corn": ["corn"], "tomato": ["tomato"],
    "pluot": ["pluot"], "shiso": ["shiso", "perilla"], "bottarga": ["bottarga"], "bluefin": ["bluefin", "tuna"],
}
STOP = {"a", "an", "the", "of", "and", "with", "fresh", "to", "taste", "for", "serving", "garnish", "or", "into", "cut"}


def singular(word: str) -> str:
    w = word.lower()
    if len(w) <= 3:
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("oes"):
        return w[:-2]
    if w.endswith(("ses", "xes", "shes", "ches")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokens(text: str) -> set[str]:
    return {singular(t) for t in re.findall(r"[a-zà-ü]+", text.lower()) if t not in STOP}


def dish_words(item: MenuItem) -> tuple[set[str], str]:
    """(keywords that must appear somewhere in the recipe, the dish's head word)."""
    name_tokens = [t for t in re.findall(r"[a-zà-ü]+", item.name.lower())]
    head = name_tokens[-1] if name_tokens else ""
    words = {singular(t) for t in name_tokens if t not in GENERIC_WORDS and len(t) >= 3}
    section = item.section.strip().lower()
    for w in DISH_SYNONYMS.get(head, set()):
        words.add(singular(w))
    if section in DISH_SYNONYMS:
        words |= {singular(w) for w in DISH_SYNONYMS[section]}
    return words, head


def raw_family(item: MenuItem) -> str | None:
    """Which family of raw dishes the menu item belongs to, if any: a crudo-type dish, or a leaf salad whose menu words name no
    cooking of the leaves. None for everything else (a salmon main may be seared, roasted or baked)."""
    _, head = dish_words(item)
    if head in RAW_DISH_TYPES:
        return "raw_fish"
    if head in LEAF_SALAD_HEADS and not COOKED_TITLE_WORDS.search(f"{item.name} {item.description}"):
        return "leaf_salad"
    return None


def cooked_main_ingredient(item: MenuItem, recipe: SourceRecipe) -> str | None:
    """The first method sentence that cooks the raw dish's main ingredient ("place lettuce on the grill ... until charred"), or None.
    A title can sound right ("Grilled Little Gem salad" is still a salad); the method text decides (2C.1)."""
    family = raw_family(item)
    if family is None or not recipe.instructions_text:
        return None
    main = MAIN_WORDS_BY_FAMILY[family]
    for sentence in re.split(r"(?<=[.!?])\s+", recipe.instructions_text):
        verb = METHOD_COOK_VERBS.search(sentence)
        if verb and main.search(sentence):
            return f"{verb.group(1).lower()}: {sentence.strip()[:120]}"
    return None


def gate(item: MenuItem, recipe: SourceRecipe) -> tuple[bool, str | None]:
    """Cheap deterministic rejection before any USDA or LLM work. Returns (passed, reason)."""
    if "no_quantities_listicle_suspect" in recipe.flags:
        return False, "listicle_or_collection:no_quantities"
    if LISTICLE_TITLE.match(recipe.title or ""):
        return False, "listicle_or_collection:title"
    if recipe.n_lines < 2:
        return False, "too_few_ingredient_lines"
    words, head = dish_words(item)
    if head in RAW_DISH_TYPES:
        m = COOKED_TITLE_WORDS.search(recipe.title or "")
        if m and singular(head) not in tokens(recipe.title):
            return False, f"hard_exclusion:cooked_title_for_raw_dish:{m.group(1).lower()}"
    cooked = cooked_main_ingredient(item, recipe)
    if cooked:
        return False, f"hard_exclusion:main_ingredient_cooked_in_method:{cooked.split(':')[0]}"
    seen = tokens(recipe.title)
    for i in recipe.ingredients:
        seen |= tokens(i.name)
    if words and not (words & seen):
        return False, f"dish_word_absent:{'/'.join(sorted(words))}"
    return True, None


# A menu description segment that is a service note, not an ingredient ("(served with the above accompaniments)", "choice of two sides",
# "approximately 75 minutes", "$1 from each chicken sold is donated"). Zuni Café, 2026-11-05: the reader put such a note in the description once
# and it became an unfillable menu-only line that left the ribeye without an upper bound.
MENU_NOTE = re.compile(r"^\s*\(.*\)\s*$|\b(served with|accompaniments?|the above|choice of|supplement|per person|for two|for the table|minutes?|approximately|"
                       r"market price|m\.p\.|sold|donated|donation|allergens?|contains|gluten[- ]free|vegan|vegetarian|please|ask your server|subject to)\b|\$\s?\d", re.I)


def menu_coverage(item: MenuItem, recipe: SourceRecipe) -> tuple[Decimal | None, list[str], list[str]]:
    """Measure A: (coverage fraction, matched menu words, missing menu words). Deterministic token overlap plus synonyms."""
    listed = [w.strip() for w in item.description.split(",") if w.strip() and not MENU_NOTE.search(w)]   # a service note is not an ingredient
    if not listed:
        return None, [], []
    recipe_tokens: set[str] = set()
    for ing in recipe.ingredients:
        recipe_tokens |= tokens(ing.name) | tokens(" ".join(ing.preparation_words))
    matched, missing = [], []
    for word in listed:
        key = word.lower()
        wanted = MENU_SYNONYMS.get(key) or MENU_SYNONYMS.get(singular(key)) or [key.split()[-1]]
        if any(singular(w) in recipe_tokens or any(singular(w) in t for t in recipe_tokens if len(w) > 4) for w in wanted):
            matched.append(word)
        else:
            missing.append(word)
    return Decimal(len(matched)) / Decimal(len(listed)), matched, missing


# -- the LLM rubric (one call per dish) ----------------------------------------------


class RubricRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    dish_type: str
    preparation: str
    course_portion: str
    reason: str = Field(default="", max_length=400)


class RubricReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipes: list[RubricRow]


def combine(dish_type: str, preparation: str, course: str) -> tuple[str, str | None]:
    """Python decides the grade (D10): a different dish or a different preparation is a hard exclusion."""
    if dish_type == "different":
        return "low", "hard_exclusion:dish_type_different"
    if preparation == "different":
        return "low", "hard_exclusion:preparation_different"
    if dish_type in ("same", "variant") and preparation in ("same", "similar"):
        return ("high" if course == "same" else "medium"), None      # spec 3.3: high when all three are same/similar
    return "low", None


def _recipe_block(i: int, r: SourceRecipe, item: MenuItem | None = None) -> str:
    names = ", ".join(ing.name for ing in r.ingredients[:20])
    verbs = ", ".join(r.cooking_verbs) or "none detected"
    method = ""
    if item is not None:
        cooked = cooked_main_ingredient(item, r)
        if cooked:
            method = f'; method text cooks the main ingredient: "{cooked.split(": ", 1)[1]}"'
    return f'{i}. "{r.title}" ({r.host}); yield: {r.yield_text or "not stated"}; cooking methods: {verbs}{method}; ingredients: {names}'


def _apply_grade(rel: Relevance, dish_type: str, preparation: str, course: str, reason: str) -> bool:
    if dish_type not in ("same", "variant", "different") or preparation not in ("same", "similar", "different") or course not in ("same", "different"):
        return False
    grade, hard = combine(dish_type, preparation, course)
    rel.dish_type, rel.preparation, rel.course_portion = dish_type, preparation, course
    rel.rubric_reason, rel.grade, rel.hard_exclusion = reason[:300], grade, hard
    return True


def grade_batch(item: MenuItem, recipes: list[SourceRecipe], relevances: list[Relevance], llm: Any, parse_json_object, *, cache: JudgementCache | None = None) -> dict[str, Any]:
    """Fill dish_type / preparation / course_portion / grade on each Relevance (same order as `recipes`). A saved grade is reused (12.9.5); the rest go
    to the model in one call. Recipes missing from the reply, or a reply that does not validate, stay `ungraded`. Returns a small log dict."""
    if not recipes:
        return {"called": False}
    to_ask: list[tuple[SourceRecipe, Relevance]] = []
    from_saved = 0
    for r, rel in zip(recipes, relevances):
        saved = cache.get("grades", item, r, GRADE_PROMPT_VERSION) if cache is not None else None
        if saved is not None and _apply_grade(rel, saved.get("dish_type", ""), saved.get("preparation", ""), saved.get("course_portion", ""), saved.get("reason", "")):
            from_saved += 1
        else:
            to_ask.append((r, rel))
    if not to_ask:
        return {"called": False, "graded": from_saved, "of": len(recipes), "from_saved": from_saved}
    listing = "\n".join(_recipe_block(i + 1, r, item) for i, (r, _) in enumerate(to_ask))
    prompt = RELEVANCE_PROMPT.format(name=item.name, section=item.section or "none", description=item.description or "none printed", recipes=listing)
    try:
        reply = llm.invoke([HumanMessage(content=prompt)])
    except Exception as exc:
        return {"called": True, "error": type(exc).__name__}
    content = getattr(reply, "content", reply)
    data = parse_json_object(content if isinstance(content, str) else str(content))
    try:
        parsed = RubricReply.model_validate(data or {})
    except ValidationError as exc:
        return {"called": True, "error": f"invalid_reply:{len(exc.errors())}_problems"}
    rows = {row.index: row for row in parsed.recipes}
    graded = from_saved
    for i, (r, rel) in enumerate(to_ask, start=1):
        row = rows.get(i)
        if row is None or not _apply_grade(rel, row.dish_type, row.preparation, row.course_portion, row.reason):
            continue
        graded += 1
        if cache is not None:
            cache.put("grades", item, r, GRADE_PROMPT_VERSION, {"dish_type": row.dish_type, "preparation": row.preparation, "course_portion": row.course_portion, "reason": row.reason})
    return {"called": True, "graded": graded, "of": len(recipes), "from_saved": from_saved}
