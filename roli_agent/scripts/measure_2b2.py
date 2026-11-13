"""Phase 2B-2 live measurement (spec 2B section 12; requirements 7 and 8): the five Flour + Water dishes through the
whole pipeline, once cold and once warm, with per-stage seconds, LLM calls/tokens/cost, USDA calls and HTTP requests.

    .venv/bin/python -m roli_agent.scripts.measure_2b2 [--out roli_agent/eval] [--cache-dir .cache/roli_recipes_2b2]

Cold: empty page cache, empty search cache, empty match cache, cold USDA service cache (a fresh process). Warm: the same
caches after the cold run, in the same process. Writes <out>/2b2_live_<date>.json with every DishEstimate and a markdown report.
Costs about 10 Tavily credits (cold run only) and a few hundred USDA requests; pages are fetched politely.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from roli_nutrition import NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

from roli_agent.config import BATCH_ANSWER_TOKENS, BATCH_TIMEOUT_SECONDS, ROOT
from roli_agent.llm import make_chat_model
from roli_agent.recipes.extract import ExtractionCache
from roli_agent.recipes.fetch import FetchCache, PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.metrics import CountingTransport, Meter
from roli_agent.recipes.adapt import WeightsTable, adapt_pairs
from roli_agent.recipes.ingest import ingest_dish
from roli_agent.recipes.pipeline import estimate_dish
from roli_agent.recipes.portions import PortionRules, pair_inputs, portion_scenario, published_input
from roli_agent.recipes.search import CachedSource, TavilySource
from roli_agent.scripts.ingest_report_2b1 import DISHES, slug


def run_all(label: str, cache_dir: Path, llm, service, transport: CountingTransport, out: dict, adapt: bool = False, portion: bool = False) -> None:
    source = CachedSource(TavilySource(), cache_dir / "search")
    fetcher = PoliteFetcher(cache=FetchCache(cache_dir / "pages"))
    match_cache = MatchCache(cache_dir / "usda_matches.json")
    extraction_cache = ExtractionCache(cache_dir / "extractions")
    for item in DISHES:
        before = transport.requests
        meter = Meter()
        t = time.perf_counter()
        rules = PortionRules.load() if portion else None
        ingestion = None
        if portion:
            # 2D needs the pages' method text for the experimental pairs below, and the estimate does not keep it: ingest first, then pass it in.
            # The extraction cache answers every page, so this costs no model call; the time is recorded as stage "ingest" by hand.
            t_ing = time.perf_counter()
            ingestion = ingest_dish(item, source=source, fetcher=fetcher, llm=llm, extraction_cache=extraction_cache)
            ingest_seconds = round(time.perf_counter() - t_ing, 3)
        est = estimate_dish(item, source=source, fetcher=fetcher, service=service, llm=llm, match_cache=match_cache, meter=meter,
                            usda_http_requests=lambda: transport.requests - before, extraction_cache=extraction_cache,
                            adapt_mode="approved" if adapt else "off", portion_rules=rules, ingestion=ingestion)
        est_json = est.model_dump(mode="json")
        if ingestion is not None:
            est_json["cost"]["stage_seconds"]["ingest"] = ingest_seconds
        recipes_by_url = {r.canonical_url: r for r in (ingestion.recipes if ingestion else [])}
        if adapt:                                                  # Phase 2C: the experimental diagnostic on the SAME published scenarios
            exp_pairs, exp_summary = adapt_pairs(est.scenarios, service=service, table=WeightsTable.load(), mode="experimental")
            est_json["experimental"] = {"adapted_pairs": [p.model_dump(mode="json") for p in exp_pairs], "internal_summary": exp_summary.model_dump(mode="json")}
            print(f"    2C approved:     {est.internal_summary.statement}")
            print(f"    2C experimental: {exp_summary.statement}")
            if portion:                                             # Phase 2D on the experimental pairs too (internal), timed separately
                from roli_nutrition.recipe import RecipeCalculator
                t2 = time.perf_counter()
                calc = RecipeCalculator(service)
                exp_portioned = []
                for pair in exp_pairs:
                    sc = next(x for x in est.scenarios if x.scenario_id == pair.derived_from)
                    inputs = pair_inputs(pair, sc)
                    if inputs is not None:
                        # method text is not kept on the estimate; the portion models read it from the ingestion result's recipes
                        r = recipes_by_url.get(sc.source.canonical_url)
                        exp_portioned.append(portion_scenario(inputs, item=item, rules=rules, calculator=calc, yield_text=sc.source.yield_text,
                                                              method_text=r.instructions_text if r else "").model_dump(mode="json"))
                est_json["experimental"]["portioned"] = exp_portioned
                est_json["cost"]["stage_seconds"]["portion_experimental"] = round(time.perf_counter() - t2, 3)
                print(f"    2D: {sum(1 for p in est.portioned if p.applicable)} of {len(est.portioned)} published scenarios / approved pairs portioned; "
                      f"{sum(1 for p in exp_portioned if p['applicable'])} of {len(exp_portioned)} experimental pairs portioned; stages {est_json['cost']['stage_seconds']}")
        est_json["cost"]["search_cache_hits"] = source.hits
        out[label][slug(item.name)] = est_json
        s, c = est.summary, est.cost
        print(f"\n## [{label}] {item.name}: {time.perf_counter() - t:.1f} s | recipes {s.n_distinct} read, {s.n_gate_passed} gate, {s.n_relevant} relevant, "
              f"{s.n_calculated} calculated, {s.n_complete} complete, {s.n_eligible} eligible | LLM {c.llm_calls} calls "
              f"{c.llm_prompt_tokens}+{c.llm_completion_tokens} tok cost {c.llm_cost_usd} | USDA {c.usda_searches} searches, {c.usda_lookups} lookups, "
              f"{c.usda_portion_lookups} portions, {c.usda_http_requests} HTTP | match cache hits {c.match_cache_hits} | stages {c.stage_seconds}")
        print("   ", s.statement)
        print("    exclusions:", s.exclusion_reasons, "| blocked only by seasonings:", s.blocked_only_by_seasonings,
              "| only menu-only:", s.blocked_only_by_menu_only, "| both:", s.blocked_only_by_seasonings_and_menu_only)
        for sc in est.scenarios:
            if sc.status == "calculated":
                d = sc.calculation["display"]
                print(f"    - {sc.source.title[:45]!r} ({sc.source.host}) grade={sc.relevance.grade} {sc.calculation_status} rep={sc.representativeness} "
                      f"eligible={sc.eligible_for_range} matches={sc.match_counts} blockers={sc.blockers} | sat {d['saturated_fat_g']} | chol {d['cholesterol_mg']}")
            else:
                print(f"    - {sc.source.title[:45]!r} ({sc.source.host}) {sc.status}: {sc.status_reason}")
        for n in est.notes:
            print("    note:", n)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "roli_agent" / "eval"))
    parser.add_argument("--cache-dir", default=str(ROOT / ".cache" / "roli_recipes_2b2"))
    parser.add_argument("--keep-cache", action="store_true", help="do not empty the cache directory first (the first run is then not cold)")
    parser.add_argument("--adapt", action="store_true", help="Phase 2C: build menu-adapted pairs in approved mode and, on the same scenarios, in experimental mode")
    parser.add_argument("--cold-only", action="store_true", help="skip the warm pass")
    parser.add_argument("--tag", default="", help="suffix for the output file name")
    parser.add_argument("--portion", action="store_true", help="Phase 2D: run the restaurant portion models on published scenarios, approved pairs and experimental pairs (internal)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    cache_dir = Path(args.cache_dir)
    if not args.keep_cache and cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    transport = CountingTransport()
    settings = Settings.from_env()
    service = NutritionService(settings, client=UsdaClient(settings.api_key, transport=transport))
    llm = make_chat_model(max_tokens=BATCH_ANSWER_TOKENS, timeout=BATCH_TIMEOUT_SECONDS)
    out: dict = {"date": str(date.today()), "model": llm.model_name, "cold": {}, "warm": {}}
    run_all("cold", cache_dir, llm, service, transport, out, adapt=args.adapt, portion=args.portion)
    if not args.cold_only:
        run_all("warm", cache_dir, llm, service, transport, out, adapt=args.adapt, portion=args.portion)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"2b2_live_{date.today()}{args.tag}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("\nwritten:", path, "| total USDA HTTP requests:", transport.requests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
