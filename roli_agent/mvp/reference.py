"""The reference check and the flag file (SPEC_3_mvp.md 12.1, 12.9.6-7, 12.9.9; Julius, 2026-11-05 and 2026-11-06).

After a dish's saturated-fat interval is built and before ranking, the MIDDLE of its range is compared with the published figures on its dish-family card
(recipes/reference_figures.csv), per plate and per 100 g served when the served mass is known. A comparison fails when the middle is above ``factor`` x the
published high or below the published low / ``factor``. Since 12.18 (Julius, 2026-11-07) only a middle ABOVE the range flags: a middle below it is noted in the
diagnostics ("below the published range for this kind of dish; plain recipe") and the dish ranks.

Two figures minimum (12.9.6): a published range can flag a dish only when it rests on at least two independent figures, meaning different businesses, or
different brands for retail labels; several dishes of one chain, or two brands of one owner, count as one. A single figure is shown and does not flag.

Like with like (12.9.7): a figure may carry the frying fat it represents, stated by the business or shown by its saturated share of total fat. A labelled
figure is compared with the middle of Roli's range for that fat only; an unlabelled one with the middle of the whole range. So one basis can give several
comparisons, one per label. A fat with no figure is not checked.

A flagged dish is left out of the ranking and listed with the dishes not estimated. Published figures are used only here, never in a total. A flag is
temporary (12.1.4): when it opens, one line goes to ``runs/flags.jsonl`` with the run, the menu, the dish, the failed comparisons and the top contributors (12.9.9), the
lines with the largest share of the middle; the review, not the code, classifies the cause. A later run of the same menu with no failing check appends
a ``closed`` line.
"""

from __future__ import annotations

import csv
import json
import re
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..recipes.models import DishInterval

FLAG_REASON = "our estimate disagrees with published figures for this kind of dish"
BELOW_NOTE = "below the published range for this kind of dish; plain recipe"       # 12.18: a middle below the range is noted, not flagged; the dish ranks
KNOWN_LIMIT_REASON = "known limit of the data"
DEFAULT_KNOWN_LIMITS = Path(__file__).resolve().parent.parent / "recipes" / "known_limits.csv"
BASES = ("per_plate", "per_100g")
TOP_CONTRIBUTORS = 3


class Comparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    basis: str                                  # per_plate | per_100g
    choice: str = ""                            # the frying fat the figures represent; "" = unlabelled, compared with the whole range
    choice_basis: list[str] = Field(default_factory=list)
    checked: bool = False                       # True only when this comparison may flag
    roli_middle: Decimal | None = None
    published_low: Decimal | None = None
    published_high: Decimal | None = None
    allowed_low: Decimal | None = None          # published_low / factor
    allowed_high: Decimal | None = None         # published_high x factor
    independent_figures: int = 0
    figures: list[str] = Field(default_factory=list)
    failed: bool = False
    direction: str = ""                         # above | below | ""
    note: str = ""


class ReferenceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card_id: str | None = None
    checked: bool = False
    reason_unchecked: str = ""
    factor: Decimal = Decimal("1.5")
    served_mass_low: Decimal | None = None
    served_mass_high: Decimal | None = None
    comparisons: list[Comparison] = Field(default_factory=list)
    flagged: bool = False
    below_published: bool = False               # 12.18: a checked comparison fell below the published range; the dish ranks and its diagnostics say so
    top_contributors: list[dict[str, Any]] = Field(default_factory=list)
    known_limit: dict[str, str] | None = None   # 12.12.6: the row of known_limits.csv this flag falls under

    @property
    def failed(self) -> list[Comparison]:
        return [c for c in self.comparisons if c.checked and c.failed]


def _label(c: Comparison) -> str:
    return c.basis + (f" ({c.choice})" if c.choice else "")


def _compare(basis: str, choice: str, figures: list[Any], middle: Decimal | None, factor: Decimal, min_figures: int, labels: dict[str, str], note: str) -> Comparison:
    low, high = min(f.sat_fat_g for f in figures), max(f.sat_fat_g for f in figures)
    independent = sum({f.group: f.n_businesses for f in figures}.values())      # 12.16.7: an aggregate row counts the chains behind it
    out = Comparison(basis=basis, choice=choice, choice_basis=sorted({labels[f.id] for f in figures if labels.get(f.id)}), roli_middle=middle, published_low=low, published_high=high,
                     independent_figures=independent, figures=[f"{f.business}: {f.sat_fat_g} g ({f.product})" for f in figures], note=note)
    if middle is None:
        out.note = note or "Roli's middle is not known on this basis"
        return out
    out.allowed_low, out.allowed_high = low / factor, high * factor
    if independent < min_figures:
        out.note = f"shown only: {independent} independent figure, {min_figures} are needed to flag (12.9.6)"
        return out
    out.checked = True
    out.direction = "above" if middle > out.allowed_high else "below" if middle < out.allowed_low else ""
    out.failed = out.direction == "above"                 # 12.18 (Julius, 2026-11-07): only a middle above the published range flags
    if out.direction == "below":
        out.note = BELOW_NOTE
    return out


def reference_check(sat: DishInterval | None, card: Any | None, *, factor: Decimal, min_figures: int = 2, vegetable_max: Decimal = Decimal("0.20"), animal_min: Decimal = Decimal("0.35"),
                    choice_ranges: dict[str, dict[str, dict[str, str]]] | None = None, fat_bands: dict[str, dict[str, Any]] | None = None) -> ReferenceCheck:
    """``sat`` is the dish's saturated-fat interval (per plate); ``card`` a PortionRule with its figures (None = no card); ``choice_ranges`` the plate's range for
    each frying fat, from the Survey estimate."""
    f = Decimal(str(factor))
    if card is None:
        return ReferenceCheck(reason_unchecked="no reference: no dish-family card for this dish", factor=f)
    if not card.has_reference:
        return ReferenceCheck(card_id=card.id, reason_unchecked="no reference: the card carries no published figure", factor=f)
    if sat is None or sat.low is None or sat.high is None:
        return ReferenceCheck(card_id=card.id, reason_unchecked="no range to check: the dish has no bounded saturated-fat interval", factor=f)
    whole = sat.band_mid if sat.band_mid is not None else (sat.low + sat.high) / 2        # 3K (12.20): the band's median is Roli's middle when a band exists
    bounded = [i for i in sat.scenarios if i.high is not None]
    masses = [(i.served_mass_low, i.served_mass_high) for i in bounded]
    mass_known = bool(masses) and all(m[0] is not None and m[1] is not None for m in masses)
    mass_low = min(m[0] for m in masses) if mass_known else None
    mass_high = max(m[1] for m in masses) if mass_known else None
    mass_mid = (mass_low + mass_high) / 2 if mass_known and (mass_low + mass_high) > 0 else None
    ranges = choice_ranges or {}
    has_fat_choice = bool(getattr(card, "choices", {}).get("oil"))      # a card without a fat choice has nothing to label; one with it keeps its labels even when no fat range exists
    comparisons: list[Comparison] = []
    for basis in BASES:
        groups: dict[str, list[Any]] = {}
        labels: dict[str, str] = {}
        for fig in card.figures_on(basis):
            choice, how = fig.choice(Decimal(str(vegetable_max)), Decimal(str(animal_min))) if has_fat_choice else ("", "")
            groups.setdefault(choice, []).append(fig)
            labels[fig.id] = how
        for choice, figures in sorted(groups.items()):
            note = ""
            if choice and choice not in ranges:
                middle, note = None, f"Roli has no range for {choice} on this plate"
            else:
                r = ranges[choice]["saturated_fat_g"] if choice else None
                if choice and fat_bands and choice in fat_bands and fat_bands[choice].get("mid") is not None:
                    plate_middle = Decimal(str(fat_bands[choice]["mid"]))                  # 3K: that fat's band median
                else:
                    plate_middle = (Decimal(r["low"]) + Decimal(r["high"])) / 2 if r else whole
                if basis == "per_plate":
                    middle = plate_middle.quantize(Decimal("0.001"))
                elif mass_mid is None:
                    middle, note = None, "served mass unknown for at least one bounded recipe: per-100 g comparison skipped"
                else:
                    middle = (plate_middle / mass_mid * 100).quantize(Decimal("0.001"))
            comparisons.append(_compare(basis, choice, figures, middle, f, min_figures, labels, note))
    checked = any(c.checked for c in comparisons)
    return ReferenceCheck(card_id=card.id, checked=checked, reason_unchecked="" if checked else "no comparison may flag: each rests on fewer than the minimum of independent figures, or Roli's figure is unknown",
                          factor=f, served_mass_low=mass_low, served_mass_high=mass_high, comparisons=comparisons, flagged=any(c.failed for c in comparisons),
                          below_published=any(c.checked and c.direction == "below" for c in comparisons))


# -- top contributors (12.9.9) ----------------------------------------------------------------------------------------------------------


def _bound_lines(interval: dict[str, Any], bound: str, estimate: dict[str, Any] | None, survey: dict[str, Any] | None) -> dict[str, tuple[str, Decimal]]:
    """{line id: (name, grams of saturated fat per plate)} of one scenario at one bound, read from the calculator's own output."""
    out: dict[str, tuple[str, Decimal]] = {}
    sid = interval["scenario_id"]
    if interval["tier"] == "survey_dish_record":
        calc = (survey or {}).get("calculations", {}).get(bound)
        servings = Decimal(1)
    else:
        wanted = sid + "::adapted" if interval["tier"].startswith("modeled") else sid
        ps = next((p for p in (estimate or {}).get("portioned", []) if p["derived_from"] == wanted and p.get("applicable")), None)
        b = (ps or {}).get(bound) or {}
        calc = b.get("calculation")
        servings = Decimal(str(b.get("servings_for_calculator") or 1))
    for ing in (calc or {}).get("ingredients", []):
        value = (ing.get("contribution") or {}).get("saturated_fat_g")
        if value is not None and (ing.get("resolved") or {}).get("saturated_fat_g"):
            out[ing["ingredient_id"]] = (ing["name"], Decimal(str(value)) / servings)
    return out


def top_contributors(sat: dict[str, Any], estimate: dict[str, Any] | None, survey: dict[str, Any] | None, limit: int = TOP_CONTRIBUTORS) -> list[dict[str, Any]]:
    """The lines with the largest share of the middle: the mean of each line's saturated fat in the scenario that sets the low and the one that sets the high."""
    scenarios = [s for s in sat.get("scenarios", []) if s.get("high") is not None]
    if not scenarios or sat.get("low") is None or sat.get("high") is None:
        return []
    low_s = min(scenarios, key=lambda s: Decimal(str(s["low"])))
    high_s = max(scenarios, key=lambda s: Decimal(str(s["high"])))
    low_lines, high_lines = _bound_lines(low_s, "low", estimate, survey), _bound_lines(high_s, "high", estimate, survey)
    middle = (Decimal(str(sat["low"])) + Decimal(str(sat["high"]))) / 2
    if middle <= 0:
        return []
    rows = []
    for key in set(low_lines) | set(high_lines):
        lo, hi = low_lines.get(key, ("", Decimal(0))), high_lines.get(key, ("", Decimal(0)))
        grams = (lo[1] + hi[1]) / 2
        name = hi[0] if hi[0] and hi[0] == lo[0] else " / ".join(x for x in (lo[0], hi[0]) if x)
        rows.append({"line": name, "sat_fat_g": str(grams.quantize(Decimal("0.01"))), "share_of_middle": str((grams / middle).quantize(Decimal("0.01")))})
    rows.sort(key=lambda r: -Decimal(r["sat_fat_g"]))
    return rows[:limit]


# -- known limits of the data (12.12.6) ---------------------------------------------------------------------------------------------------


class KnownLimits:
    """The rows Julius has decided. ``find`` answers for one flagged dish: the row of its card whose contributor is the dish's top contributor."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows

    @classmethod
    def load(cls, path: Path = DEFAULT_KNOWN_LIMITS) -> "KnownLimits":
        with Path(path).open(encoding="utf-8", newline="") as f:
            return cls(list(csv.DictReader(f)))

    def find(self, dish_type: str | None, contributors: list[dict[str, Any]]) -> dict[str, str] | None:
        top = contributors[0]["line"] if contributors else ""
        return next((r for r in self.rows if r["card"] == dish_type and re.search(rf"\b{re.escape(r['top_contributor'])}\b", top, re.I)), None)


# -- the flag file ------------------------------------------------------------------------------------------------------------------------


class FlagFile:
    """Append-only JSON lines under runs/; a flag is identified by (menu, dish) and is open while its latest line says so."""

    def __init__(self, path: Path | None) -> None:
        self.path = Path(path) if path is not None else None
        self._lock = threading.Lock()

    def lines(self) -> list[dict[str, Any]]:
        if self.path is None or not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def latest(self) -> dict[tuple[str, str], dict[str, Any]]:
        out: dict[tuple[str, str], dict[str, Any]] = {}
        for row in self.lines():
            out[(row.get("menu", ""), row.get("dish", ""))] = row
        return out

    def open_flags(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {k: v for k, v in self.latest().items() if v.get("status") == "open"}

    def _append(self, row: dict[str, Any]) -> None:
        if self.path is None:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")

    def raise_flag(self, *, run_id: str, menu: str, dish: str, dish_type: str | None, check: ReferenceCheck) -> dict[str, Any]:
        first = check.failed[0]
        status = "known_limit" if check.known_limit else "open"
        row = {"recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": status, "run": run_id, "menu": menu, "dish": dish, "dish_type": dish_type,
               "card": check.card_id, "comparison": ", ".join(_label(c) for c in check.failed), "roli_middle": str(first.roli_middle), "published_low": str(first.published_low),
               "published_high": str(first.published_high), "direction": first.direction, "independent_figures": first.independent_figures, "top_contributors": check.top_contributors}
        if check.known_limit:
            row.update(note=f"{KNOWN_LIMIT_REASON}: {check.known_limit['reason']} (decided by {check.known_limit['decided_by']}, {check.known_limit['date']})")
        if self.latest().get((menu, dish), {}).get("status") != status:     # 12.10.11: the file records a flag opening, changing or closing; the run keeps the row either way
            self._append(row)
        return row

    def close_flag(self, *, run_id: str, menu: str, dish: str, check: ReferenceCheck) -> dict[str, Any] | None:
        """Append a closed line when the latest line for (menu, dish) is open and no check that may flag now fails."""
        if self.latest().get((menu, dish), {}).get("status") not in ("open", "known_limit"):
            return None
        passed = [c for c in check.comparisons if c.checked]
        row = {"recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": "closed", "run": run_id, "menu": menu, "dish": dish, "card": check.card_id,
               "note": "every check that may flag now passes: " + "; ".join(f"{_label(c)} {c.roli_middle} vs {c.published_low}-{c.published_high}" for c in passed)}
        self._append(row)
        return row
