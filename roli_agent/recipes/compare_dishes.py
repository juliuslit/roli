"""Phase 2D: the internal dish-comparison prototype (Julius, 2026-11-03). Internal only; never shown to a user.

Per dish and nutrient, each scenario contributes an INTERVAL per restaurant portion from the best evidence it has, in this order:

    source_complete                 the published recipe is complete from source-stated weights; the interval is the portion range only
    complete_with_inferences        complete once the documented inferences are accepted (median sizes; I01 olive-oil cholesterol zero)
    modeled_range_complete          the adapted pair (2C assumptions) is complete at both bounds, with inferences
    modeled_range_external_bound    the pair is incomplete but every missing line is bounded by non-USDA evidence (bottarga, vinegar): the bound is
                                    ADDED to the upper end and labelled; it never enters a total
    lower_bound_only                the known subtotal: a lower bound, no upper bound

A dish's interval is the lowest low and, when at least one scenario has an upper bound, the highest upper bound among the bounded scenarios;
scenarios without an upper bound are named as a caveat and can only widen the picture (an incomplete recipe whose lower bound already exceeds the
bounded recipes' maximum removes the upper bound). Pairwise verdicts: `clear` when one dish's upper bound lies below the other's lower bound,
`overlapping` when both are bounded and intersect, `insufficient_evidence` otherwise. A disjoint pair is `well_supported` only when the margin
is not narrow and does not depend on an external-evidence bound (Julius, 2026-11-03: those bounds are modeled upper estimates, not guaranteed
limits, so a comparison that rests on them is `tentative`). A dish is never ranked on a lower bound alone. Saturated fat first, cholesterol second.
"""

from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from roli_nutrition.recipe import RecipeResult

from .models import AdaptedPair, DishComparison, DishInterval, PairwiseComparison, PortionedScenario, SamplingInputs, Scenario, ScenarioInterval
from .relevance import singular

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
DEFAULT_EVIDENCE = Path(__file__).resolve().parent / "blocked_evidence.csv"


class ExternalEvidence:
    """Non-USDA composition and amount evidence for lines no USDA record can calculate. Bounds the upper end of a modeled range; never a value."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows

    @classmethod
    def load(cls, path: Path = DEFAULT_EVIDENCE) -> "ExternalEvidence":
        with Path(path).open(encoding="utf-8") as f:
            return cls(list(csv.DictReader(f)))

    def find(self, name: str, description: str = "") -> dict[str, str] | None:
        """The row whose longest ingredient key appears in the line's name; a `record_keys` entry matching the start of the line's USDA
        description wins over name keys (a record-gap line keeps its record's identity whatever the parser called it)."""
        for row in self.rows:
            for key in (row.get("record_keys") or "").split(","):
                k = key.strip().lower()
                if k and description.lower().startswith(k):
                    return row
        words = " ".join(singular(t) for t in re.findall(r"[a-zà-ü‘’']+", name.lower()))
        best = None
        for row in self.rows:
            for key in row["ingredient_keys"].split(","):
                k = " ".join(singular(t) for t in key.strip().lower().split())
                if k and re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", words) and (best is None or len(k) > best[0]):
                    best = (len(k), row)
        return best[1] if best else None

    def upper_bound(self, name: str, nutrient: str, *, grams_in_recipe: Decimal | None, fraction_high: Decimal, description: str = "") -> tuple[Decimal, str] | None:
        """The most this line could add PER PORTION for the nutrient, with its source; None when the evidence does not bound it.
        A `zero` row bounds at 0 whatever the amount. Otherwise the amount is the line's own grams when the recipe states them (the record
        merely lacks the nutrient), else the row's `grams_high`; a `recipe_line` amount is scaled by the portion fraction, a `per_plate`
        amount (a menu-only garnish) counts once per plate."""
        row = self.find(name, description)
        if row is None:
            return None
        col = "sat_fat_g_per_100g_high" if nutrient == "saturated_fat_g" else "cholesterol_mg_per_100g_high"
        if row["bound_kind"] == "zero":
            if row.get(col, "") == "":
                return None
            return Decimal(0), f"{row['id']}: {row['sources'][:160]}"
        if not row.get(col):
            return None
        per100 = Decimal(row[col])
        if grams_in_recipe is not None:
            grams, how = grams_in_recipe, f"the line's own {grams_in_recipe.normalize()} g x f {fraction_high:.3g}"
            amount = grams * fraction_high
        elif row.get("grams_high"):
            grams = Decimal(row["grams_high"])
            if row.get("scope", "per_plate") == "recipe_line":
                amount, how = grams * fraction_high, f"{grams} g (amount estimated) x f {fraction_high:.3g}"
            else:
                amount, how = grams, f"{grams} g per plate (amount estimated)"
        else:
            return None
        return amount * per100 / 100, f"{row['id']}: {how} x {per100} per 100 g; {row['sources'][:100]}"


# -- scenario intervals ------------------------------------------------------------------------------------------


def _drivers(portioned: PortionedScenario, nutrient: str, limit: int = 3) -> list[str]:
    out = []
    if portioned.fraction_low is not None and portioned.fraction_high is not None:
        out.append(f"portion {portioned.model} rule {portioned.portion_rule_id}: f = {portioned.fraction_low.fraction:.3g}-{portioned.fraction_high.fraction:.3g} "
                   f"({portioned.fraction_high.arithmetic})")
    hi = portioned.high
    if hi is None or hi.calculation_status == "invalid":
        return out
    result = RecipeResult.model_validate(hi.calculation)
    assumed = []
    for ing in result.ingredients:
        if (ing.assumption or "").startswith("ASSUMED") and ing.resolved.get(nutrient):
            per_portion = getattr(ing.contribution, nutrient) / hi.servings_for_calculator
            assumed.append((per_portion, ing))
    for per_portion, ing in sorted(assumed, key=lambda t: -t[0])[:limit]:
        if per_portion > 0:
            out.append(f"assumed {ing.name}: {ing.grams_declared} g -> {per_portion:.3g} per portion at the high bound ({(ing.assumption or '')[9:60]})")
    for inf in hi.inferences:
        if inf.kind == "inferred_zero_nutrient" and inf.nutrient == nutrient:
            out.append(f"inference {inf.rule_id}: {inf.name} {nutrient} taken as 0 (record lacks the row)")
        elif inf.kind == "assumed_size_median":
            out.append(f"assumed median size: {inf.name} {inf.grams} g")
        elif inf.kind == "class_level_cup_weight":
            out.append(f"class-level cup weight: {inf.name} {inf.grams} g")
        elif inf.kind == "saturated_fat_ceiling" and inf.nutrient == nutrient:
            out.append(f"saturated fat ceiling: {inf.name} up to its total fat ({inf.value_per_100g} g per 100 g)")
    return out


def _split_totals(pb, nutrient: str) -> tuple[Decimal, Decimal]:
    """3K: (R, P) of one portioned bound: R = the whole-recipe total of the lines the recipe states (contributions of `total_recipe` lines plus the
    inferences on them); P = the per-plate total (per_serving lines, whose saved contribution is per plate x servings, divided back by the servings the
    calculator ran with, inferences on them likewise). Read from the saved calculation; f x R + P reproduces the bound's per-portion total."""
    calc = pb.calculation or {}
    basis = {i.get("ingredient_id"): i.get("quantity_basis", "total_recipe") for i in calc.get("ingredients", [])}
    r = p = Decimal(0)
    for i in calc.get("ingredients", []):
        if not (i.get("resolved") or {}).get(nutrient) or (i.get("contribution") or {}).get(nutrient) is None:
            continue
        v = Decimal(str(i["contribution"][nutrient]))
        if i.get("quantity_basis") == "per_serving":
            p += v
        else:
            r += v
    for inf in pb.inferences:
        if inf.nutrient == nutrient and inf.contribution is not None:
            if basis.get(inf.ingredient_id) == "per_serving":
                p += inf.contribution
            else:
                r += inf.contribution
    s = pb.servings_for_calculator if pb.servings_for_calculator else Decimal(1)
    return r, p / s


def _sampling_inputs(ps: PortionedScenario, nutrient: str, external_bound: Decimal = Decimal(0)) -> SamplingInputs | None:
    """3K: the sampler's inputs for one applicable portioned scenario; None when a bound is missing."""
    if ps.low is None or ps.high is None or ps.fraction_low is None or ps.fraction_high is None:
        return None
    r_lo, p_lo = _split_totals(ps.low, nutrient)
    r_hi, p_hi = _split_totals(ps.high, nutrient)
    il, ih = ps.fraction_low.inputs, ps.fraction_high.inputs
    d = lambda v: Decimal(v) if v not in (None, "") else None
    return SamplingInputs(kind="recipe", model=ps.model, rule_id=ps.portion_rule_id, recipe_total_low=r_lo, recipe_total_high=r_hi, per_plate_low=p_lo, per_plate_high=p_hi,
                          fraction_low=ps.fraction_low.fraction, fraction_high=ps.fraction_high.fraction,
                          plate_low_g=d(il.get("W_plate_g")), plate_high_g=d(ih.get("W_plate_g")), served_mass_low=d(il.get("M_served_g")), served_mass_high=d(ih.get("M_served_g")),
                          key_plate_low_g=d(il.get("K_plate_g")), key_plate_high_g=d(ih.get("K_plate_g")), key_recipe_low_g=d(il.get("K_recipe_g")), key_recipe_high_g=d(ih.get("K_recipe_g")),
                          dough_ball_low_g=d(il.get("dough_ball_g")), dough_ball_high_g=d(ih.get("dough_ball_g")), recipe_dough_g=d(il.get("recipe_dough_g")), external_bound=external_bound)


def _served_mass(ps: PortionedScenario | None) -> dict[str, Decimal | None]:
    """3D (12.1): the grams on the plate at each bound when the portion model states them: P2's W, or P3's f x the recipe's own mass when it is known."""
    out: dict[str, Decimal | None] = {"served_mass_low": None, "served_mass_high": None}
    if ps is None or ps.fraction_low is None or ps.fraction_high is None:
        return out
    for bound, f in (("low", ps.fraction_low), ("high", ps.fraction_high)):
        w = f.inputs.get("W_plate_g")
        m = f.inputs.get("M_recipe_g")
        if w:
            out[f"served_mass_{bound}"] = Decimal(w)
        elif m:
            out[f"served_mass_{bound}"] = (Decimal(m) * f.fraction).quantize(Decimal("0.1"))
    return out


def scenario_interval(scenario: Scenario, pair: AdaptedPair | None, portioned_published: PortionedScenario | None, portioned_pair: PortionedScenario | None,
                      nutrient: str, evidence: ExternalEvidence) -> ScenarioInterval | None:
    """The best-evidence interval of one scenario for one nutrient, per restaurant portion; None when no portion model applies."""
    pp = portioned_published if portioned_published is not None and portioned_published.applicable else None
    pr = portioned_pair if portioned_pair is not None and portioned_pair.applicable else None
    common = dict(scenario_id=scenario.scenario_id, nutrient=nutrient, **_served_mass(pp if pp is not None else pr))
    left_out = [i.name for i in scenario.inferences if i.kind in ("excluded_negligible", "excluded_not_eaten")]   # I03/I04/tags: complete by a stated rule, not from the source alone
    if pp is not None and pp.low is not None and pp.high is not None:
        lo, hi = pp.low.per_portion[nutrient], pp.high.per_portion[nutrient]
        if lo["total"] is not None and hi["total"] is not None and not any(i.kind in ("assumed_size_median", "class_level_cup_weight") for i in pp.low.inferences) and not left_out:
            return ScenarioInterval(**common, tier="source_complete", low=lo["total"], high=hi["total"], portion_model=pp.model,
                                    fraction_low=pp.fraction_low.fraction, fraction_high=pp.fraction_high.fraction, drivers=_drivers(pp, nutrient), sampling=_sampling_inputs(pp, nutrient))
        if lo["total_with_inferences"] is not None and hi["total_with_inferences"] is not None:
            return ScenarioInterval(**common, tier="complete_with_inferences", low=lo["total_with_inferences"], high=hi["total_with_inferences"], portion_model=pp.model,
                                    fraction_low=pp.fraction_low.fraction, fraction_high=pp.fraction_high.fraction, drivers=_drivers(pp, nutrient), sampling=_sampling_inputs(pp, nutrient))
    # 12.14.3: external bounds attach to the line they bound, whether or not an adapted pair was built: with no pair the published scenario is read the same way
    pr = pr if pr is not None else pp
    if pr is not None and pr.low is not None and pr.high is not None:
        lo, hi = pr.low.per_portion[nutrient], pr.high.per_portion[nutrient]
        drivers = _drivers(pr, nutrient)
        common["assumption_driven"] = bool(pair is not None and (pair.high.assumption_driven or pair.low.assumption_driven))
        if lo["total_with_inferences"] is not None and hi["total_with_inferences"] is not None:
            return ScenarioInterval(**common, tier="modeled_range_complete", low=lo["total_with_inferences"], high=hi["total_with_inferences"], portion_model=pr.model,
                                    fraction_low=pr.fraction_low.fraction, fraction_high=pr.fraction_high.fraction, drivers=drivers, sampling=_sampling_inputs(pr, nutrient))
        # incomplete at the high bound: can every remaining line be bounded by external evidence?
        it = pr.high.inferred_totals.get(nutrient)
        remaining = it.remaining_excludes if it is not None else ["unknown"]
        remaining_ids = it.remaining_ids if it is not None else []
        high_result = RecipeResult.model_validate(pr.high.calculation)
        by_id = {i.ingredient_id: i for i in high_result.ingredients}
        bounds, sources, unbounded = Decimal(0), [], []
        for k, entry in enumerate(remaining):
            name = entry.rsplit(" (", 1)[0]
            ing = by_id.get(remaining_ids[k]) if k < len(remaining_ids) else None
            grams = ing.grams_in_recipe if ing is not None else None
            desc = ing.usda.description if ing is not None and ing.usda is not None else ""
            b = evidence.upper_bound(name, nutrient, grams_in_recipe=grams, fraction_high=pr.fraction_high.fraction, description=desc)
            if b is None:
                unbounded.append(entry)
            else:
                bounds += b[0]
                sources.append(f"{name}: +{b[0]:.3g} {'g' if nutrient == 'saturated_fat_g' else 'mg'}: {b[1]}")
        low_known = lo["known_subtotal"] if lo["total_with_inferences"] is None else lo["total_with_inferences"]
        if not unbounded:
            high_known = hi["known_subtotal"] if hi["total_with_inferences"] is None else hi["total_with_inferences"]
            return ScenarioInterval(**common, tier="modeled_range_external_bound", low=low_known, high=high_known + bounds, portion_model=pr.model,
                                    fraction_low=pr.fraction_low.fraction, fraction_high=pr.fraction_high.fraction, external_bound=bounds, external_bound_sources=sources,
                                    unbounded_lines=[], drivers=drivers + [f"external upper bound +{bounds:.3g} from {len(sources)} line(s) (non-USDA evidence, labelled)"],
                                    sampling=_sampling_inputs(pr, nutrient, bounds))
        return ScenarioInterval(**common, tier="lower_bound_only", low=low_known, high=None, portion_model=pr.model, fraction_low=pr.fraction_low.fraction,
                                fraction_high=pr.fraction_high.fraction, unbounded_lines=unbounded, drivers=drivers)
    return None


# -- dish intervals and the comparison --------------------------------------------------------------------------------


def dish_interval(dish: str, nutrient: str, intervals: list[ScenarioInterval], n_without_portion: int = 0, sampler: Any | None = None) -> DishInterval:
    """3K: ``sampler`` is `sampling.make_sampler(...)`'s callable; given, the band (10th-90th percentile of simulated plates) is added beside the extremes."""
    caveats: list[str] = []
    if not intervals:
        return DishInterval(dish=dish, nutrient=nutrient, low=None, high=None, bounded=False, n_scenarios=0, n_bounded=0,
                            caveats=[f"no scenario could be portioned ({n_without_portion} without an applicable portion model)"])
    bounded = [i for i in intervals if i.high is not None]
    unbounded = [i for i in intervals if i.high is None]
    # the dish's low is the lowest low of the BOUNDED scenarios when there are any (2026-11-05, Julius: a midpoint must not make an incomplete subtotal look
    # complete; an incomplete recipe's known subtotal is a true but weak lower bound and is reported as a caveat instead); with no bounded scenario it is the
    # lowest known subtotal, as before, and the dish is not ranked
    low = min(i.low for i in bounded) if bounded else min(i.low for i in intervals)
    high = max(i.high for i in bounded) if bounded else None
    if bounded and unbounded and min(i.low for i in unbounded) < low:
        caveats.append(f"{sum(1 for i in unbounded if i.low < low)} incomplete recipe(s) have a lower known subtotal ({min(i.low for i in unbounded):.3g}) than the range's low; it is a partial figure and is not in the range")
    # the upper bound as it would be without the external-evidence tier: scenarios whose bound depends on it drop out of the max
    usda_bounded = [i for i in bounded if i.tier != "modeled_range_external_bound"]
    high_without_external = max(i.high for i in usda_bounded) if usda_bounded else None
    if unbounded:
        caveats.append(f"{len(unbounded)} of {len(intervals)} recipes have no upper bound ({'; '.join(f'{i.scenario_id.split(':')[0]}: {', '.join(i.unbounded_lines)[:80]}' for i in unbounded)})")
    if high is not None and any(i.low > high for i in unbounded):
        caveats.append("an incomplete recipe's lower bound already exceeds the bounded recipes' upper bound: the upper bound is withdrawn")
        high = None
    if high is not None and unbounded:
        caveats.append(f"upper bound from {len(bounded)} of {len(intervals)} recipes only")
    if n_without_portion:
        caveats.append(f"{n_without_portion} calculated recipe(s) had no applicable portion model and are not in this interval")
    tiers = sorted({i.tier for i in intervals})
    if "modeled_range_external_bound" in tiers:
        caveats.append("the upper bound includes external evidence bounds for lines no USDA record could calculate (labelled per scenario; never inside a total)")
    if "survey_dish_record" in tiers:
        caveats.append("includes a USDA Survey (FNDDS) fried-food record with USDA's own frying-oil amount, scaled to a modeled plate (experimental, assumption-driven)")
    driven = [i for i in intervals if i.assumption_driven]
    if driven:
        caveats.append(f"assumption-driven: assumed lines exceed 30 % of a known subtotal in {len(driven)} of {len(intervals)} recipes")
    if "source_complete" not in tiers:
        caveats.append("no recipe is complete from source-stated weights alone: every figure rests on documented inferences or 2C assumptions")
    drivers = []
    top = sorted(bounded, key=lambda i: -(i.high or 0))[:1]
    for i in top + ([] if bounded else intervals[:1]):
        drivers.extend(f"{i.scenario_id.split(':')[0]}: {d}" for d in i.drivers[:4])
    bound_driven = bool(high is not None and top and top[0].assumption_driven)
    if bound_driven:
        caveats.append("the upper bound comes from a recipe whose assumed lines exceed 30 % of the known subtotal (experimental weights rows)")
    band: dict[str, Any] = {}
    if sampler is not None and high is not None:
        res = sampler(dish, nutrient, intervals)
        if res.draws:
            band = dict(band_low=res.band_low, band_mid=res.band_mid, band_high=res.band_high, band_draws=res.draws, band_method=res.method, plate_source=res.plate_source,
                        recipe_weights=res.recipe_weights, set_aside=list(res.set_aside), fat_bands=res.fat_bands)
            caveats.extend(res.set_aside_notes)
            caveats.append(f"band (3K): most plates {res.band_low:.3g}-{res.band_high:.3g}, middle {res.band_mid:.3g}; the extremes {low:.3g}-{high:.3g} stay as the outer limits ({res.method})")
    return DishInterval(dish=dish, nutrient=nutrient, low=low, high=high, high_without_external=high_without_external if high is not None else None,
                        bound_assumption_driven=bound_driven, bounded=high is not None, n_scenarios=len(intervals), n_bounded=len(bounded), scenarios=intervals,
                        caveats=caveats, drivers=drivers, **band)


def _pairwise(a: DishInterval, b: DishInterval) -> PairwiseComparison:
    common = dict(dish_a=a.dish, dish_b=b.dish, nutrient=a.nutrient)
    if a.low is None or b.low is None:
        return PairwiseComparison(**common, verdict="insufficient_evidence", reason="a dish has no portioned scenario")
    unit = "g" if a.nutrient == "saturated_fat_g" else "mg"
    g = lambda v: f"{v.normalize():.3g}" if v != 0 else "0"
    bands = all(x.band_low is not None and x.band_high is not None for x in (a, b))
    for lower, other in ((a, b), (b, a)):
        if bands and lower.high is not None and not lower.high < other.low and lower.band_high < other.band_low:
            # 3K (12.20): most plates of one dish sit below most plates of the other, but the extremes still overlap: an order, and a tentative one
            margin = other.band_low - lower.band_high
            why = [f"most plates apart: {lower.dish}'s band ends at {g(lower.band_high)} {unit} and {other.dish}'s begins at {g(other.band_low)} {unit}, but the full ranges overlap "
                   f"({g(lower.low)}-{g(lower.high)} against {g(other.low)}-{g(other.high)} {unit})"]
            caveats = [c for c in lower.caveats + other.caveats if "assumption-driven" in c]
            return PairwiseComparison(**common, verdict="tentative", lower=lower.dish, margin=margin, tentative_because=why,
                                      reason=f"{lower.dish} most plates {g(lower.band_low)}-{g(lower.band_high)} {unit}; {other.dish} most plates {g(other.band_low)}-{g(other.band_high)} {unit}", caveats=caveats + why)
    for lower, other in ((a, b), (b, a)):
        if lower.high is not None and lower.high < other.low:
            margin = other.low - lower.high
            widths = [x.high - x.low for x in (lower, other) if x.high is not None]
            caveats = [c for c in lower.caveats + other.caveats if "upper bound" in c or "external evidence" in c or "assumption-driven" in c]
            why: list[str] = []
            if widths and margin < Decimal("0.1") * max(widths):
                why.append(f"narrow margin: {g(margin)} {unit} between {lower.dish}'s upper bound and {other.dish}'s lower bound, against ranges up to {g(max(widths))} {unit} wide")
            # does the verdict rest on an external-evidence bound? The lower dish's upper bound (or the other dish's lower bound) must hold without it.
            if lower.high_without_external is None:
                why.append(f"{lower.dish}'s upper bound exists only through external-evidence bounds (modeled upper estimates, not guaranteed limits)")
            elif lower.high_without_external != lower.high and lower.high_without_external >= other.low:
                why.append(f"without the external-evidence bounds {lower.dish}'s upper bound would be {g(lower.high_without_external)} {unit}, above {other.dish}'s lower bound")
            if lower.bound_assumption_driven:
                # Phase 3 (Julius, 2026-11-04): an order that rests on experimental ingredient assumptions is tentative, never presented as certain
                why.append(f"{lower.dish}'s upper bound comes from a recipe where assumed amounts (experimental weights rows) exceed 30 % of the known subtotal")
            verdict = "tentative" if why else "well_supported"
            return PairwiseComparison(**common, verdict=verdict, lower=lower.dish, margin=margin, tentative_because=why,
                                      reason=f"{lower.dish} at most {g(lower.high)} {unit} per portion; {other.dish} at least {g(other.low)} {unit}", caveats=caveats + why)
    if a.high is not None and b.high is not None:
        return PairwiseComparison(**common, verdict="overlapping", reason=f"{a.dish} {g(a.low)}-{g(a.high)} {unit} overlaps {b.dish} {g(b.low)}-{g(b.high)} {unit}",
                                  caveats=[c for c in a.caveats + b.caveats if "assumption-driven" in c])
    missing = [d.dish for d in (a, b) if d.high is None]
    lower_candidate = a.dish if a.low <= b.low else b.dish
    return PairwiseComparison(**common, verdict="insufficient_evidence",
                              reason=f"{' and '.join(missing)} ha{'s' if len(missing) == 1 else 've'} no upper bound; {lower_candidate} has the lower lower bound but a lower bound alone cannot rank it",
                              caveats=[c for d in (a, b) for c in d.caveats if "no upper bound" in c])


def compare_dishes(per_dish: dict[str, dict[str, DishInterval]]) -> DishComparison:
    """`per_dish`: nutrient -> dish -> DishInterval. Pairwise verdicts for both nutrients; an ordering only where saturated fat decides."""
    pairwise: list[PairwiseComparison] = []
    dishes = sorted({d for n in per_dish.values() for d in n})
    for nutrient in NUTRIENTS:
        ivs = per_dish.get(nutrient, {})
        for i, a in enumerate(dishes):
            for b in dishes[i + 1:]:
                if a in ivs and b in ivs:
                    pairwise.append(_pairwise(ivs[a], ivs[b]))
    sat = per_dish.get("saturated_fat_g", {})
    bounded = sorted((d for d in dishes if d in sat and sat[d].bounded), key=lambda d: (sat[d].high, sat[d].low))
    unbounded = [d for d in dishes if d in sat and not sat[d].bounded]
    sat_pairs = [p for p in pairwise if p.nutrient == "saturated_fat_g"]
    n_well = sum(1 for p in sat_pairs if p.verdict == "well_supported")
    n_tent = sum(1 for p in sat_pairs if p.verdict == "tentative")
    n_pairs = len(sat_pairs)
    note = (f"saturated fat decides {n_well + n_tent} of {n_pairs} dish pairs ({n_well} well supported, {n_tent} tentative); {len(bounded)} dishes have an upper bound, "
            f"{len(unbounded)} do not ({', '.join(unbounded) or 'none'}). Dishes without an upper bound are never ranked; cholesterol is reported as the secondary criterion.")
    statement = "INTERNAL 2D prototype: " + note + " Modeled restaurant portions from unreviewed rule rows; not verified restaurant values; not for users."
    flags = sorted({c for n in per_dish.values() for iv in n.values() for c in iv.caveats if "non-USDA" in c} | ({"unbounded_dishes"} if unbounded else set()))
    return DishComparison(intervals=per_dish, pairwise=pairwise, ordering=bounded + unbounded, ordering_note=note, statement=statement, flags=flags)
