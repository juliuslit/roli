"""Phase 3: one menu photo -> up to three recommendations, with everything behind them kept (SPEC_3_mvp.md sections 2-3).

Local-testing milestone (2026-11-04): dishes are chosen across courses by lean words (selection.py), every model call and live search of a run
goes through one MenuBudget (budget.py), and each menu item keeps its decision (evaluated / excluded / skipped / budget_stopped) with the reason.

    runner = MenuRunner(MvpConfig())                      # real model, Tavily, USDA, caches under .cache/roli_mvp
    run = runner.run("menu.jpg")                          # a MenuRun, also saved as roli_agent/runs/<run_id>/run.json

Reuses the existing components unchanged: the menu reader node, `estimate_dish` (recipe search, extraction, relevance, USDA matching, conversion,
Phase 2A calculation, 2C adaptation, 2D portioning), the 2D intervals and comparison, the Phase 3 ranking. Dishes run in parallel threads; a dish
that fails is recorded and the run continues. Python owns every number and every word a tester reads.
"""

from __future__ import annotations

import io
import os
import json
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from roli_nutrition import AnswerStore, NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

from .. import harness
from ..config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, MENU_PROMPT_VERSION, MODEL_ID, ROOT
from ..llm import RateLimitedLLM, make_chat_model, parse_json_object
from ..nodes import make_read_menu
from ..recipes.adapt import WeightsTable, adapt_pairs
from ..recipes.compare_dishes import ExternalEvidence, compare_dishes, dish_interval, scenario_interval
from ..recipes.extract import ExtractionCache
from ..recipes.fetch import FailedPages, FetchCache, PoliteFetcher
from ..recipes.judgements import JudgementCache, prompt_version
from ..recipes.match import MatchCache
from ..recipes.metrics import CountingTransport, Meter
from ..recipes.models import AdaptedPair, DishComparison, DishInterval, MenuItem, PortionedScenario
from ..recipes.pipeline import TopUp, estimate_dish
from ..recipes.portions import KIDS_SECTIONS, PortionRules, dish_type_for, pair_inputs, portion_scenario, published_input
from ..recipes.plate_weights import PlateWeights
from ..recipes.sampling import PlateSampler, load_frying_fat_prior, make_sampler
from ..recipes.search import CachedSource, TavilySource
from ..recipes.survey import estimate_survey_dish, is_fried_item
from .budget import BudgetedLLM, BudgetedSource, Limits, MenuBudget, Prices, SpendLedger
from .models import DishRun, MenuRun, MvpConfig, Unranked
from .ranking import APART_GROUPS, frying_fat_line, rank_dishes, recommendation_text, unranked_causes
from .readings import SavedReadings
from .reference import FLAG_REASON, KNOWN_LIMIT_REASON, FlagFile, KnownLimits, ReferenceCheck, reference_check, top_contributors
from .dish_kind import DishKindCache, classify_menu
from .selection import candidate_items, kind_label, select_dishes, unsized_kinds  # noqa: F401  (candidate_items re-exported for the Phase 3 callers)

NUTRIENTS = ("saturated_fat_g", "cholesterol_mg")
TELEGRAM_MAX_SIDE = 1280
DEFAULT_CACHE = ROOT / ".cache" / "roli_mvp"
DEFAULT_RUNS = ROOT / "roli_agent" / "runs"
DEFAULT_USDA_STORE = ROOT / ".cache" / "usda_store"
LEDGER_NAME = "spend_ledger.jsonl"
FLAGS_NAME = "flags.jsonl"
RELEASE_CHECK_SECONDS = 24 * 3600               # 12.5.4: detection at app start and once a day while it runs
USDA_UNAVAILABLE_REASON = "USDA was unavailable during this dish (its hourly request limit was reached); the estimate may be incomplete, so the dish is not ranked"


def prepare_photo(data: bytes, dest: Path) -> Path:
    """Save the upload the way Telegram would deliver it: JPEG, longest side 1280 px (the size the menu reader was tested at)."""
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        im.thumbnail((TELEGRAM_MAX_SIDE, TELEGRAM_MAX_SIDE))
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=88)
    return dest




def unique_keys(items: list[MenuItem]) -> list[str]:
    seen: dict[str, int] = {}
    keys = []
    for it in items:
        base = re.sub(r"[^a-z0-9]+", "_", it.name.lower()).strip("_") or "dish"
        seen[base] = seen.get(base, 0) + 1
        keys.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return keys


class MenuRunner:
    def __init__(self, config: MvpConfig | None = None, *, service: Any | None = None, llm: Any | None = None, menu_llm: Any | None = None,
                 read_menu: Callable[[str], dict] | None = None, source_factory: Callable[[], Any] | None = None, fetcher_factory: Callable[[], Any] | None = None,
                 extraction_cache_factory: Callable[[], Any] | None = None, match_cache: MatchCache | None = None, cache_dir: Path = DEFAULT_CACHE,
                 runs_dir: Path = DEFAULT_RUNS, parse_json=parse_json_object, usda_requests: Callable[[], int] | None = None,
                 prices: Prices | None = None, ledger: SpendLedger | None = None, flags: FlagFile | None = None) -> None:
        self.config = config or MvpConfig()
        self.config.adapt_mode = "experimental" if self.config.experimental else "approved"
        self.cache_dir, self.runs_dir = Path(cache_dir), Path(runs_dir)
        self._transport = None
        if service is None:
            settings = Settings.from_env()
            if "ROLI_CACHE_MAX_ENTRIES" not in os.environ:
                settings = replace(settings, cache_max_entries=5000)   # one menu touches far more than 1,000 USDA records; evictions re-fetch and spend the hourly allowance (2026-11-05)
            settings = replace(settings, reserve_requests=self.config.usda_reserve_requests)
            self._transport = CountingTransport()
            # 3D (12.5.1): saved answers on disk, shared by every process; the in-memory cache is only the fast layer
            store = AnswerStore(self.config.usda_store_dir or DEFAULT_USDA_STORE, stale_days=settings.stale_days)
            service = NutritionService(settings, client=UsdaClient(settings.api_key, transport=self._transport, halt_seconds=settings.halt_seconds), store=store)
        self.service = service
        self.usda_requests = usda_requests or (lambda: self._transport.requests if self._transport else 0)
        self.flags = flags if flags is not None else FlagFile(self.runs_dir / FLAGS_NAME)
        self.known_limits = KnownLimits.load()
        self.release_status: dict[str, Any] | None = None
        self._release_checked_at: float | None = None
        # one rate limit for the whole process (OpenRouter: 20 requests per minute per model on this account); a 429 is retried, never fatal to a dish
        self.llm = RateLimitedLLM(llm or make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS), per_minute=self.config.llm_per_minute)
        self.menu_llm = menu_llm or (llm if llm is not None else make_chat_model(timeout=harness.CALL_TIMEOUT_SECONDS))
        if not isinstance(self.menu_llm, RateLimitedLLM):
            self.menu_llm = RateLimitedLLM(self.menu_llm, per_minute=self.config.llm_per_minute)
            self.menu_llm._lock, self.menu_llm._times = self.llm._lock, self.llm._times      # the two wrappers share one budget of requests per minute
        self._read_menu = read_menu
        self.source_factory = source_factory or (lambda: CachedSource(TavilySource(), self.cache_dir / "search"))
        failed_pages = FailedPages(self.cache_dir / "failed_pages.json", sealed=self.config.reuse_saved_reading)     # 12.12.7
        self.fetcher_factory = fetcher_factory or (lambda: PoliteFetcher(cache=FetchCache(self.cache_dir / "pages"), failed_pages=failed_pages))
        self.extraction_cache_factory = extraction_cache_factory or (lambda: ExtractionCache(self.cache_dir / "extractions"))
        self.match_cache = match_cache if match_cache is not None else MatchCache(self.cache_dir / "usda_matches.json")
        self.judgements = JudgementCache(self.cache_dir / "judgements", getattr(self.llm, "model_name", None) or MODEL_ID) if self.config.save_judgements else None
        self.dish_kinds = DishKindCache(self.cache_dir / "judgements", getattr(self.llm, "model_name", None) or MODEL_ID) if self.config.save_judgements else None
        self.readings = SavedReadings(self.cache_dir / "readings", getattr(self.menu_llm, "model_name", None) or MODEL_ID, prompt_version(harness.load_prompt(MENU_PROMPT_VERSION)))
        self.parse_json = parse_json
        self.weights = WeightsTable.load()
        self.rules = PortionRules.load()
        self.evidence = ExternalEvidence.load()
        # 3K (12.20): the band's inputs: measured plate weights per row, the frying-fat prior, the plate-weight model when it is on
        self.plate_weights = PlateWeights.load()
        self.fat_prior = load_frying_fat_prior() if self.config.frying_fat_prior else None
        self.plate_model = None
        if self.config.plate_weight_model is not False:
            from ..recipes.plate_model import PlateModel
            loaded = PlateModel.load()
            if loaded is not None and (self.config.plate_weight_model is True or loaded.live):
                self.plate_model = loaded
        # spending safeguards: limits from the config, the day's spending from the ledger, per-token prices only for estimating unpriced calls
        self.limits = Limits(menu_usd=Decimal(str(self.config.menu_budget_usd)), menu_search_credits=self.config.menu_search_credits,
                             daily_usd=Decimal(str(self.config.daily_budget_usd)), daily_search_credits=self.config.daily_search_credits)
        self.ledger = ledger if ledger is not None else SpendLedger(self.runs_dir / LEDGER_NAME)
        self.prices = prices if prices is not None else Prices.load(getattr(self.llm, "model_name", None) or MODEL_ID, self.cache_dir / "openrouter_prices.json")

    def new_budget(self, run_id: str) -> MenuBudget:
        return MenuBudget(self.limits, self.ledger, self.prices, run_id=run_id)

    # -- USDA access (3D, 12.5) --------------------------------------------------------------------------------------------------

    def usda_status(self) -> dict[str, Any]:
        fn = getattr(self.service, "usda_status", None)
        return fn() if callable(fn) else {}

    def usda_allows(self) -> tuple[bool, str]:
        fn = getattr(self.service, "allowance_ok", None)
        return fn(self.config.usda_reserve_requests) if callable(fn) else (True, "")

    def maybe_check_release(self) -> dict[str, Any] | None:
        """12.5.4: one request per refreshable table at app start and once a day; never when USDA is refusing or the reserve is reached."""
        fn = getattr(self.service, "check_release", None)
        if not self.config.release_check or not callable(fn):
            return None
        now = time.time()
        if self._release_checked_at is not None and now - self._release_checked_at < RELEASE_CHECK_SECONDS:
            return self.release_status
        if not self.usda_allows()[0]:
            return self.release_status
        self._release_checked_at = now
        self.release_status = fn()
        return self.release_status

    # -- the menu ---------------------------------------------------------------------------------------------------------------

    def read_menu(self, photo_path: str, budget: MenuBudget | None = None, *, save: bool = True) -> tuple[dict | None, str | None, str]:
        """(the reader's answer, the error, "fresh" or "saved"). ``save=False`` leaves the saved reading alone: the reader check (12.10.5)."""
        saved = self.readings.get(photo_path) if self.config.reuse_saved_reading else None
        if saved is not None:
            return saved, None, "saved"
        menu, err = self._read_fresh(photo_path, budget)
        if menu is not None and save:
            self.readings.put(photo_path, menu)
        return menu, err, "fresh"

    def _read_fresh(self, photo_path: str, budget: MenuBudget | None = None) -> tuple[dict | None, str | None]:
        if self._read_menu is not None:
            try:
                return self._read_menu(photo_path), None
            except Exception as exc:                        # noqa: BLE001
                return None, f"menu reader failed: {type(exc).__name__}"
        llm = BudgetedLLM(self.menu_llm, budget) if budget is not None else self.menu_llm
        node = make_read_menu(llm, harness.load_prompt)
        try:
            out = node({"photo_path": photo_path, "trace": []})
        except Exception as exc:                            # noqa: BLE001
            return None, f"menu reader failed: {type(exc).__name__}: {str(exc)[:120]}"
        return out.get("menu"), out.get("menu_error")

    # -- one dish ----------------------------------------------------------------------------------------------------------------

    def evaluate_dish(self, key: str, index: int, item: MenuItem, budget: MenuBudget | None = None, *, dish_type: Any = ...) -> DishRun:
        """``dish_type`` is the family selection decided (the dish-kind call's answer when it is on, 12.16.11); left out, the word lists decide, as before 3J."""
        t0 = time.perf_counter()
        dt = dish_type_for(item) if dish_type is ... else dish_type       # 3J bug fix: the family the dish-kind call chose must reach the portion rules, not only the selection
        run = DishRun(key=key, item=item.model_dump(), menu_index=index, status="evaluated", dish_type=dt)
        llm = BudgetedLLM(self.llm, budget) if budget is not None else self.llm
        source = self.source_factory()
        if budget is not None:
            source = BudgetedSource(source, budget)
        try:
            meter = Meter()
            reserve_usd, reserve_credits = Decimal(str(self.config.dish_reserve_usd)), self.config.dish_reserve_credits
            topup = TopUp(min_usable=self.config.min_usable_recipes, extra_fetch=self.config.extra_fetch,
                          allowed=(lambda: budget.reserve_topup(self.config.max_topups_per_menu, reserve_usd, reserve_credits)) if budget is not None else (lambda: True),
                          used=lambda: None)                                # the slot is counted by reserve_topup, atomically across the dish threads
            est = estimate_dish(item, source=source, fetcher=self.fetcher_factory(), service=self.service, llm=llm, parse_json_object=self.parse_json,
                                max_fetch=self.config.max_fetch, match_cache=self.match_cache, meter=meter, extraction_cache=self.extraction_cache_factory(),
                                adapt_mode=self.config.adapt_mode, weights_table=self.weights, portion_rules=self.rules,
                                exclude_herbs_spices=self.config.exclude_herbs_spices, backfill_recipes=self.config.backfill_recipes, survey_measures=self.config.survey_measures,
                                line_tags=self.config.line_tags, low_fat_g_per_100g=self.config.low_fat_g_per_100g, negligible_sat_fat_per_100g=self.config.negligible_sat_fat_per_100g, allow_unsourced_rules=self.config.reference_check,
                                judgements=self.judgements, topup=topup, dish_type=dt)
            est_json = est.model_dump(mode="json")
            run.cost = {k: est_json["cost"].get(k) for k in ("llm_calls", "llm_cost_usd", "search_credits", "usda_lookups", "usda_portion_lookups", "pages_fetched", "pages_from_cache", "seconds", "stage_seconds")}
            run.n_scenarios = sum(1 for s in est.scenarios if s.status == "calculated")
            if budget is not None and budget.tripped_in_this_thread():
                # a limit stopped a model call or a search inside this dish: the stages after it ran degraded (grading or matching caught the error)
                run.status, run.reason = "budget_stopped", "a spending limit stopped this dish part-way: " + "; ".join(budget.interruptions[-1:])
                run.estimate = est_json
                run.seconds = round(time.perf_counter() - t0, 1)
                return run
            if run.n_scenarios == 0:
                failures = [n for n in est.notes if "failed" in n or "unavailable" in n]        # ingestion catches a search outage and says so in its notes
                run.status, run.reason = "no_recipes", ("; ".join(failures)[:200] + ": " if failures else "") + est.summary.statement[:300]
            pairs = {p.derived_from: p for p in est.adapted_pairs}
            portioned_pub = {p.derived_from: p for p in est.portioned if p.input_kind == "published"}
            portioned_pair = {p.derived_from.removesuffix("::adapted"): p for p in est.portioned if p.input_kind == "adapted_pair"}
            run.n_portioned = sum(1 for p in est.portioned if p.applicable)
            survey = None
            if self.config.survey_fried_dishes and is_fried_item(item):
                survey = estimate_survey_dish(item, dt, service=self.service, rules=self.rules, weights=self.weights, slug=key)
                run.survey_dish = survey.model_dump(mode="json")
            # 3K (12.20): the band sampler: recipes weighted by relevance grade and menu coverage, plate weights from the measured samples behind the row
            grade_of = {s.scenario_id: s.relevance.grade for s in est.scenarios}
            coverage_of = {s.scenario_id: s.relevance.menu_coverage for s in est.scenarios}
            plates = PlateSampler(self.plate_weights, n_min=self.config.plate_samples_min, model=self.plate_model, dish_words=f"{item.name} {item.description}", section=item.section, family=dt)
            sampler = make_sampler(plates, draws=self.config.band_draws, grade_of=grade_of, coverage_of=coverage_of, outlier_factor=float(self.config.recipe_outlier_factor),
                                   fat_prior=self.fat_prior, medium_weight=float(self.config.grade_weight_medium), q_low=float(self.config.band_low_q), q_high=float(self.config.band_high_q))
            for n in NUTRIENTS:
                ivs, no_portion = [], 0
                for s in est.scenarios:
                    if s.status != "calculated":
                        continue
                    iv = scenario_interval(s, pairs.get(s.scenario_id), portioned_pub.get(s.scenario_id), portioned_pair.get(s.scenario_id), n, self.evidence)
                    if iv is None:
                        no_portion += 1
                    else:
                        ivs.append(iv)
                if survey is not None and survey.applicable and survey.interval(n) is not None:
                    ivs.append(survey.interval(n))
                run.intervals[n] = dish_interval(key, n, ivs, no_portion, sampler=sampler).model_dump(mode="json")
            run.estimate = est_json
            # 3D (12.5.2): a dish USDA refused during is not ranked; (12.1): the reference check against the dish-family card, before ranking
            if _usda_rate_limited(run) or self.usda_status().get("halted"):
                run.status, run.reason = "usda_unavailable", USDA_UNAVAILABLE_REASON
            elif self.config.reference_check:
                sat = DishInterval.model_validate(run.intervals["saturated_fat_g"])
                card = self.rules.card_for(dt, f"{item.name} {item.description}")
                check = reference_check(sat, card, factor=self.config.reference_check_factor, min_figures=self.config.reference_min_figures, vegetable_max=self.config.fried_sat_share_vegetable_max,
                                        animal_min=self.config.fried_sat_share_animal_min, choice_ranges=survey.choice_ranges if survey is not None and survey.applicable else None,
                                        fat_bands=sat.fat_bands or None)
                if check.flagged:
                    check.top_contributors = top_contributors(run.intervals["saturated_fat_g"], est_json, run.survey_dish)
                    check.known_limit = self.known_limits.find(dt, check.top_contributors)
                    run.status, run.reason = "flagged", f"{KNOWN_LIMIT_REASON}: {check.known_limit['reason']}" if check.known_limit else FLAG_REASON
                run.reference = check.model_dump(mode="json")
        except Exception as exc:                            # noqa: BLE001  a dish never takes the menu down
            if budget is not None and budget.tripped_in_this_thread():
                run.status, run.reason = "budget_stopped", f"a spending limit stopped this dish: {str(exc)[:200]}"
            else:
                run.status, run.reason = "error", f"{type(exc).__name__}: {str(exc)[:200]}"
        run.seconds = round(time.perf_counter() - t0, 1)
        return run

    # -- the run -----------------------------------------------------------------------------------------------------------------

    def run(self, photo_path: str | Path, *, run_id: str | None = None, progress: Callable[[str], None] | None = None) -> MenuRun:
        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        say = progress or (lambda msg: None)
        t_all = time.perf_counter()
        mr = MenuRun(run_id=run_id, created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), config=self.config, photo=str(photo_path))
        budget = self.new_budget(run_id)
        try:
            return self._run(mr, photo_path, budget, say, t_all)
        finally:
            budget.close()

    def _run(self, mr: MenuRun, photo_path, budget: MenuBudget, say, t_all: float) -> MenuRun:
        usda_before = self.usda_requests()
        release = self.maybe_check_release()
        status0 = self.usda_status()
        if status0.get("remaining") is not None:
            say(f"USDA allowance: {status0['remaining']} of {status0.get('limit')} requests left this hour (reserve {self.config.usda_reserve_requests})")
        say("reading the menu photo")
        t0 = time.perf_counter()
        menu, err, mr.reading = self.read_menu(str(photo_path), budget)
        mr.timings["read_menu"] = round(time.perf_counter() - t0, 1)
        mr.menu, mr.menu_error = menu, err
        if menu is None:
            mr.status, mr.recommendation = "failed", f"Roli could not read the menu photo ({err}). No recommendation is possible."
            mr.recommendation_words = len(mr.recommendation.split())
            mr.errors.append(err or "menu unreadable")
            mr.spend = budget.report()
            self.save(mr)
            return mr
        kinds = None
        if self.config.dish_kind_model:                   # 12.16.11: one call per menu; the word lists answer for anything it does not
            kinds, kind_log = classify_menu(menu.get("items") or [], BudgetedLLM(self.llm, budget), self.parse_json, cache=self.dish_kinds)
            mr.dish_kind_log = kind_log
            say(f"dish kinds: {kind_log}")
        cands = select_dishes(menu, self.config.max_dishes, kinds)
        for c in cands:
            k = kinds.get(c.index) if kinds else None
            if k is not None:
                c.kind = {"family": k.family, "source": k.source, "model_kind": k.model_kind, "reason": k.reason, "note": k.note}
        chosen = [(c.index, c.item) for c in cands if c.decision == "selected"]
        by_index = {c.index: c for c in cands}
        keys = unique_keys([it for _, it in chosen])
        for c in cands:
            if c.decision != "selected":
                mr.dishes.append(DishRun(key=unique_keys([c.item])[0] + f"_{c.index}", item=c.item.model_dump(), menu_index=c.index, status=c.decision,
                                         reason=c.reason, dish_type=c.dish_type, selection=c.selection()))
        n_candidates = sum(1 for c in cands if c.decision in ("selected", "skipped"))
        say(f"menu read: {len(menu.get('items', []))} items, {n_candidates} candidate dishes; evaluating {len(chosen)} across courses with {self.config.workers} workers "
            f"(budget ${self.limits.menu_usd} model calls, {self.limits.menu_search_credits} search credits)")
        t0 = time.perf_counter()
        results: dict[str, DishRun] = {}
        lock = threading.Lock()
        reserve_usd, reserve_credits = Decimal(str(self.config.dish_reserve_usd)), self.config.dish_reserve_credits

        def work(args):
            key, (i, it) = args
            c = by_index[i]
            ok, why = budget.allows_dish(reserve_usd, reserve_credits)
            if ok:
                ok, why = self.usda_allows()                    # 12.5.3: pause before the reserve; 12.5.2: nothing starts after a refusal
            if not ok:
                dr = DishRun(key=key, item=it.model_dump(), menu_index=i, status="skipped", reason=f"skipped before it started, {why}", dish_type=c.dish_type, selection=c.selection())
                say(f"skipped {it.name}: {why}")
            else:
                say(f"estimating {it.name}")
                dr = self.evaluate_dish(key, i, it, budget, dish_type=c.dish_type)
                dr.selection = c.selection()
                rep = budget.report()
                say(f"done {it.name}: {dr.status} ({dr.seconds} s, {dr.n_scenarios} recipes, {dr.n_portioned} portioned); spent ${rep['model_usd_total'][:6]} of ${self.limits.menu_usd}, "
                    f"{rep['search_credits']} credits")
            with lock:
                results[key] = dr
            return dr

        with ThreadPoolExecutor(max_workers=max(1, self.config.workers)) as pool:
            list(pool.map(work, zip(keys, chosen)))
        mr.timings["estimate_dishes"] = round(time.perf_counter() - t0, 1)
        mr.dishes.extend(results[k] for k in keys)
        mr.dishes.sort(key=lambda d: d.menu_index)

        # comparison and ranking over the evaluated dishes
        t0 = time.perf_counter()
        evaluated = [d for d in mr.dishes if d.status == "evaluated"]
        names = {d.key: d.item["name"] for d in evaluated}
        per = {n: {} for n in NUTRIENTS}
        for d in evaluated:
            for n in NUTRIENTS:
                per[n][d.key] = DishInterval.model_validate(d.intervals[n])
        comparison = compare_dishes(per) if evaluated else DishComparison()
        ranked, unranked = rank_dishes(comparison, names)
        apart = {d.key: APART_GROUPS[d.dish_type] for d in mr.dishes if d.dish_type in APART_GROUPS}    # 12.18 (12.14.4 generalised): sides, soups, dips, desserts, snacks and kids' dishes after the mains, never in the top three
        ranked = [r for r in ranked if r.key not in apart] + [r for r in ranked if r.key in apart]
        for i, r in enumerate(ranked, start=1):
            r.rank, r.listed_apart, r.snack = i, apart.get(r.key), apart.get(r.key) == "snack"
        kids_section = any(KIDS_SECTIONS.search(str(it.get("section") or "")) for it in (menu.get("items") or []) if isinstance(it, dict))
        # 3D: flagged and USDA-unavailable dishes are listed with the dishes not estimated, with the reason (12.1.3)
        unranked += [Unranked(key=d.key, name=d.item["name"], reason=d.reason or "") for d in mr.dishes if d.status in ("flagged", "usda_unavailable")]
        fat_lines = {d.key: frying_fat_line(d.item["name"], (d.survey_dish or {}).get("choice_ranges") or {}, (d.intervals.get("saturated_fat_g") or {}).get("fat_bands") or None) for d in mr.dishes}
        for row in (*ranked, *unranked):
            row.fat_line = fat_lines.get(row.key)
        mr.comparison = comparison.model_dump(mode="json")
        mr.ranking, mr.unranked = ranked, unranked
        menu_name = Path(str(photo_path)).name
        for d in mr.dishes:
            if d.reference is None:
                continue
            check = ReferenceCheck.model_validate(d.reference)
            if d.status == "flagged":
                mr.flags.append(self.flags.raise_flag(run_id=mr.run_id, menu=menu_name, dish=d.item["name"], dish_type=d.dish_type, check=check))
            elif check.checked and not check.flagged:
                closed = self.flags.close_flag(run_id=mr.run_id, menu=menu_name, dish=d.item["name"], check=check)
                if closed:
                    mr.flags.append(closed)
        n_skipped = sum(1 for d in mr.dishes if d.status == "skipped")
        n_stopped = sum(1 for d in mr.dishes if d.status == "budget_stopped")
        n_considered = n_candidates
        n_unestimated = len(chosen) - n_skipped_in_run(mr) - len(ranked)
        n_food = sum(1 for c in cands if not c.reason.startswith("excluded: not a dish") and c.reason != "excluded: an option of another item")
        kinds_by_key = {d.key: kind_label(MenuItem(name=d.item.get("name", ""), description=d.item.get("description", ""), section=d.item.get("section", ""))) for d in mr.dishes}
        causes = unranked_causes(unranked, kinds_by_key)
        n_no_recipe = sum(1 for d in mr.dishes if d.status == "no_recipes")
        n_failed = sum(1 for d in mr.dishes if d.status in ("error", "usda_unavailable"))
        causes += ([f"{n_no_recipe} had no usable recipe"] if n_no_recipe else []) + ([f"{n_failed} failed with an error"] if n_failed else [])
        mr.recommendation, mr.recommendation_words = recommendation_text(ranked, len(evaluated), n_considered, n_unestimated, n_skipped=n_skipped, n_stopped=n_stopped,
                                                                         unsized_kinds=unsized_kinds(cands), n_food=n_food, causes=causes, kids_section=kids_section)
        mr.timings["compare_and_rank"] = round(time.perf_counter() - t0, 3)
        mr.timings["total"] = round(time.perf_counter() - t_all, 1)
        mr.spend = budget.report()
        mr.totals = {
            "dishes_on_menu": len(menu.get("items", [])), "dishes_candidates": n_candidates, "dishes_selected": len(chosen), "dishes_evaluated": len(evaluated),
            "dishes_ranked": len(ranked), "dishes_unranked": len(unranked), "dishes_no_recipes": sum(1 for d in mr.dishes if d.status == "no_recipes"),
            "dishes_error": sum(1 for d in mr.dishes if d.status == "error"), "dishes_excluded": sum(1 for d in mr.dishes if d.status in ("excluded", "not_evaluated")),
            "dishes_skipped": n_skipped, "dishes_budget_stopped": n_stopped,
            "search_credits": mr.spend["search_credits"], "llm_calls": mr.spend["model_calls"],
            "llm_cost_usd": mr.spend["model_usd_total"], "llm_cost_usd_actual": mr.spend["model_usd_actual"], "llm_cost_usd_estimated": mr.spend["model_usd_estimated"],
            "usda_http_requests": self.usda_requests() - usda_before, "pages_fetched": sum(int(d.cost.get("pages_fetched") or 0) for d in mr.dishes),
            "rate_limit_waits": self.llm.waits + self.menu_llm.waits, "rate_limit_retries": self.llm.retries + self.menu_llm.retries,
        }
        mr.errors.extend(f"{d.item['name']}: {d.reason}" for d in mr.dishes if d.status in ("error", "budget_stopped", "usda_unavailable") or (d.status == "no_recipes" and "failed" in (d.reason or "")))
        limited = [d.item["name"] for d in mr.dishes if _usda_rate_limited(d)]
        if limited:
            mr.errors.append(f"USDA FoodData Central refused requests (this key's limit is 3,600 per rolling hour) during {len(limited)} dish(es): {', '.join(limited[:5])}. "
                             f"Their estimates may be incomplete; wait before the next menu.")
        mr.errors.extend(f"budget: {x}" for x in budget.interruptions)
        status1 = self.usda_status()
        mr.usda = {"requests": self.usda_requests() - usda_before, "remaining_before": status0.get("remaining"), "remaining_after": status1.get("remaining"), "limit": status1.get("limit"),
                   "halted": status1.get("halted"), "reserve": self.config.usda_reserve_requests, "store_hits": status1.get("store_hits"), "store_misses": status1.get("store_misses"),
                   "release": status1.get("release") or {}, "release_check": release, "dishes_usda_unavailable": sum(1 for d in mr.dishes if d.status == "usda_unavailable"),
                   "dishes_flagged": sum(1 for d in mr.dishes if d.status == "flagged" and not (d.reference or {}).get("known_limit"))}
        mr.totals["dishes_flagged"] = mr.usda["dishes_flagged"]
        mr.totals["dishes_known_limit"] = sum(1 for d in mr.dishes if d.status == "flagged" and (d.reference or {}).get("known_limit"))
        mr.totals["dishes_usda_unavailable"] = mr.usda["dishes_usda_unavailable"]
        mr.status = "done"
        self.save(mr)
        say("done")
        return mr

    def save(self, mr: MenuRun) -> Path:
        folder = self.runs_dir / mr.run_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "run.json"
        path.write_text(mr.model_dump_json(indent=1), encoding="utf-8")
        return path


def _usda_rate_limited(d: DishRun) -> bool:
    """USDA answered 429 somewhere in this dish: a match note, a D25 or Survey lookup, or the fried-dish estimate's reason."""
    if d.status == "usda_unavailable":
        return True
    texts = [n for n in ((d.estimate or {}).get("notes") or [])] + [str((d.survey_dish or {}).get("reason") or "")]
    texts += [str(c.get("choice") or "") + str(c.get("problem") or "") for c in ((d.survey_dish or {}).get("components") or [])]
    return any("rate_limited" in t for t in texts)


def n_skipped_in_run(mr: MenuRun) -> int:
    """Selected dishes that never started (budget pre-check): they are neither estimated nor 'could not be estimated'."""
    return sum(1 for d in mr.dishes if d.status == "skipped" and "before it started" in (d.reason or ""))


def load_run(runs_dir: Path, run_id: str) -> MenuRun | None:
    path = Path(runs_dir) / run_id / "run.json"
    if not path.exists():
        return None
    return MenuRun.model_validate_json(path.read_text(encoding="utf-8"))
