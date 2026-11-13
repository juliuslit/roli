"""Phase 3 MVP: menu run orchestration, ranking and recommendation text, the web app. No network: fake menu reader, fake search, saved USDA records."""

from __future__ import annotations

import copy
import io
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from roli_agent.llm import parse_json_object
from roli_agent.mvp.menu_run import MenuRunner, candidate_items, load_run, prepare_photo
from roli_agent.mvp.models import MvpConfig
from roli_agent.mvp.ranking import WORD_LIMIT, rank_dishes, recommendation_text
from roli_agent.mvp.web import create_app
from roli_agent.recipes.compare_dishes import compare_dishes, dish_interval
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import MenuItem, ScenarioInterval
from roli_agent.recipes.portions import PortionRules, dish_type_for
from roli_agent.mvp import selection

from conftest import load, make_service
from recipe_test_helpers import BLUEFIN, OLIVE, TOMATO, FakeSource, RuleLLM, SEARCHES, QUERIES, recipe_page
from test_recipes_fetch_search import Site

D = Decimal
SALT, CHIVES = 173468, 169994

MENU = {"readable": "yes", "problems": "", "items": [
    {"section": "TO START", "category": "food", "name": "BLUEFIN CRUDO", "description": "bottarga, chive", "price": "22"},
    {"section": "TO START", "category": "food", "name": "HEIRLOOM TOMATOES", "description": "", "price": "18"},
    {"section": "DESSERT", "category": "food", "name": "TIRAMISU", "description": "", "price": "12"},
    {"section": "DRINKS", "category": "drink", "name": "NEGRONI", "description": "", "price": "14"},
    {"section": "ENTREE", "category": "food", "name": "KING SALMON", "description": "squash", "price": "44"},
]}
PAGES = {
    "https://a.test/crudo": recipe_page("Tuna Crudo", ["200 g bluefin tuna, thinly sliced", "27 g olive oil", "100 g tomatoes, diced"], steps="Slice and dress. Serve."),
    "https://a.test/tomatoes": recipe_page("Heirloom Tomato Salad", ["600 g tomatoes, sliced", "27 g olive oil", "flaky salt, to taste"], steps="Slice and dress."),
}
Q = dict(QUERIES, **{"flaky salt": ("salt table", SALT, "direct"), "chive": ("chives raw", CHIVES, "direct"), "bottarga": ("fish roe", None, "direct"), "squash": ("squash raw", None, "direct")})


class RoutedSource:
    """Search results per dish name; one dish raises to exercise the error path."""

    def search(self, query: str, mode: str, max_results: int = 10):
        q = query.lower()
        if "salmon" in q:
            raise httpx.ConnectError("search down")
        if "crudo" in q:
            return [{"url": "https://a.test/crudo", "title": "Tuna Crudo"}] if mode == "open" else []
        if "tomato" in q:
            return [{"url": "https://a.test/tomatoes", "title": "Heirloom Tomato Salad"}] if mode == "open" else []
        return []


def usda():
    foods = {fid: load(f"food_{fid}") for fid in (BLUEFIN, OLIVE, TOMATO, SALT, CHIVES)}
    searches = dict(SEARCHES, **{"salt table": [SALT], "chives raw": [CHIVES]})

    def respond(request):
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = [f for f in searches.get(q, []) if f in foods]
            return httpx.Response(200, json={"foods": [{"fdcId": f, "description": foods[f]["description"], "dataType": foods[f]["dataType"]} for f in ids]})
        import re
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=foods[fid]) if fid in foods else httpx.Response(404, content=b"")
    return make_service(respond)


def toy_rules() -> PortionRules:
    """The first 3I rebuild (12.16.8) left the toy menu's families, crudo, tomato salad and fish main, without a measured source; the second rebuild sourced them
    again from chain sheets, with new ranges and reference figures. These tests exercise the pipeline, not the table: here the three rows are pinned to
    the 3H state, sourced and without reference figures, so a table change never moves the toy expectations."""
    rows = []
    for r in PortionRules.load().rows:
        r = copy.copy(r)
        if r.id in ("PR02", "PR03", "PR05"):
            r.review_status, r.sources, r.figures = "proposed_unreviewed", "TEST FIXTURE: treated as sourced for the pipeline tests", []
        rows.append(r)
    return PortionRules(rows)


TOY_RULES = toy_rules()


@pytest.fixture(autouse=True)
def _toy_rules(monkeypatch):
    monkeypatch.setattr(selection, "RULES", TOY_RULES)


def runner(tmp_path: Path, menu=MENU, workers=2) -> MenuRunner:
    service, _ = usda()
    r = MenuRunner(MvpConfig(workers=workers, max_dishes=12), service=service, llm=RuleLLM(queries=Q), read_menu=lambda p: menu, source_factory=RoutedSource,
                      fetcher_factory=lambda: PoliteFetcher(transport=httpx.MockTransport(Site(pages=PAGES)), sleep=lambda s: None), extraction_cache_factory=lambda: None,
                      match_cache=MatchCache(None), cache_dir=tmp_path / "cache", runs_dir=tmp_path / "runs", parse_json=parse_json_object, usda_requests=lambda: 0)
    r.rules = TOY_RULES
    return r


def photo_bytes(size=(1600, 2400)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (240, 230, 220)).save(buf, "PNG")
    return buf.getvalue()


# -- the run ----------------------------------------------------------------------------------------------------------------


def test_candidate_items_keep_only_dishes_with_a_portion_rule_and_respect_the_cap():
    chosen, aside = candidate_items(MENU, max_dishes=12)
    assert [it.name for _, it in chosen] == ["BLUEFIN CRUDO", "HEIRLOOM TOMATOES", "TIRAMISU", "KING SALMON"]          # 12.16.9: a dessert is a dish like any other
    reasons = {it.name: why for _, it, why in aside}
    assert reasons["NEGRONI"].startswith("excluded: not a dish")
    chosen2, aside2 = candidate_items(MENU, max_dishes=1)
    assert len(chosen2) == 1 and any("cap of 1" in why for _, _, why in aside2)


def test_menu_run_end_to_end_with_a_failing_dish(tmp_path):
    r = runner(tmp_path)
    photo = prepare_photo(photo_bytes(), tmp_path / "menu.jpg")
    with Image.open(photo) as im:
        assert max(im.size) == 1280                                                     # Telegram size
    said = []
    run = r.run(photo, run_id="t1", progress=said.append)
    assert run.status == "done" and run.run_id == "t1" and (tmp_path / "runs" / "t1" / "run.json").exists()
    by = {d.item["name"]: d for d in run.dishes}
    assert by["KING SALMON"].status == "no_recipes" and "ConnectError" in by["KING SALMON"].reason      # search down: ingestion records it, the run went on
    assert by["TIRAMISU"].status == "no_recipes" and by["TIRAMISU"].dish_type == "dessert" and by["NEGRONI"].status == "excluded"      # 12.16.9: tried, and the search was down
    assert by["BLUEFIN CRUDO"].selection["decision"] == "selected" and by["BLUEFIN CRUDO"].selection["course"] == "starters" and by["BLUEFIN CRUDO"].selection["lean_score"] >= 2
    assert by["BLUEFIN CRUDO"].status == "evaluated" and by["HEIRLOOM TOMATOES"].status == "evaluated"
    assert by["BLUEFIN CRUDO"].dish_type == "crudo_starter" and by["HEIRLOOM TOMATOES"].dish_type == "tomato_salad_starter"
    # the crudo's menu-only bottarga is blocked: no upper bound without the external bound; the tomato salad is complete at both bounds
    assert run.comparison is not None and len(run.ranking) + len(run.unranked) == 2
    names = [x.name for x in run.ranking]
    assert "HEIRLOOM TOMATOES" in names
    assert run.recommendation.startswith("Among the ") and "I could estimate (4 tried; " in run.recommendation and run.recommendation_words <= WORD_LIMIT
    assert "Heirloom Tomatoes" in run.recommendation and "not this kitchen's numbers" in run.recommendation
    assert run.totals["dishes_evaluated"] == 2 and run.totals["dishes_no_recipes"] == 2 and run.totals["dishes_error"] == 0 and run.totals["dishes_excluded"] == 1     # 12.16.9: the dessert is tried too
    assert run.spend["model_calls"] > 0 and run.spend["interruptions"] == [] and run.spend["limits"]["menu_usd"] == "0.50"
    assert (tmp_path / "runs" / "spend_ledger.jsonl").exists() and json.loads((tmp_path / "runs" / "spend_ledger.jsonl").read_text().splitlines()[-1])["run_id"] == "t1"
    assert run.errors and run.errors[0].startswith("KING SALMON:")
    assert any("estimating" in s for s in said) and said[-1] == "done"
    saved = load_run(tmp_path / "runs", "t1")
    assert saved is not None and saved.recommendation == run.recommendation
    # provenance survives into the stored run: assumptions and portion models per dish
    tom = by["HEIRLOOM TOMATOES"].estimate
    assert tom["adapt_mode"] == "experimental" and tom["portioned"] and any(p["applicable"] for p in tom["portioned"])
    assert all(a["review_status"] for p in tom["adapted_pairs"] for a in p["assumptions"])


def test_menu_unreadable_gives_a_failed_run_without_numbers(tmp_path):
    r = runner(tmp_path, menu=None)
    r._read_menu = lambda p: (_ for _ in ()).throw(ValueError("bad photo"))
    run = r.run(tmp_path / "nope.jpg", run_id="t2")
    assert run.status == "failed" and "could not read the menu photo" in run.recommendation and run.ranking == [] and not any(ch.isdigit() for ch in run.recommendation.split("(")[0])


def test_approved_mode_ranks_nothing_today(tmp_path):
    r = runner(tmp_path)
    r.config = MvpConfig(experimental=False, workers=2)
    r.config.adapt_mode = "approved"
    run = r.run(prepare_photo(photo_bytes(), tmp_path / "m.jpg"), run_id="t3")
    assert run.status == "done" and run.config.experimental is False
    # the tomato salad still ranks (its lines are complete from source weights and the salt is a zero-nutrient nominal fill); the crudo cannot
    assert all(d.estimate is None or d.estimate["adapt_mode"] == "approved" for d in run.dishes)


# -- ranking and words -----------------------------------------------------------------------------------------------------------


def iv(dish, low, high, tier="modeled_range_complete", **kw):
    return dish_interval(dish, kw.pop("nutrient", "saturated_fat_g"), [ScenarioInterval(scenario_id=f"{dish}:r", nutrient=kw.pop("n", "saturated_fat_g"), tier=tier, low=D(low), high=None if high is None else D(high), **kw)])


def test_rank_dishes_orders_by_upper_bound_and_labels_support():
    sat = {"a": iv("a", "1", "2"), "b": iv("b", "3", "5"), "c": iv("c", "4.5", "6"), "u": iv("u", "0.5", None, tier="lower_bound_only", unbounded_lines=["cream (missing_grams)"])}
    chol = {d: iv(d, "10", "20", nutrient="cholesterol_mg", n="cholesterol_mg") for d in sat}
    cmp = compare_dishes({"saturated_fat_g": sat, "cholesterol_mg": chol})
    ranked, unranked = rank_dishes(cmp, {"a": "Tomato Salad", "b": "Crudo", "c": "Gem Salad", "u": "Pizza"})
    assert [r.key for r in ranked] == ["a", "b", "c"] and [r.support for r in ranked] == ["well_supported", "close_call", "well_supported"]
    assert ranked[0].beats_well_supported == 2 and ranked[1].overlaps == 1 and ranked[1].reasons[0].startswith("overlaps Gem Salad")
    assert unranked[0].key == "u" and "no upper bound" in unranked[0].reason
    text, n = recommendation_text(ranked, 3, 4, 1)
    assert n <= WORD_LIMIT and text.startswith("Among the 3 dishes I could estimate (4 tried; 1 had no usable estimate), lowest saturated fat first: "
                                               "1) Tomato Salad, about 1.0-2.0 g saturated fat per plate; 2) Crudo, 3.0-5.0 g; 3) Gem Salad, 4.5-6.0 g. ")
    assert "Crudo and Gem Salad overlap, so treat that order as a toss-up." in text and "Tomato Salad cholesterol about 10-20 mg." in text
    full, _ = recommendation_text(ranked, 3, 3, 0)
    assert full.startswith("Lowest saturated fat on this menu, by my estimate: 1) Tomato Salad")           # complete coverage only
    one, _ = rank_dishes(compare_dishes({"saturated_fat_g": {"a": sat["a"]}, "cholesterol_mg": {"a": chol["a"]}}), {"a": "Tomato Salad"})
    assert one[0].support == "only_estimate" and "the only dish I could estimate, so this is one figure, not a ranking" in recommendation_text(one, 1, 6, 5)[0]
    assert "Among the 1 dish I could estimate" in recommendation_text(one, 1, 6, 5)[0]
    empty, n0 = recommendation_text([], 0, 5, 5)
    assert "couldn't estimate any of the 5 dishes" in empty and n0 <= WORD_LIMIT
    skipped, _ = recommendation_text(ranked, 3, 9, 1, n_skipped=5)
    assert "(4 tried; 1 had no usable estimate; 5 not tried)" in skipped


def test_recommendation_never_exceeds_eighty_words():
    from roli_agent.mvp.models import RankedDish
    long_name = "An Extraordinarily Long Dish Name With Many Many Words In It Indeed Truly"
    ranked = [RankedDish(rank=i + 1, key=f"d{i}", name=f"{long_name} {i}", saturated_fat_low=D(1), saturated_fat_high=D(2), cholesterol_low=D(1), cholesterol_high=D(9), support="close_call") for i in range(3)]
    text, n = recommendation_text(ranked, 3, 30, 27)
    assert n <= WORD_LIMIT


# -- the web app --------------------------------------------------------------------------------------------------------------------


class InstantRunner(MenuRunner):
    """A runner whose run() is the fake end-to-end run above, so the web tests exercise the real pages on a real MenuRun."""

    def __init__(self, inner: MenuRunner):
        self.__dict__.update(inner.__dict__)


def test_web_app_requires_the_token_and_serves_the_pages(tmp_path):
    inner = runner(tmp_path)
    app = create_app(InstantRunner(inner), token="secret", runs_dir=tmp_path / "runs")
    client = TestClient(app)
    assert client.get("/").status_code == 401 and client.get("/?token=wrong").status_code == 401
    r = client.get("/?token=secret")
    assert r.status_code == 200 and "Experimental" in r.text and "Read this menu" in r.text and client.cookies.get("roli_token") == "secret"
    # upload starts a run and redirects; the run page renders while running and when done
    r = client.post("/menu", files={"photo": ("menu.png", photo_bytes(), "image/png")}, data={"restaurant": "Test Place"}, follow_redirects=False)
    assert r.status_code == 303 and "/run/" in r.headers["location"]
    run_id = r.headers["location"].split("/run/")[1].split("?")[0]
    import time
    for _ in range(100):
        page = client.get(f"/run/{run_id}")
        if "Recommendation" in page.text:
            break
        time.sleep(0.1)
    assert "Recommendation" in page.text and "lowest saturated fat first" in page.text and "not this kitchen" in page.text and "search credits" in page.text
    assert "KING SALMON" in page.text or "King Salmon" in page.text              # the errored dish is listed as unranked or not evaluated
    diag = client.get(f"/run/{run_id}/diagnostics")
    assert diag.status_code == 200 and "Pairwise verdicts" in diag.text and "Portion models" in diag.text and "proposed_unreviewed" in diag.text and "ConnectError" in diag.text
    js = client.get(f"/run/{run_id}/json").json()
    assert js["run_id"] == run_id and js["status"] == "done"
    fb = client.post(f"/run/{run_id}/feedback", data={"kind": "ranking_unexpected", "dish": "", "text": "I expected the crudo first"}, follow_redirects=False)
    assert fb.status_code == 303
    lines = (tmp_path / "runs" / "feedback.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["kind"] == "ranking_unexpected" and json.loads(lines[0])["run_id"] == run_id
    assert client.post(f"/run/{run_id}/feedback", data={"kind": "bogus"}, follow_redirects=False).status_code == 400
    assert "Past runs" in client.get("/runs").text and client.get("/run/nope").status_code == 404
    # not an image, and too large
    assert client.post("/menu", files={"photo": ("x.txt", b"hello", "text/plain")}, follow_redirects=False).status_code == 400
    assert client.post("/menu", files={"photo": ("big.png", b"0" * (12 * 1024 * 1024 + 1), "image/png")}, follow_redirects=False).status_code == 413
    assert (tmp_path / "runs" / run_id / "restaurant.txt").read_text() == "Test Place"


def test_app_without_a_token_runs_in_local_mode(tmp_path, monkeypatch):
    """Local testing (2026-11-04): no token means local mode, every page open, bound to 127.0.0.1 by the launch script; a token still locks every route."""
    monkeypatch.delenv("ROLI_WEB_TOKEN", raising=False)
    app = create_app(InstantRunner(runner(tmp_path)), token=None, runs_dir=tmp_path / "runs")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200 and "Local mode" in r.text and "Experimental" in r.text and client.cookies.get("roli_token") is None
    assert client.get("/runs").status_code == 200
    with pytest.raises(RuntimeError):
        create_app(None, token=None, runs_dir=tmp_path, local=False)


def test_dish_types_for_unseen_menus():
    cases = {("SIRLOIN STEAK 10oz", "PUB CLASSICS"): "meat_main", ("WAGYU BEEF BURGER", "PUB CLASSICS"): "burger", ("TAGLIATELLE CARBONARA", "SEASONAL MAINS"): "pasta_main",
             ("Crudo of Swordfish", "(specials)"): "crudo_starter", ("Spaghetti with Gulf shrimp", ""): "pasta_main", ("STICKY TOFFEE PUDDING", "DESSERTS"): "dessert",
             ("PASTOR", "MEXICO CITY TACOS"): "taco", ("Zuni Caesar salad", "Food"): "leaf_salad_starter", ("PAN FRIED SEABASS", "SEASONAL MAINS"): "fish_main",
             ("CHICKEN & MUSHROOM ARANCINI", "STARTERS"): "vegetable_starter", ("JOSEY BAKER SOURDOUGH", "BREAD"): "side_bread"}       # 12.16.9: every kind has a family
    for (name, section), want in cases.items():
        assert dish_type_for(MenuItem(name=name, description="", section=section)) == want, name


def test_rate_limited_llm_spaces_calls_and_retries_a_429():
    from roli_agent.llm import RateLimitedLLM
    clock = {"t": 0.0}
    slept = []

    def sleep(s):
        slept.append(s)
        clock["t"] += s

    class Model:
        def __init__(self):
            self.calls = 0
            self.fail_first = 1

        def invoke(self, messages, **kw):
            self.calls += 1
            if self.fail_first:
                self.fail_first -= 1
                raise RuntimeError("Error code: 429 - Rate limit exceeded")
            return f"ok {self.calls}"
    m = Model()
    llm = RateLimitedLLM(m, per_minute=3, sleep=sleep, clock=lambda: clock["t"])
    assert llm.invoke("a") == "ok 2" and llm.retries == 1 and slept and slept[0] == 15.0          # the 429 was retried after a pause
    llm.invoke("b"); llm.invoke("c")                                                            # budget: 3 per minute (the retry counted)
    assert llm.waits >= 1 and clock["t"] >= 60.0                                                # the fourth call waited for the window

    class Broken:
        def invoke(self, messages, **kw):
            raise ValueError("not a rate limit")
    with pytest.raises(ValueError):
        RateLimitedLLM(Broken(), sleep=sleep, clock=lambda: clock["t"]).invoke("x")              # other errors pass straight through
