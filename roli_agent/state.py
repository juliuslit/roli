"""The graph's state: every nutrition-related fact has its own slot, errors separate from results."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class RoliState(TypedDict, total=False):
    # Input
    text: str
    photo_path: str | None

    # Interpretation (LLM)
    intent: Literal["food_lookup", "menu", "recipe", "dish", "other", "unclear"]
    interpretation: dict[str, Any]       # food, usda_query, preparation, as the LLM returned them

    # USDA search (Python)
    search: dict[str, Any] | None        # SearchResult.model_dump(): query, candidates
    search_error: dict[str, Any] | None  # ErrorResult.model_dump()

    # Record selection (LLM proposes, Python verifies against the candidate list)
    selected_fdc_id: int | None
    selection_note: str                  # why the selection stands, or why it was rejected/unresolved

    # Nutrition (Python)
    nutrition: dict[str, Any] | None         # NutritionResult.model_dump(); status complete or partial
    nutrition_error: dict[str, Any] | None   # ErrorResult.model_dump()
    missing_nutrients: list[str]
    numbers_allowed: bool                    # True only when `nutrition` holds a validated USDA record

    # Recipe path (Phase 2A): a structured recipe supplied by the caller, never extracted by the LLM
    recipe: dict[str, Any] | None
    recipe_result: dict[str, Any] | None     # RecipeResult.model_dump(mode="json"); status complete or incomplete
    recipe_error: dict[str, Any] | None      # RecipeInvalid.model_dump(): the recipe itself was unusable

    # Dish path (Phase 2B-2): one menu item -> published recipes -> USDA -> calculator -> comparison
    menu_item: dict[str, Any] | None
    dish_estimate: dict[str, Any] | None     # DishEstimate.model_dump(mode="json")
    dish_error: str | None

    # Menu path
    menu: dict[str, Any] | None          # readable, problems, items (the menu reader's answer format)
    menu_error: str | None

    # Output and audit trail
    response: str
    trace: list[str]                     # one line per step, for inspection and tests
