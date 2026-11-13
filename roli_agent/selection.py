"""The structural guard shared by the food path (Phase 1E) and recipe matching (Phase 2B-2).

An LLM may *propose* a USDA record; Python *accepts* it only if that FDC ID is in the candidate
list USDA returned for this very search. An ID from memory, a string, a float or `true` is rejected.
"""

from __future__ import annotations

from typing import Any, Iterable


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def accept_proposed_id(proposed: Any, allowed: Iterable[int]) -> int | None:
    """Return the proposed FDC ID if it is a real integer among `allowed`, else None."""
    if not is_int(proposed):
        return None
    return proposed if proposed in set(allowed) else None
