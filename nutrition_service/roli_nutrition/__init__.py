"""roli_nutrition: saturated fat and cholesterol for one USDA food, checked by code.

Typical use (LangGraph, Phase 2):

    from roli_nutrition import get_nutrition, search_foods
    r = get_nutrition(171999)
    state_update = r.model_dump()

The core depends on httpx and Pydantic only. It never imports MCP, LangGraph,
LangChain, python-dotenv or uvicorn.
"""

from .config import ConfigError, Settings
from .portions import Portion, PortionsResult
from .schemas import Candidate, ErrorResult, NutritionResult, SearchResult
from .service import NutritionService, default_service, get_nutrition, search_foods
from .store import AnswerStore

__all__ = [
    "AnswerStore",
    "Candidate",
    "ConfigError",
    "ErrorResult",
    "NutritionResult",
    "NutritionService",
    "Portion",
    "PortionsResult",
    "SearchResult",
    "Settings",
    "default_service",
    "get_nutrition",
    "search_foods",
]
