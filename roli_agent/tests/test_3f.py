"""Checkpoint 3F (SPEC_3_mvp.md 12.10): the raw-flesh conversion, the D25 same-food test, the marinade and frying rules, cleaned queries, the saved reading, the
new-potatoes rows, the frying-fat sentence, and the flag file. No network."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from roli_nutrition.inputs import InputFood
from roli_nutrition.nutrients import extract_nutrition, parse_search
from roli_nutrition.portions import extract_portions

from roli_agent.mvp.menu_run import MenuRunner
from roli_agent.mvp.models import MvpConfig, RankedDish
from roli_agent.mvp.ranking import NOT_RESTAURANT, frying_fat_line, recommendation_text
from roli_agent.mvp.readings import SavedReadings
from roli_agent.mvp.reference import FlagFile, reference_check
from roli_agent.prompts import LINE_TAGS_PROMPT
from roli_agent.recipes.adapt import DEFAULT_TABLE, WeightsTable
from roli_agent.recipes.equivalence import same_food
from roli_agent.recipes.ingest import clean_query, default_queries
from roli_agent.recipes.models import MatchDecision, MenuItem
from roli_agent.recipes.parse import parse_line
from roli_agent.recipes.portions import PortionRules
from roli_agent.recipes.survey import SurveyComponent, SurveyMeasurePolicy, _amount
from roli_agent.recipes.tags import method_sentences, validate_tag
from roli_agent.scripts.eval_line_tags import SET
from roli_agent.scripts.eval_mvp import flag_text
from roli_agent.scripts.reader_check import compare_readings

from conftest import load
from test_3d_reference_usda import dish
from test_mvp_local import SurveyFakeService

D = Decimal
WEIGHTS = WeightsTable.load()
RULES = PortionRules.load()


# -- 12.10.1: raw flesh on the finished-food basis --------------------------------------------------------------------------------------


def component(family="fish"):
    return SurveyComponent(text="CORNISH FISH", family=family, query="q")


def test_pr15_round_trip_returns_the_measured_fried_weights():
    pr15 = next(r for r in RULES.rows if r.id == "PR15")
    assert (pr15.low, pr15.high) == (D("99.9"), D("129.2"))
    svc = SurveyFakeService()
    inputs = svc.get_inputs(2706244)                                       # "Fish, cod, fried": the record PR15 cites
    comp = component()
    _amount(comp, "fish_and_chips", RULES, list(inputs.inputs), [], inputs.grams_per_100g_scale)
    assert comp.raw_share == D("76.01") and (comp.grams_low, comp.grams_high) == (D("131.4"), D("170.0"))
    assert "scaled by USDA's moisture change" in comp.amount_basis


def test_a_raw_flesh_rule_gives_a_plate_about_15_percent_lighter_than_the_unscaled_share():
    svc = SurveyFakeService()
    inputs = svc.get_inputs(2706334)                                       # Calamari, fried
    comp = component("shellfish")
    _amount(comp, "fish_starter", RULES, list(inputs.inputs), [], inputs.grams_per_100g_scale)      # 3I: on PR11; PR02 (fish_main) is unsourced and portions nothing
    pr02 = next(r for r in RULES.rows if r.id == "PR11")
    assert abs(comp.grams_low - pr02.low / D("0.7601")) <= D("0.1") and abs(comp.grams_high - pr02.high / D("0.7601")) <= D("0.1")   # raw at 76.01 g per 100 g of fried fish (the code divides by the unrounded share)
    assert abs(comp.grams_low / (pr02.low * 100 / 65) - D("0.855")) < D("0.001")


def test_with_no_moisture_change_the_unscaled_share_stays_and_the_diagnostics_say_so():
    comp = component()
    _amount(comp, "fish_starter", RULES, [InputFood.model_construct(description="Fish, cod, Atlantic, raw", grams_per_100g=65.0)], [], None)
    assert comp.raw_share == D("65.00") and "no moisture change" in comp.amount_basis and "unscaled 65" in comp.amount_basis


# -- 12.10.7: a borrowed cup weight needs the same food ---------------------------------------------------------------------------------


class CheeseService:
    """Real saved USDA replies for the two searches and the two records."""

    bodies = {2705730: "food_survey_2705730", 2705778: "food_survey_2705778", 2709614: "food_survey_2709614", 2709628: "food_survey_2709628"}
    searches = {"Cheese parmesan": "search_exact_cheese_parmesan", "Cheese": "search_exact_cheese", "Spinach baby": "search_exact_spinach_baby", "Spinach": "search_exact_spinach"}

    def search_foods(self, query, limit=5, data_types=None):
        return parse_search(query, load(self.searches[query]), limit)

    def get_portions(self, fdc_id):
        return extract_portions(fdc_id, load(self.bodies[fdc_id])) if fdc_id in self.bodies else extract_portions(fdc_id, {"foodPortions": []})


def test_same_food_needs_the_variety_not_the_first_word():
    assert same_food("Cheese, Parmesan, hard", "Cheese, parmesan, hard")
    assert not same_food("Cheese, cottage cheese, with gelatin dessert", "Cheese, parmesan, hard")
    assert not same_food("Yogurt, almond milk", "Yogurt, Greek, plain, whole milk") and not same_food("Spinach, creamed", "Spinach, baby")
    assert same_food("Onions, raw", "Onions, red, raw") and same_food("Olives, NFS", "Olives, ripe, canned (jumbo-super colossal)") and same_food("Raisins", "Raisins, golden, seedless")
    assert same_food("Olives, green", "Olives, pickled, canned or bottled, green") and not same_food("Olives, black", "Olives, pickled, canned or bottled, green")
    assert not same_food("Olive oil", "Oil, olive, salad or cooking")


def test_quarter_cup_of_parmesan_is_a_parmesan_measure_not_60_g_of_cottage_cheese():
    sr = MatchDecision(name="parmesan", preparation_hint="as_used", fdc_id=170848, description="Cheese, parmesan, hard", data_type="SR Legacy", match_type="direct")
    lent = SurveyMeasurePolicy(CheeseService()).find(parse_line("1/4 cup thinly sliced Parmesan"), sr)
    assert lent is not None and D(20) <= lent.grams <= D(25) and "Cheese, Parmesan" in lent.grams_reference and "cottage" not in lent.grams_reference


def test_packed_baby_spinach_is_raw_spinach_not_creamed():
    sr = MatchDecision(name="baby spinach", preparation_hint="as_used", fdc_id=1, description="Spinach, baby", data_type="Foundation", match_type="direct")
    lent = SurveyMeasurePolicy(CheeseService()).find(parse_line("3 cups baby spinach leaves"), sr)
    assert lent is not None and lent.grams == D(75) and "Spinach, raw" in lent.grams_reference


# -- 12.10.2-3: the tag rules -----------------------------------------------------------------------------------------------------------


def test_the_prompt_carries_the_marinade_frying_and_poaching_rules():
    for words in ("a cup or more of oil used to fry, deep or shallow", "drained, thrown away or left in the jar", "brushed on, cooked with the food or served on the plate", "turns it into a sauce or serves it", "a lemon stuffed in a cavity", "stock, sausage"):
        assert words in LINE_TAGS_PROMPT


def test_the_guards_let_the_decided_tags_through_and_keep_refusing_the_rest():
    assert validate_tag("soy sauce", "cooking_medium", "prepared_product", "marinade").role == "cooking_medium"
    assert validate_tag("lemon", "removed", "plain_food", "cavity").role == "removed"
    assert validate_tag("garlic", "removed", "plain_food", "").role == "eaten" and validate_tag("brown sugar", "cooking_medium", "plain_food", "").role == "eaten"


def test_the_method_sentences_reach_what_happens_to_a_marinade_late_in_the_method():
    text = next(r["method"] for r in json.loads(Path(SET).read_text(encoding="utf-8"))["recipes"] if "lofthouse" in r["title"])
    assert any("Brush dough" in s for s in method_sentences(text))


def test_the_test_set_holds_the_decided_lines_and_the_two_real_misses():
    doc = json.loads(Path(SET).read_text(encoding="utf-8"))
    lines = [l for r in doc["recipes"] for l in r["lines"]]
    assert sum("12.10.3 decided" in l.get("rule", "") for l in lines) == 12 and not any("unclear" in l for l in lines)
    assert {l["kind"] for l in lines if l["line"] in ("4 cups fish stock", "4 cups chicken stock", "6 cups vegetable stock", "1 sausage")} == {"prepared_product"}
    assert sum("harmful miss in 3E" in l.get("rule", "") for l in lines) == 2


# -- 12.10.4: cleaned search queries ----------------------------------------------------------------------------------------------------


def test_one_rule_cleans_every_query():
    assert clean_query("FISH OF THE DAY.") == "fish of the day" and clean_query("SIRLOIN STEAK 10oz") == "sirloin steak" and clean_query("Rib-eye* £14") == "rib eye"
    assert clean_query("Zuni Caesar salad*") == "zuni caesar salad" and clean_query("DESSERTS 8") == "desserts" and clean_query("Steak 12.50") == "steak" and clean_query("8 oz. burger") == "burger"
    assert clean_query("7 layer dip") == "7 layer dip"


def test_two_readings_of_one_dish_make_one_search():
    a = default_queries(MenuItem(name="SNAPPER", description="WATERMELON, FETTA", section="FISH OF THE DAY"))
    b = default_queries(MenuItem(name="Snapper*", description="Watermelon., fetta", section="FISH OF THE DAY."))
    assert a == b == {"open": "snapper fish of the day recipe", "structured_hosts": "snapper fish of the day recipe watermelon"}
    assert default_queries(MenuItem(name="TOFFEE PUDDING", section="DESSERTS 8"))["open"] == "toffee pudding recipe"    # a generic heading stays generic with its price


# -- 12.10.5: the saved reading ---------------------------------------------------------------------------------------------------------


class Reader:
    def __init__(self):
        self.calls = 0

    def __call__(self, photo):
        self.calls += 1
        return {"readable": True, "items": [{"name": f"DISH {self.calls}", "description": "", "section": ""}]}


def runner(tmp_path, reader, **cfg):
    return MenuRunner(MvpConfig(**cfg), service=object(), llm=object(), read_menu=reader, cache_dir=tmp_path, usda_requests=lambda: 0)


def test_a_reading_is_saved_and_reused_only_when_the_setting_is_on(tmp_path):
    photo = tmp_path / "menu.jpg"
    photo.write_bytes(b"one photo")
    reader = Reader()
    assert runner(tmp_path, reader).read_menu(str(photo))[2] == "fresh" and reader.calls == 1
    menu, err, source = runner(tmp_path, reader, reuse_saved_reading=True).read_menu(str(photo))
    assert (source, err, reader.calls, menu["items"][0]["name"]) == ("saved", None, 1, "DISH 1")
    assert runner(tmp_path, reader).read_menu(str(photo))[2] == "fresh" and reader.calls == 2      # off by default: a tester's run always reads the photo
    photo.write_bytes(b"another photo")
    assert runner(tmp_path, reader, reuse_saved_reading=True).read_menu(str(photo))[2] == "fresh"  # the key is the image, not the file name


def test_the_key_holds_the_image_the_prompt_and_the_model_and_the_reader_check_saves_nothing(tmp_path):
    photo = tmp_path / "menu.jpg"
    photo.write_bytes(b"one photo")
    saved = SavedReadings(tmp_path / "r", "m1", "p1")
    saved.put(photo, {"items": []})
    assert saved.get(photo) == {"items": []} and SavedReadings(tmp_path / "r", "m2", "p1").get(photo) is None and SavedReadings(tmp_path / "r", "m1", "p2").get(photo) is None
    r = runner(tmp_path, Reader())
    r.read_menu(str(photo), save=False)
    assert r.readings.get(photo) is None


def test_the_reader_check_lists_what_changed():
    a = {"items": [{"name": "COBIA", "description": "SALAD", "section": "FISH OF THE DAY"}, {"name": "SNAPPER"}]}
    b = {"items": [{"name": "COBIA", "description": "SALAD", "section": "FISH OF THE DAY."}]}
    diffs = compare_readings(a, b)
    assert diffs[0] == "item count: 2 vs 1" and "section: 'FISH OF THE DAY' vs 'FISH OF THE DAY.'" in diffs[1] and diffs[2] == "only in the first reading: 'SNAPPER'"
    assert compare_readings(a, a) == []


# -- 12.10.6: new potatoes --------------------------------------------------------------------------------------------------------------


def test_new_potatoes_have_a_plain_row_and_butter_only_when_the_menu_says_buttered():
    plain, buttered = WEIGHTS.find("New Potatoes", "fish_main"), WEIGHTS.find("Buttered New Potatoes", "fish_main")
    assert plain.id == "W58" and plain.fdc_id == 2709395 and (plain.low, plain.high) == (D(120), D(180))
    assert buttered.id == "W59" and buttered.fdc_id == 2709397 and (buttered.low, buttered.high) == (D(120), D(180))
    assert WEIGHTS.find("Jersey Royals", "fish_main").id == "W58" and WEIGHTS.find("new potatoes in butter", "fish_main").id == "W59"
    for other in ("Sauteed New Potatoes", "Roast new potatoes", "New potato salad", "Crushed new potatoes"):
        assert WEIGHTS.find(other, "fish_main") is None, other


def test_both_potato_rows_carry_the_values_of_their_usda_records():
    for row_id, fixture in (("W58", 2709395), ("W59", 2709397)):
        row = next(r for r in csv.DictReader(open(DEFAULT_TABLE, encoding="utf-8")) if r["id"] == row_id)
        n = extract_nutrition(fixture, load(f"food_survey_{fixture}"))
        assert (D(str(n.saturated_fat_g)), D(str(n.cholesterol_mg))) == (D(row["sat_fat_g_per_100g"]), D(row["cholesterol_mg_per_100g"])) and n.description == row["usda_description"]
        assert any(p.label == "1 new potato" and p.gram_weight == 60.0 for p in extract_portions(fixture, load(f"food_survey_{fixture}")).portions)


# -- 12.10.9: the frying-fat sentence ---------------------------------------------------------------------------------------------------

RANGES = {"beef dripping": {"saturated_fat_g": {"low": "21.93", "high": "30.70"}}, "vegetable oil": {"saturated_fat_g": {"low": "6.90", "high": "10.06"}}}
LINE = "Cornish Fish & Chips: about 6.9-10 g saturated fat if fried in vegetable oil, up to about 31 g in beef dripping. Ask what they fry in."


def ranked(rank, name, low="1", high="2", fat_line=None):
    return RankedDish(rank=rank, key=name, name=name, saturated_fat_low=D(low), saturated_fat_high=D(high), cholesterol_low=D(300), cholesterol_high=D(400), support="close_call", overlaps_with=[], fat_line=fat_line)


def test_the_sentence_comes_from_the_computed_ranges_in_the_specified_words():
    assert frying_fat_line("CORNISH FISH & CHIPS", RANGES) == LINE
    assert frying_fat_line("CORNISH FISH & CHIPS", {"vegetable oil": RANGES["vegetable oil"]}) is None and frying_fat_line("x", {}) is None


def test_the_sentence_survives_the_word_limit_and_the_optional_sentences_go_first():
    long = "Slow braised Cornish hake with fennel, saffron, potatoes and a great many other things"
    picks = [ranked(1, long), ranked(2, "CORNISH FISH & CHIPS", "6.9", "31", LINE), ranked(3, long + " again")]
    text, words = recommendation_text(picks, 3, 14, 11, n_skipped=2)
    assert LINE in text and text.endswith(NOT_RESTAURANT)
    assert "2) Cornish Fish & Chips;" in text and "6.9-31" not in text and words == len(text.split())


def test_two_such_dishes_keep_both_sentences_and_the_disclaimer_even_over_the_limit():
    second = LINE.replace("Cornish", "Whitby")
    text, words = recommendation_text([ranked(1, "CORNISH FISH & CHIPS", "6.9", "31", LINE), ranked(2, "WHITBY FISH & CHIPS", "6.9", "31", second), ranked(3, "Soup")], 3, 14, 11, n_skipped=2)
    assert LINE in text and second in text and "..." not in text


# -- 12.10.11: the flag file ------------------------------------------------------------------------------------------------------------


def test_the_flag_file_gets_a_line_only_when_a_flag_opens_or_closes(tmp_path):
    f = FlagFile(tmp_path / "flags.jsonl")
    card = RULES.card_for("snack_bowl", "olives")
    bad, good = reference_check(dish("4.8", "19.3"), card, factor=D("1.5")), reference_check(dish("1.2", "2.4"), card, factor=D("1.5"))
    for run in ("r1", "r2", "r3"):
        row = f.raise_flag(run_id=run, menu="m.jpg", dish="Olives", dish_type="snack_bowl", check=bad)
        assert row["status"] == "open" and row["run"] == run                                     # the run still reports it
    f.close_flag(run_id="r4", menu="m.jpg", dish="Olives", check=good)
    f.raise_flag(run_id="r5", menu="m.jpg", dish="Olives", dish_type="snack_bowl", check=bad)
    assert [(l["run"], l["status"]) for l in f.lines()] == [("r1", "open"), ("r4", "closed"), ("r5", "open")]


def test_the_closed_flag_report_prints_no_none():
    text = flag_text({"status": "closed", "dish": "SICILIAN OLIVES", "note": "every check that may flag now passes: per_100g 2.681 vs 1.7-2.8"})
    assert text == "closed SICILIAN OLIVES (every check that may flag now passes: per_100g 2.681 vs 1.7-2.8)" and "None" not in text


def test_a_flagged_dish_shows_the_sentence_where_a_tester_reads_it():
    from roli_agent.mvp.models import MenuRun, Unranked
    from roli_agent.mvp.web import ENV
    run = MenuRun(run_id="r", created_at="now", config=MvpConfig(), status="done", recommendation="x", unranked=[Unranked(key="k", name="CORNISH FISH & CHIPS", reason="our estimate disagrees", fat_line=LINE)])
    html = ENV.get_template("run").render(token="", local_mode=True, banner="", config=MvpConfig(), run=run, progress=[], running=False)
    assert LINE.replace("&", "&amp;") in html                                                    # 12.12.8: escaped on the page, read as "&" by the tester
