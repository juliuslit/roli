"""Recipe scenarios for a menu dish (Phase 2B). Spec: roli_agent/SPEC_2B_recipe_scenarios.md.

2B-1 (ingestion): search -> fetch -> extract -> parse -> weight conversion, with provenance (`ingest_dish`).
2B-2 (scenarios): relevance gate and rubric, batched USDA matching on the 1E path, USDA-portion conversion,
menu-only lines, the unchanged Phase 2A calculator and comparison (`estimate_dish`). No nutrient number is
ever read from a page or produced by an LLM.
"""

from .ingest import IngestionResult, ingest_dish
from .models import DishEstimate, IngestionStats, MenuItem, ParsedIngredient, Scenario, SearchHit, SourceRecipe
from .pipeline import estimate_dish

__all__ = ["DishEstimate", "IngestionResult", "IngestionStats", "MenuItem", "ParsedIngredient", "Scenario", "SearchHit", "SourceRecipe",
           "estimate_dish", "ingest_dish"]
