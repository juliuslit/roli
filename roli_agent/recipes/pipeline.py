"""Phase 2B-2 orchestration: menu item -> DishEstimate (spec 2B sections 6-12).

    ingest (2B-1) -> gate -> coverage -> rubric (1 LLM call) -> choose scenarios -> match USDA (batched 1E path)
    -> resolve preparation state -> convert volumes/counts with USDA portions -> append menu-only lines (D8)
    -> Phase 2A calculator, unchanged -> representativeness and eligibility -> Phase 2A comparison -> statement

Python owns every number and every decision about what may be said. The LLM grades relevance, writes USDA
queries and picks records from USDA's own candidate lists; nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

import re
from decimal import Decimal
from typing import Any, Callable

from roli_nutrition import ErrorResult
from roli_nutrition.recipe import RecipeCalculator, RecipeInput, RecipeResult, compare_scenarios
from roli_nutrition.recipe.calculator import display_amount

from ..llm import parse_json_object as _default_parse
from .convert import convert_with_portions
from .completeness import CompleteRecordPolicy
from .equivalence import EquivalentRecordPolicy
from .fetch import PoliteFetcher
from .extract import ExtractionCache
from .inference import (HERB_SPICE_REASON, LOW_FAT_G_PER_100G, MEDIUM_NEGLIGIBLE_REASON, NEGLIGIBLE_COMPOSITION_REASON, REMOVED_REASON, ZERO_WEIGHT_WORDS, NutrientFacts, apply_inference_layer, completeness_basis, near_zero,
                        composition_inference, herb_spice_inference, is_herb_or_spice, not_eaten_inference)
from .ingest import topup_query, COOKING_VERBS, ingest_dish
from .match import MatchCache, MatchRequest, UsdaMatcher
from .metrics import Meter, MeteredLLM, MeteredService
from .models import (BlockerCategory, Conversion, DishCosts, DishEstimate, DishSummary, IngestionResult, MatchDecision, MenuItem,
                     ParsedIngredient, Relevance, Scenario, ScenarioIngredient, ScenarioSource, SourceRecipe)
from .relevance import gate, grade_batch, menu_coverage
from .search import RecipeSource
from .tags import LineTags, menu_word_tag, tag_lines, validate_tag

MAX_SCENARIOS = 4


@dataclass
class TopUp:
    """3K (12.20): the second search for a dish that ended on too few usable recipes. `allowed` is asked once, right before the search (the menu's spending room and
    top-up count); `used` is told once a top-up ran."""
    min_usable: int = 3
    extra_fetch: int = 6
    allowed: Callable[[], bool] = lambda: True
    used: Callable[[], None] = lambda: None
BACKFILL_ROUNDS = 1                     # replacement rounds after the first batch (2026-11-05); each round tries up to MAX_SCENARIOS more recipes
PROXY_SHARE_LIMIT = Decimal("0.5")      # D18 (proposed): above this share of a nutrient, a scenario depends on substitutes and leaves the range
MENU_ONLY_ASSUMPTION = "listed on the menu, not in this recipe; quantity unknown"
FRIED_WORDS = re.compile(r"\b(deep[- ]?fr(?:y|ied|ying)|shallow[- ]?fr(?:y|ied|ying)|pan[- ]?fr(?:y|ied|ying)|fr(?:y|ied|ying)|fritto|fritti|fritters?|tempura|battered|crumbed|breaded|crispy|crisp(?:ed)?|"
                         r"schnitzel|katsu|croquettes?|arancini|frites|fries|chips|crackling)\b", re.I)
FRYING_BATH_MIN_G = Decimal(100)        # a frying recipe that lists this much oil or more lists the bath, not what is eaten ("1 1/2 - 2 cups vegetable oil" for one potato)
FRYING_FAT_LINE = re.compile(r"\b(for|to)\s+(?:deep[- ]|shallow[- ]|pan[- ])?fry(?:ing)?\b|\bfor the fryer\b|\bfrying oil\b|\bdeep[- ]fry(?:ing)?\b", re.I)
FAT_RECORD_HEAD = re.compile(r"^(oil|butter|lard|shortening|fat|margarine|margarine-like|ghee|tallow|schmaltz|animal fat|cream)\b", re.I)
NOT_VERIFIED = "Not a verified value for the restaurant's dish."
NO_VALUES = "No nutrition values are given; Roli does not estimate them from other sources."

# Measurement only (D5): ingredients whose unknown quantity is the classic "to taste" seasoning. Nothing here changes grams.
SEASONING = re.compile(r"\b(salt|pepper|peppercorns?|chil(?:i|e|li)\s+flakes|red pepper flakes|flakes|oregano|thyme|rosemary|bay lea(?:f|ves)|"
                       r"cumin|paprika|turmeric|coriander|nutmeg|cinnamon|allspice|spices?|seasoning|zest|water|vinegar|lemon juice|lime juice|"
                       r"sugar|honey|garlic|herbs?)\b", re.I)
FLESH = re.compile(r"\b(fish|salmon|tuna|bass|cod|halibut|trout|shrimp|prawns?|scallops?|anchov\w*|sardines?|mackerel|chicken|beef|pork|lamb|duck|"
                   r"veal|bacon|pancetta|guanciale|prosciutto|eggs?|squid|octopus|crab|lobster|clams?|mussels?|steak|fillets?)\b", re.I)
# A name that ends in one of these is a product made from the animal, not its flesh: "chicken stock", "fish sauce", "duck fat" (2D, 2026-11-03;
# found on the frozen inputs: "1/3 cup chicken stock" was treated as a flesh food of unknown state and excluded as preparation_unresolved).
NON_FLESH_TAIL = re.compile(r"\b(stock|broth|bouillon|sauce|oil|fat|powder|seasoning|flavou?r|flavou?ring|extract|dashi|fumet|gravy|jus|paste|wash|egg wash)\s*\*?$", re.I)


# "fresh egg pasta", "egg noodles", "egg wash", "chicken-stock cubes": the animal word qualifies a product that is not flesh (Phase 3, live run)
NON_FLESH_PRODUCT = re.compile(r"\b(pasta|noodles?|ribbons|dough|bread|wash|cubes?|crackers?|pastry|batter)\b", re.I)


def is_flesh_name(name: str) -> bool:
    n = name.strip()
    return bool(FLESH.search(n)) and not NON_FLESH_TAIL.search(n) and not NON_FLESH_PRODUCT.search(n)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# -- preparation state (spec 2B section 6, D6) -------------------------------------------------


def _cooked_in_dish(parsed: ParsedIngredient, recipe: SourceRecipe) -> bool:
    if not recipe.cooking_verbs:
        return False
    head = re.findall(r"[a-zà-ü]+", parsed.name.lower())
    if recipe.instructions_text and head:
        noun = head[-1].rstrip("s")
        for sentence in re.split(r"(?<=[.!?])\s+", recipe.instructions_text):
            if COOKING_VERBS.search(sentence) and noun in sentence.lower():
                return True
        return False
    return is_flesh_name(parsed.name)              # no method text saved: the conservative rule for flesh foods only


def preparation_state_for(parsed: ParsedIngredient, recipe: SourceRecipe, match: MatchDecision | None) -> tuple[str, str, list[str]]:
    """(state declared to the calculator, reason, flags). Declared from the recipe's own words; never a yield adjustment."""
    hint = parsed.preparation_hint
    if hint == "raw":
        return "raw", "the line says raw", []
    if hint == "cooked":
        return "cooked", "the line says it is cooked (toasted, roasted, ...)", []
    if hint == "as_used":
        return "as_used", "an ingredient class used as it is (oil, cheese, condiment, seeds, bread)", []
    if match is None or match.fdc_id is None:
        return "unknown", "no USDA record to compare the state with", []
    flesh = is_flesh_name(parsed.name)
    if match.record_state == "raw":
        if _cooked_in_dish(parsed, recipe):
            return "raw", "the recipe lists a raw weight and cooks it; raw USDA record, no cooking yield applied (D6)", ["raw_weight_of_cooked_dish"]
        return "raw", "no cooking step applies to this ingredient; raw USDA record", []
    if match.record_state == "unknown" and not flesh:
        return "as_used", "the USDA record is neither raw nor cooked (condiment, cheese, oil, bread or similar)", []
    if match.record_state == "cooked":
        return "unknown", "the line does not say cooked but the chosen record is a cooked food", ["state_conflict"]
    return "unknown", "a flesh food with no stated state and a record of unknown state", []


def blocker_for(si: ScenarioIngredient, reasons: set[str] | None = None) -> BlockerCategory:
    """Why a line the calculator excluded could not be calculated. Priority order fixed; measurement only. `reasons` are the
    calculator's own exclusion codes for the line; they decide between the last categories (2C.1: a line declared cooked on a
    record of unknown state was counted as a nutrient gap)."""
    reasons = reasons or set()
    if si.origin == "menu_only":
        return "menu_only"
    if si.origin == "method_fat":
        return "unknown_quantity"
    if "cooking_medium" in si.flags:
        return "cooking_medium_unknown_amount"       # 3D (12.3.2): the bath or marinade is listed; the share that clings to the food is not
    p = si.parsed
    if p is not None and p.quantity is None:
        if SEASONING.search(p.name):
            return "seasoning_unknown_quantity"
        return "optional_unknown_quantity" if p.optional else "unknown_quantity"
    if "state_conflict" in si.flags or (si.match is not None and (si.match.issue or "").startswith("state_conflict")):
        return "state_conflict"
    if si.match is None or si.match.fdc_id is None:
        if si.match is not None and (si.match.issue or "").startswith("usda_error"):
            return "usda_error"
        return "unresolved_usda"
    if si.conversion.grams is None:
        return "proxy_portion_refused" if "proxy_count_portion_refused" in si.flags else "no_usda_portion"
    if si.preparation_state == "unknown" or any(r.startswith("preparation_unresolved") or r.startswith("as_used_not") for r in reasons):
        return "preparation_unresolved"
    if any(r.startswith("preparation_mismatch") for r in reasons):
        return "state_conflict"
    return "nutrient_not_reported"


# -- the estimate ---------------------------------------------------------------------------------


def estimate_dish(item: MenuItem, *, source: RecipeSource, fetcher: PoliteFetcher, service: Any, llm: Any,
                  parse_json_object: Callable[[str], dict | None] = _default_parse, queries: dict | None = None,
                  max_fetch: int = 12, max_scenarios: int = MAX_SCENARIOS, match_cache: MatchCache | None = None,
                  meter: Meter | None = None, usda_http_requests: Callable[[], int] | None = None,
                  ingestion: IngestionResult | None = None, prefetch_workers: int = 6, extraction_cache: ExtractionCache | None = None,
                  equivalent_records: EquivalentRecordPolicy | bool = True, adapt_mode: str = "off", weights_table: Any | None = None,
                  complete_records: CompleteRecordPolicy | None = None, portion_rules: Any | None = None,
                  exclude_herbs_spices: bool = False, backfill_recipes: bool = False, survey_measures: bool = False,
                  line_tags: bool = False, negligible_sat_fat_per_100g: Decimal | None = None, low_fat_g_per_100g: Decimal | None = None, allow_unsourced_rules: bool = True,
                  judgements: Any | None = None, topup: "TopUp | None" = None, dish_type: Any = ...) -> DishEstimate:
    """3D: ``line_tags`` makes one model call per dish that tags every line (12.3); ``negligible_sat_fat_per_100g`` is the 12.4(b) threshold (None = rule off)."""
    meter = meter or Meter()
    low_fat = low_fat_g_per_100g if low_fat_g_per_100g is not None else LOW_FAT_G_PER_100G       # 12.16.2
    from .portions import dish_type_for
    family = dish_type_for(item) if dish_type is ... else dish_type        # 3K bug fix (known-answer check, 2026-11-08): the dish-kind call's family reaches the portion and weights steps
    llm = MeteredLLM(llm, meter)
    service = MeteredService(service, meter)
    notes: list[str] = []

    # 1. ingest (2B-1)
    with meter.stage("ingest"):
        if ingestion is None:
            ingestion = ingest_dish(item, source=source, fetcher=fetcher, queries=queries, llm=llm, parse_json_object=parse_json_object, max_fetch=max_fetch,
                                    extraction_cache=extraction_cache)
    notes.extend(ingestion.notes)
    distinct = [r for r in ingestion.recipes if r.duplicate_of is None]

    # 2. gate + coverage (Python), 3. rubric (one LLM call)
    scenarios: list[Scenario] = []

    def file_recipes(recs: list[SourceRecipe]) -> list[Scenario]:
        """Gate, coverage and one rubric call for a batch of distinct recipes; the scenarios are appended and returned (3K: the top-up files its recipes the same way)."""
        relevances: list[Relevance] = []
        graded_recipes: list[SourceRecipe] = []
        added: list[Scenario] = []
        with meter.stage("relevance"):
            for r in recs:
                cov, matched, missing = menu_coverage(item, r)
                rel = Relevance(menu_coverage=cov, menu_matched=matched, menu_missing=missing)
                passed, reason = gate(item, r)
                rel.gate, rel.gate_reason = ("passed", None) if passed else ("rejected", reason)
                if passed:
                    graded_recipes.append(r)
                    relevances.append(rel)
                s = Scenario(scenario_id=_scenario_id(r, scenarios), source=_source_of(r), relevance=rel,
                             status="rejected" if not passed else "not_processed", status_reason=None if passed else reason)
                scenarios.append(s)
                added.append(s)
            rubric_log = grade_batch(item, graded_recipes, relevances, llm, parse_json_object, cache=judgements)
            if rubric_log.get("error"):
                notes.append(f"relevance grading failed: {rubric_log['error']}; recipes stay ungraded and are not calculated")
        for s in added:
            if s.status == "rejected":
                continue
            rel = s.relevance
            if rel.hard_exclusion:
                s.status, s.status_reason = "rejected", rel.hard_exclusion
            elif rel.grade == "low":
                s.status, s.status_reason = "rejected", "relevance_low"
            elif rel.grade == "ungraded":
                s.status, s.status_reason = "not_processed", "relevance_ungraded"
            elif s.source.servings is None:
                s.status, s.status_reason = "not_processed", "servings_unknown"
        return added

    file_recipes(distinct)
    by_url = {s.source.canonical_url: s for s in scenarios}

    # 4. choose which relevant recipes to process (cap), best first
    order = {"high": 0, "medium": 1}
    candidates = [s for s in scenarios if s.status == "not_processed" and s.status_reason is None]
    recipe_of = {r.canonical_url: r for r in distinct}
    candidates.sort(key=lambda s: (order.get(s.relevance.grade, 9), -(recipe_of[s.source.canonical_url].n_quantified), s.source.url))
    chosen = candidates[:max_scenarios]
    waiting = candidates[max_scenarios:]
    for s in waiting:
        s.status_reason = "beyond_scenario_cap"

    tags: LineTags | None = None
    if line_tags:
        # 12.3.1: one call per dish, all its recipes together: the chosen ones and the ones a backfill round could still bring in (at most one round)
        to_tag = [recipe_of[s.source.canonical_url] for s in chosen + waiting[:max_scenarios]]
        with meter.stage("tags"):
            words = sorted({w for s in chosen + waiting[:max_scenarios] for w in s.relevance.menu_missing})
            tags = tag_lines(item, to_tag, llm, parse_json_object, cache=judgements, menu_words=words)
        if not tags.available:
            notes.append(f"line tags unavailable ({tags.log.get('error')}): the text patterns of 3C decide frying fat and the near-zero composition rule is not applied (12.3.4)")
        elif "tagged" in tags.log:
            notes.append(f"line tags: {tags.log['tagged']} lines in {tags.log['recipes']} recipes ({tags.log['from_saved']} from saved tags); {tags.log['overridden']} answers overridden by code; counts {tags.counts()}")

    calculator = RecipeCalculator(service)
    portions_cache: dict[int, Any] = {}
    policy = equivalent_records if isinstance(equivalent_records, EquivalentRecordPolicy) else EquivalentRecordPolicy(service, enabled=bool(equivalent_records))
    complete_policy = complete_records if complete_records is not None else CompleteRecordPolicy(service, enabled=False)
    from .survey import SurveyMeasurePolicy
    survey_policy = SurveyMeasurePolicy(service) if survey_measures else None     # D25 (Julius, 2026-11-05): a Survey record of the same food lends a cup weight

    def process(batch: list[Scenario]) -> None:
        """5. USDA matching, batched (plus menu-only words, so provenance shows their record too); 6. state, conversion, menu-only lines, calculator."""
        with meter.stage("match"):
            requests: list[MatchRequest] = []
            for s in batch:
                r = recipe_of[s.source.canonical_url]
                cat = (lambda n: (tags.get(r.canonical_url, n).category if tags is not None and tags.available and tags.get(r.canonical_url, n) is not None else ""))
                requests += [MatchRequest(name=p.name, preparation_hint=p.preparation_hint, category=cat(n)) for n, p in enumerate(r.ingredients, start=1)]   # 3K: the category rides along for the zero-fat fallback
                requests += [MatchRequest(name=w, preparation_hint="unknown", category=(tags.menu[w].category if tags is not None and tags.available and w in tags.menu else "")) for w in s.relevance.menu_missing]
            matcher = UsdaMatcher(service, llm, parse_json_object=parse_json_object, cache=match_cache)
            context = f'{item.name} ({item.section or "menu item"}): {item.description or "no ingredients printed"}'
            decisions, match_log = matcher.match(requests, context=context) if requests else ({}, None)
            if match_log is not None:
                meter.count("match_cache_hits", match_log.cache_hits)
                meter.llm_failures += match_log.llm_failures
                notes.extend(f"match: {n}" for n in match_log.notes)
        with meter.stage("convert_and_calculate"):
            _prefetch(service, decisions, prefetch_workers)
            for s in batch:
                _build_scenario(s, recipe_of[s.source.canonical_url], decisions, service, portions_cache, calculator, notes, policy, complete_policy, item=item,
                                exclude_herbs_spices=exclude_herbs_spices, survey_policy=survey_policy, tags=tags, negligible_sat_fat=negligible_sat_fat_per_100g, low_fat=low_fat)

    def model_portions() -> tuple[list, Any, list]:
        """Phases 2C and 2D, internal only; the reply never reads these. Pure Python over the calculated scenarios, so a backfill simply runs it again."""
        pairs, summary_2c, out = [], None, []
        if adapt_mode != "off":
            from .adapt import WeightsTable, adapt_pairs
            from .survey import fried_record_covers
            with meter.stage("adapt"):
                pairs, summary_2c = adapt_pairs(scenarios, service=service, table=weights_table or WeightsTable.load(), mode=adapt_mode, dish_type=family, item=item, medium_covered=fried_record_covers(item), low_fat=low_fat)
        if portion_rules is not None:
            from .portions import pair_inputs, portion_scenario, published_input
            with meter.stage("portion"):
                for s in scenarios:
                    inp = published_input(s, service, low_fat)
                    if inp is None:
                        continue
                    r = recipe_of[s.source.canonical_url]
                    out.append(portion_scenario(inp, item=item, rules=portion_rules, calculator=calculator, yield_text=r.yield_text, method_text=r.instructions_text, allow_unsourced=allow_unsourced_rules, dish_type=family))
                for pair in pairs:
                    s = next(x for x in scenarios if x.scenario_id == pair.derived_from)
                    inputs = pair_inputs(pair, s, service, low_fat)
                    if inputs is None:
                        continue
                    r = recipe_of[s.source.canonical_url]
                    out.append(portion_scenario(inputs, item=item, rules=portion_rules, calculator=calculator, yield_text=r.yield_text, method_text=r.instructions_text, allow_unsourced=allow_unsourced_rules, dish_type=family))
        return pairs, summary_2c, out

    process(chosen)
    adapted, internal, portioned = model_portions()
    # Julius, 2026-11-05: a recipe that cannot be portioned gives its place to the next eligible one. At most one round of replacements (so at most twice the
    # cap's worth of recipes are processed): a third round on the Greyhound schnitzel processed 11 recipes, made about 900 USDA requests for one dish and hit
    # USDA's hourly request limit, which then failed the dish's Survey lookup.
    rounds = 0
    while backfill_recipes and portion_rules is not None and waiting and rounds < BACKFILL_ROUNDS:
        rounds += 1
        # 3D (12.5.2): replacement recipes are fetched only for a recipe's own failure, never because of a USDA error. A recipe that USDA refused
        # keeps its place, and when the client is refusing to ask USDA at all no replacement is tried.
        halted = _usda_halted(service)
        if halted:
            notes.append("backfill skipped: USDA refused requests this hour; a USDA error is never a reason to fetch replacement recipes (12.5.2)")
            break
        usda_failed = {s.scenario_id for s in scenarios if s.status == "calculated" and any(l.blocker == "usda_error" for l in s.ingredients)}
        usable = {p.derived_from.removesuffix("::adapted") for p in portioned if p.applicable} | usda_failed
        if usda_failed:
            notes.append(f"backfill: {len(usda_failed)} recipe(s) failed on a USDA error keep their place and are not replaced (12.5.2)")
        need = max_scenarios - len(usable)
        if need <= 0:
            break
        batch, waiting = waiting[:need], waiting[need:]
        for s in batch:
            s.status_reason = None
        notes.append(f"backfill: {len(usable)} of the recipes tried could be portioned; trying {len(batch)} more")
        process(batch)
        adapted, internal, portioned = model_portions()
    # 3K (12.20, Julius's decision 3 of 2026-11-08): when fewer than `topup.min_usable` recipes could be portioned after the first round and its backfill, one more
    # search phrased from the menu's own words (`ingest.topup_query`), one credit, a handful of new pages, graded and tagged like the first ones, processed up to the cap;
    # never after a USDA refusal (12.5.2), never beyond the menu's spending room or its top-up count.
    topup_log: dict[str, Any] = {}
    if topup is not None and portion_rules is not None:
        usable_now = {p.derived_from.removesuffix("::adapted") for p in portioned if p.applicable}
        if len(usable_now) < topup.min_usable:
            if _usda_halted(service):
                notes.append("top-up skipped: USDA refused requests this hour; a USDA error is never a reason to fetch more recipes (12.5.2)")
                topup_log = {"skipped": "usda_halted", "usable_before": len(usable_now)}
            elif not topup.allowed():
                notes.append("top-up skipped: the menu's spending room or its top-up count is used up")
                topup_log = {"skipped": "budget", "usable_before": len(usable_now)}
            else:
                q = topup_query(item)
                known = {r.canonical_url for r in ingestion.recipes} | {h.canonical_url for h in ingestion.hits}
                with meter.stage("ingest"):
                    extra = ingest_dish(item, source=source, fetcher=fetcher, queries={"open": q}, llm=llm, parse_json_object=parse_json_object, max_fetch=topup.extra_fetch,
                                        extraction_cache=extraction_cache, modes=("open",), skip_urls=known)
                notes.extend(f"top-up: {n}" for n in extra.notes)
                have_urls = {r.canonical_url for r in distinct}
                have_hashes = {r.content_hash for r in distinct}
                new = [r for r in extra.recipes if r.duplicate_of is None and r.canonical_url not in have_urls and r.content_hash not in have_hashes]
                distinct.extend(new)
                recipe_of.update({r.canonical_url: r for r in new})
                added = file_recipes(new) if new else []
                fresh = [s for s in added if s.status == "not_processed" and s.status_reason is None]
                fresh.sort(key=lambda s: (order.get(s.relevance.grade, 9), -(recipe_of[s.source.canonical_url].n_quantified), s.source.url))
                batch, rest = fresh[:max_scenarios], fresh[max_scenarios:]
                for s in rest:
                    s.status_reason = "beyond_scenario_cap"
                if line_tags and batch:
                    with meter.stage("tags"):
                        words = sorted({w for s in batch for w in s.relevance.menu_missing})
                        more = tag_lines(item, [recipe_of[s.source.canonical_url] for s in batch], llm, parse_json_object, cache=judgements, menu_words=words)
                    if tags is None:
                        tags = more
                    else:
                        tags.merge(more)
                if batch:
                    process(batch)
                    adapted, internal, portioned = model_portions()
                usable_after = {p.derived_from.removesuffix("::adapted") for p in portioned if p.applicable}
                topup.used()
                topup_log = {"query": q, "hits": len(extra.hits), "fetched": extra.stats.fetched, "new_recipes": len(new), "processed": len(batch), "usable_before": len(usable_now),
                             "usable_after": len(usable_after), "credits": extra.stats.search_credits}
                notes.append(f"top-up (12.20): {len(usable_now)} recipe(s) could be portioned after the first round; searched '{q}', {len(extra.hits)} hits, {len(new)} new recipe(s), "
                             f"{len(batch)} processed; {len(usable_after)} usable now")
    notes.extend(f"D22: {e['line'][:60]!r}: {e['from']} -> {e['to']}" for e in policy.log if "to" in e)
    if survey_policy is not None:
        notes.extend(f"D25: {e['line'][:60]!r}: measure {e['grams']} g from Survey record {e['measure_from']} '{e['description']}'; nutrients from {e['from']}" for e in survey_policy.log)
    notes.extend(f"D24 ({'applied' if e['applied'] else 'not applied: policy off'}): {e['line'][:60]!r}: {e['from']} -> {e['to']} (sat fat delta {e['delta']} g/100 g)"
                 for e in complete_policy.log if "to" in e)

    # 7. comparison over eligible scenarios (Phase 2A compare, unchanged)
    with meter.stage("compare"):
        eligible = [s for s in scenarios if s.eligible_for_range]
        comparison = None
        if eligible:
            results = [RecipeResult.model_validate(s.calculation) for s in eligible]
            comparison = compare_scenarios(results, basis="per_serving").model_dump(mode="json")

    summary = _summary(item, scenarios, comparison, ingestion)
    cost = meter.costs(usda_http_requests=usda_http_requests() if usda_http_requests else None, search_credits=ingestion.stats.search_credits,
                       pages_fetched=ingestion.stats.fetched, pages_from_cache=ingestion.stats.fetch_from_cache)
    return DishEstimate(menu_item=item, queries=ingestion.queries, ingestion=ingestion.stats, scenarios=scenarios, comparison=comparison,
                        summary=summary, cost=cost, notes=notes, adapt_mode=adapt_mode, adapted_pairs=adapted, internal_summary=internal, portioned=portioned, topup=topup_log)


def _usda_halted(service: Any) -> bool:
    """True when the nutrition service reports that USDA refused a request this hour (spec v2.3); False for a service without that method (tests)."""
    status = getattr(service, "usda_status", None)
    if not callable(status):
        return False
    try:
        return bool(status().get("halted"))
    except Exception:  # noqa: BLE001
        return False


def _prefetch(service: Any, decisions: dict[str, MatchDecision], workers: int) -> None:
    """Warm the service cache for every matched record (nutrition and portions) with a few threads: USDA answers in
    about a second per request, and a dish needs 30-50 records. Results are not used here; the later sequential calls
    hit the cache. The service is documented thread-safe and never raises."""
    if workers <= 1:
        return
    from concurrent.futures import ThreadPoolExecutor
    ids = sorted({d.fdc_id for d in decisions.values() if d.fdc_id is not None})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fid in ids:
            pool.submit(service.get_nutrition, fid)
            pool.submit(service.get_portions, fid)


def _scenario_id(r: SourceRecipe, existing: list[Scenario]) -> str:
    base = f"{r.host}:{_slug(r.title)[:40] or 'recipe'}"
    sid, n = base, 2
    taken = {s.scenario_id for s in existing}
    while sid in taken:
        sid, n = f"{base}-{n}", n + 1
    return sid


def _source_of(r: SourceRecipe) -> ScenarioSource:
    return ScenarioSource(url=r.url, canonical_url=r.canonical_url, host=r.host, title=r.title, found_by=list(r.found_by), extraction=r.extraction,
                          yield_text=r.yield_text, yield_source=r.yield_source, servings=r.servings, servings_note=r.servings_note,
                          n_lines=r.n_lines, flags=list(r.flags))


def _build_scenario(s: Scenario, r: SourceRecipe, decisions: dict[str, MatchDecision], service: Any, portions_cache: dict, calculator: RecipeCalculator,
                    notes: list[str], policy: EquivalentRecordPolicy | None = None, complete_policy: CompleteRecordPolicy | None = None,
                    item: MenuItem | None = None, exclude_herbs_spices: bool = False, survey_policy: Any | None = None,
                    tags: LineTags | None = None, negligible_sat_fat: Decimal | None = None, low_fat: Decimal = LOW_FAT_G_PER_100G) -> None:
    lines: list[ScenarioIngredient] = []
    flags: set[str] = set()
    tagged = tags is not None and tags.available
    for n, p in enumerate(r.ingredients, start=1):
        match = decisions.get(MatchRequest(name=p.name, preparation_hint=p.preparation_hint).key)
        converted = p
        if "sub_recipe_reference" in p.flags and "sub_recipe_components_on_page" in p.flags:
            # "1 recipe pizza dough, recipe follows": the dough's own lines are in this list; the reference is not an ingredient (2C.1)
            lines.append(ScenarioIngredient(ingredient_id=f"ing_{n:02d}", origin="recipe", line=p.line, name=p.name, parsed=p, match=match,
                                            conversion=Conversion(from_text="sub-recipe reference", grams=None, method="none"), preparation_state="unknown",
                                            state_reason="a reference to a sub-recipe whose components are listed on the same page",
                                            excluded_from_calculation="sub_recipe_reference_components_listed", flags=sorted(set(p.flags))))
            flags.add(f"sub_recipe_reference_skipped:{p.name}")
            continue
        if p.grams is None and p.quantity is not None and p.unit_kind in ("volume", "count") and match is not None and match.fdc_id is not None:
            portions = portions_cache.get(match.fdc_id)
            if portions is None:
                result = service.get_portions(match.fdc_id)
                portions = [] if isinstance(result, ErrorResult) else list(result.portions)
                if isinstance(result, ErrorResult):
                    p = p.model_copy(update={"flags": p.flags + [f"portions_unavailable:{result.error_code}"]})
                portions_cache[match.fdc_id] = portions
            converted = convert_with_portions(p, portions, match.fdc_id, proxy=(match.match_type == "proxy"), record=match.description or "")
            if converted.grams is None and policy is not None:
                found = policy.find(p, match)                     # D22: same food, same state, equivalent values, usable measure
                if found is not None:
                    match, converted = found
                    flags.add(f"d22_equivalent_record:{p.name}")
            if converted.grams is None and survey_policy is not None:
                lent = survey_policy.find(p, match)               # D25: the same food's Survey record lends its volume measure; the record and its nutrients stay
                if lent is not None:
                    converted = lent
                    flags.add(f"d25_survey_measure:{p.name}")
        if complete_policy is not None and match is not None and match.fdc_id is not None:
            found = complete_policy.find(p, match, converted)     # D24 (proposed): same food, both nutrients reported, saturated fat within tolerance
            if found is not None and complete_policy.enabled:
                match, converted = found
                flags.add(f"d24_complete_record:{p.name}")
        tag = None
        excluded_reason: str | None = None
        if tagged:
            raw = tags.get(r.canonical_url, n)
            if raw is not None:
                # 12.3: re-validated now that the line's USDA record is known (can only make the tag stricter)
                tag = validate_tag(p.name, raw.raw_role or raw.role, raw.raw_kind or raw.kind, raw.reason, record_description=match.description if match else None,
                                   match_type=match.match_type if match else None, category=raw.category)
                if tag.role == "removed":
                    excluded_reason = REMOVED_REASON
                elif tag.role == "cooking_medium":
                    nut = service.get_nutrition(match.fdc_id) if match is not None and match.fdc_id is not None else None
                    if nut is not None and not isinstance(nut, ErrorResult) and near_zero(nut, negligible_sat_fat if negligible_sat_fat is not None else Decimal("0.1"), low_fat):
                        excluded_reason = MEDIUM_NEGLIGIBLE_REASON                 # a brine, water or stock bath: nothing to count, not part of the served mass
                    else:
                        # 12.3.2: never counted at its recipe weight; the eaten share comes from USDA's fried-food record or a per-plate row (W09)
                        converted = converted.model_copy(update={"grams": None, "grams_reference": f"cooking medium (line tag: {tag.reason[:80]}); the recipe weight is the bath or marinade, not what is eaten",
                                                                 "flags": converted.flags + ["cooking_medium"]})
        else:
            is_fat = match is not None and FAT_RECORD_HEAD.match(match.description or "") is not None
            bath = converted.grams is not None and converted.grams >= FRYING_BATH_MIN_G and bool(FRIED_WORDS.search(" ".join(r.cooking_verbs)) or FRIED_WORDS.search((r.instructions_text or "")[:3000]))
            if converted.grams is not None and is_fat and (FRYING_FAT_LINE.search(converted.line or "") or bath):
                # 3C text patterns, kept as the fallback when the tag call fails (12.3.4): "2 cups canola oil, for frying" is the pan's, not the plate's
                converted = converted.model_copy(update={"grams": None, "grams_reference": "stated frying fat; the amount absorbed by the food is unknown", "flags": converted.flags + ["frying_fat_stated_not_consumed"]})
        state, state_reason, sflags = preparation_state_for(p, r, match)
        conv = _conversion_of(converted)
        assumption = "; ".join(x for x in [conv.reference, state_reason if state_reason else None] + [f for f in sflags + conv.flags if f in
                               ("raw_weight_of_cooked_dish", "range_midpoint", "density_assumed_1", "embedded_weight_total_assumed", "portion_default_medium",
                                "portion_default_single", "portion_whole_item", "portion_derived_volume", "proxy_volume_portion", "d22_equivalent_record", "portion_modifier_unmatched",
                                "assumed_size_median", "single_labelled_size", "survey_measure", "class_level_cup_weight")] if x)[:500]
        si = ScenarioIngredient(ingredient_id=f"ing_{n:02d}", origin="recipe", line=p.line, name=p.name, parsed=converted, match=match, conversion=conv,
                                preparation_state=state, state_reason=state_reason, assumption=assumption or None, flags=sorted(set(sflags + converted.flags)),
                                tag_role=tag.role if tag else "", tag_kind=tag.kind if tag else "", tag_reason=tag.reason if tag else "", tag_note=tag.note if tag else "",
                                tag_category=tag.category if tag else "")
        if "cooking_medium" in si.flags:
            si.assumption = "cooking medium (line tag): not counted at its recipe weight and not part of the served mass; the eaten share comes from USDA's fried-food record or a per-plate row (12.3.2)"
            flags.add("cooking_medium_open")
        if excluded_reason is not None:
            si.excluded_from_calculation = excluded_reason
            si.assumption = ("lifted out before serving (line tag 'removed'); left out of the calculation and the recipe weight (12.3.3)" if excluded_reason == REMOVED_REASON
                             else "a cooking medium whose record reports no saturated fat or cholesterol to speak of (brine, water, stock); left out of the calculation and the served mass (12.3.2)")
            flags.add("tag_excluded")
        lines.append(si)
        flags.update(f for f in sflags if f == "raw_weight_of_cooked_dish")
        for f in converted.flags:
            if f in ("range_midpoint", "density_assumed_1", "embedded_weight_total_assumed"):
                flags.add(f"{f}:{p.name}")
    for word in s.relevance.menu_missing:                                           # D8: nothing listed on the menu vanishes
        n = len(lines) + 1
        match = decisions.get(MatchRequest(name=word, preparation_hint="unknown").key)
        tag = menu_word_tag(tags, item, word, match) if tagged and item is not None else None      # 12.14.12: menu-only lines have a kind too
        lines.append(ScenarioIngredient(ingredient_id=f"ing_{n:02d}", origin="menu_only", line=None, name=word, parsed=None, match=match,
                                        conversion=Conversion(from_text="not in this recipe", grams=None, method="none"), preparation_state="unknown",
                                        state_reason="menu-only line", assumption=MENU_ONLY_ASSUMPTION, blocker="menu_only",
                                        tag_role=tag.role if tag else "", tag_kind=tag.kind if tag else "", tag_reason=tag.reason if tag else "", tag_note=tag.note if tag else "",
                                        tag_category=tag.category if tag else ""))
    if exclude_herbs_spices:
        for l in lines:
            if l.origin != "method_fat" and l.excluded_from_calculation is None and is_herb_or_spice(l.name, l.match.description if l.match else None, l.match.match_type if l.match else None):
                l.excluded_from_calculation = HERB_SPICE_REASON
                l.blocker = None
                l.assumption = "herb or spice left out of the calculation and the recipe weight (Julius, 2026-11-05); not a USDA value"
                flags.add("herbs_spices_excluded")
    composition_log: dict[str, tuple] = {}
    if tagged and negligible_sat_fat is not None:
        # 12.14.12: a plain food whose record shows at most the threshold of saturated fat and 0 cholesterol, reported or by the facts of 12.14.7, never holds up a recipe, from the recipe or
        # the menu, with a quantity or without. The rule sets the line's nutrients only: a stated amount with no USDA weight keeps `mass_gap`, the pair still looks for its weight, and the
        # plate-weight method still needs it (salt, zest, peel and citrus juice count as zero weight, 12.4.4). A prepared product never passes, whatever it was matched to.
        for l in lines:
            if l.origin not in ("recipe", "menu_only") or l.excluded_from_calculation is not None or l.conversion.grams is not None or l.match is None or l.match.fdc_id is None or l.tag_kind != "plain_food":
                continue
            nut = service.get_nutrition(l.match.fdc_id)
            if isinstance(nut, ErrorResult) or not near_zero(nut, negligible_sat_fat, low_fat):
                continue                                                # D23: a missing value is not zero
            if l.origin == "recipe" and l.parsed is not None and l.parsed.quantity is not None and not ZERO_WEIGHT_WORDS.search(l.name):
                l.mass_gap = blocker_for(l)
            l.excluded_from_calculation = NEGLIGIBLE_COMPOSITION_REASON
            l.blocker = None
            l.assumption = f"the record shows {nut.saturated_fat_g} g saturated fat and {nut.cholesterol_mg} mg cholesterol per 100 g (reported, or by the facts of 12.14.7): counted as zero for both (12.14.12)"
            composition_log[l.ingredient_id] = (nut.fdc_id, nut.description, l.match.match_type, nut.saturated_fat_g, nut.cholesterol_mg)
            flags.add("negligible_composition_excluded")
    menu_text = f"{item.name} {item.description}" if item is not None else ""
    fried = FRIED_WORDS.search(menu_text) or FRIED_WORDS.search(" ".join(r.cooking_verbs)) or FRIED_WORDS.search((r.instructions_text or "")[:3000])
    has_fat = any(l.origin == "recipe" and l.match is not None and l.match.fdc_id is not None and FAT_RECORD_HEAD.match(l.match.description or "") for l in lines)
    if fried and not has_fat:
        # Phase 3 (2026-11-04, Julius: never invent deep-frying oil): a breaded whiting recipe listed fish, flour, egg and crumbs and fried them in
        # oil named only in the method; the list is not complete. The open line keeps the upper bound honest; no row or evidence may fill it.
        n = len(lines) + 1
        lines.append(ScenarioIngredient(ingredient_id=f"ing_{n:02d}", origin="method_fat", line=None, name="frying fat (the recipe fries but lists no oil, butter or fat)", parsed=None, match=None,
                                        conversion=Conversion(from_text="method text only", grams=None, method="none"), preparation_state="unknown",
                                        state_reason=f"the method or the menu says fried ({fried.group(0).lower()}) and no fat line is in the ingredient list",
                                        assumption="frying fat not listed by the recipe; quantity unknown and never assumed", blocker="unknown_quantity"))
        flags.add("frying_fat_not_listed")
    s.ingredients = lines
    recipe_lines = [l for l in lines if l.origin == "recipe"]
    s.match_counts = {"direct": sum(1 for l in recipe_lines if l.match and l.match.match_type == "direct"),
                      "proxy": sum(1 for l in recipe_lines if l.match and l.match.match_type == "proxy"),
                      "unresolved": sum(1 for l in recipe_lines if not l.match or l.match.match_type == "unresolved")}
    s.proxies = [f"{l.name} -> {l.match.description} ({l.match.fdc_id})" for l in recipe_lines if l.match and l.match.match_type == "proxy"]

    recipe_input = {"recipe_name": s.scenario_id, "servings": str(r.servings), "ingredients": [
        {"name": l.name[:200] or "ingredient", "fdc_id": l.match.fdc_id if l.match else None,
         "grams": str(l.conversion.grams) if l.conversion.grams is not None else None, "preparation_state": l.preparation_state,
         "assumption": l.assumption, "ingredient_id": l.ingredient_id} for l in lines if l.excluded_from_calculation is None]}
    result = calculator.calculate(recipe_input)                                     # Phase 2A, unchanged
    if not isinstance(result, RecipeResult):
        s.status, s.status_reason, s.calculation_status = "invalid", "; ".join(result.problems)[:300], "invalid"
        s.calculation = result.model_dump(mode="json")
        s.representativeness = "not_calculated"
        return
    s.status, s.calculation, s.calculation_status = "calculated", result.model_dump(mode="json"), result.status
    s.completeness_by_nutrient = {n: t.complete for n, t in result.totals.items()}     # D23 measurement
    # 2D: the documented-inference layer, beside the calculation (assumed median sizes; narrow zero-nutrient rules). The calculation is untouched.
    median_ids = {l.ingredient_id: (l.conversion.reference or "") for l in lines if "assumed_size_median" in l.conversion.flags}
    class_ids = {l.ingredient_id: (l.conversion.reference or "") for l in lines if "class_level_cup_weight" in l.conversion.flags}
    s.inferences, s.inferred_totals = apply_inference_layer(result, median_ids, class_ids, NutrientFacts(service, {l.ingredient_id for l in lines if l.tag_kind == "plain_food"}, low_fat))
    left_out = [herb_spice_inference(l.ingredient_id, l.name, l.conversion.grams) for l in lines if l.excluded_from_calculation == HERB_SPICE_REASON]
    left_out += [not_eaten_inference(l.ingredient_id, l.name, l.conversion.grams, "removed" if l.excluded_from_calculation == REMOVED_REASON else "medium", l.tag_reason)
                 for l in lines if l.excluded_from_calculation in (REMOVED_REASON, MEDIUM_NEGLIGIBLE_REASON)]
    left_out += [composition_inference(l.ingredient_id, l.name, fdc_id=v[0], description=v[1], match_type=v[2], sat=v[3], chol=v[4], threshold=negligible_sat_fat)
                 for l in lines for v in [composition_log.get(l.ingredient_id)] if v is not None]
    s.inferences = s.inferences + left_out
    s.basis = "documented_inferences" if s.inferences else "source_reported"
    s.completeness_basis = completeness_basis(s.inferred_totals, bool(median_ids) or bool(class_ids) or bool(left_out))
    if median_ids:
        flags.add("assumed_size_median")
    if class_ids:
        flags.add("class_level_cup_weight")

    # blockers (measurement) from the lines the calculator excluded for any nutrient, told apart by the calculator's own reason codes
    excluded_reasons: dict[str, set[str]] = {}
    for t in result.totals.values():
        for e in t.excludes:
            excluded_reasons.setdefault(e.ingredient_id, set()).add(e.reason)
    counts: dict[str, int] = {}
    for l in lines:
        if l.ingredient_id in excluded_reasons:
            l.blocker = blocker_for(l, excluded_reasons[l.ingredient_id])
            counts[l.blocker] = counts.get(l.blocker, 0) + 1
    s.blockers = counts
    cats = set(counts)
    s.complete_except_seasonings = bool(cats) and cats <= {"seasoning_unknown_quantity"}
    s.complete_except_menu_only = bool(cats) and cats <= {"menu_only"}
    s.complete_except_seasonings_and_menu_only = bool(cats) and cats <= {"seasoning_unknown_quantity", "menu_only"} and len(cats) == 2

    # proxy share per nutrient (D10): proxies weighted by their effect, not counted
    proxy_ids = {l.ingredient_id for l in recipe_lines if l.match and l.match.match_type == "proxy"}
    share: dict[str, Decimal | None] = {}
    amounts: dict[str, Decimal] = {}
    largest: dict[str, bool] = {}
    for nutrient, total in result.totals.items():
        contributions = {i.ingredient_id: getattr(i.contribution, nutrient) for i in result.ingredients if i.resolved[nutrient]}
        proxy_sum = sum((v for k, v in contributions.items() if k in proxy_ids), Decimal(0))
        amounts[nutrient] = proxy_sum
        share[nutrient] = (proxy_sum / total.known_subtotal) if total.known_subtotal > 0 else None
        top = max(contributions, key=lambda k: contributions[k]) if contributions else None
        largest[nutrient] = bool(top is not None and top in proxy_ids and contributions[top] > 0)
    s.proxy_contribution, s.proxy_share, s.largest_contributor_is_proxy = amounts, share, largest
    s.proxy_share_percent = {n: int(v * 100) for n, v in share.items() if v is not None}
    largest_is_proxy = any(largest.values())
    if largest_is_proxy:
        flags.add("proxy_largest_contributor")
    if any(v is not None and v > 0 for v in share.values()):
        flags.add("proxy_share_of_known_subtotal")       # D18: shares are of the known subtotal, never of the unknown true total
    proxy_dependent = largest_is_proxy or any(v is not None and v > PROXY_SHARE_LIMIT for v in share.values())
    over_limit = any(v is not None and v > PROXY_SHARE_LIMIT for v in share.values())

    grade, cov = s.relevance.grade, s.relevance.menu_coverage
    if grade == "low":
        s.representativeness = "low"
    elif proxy_dependent:
        s.representativeness = "proxy_dependent"
    elif grade == "high" and (cov is None or cov == 1):
        s.representativeness = "high"
    else:
        s.representativeness = "medium"
    s.flags = sorted(flags)
    if result.status != "complete":
        missing = ", ".join(sorted({l.name for l in lines if l.blocker}))
        s.eligible_for_range, s.ineligible_reason = False, f"incomplete: {missing}"[:300]
    elif s.inferences:
        # complete only with a documented inference (an assumed median size): internal estimates may use it; the user-facing range may not
        s.eligible_for_range, s.ineligible_reason = False, f"documented_inferences: {', '.join(sorted({i.name for i in s.inferences}))}"[:300]
    elif over_limit:
        worst = max((v for v in share.values() if v is not None), default=Decimal(0))
        s.eligible_for_range, s.ineligible_reason = False, f"proxy_dependent: {int(worst * 100)}% of a nutrient's known subtotal comes from substitute USDA records"
    else:
        s.eligible_for_range, s.ineligible_reason = True, None


def _conversion_of(p: ParsedIngredient) -> Conversion:
    text = " ".join(x for x in [p.quantity_text, p.unit_raw or (p.unit if p.unit not in (None, "each") else None)] if x) or (p.quantity_text or "no quantity")
    if p.grams is None:
        method = "none"
    elif "embedded_weight" in p.flags:
        method = "embedded_weight"
    elif "assumed_size_median" in p.flags:
        method = "usda_portion_median"
    elif "usda_portion" in p.flags:
        method = "usda_portion"
    elif "density_assumed_1" in p.flags:
        method = "density_water_like"
    else:
        method = "weight_unit"
    keep = [f for f in p.flags if f in ("range_midpoint", "vague_quantity", "conversion_pending_usda_portion", "density_assumed_1", "embedded_weight",
                                        "embedded_weight_total_assumed", "usda_portion", "portion_default_medium", "portion_default_single",
                                        "portion_default_whole", "portion_whole_item", "portion_size_unspecified", "portion_derived_volume", "proxy_volume_portion",
                                        "proxy_count_portion_refused", "inline_weight", "d22_equivalent_record", "d24_complete_record", "portion_modifier_unmatched", "portion_ambiguous",
                                        "portion_none_for_unit", "embedded_weight_after_measure", "unit_typo_corrected", "unit_repeated", "unit_from_name", "portion_size_word_unmatched",
                                        "assumed_size_median", "single_labelled_size")]
    return Conversion(from_text=text, grams=p.grams, method=method, reference=p.grams_reference, flags=keep)


# -- summary and statement (Python templates; the only words a user sees) -----------------------------------


def _summary(item: MenuItem, scenarios: list[Scenario], comparison: dict | None, ingestion: IngestionResult) -> DishSummary:
    st = ingestion.stats
    relevant = [s for s in scenarios if s.relevance.grade in ("high", "medium") and not s.relevance.hard_exclusion]
    calculated = [s for s in scenarios if s.status == "calculated"]
    complete = [s for s in calculated if s.calculation_status == "complete"]
    eligible = [s for s in scenarios if s.eligible_for_range]
    reasons: dict[str, int] = {}
    for s in scenarios:
        if s.eligible_for_range:
            continue
        key = s.status_reason if s.status != "calculated" else (s.ineligible_reason or "ineligible").split(":")[0]
        key = (key or "unknown").split(":")[0] if s.status != "calculated" else key
        reasons[key] = reasons.get(key, 0) + 1
    flags = sorted({f.split(":")[0] for s in eligible for f in s.flags})
    listed = [w.strip() for w in item.description.split(",") if w.strip()]
    missing_set = {w for s in relevant for w in s.relevance.menu_missing}
    all_missing = [w for w in listed if w in missing_set]                       # in the menu's own order
    statement = _statement(item, scenarios, comparison, len([r for r in ingestion.recipes if r.duplicate_of is None]), relevant, calculated, complete,
                           eligible, flags, all_missing)
    return DishSummary(
        n_hits=st.hits_after_url_dedup, n_fetched=st.fetched, n_extracted=st.extracted, n_distinct=st.distinct_recipes,
        n_gate_passed=sum(1 for s in scenarios if s.relevance.gate == "passed"), n_relevant=len(relevant),
        n_processed=sum(1 for s in scenarios if s.status in ("calculated", "invalid")), n_calculated=len(calculated), n_complete=len(complete),
        n_eligible=len(eligible), exclusion_reasons=reasons,
        n_saturated_fat_only_complete=sum(1 for s in calculated if s.completeness_by_nutrient.get("saturated_fat_g") and not s.completeness_by_nutrient.get("cholesterol_mg")),
        blocked_only_by_seasonings=sum(1 for s in calculated if s.complete_except_seasonings),
        blocked_only_by_menu_only=sum(1 for s in calculated if s.complete_except_menu_only),
        blocked_only_by_seasonings_and_menu_only=sum(1 for s in calculated if s.complete_except_seasonings_and_menu_only),
        range_meaningful=bool(comparison) and all(n["range_meaningful"] for n in comparison["nutrients"].values()),
        statement=statement, flags=flags,
    )


def _statement(item, scenarios, comparison, n_distinct, relevant, calculated, complete, eligible, flags, all_missing) -> str:
    name = item.name
    if not relevant:
        return (f"No comparable published recipe was found for {name}: {n_distinct} recipes were read and none matched the dish type and "
                f"preparation. {NO_VALUES}")
    notes = []
    if "raw_weight_of_cooked_dish" in flags:
        notes.append("Based on raw ingredient weights; cooking losses and any cooking fat absorbed are not accounted for.")
    proxies = sorted({p for s in eligible for p in s.proxies})
    if proxies:
        notes.append("Substitute USDA records were used for: " + "; ".join(proxies) + ".")
    if len(eligible) >= 2 and comparison:
        sat, chol = comparison["nutrients"]["saturated_fat_g"], comparison["nutrients"]["cholesterol_mg"]
        text = (f"Range across {len(eligible)} modeled recipes for {name}, per serving: saturated fat {_amt(sat['min'], 'saturated_fat_g')} to "
                f"{_amt(sat['max'], 'saturated_fat_g')} (median {_amt(sat['median'], 'saturated_fat_g')}); cholesterol {_amt(chol['min'], 'cholesterol_mg')} to "
                f"{_amt(chol['max'], 'cholesterol_mg')} (median {_amt(chol['median'], 'cholesterol_mg')}). ")
        return text + " ".join(notes + [f"Ranges describe the published recipes only. {NOT_VERIFIED}"])
    if len(eligible) == 1:
        s = eligible[0]
        d = s.calculation["display"]
        return (f"Only 1 of {len(relevant)} comparable recipes for {name} could be calculated completely; evidence is insufficient for a range. "
                f"That recipe ({s.source.title}, {s.source.host}) gives saturated fat {d['saturated_fat_g']} and cholesterol {d['cholesterol_mg']}. "
                + " ".join(notes + [NOT_VERIFIED]))
    reasons = []
    cats = {c for s in calculated for c in s.blockers}
    if "menu_only" in cats and all_missing:
        reasons.append(f"the published recipes do not include {', '.join(all_missing)}, which the menu lists")
    if "seasoning_unknown_quantity" in cats:
        reasons.append("some seasonings have no stated quantity (\"to taste\")")
    if "unknown_quantity" in cats or "optional_unknown_quantity" in cats:
        reasons.append("some ingredients have no stated quantity")
    if "no_usda_portion" in cats:
        reasons.append("some household measures have no USDA weight")
    if "cooking_medium_unknown_amount" in cats:
        reasons.append("the share of a cooking oil, marinade or brine that is eaten is unknown")
    if "proxy_portion_refused" in cats:
        reasons.append("some counted items are matched to substitute records whose item sizes do not apply")
    if cats & {"unresolved_usda", "state_conflict", "preparation_unresolved", "usda_error"}:
        reasons.append("some ingredients could not be matched to a USDA record")
    if "proxy_dependent" in {(s.ineligible_reason or "").split(":")[0] for s in calculated}:
        reasons.append("the complete recipes depend on substitute USDA records for most of a nutrient")
    why = "; ".join(reasons) if reasons else "no relevant recipe could be processed"
    tail = (" Known subtotals cover the other ingredients only and are not totals for the dish." if calculated else "")
    return f"{len(relevant)} comparable recipes were found for {name}, but none could be calculated completely: {why}.{tail} {NO_VALUES if not calculated else NOT_VERIFIED}"


def _amt(value: str | None, nutrient: str) -> str:
    return "unknown" if value is None else display_amount(Decimal(str(value)), nutrient)
