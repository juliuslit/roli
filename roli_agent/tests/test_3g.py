"""Checkpoint 3G (SPEC_3_mvp.md 12.12): the recipe's own grams, D25 same food first, the near-zero rule for small items, food stored in oil, the known-limit status, failed pages in test
reruns, escaping on every page, the reader's v6 prompt and the real-page tag cases. No network."""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from roli_agent.mvp.models import DishRun, MenuRun, MvpConfig, Unranked
from roli_agent.mvp.reference import FLAG_REASON, KNOWN_LIMIT_REASON, FlagFile, KnownLimits, reference_check
from roli_agent.mvp.web import ENV
from roli_agent.prompts import LINE_TAGS_PROMPT
from roli_agent.recipes.convert import apply_embedded_weight, convert_weight
from roli_agent.recipes.equivalence import class_level, same_food
from roli_agent.recipes.fetch import FailedPages, PoliteFetcher
from roli_agent.recipes.inference import completeness_basis, size_inferences
from roli_agent.recipes.models import MatchDecision, MenuItem
from roli_agent.recipes.parse import parse_line, split_parentheses
from roli_agent.recipes.portions import PortionRules
from roli_agent.recipes.survey import SurveyMeasurePolicy
from roli_agent.scripts.eval_line_tags import SET, score

from test_3d_reference_usda import dish, make_runner, photo_bytes, prepare_photo
from test_3d_tags_cards import TaggingLLM

D = Decimal
RULES = PortionRules.load()


def weighed(line: str):
    return apply_embedded_weight(convert_weight(parse_line(line)))


# -- 12.12.5: the recipe's own grams win ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("line, grams, name", [
    ("1/3 cup pecorino romano (33g)", "33", "pecorino romano"),
    ("1/3 cup freshly grated pecorino romano ((33g), or parmesan cheese)", "33", "freshly grated pecorino romano"),        # the page's own line, Salsiccia Bianca, 3F
    ("½ cup Parmesan cheese (grated, (65g) $1.78)", "65", "parmesan cheese"),                                             # the price no longer lands in the food's name
    ("½ cup all-purpose flour (80g, $0.09)", "80", "all-purpose flour"),
    ("2 Tablespoons/30g extra-virgin olive oil", "30", "extra-virgin olive oil"),
    ("1/2 cup / 113 g butter", "113", "butter"),
    ("1 cup (100g/3.5oz) grated parmesan", "100", "grated parmesan"),
    ("1/3 cup (1 oz; 33g) pecorino", "33", "pecorino"),
    ("4 oz / 113 g feta", "113", "feta"),                                                                                 # both systems: the grams the page wrote
    ("1 cup (240 g) water", "240", "water"),                                                                              # before the 1 g/ml assumption
])
def test_a_weight_stated_on_the_line_is_used_before_any_cup_conversion(line, grams, name):
    p = weighed(line)
    assert p.grams == D(grams) and p.name == name and "conversion_pending_usda_portion" not in p.flags and "density_assumed_1" not in p.flags


def test_a_stated_range_on_a_volume_line_is_read_at_its_midpoint_and_says_so():
    p = weighed("1 1/2 cups thickly sliced mushrooms (5 to 6 ounces)")
    assert abs(p.grams - D("155.92")) < D("0.01") and "range_midpoint" in p.flags and "midpoint" in p.grams_reference


def test_a_note_with_other_words_is_still_not_a_weight():
    assert weighed("2 cups tomatoes (from a 14 oz can)").grams is None
    assert weighed("10 ounces spinach (from a 300 g bag)").grams == D("10") * D("28.349523125")


def test_a_second_system_after_grams_leaves_the_name_and_the_grams_alone():
    p = weighed("400g / 14oz orecchiette pasta (or other pasta)")
    assert p.grams == D(400) and p.name == "orecchiette pasta"
    assert weighed("1 cup / 240 ml milk").name == "milk"


def test_brackets_inside_a_note_stay_in_the_note():
    assert split_parentheses("salmon ((3/4 lb) Any variety; I used sockeye)") == (["(3/4 lb) Any variety; I used sockeye"], "salmon  ")
    assert split_parentheses("olives (open note")[0] == ["open note"]


# -- 12.12.4: D25, same food first ------------------------------------------------------------------------------------------------------


def test_the_same_food_is_recognised_across_usda_tables():
    assert same_food("Nuts, walnuts, english", "Nuts, walnuts, dry roasted, with salt added")
    assert same_food("Walnuts, excluding honey roasted", "Nuts, walnuts, english")
    assert same_food("Italian sausage", "Sausage, Italian, pork, mild, raw")
    assert same_food("Olives, ripe, canned (small-extra large)", "Olives, ripe, canned (jumbo-super colossal)")
    assert not same_food("Walnuts, honey roasted", "Nuts, walnuts, english") and not same_food("Walnut oil", "Nuts, walnuts, english")
    assert not same_food("Mushrooms, shiitake, stir-fried", "Mushrooms, shiitake, raw")                  # cooked against raw
    assert not same_food("Pork, cured, ham, patties, unheated", "Pork, cured, bacon, unprepared")        # the second segment says how it is kept, not which food
    assert not same_food("Olive oil", "Oil, olive, salad or cooking")


def test_the_wrong_lenders_of_the_first_3g_pass_stay_out():
    """Printed by the first live pass: goat meat for goat cheese, half and half for heavy cream, cooked tomatoes for raw (240 g against 180 g a cup), white pepper for black."""
    assert not same_food("Goat", "Cheese, goat, soft type")
    assert not same_food("Cream, fluid, half and half", "Cream, fluid, heavy whipping") and same_food("Cream, heavy", "Cream, fluid, heavy whipping")
    assert not same_food("Tomatoes, red, ripe, cooked", "Tomatoes, red, ripe, raw, year round average") and same_food("Tomatoes, raw", "Tomatoes, red, ripe, raw, year round average")
    assert not same_food("Spices, pepper, white", "Spices, pepper, black")
    assert same_food("Sesame seeds", "Seeds, sesame seeds, whole, roasted and toasted")


def test_class_level_records_are_nfs_or_a_whole_category():
    for lender in ("Nuts, NFS", "Pork, NFS", "Sausage, NFS", "Olives, NFS", "Fish, canned", "Mushrooms, raw", "Seaweed, raw"):
        assert class_level(lender), lender
    for lender in ("Onions, raw", "Tomatoes, raw", "Raisins", "Olives, green", "Italian sausage", "Cheese, Ricotta", "Fish, anchovy"):
        assert not class_level(lender), lender


class Lenders:
    def __init__(self, tables: dict[str, list[tuple[int, str, str]]], cups: dict[int, float]):
        self.tables, self.cups, self.calls = tables, cups, []

    def search_foods(self, query, limit, data_types=None):
        self.calls.append((query, tuple(data_types)))
        rows = self.tables.get(data_types[0], [])
        return SimpleNamespace(candidates=[SimpleNamespace(fdc_id=i, description=d, data_type=t) for i, d, t in rows])

    def get_portions(self, fdc_id):
        cup = self.cups.get(fdc_id)
        return SimpleNamespace(portions=[SimpleNamespace(label="1 cup", gram_weight=cup, amount=1, measure="cup", modifier="")] if cup else [])


WALNUTS = MatchDecision(name="walnuts", preparation_hint="as_used", fdc_id=170594, description="Nuts, walnuts, dry roasted, with salt added", data_type="SR Legacy", match_type="direct")
NFS = (2707484, "Nuts, NFS", "Survey (FNDDS)")


def test_a_same_food_record_lends_before_a_class_level_one_in_any_table():
    svc = Lenders({"Foundation": [(170187, "Nuts, walnuts, english", "SR Legacy")], "Survey (FNDDS)": [NFS]}, {170187: 117, 2707484: 142})
    lent = SurveyMeasurePolicy(svc).find(parse_line("1 cup chopped walnuts"), WALNUTS)
    assert lent.grams == D(117) and "class_level_cup_weight" not in lent.flags and "SR Legacy record 170187" in lent.grams_reference
    assert ("Nuts walnuts", ("Foundation", "SR Legacy")) in svc.calls


def test_a_class_level_record_lends_only_when_no_same_food_record_has_the_measure_and_the_line_says_so():
    svc = Lenders({"Foundation": [(170187, "Nuts, walnuts, english", "SR Legacy")], "Survey (FNDDS)": [NFS]}, {2707484: 142})
    lent = SurveyMeasurePolicy(svc).find(parse_line("1 cup chopped walnuts"), WALNUTS)
    assert lent.grams == D(142) and "class_level_cup_weight" in lent.flags and "class-level record" in lent.grams_reference


def test_a_class_level_cup_weight_is_complete_with_inferences_not_source_complete():
    result = SimpleNamespace(ingredients=[SimpleNamespace(ingredient_id="ing_01", name="walnuts", grams_in_recipe=D(142))])
    (inf,) = size_inferences(result, {}, {"ing_01": "USDA 2707484 portion '1 cup' = 142 g"})
    assert inf.kind == "class_level_cup_weight" and "12.12.4" in inf.review_status
    total = SimpleNamespace(source_complete=True, complete_with_inferences=True)
    assert completeness_basis({"saturated_fat_g": total}, True) == {"saturated_fat_g": "complete_with_inferences"}


# -- 12.12.2: the near-zero rule for small items ----------------------------------------------------------------------------------------


def test_the_tag_prompt_keeps_the_stored_in_oil_sentence_and_the_marinade_rule():
    assert "oil a food is stored in or served out of (a jar or bowl of olives, feta or vegetables in oil, a confit): only the oil that clings to the food is eaten" in LINE_TAGS_PROMPT
    assert 'A marinade that is brushed on, cooked with the food or served on the plate is "eaten"' in LINE_TAGS_PROMPT


# -- 12.12.6: known limit of the data ---------------------------------------------------------------------------------------------------

CHIPS = [{"line": "CHIPS fat", "sat_fat_g": "10.93", "share_of_middle": "0.58"}, {"line": "FISH fat", "sat_fat_g": "5.98", "share_of_middle": "0.32"}]
LIMIT = {"card": "snack_bowl", "top_contributor": "chips", "reason": "USDA has no thick-cut chips record", "date": "2026-11-06", "decided_by": "Julius"}


def test_the_table_has_exactly_julius_s_row():
    assert KnownLimits.load().rows == [{**LIMIT, "card": "fish_and_chips"}]


def test_a_row_applies_only_to_its_card_and_while_its_contributor_is_on_top():
    limits = KnownLimits.load()
    assert limits.find("fish_and_chips", CHIPS)["reason"] == "USDA has no thick-cut chips record"
    assert limits.find("snack_bowl", CHIPS) is None and limits.find("fish_and_chips", list(reversed(CHIPS))) is None and limits.find("fish_and_chips", []) is None


def test_a_known_limit_replaces_the_open_flag_and_no_longer_counts_as_a_to_do(tmp_path):
    f = FlagFile(tmp_path / "flags.jsonl")
    card = RULES.card_for("snack_bowl", "olives")
    bad, good = reference_check(dish("4.8", "19.3"), card, factor=D("1.5")), reference_check(dish("1.2", "2.4"), card, factor=D("1.5"))
    f.raise_flag(run_id="r1", menu="m.jpg", dish="Olives", dish_type="snack_bowl", check=bad)
    assert len(f.open_flags()) == 1
    bad.known_limit = LIMIT
    for run in ("r2", "r3"):
        row = f.raise_flag(run_id=run, menu="m.jpg", dish="Olives", dish_type="snack_bowl", check=bad)
        assert row["status"] == "known_limit" and "USDA has no thick-cut chips record" in row["note"] and "Julius" in row["note"]
    assert f.open_flags() == {} and [(l["run"], l["status"]) for l in f.lines()] == [("r1", "open"), ("r2", "known_limit")]
    assert f.close_flag(run_id="r4", menu="m.jpg", dish="Olives", check=good)["status"] == "closed"


def test_the_build_never_sets_the_status_without_a_row(tmp_path):
    runner, _ = make_runner(tmp_path, [3000], llm=TaggingLLM({"olive oil": ("eaten", "plain_food")}))
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.status == "flagged" and d.reason == FLAG_REASON and d.reference["known_limit"] is None and run.flags[0]["status"] == "open"
    assert run.totals["dishes_flagged"] == 1 and run.totals["dishes_known_limit"] == 0


def test_a_known_limit_dish_stays_out_of_the_ranking_keeps_its_line_and_leaves_the_to_do_count(tmp_path):
    runner, _ = make_runner(tmp_path, [3000], llm=TaggingLLM({"olive oil": ("eaten", "plain_food")}))
    runner.known_limits = KnownLimits([{**LIMIT, "top_contributor": "olive oil", "reason": "a test reason"}])
    run = runner.run(prepare_photo(photo_bytes(), tmp_path / "menu.jpg"), run_id="r1")
    (d,) = [x for x in run.dishes if x.item["name"] == "MARINATED OLIVES"]
    assert d.status == "flagged" and d.reason == f"{KNOWN_LIMIT_REASON}: a test reason" and run.ranking == []
    assert [(u.name, u.reason) for u in run.unranked] == [("MARINATED OLIVES", f"{KNOWN_LIMIT_REASON}: a test reason")]
    assert run.totals["dishes_flagged"] == 0 and run.totals["dishes_known_limit"] == 1 and runner.flags.open_flags() == {} and run.flags[0]["status"] == "known_limit"
    html = ENV.get_template("run").render(token="", local_mode=True, banner="", config=MvpConfig(), run=run, progress=[], saved=False)
    assert "known limit of the data: a test reason" in html and "left out until the cause is fixed" not in html


# -- 12.12.7: failed pages in test reruns -----------------------------------------------------------------------------------------------

PAGE = "<html><body>recipe</body></html>"


def fetcher(status, failed, seen):
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(status, html=PAGE)
    return PoliteFetcher(transport=httpx.MockTransport(respond), sleep=lambda s: None, respect_robots=False, failed_pages=failed)


def test_a_page_that_failed_in_the_saved_pass_stays_failed_in_a_test_rerun_and_a_live_run_retries_it(tmp_path):
    path, url, seen = tmp_path / "failed_pages.json", "https://a.test/r", []
    first, _ = fetcher(500, FailedPages(path), seen).fetch(url)
    assert first.status == "http_error" and len(seen) == 1
    rerun, html = fetcher(200, FailedPages(path, sealed=True), seen).fetch(url)
    assert rerun.status == "http_error" and rerun.http_status == 500 and html == "" and "kept failed" in rerun.detail and len(seen) == 1     # no request at all
    live, html = fetcher(200, FailedPages(path), seen).fetch(url)
    assert live.status == "ok" and html and len(seen) == 2
    again, _ = fetcher(200, FailedPages(path, sealed=True), seen).fetch(url)
    assert again.status == "ok" and len(seen) == 3                                                                                          # the success cleared the note


def test_a_test_rerun_writes_nothing_and_the_runner_seals_only_with_reuse_on(tmp_path):
    path, seen = tmp_path / "failed_pages.json", []
    fetcher(500, FailedPages(path, sealed=True), seen).fetch("https://a.test/new")
    assert not path.exists()
    runner, _ = make_runner(tmp_path, [3000])
    assert runner.config.reuse_saved_reading is False


# -- 12.12.8: escaping ------------------------------------------------------------------------------------------------------------------

MARKUP = "<script>alert(1)</script><b>Soup</b>"


def page(name, **ctx):
    return ENV.get_template(name).render(token="", local_mode=True, banner="", config=MvpConfig(), progress=[], saved=False, **ctx)


def test_a_menu_name_with_markup_is_shown_as_text_on_every_page():
    item = {"name": MARKUP, "section": MARKUP, "description": MARKUP}
    run = MenuRun(run_id="r", created_at="now", config=MvpConfig(), status="done", recommendation=f"Try {MARKUP}", errors=[MARKUP],
                  dishes=[DishRun(key="k", item=item, menu_index=0, status="flagged", reason=MARKUP)], unranked=[Unranked(key="k", name=MARKUP, reason=MARKUP, fat_line=MARKUP)])
    for html in (page("run", run=run), page("diag", run=run), page("runs", runs=[run])):
        assert "<script>" not in html and "<b>Soup" not in html and "&lt;script&gt;" in html


# -- 12.12.3: reader v6 -----------------------------------------------------------------------------------------------------------------


def test_v6_is_v5_plus_one_rule():
    from roli_agent.config import ROOT
    prompts = ROOT / "menu_reader_eval" / "prompts"
    v5, v6 = (prompts / "menu_reader_v5.md").read_text().splitlines(), (prompts / "menu_reader_v6.md").read_text().splitlines()
    added = [line for line in v6 if line not in v5]
    assert [line for line in v6 if line in v5] == v5 and len(added) == 1 and added[0].startswith("10. A line that describes several dishes is not a dish")


# -- 12.12.9: real-page tag cases -------------------------------------------------------------------------------------------------------


def test_the_real_page_cases_are_whole_recipes_beside_the_made_up_ones():
    doc = json.loads(SET.read_text(encoding="utf-8"))
    real = [r for r in doc["recipes"] if r.get("source") == "real_page"]
    assert len(real) == 5 and sum(len(r["lines"]) for r in real) == 45 and all(r["method"] and r["url"].startswith("https://") for r in real)
    assert {r["url"].split("/")[2].replace("www.", "").replace("cooking.", "") for r in real} == {"thecozyapron.com", "foodiecrush.com", "foodnetwork.com", "budgetbytes.com", "nytimes.com"}
    assert len(doc["recipes"]) - len(real) == 34 and sum(1 for r in real if r["dish"] == "SICILIAN OLIVES") == 1
    oil = [l for r in real for l in r["lines"] if "olive oil" in l["line"]]
    assert len(oil) == 5 and {l["role"] for l in oil} == {"cooking_medium"}


def test_the_report_counts_the_real_page_cases_apart():
    doc = json.loads(SET.read_text(encoding="utf-8"))
    doc["recipes"] = [r for r in doc["recipes"] if r.get("source") == "real_page"] + doc["recipes"][:1]
    result = score(doc, TaggingLLM({}))
    assert result["real_page"]["scored"] == 45 and result["scored"] == 45 + len(doc["recipes"][-1]["lines"])
