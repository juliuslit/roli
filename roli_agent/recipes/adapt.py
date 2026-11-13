"""Phase 2C: menu-adapted scenarios, internal only (SPEC_2C_menu_adapted_scenarios.md, revision 3).

A published scenario is never modified. `adapt_pairs` derives one low/high PAIR per calculated published scenario:
every gap that a permitted source can fill gets an explicit assumed weight (low and high), the modeled list goes
through the unchanged Phase 2A calculator, and the result carries every assumption with its source, computed
display class and computed materiality. Modes: "approved" uses only rows with `approved_by` filled (plus the two
record-derived sources below); "experimental" also uses `proposed_unreviewed` and `usda_measure` rows without
changing their review status; blocked rows are never used. Missing USDA nutrient values stay missing (D23).
"""

from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from roli_nutrition import ErrorResult
from roli_nutrition.recipe import RecipeCalculator, RecipeResult
from roli_nutrition.recipe.preparation import is_flesh_food, record_state

from .inference import LOW_FAT_G_PER_100G, NutrientFacts, apply_inference_layer
from .models import (AdaptedPair, AdaptedScenario, AdaptMode, Assumption, InternalSummary, Scenario, Unfilled)
from .relevance import singular

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
FLOOR = {"saturated_fat_g": Decimal("0.005"), "cholesterol_mg": Decimal("0.5")}        # Phase 2A display floor
REFERENCE = {"saturated_fat_g": Decimal("20"), "cholesterol_mg": Decimal("300")}      # daily reference amounts, materiality tiers only
ASSUMPTION_SHARE_WARNING = Decimal("0.30")
DEFAULT_TABLE = Path(__file__).resolve().parent / "assumed_weights.csv"
BLOCKED = "blocked_questionable_proxy"


# -- computed classifications -------------------------------------------------------------------


def display_class(sat: float | None, chol: float | None, grams_high: Decimal | None) -> str:
    if sat is None or chol is None:
        return "nutrient_missing"
    if grams_high is None:
        return "nutrient_missing"
    s, c = Decimal(str(sat)) * grams_high / 100, Decimal(str(chol)) * grams_high / 100
    if Decimal(str(sat)) == 0 and Decimal(str(chol)) == 0:
        return "zero_nutrient"
    if s < FLOOR["saturated_fat_g"] and c < FLOOR["cholesterol_mg"]:
        return "low_impact"
    return "displayable"


def materiality(sat_g: Decimal | None, chol_mg: Decimal | None) -> str:
    """Absolute high-bound contribution against daily reference amounts; separate from the display class."""
    if sat_g is None or chol_mg is None:
        return "unknown"
    if sat_g < FLOOR["saturated_fat_g"] and chol_mg < FLOOR["cholesterol_mg"]:
        return "negligible"
    worst = max(sat_g / REFERENCE["saturated_fat_g"], chol_mg / REFERENCE["cholesterol_mg"])
    if worst < Decimal("0.01"):
        return "minor"
    if worst < Decimal("0.05"):
        return "moderate"
    return "major"


# -- the weights table -------------------------------------------------------------------------


class WeightRow:
    def __init__(self, row: dict[str, str]) -> None:
        self.id = row["id"]
        self.role = row["ingredient_role"]
        self.keys = [k.strip().lower() for k in row.get("ingredient_keys", "").split(",") if k.strip()]
        self.fdc_id = int(row["fdc_id"]) if row.get("fdc_id") else None
        self.description = row.get("usda_description", "")
        self.low = Decimal(row["low_g"]) if row.get("low_g") else None
        self.high = Decimal(row["high_g"]) if row.get("high_g") else None
        self.basis = row.get("basis", "")
        self.measures = row.get("measures", "")
        self.review_status = row.get("review_status", "")
        self.approved_by = row.get("approved_by", "").strip()
        self.notes = row.get("notes", "")
        # 2D: what the range describes. per_plate = one restaurant plate (enters a recipe for N servings as a per-serving amount);
        # per_count_unit = one item (multiplied by the line's stated count). Missing column -> per_plate, the 2C meaning of "restaurant usage".
        self.amount_basis = (row.get("amount_basis") or "per_plate").strip()
        # Phase 3: a row may be limited to portion dish types ("pizza_neapolitan"); empty = any dish. A restricted row is never used for an unknown type.
        self.dish_types = {t.strip() for t in (row.get("dish_types") or "").split(",") if t.strip()}
        # Phase 3: a regular expression on the ORIGINAL line name that rules the row out ("roasted peppers" is not black pepper).
        pat = (row.get("exclude_pattern") or "").strip()
        self.exclude = re.compile(pat, re.I) if pat else None
        # Phase 3: USDA description heads this row's food can stand in for. A menu-only cheese on a recipe that already has a cheese line may
        # REPLACE it (low bound 0) rather than add to it (high bound): the menu names the kitchen's cheese, not an extra one.
        self.substitutes_family = {t.strip().lower() for t in (row.get("substitutes_family") or "").split(",") if t.strip()}
        # 2026-11-05 (Julius): a row whose amount depends on the ingredient's ROLE on the plate (a sprinkle of feta over fish vs feta as a salad's
        # component). When the role is clear, the garnish takes the lower half of the row's range and the substantial ingredient the upper half;
        # when it is ambiguous the whole range stays. Cheese, cured meat, nut, seed and olive rows; never oils, dressings or vegetables.
        self.role_sensitive = (row.get("role_sensitive") or "").strip().lower() in ("yes", "true", "1")

    @property
    def blocked(self) -> bool:
        return self.review_status.startswith(BLOCKED) or self.basis == "blocked"

    @property
    def sourced(self) -> bool:
        """3D (12.2.2): a row whose measures or notes say 'no source' has no measured figure behind its amounts."""
        return not re.search(r"\bno (?:measured )?source\b", f"{self.measures} {self.notes} {self.basis}", re.I)

    def usable(self, mode: AdaptMode, allow_unsourced: bool = True) -> tuple[bool, str | None]:
        if self.blocked:
            return False, "blocked_row"
        if not allow_unsourced and not self.sourced:
            return False, "row_unsourced"
        if self.fdc_id is None or self.low is None or self.high is None:
            return False, "row_incomplete"
        if mode == "approved" and not self.approved_by:
            return False, "row_unapproved"
        return True, None


DEFAULT_DATA = DEFAULT_TABLE.parent / "assumed_weights_data.csv"
DATA_MIN_FAMILY, DATA_MIN_ANY = 8, 15          # 3K (12.20): recipes behind a data range before it replaces the hand row (dish family / any family)
DATA_MAX_SPREAD = Decimal(20)                   # a data range wider than this (p90 / p10) describes mismatched lines, not one role: the hand row stands
DATA_MAX_DISTANCE = Decimal(4)                  # a data median more than this many times outside the hand row's range is another food or another basis: the hand row stands


class DataRange:
    """3K: a per-serving range built from stored recipes by scripts/build_assumed_weights.py: the 10th-90th percentile of the amounts recipe writers state."""

    def __init__(self, row: dict[str, str]) -> None:
        self.row_id, self.family = row["row_id"], row["dish_family"]
        self.n_recipes, self.n_lines = int(row["n_recipes"]), int(row["n_lines"])
        self.low, self.high, self.median = Decimal(row["p10_g"]), Decimal(row["p90_g"]), Decimal(row["p50_g"])
        self.sources, self.built_on, self.review_status = row.get("sources", ""), row.get("built_on", ""), row.get("review_status", "built_from_recipes")


class WeightsTable:
    def __init__(self, rows: list[WeightRow], data: list[DataRange] | None = None) -> None:
        self.rows = rows
        self.data: dict[tuple[str, str], DataRange] = {(d.row_id, d.family): d for d in (data or [])}

    @classmethod
    def load(cls, path: Path = DEFAULT_TABLE, data_path: Path | None = DEFAULT_DATA, *, use_data: bool = True) -> "WeightsTable":
        with Path(path).open(encoding="utf-8") as f:
            rows = [WeightRow(r) for r in csv.DictReader(f)]
        data: list[DataRange] = []
        if use_data and data_path is not None and Path(data_path).exists():
            with Path(data_path).open(encoding="utf-8", newline="") as f:
                data = [DataRange(r) for r in csv.DictReader(f)]
        return cls(rows, data)

    @staticmethod
    def data_usable(row: WeightRow, d: "DataRange | None", n_min: int) -> tuple[bool, str]:
        """Whether a data range may replace the hand row: enough recipes, a spread under DATA_MAX_SPREAD (wider means the lines were not one role), a median within
        DATA_MAX_DISTANCE of the hand row's range (further means another food or another basis). The reason is written for the report and the diagnostics."""
        if d is None:
            return False, "no data range"
        if d.n_recipes < n_min:
            return False, f"{d.n_recipes} recipes, {n_min} needed"
        if d.low <= 0 or d.high / d.low > DATA_MAX_SPREAD:
            return False, f"spread {d.low}-{d.high} g is wider than {DATA_MAX_SPREAD}x: not one role"
        if row.low is not None and row.high is not None and (d.median < row.low / DATA_MAX_DISTANCE or d.median > row.high * DATA_MAX_DISTANCE):
            return False, f"median {d.median} g is more than {DATA_MAX_DISTANCE}x outside the hand row {row.low}-{row.high} g"
        return True, "used"

    def range_for(self, row: WeightRow, dish_type: str | None) -> tuple[Decimal, Decimal, str, str, DataRange | None]:
        """(low, high, basis words, review status, the data range used or None). 3K (12.20): the data range of the dish family when at least DATA_MIN_FAMILY recipes
        state the amount and the guards of `data_usable` hold; else the all-family data range at DATA_MIN_ANY recipes when the hand row is not limited to dish types;
        else the hand row as it stands."""
        if row.amount_basis == "per_plate":
            d = self.data.get((row.id, dish_type or ""))
            if self.data_usable(row, d, DATA_MIN_FAMILY)[0]:
                return d.low, d.high, f"built from recipes (12.20): the 10th-90th percentile of per-serving amounts in {d.n_recipes} {dish_type} recipes ({d.n_lines} lines), built {d.built_on}; hand row {row.low}-{row.high} g set aside", d.review_status, d
            d = self.data.get((row.id, "any"))
            if not row.dish_types and self.data_usable(row, d, DATA_MIN_ANY)[0]:
                return d.low, d.high, f"built from recipes (12.20): the 10th-90th percentile of per-serving amounts in {d.n_recipes} recipes of any dish ({d.n_lines} lines), built {d.built_on}; hand row {row.low}-{row.high} g set aside", d.review_status, d
        return row.low, row.high, "", row.review_status, None

    def find(self, name: str, dish_type: str | None = None) -> WeightRow | None:
        """The row whose longest key appears, as whole words, in the singularised name. A row limited to dish types applies only when the
        dish's type is one of them (W32 cheese on a pizza vs W31 cheese on a plate); on a tie the dish-typed row wins."""
        words = " ".join(singular(t) for t in re.findall(r"[a-zà-ü']+", name.lower()))
        best: tuple[tuple[int, int, int], WeightRow] | None = None
        for row in self.rows:
            if row.dish_types and (dish_type is None or dish_type not in row.dish_types):
                continue
            if row.exclude is not None and row.exclude.search(name):
                continue
            for key in row.keys:
                k = " ".join(singular(t) for t in key.split())
                score = (len(k), 0 if row.blocked else 1, 1 if row.dish_types else 0)   # longest key; usable beats blocked (W03c over W03b); dish-typed beats generic
                if re.search(rf"(?<![a-z'])" + re.escape(k) + r"(?![a-z])", words) and (best is None or score > best[0]):
                    best = (score, row)
        return best[1] if best else None


# -- adaptation --------------------------------------------------------------------------------


def _state_for(description: str) -> str:
    st = record_state(description)
    if st in ("raw", "cooked"):
        return st
    return "unknown" if is_flesh_food(description) else "as_used"


CLINGING_ROW = "W09"


def _nutrition(service: Any, fdc_id: int):
    r = service.get_nutrition(fdc_id)
    return None if isinstance(r, ErrorResult) else r


def adapt_pairs(scenarios: list[Scenario], *, service: Any, table: WeightsTable, mode: AdaptMode, dish_type: str | None = None, item: Any | None = None,
                medium_covered: bool = False, low_fat: Decimal = LOW_FAT_G_PER_100G) -> tuple[list[AdaptedPair], InternalSummary]:
    if mode == "off":
        raise ValueError("adapt_pairs needs mode 'approved' or 'experimental'")
    calc = RecipeCalculator(service)
    pairs: list[AdaptedPair] = []
    published = [s for s in scenarios if s.status == "calculated" and s.calculation is not None]
    for s in published:
        frozen = s.model_dump_json()
        pair = _adapt_one(s, service=service, table=table, mode=mode, calc=calc, dish_type=dish_type, item=item, medium_covered=medium_covered, low_fat=low_fat)
        assert s.model_dump_json() == frozen, "the published scenario must not change"   # byte-for-byte guard
        if pair is not None:
            pairs.append(pair)
    return pairs, _internal_summary(mode, published, pairs)


GARNISH_WORDS = re.compile(r"\b(sprinkled?|sprinkling|crumbled?|crumbles?|shav(?:ed|ings)|grated|grating|dust(?:ed|ing)|scatter(?:ed)?|shaving|flakes? of|a little|a touch of|"
                           r"to finish|finish(?:ed)? with|to garnish|garnish(?:ed)?|for serving|to serve|on top|topped with|drizzle)\b", re.I)
SUBSTANTIAL_WORDS = re.compile(r"\b(salad of|platter|board|plate of|wedge of|slab of|whole|half a|baked|melted|stuffed with|filled with|generous|loaded)\b", re.I)
PROTEIN_DISH_TYPES = {"fish_main", "meat_main", "crudo_starter", "fish_starter"}
COMPONENT_DISH_TYPES = {"leaf_salad_starter", "tomato_salad_starter", "pizza_neapolitan"}


def _segment_with(text: str, name: str) -> str | None:
    """The comma- or semicolon-separated piece of `text` that names the ingredient, or None."""
    words = [singular(t) for t in re.findall(r"[a-zà-ü']+", name.lower())]
    if not words:
        return None
    for seg in re.split(r"[,;]|\band\b|\bwith\b", text):
        seg_words = {singular(t) for t in re.findall(r"[a-zà-ü']+", seg.lower())}
        if all(w in seg_words for w in words):
            return seg
    return None


def ingredient_role(name: str, *, menu_name: str = "", menu_description: str = "", line_text: str | None = None, dish_type: str | None = None) -> tuple[str | None, str]:
    """('garnish' | 'substantial' | None, reason). Clear roles only: a garnish word beside the ingredient on the menu or in the recipe line; the
    ingredient named in the dish's own name on a salad or pizza (substantial); a cheese, cured meat or nut listed beside a fish or meat main
    (garnish: the protein is the dish). Anything else is ambiguous and keeps the row's whole range."""
    for label, text in (("recipe line", line_text or ""), ("menu description", menu_description), ("dish name", menu_name)):
        seg = text if label == "recipe line" and text else _segment_with(text, name)      # a recipe line is one ingredient: read all of it
        if seg is None:
            continue
        if GARNISH_WORDS.search(seg):
            return "garnish", f"the {label} says '{seg.strip()[:60]}'"
        if SUBSTANTIAL_WORDS.search(seg):
            return "substantial", f"the {label} says '{seg.strip()[:60]}'"
    if dish_type in COMPONENT_DISH_TYPES and _segment_with(menu_name, name) is not None:
        return "substantial", f"named in the dish's own name on a {dish_type.replace('_', ' ')}"
    if dish_type in PROTEIN_DISH_TYPES and _segment_with(menu_description, name) is not None:
        return "garnish", f"listed beside a {dish_type.replace('_', ' ')}: the fish or meat is the dish"
    return None, "role ambiguous: the row's whole range applies"


def _adapt_one(s: Scenario, *, service, table: WeightsTable, mode: AdaptMode, calc: RecipeCalculator, dish_type: str | None = None, item: Any | None = None, medium_covered: bool = False,
               low_fat: Decimal = LOW_FAT_G_PER_100G) -> AdaptedPair | None:
    assumptions: list[Assumption] = []
    unfilled: list[Unfilled] = []
    base_lines: list[dict] = []
    present_heads = {(line.match.description or "").split(",", 1)[0].strip().lower() for line in s.ingredients
                     if line.origin == "recipe" and line.match is not None and line.match.fdc_id is not None and line.blocker is None}
    for line in s.ingredients:
        weighed = None
        if line.excluded_from_calculation is not None:
            gap = _gap_for(line, line.mass_gap)[0] if line.mass_gap else None
            weighed = _fill(line, gap, service=service, table=table, mode=mode, dish_type=dish_type, present_heads=present_heads, item=item, scenario=s) if gap else None
            if not isinstance(weighed, Assumption):
                continue                                    # never sent to the calculator, published or adapted; it must not come back as an unknown line
            weighed.mass_only = True                        # 12.14.12: a near-zero line's weight, found for the plate-weight method
        base = {"name": line.name[:200] or "ingredient", "fdc_id": line.match.fdc_id if line.match else None,
                "grams": str(line.conversion.grams) if line.conversion.grams is not None else None,
                "preparation_state": line.preparation_state, "assumption": line.assumption, "ingredient_id": line.ingredient_id}
        base_lines.append(base)
        if weighed is not None:
            assumptions.append(weighed)
            continue
        if line.blocker is None:
            if line.parsed is not None and "assumed_size_median" in line.parsed.flags and len(line.parsed.portion_options) >= 1:
                # D20 revised: the published scenario carries the median size; the pair carries the labelled spread (smallest to largest size)
                a = _spread_for_median_line(line, service)
                if not isinstance(a, str):
                    assumptions.append(a)
            continue
        gap, reason = _gap_for(line)
        if gap is None:
            unfilled.append(Unfilled(ingredient_id=line.ingredient_id, name=line.name, reason=reason))
            continue
        a = _fill(line, gap, service=service, table=table, mode=mode, dish_type=dish_type, present_heads=present_heads, item=item, scenario=s, medium_covered=medium_covered)
        if isinstance(a, str):
            unfilled.append(Unfilled(ingredient_id=line.ingredient_id, name=line.name, reason=a))
        else:
            assumptions.append(a)
    if not assumptions:
        return None
    by_id = {a.ingredient_id: a for a in assumptions}
    results = {}
    for bound in ("low", "high"):
        lines = []
        for base in base_lines:
            a = by_id.get(base["ingredient_id"])
            if a is None:
                lines.append(base)
                continue
            grams = a.grams_low if bound == "low" else a.grams_high
            per_plate = a.amount_basis == "per_plate"
            lines.append({**base, "fdc_id": a.fdc_id, "grams": str(grams), "preparation_state": _state_for(a.description),
                          "quantity_basis": "per_serving" if per_plate else "total_recipe",
                          "assumption": f"ASSUMED ({a.gap}, {a.source}{', ' + a.row_id if a.row_id else ''}, {bound}): {grams} g{' per plate' if per_plate else ''}; {a.basis}; "
                                        f"{a.review_status}; recipe stated: {'nothing' if a.grams_declared is None else a.grams_declared}"
                                        f"{'; published scenario used the median ' + str(a.published_grams) + ' g' if a.published_grams is not None else ''}"[:500]})
        result = calc.calculate({"recipe_name": f"{s.scenario_id}::adapted_{bound}", "servings": str(s.source.servings), "ingredients": lines})
        results[bound] = (result, lines)
    facts = NutrientFacts(service, {l.ingredient_id for l in s.ingredients if l.tag_kind == "plain_food"}, low_fat)
    low, high = (_adapted_scenario(results[b][0], b, assumptions, s, results[b][1], facts) for b in ("low", "high"))
    results = {b: r for b, (r, _) in results.items()}
    for a in assumptions:                                   # per-assumption contributions, from the calculator's own output
        for bound, res in results.items():
            ing = next((i for i in res.ingredients if i.ingredient_id == a.ingredient_id), None) if isinstance(res, RecipeResult) else None
            values = {n: (getattr(ing.contribution, n) if ing is not None else None) for n in NUTRIENTS}
            if bound == "low":
                a.contribution_low = values
            else:
                a.contribution_high = values
    sens_ps, sens_tot = {}, {}
    for n in NUTRIENTS:
        if isinstance(results["low"], RecipeResult) and isinstance(results["high"], RecipeResult):
            sens_ps[n] = results["high"].per_serving[n].known_subtotal - results["low"].per_serving[n].known_subtotal
            sens_tot[n] = results["high"].totals[n].known_subtotal - results["low"].totals[n].known_subtotal
        else:
            sens_ps[n] = sens_tot[n] = None
    flags = sorted({f for f in s.flags} | {"menu_adapted"} | ({"assumption_driven"} if low.assumption_driven or high.assumption_driven else set()))
    return AdaptedPair(pair_id=f"{s.scenario_id}::adapted", derived_from=s.scenario_id, mode=mode, servings=s.source.servings, assumptions=assumptions,
                       unfilled=unfilled, low=low, high=high, sensitivity_per_serving=sens_ps, sensitivity_total=sens_tot, flags=flags)


def _gap_for(line, blocker: str | None = None) -> tuple[str | None, str]:
    b = blocker or line.blocker
    if b == "menu_only":
        return "G1_menu_only", ""
    if b in ("seasoning_unknown_quantity", "optional_unknown_quantity", "unknown_quantity"):
        return "G2_unquantified", ""
    if b == "cooking_medium_unknown_amount":
        return "G6_cooking_medium", ""              # 12.14.2: what clings to the food is W09's amount, never the recipe weight
    if b == "proxy_portion_refused":
        return "G4_proxy_count", ""
    if b == "no_usda_portion":
        if line.parsed is not None and line.parsed.unit in ("pinch", "dash", "handful"):
            return "G2_unquantified", ""         # "1 pinch red pepper flakes": a pinch is not a USDA measure on any record; the table row for the role applies (Phase 3)
        if line.parsed is not None and "portion_size_unspecified" in line.parsed.flags and line.match and line.match.match_type == "direct":
            return "G3_size_unspecified", ""
        if line.parsed is not None and "portion_ambiguous" in line.parsed.flags and len(line.parsed.portion_options) >= 2:
            return "G5_measure_ambiguous", ""
        return None, "ambiguous_or_missing_measure"
    if b == "nutrient_not_reported":
        return None, "nutrient_missing_on_record"
    if b in ("unresolved_usda", "state_conflict", "usda_error", "preparation_unresolved"):
        return None, "no_usda_record"
    return None, f"other:{b}"


def _fill(line, gap: str, *, service, table: WeightsTable, mode: AdaptMode, dish_type: str | None = None, present_heads: set[str] | None = None, item: Any | None = None,
          scenario: Scenario | None = None, medium_covered: bool = False) -> Assumption | str:
    if gap == "G6_cooking_medium":
        return "fried_record_covers_this_oil" if medium_covered else _fill_medium(line, service, table, mode)
    if gap == "G3_size_unspecified":
        return _fill_from_size_labels(line, service)
    if gap == "G5_measure_ambiguous":
        return _fill_from_measure_options(line, service)
    if gap == "G2_unquantified" and line.match and line.match.fdc_id is not None and not re.search(r"\b(and|or|&)\b", line.name):
        # a compound line ("kosher salt and freshly ground black pepper") names more than the matched record; it goes to the table
        nut = _nutrition(service, line.match.fdc_id)
        if nut is not None and nut.saturated_fat_g == 0 and nut.cholesterol_mg == 0:
            return _fill_zero_nutrient(line, service, nut)
    row = table.find(line.name, dish_type)
    if row is None:
        return "no_table_row"
    ok, why = row.usable(mode)
    if not ok:
        return why
    nut = _nutrition(service, row.fdc_id)
    if nut is None:
        return "row_record_unavailable"
    cls = display_class(nut.saturated_fat_g, nut.cholesterol_mg, row.high)
    sat_high = Decimal(str(nut.saturated_fat_g)) * row.high / 100 if nut.saturated_fat_g is not None else None
    chol_high = Decimal(str(nut.cholesterol_mg)) * row.high / 100 if nut.cholesterol_mg is not None else None
    proxy = "proxy" in (row.notes + " " + row.measures).lower() or (line.match is not None and line.match.match_type == "proxy")
    note = ""
    if line.match and line.match.fdc_id is not None and line.match.fdc_id != row.fdc_id:
        note = f"the line's matched record {line.match.fdc_id} differs from the row's record {row.fdc_id}; the row's record is used"
    # 2D: how the row's grams enter the recipe. A count line (G4: "4 heads little gem", "1 pinch flakes", "2 large pluots") takes the row as an
    # amount per counted item times the stated count, as a whole-recipe amount. Otherwise a per_plate row is a per-serving amount (one plate),
    # a per_count_unit row ("egg yolk, one") a single item.
    low, high, data_basis, status, data = table.range_for(row, dish_type)      # 3K (12.20): a range built from stored recipes replaces the hand row where enough recipes exist
    amount_basis = row.amount_basis
    qty = line.parsed.quantity if line.parsed is not None else None
    if gap == "G4_proxy_count" and qty is not None:
        low, high, amount_basis, status = row.low * qty, row.high * qty, "per_count_unit", row.review_status
        basis = f"{row.basis}: {row.measures}; row taken per counted item x {qty} stated"
    elif amount_basis == "per_plate":
        basis = (f"{data_basis}; per plate (enters the recipe as a per-serving amount)" if data is not None else f"{row.basis}: {row.measures}; per plate (enters the recipe as a per-serving amount)")
    else:
        basis = f"{row.basis}: {row.measures}; one item"
    role_note = ""
    if row.role_sensitive and gap in ("G1_menu_only", "G2_unquantified") and amount_basis == "per_plate":
        role, why = ingredient_role(line.name, menu_name=getattr(item, "name", "") or "", menu_description=getattr(item, "description", "") or "",
                                    line_text=line.line, dish_type=dish_type)
        mid = (low + high) / 2
        if role == "garnish":
            high, role_note = mid, f"role: garnish ({why}) -> lower half of the range {low}-{high} g"
        elif role == "substantial":
            low, role_note = mid, f"role: substantial ({why}) -> upper half of the range {low}-{high} g"
        if role_note:
            basis += f"; {role_note}"
    if gap == "G1_menu_only" and row.substitutes_family and present_heads and (row.substitutes_family & present_heads):
        # the recipe already has a line of this family: the menu's word may name THAT ingredient (low 0) or an addition to it (high unchanged)
        family = ", ".join(sorted(row.substitutes_family & present_heads))
        low = Decimal(0)
        note = (note + "; " if note else "") + f"the recipe already has a '{family}' line: the menu's {line.name} may replace it (low bound 0 g) or add to it (high bound)"
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap=gap, source="table_row", row_id=row.id, fdc_id=row.fdc_id,
                      description=nut.description, grams_low=low, grams_high=high, basis=basis, amount_basis=amount_basis,
                      review_status=status, display_class=cls, materiality_at_high=materiality(sat_high, chol_high),
                      composition_proxy=proxy, note=note)


def _fill_medium(line, service, table: WeightsTable, mode: AdaptMode) -> Assumption | str:
    """12.14.2, one rule: every cooking medium gets W09's clinging amount per plate, on the line's own record. A USDA fried-food record answers for a deep-fried dish instead (the caller)."""
    row = next((r for r in table.rows if r.id == CLINGING_ROW), None)
    if row is None:
        return "no_table_row"
    ok, why = row.usable(mode)
    if not ok:
        return why
    fdc_id = line.match.fdc_id if line.match is not None and line.match.fdc_id is not None else row.fdc_id
    nut = _nutrition(service, fdc_id)
    if nut is None:
        return "row_record_unavailable"
    sat_high = Decimal(str(nut.saturated_fat_g)) * row.high / 100 if nut.saturated_fat_g is not None else None
    chol_high = Decimal(str(nut.cholesterol_mg)) * row.high / 100 if nut.cholesterol_mg is not None else None
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap="G6_cooking_medium", source="table_row", row_id=row.id, fdc_id=nut.fdc_id, description=nut.description,
                      grams_low=row.low, grams_high=row.high, amount_basis="per_plate", basis=f"cooking medium (line tag): only what clings to the food is eaten, {row.low}-{row.high} g per plate; {row.measures}",
                      review_status=row.review_status, display_class=display_class(nut.saturated_fat_g, nut.cholesterol_mg, row.high), materiality_at_high=materiality(sat_high, chol_high),
                      composition_proxy=bool(line.match and line.match.match_type == "proxy"))


def _fill_zero_nutrient(line, service, nut) -> Assumption | str:
    portions = service.get_portions(nut.fdc_id)
    if isinstance(portions, ErrorResult) or not portions.portions:
        return "zero_nutrient_no_measure"
    smallest = min(portions.portions, key=lambda p: p.gram_weight / p.amount)
    grams = Decimal(str(smallest.gram_weight)) / Decimal(str(smallest.amount))
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap="G2_unquantified", source="zero_nutrient_nominal", fdc_id=nut.fdc_id,
                      description=nut.description, grams_low=grams, grams_high=grams,
                      basis=f"nominal weight = the record's smallest household measure '{smallest.label}' = {smallest.gram_weight:g} g; USDA reports 0 g and 0 mg per 100 g, so any weight contributes 0",
                      review_status="D5 zero-nutrient (approved in principle for 2C)", display_class="zero_nutrient", materiality_at_high="negligible")


def _spread_for_median_line(line, service) -> Assumption | str:
    """D20 revised: a line the published scenario weighed at the median of the record's sizes; the pair takes the smallest listed size as
    low and the largest as high (the labels the converter recorded), so the sensitivity to the size assumption is visible."""
    options = sorted(line.parsed.portion_options, key=lambda o: Decimal(o["grams"]))
    low, high = Decimal(options[0]["grams"]), Decimal(options[-1]["grams"])
    nut = _nutrition(service, line.match.fdc_id)
    if nut is None:
        return "row_record_unavailable"
    cls = display_class(nut.saturated_fat_g, nut.cholesterol_mg, high)
    sat_high = Decimal(str(nut.saturated_fat_g)) * high / 100 if nut.saturated_fat_g is not None else None
    chol_high = Decimal(str(nut.cholesterol_mg)) * high / 100 if nut.cholesterol_mg is not None else None
    labels = "; ".join(f"'{o['label']}' -> {Decimal(o['grams']):.4g} g" for o in options)
    single = len(options) == 1
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap="G3_size_unspecified", source="record_size_labels", fdc_id=nut.fdc_id,
                      description=nut.description, grams_low=low, grams_high=high, published_grams=line.conversion.grams,
                      basis=f"{line.parsed.quantity} x the record's listed sizes ({labels}); low = smallest, high = largest; the published scenario used the median",
                      review_status="record size labels; published scenario carries the median (D20 revised 2026-11-03: assumed_size_median)",
                      display_class=cls, materiality_at_high=materiality(sat_high, chol_high), note="single labelled size" if single else "")


def _fill_from_size_labels(line, service) -> Assumption | str:
    """G3: the record lists sizes (by word or by dimension) and the recipe names none: low = smallest listed whole item, high = largest
    (D20: labelled, never a median). A record with a single sized label gives low = high, flagged as a single label."""
    from .convert import NOT_A_WHOLE_ITEM, is_sized_label
    portions = service.get_portions(line.match.fdc_id)
    if isinstance(portions, ErrorResult) or not portions.portions:
        return "ambiguous_or_missing_measure"
    sized = [p for p in portions.portions if not NOT_A_WHOLE_ITEM.search(p.label) and p.measure.upper() != "RACC" and is_sized_label(p.label)]
    if not sized:
        return "ambiguous_or_missing_measure"
    per_item = sorted(((Decimal(str(p.gram_weight)) / Decimal(str(p.amount)), p) for p in sized), key=lambda t: t[0])
    qty = line.parsed.quantity
    low, high = per_item[0][0] * qty, per_item[-1][0] * qty
    nut = _nutrition(service, line.match.fdc_id)
    if nut is None:
        return "row_record_unavailable"
    cls = display_class(nut.saturated_fat_g, nut.cholesterol_mg, high)
    sat_high = Decimal(str(nut.saturated_fat_g)) * high / 100 if nut.saturated_fat_g is not None else None
    chol_high = Decimal(str(nut.cholesterol_mg)) * high / 100 if nut.cholesterol_mg is not None else None
    if len(sized) == 1:
        basis = f"{qty} x the record's only listed size '{per_item[0][1].label}' = {per_item[0][1].gram_weight:g} g (single labelled size: low = high)"
    else:
        basis = f"{qty} x the record's smallest listed size '{per_item[0][1].label}' = {per_item[0][1].gram_weight:g} g to its largest '{per_item[-1][1].label}' = {per_item[-1][1].gram_weight:g} g"
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap="G3_size_unspecified", source="record_size_labels", fdc_id=nut.fdc_id,
                      description=nut.description, grams_low=low, grams_high=high, basis=basis,
                      review_status="record size labels (D20: labelled size assumption, not a median)", display_class=cls, materiality_at_high=materiality(sat_high, chol_high),
                      note="single labelled size" if len(sized) == 1 else "")


def _fill_from_measure_options(line, service) -> Assumption | str:
    """G5 (2C.1): the line's unit matches several labels of the record that weigh differently ("1 tsp, leaves" 1 g vs "1 tsp, ground"
    1.8 g; "1 cup, cubes" vs "1 cup, crumbs"). The published line stays unknown (D20: no default); the pair takes the smallest label
    as low and the largest as high, both labelled, never averaged. On a composition proxy the labels are the proxy's volume measures (D21)."""
    options = sorted(line.parsed.portion_options, key=lambda o: Decimal(o["grams"]))
    if len(options) < 2:
        return "ambiguous_or_missing_measure"
    low, high = Decimal(options[0]["grams"]), Decimal(options[-1]["grams"])
    nut = _nutrition(service, line.match.fdc_id)
    if nut is None:
        return "row_record_unavailable"
    cls = display_class(nut.saturated_fat_g, nut.cholesterol_mg, high)
    sat_high = Decimal(str(nut.saturated_fat_g)) * high / 100 if nut.saturated_fat_g is not None else None
    chol_high = Decimal(str(nut.cholesterol_mg)) * high / 100 if nut.cholesterol_mg is not None else None
    labels = "; ".join(f"'{o['label']}' -> {Decimal(o['grams']):.4g} g" for o in options)
    return Assumption(ingredient_id=line.ingredient_id, name=line.name, gap="G5_measure_ambiguous", source="record_measure_labels", fdc_id=nut.fdc_id,
                      description=nut.description, grams_low=low, grams_high=high,
                      basis=f"the line's measure matches {len(options)} labels of the record: {labels}; low = smallest, high = largest",
                      review_status="record measure labels (D20: the published line stays unknown; the pair carries the labelled spread)",
                      display_class=cls, materiality_at_high=materiality(sat_high, chol_high),
                      composition_proxy=bool(line.match and line.match.match_type == "proxy"))


def _adapted_scenario(result, bound: str, assumptions: list[Assumption], published: Scenario, calculator_input: list[dict] | None = None, facts: NutrientFacts | None = None) -> AdaptedScenario:
    if not isinstance(result, RecipeResult):
        return AdaptedScenario(bound=bound, calculation=result.model_dump(mode="json"), calculation_status="invalid", calculator_input=calculator_input or [])
    inferences, inferred_totals = apply_inference_layer(result, facts=facts, bound=bound)        # the nutrient facts on this bound (size medians are pair assumptions here)
    assumed_ids = {a.ingredient_id for a in assumptions}
    proxy_ids = {l.ingredient_id for l in published.ingredients if l.match and l.match.match_type == "proxy" and l.ingredient_id not in assumed_ids}
    proxy_ids |= {a.ingredient_id for a in assumptions if a.composition_proxy}
    contribution, share, percent, proxy_share = {}, {}, {}, {}
    for n in NUTRIENTS:
        resolved = {i.ingredient_id: getattr(i.contribution, n) for i in result.ingredients if i.resolved[n]}
        assumed = sum((v for k, v in resolved.items() if k in assumed_ids), Decimal(0))
        proxies = sum((v for k, v in resolved.items() if k in proxy_ids), Decimal(0))
        known = result.totals[n].known_subtotal
        contribution[n] = assumed
        share[n] = (assumed / known) if known > 0 else None
        proxy_share[n] = (proxies / known) if known > 0 else None
        if share[n] is not None:
            percent[n] = int(share[n] * 100)
    driven = any(v is not None and v > ASSUMPTION_SHARE_WARNING for v in share.values())
    flags = ["assumption_driven"] if driven else []
    if any(v is None for v in share.values()):
        flags.append("no_known_contribution_to_compare_with")
    return AdaptedScenario(bound=bound, calculation=result.model_dump(mode="json"), calculation_status=result.status,
                           completeness_by_nutrient={n: result.totals[n].complete for n in NUTRIENTS}, assumed_contribution=contribution,
                           assumed_share=share, assumed_share_percent=percent, assumption_driven=driven, proxy_share=proxy_share, flags=flags,
                           calculator_input=calculator_input or [], inferences=inferences, inferred_totals=inferred_totals)


def _internal_summary(mode: AdaptMode, published: list[Scenario], pairs: list[AdaptedPair]) -> InternalSummary:
    from collections import Counter
    by_gap, by_class, by_mat, by_row, unfilled = Counter(), Counter(), Counter(), Counter(), Counter()
    spreads = 0
    for p in pairs:
        for a in p.assumptions:
            if a.published_grams is not None or a.mass_only:       # a spread on a line the published scenario already weighed (median size), or a near-zero line's weight: not a blocked line
                spreads += 1
                continue
            by_gap[a.gap] += 1; by_class[a.display_class] += 1; by_mat[a.materiality_at_high] += 1; by_row[a.row_id or a.source] += 1
        for u in p.unfilled:
            unfilled[u.reason] += 1
    # published scenarios with no pair at all: their blockers are unfilled too, counted separately so the totals reconcile
    paired = {p.derived_from for p in pairs}
    in_pairs = sum(unfilled.values())
    for s in published:
        if s.scenario_id not in paired:
            for l in s.ingredients:
                if l.blocker:
                    unfilled["no_pair:" + l.blocker] += 1
    no_pair = sum(unfilled.values()) - in_pairs
    blocked = sum(1 for s in published for l in s.ingredients if l.blocker)
    assert blocked == sum(by_gap.values()) + in_pairs + no_pair, "filled + unfilled must equal the blocked lines"
    n_low = sum(1 for p in pairs if p.low.calculation_status == "complete")
    n_high = sum(1 for p in pairs if p.high.calculation_status == "complete")
    n_low_inf = sum(1 for p in pairs if p.low.inferred_totals and all(t.complete_with_inferences for t in p.low.inferred_totals.values()))
    n_high_inf = sum(1 for p in pairs if p.high.inferred_totals and all(t.complete_with_inferences for t in p.high.inferred_totals.values()))
    sat_only = sum(1 for p in pairs if p.high.completeness_by_nutrient.get("saturated_fat_g") and not p.high.completeness_by_nutrient.get("cholesterol_mg"))
    driven = sum(1 for p in pairs if p.low.assumption_driven or p.high.assumption_driven)

    def spread(bound: str) -> dict:
        out = {}
        for n in NUTRIENTS:
            vals = [Decimal(str(getattr(p, bound).calculation["per_serving"][n]["total"])) for p in pairs
                    if getattr(p, bound).calculation_status == "complete" and getattr(p, bound).calculation["per_serving"][n]["total"] is not None]
            out[n] = {"min": min(vals) if vals else None, "max": max(vals) if vals else None, "n": Decimal(len(vals))}
        return out
    statement = (f"INTERNAL ({mode}): {len(pairs)} of {len(published)} published scenarios could be adapted; of {blocked} blocked lines, "
                 f"{sum(by_gap.values())} filled by assumption, {in_pairs} left unfilled in pairs, {no_pair} in scenarios without a pair; "
                 f"complete for the modeled list: {n_low} at the low bound, {n_high} at the high bound; "
                 f"{driven} assumption-driven (> 30 % of a known subtotal); with documented inferences: {n_low_inf} / {n_high_inf} complete. "
                 f"Recipe serving basis; not restaurant totals; not for users.")
    return InternalSummary(mode=mode, n_published_calculated=len(published), n_pairs=len(pairs), n_lines_filled=sum(by_gap.values()),
                           filled_by_gap=dict(by_gap), filled_by_class=dict(by_class), filled_by_materiality=dict(by_mat), filled_by_row=dict(by_row),
                           n_unfilled=sum(unfilled.values()), n_unfilled_in_pairs=in_pairs, n_unfilled_no_pair=no_pair, n_blocked_lines=blocked,
                           unfilled_by_reason=dict(unfilled), n_complete_low=n_low, n_complete_high=n_high,
                           n_saturated_fat_only_complete_high=sat_only, n_assumption_driven=driven, between_recipe_low=spread("low"), between_recipe_high=spread("high"),
                           n_complete_low_with_inferences=n_low_inf, n_complete_high_with_inferences=n_high_inf, n_median_size_spreads=spreads, statement=statement)
