"""Data shapes for recipe ingestion. Pydantic, extra="forbid", Decimal quantities as in Phase 2A."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SearchMode = Literal["open", "structured_hosts"]
UnitKind = Literal["weight", "volume", "count", "none"]
PreparationHint = Literal["raw", "cooked", "as_used", "unknown"]
PreparationState = PreparationHint          # what the calculator is told; same vocabulary as spec 2A
ExtractionMethod = Literal["recipe_scrapers", "json_ld", "llm_text", "none"]
MatchType = Literal["direct", "proxy", "unresolved"]
RelevanceGrade = Literal["high", "medium", "low", "ungraded"]
Representativeness = Literal["high", "medium", "proxy_dependent", "low", "not_calculated"]
ScenarioStatus = Literal["rejected", "not_processed", "calculated", "invalid"]
ConversionMethod = Literal["weight_unit", "embedded_weight", "density_water_like", "usda_portion", "usda_portion_median", "none"]
BlockerCategory = Literal["menu_only", "seasoning_unknown_quantity", "optional_unknown_quantity", "unknown_quantity",
                          "no_usda_portion", "proxy_portion_refused", "unresolved_usda", "state_conflict", "preparation_unresolved", "usda_error", "nutrient_not_reported",
                          "cooking_medium_unknown_amount"]   # 3D (12.3.2): a bath, marinade or brine whose eaten share is unknown; never counted at its recipe weight


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MenuItem(_Strict):
    name: str
    description: str = ""          # the printed ingredient words, e.g. "bottarga, muscat grape, chive"
    section: str = ""
    restaurant: str = ""


class SearchHit(_Strict):
    url: str
    canonical_url: str
    title: str = ""
    host: str
    found_by: list[SearchMode]     # which search mode(s) returned it (D12)
    ranks: dict[SearchMode, int]   # 1-based rank within each mode's result list
    snippet: str = ""


class FetchOutcome(_Strict):
    url: str
    status: Literal["ok", "robots_disallowed", "http_error", "rate_limited", "network_error", "too_large", "not_html", "host_refused"]
    http_status: int | None = None
    from_cache: bool = False
    seconds: float | None = None
    detail: str = ""


class ParsedIngredient(_Strict):
    line: str                                  # verbatim, as the page had it
    quantity_text: str | None = None           # "2", "1/2", "1½", "1-2", "to taste"
    quantity: Decimal | None = None            # parsed; None = unknown
    quantity_low: Decimal | None = None        # set when a range was given (D3)
    quantity_high: Decimal | None = None
    unit_raw: str | None = None                # "tablespoons"
    unit: str | None = None                    # normalised: g, kg, oz, lb, ml, l, tsp, tbsp, cup, fl_oz, piece, clove, slice, large, medium, small, pinch, ...
    unit_kind: UnitKind = "none"
    name: str                                  # the food words, lower-cased
    preparation_words: list[str] = Field(default_factory=list)
    preparation_hint: PreparationHint = "unknown"
    optional: bool = False
    grams: Decimal | None = None               # only for explicit weight units (and the liquid density rule); else None
    grams_reference: str | None = None         # "1 oz = 28.349523125 g (NIST)" or "density 1.0 g/ml assumed (water-like liquid)"
    flags: list[str] = Field(default_factory=list)   # range_midpoint, vague_quantity, conversion_pending_usda_portion, density_assumed_1, ...
    portion_options: list[dict[str, str]] = Field(default_factory=list)   # 2C.1: the USDA labels a `portion_ambiguous` line could not choose between (label, grams)


class SourceRecipe(_Strict):
    url: str
    canonical_url: str
    host: str
    title: str = ""
    found_by: list[SearchMode]
    fetched_at: str
    extraction: ExtractionMethod
    yield_text: str = ""                        # verbatim
    servings: Decimal | None = None             # parsed; None = unknown or not a serving count
    servings_note: str = ""
    servings_low: Decimal | None = None
    servings_high: Decimal | None = None
    ingredient_lines: list[str]                 # verbatim
    instructions_text: str = ""                 # verbatim instructions (kept in memory for state hints; not written to fixtures)
    cooking_verbs: list[str] = Field(default_factory=list)   # deterministic hints from the instructions
    ingredients: list[ParsedIngredient]
    content_hash: str                           # hash of normalised ingredient lines, for content dedup
    duplicate_of: str | None = None             # canonical_url of the record this one duplicates by content
    flags: list[str] = Field(default_factory=list)
    yield_source: Literal["structured", "page_text", "none"] = "none"   # D15: where the yield text came from

    # -- usability measures (requirement 6) --
    @property
    def n_lines(self) -> int:
        return len(self.ingredients)

    @property
    def n_quantified(self) -> int:
        """Lines with a parsed numeric quantity and a recognised unit (or an explicit count)."""
        return sum(1 for i in self.ingredients if i.quantity is not None and i.unit_kind != "none")

    @property
    def n_grams_known(self) -> int:
        return sum(1 for i in self.ingredients if i.grams is not None)


class IngestionStats(_Strict):
    searches: int
    search_credits: int
    hits_open: int
    hits_structured: int
    hits_after_url_dedup: int
    hits_in_both_modes: int
    blocked_hosts_skipped: int
    fetched: int
    fetch_ok: int
    fetch_from_cache: int
    robots_disallowed: int
    rate_limited: int
    http_errors: int
    refused_hosts_skipped: int = 0              # D17: hosts that refused scripted access twice recently are not asked again
    extracted: int                              # recipes with at least one ingredient line
    extracted_by: dict[str, int]
    extracted_from_cache: int = 0               # pages whose extraction came from the extraction cache (no LLM fallback run)
    content_duplicates: int
    distinct_recipes: int
    with_servings: int
    pct_lines_quantified: float                 # over distinct recipes
    pct_lines_grams_known: float
    recipes_with_all_lines_quantified: int
    seconds: float


class IngestionResult(_Strict):
    menu_item: MenuItem
    queries: dict[SearchMode, str]
    hits: list[SearchHit]
    fetches: list[FetchOutcome]
    recipes: list[SourceRecipe]                 # distinct recipes (content duplicates are kept but marked)
    stats: IngestionStats
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 2B-2: matching, conversion, relevance, scenarios, the dish estimate
# ---------------------------------------------------------------------------


class MatchDecision(_Strict):
    """One ingredient name -> one USDA record (or none). FDC IDs only ever come from USDA's own candidate list."""
    name: str                                   # normalised ingredient name (cache key part 1)
    preparation_hint: PreparationHint           # cache key part 2 (D7)
    query: str | None = None                    # the USDA-style search words used
    fdc_id: int | None = None
    description: str | None = None
    data_type: str | None = None
    record_state: Literal["raw", "cooked", "unknown"] | None = None
    match_type: MatchType = "unresolved"
    reason: str = ""                            # the LLM's sentence; trace and provenance only, never the user reply
    source: Literal["llm", "cache", "none", "d22", "d24"] = "none"
    candidates_seen: int = 0
    candidates: list[dict[str, Any]] = Field(default_factory=list)   # USDA's own list for this search (fdc_id, description, data_type): D22 may only choose from it
    substituted_for: int | None = None          # D22: the model's original choice, replaced by an equivalent record with usable measures
    retried_with_plain_name: bool = False       # the model's query returned no candidates; one retry with the plain ingredient name supplied them
    saturated_fat_delta_per_100g: Decimal | None = None   # D24 (proposed): replacement minus original saturated fat per 100 g, when both report it
    issue: str | None = None                    # no_candidates, llm_declined, guard_rejected, state_conflict, usda_error:<code>, selection_missing
    category_fallback: str = ""                 # 3K (12.20): the zero-fat category whose fixed record stood in when the line matched nothing (wine_or_spirit, beer, salt, water_or_stock)


class Conversion(_Strict):
    from_text: str                              # "2 tbsp", "1 (14 oz) can", "4 each"
    grams: Decimal | None
    method: ConversionMethod
    reference: str | None = None                # the factor and where it comes from
    flags: list[str] = Field(default_factory=list)


class ScenarioIngredient(_Strict):
    """A line as it enters the calculator, with everything that was done to it."""
    ingredient_id: str
    origin: Literal["recipe", "menu_only", "method_fat"]   # method_fat (Phase 3): the recipe fries but lists no fat; an open line, never a quantity
    line: str | None                            # verbatim page line; None for menu-only lines (D8)
    name: str
    parsed: ParsedIngredient | None = None
    match: MatchDecision | None = None
    conversion: Conversion
    preparation_state: PreparationState         # what the calculator was told
    state_reason: str = ""
    assumption: str | None = None
    blocker: BlockerCategory | None = None      # why this line cannot be fully calculated (measurement, D5)
    excluded_from_calculation: str | None = None   # 2C.1: a line that is not an ingredient (a sub-recipe reference whose components are listed); never sent to the calculator
    flags: list[str] = Field(default_factory=list)
    # 3D (12.3): the line tags, validated by code; "" when the tag call failed and the text patterns were used instead
    mass_gap: str | None = None                 # 12.14.12: a near-zero line with a stated amount and no USDA weight: why it is unweighed; the pair still looks for its weight
    tag_role: str = ""                          # eaten | cooking_medium | removed
    tag_kind: str = ""                          # plain_food | prepared_product
    tag_category: str = ""                      # 3K (12.20): the food category the tag call named (tags.CATEGORIES)
    tag_reason: str = ""                        # the model's words, provenance only
    tag_note: str = ""                          # why code overrode the model


class Relevance(_Strict):
    menu_coverage: Decimal | None = None        # matched / listed menu ingredients; None when the menu lists none
    menu_matched: list[str] = Field(default_factory=list)
    menu_missing: list[str] = Field(default_factory=list)
    gate: Literal["passed", "rejected", "not_run"] = "not_run"
    gate_reason: str | None = None
    dish_type: Literal["same", "variant", "different"] | None = None
    preparation: Literal["same", "similar", "different"] | None = None
    course_portion: Literal["same", "different"] | None = None
    rubric_reason: str = ""                     # LLM sentence, trace/provenance only
    grade: RelevanceGrade = "ungraded"
    hard_exclusion: str | None = None           # D10


class ScenarioSource(_Strict):
    url: str
    canonical_url: str
    host: str
    title: str
    found_by: list[SearchMode]
    extraction: ExtractionMethod
    yield_text: str
    yield_source: str
    servings: Decimal | None
    servings_note: str
    n_lines: int
    flags: list[str]


class Scenario(_Strict):
    scenario_id: str                            # distinct name for the comparison
    source: ScenarioSource
    relevance: Relevance
    status: ScenarioStatus
    status_reason: str | None = None
    ingredients: list[ScenarioIngredient] = Field(default_factory=list)
    match_counts: dict[str, int] = Field(default_factory=dict)          # direct / proxy / unresolved over recipe lines
    proxies: list[str] = Field(default_factory=list)                    # "pecorino sardo -> Cheese, romano (171249)"
    calculation: dict[str, Any] | None = None   # Phase 2A RecipeResult.model_dump(mode="json"), unchanged
    calculation_status: Literal["complete", "incomplete", "invalid"] | None = None
    blockers: dict[str, int] = Field(default_factory=dict)              # category -> number of excluded lines
    complete_except_seasonings: bool = False    # D5 measurement
    complete_except_menu_only: bool = False
    complete_except_seasonings_and_menu_only: bool = False
    proxy_contribution: dict[str, Decimal] = Field(default_factory=dict)   # D18: absolute contribution of proxy lines per nutrient
    proxy_share: dict[str, Decimal | None] = Field(default_factory=dict)   # share of each nutrient's KNOWN SUBTOTAL from proxy lines (not of the unknown true total)
    proxy_share_percent: dict[str, int] = Field(default_factory=dict)       # rounded down, for the reply
    proxy_share_basis: str = "known_subtotal"
    largest_contributor_is_proxy: dict[str, bool] = Field(default_factory=dict)
    representativeness: Representativeness = "not_calculated"
    eligible_for_range: bool = False
    ineligible_reason: str | None = None
    completeness_by_nutrient: dict[str, bool] = Field(default_factory=dict)   # D23 measurement: saturated fat may be complete while cholesterol is not
    flags: list[str] = Field(default_factory=list)
    # Phase 2D (2026-11-03): documented inferences beside the source-reported calculation. `calculation` is still the unchanged Phase 2A
    # result; `inferred_totals` is a separate Python layer that says what the totals would be if the listed inferences are accepted.
    basis: Literal["source_reported", "documented_inferences"] = "source_reported"
    inferences: list["Inference"] = Field(default_factory=list)
    inferred_totals: dict[str, "InferredTotal"] = Field(default_factory=dict)
    completeness_basis: dict[str, str] = Field(default_factory=dict)        # per nutrient: complete_source_reported | complete_with_inferences | incomplete


# ---------------------------------------------------------------------------
# Phase 2D: documented inferences (D20 revised: assumed median sizes; narrow zero-nutrient inferences)
# ---------------------------------------------------------------------------

InferenceKind = Literal["assumed_size_median", "inferred_zero_nutrient", "excluded_negligible", "excluded_not_eaten", "class_level_cup_weight", "saturated_fat_ceiling"]   # excluded_not_eaten: 3D line tags (removed; a near-zero medium); class_level_cup_weight: 12.12.4


class Inference(_Strict):
    """One documented inference. Never changes a USDA record or the Phase 2A arithmetic; it is reported beside them."""
    kind: InferenceKind
    rule_id: str | None = None                  # I01 olive-oil cholesterol zero, ...
    ingredient_id: str
    name: str
    nutrient: str | None = None                 # inferred_zero_nutrient only
    value_per_100g: Decimal | None = None       # the inferred per-100 g value (0 for a zero inference); None for a size assumption
    grams: Decimal | None = None                # the line's grams in the recipe (the median weight for a size assumption)
    contribution: Decimal | None = None         # grams x value / 100, whole recipe; 0 for a zero inference
    detail: str                                 # what was absent and what was assumed, in words
    reference: str                              # the evidence
    review_status: str


class InferredTotal(_Strict):
    """A nutrient's whole-recipe total when the documented inferences are accepted. `source_complete` is the Phase 2A verdict."""
    nutrient: str
    source_complete: bool
    complete_with_inferences: bool
    known_subtotal: Decimal                     # Phase 2A known subtotal, unchanged
    inferred_contribution: Decimal              # sum of inferred contributions (0 for zero inferences)
    total: Decimal | None                       # known_subtotal + inferred_contribution when complete_with_inferences, else None
    per_serving_total: Decimal | None = None    # total / servings, quantised like Phase 2A
    inferred_lines: list[str] = Field(default_factory=list)
    remaining_excludes: list[str] = Field(default_factory=list)   # "name (reason)" of lines still unknown
    remaining_ids: list[str] = Field(default_factory=list)        # their ingredient ids, in the same order


# ---------------------------------------------------------------------------
# Phase 2C: menu-adapted scenarios (internal only)
# ---------------------------------------------------------------------------

Gap = Literal["G1_menu_only", "G2_unquantified", "G3_size_unspecified", "G4_proxy_count", "G5_measure_ambiguous", "G6_cooking_medium"]   # G6 (3D): the clinging share of a medium, from a per-plate row
DisplayClass = Literal["zero_nutrient", "low_impact", "displayable", "nutrient_missing"]
Materiality = Literal["negligible", "minor", "moderate", "major", "unknown"]
AdaptMode = Literal["off", "approved", "experimental"]


class Assumption(_Strict):
    ingredient_id: str
    name: str
    gap: Gap
    source: Literal["table_row", "record_size_labels", "record_measure_labels", "zero_nutrient_nominal"]
    row_id: str | None = None
    amount_basis: Literal["total_recipe", "per_plate", "per_count_unit"] = "total_recipe"   # 2D: how the assumed grams enter the calculator
    mass_only: bool = False                     # 12.14.12: the row weighs a near-zero line for the plate weight; the line held nothing up
    published_grams: Decimal | None = None      # 2D: the median weight the published scenario used (assumed_size_median lines), else None
    fdc_id: int
    description: str
    grams_declared: Decimal | None = None       # what the recipe said: always None for an assumed line
    grams_low: Decimal
    grams_high: Decimal
    basis: str                                  # where the bounds come from
    review_status: str
    display_class: DisplayClass                 # computed from the record and grams_high
    materiality_at_high: Materiality            # computed, absolute
    contribution_low: dict[str, Decimal | None] = Field(default_factory=dict)
    contribution_high: dict[str, Decimal | None] = Field(default_factory=dict)
    composition_proxy: bool = False             # the record stands in for a different food
    note: str = ""


class Unfilled(_Strict):
    ingredient_id: str
    name: str
    reason: str                                 # no_table_row, blocked_row, row_unapproved, nutrient_missing_on_record, ambiguous_or_missing_measure, no_usda_record, ...


class AdaptedScenario(_Strict):
    bound: Literal["low", "high"]
    calculation: dict[str, Any]                 # Phase 2A RecipeResult.model_dump(mode="json") of the modeled list; arithmetic unchanged
    calculation_status: Literal["complete", "incomplete", "invalid"]
    completeness_by_nutrient: dict[str, bool] = Field(default_factory=dict)
    assumed_contribution: dict[str, Decimal] = Field(default_factory=dict)      # absolute, per nutrient, whole recipe
    assumed_share: dict[str, Decimal | None] = Field(default_factory=dict)      # of the KNOWN SUBTOTAL; None when that subtotal is 0
    assumed_share_percent: dict[str, int] = Field(default_factory=dict)
    assumption_driven: bool = False             # any share > 30 %: a warning, never a discard
    proxy_share: dict[str, Decimal | None] = Field(default_factory=dict)       # composition proxies (published lines and proxy-based rows)
    flags: list[str] = Field(default_factory=list)
    calculator_input: list[dict[str, Any]] = Field(default_factory=list)       # 2D: the modeled line list as given to the calculator, so a portion model can re-run it
    inferences: list[Inference] = Field(default_factory=list)                  # 2D: the inference layer on this bound
    inferred_totals: dict[str, InferredTotal] = Field(default_factory=dict)


class AdaptedPair(_Strict):
    pair_id: str
    derived_from: str                           # the published scenario_id; the published object is never modified
    mode: AdaptMode
    scenario_kind: Literal["menu_adapted_pair"] = "menu_adapted_pair"
    servings: Decimal
    servings_basis: Literal["recipe"] = "recipe"
    representativeness: Literal["assumed"] = "assumed"
    assumptions: list[Assumption]
    unfilled: list[Unfilled]
    low: AdaptedScenario
    high: AdaptedScenario
    sensitivity_per_serving: dict[str, Decimal | None] = Field(default_factory=dict)   # high minus low known subtotal, recipe basis
    sensitivity_total: dict[str, Decimal | None] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    note: str = "complete for the modeled ingredient list where stated; not a verified restaurant total; per-serving values are on the recipe's own serving count"


class InternalSummary(_Strict):
    mode: AdaptMode
    n_published_calculated: int
    n_pairs: int
    n_lines_filled: int
    filled_by_gap: dict[str, int] = Field(default_factory=dict)
    filled_by_class: dict[str, int] = Field(default_factory=dict)
    filled_by_materiality: dict[str, int] = Field(default_factory=dict)
    filled_by_row: dict[str, int] = Field(default_factory=dict)
    n_unfilled: int                             # = n_unfilled_in_pairs + n_unfilled_no_pair
    n_unfilled_in_pairs: int = 0
    n_unfilled_no_pair: int = 0                 # blocked lines of published scenarios for which no pair could be built
    n_blocked_lines: int = 0                    # = n_lines_filled + n_unfilled (the denominator every count adds up to)
    unfilled_by_reason: dict[str, int] = Field(default_factory=dict)
    n_complete_low: int
    n_complete_high: int
    n_saturated_fat_only_complete_high: int     # D23 measurement: saturated fat complete, cholesterol not
    n_complete_low_with_inferences: int = 0     # 2D: complete once the documented inferences (I01 olive-oil cholesterol) are accepted
    n_complete_high_with_inferences: int = 0
    n_median_size_spreads: int = 0              # 2D: pair assumptions that only spread a median-weighed published line (not blocked lines)
    n_assumption_driven: int
    between_recipe_low: dict[str, dict[str, Decimal | None]] = Field(default_factory=dict)   # per nutrient: min/max per-serving over complete low scenarios
    between_recipe_high: dict[str, dict[str, Decimal | None]] = Field(default_factory=dict)
    statement: str                              # internal wording only; never shown to a user


class DishCosts(_Strict):
    stage_seconds: dict[str, float] = Field(default_factory=dict)
    llm_calls: int = 0
    llm_calls_by_stage: dict[str, int] = Field(default_factory=dict)
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_cost_usd: Decimal | None = None         # from the provider's usage report; None = not reported
    llm_failures: int = 0
    usda_searches: int = 0                      # service calls
    usda_lookups: int = 0
    usda_portion_lookups: int = 0
    usda_http_requests: int | None = None       # HTTP requests actually sent (None when not measured)
    match_cache_hits: int = 0
    search_credits: int = 0
    pages_fetched: int = 0
    pages_from_cache: int = 0
    seconds: float = 0.0


class DishSummary(_Strict):
    n_hits: int
    n_fetched: int
    n_extracted: int
    n_distinct: int
    n_gate_passed: int
    n_relevant: int                              # grade high or medium
    n_processed: int                             # matched, converted and calculated
    n_calculated: int
    n_complete: int
    n_eligible: int
    n_saturated_fat_only_complete: int = 0     # D23 measurement on published scenarios
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    blocked_only_by_seasonings: int = 0          # D5 measurement
    blocked_only_by_menu_only: int = 0
    blocked_only_by_seasonings_and_menu_only: int = 0
    range_meaningful: bool = False
    statement: str                               # Python template; the only text shown to a user
    flags: list[str] = Field(default_factory=list)


class DishEstimate(_Strict):
    menu_item: MenuItem
    queries: dict[SearchMode, str]
    ingestion: IngestionStats
    scenarios: list[Scenario]
    comparison: dict[str, Any] | None = None     # Phase 2A ComparisonResult.model_dump(mode="json") over eligible scenarios
    summary: DishSummary
    cost: DishCosts
    notes: list[str] = Field(default_factory=list)
    # Phase 2C, internal only: never read by the reply template
    adapt_mode: AdaptMode = "off"
    adapted_pairs: list[AdaptedPair] = Field(default_factory=list)
    internal_summary: InternalSummary | None = None
    portioned: list["PortionedScenario"] = Field(default_factory=list)   # Phase 2D, internal only: restaurant-portion models of the scenarios and pairs
    topup: dict[str, Any] = Field(default_factory=dict)                  # 3K (12.20): the second search when too few recipes were usable: query, hits, new recipes, usable before/after


# ---------------------------------------------------------------------------
# Phase 2D: restaurant portion models (internal only; SPEC_2D_restaurant_portions.md)
# ---------------------------------------------------------------------------

PortionModel = Literal["P1", "P2", "P3"]
PortionConfidence = Literal["portion_published", "portion_reviewed", "portion_proposed"]


class PortionFraction(_Strict):
    bound: Literal["low", "high"]
    fraction: Decimal                           # f: the share of the whole recipe on one restaurant plate
    arithmetic: str                             # "K / K_recipe = 113 g / 680.388555 g", "units_per_portion x area_ratio / k", "W / M_served"
    inputs: dict[str, str] = Field(default_factory=dict)


class PortionedBound(_Strict):
    input_bound: Literal["published", "low", "high"]
    fraction: Decimal
    servings_for_calculator: Decimal            # 1 / f, the serving count the unchanged Phase 2A calculator was re-run with
    calculation: dict[str, Any]                 # Phase 2A RecipeResult.model_dump(mode="json"); per_serving = per restaurant portion
    calculation_status: Literal["complete", "incomplete", "invalid"]
    completeness_by_nutrient: dict[str, bool] = Field(default_factory=dict)
    inferences: list[Inference] = Field(default_factory=list)
    inferred_totals: dict[str, InferredTotal] = Field(default_factory=dict)
    per_portion: dict[str, dict[str, Decimal | None]] = Field(default_factory=dict)   # nutrient -> known_subtotal, total (source), total_with_inferences


class PortionedScenario(_Strict):
    derived_from: str                           # scenario_id (published) or pair_id
    input_kind: Literal["published", "adapted_pair"]
    adapt_mode: AdaptMode = "off"
    servings_basis: Literal["restaurant_model"] = "restaurant_model"
    dish_type: str
    model: PortionModel
    portion_rule_id: str | None = None
    rule_basis: str = ""
    review_status: str = ""
    confidence: PortionConfidence = "portion_proposed"
    applicable: bool
    not_applicable_reason: str | None = None
    fraction_low: PortionFraction | None = None
    fraction_high: PortionFraction | None = None
    low: PortionedBound | None = None
    high: PortionedBound | None = None
    recipe_basis: dict[str, Any] = Field(default_factory=dict)      # the input's serving count and per-serving figures, untouched
    limitations: list[str] = Field(default_factory=list)
    uncertainty: dict[str, Any] = Field(default_factory=dict)      # fraction_ratio, per-portion spread per nutrient
    note: str = "modeled restaurant portion; not a verified restaurant serving; the recipe-basis figures stay reported beside it; internal only"


# ---------------------------------------------------------------------------
# Phase 2D: internal dish comparison prototype
# ---------------------------------------------------------------------------

EvidenceTier = Literal["source_complete", "complete_with_inferences", "modeled_range_complete", "modeled_range_external_bound", "lower_bound_only", "survey_dish_record"]
Verdict = Literal["well_supported", "tentative", "overlapping", "insufficient_evidence"]


class SamplingInputs(_Strict):
    """3K (SPEC_3_mvp.md 12.20): what the band sampler needs to re-form one scenario's per-plate value at any plate weight and any position between the
    adapted pair's two bounds, without calling the calculator again. Per portion at a bound: V = f x R + P, where R is the whole-recipe total of the
    lines the recipe states (`quantity_basis` total_recipe, inferences included) and P the per-plate total (menu-only lines, per-plate weights rows, the
    clinging medium), which the calculator counts once per plate (`roli_nutrition.recipe.calculator`: a per_serving line's grams x servings). Both are
    read from the saved Phase 2A calculations; nothing here is a new figure."""
    kind: Literal["recipe", "survey"] = "recipe"
    model: PortionModel | None = None
    rule_id: str | None = None
    recipe_total_low: Decimal = Decimal(0)      # R at the pair's low bound (whole recipe)
    recipe_total_high: Decimal = Decimal(0)
    per_plate_low: Decimal = Decimal(0)         # P at the low bound (per plate)
    per_plate_high: Decimal = Decimal(0)
    fraction_low: Decimal | None = None         # f at each bound, as the portion model set it
    fraction_high: Decimal | None = None
    plate_low_g: Decimal | None = None          # P2: W at each bound (the rule's plate weight)
    plate_high_g: Decimal | None = None
    served_mass_low: Decimal | None = None      # P2: M_served at each bound (the recipe's mass, assumed lines included)
    served_mass_high: Decimal | None = None
    key_plate_low_g: Decimal | None = None      # P3: K_plate at each bound (the rule's raw key weight)
    key_plate_high_g: Decimal | None = None
    key_recipe_low_g: Decimal | None = None     # P3: K_recipe at each bound
    key_recipe_high_g: Decimal | None = None
    dough_ball_low_g: Decimal | None = None     # P1: the rule's dough ball at each bound
    dough_ball_high_g: Decimal | None = None
    recipe_dough_g: Decimal | None = None       # P1: the recipe's dough (None when the page's unit count set f)
    external_bound: Decimal = Decimal(0)        # added at the top of the range from non-USDA evidence (per portion, at fraction_high)
    choice_ranges: dict[str, dict[str, Decimal]] = Field(default_factory=dict)   # survey: {fat label: {"low", "high"}} per plate for this nutrient


class ScenarioInterval(_Strict):
    scenario_id: str
    nutrient: str
    tier: EvidenceTier
    low: Decimal                                # per restaurant portion
    high: Decimal | None                        # None = no defensible upper bound
    portion_model: PortionModel | None = None
    fraction_low: Decimal | None = None
    fraction_high: Decimal | None = None
    unbounded_lines: list[str] = Field(default_factory=list)
    external_bound: Decimal | None = None       # added to `high` from non-USDA evidence; never inside a total
    external_bound_sources: list[str] = Field(default_factory=list)
    assumption_driven: bool = False             # the pair behind this interval has assumed lines above 30 % of a known subtotal
    drivers: list[str] = Field(default_factory=list)
    served_mass_low: Decimal | None = None      # 3D (12.1): grams on the plate at each bound when the portion model knows them (P2: the rule's W; Survey: the components)
    served_mass_high: Decimal | None = None
    sampling: SamplingInputs | None = None      # 3K: what the band sampler needs (None on intervals saved before 3K)


class DishInterval(_Strict):
    dish: str
    nutrient: str
    low: Decimal | None
    high: Decimal | None
    high_without_external: Decimal | None = None   # the upper bound with every external-evidence bound removed (None when then unbounded)
    bound_assumption_driven: bool = False       # Phase 3: the scenario that sets `high` has assumed lines above 30 % of its known subtotal
    bounded: bool
    n_scenarios: int
    n_bounded: int
    scenarios: list[ScenarioInterval] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    # 3K (12.20): the middle band of simulated plates. `low`/`high` stay the extremes (the lowest low and the highest high over every bounded recipe);
    # the band is the 10th-90th percentile of draws over plate weight x recipe x assumed-amount position, the headline a tester reads.
    band_low: Decimal | None = None
    band_mid: Decimal | None = None
    band_high: Decimal | None = None
    band_draws: int = 0
    band_method: str = ""                       # how the band was formed, in words (draws, quantiles, plate source)
    plate_source: str = ""                      # samples:<n> | model | uniform | mixed, where the plate weights came from
    recipe_weights: dict[str, Decimal] = Field(default_factory=dict)   # scenario_id -> draw weight (relevance grade x menu coverage)
    set_aside: list[str] = Field(default_factory=list)                 # scenario ids left out of the draws as outliers (still in the extremes)
    fat_bands: dict[str, dict[str, Decimal]] = Field(default_factory=dict)   # survey fats: {label: {"low", "mid", "high"}} per-fat bands


class PairwiseComparison(_Strict):
    dish_a: str
    dish_b: str
    nutrient: str
    verdict: Verdict
    lower: str | None = None                    # which dish is lower, when the intervals are disjoint (well_supported or tentative)
    margin: Decimal | None = None               # disjoint intervals: the gap between the lower dish's upper bound and the other's lower bound
    tentative_because: list[str] = Field(default_factory=list)   # why a disjoint pair is only tentative: narrow margin, external bounds decide, ...
    reason: str
    caveats: list[str] = Field(default_factory=list)


class DishComparison(_Strict):
    nutrient_priority: list[str] = Field(default_factory=lambda: ["saturated_fat_g", "cholesterol_mg"])
    intervals: dict[str, dict[str, DishInterval]] = Field(default_factory=dict)      # nutrient -> dish -> interval
    pairwise: list[PairwiseComparison] = Field(default_factory=list)
    ordering: list[str] = Field(default_factory=list)                                # dishes from lowest saturated fat, where decided
    ordering_note: str = ""
    statement: str = ""                                                              # internal wording; never shown to a user
    flags: list[str] = Field(default_factory=list)
