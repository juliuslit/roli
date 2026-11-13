"""Raw/cooked compatibility, decided from the USDA description with a fixed word table (spec 2A, section 5)."""

from __future__ import annotations

import re

from .models import Compatibility, PreparationState, RecordState

# "unprepared" and "unheated" are USDA's words for cured meats as sold (bacon, pancetta proxies, ham): the raw weight basis (Phase 3, 2026-11-04).
RAW_WORDS = ("raw", "unprepared", "uncooked", "unheated")
COOKED_PHRASES = (
    "cooked", "roasted", "baked", "boiled", "grilled", "broiled", "fried",
    "braised", "steamed", "toasted", "dry heat", "moist heat",
)
# Foods whose nutrient density changes with cooking (water loss), so the weight basis matters.
FLESH_PREFIXES = (
    "fish", "beef", "pork", "chicken", "turkey", "lamb", "veal", "game meat",
    "duck", "goose", "crustaceans", "mollusks", "egg",
)

_RAW = re.compile(r"\b(" + "|".join(RAW_WORDS) + r")\b", re.IGNORECASE)
_COOKED = re.compile(r"\b(" + "|".join(COOKED_PHRASES) + r")\b", re.IGNORECASE)


def record_state(description: str) -> RecordState:
    """'Fish, tuna, fresh, bluefin, raw' -> raw; '..., cooked, dry heat' -> cooked; 'Cheese, romano' -> unknown.
    Both kinds of words present also gives unknown rather than a guess."""
    raw = bool(_RAW.search(description))
    cooked = bool(_COOKED.search(description))
    if raw and not cooked:
        return "raw"
    if cooked and not raw:
        return "cooked"
    return "unknown"


def is_flesh_food(description: str) -> bool:
    """True when the description's first comma-separated word names meat, fish, poultry, shellfish or egg."""
    head = description.split(",", 1)[0].strip().lower()
    return head in FLESH_PREFIXES


def compatibility(ingredient_state: PreparationState, description: str) -> tuple[Compatibility, str | None]:
    """Return (status, issue_code). Only 'compatible' lets an ingredient count toward subtotals.

    as_used: fine for oils, cheeses, condiments, seeds, bread; refused for flesh foods, where
    raw and cooked weights are not interchangeable (D2).
    """
    state = record_state(description)
    if ingredient_state == "as_used":
        if is_flesh_food(description):
            return "unresolved", "as_used_not_accepted_for_flesh"
        return "compatible", None
    if ingredient_state == "unknown" or state == "unknown":
        return "unresolved", "preparation_unresolved"
    if ingredient_state == state:
        return "compatible", None
    return "mismatch", "preparation_mismatch"
