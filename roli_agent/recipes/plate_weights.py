"""3K (SPEC_3_mvp.md 12.20): the measured plate weights behind each plate-size row, one sample per chain item or USDA FNDDS portion.

`scripts/build_cards.py` writes `recipes/plate_weights.csv` (rule_id, source, business, item, grams, kind, read_on) from the same MenuStat items, chain-sheet
items and FNDDS portions it summarises into each row's 10th-90th percentile range. The band sampler draws plate weights from these samples instead of pairing
the two ends of the range; the row's approved range truncates them (a sample outside the approved range is not drawn), and a row with fewer than the configured
minimum of samples falls back to a uniform draw over its approved range. Nothing here is a new figure: every sample is one measured item with its source.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "plate_weights.csv"
COLUMNS = ("rule_id", "source", "business", "item", "grams", "kind", "read_on")


class PlateWeights:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows
        self._by_rule: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            try:
                self._by_rule[r["rule_id"]].append(float(Decimal(r["grams"])))
            except (KeyError, ValueError, ArithmeticError):
                continue
        for v in self._by_rule.values():
            v.sort()

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> "PlateWeights":
        p = Path(path)
        if not p.exists():
            return cls([])
        with p.open(encoding="utf-8", newline="") as fh:
            return cls(list(csv.DictReader(fh)))

    def for_rule(self, rule_id: str, low: float | Decimal | None = None, high: float | Decimal | None = None) -> list[float]:
        """The samples for a row, sorted, truncated to [low, high] when given (the approved range)."""
        xs = self._by_rule.get(rule_id, [])
        lo = float(low) if low is not None else None
        hi = float(high) if high is not None else None
        return [x for x in xs if (lo is None or x >= lo) and (hi is None or x <= hi)]

    def enough(self, rule_id: str, n_min: int, low=None, high=None) -> bool:
        return len(self.for_rule(rule_id, low, high)) >= n_min

    def rule_ids(self) -> list[str]:
        return sorted(self._by_rule)
