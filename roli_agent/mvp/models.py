"""Shapes of one menu run (Phase 3). Pydantic, extra forbidden, everything JSON-serialisable for the run store and the pages."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# evaluated: estimated (ranked or not); no_recipes: nothing calculable; error: the dish failed; excluded: not a dish Roli ranks (drink, dessert, side, option);
# skipped: a candidate left out by the cap or the budget before it started; budget_stopped: a spending limit stopped it part-way.
# "not_evaluated" is the Phase 3 name for excluded/skipped, kept so the saved runs of 2026-11-04 still load.
# 3D: flagged = the reference check found the estimate outside the published range (12.1.3), not ranked; usda_unavailable = USDA refused requests during
# the dish (12.5.2), not ranked.
DishStatus = Literal["evaluated", "no_recipes", "not_evaluated", "error", "excluded", "skipped", "budget_stopped", "flagged", "usda_unavailable"]
Support = Literal["well_supported", "tentative", "close_call", "only_estimate", "unranked"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MvpConfig(_Strict):
    experimental: bool = True                   # proposed portion rules, evidence-based weights rows, category defaults, nutrient facts 12.14.7, external bounds
    max_dishes: int = 30                        # dishes evaluated per menu; chosen across courses by lean words, not menu order (selection.py). 12.18 (Julius, 2026-11-07): 30, from 14
    exclude_herbs_spices: bool = True           # rule I03 (Julius, 2026-11-05): herbs and spices left out of the calculation, labelled
    survey_measures: bool = True                # D25 (Julius, 2026-11-05): a Survey record of the same food may lend a cup or spoon weight
    survey_fried_dishes: bool = True            # a fried dish gets one more interval from a USDA Survey fried-food record (recipes/survey.py)
    backfill_recipes: bool = True               # a recipe that cannot be portioned gives its place to the next eligible one
    # 3D (SPEC_3_mvp.md section 12, Julius 2026-11-05). Every value the spec marks as a proposal is a default here, not a constant.
    reuse_saved_reading: bool = False           # 12.10.5: evaluation reruns reuse the reader's saved answer for the same photo; a tester's run always reads it. 12.12.7: a page that failed in the saved pass stays failed
    save_judgements: bool = True                # 12.9.5: relevance grades and line tags saved and reused, keyed by page, menu item, prompt version and model
    dish_kind_model: bool = True                 # 12.16.11: one model call per menu sorts the items into card families. 12.18 (Julius, 2026-11-07): on; the word lists are the fallback, and every fallback is logged
    line_tags: bool = True                      # 12.3: one model call per dish tags every recipe line (eaten / cooking_medium / removed; plain_food / prepared_product)
    low_fat_g_per_100g: Decimal = Decimal("3")   # 12.16.2: fact 12.14.7(b) applies to a record with at most this much total fat per 100 g (EU "low fat" claim limit)
    negligible_sat_fat_per_100g: Decimal = Decimal("0.1")   # 12.4(b): a plain food at or under this (and 0 mg cholesterol) with a missing amount cannot move the result
    # 3K (SPEC_3_mvp.md 12.20, Julius's decisions of 2026-11-08): the band, the recipe weights, the top-up, the data-built assumed weights, the plate model, the fat prior
    band_draws: int = 2000                      # 12.20: simulated plates per dish and nutrient; the band is their 10th-90th percentile
    band_low_q: Decimal = Decimal("0.10")
    band_high_q: Decimal = Decimal("0.90")
    plate_samples_min: int = 10                 # fewer measured plate weights inside the approved range than this: draw uniformly over the range
    recipe_outlier_factor: Decimal = Decimal("5")   # with three or more recipes, one whose midpoint is this many times from the others' median is set aside
    grade_weight_medium: Decimal = Decimal("0.5")   # a medium-relevance recipe's draw weight against a high one's 1.0
    plate_weight_model: bool | None = None      # 12.20: the MenuStat plate-weight regression draws P2 plate weights; None = follow `live` in recipes/plate_model.json (set by scripts/plate_model.py's held-out result)
    frying_fat_prior: bool = True               # 12.20: recipes/frying_fat_prior.csv weights the survey fat choices (NEODA trade estimate); off = equal draws
    min_usable_recipes: int = 3                 # 12.20: below this many usable recipes after the first round, one top-up search runs
    extra_fetch: int = 6                        # pages fetched by the top-up
    max_topups_per_menu: int = 8                # top-ups a menu may spend (one search credit and two model calls each)
    assumed_weights_from_data: bool = True      # 12.20: assumed-weight ranges built from stored recipes replace the hand rows where enough recipes exist
    reference_check: bool = True                # 12.1: compare the middle of each range with the dish-family card's published figures; flag and leave out
    reference_check_factor: Decimal = Decimal("1.5")        # 12.1.2: flagged above published high x factor or below published low / factor
    reference_min_figures: int = 2              # 12.9.6: a published range may flag only when it rests on this many independent figures
    fried_sat_share_vegetable_max: Decimal = Decimal("0.20")   # 12.9.7: a fried dish's saturated share of total fat below this shows a liquid vegetable oil
    fried_sat_share_animal_min: Decimal = Decimal("0.35")      # 12.9.7: above this it shows beef dripping or palm
    usda_reserve_requests: int = 200            # 12.5.3: no dish starts when USDA's remaining hourly allowance is at or under this
    usda_store_dir: str | None = None           # 12.5.1: saved USDA answers on disk; None = roli/.cache/usda_store
    release_check: bool = True                  # 12.5.4: one request per refreshable table at app start and once a day
    menu_budget_usd: Decimal = Decimal("0.50")  # model calls per menu, the menu-reading call included; actual plus estimated spending
    menu_search_credits: int = 30               # Tavily credits per menu (2 per dish cold; 0 from the cache)
    daily_budget_usd: Decimal = Decimal("5.00") # model calls per local day across runs (spend ledger)
    daily_search_credits: int = 300
    dish_reserve_usd: Decimal = Decimal("0.03") # room a dish needs before it starts (a cold dish costs about $0.02 in model calls)
    dish_reserve_credits: int = 2
    workers: int = 3                            # dishes evaluated in parallel (the model's 20 requests per minute are the real ceiling)
    llm_per_minute: int = 16                    # shared across threads; OpenRouter allows 20 per minute per model on this account
    max_fetch: int = 12                         # recipe pages fetched per dish
    adapt_mode: str = "experimental"            # derived: "experimental" when experimental else "approved"
    banner: str = ("Experimental: modeled from published recipes with unapproved portion rules and assumed weights; "
                   "not the restaurant's figures.")


class DishRun(_Strict):
    key: str                                    # unique within the run (the menu name, de-duplicated)
    item: dict[str, Any]                        # name, description, section (MenuItem)
    menu_index: int
    status: DishStatus
    reason: str | None = None                   # why not evaluated / no recipes / the error text
    dish_type: str | None = None                # portion dish type (None = no rule)
    selection: dict[str, Any] = Field(default_factory=dict)      # decision, course, lean_score, matched words, rank, reason (selection.py)
    estimate: dict[str, Any] | None = None      # DishEstimate.model_dump(mode="json"), with the experimental pairs and portioned scenarios
    survey_dish: dict[str, Any] | None = None   # SurveyDishEstimate dump for a fried dish (2026-11-05), applicable or not
    reference: dict[str, Any] | None = None     # 3D: ReferenceCheck dump (card, both comparisons, flagged)
    intervals: dict[str, Any] = Field(default_factory=dict)      # nutrient -> DishInterval dump
    n_scenarios: int = 0
    n_portioned: int = 0
    seconds: float = 0.0
    cost: dict[str, Any] = Field(default_factory=dict)


class RankedDish(_Strict):
    rank: int
    key: str
    name: str
    saturated_fat_low: Decimal
    saturated_fat_high: Decimal
    saturated_fat_mid: Decimal | None = None     # (low + high) / 2: the ranking value since 2026-11-05; not a verified figure
    cholesterol_low: Decimal | None
    cholesterol_high: Decimal | None
    cholesterol_mid: Decimal | None = None
    tie_broken_by_cholesterol: bool = False
    support: Support
    beats_well_supported: int = 0
    beats_tentative: int = 0
    overlaps: int = 0
    overlaps_with: list[str] = Field(default_factory=list)       # names of ranked dishes below whose range this one overlaps
    tentative_vs: list[str] = Field(default_factory=list)
    cholesterol_driver: str | None = None       # one named ingredient that supplies most of the cholesterol upper end (bottarga), else None
    cholesterol_driver_share: Decimal | None = None
    reasons: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    fat_line: str | None = None                  # 12.10.9: the frying-fat sentence, when the dish's range spans the card's choices
    snack: bool = False                          # 12.14.4: a dish on the snack_bowl card: listed apart, never in the top three (kept for the saved runs; listed_apart == "snack" since 12.18)
    listed_apart: str | None = None              # 12.18: a dish of a non-main family (side, soup, dip, dessert, snack, kids): after the mains, never in the top three, one "Lightest ..." line per group
    # 3K (12.20): the band a tester reads ("most plates"); saturated_fat_low/high and cholesterol_low/high stay the extremes
    band_low: Decimal | None = None
    band_high: Decimal | None = None
    cholesterol_band_low: Decimal | None = None
    cholesterol_band_high: Decimal | None = None
    plate_source: str = ""
    set_aside: list[str] = Field(default_factory=list)


class Unranked(_Strict):
    key: str
    name: str
    reason: str
    fat_line: str | None = None                  # 12.10.9: the frying-fat sentence, when the dish's range spans the card's choices


class Feedback(_Strict):
    run_id: str
    dish: str | None = None
    kind: Literal["dish_inaccurate", "ranking_unexpected", "uncertainty_unhelpful", "other"]
    text: str = ""
    submitted_at: str


class MenuRun(_Strict):
    run_id: str
    created_at: str
    config: MvpConfig
    photo: str | None = None
    menu: dict[str, Any] | None = None          # the menu reader's answer (readable, problems, items)
    menu_error: str | None = None
    dish_kind_log: dict[str, Any] = Field(default_factory=dict)   # 12.16.11
    reading: str = ""                           # 12.10.5: "fresh" or "saved"
    dishes: list[DishRun] = Field(default_factory=list)
    comparison: dict[str, Any] | None = None    # DishComparison dump over the evaluated dishes
    ranking: list[RankedDish] = Field(default_factory=list)
    unranked: list[Unranked] = Field(default_factory=list)
    recommendation: str = ""
    recommendation_words: int = 0
    timings: dict[str, float] = Field(default_factory=dict)
    totals: dict[str, Any] = Field(default_factory=dict)         # credits, llm calls, llm cost, usda requests
    spend: dict[str, Any] = Field(default_factory=dict)          # MenuBudget.report(): actual and estimated model cost, credits, limits, interruptions
    errors: list[str] = Field(default_factory=list)
    status: Literal["running", "done", "failed"] = "running"
    progress: list[str] = Field(default_factory=list)
    flags: list[dict[str, Any]] = Field(default_factory=list)    # 3D: flags raised or closed by this run (also appended to runs/flags.jsonl)
    usda: dict[str, Any] = Field(default_factory=dict)           # 3D: requests this run, remaining allowance before/after, halted, store hits, the FoodData Central release used
