"""Graph nodes. Each returns only the state keys it changes.

LLM nodes: `interpret`, `select_record`, `read_menu`. They produce text that Python parses
and checks. Python nodes: `route_input`, `search_usda`, `fetch_nutrition`, `compose`.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from langchain_core.messages import HumanMessage

from roli_nutrition import ErrorResult, NutritionResult, NutritionService, SearchResult
from roli_nutrition.recipe import RecipeCalculator, RecipeResult

from . import responses
from .config import MENU_PROMPT_VERSION, SEARCH_LIMIT
from .llm import image_data_url, parse_json_object
from .prompts import INTERPRET_PROMPT, SELECT_PROMPT
from .selection import accept_proposed_id
from .state import RoliState

logger = logging.getLogger("roli_agent")

LlmCall = Callable[[list], Any]  # llm.invoke(messages) -> message with .content


def _text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):  # some models return content blocks
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def _trace(state: RoliState, line: str) -> list[str]:
    return list(state.get("trace", [])) + [line]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------


def route_input(state: RoliState) -> dict:
    """A photo means the menu path; text alone goes to interpretation.

    Also sets every nutrition slot to its empty value, so later nodes and the reply builder
    always find the keys: numbers are forbidden until `fetch_nutrition` explicitly allows them."""
    defaults = {"interpretation": {}, "search": None, "search_error": None, "selected_fdc_id": None,
                "selection_note": "", "nutrition": None, "nutrition_error": None, "missing_nutrients": [],
                "numbers_allowed": False, "menu": None, "menu_error": None, "recipe_result": None, "recipe_error": None,
                "dish_estimate": None, "dish_error": None}
    if state.get("menu_item") is not None:
        return {**defaults, "intent": "dish", "trace": _trace(state, "route: menu item supplied -> dish path (recipe scenarios)")}
    if state.get("recipe") is not None:
        return {**defaults, "intent": "recipe", "trace": _trace(state, "route: structured recipe supplied -> calculator path")}
    if state.get("photo_path"):
        return {**defaults, "intent": "menu", "trace": _trace(state, "route: photo attached -> menu path")}
    return {**defaults, "trace": _trace(state, "route: text only -> interpret")}


def make_interpret(llm: Any):
    def interpret(state: RoliState) -> dict:
        reply = _text(llm.invoke([HumanMessage(content=INTERPRET_PROMPT + state.get("text", ""))]))
        data = parse_json_object(reply)
        if not data or data.get("intent") not in ("food_lookup", "other"):
            return {"intent": "unclear", "interpretation": {}, "trace": _trace(state, "interpret: unparsable LLM reply -> unclear")}
        if data["intent"] == "other":
            return {"intent": "other", "interpretation": data, "trace": _trace(state, "interpret: intent other")}
        query = str(data.get("usda_query") or "").strip()
        if not query:
            return {"intent": "unclear", "interpretation": data, "trace": _trace(state, "interpret: no usda_query -> unclear")}
        return {
            "intent": "food_lookup",
            "interpretation": {"food": str(data.get("food") or query), "usda_query": query,
                               "preparation": str(data.get("preparation") or "unknown")},
            "trace": _trace(state, f"interpret: food={data.get('food')!r} query={query!r}"),
        }
    return interpret


def make_search_usda(service: NutritionService):
    def search_usda(state: RoliState) -> dict:
        query = state["interpretation"]["usda_query"]
        result = service.search_foods(query, SEARCH_LIMIT)
        if isinstance(result, ErrorResult):
            return {"search": None, "search_error": result.model_dump(), "selected_fdc_id": None,
                    "trace": _trace(state, f"search: error {result.error_code}")}
        assert isinstance(result, SearchResult)
        return {"search": result.model_dump(), "search_error": None,
                "trace": _trace(state, f"search: {len(result.candidates)} candidates for {query!r}")}
    return search_usda


def make_select_record(llm: Any):
    def select_record(state: RoliState) -> dict:
        candidates = (state.get("search") or {}).get("candidates") or []
        if not candidates:
            return {"selected_fdc_id": None, "selection_note": "USDA returned no candidates",
                    "trace": _trace(state, "select: no candidates")}
        interp = state["interpretation"]
        listing = "\n".join(f"- fdc_id {c['fdc_id']}: {c['description']} [{c['data_type']}]" for c in candidates)
        prompt = SELECT_PROMPT.format(food=interp["food"], preparation=interp.get("preparation", "unknown"), candidates=listing)
        reply = _text(llm.invoke([HumanMessage(content=prompt)]))
        data = parse_json_object(reply) or {}
        proposed = data.get("fdc_id")
        allowed = {c["fdc_id"] for c in candidates}
        reason = str(data.get("reason") or "")[:300]
        if proposed is None:
            # The LLM's own words stay in the trace for debugging; the user sees fixed wording (Julius, 2026-11-02).
            return {"selected_fdc_id": None, "selection_note": "no candidate names the same food and preparation",
                    "trace": _trace(state, f"select: LLM found no match ({reason})")}
        if accept_proposed_id(proposed, allowed) is None:
            # The structural guard: an ID that USDA did not return for this search is never used.
            return {"selected_fdc_id": None, "selection_note": "the proposed record was not among USDA's results",
                    "trace": _trace(state, f"select: REJECTED proposed id {proposed!r} not in candidate list")}
        return {"selected_fdc_id": proposed, "selection_note": "selected from USDA's results",
                "trace": _trace(state, f"select: {proposed} ({reason})")}
    return select_record


def make_fetch_nutrition(service: NutritionService):
    def fetch_nutrition(state: RoliState) -> dict:
        fdc_id = state["selected_fdc_id"]
        result = service.get_nutrition(fdc_id)
        if isinstance(result, NutritionResult):
            return {"nutrition": result.model_dump(), "nutrition_error": None,
                    "missing_nutrients": list(result.missing_nutrients), "numbers_allowed": True,
                    "trace": _trace(state, f"fetch: {result.status} for {fdc_id}")}
        return {"nutrition": None, "nutrition_error": result.model_dump(), "missing_nutrients": [],
                "numbers_allowed": False, "trace": _trace(state, f"fetch: error {result.error_code} for {fdc_id}")}
    return fetch_nutrition


def make_read_menu(llm: Any, load_prompt: Callable[[str], str]):
    def read_menu(state: RoliState) -> dict:
        try:
            data_url, _size = image_data_url(state["photo_path"])
        except Exception as exc:  # unreadable file, wrong path
            return {"menu": None, "menu_error": f"photo could not be opened: {type(exc).__name__}",
                    "trace": _trace(state, "menu: photo unreadable")}
        prompt = load_prompt(MENU_PROMPT_VERSION)
        message = HumanMessage(content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}])
        reply = _text(llm.invoke([message]))
        menu = parse_json_object(reply)
        if not menu or not isinstance(menu.get("items"), list):
            return {"menu": None, "menu_error": "the menu reader returned no usable item list",
                    "trace": _trace(state, "menu: unparsable reader output")}
        return {"menu": menu, "menu_error": None,
                "trace": _trace(state, f"menu: {len(menu['items'])} items, readable={menu.get('readable')}")}
    return read_menu


def make_calculate_recipe(service: NutritionService):
    calculator = RecipeCalculator(service)

    def calculate_recipe(state: RoliState) -> dict:
        """Pure Python: validate the supplied recipe, fetch USDA references, do the arithmetic.
        Numbers become allowed only when a RecipeResult exists; an invalid recipe allows none."""
        result = calculator.calculate(state["recipe"])
        if isinstance(result, RecipeResult):
            return {"recipe_result": result.model_dump(mode="json"), "recipe_error": None, "numbers_allowed": True,
                    "trace": _trace(state, f"recipe: {result.status}; sat complete={result.totals['saturated_fat_g'].complete}, "
                                           f"chol complete={result.totals['cholesterol_mg'].complete}")}
        return {"recipe_result": None, "recipe_error": result.model_dump(), "numbers_allowed": False,
                "trace": _trace(state, f"recipe: invalid ({len(result.problems)} problems)")}
    return calculate_recipe


def compose(state: RoliState) -> dict:
    reply = responses.compose(state)
    logger.info(json.dumps({"event": "reply", "intent": state.get("intent"), "numbers_allowed": bool(state.get("numbers_allowed")),
                            "fdc_id": state.get("selected_fdc_id"), "error": (state.get("search_error") or state.get("nutrition_error") or {}).get("error_code")}))
    return {"response": reply, "trace": _trace(state, "compose: done")}


def make_estimate_dish(service: NutritionService, llm: Any, *, source_factory: Callable[[], Any], fetcher_factory: Callable[[], Any],
                       match_cache_factory: Callable[[], Any] | None = None, max_scenarios: int | None = None,
                       extraction_cache_factory: Callable[[], Any] | None = None):
    """Phase 2B-2: the whole recipe-scenario pipeline as one node. Everything numeric comes from the pipeline's
    Phase 2A objects; the LLM only grades relevance, writes USDA queries and picks from USDA's candidate lists."""
    from .recipes.models import MenuItem
    from .recipes.pipeline import MAX_SCENARIOS, estimate_dish

    def estimate(state: RoliState) -> dict:
        try:
            item = MenuItem.model_validate(state["menu_item"])
        except Exception as exc:
            return {"dish_estimate": None, "dish_error": f"menu item invalid: {type(exc).__name__}", "numbers_allowed": False,
                    "trace": _trace(state, "dish: invalid menu item")}
        try:
            source, fetcher = source_factory(), fetcher_factory()
            cache = match_cache_factory() if match_cache_factory else None
            extraction_cache = extraction_cache_factory() if extraction_cache_factory else None
        except Exception as exc:                                   # e.g. no TAVILY_API_KEY
            return {"dish_estimate": None, "dish_error": f"recipe search unavailable: {type(exc).__name__}", "numbers_allowed": False,
                    "trace": _trace(state, f"dish: setup failed {type(exc).__name__}")}
        estimate = estimate_dish(item, source=source, fetcher=fetcher, service=service, llm=llm, match_cache=cache,
                                 max_scenarios=max_scenarios or MAX_SCENARIOS, extraction_cache=extraction_cache)
        s = estimate.summary
        return {"dish_estimate": estimate.model_dump(mode="json"), "dish_error": None,
                "numbers_allowed": s.n_calculated > 0,            # only Phase 2A results may be printed
                "trace": _trace(state, f"dish: {s.n_distinct} recipes, {s.n_relevant} relevant, {s.n_calculated} calculated, "
                                       f"{s.n_complete} complete, {s.n_eligible} eligible; {estimate.cost.llm_calls} LLM calls")}
    return estimate
