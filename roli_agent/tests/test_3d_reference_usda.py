"""Checkpoint 3D: the reference check and the flag file (12.1), and USDA access in the runner (12.5): a flagged dish leaves the ranking and comes back
when its cause is fixed; a dish USDA refused is not ranked and nothing more is asked; the reserve pauses dishes; saved answers make a rerun free;
release detection runs once at start. No network."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import httpx

from roli_nutrition import AnswerStore, NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

from roli_agent.llm import parse_json_object
from roli_agent.mvp.menu_run import MenuRunner, prepare_photo
from roli_agent.mvp.models import MvpConfig
from roli_agent.mvp.reference import FLAG_REASON, FlagFile, reference_check
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import DishInterval, ScenarioInterval
from roli_agent.recipes.portions import PortionRule, PortionRules

from conftest import SENTINEL_KEY, Recorder
from recipe_test_helpers import FakeSource
from test_3d_tags_cards import FOODS, OLIVE_PAGE, SEARCHES, TAGS, TaggingLLM
from test_mvp import photo_bytes
from test_recipes_fetch_search import Site

D = Decimal
RULES = PortionRules.load()


def iv(low, high, mass=(50, 100), tier="modeled_range_complete"):
    return ScenarioInterval(scenario_id="s", nutrient="saturated_fat_g", tier=tier, low=D(low), high=D(high), served_mass_low=D(mass[0]) if mass else None, served_mass_high=D(mass[1]) if mass else None)


def dish(low, high, mass=(50, 100)):
    return DishInterval(dish="d", nutrient="saturated_fat_g", low=D(low), high=D(high), bounded=True, n_scenarios=1, n_bounded=1, scenarios=[iv(low, high, mass)])


# -- 12.1: the check ---------------------------------------------------------------------------------------------------------------


def by(check, basis, choice=""):
    return next(c for c in check.comparisons if c.basis == basis and c.choice == choice)


def test_reference_check_flags_above_only_notes_below_with_the_factor_as_a_setting():
    card = RULES.card_for("snack_bowl", "marinated olives")                                   # per 100 g 1.7-2.8 from five brands; per plate 1.4 from one chain
    ok = reference_check(dish("1.2", "2.4"), card, factor=D("1.5"))                          # per 100 g 1.8 / 75 x 100 = 2.4 (allowed 1.13-4.2)
    assert ok.checked and not ok.flagged and ok.card_id == "PR13" and by(ok, "per_100g").roli_middle == D("2.400") and by(ok, "per_100g").independent_figures == 5
    assert (ok.served_mass_low, ok.served_mass_high) == (D(50), D(100)) and by(ok, "per_100g").allowed_high == D("4.2")
    high = reference_check(dish("4.8", "19.3"), card, factor=D("1.5"))                       # the Zuni olives of 3C
    assert high.flagged and [c.basis for c in high.failed] == ["per_100g"] and by(high, "per_100g").direction == "above"
    low = reference_check(dish("0.2", "0.4"), card, factor=D("1.5"))
    assert not low.flagged and low.below_published and by(low, "per_100g").direction == "below" and not by(low, "per_100g").failed     # 12.18: below is noted, never flagged
    assert by(low, "per_100g").note == "below the published range for this kind of dish; plain recipe"
    wide = reference_check(dish("4.8", "19.3"), card, factor=D("10"))                        # the factor is a setting: at x10 nothing is flagged
    assert not wide.flagged and wide.factor == D(10)


def test_reference_check_skips_what_it_cannot_compare_and_says_so():
    assert reference_check(dish("1", "2"), None, factor=D("1.5")).reason_unchecked.startswith("no reference: no dish-family card")
    no_mass = reference_check(dish("1.2", "2.4", mass=None), RULES.card_for("snack_bowl", "olives"), factor=D("1.5"))
    assert not by(no_mass, "per_100g").checked and "served mass unknown" in by(no_mass, "per_100g").note and not no_mass.flagged
    fc = RULES.card_for("fish_and_chips", "fish & chips")
    unbounded = DishInterval(dish="d", nutrient="saturated_fat_g", low=D(1), high=None, bounded=False, n_scenarios=1, n_bounded=0)
    assert "no range to check" in reference_check(unbounded, fc, factor=D("1.5")).reason_unchecked
    pr02 = next(r for r in RULES.rows if r.id == "PR02")
    bare = PortionRule({"id": "PRX", "dish_type": "x", "model": "P2", "low": "1", "high": "2"})
    assert "no published figure" in reference_check(dish("1", "2"), bare, factor=D("1.5")).reason_unchecked


def test_flag_file_opens_and_closes_by_menu_and_dish(tmp_path):
    f = FlagFile(tmp_path / "flags.jsonl")
    card = RULES.card_for("snack_bowl", "olives")
    bad = reference_check(dish("4.8", "19.3"), card, factor=D("1.5"))
    bad.top_contributors = [{"line": "olive oil", "sat_fat_g": "9.00", "share_of_middle": "0.75"}]
    row = f.raise_flag(run_id="r1", menu="menu_01.jpg", dish="Marinated olives", dish_type="snack_bowl", check=bad)
    assert row["status"] == "open" and row["comparison"] == "per_100g" and row["published_high"] == "2.8" and row["top_contributors"][0]["line"] == "olive oil" and "suspected_question" not in row
    assert list(f.open_flags()) == [("menu_01.jpg", "Marinated olives")]
    good = reference_check(dish("1.2", "2.4"), card, factor=D("1.5"))
    assert f.close_flag(run_id="r2", menu="menu_02.jpg", dish="Marinated olives", check=good) is None                       # another menu: nothing to close
    closed = f.close_flag(run_id="r2", menu="menu_01.jpg", dish="Marinated olives", check=good)
    assert closed["status"] == "closed" and "every check that may flag now passes" in closed["note"] and f.open_flags() == {}
    lines = [json.loads(l) for l in (tmp_path / "flags.jsonl").read_text().splitlines()]
    assert [l["status"] for l in lines] == ["open", "closed"] and FlagFile(None).open_flags() == {}


# -- the runner: flags, USDA refusal, the reserve, saved answers, release detection -----------------------------------------------------


MENU = {"readable": "yes", "problems": "", "items": [{"section": "BAR SNACKS", "category": "food", "name": "MARINATED OLIVES", "description": "", "price": "5"}]}
PAGES = {"https://a.test/olives": OLIVE_PAGE}
LIST_ROW = [{"fdcId": 1, "description": "newest", "dataType": "Foundation", "publicationDate": "2026-10-29"}]


def usda_responder(remaining: list[int], *, refuse_after: int | None = None):
    def respond(request: httpx.Request) -> httpx.Response:
        remaining[0] -= 1
        headers = {"x-ratelimit-limit": "3600", "x-ratelimit-remaining": str(max(remaining[0], 0))}
        if refuse_after is not None and remaining[0] < refuse_after:
            return httpx.Response(429, content=b"", headers=headers)
        if request.url.path.endswith("/foods/list"):
            return httpx.Response(200, json=LIST_ROW, headers=headers)
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = SEARCHES.get(q, [])
            return httpx.Response(200, json={"totalHits": len(ids), "foods": [{"fdcId": f, "description": FOODS[f]["description"], "dataType": FOODS[f]["dataType"]} for f in ids]}, headers=headers)
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=FOODS[fid], headers=headers) if fid in FOODS else httpx.Response(404, content=b"", headers=headers)
    return respond


def make_runner(tmp_path: Path, remaining: list[int], *, refuse_after=None, store=True, llm=None, **cfg) -> tuple[MenuRunner, Recorder]:
    rec = Recorder(usda_responder(remaining, refuse_after=refuse_after))
    client = UsdaClient(SENTINEL_KEY, transport=httpx.MockTransport(rec), sleep=lambda s: None, halt_seconds=3600)
    service = NutritionService(Settings(api_key=SENTINEL_KEY, reserve_requests=cfg.get("usda_reserve_requests", 200)), client=client,
                               store=AnswerStore(tmp_path / "usda_store") if store else None)
    runner = MenuRunner(MvpConfig(workers=1, max_dishes=4, **cfg), service=service, llm=llm or TaggingLLM(TAGS), read_menu=lambda p: MENU,
                        source_factory=lambda: FakeSource({"open": [{"url": u, "title": ""} for u in PAGES], "structured_hosts": []}),
                        fetcher_factory=lambda: PoliteFetcher(transport=httpx.MockTransport(Site(pages=PAGES)), sleep=lambda s: None), extraction_cache_factory=lambda: None,
                        match_cache=MatchCache(None), cache_dir=tmp_path / "cache", runs_dir=tmp_path / "runs", parse_json=parse_json_object,
                        usda_requests=lambda: len(rec.requests))
    return runner, rec


def test_the_marinated_olives_pass_the_check_rank_and_record_usda_figures(tmp_path):
    """With the oil a medium and W09 for what clings, the bowl passes per 100 g; the plate figure comes from one chain, so it is shown and cannot flag (12.9.6)."""
    remaining = [3000]
    runner, rec = make_runner(tmp_path, remaining)
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    ref = d.reference
    assert d.status == "evaluated" and d.dish_type == "snack_bowl" and ref["card_id"] == "PR13" and ref["checked"] and not ref["flagged"], ref
    plate = next(c for c in ref["comparisons"] if c["basis"] == "per_plate")
    assert plate["checked"] is False and "1 independent figure" in plate["note"] and plate["roli_middle"] is not None
    assert (ref["served_mass_low"], ref["served_mass_high"]) == ("50", "100")
    assert run.ranking[0].name == "MARINATED OLIVES" and D(run.ranking[0].saturated_fat_high) < D(5) and run.flags == []
    # USDA figures on the run: requests, the remaining count from the headers, the release detected once at start (one request per refreshable table)
    assert run.usda["requests"] == len(rec.requests) and run.usda["remaining_after"] == remaining[0] and run.usda["limit"] == 3600 and run.usda["halted"] is False
    assert run.usda["release"]["Foundation"]["latest_publication_date"] == "2026-10-29" and run.usda["release_check"]["requests"] == 2
    assert sum(1 for r in rec.requests if r.url.path.endswith("/foods/list")) == 2
    assert run.totals["dishes_flagged"] == 0 and "USDA FoodData Central" not in " ".join(run.errors)


def test_a_rerun_on_the_saved_store_makes_no_usda_request_and_the_release_check_runs_once(tmp_path):
    remaining = [3000]
    runner, rec = make_runner(tmp_path, remaining)
    runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    first = len(rec.requests)
    assert first > 2
    run2 = runner.run(tmp_path / "menu.jpg", run_id="r2")                                            # same process: memory cache and store; no second release check
    assert len(rec.requests) == first and run2.usda["requests"] == 0 and run2.ranking
    runner2, rec2 = make_runner(tmp_path, remaining, release_check=False)                           # a new process: empty memory, the same store on disk
    run3 = runner2.run(tmp_path / "menu.jpg", run_id="r3")
    assert rec2.requests == [] and run3.usda["requests"] == 0 and run3.usda["store_hits"] > 0 and run3.ranking[0].name == "MARINATED OLIVES"


def test_a_usda_refusal_marks_the_dish_unavailable_and_nothing_more_is_asked(tmp_path):
    remaining = [3000]
    runner, rec = make_runner(tmp_path, remaining, refuse_after=2996, store=False)                   # the 5th request is refused
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.status == "usda_unavailable" and "not ranked" in d.reason and run.ranking == [] and [u.name for u in run.unranked] == ["MARINATED OLIVES"]
    assert run.usda["halted"] is True and run.usda["dishes_usda_unavailable"] == 1
    refused = [r for r in rec.requests]
    assert len(refused) == 5                                                                           # 4 answered, the 5th refused, then nothing: the client is halted
    assert any("USDA FoodData Central refused requests" in e for e in run.errors)


def test_the_reserve_pauses_dishes_before_they_start(tmp_path):
    remaining = [3000]
    runner, rec = make_runner(tmp_path, remaining)
    runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    remaining[0] = 150
    runner2, rec2 = make_runner(tmp_path, remaining, store=False, release_check=False, usda_reserve_requests=200)
    runner2.service.get_nutrition(171413)                                                              # one reply carries the headers: 149 left, under the reserve
    run = runner2.run(tmp_path / "menu.jpg", run_id="r2")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.status == "skipped" and "USDA allowance reserve reached" in d.reason and "not tried" in run.recommendation
    assert len(rec2.requests) == 1


def test_a_flagged_dish_is_left_out_listed_with_the_reason_and_the_flag_closes_when_it_passes(tmp_path):
    remaining = [3000]
    # the 3C reading of the marinade: the oil tagged as eaten puts 216 g of oil in the recipe -> far above the published range per 100 g
    eaten = TaggingLLM({"olive oil": ("eaten", "plain_food"), "bay": ("removed", "plain_food")})
    runner, rec = make_runner(tmp_path, remaining, llm=eaten)
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.status == "flagged" and d.reason == FLAG_REASON and d.reference["flagged"] and d.reference["top_contributors"][0]["line"] == "olive oil"
    assert run.ranking == [] and [(u.name, u.reason) for u in run.unranked] == [("MARINATED OLIVES", FLAG_REASON)]
    assert "couldn't estimate any" in run.recommendation and len(run.flags) == 1 and run.flags[0]["status"] == "open" and run.totals["dishes_flagged"] == 1
    assert run.flags[0]["comparison"] == "per_100g" and D(run.flags[0]["roli_middle"]) > D("4.2") and D(run.flags[0]["top_contributors"][0]["share_of_middle"]) > D("0.5")
    assert runner.flags.open_flags() and (tmp_path / "runs" / "flags.jsonl").exists()
    # the cause fixed (the oil is a medium): the dish returns and the flag closes
    runner2, _ = make_runner(tmp_path, remaining, llm=TaggingLLM(TAGS))
    runner2.judgements = None                                                                   # the saved tags of the first run are the wrong answer this test replaces
    run2 = runner2.run(tmp_path / "menu.jpg", run_id="r2")
    (d2,) = [x for x in run2.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d2.status == "evaluated" and run2.ranking[0].name == "MARINATED OLIVES"
    assert len(run2.flags) == 1 and run2.flags[0]["status"] == "closed" and runner2.flags.open_flags() == {}
    # the check off: no reference, and unsourced rule rows are left out (12.2.2)
    runner3, _ = make_runner(tmp_path, remaining, llm=eaten, reference_check=False)
    runner3.judgements = None
    run3 = runner3.run(tmp_path / "menu.jpg", run_id="r3")
    (d3,) = [x for x in run3.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d3.status == "evaluated" and d3.reference is None and run3.ranking


def test_tag_calls_are_counted_in_the_spend_ledger(tmp_path):
    remaining = [3000]
    runner, _ = make_runner(tmp_path, remaining)
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.cost["llm_calls"] >= 4 and (d.estimate["cost"]["llm_calls_by_stage"].get("tags") == 1)
    ledger = [json.loads(l) for l in (tmp_path / "runs" / "spend_ledger.jsonl").read_text().splitlines()]
    assert ledger[-1]["run_id"] == "r1" and ledger[-1]["model_calls"] == run.spend["model_calls"] >= d.cost["llm_calls"]
