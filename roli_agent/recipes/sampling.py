"""3K (SPEC_3_mvp.md 12.20): the band. Roli's extremes pair the smallest plate with the leanest recipe and the largest plate with the richest, so the two
causes of width multiply. The band draws many plates instead: a recipe (weighted by its relevance grade and how many menu ingredients it covers), a position
between the adapted pair's two bounds (where the assumed amounts sit), and a plate weight from the measured samples behind the row, and re-forms the per-plate
value from the saved Phase 2A totals (V = f x R + P, see `models.SamplingInputs`). The 10th, 50th and 90th percentiles of the draws are the band a tester reads
("most plates"); the extremes stay on the diagnostics page. Everything is deterministic: the seed is derived from the dish, the nutrient and the scenario ids.

Nothing here calls a model or the calculator; the draws only re-combine figures the calculator already produced. Decimals are converted to floats for the
draws and the three quantiles are converted back; the extremes are never recomputed.
"""

from __future__ import annotations

import csv
import hashlib
import math
import random
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from .models import ScenarioInterval
from .plate_weights import PlateWeights

DEFAULT_FAT_PRIOR = Path(__file__).resolve().parent / "frying_fat_prior.csv"
GRADE_WEIGHT = {"high": 1.0, "medium": 0.5, "low": 0.25, "ungraded": 0.5}
DEFAULT_DRAWS = 2000
Q_LOW, Q_MID, Q_HIGH = 0.10, 0.50, 0.90
OUTLIER_FACTOR = 5.0
MIN_FAT_DRAWS = 20
MIDPOINT_FLOOR = 0.01


@dataclass
class BandResult:
    band_low: Decimal | None = None
    band_mid: Decimal | None = None
    band_high: Decimal | None = None
    draws: int = 0
    method: str = ""
    plate_source: str = ""
    recipe_weights: dict[str, Decimal] = field(default_factory=dict)
    set_aside: list[str] = field(default_factory=list)
    set_aside_notes: list[str] = field(default_factory=list)
    fat_bands: dict[str, dict[str, Decimal]] = field(default_factory=dict)


def band_seed(dish: str, nutrient: str, scenario_ids: list[str]) -> int:
    """A stable seed from the dish, the nutrient and the sorted scenario ids (never Python's hash, which changes between processes)."""
    raw = "|".join([dish, nutrient, *sorted(scenario_ids)])
    return int(hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8], 16)


def quantile(values: list[float], q: float) -> float:
    """Nearest-rank quantile of a sorted list."""
    if not values:
        raise ValueError("no values")
    k = max(0, min(len(values) - 1, math.ceil(q * len(values)) - 1))
    return values[k]


def load_frying_fat_prior(path: Path | str = DEFAULT_FAT_PRIOR) -> dict[str, float] | None:
    """{fat label: share} from recipes/frying_fat_prior.csv; None when the file is absent or empty. Labels are the card's choice labels (card PR15: 'vegetable oil', 'beef dripping')."""
    p = Path(path)
    if not p.exists():
        return None
    with p.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("fat_label") or "").strip() and (r.get("share") or "").strip()]
    if not rows:
        return None
    out: dict[str, float] = {}
    for r in rows:
        try:
            out[r["fat_label"].strip().lower()] = float(r["share"])
        except ValueError:
            continue
    return out or None


class PlateSampler:
    """Draws one plate weight (or key weight, or dough ball) for a row: from the measured samples behind the row, truncated to the approved range, when there
    are at least `n_min`; from a plate-weight model when one is on and the row is a P2 row; otherwise uniformly over the approved range. Reports where each
    draw came from."""

    def __init__(self, weights: PlateWeights | None, *, n_min: int = 10, model: Any | None = None, dish_words: str = "", section: str = "", family: str | None = None) -> None:
        self.weights = weights or PlateWeights([])
        self.n_min = n_min
        self.model = model
        self.dish_words, self.section, self.family = dish_words, section, family
        self._cache: dict[tuple, list[float]] = {}

    def draw(self, rng: random.Random, rule_id: str | None, model_kind: str | None, low: Decimal | None, high: Decimal | None) -> tuple[float, str]:
        lo = float(low) if low is not None else None
        hi = float(high) if high is not None else None
        if lo is None or hi is None:
            return (lo if lo is not None else hi if hi is not None else 0.0), "interval"
        if hi < lo:
            lo, hi = hi, lo
        if self.model is not None and model_kind == "P2" and rule_id:
            v = self.model.sample(rng, self.dish_words, self.section, self.family, lo, hi)
            if v is not None:
                return float(v), "model"
        key = (rule_id, lo, hi)
        if key not in self._cache:
            self._cache[key] = self.weights.for_rule(rule_id, lo, hi) if rule_id else []
        xs = self._cache[key]
        if len(xs) >= self.n_min:
            return xs[rng.randrange(len(xs))], f"samples:{len(xs)}"
        return rng.uniform(lo, hi), "uniform"


def _lerp(a: float, lo: Decimal | None, hi: Decimal | None) -> float | None:
    if lo is None or hi is None:
        return None
    return float(lo) + a * (float(hi) - float(lo))


def recipe_weights(intervals: list[ScenarioInterval], grade_of: dict[str, str], coverage_of: dict[str, Decimal | None], *, medium_weight: float = 0.5) -> dict[str, float]:
    """Draw weight per scenario: the relevance grade (high 1.0, medium `medium_weight`) times a coverage factor 0.5 + 0.5 x the share of menu ingredients the
    recipe lists (unknown coverage counts as 1); a survey record weighs 1.0."""
    out: dict[str, float] = {}
    gw = dict(GRADE_WEIGHT)
    gw["medium"] = medium_weight
    for iv in intervals:
        if iv.sampling is not None and iv.sampling.kind == "survey":
            out[iv.scenario_id] = 1.0
            continue
        g = gw.get(grade_of.get(iv.scenario_id, "ungraded"), 0.5)
        cov = coverage_of.get(iv.scenario_id)
        c = 1.0 if cov is None else 0.5 + 0.5 * float(cov)
        out[iv.scenario_id] = max(0.0, g * c)
    return out


def outliers(intervals: list[ScenarioInterval], factor: float = OUTLIER_FACTOR) -> list[tuple[str, str]]:
    """With three or more bounded recipes, the ones whose midpoint is more than `factor` from the median of the others' midpoints (on the log scale), with a note."""
    bounded = [iv for iv in intervals if iv.high is not None]
    if len(bounded) < 3:
        return []
    mids = {iv.scenario_id: max(float(iv.low + iv.high) / 2, MIDPOINT_FLOOR) for iv in bounded}
    out = []
    for sid, m in mids.items():
        others = sorted(v for k, v in mids.items() if k != sid)
        med = others[len(others) // 2] if len(others) % 2 else (others[len(others) // 2 - 1] + others[len(others) // 2]) / 2
        ratio = max(m / med, med / m)
        if ratio > factor:
            out.append((sid, f"{sid.split(':')[0]} set aside as an outlier: its midpoint {m:.3g} is {ratio:.0f}x the others' median {med:.3g}; it stays in the extremes, not in the band"))
    if len(out) >= 2 and 3 * len(out) >= len(bounded):
        return []                                       # two or more recipes making a third or more of them: a second kind of the dish, not an outlier; every recipe stays in the draws
    return out


def sample_band(intervals: list[ScenarioInterval], *, plates: PlateSampler, draws: int = DEFAULT_DRAWS, seed: int = 0, grade_of: dict[str, str] | None = None,
                coverage_of: dict[str, Decimal | None] | None = None, outlier_factor: float = OUTLIER_FACTOR, fat_prior: dict[str, float] | None = None,
                medium_weight: float = 0.5, q_low: float = Q_LOW, q_high: float = Q_HIGH) -> BandResult:
    """The band over the bounded scenarios that carry sampling inputs. Returns an empty result when none does."""
    bounded = sorted((iv for iv in intervals if iv.high is not None and iv.sampling is not None), key=lambda iv: iv.scenario_id)
    res = BandResult()
    if not bounded or draws <= 0:
        return res
    aside = outliers(bounded, outlier_factor)
    aside_ids = {sid for sid, _ in aside}
    res.set_aside = [sid for sid, _ in aside]
    res.set_aside_notes = [note for _, note in aside]
    kept = [iv for iv in bounded if iv.scenario_id not in aside_ids] or bounded
    weights = recipe_weights(kept, grade_of or {}, coverage_of or {}, medium_weight=medium_weight)
    res.recipe_weights = {k: Decimal(str(round(v, 3))) for k, v in weights.items()}
    total = sum(weights.values())
    if total <= 0:
        weights = {k: 1.0 for k in weights}
        total = float(len(weights))
    cum, acc = [], 0.0
    for iv in kept:
        acc += weights[iv.scenario_id] / total
        cum.append(acc)
    rng = random.Random(seed)
    values: list[float] = []
    sources: Counter = Counter()
    fat_values: dict[str, list[float]] = {}
    for _ in range(draws):
        u = rng.random()
        iv = kept[next((k for k, c in enumerate(cum) if u <= c), len(kept) - 1)]
        si = iv.sampling
        a = rng.random()
        if si.kind == "survey":
            labels = sorted(si.choice_ranges)
            if labels:
                if fat_prior:
                    shares = [max(0.0, fat_prior.get(l.lower(), 0.0)) for l in labels]
                    if sum(shares) <= 0:
                        shares = [1.0] * len(labels)
                else:
                    shares = [1.0] * len(labels)
                t = rng.random() * sum(shares)
                acc2, label = 0.0, labels[-1]
                for l, s in zip(labels, shares):
                    acc2 += s
                    if t <= acc2:
                        label = l
                        break
                r = si.choice_ranges[label]
                v = float(r["low"]) + a * (float(r["high"]) - float(r["low"]))
                fat_values.setdefault(label, []).append(v)
            else:
                v = float(iv.low) + a * (float(iv.high) - float(iv.low))
            sources["survey"] += 1
            values.append(v)
            continue
        r_tot = _lerp(a, si.recipe_total_low, si.recipe_total_high) or 0.0
        p_tot = _lerp(a, si.per_plate_low, si.per_plate_high) or 0.0
        ext = a * float(si.external_bound or 0)
        v = None
        if si.model == "P2":
            m = _lerp(a, si.served_mass_low, si.served_mass_high)
            if m and si.plate_low_g is not None and si.plate_high_g is not None:
                w, src = plates.draw(rng, si.rule_id, "P2", si.plate_low_g, si.plate_high_g)
                v = r_tot * w / m + p_tot + ext
                sources[src] += 1
        elif si.model == "P3":
            kr = _lerp(a, si.key_recipe_low_g, si.key_recipe_high_g)
            if kr and si.key_plate_low_g is not None and si.key_plate_high_g is not None:
                kp, src = plates.draw(rng, si.rule_id, "P3", si.key_plate_low_g, si.key_plate_high_g)
                v = (kp / kr) * r_tot + p_tot + ext
                sources[src] += 1
        elif si.model == "P1":
            if si.recipe_dough_g and si.dough_ball_low_g is not None and si.dough_ball_high_g is not None:
                ball, src = plates.draw(rng, si.rule_id, "P1", si.dough_ball_low_g, si.dough_ball_high_g)
                f = min(ball / float(si.recipe_dough_g), 1.0)
                v = f * r_tot + p_tot + ext
                sources[src] += 1
            elif si.fraction_low is not None:
                v = float(si.fraction_low) * r_tot + p_tot + ext
                sources["unit count"] += 1
        if v is None:                                   # inputs missing: the interval's own ends, interpolated
            v = float(iv.low) + a * (float(iv.high) - float(iv.low))
            sources["interval"] += 1
        values.append(max(v, 0.0))
    values.sort()
    dec = lambda x: Decimal(str(round(x, 6)))
    res.band_low, res.band_mid, res.band_high = dec(quantile(values, q_low)), dec(quantile(values, Q_MID)), dec(quantile(values, q_high))
    res.draws = len(values)
    if len(sources) == 1:
        res.plate_source = next(iter(sources))
    else:
        res.plate_source = "mixed(" + ", ".join(f"{k} {100 * n / len(values):.0f} %" for k, n in sources.most_common()) + ")"
    res.method = (f"{len(values)} draws over {len(kept)} recipe(s) by relevance weight, a position between each pair's bounds and a plate weight ({res.plate_source}); "
                  f"band = {int(q_low * 100)}th-{int(q_high * 100)}th percentile" + (f"; {len(aside)} recipe(s) set aside" if aside else "")
                  + ("; frying fat drawn by the prior" if fat_prior and fat_values else ""))
    for label, vals in fat_values.items():
        if len(vals) >= MIN_FAT_DRAWS:
            vals.sort()
            res.fat_bands[label] = {"low": dec(quantile(vals, q_low)), "mid": dec(quantile(vals, Q_MID)), "high": dec(quantile(vals, q_high))}
    return res


def make_sampler(plates: PlateSampler, *, draws: int, grade_of: dict[str, str], coverage_of: dict[str, Decimal | None], outlier_factor: float, fat_prior: dict[str, float] | None,
                 medium_weight: float = 0.5, q_low: float = Q_LOW, q_high: float = Q_HIGH) -> Callable[[str, str, list[ScenarioInterval]], BandResult]:
    """The callable `dish_interval` takes: (dish, nutrient, intervals) -> BandResult, seeded from the dish, the nutrient and the scenario ids."""
    def run(dish: str, nutrient: str, intervals: list[ScenarioInterval]) -> BandResult:
        seed = band_seed(dish, nutrient, [iv.scenario_id for iv in intervals])
        return sample_band(intervals, plates=plates, draws=draws, seed=seed, grade_of=grade_of, coverage_of=coverage_of, outlier_factor=outlier_factor,
                           fat_prior=fat_prior, medium_weight=medium_weight, q_low=q_low, q_high=q_high)
    return run
