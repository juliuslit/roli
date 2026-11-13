"""roli_agent: the first LangGraph application for Roli.

Phase 1E scope: two input paths.
- A single-food question -> USDA search -> record selection -> validated values -> deterministic answer.
- A menu photo -> the existing menu reader -> dishes and listed ingredients, no nutrition totals.

Division of labour: the LLM interprets text and pictures; Python (the `roli_nutrition`
library and this package) does every lookup, every number and every decision about
what may be said. No nutrition figure in a reply can come from the LLM.
"""

from .graph import build_graph, run_roli

__all__ = ["build_graph", "run_roli"]
