"""Wiring: nodes, conditional edges, and the public entry point.

    START -> route_input -+-> interpret -+-> search_usda -> select_record -> fetch_nutrition -> compose -> END
                          |              +-> compose (other / unclear)
                          +-> read_menu -> compose
                          +-> calculate_recipe -> compose        (Phase 2A: structured recipe, no LLM)
                          +-> estimate_dish -> compose           (Phase 2B-2: menu item -> recipe scenarios)
    search_usda -> compose on error; select_record -> compose when unresolved.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from roli_nutrition import NutritionService, Settings

from . import harness, nodes
from .config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, SHORT_ANSWER_TOKENS
from .llm import make_chat_model
from .state import RoliState


def _after_route(state: RoliState) -> str:
    intent = state.get("intent")
    if intent == "dish":
        return "estimate_dish"
    if intent == "recipe":
        return "calculate_recipe"
    return "read_menu" if intent == "menu" else "interpret"


def _after_interpret(state: RoliState) -> str:
    return "search_usda" if state.get("intent") == "food_lookup" else "compose"


def _after_search(state: RoliState) -> str:
    return "compose" if state.get("search_error") else "select_record"


def _after_select(state: RoliState) -> str:
    return "fetch_nutrition" if state.get("selected_fdc_id") is not None else "compose"


def _default_source():
    from .recipes.search import TavilySource
    return TavilySource()


def _default_fetcher():
    from .config import ROOT
    from .recipes.fetch import FetchCache, PoliteFetcher
    return PoliteFetcher(cache=FetchCache(ROOT / ".cache" / "roli_recipes"))


def _default_match_cache():
    from .config import ROOT
    from .recipes.match import MatchCache
    return MatchCache(ROOT / ".cache" / "roli_recipes" / "usda_matches.json")


def _default_extraction_cache():
    from .config import ROOT
    from .recipes.extract import ExtractionCache
    return ExtractionCache(ROOT / ".cache" / "roli_recipes" / "extractions")


def build_graph(*, llm: Any | None = None, menu_llm: Any | None = None, service: NutritionService | None = None,
                load_prompt=None, recipe_source=None, fetcher=None, match_cache=None):
    """Compile the graph. Tests inject a scripted `llm` and a `service` on saved USDA replies;
    the real run builds Gemini through OpenRouter and the service from the environment."""
    injected = llm is not None
    llm = llm or make_chat_model(max_tokens=SHORT_ANSWER_TOKENS)
    # Menu reading gets the harness's long timeout and token cap; a test's scripted LLM serves both paths.
    menu_llm = menu_llm or (llm if injected else make_chat_model(timeout=harness.CALL_TIMEOUT_SECONDS))
    service = service or NutritionService(Settings.from_env())
    load_prompt = load_prompt or harness.load_prompt

    g = StateGraph(RoliState)
    g.add_node("route_input", nodes.route_input)
    g.add_node("interpret", nodes.make_interpret(llm))
    g.add_node("search_usda", nodes.make_search_usda(service))
    g.add_node("select_record", nodes.make_select_record(llm))
    g.add_node("fetch_nutrition", nodes.make_fetch_nutrition(service))
    g.add_node("read_menu", nodes.make_read_menu(menu_llm, load_prompt))
    g.add_node("calculate_recipe", nodes.make_calculate_recipe(service))
    # The dish path's batched prompts need a larger answer cap and a longer wait than a single-food question.
    dish_llm = llm if injected else make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS)
    g.add_node("estimate_dish", nodes.make_estimate_dish(
        service, dish_llm,
        source_factory=(lambda: recipe_source) if recipe_source is not None else _default_source,
        fetcher_factory=(lambda: fetcher) if fetcher is not None else _default_fetcher,
        match_cache_factory=(lambda: match_cache) if match_cache is not None else _default_match_cache,
        extraction_cache_factory=_default_extraction_cache if recipe_source is None else None))
    g.add_node("compose", nodes.compose)

    g.add_edge(START, "route_input")
    g.add_conditional_edges("route_input", _after_route, ["read_menu", "interpret", "calculate_recipe", "estimate_dish"])
    g.add_conditional_edges("interpret", _after_interpret, ["search_usda", "compose"])
    g.add_conditional_edges("search_usda", _after_search, ["select_record", "compose"])
    g.add_conditional_edges("select_record", _after_select, ["fetch_nutrition", "compose"])
    g.add_edge("fetch_nutrition", "compose")
    g.add_edge("read_menu", "compose")
    g.add_edge("calculate_recipe", "compose")
    g.add_edge("estimate_dish", "compose")
    g.add_edge("compose", END)
    return g.compile()


def run_roli(text: str = "", photo_path: str | None = None, *, recipe: dict | None = None, menu_item: dict | None = None, graph=None) -> dict:
    """One request in, one reply out. Returns {"response": str, "state": full final state}.

    `recipe` is a structured recipe (spec 2A, section 3) supplied by the caller; it takes the
    calculator path with no LLM call. `menu_item` ({name, description, section}) takes the Phase 2B-2
    dish path. Text and photo are ignored when either is given; a menu item wins over a recipe."""
    graph = graph or build_graph()
    state = graph.invoke({"text": text, "photo_path": photo_path, "recipe": recipe, "menu_item": menu_item, "trace": []})
    return {"response": state["response"], "state": state}
