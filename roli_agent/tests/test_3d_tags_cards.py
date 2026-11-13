"""Checkpoint 3D (SPEC_3_mvp.md section 12, Julius 2026-11-05): line tags and their validation (12.3), lines that cannot move the result (12.4),
the plate-weight rule (12.4.4), the dish-family cards with the evidence rule (12.2), and a USDA Survey record rebuilt from its inputs with the
card's choices (12.2.3). No network: saved USDA replies, a rule-driven fake model."""

from __future__ import annotations

import json
import re
from decimal import Decimal

import httpx
from langchain_core.messages import AIMessage

from roli_agent.llm import parse_json_object
from roli_agent.recipes.fetch import PoliteFetcher
from roli_agent.recipes.match import MatchCache
from roli_agent.recipes.models import MenuItem
from roli_agent.recipes.pipeline import estimate_dish
from roli_agent.recipes.portions import PortionRules, dish_type_for, parse_choices
from roli_agent.recipes.tags import LineTags, tag_lines, validate_tag

from conftest import load, make_service
from recipe_test_helpers import FakeSource, RuleLLM, candidates, recipe_page
from test_recipes_fetch_search import Site

D = Decimal
OLIVE_OIL, GARLIC, THYME, LEMON_PEEL, SALT, PEPPER, OLIVES, MAYO, BAY, ONION, TOMATO = 171413, 169230, 173470, 167749, 173468, 170931, 2710089, 171009, 171328, 170000, 170457

# ingredient name -> (query, record, match type); the Survey olives record stands in for olives (no SR Legacy olive fixture is saved)
QUERIES = {"green olives": ("olives green", OLIVES, "proxy"), "olive oil": ("oil olive", OLIVE_OIL, "direct"), "garlic": ("garlic raw", GARLIC, "direct"),
           "fresh thyme": ("thyme fresh", THYME, "direct"), "zest of lemon": ("lemon peel raw", LEMON_PEEL, "direct"), "lemon zest": ("lemon peel raw", LEMON_PEEL, "direct"),
           "maldon sea salt": ("salt table", SALT, "proxy"), "bay": ("spices oregano dried", BAY, "proxy"), "salsa verde": ("salad dressing mayonnaise", MAYO, "proxy"),
           "red onion": ("onions raw", ONION, "direct"), "tomatoes": ("tomatoes red ripe raw", TOMATO, "direct"), "water": ("tomatoes red ripe raw", TOMATO, "proxy"),
           "chicken": ("tomatoes red ripe raw", TOMATO, "proxy"), "brine": ("salt table", SALT, "proxy")}
SEARCHES = {"olives green": [OLIVES], "oil olive": [OLIVE_OIL], "garlic raw": [GARLIC], "thyme fresh": [THYME], "lemon peel raw": [LEMON_PEEL], "salt table": [SALT],
            "spices oregano dried": [BAY], "salad dressing mayonnaise": [MAYO], "onions raw": [ONION], "tomatoes red ripe raw": [TOMATO]}
FOODS = {fid: load(name) for fid, name in {OLIVE_OIL: "food_171413", GARLIC: "food_169230", THYME: "food_173470", LEMON_PEEL: "food_167749", SALT: "food_173468", PEPPER: "food_170931",
                                           OLIVES: "food_survey_2710089", MAYO: "food_171009", BAY: "food_171328", ONION: "food_170000", TOMATO: "food_170457"}.items()}


def usda():
    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            q = json.loads(request.content)["query"]
            ids = SEARCHES.get(q, [])
            return httpx.Response(200, json={"totalHits": len(ids), "foods": [{"fdcId": f, "description": FOODS[f]["description"], "dataType": FOODS[f]["dataType"]} for f in ids]})
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=FOODS[fid]) if fid in FOODS else httpx.Response(404, content=b"")
    return make_service(respond)


class TaggingLLM(RuleLLM):
    """The 2B-2 rule model plus the 3D tag prompt: `tags` maps a line-name fragment to (role, kind); unknown lines are eaten plain foods."""

    def __init__(self, tags: dict[str, tuple[str, str]] | None = None, *, break_tags: bool = False, **kw):
        super().__init__(queries=QUERIES, **kw)
        self.tags, self.break_tags = tags or {}, break_tags
        self.tag_calls = 0

    def invoke(self, messages) -> AIMessage:
        text = messages[-1].content
        if isinstance(text, str) and text.startswith("You tag the ingredient lines"):
            self.prompts.append(text)
            self.tag_calls += 1
            if self.break_tags:
                return AIMessage(content="no json here")
            recipes = []
            for block in re.split(r"\n(?=\d+\. \")", text.split("Recipes (title")[1]):
                m = re.match(r'(\d+)\. "', block.strip())
                if not m:
                    continue
                lines = []
                for lm in re.finditer(r"^\s+(\d+)\. (.*)$", block, re.M):
                    role, kind = "eaten", "plain_food"
                    for frag, (r, k) in self.tags.items():
                        if frag in lm.group(2).lower():
                            role, kind = r, k
                    lines.append({"n": int(lm.group(1)), "role": role, "kind": kind, "reason": "test tag"})
                recipes.append({"index": int(m.group(1)), "lines": lines})
            return AIMessage(content=json.dumps({"recipes": recipes}))
        return super().invoke(messages)


def estimate(pages, item, llm, **kw):
    hits = {"open": [{"url": u, "title": ""} for u in pages], "structured_hosts": []}
    service, _ = usda()
    return estimate_dish(item, source=FakeSource(hits), fetcher=PoliteFetcher(transport=httpx.MockTransport(Site(pages=pages)), sleep=lambda s: None), service=service, llm=llm,
                         parse_json_object=parse_json_object, match_cache=MatchCache(None), prefetch_workers=1, adapt_mode="experimental", portion_rules=PortionRules.load(),
                         exclude_herbs_spices=True, line_tags=True, negligible_sat_fat_per_100g=D("0.1"), **kw)


OLIVES_ITEM = MenuItem(name="MARINATED OLIVES", description="", section="BAR SNACKS")
OLIVE_PAGE = recipe_page("Marinated Olives", ["300 g green olives", "1 cup olive oil", "3 cloves garlic", "2 sprigs fresh thyme", "zest of lemon", "2 bay leaves", "Maldon sea salt"],
                         steps="Warm the oil with the garlic, thyme, zest and bay. Pour over the olives and leave to marinate. Serve.")
TAGS = {"olive oil": ("cooking_medium", "plain_food"), "bay": ("removed", "plain_food"), "salsa verde": ("eaten", "prepared_product")}


# -- 12.3: tags, validation, fallback ---------------------------------------------------------------------------------------------------


def test_validate_tag_keeps_the_stricter_reading_and_notes_every_override():
    assert validate_tag("olive oil", "cooking_medium", "plain_food", "marinade").role == "cooking_medium"
    chicken = validate_tag("chicken thighs", "cooking_medium", "plain_food", "sits in the pan")
    assert chicken.role == "eaten" and "medium tag rejected" in chicken.note and chicken.raw_role == "cooking_medium"           # 12.3.1: only fats, oils, liquids, salt
    assert validate_tag("brine", "cooking_medium", "plain_food", "").role == "cooking_medium"
    bay = validate_tag("bay leaves", "removed", "plain_food", "")
    assert bay.role == "removed" and bay.note == ""
    fish = validate_tag("cod fillet", "removed", "plain_food", "")
    assert fish.role == "eaten" and "removed tag rejected" in fish.note
    salsa = validate_tag("salsa verde", "eaten", "plain_food", "a sauce", record_description="Sauce, salsa, ready-to-serve", match_type="direct")
    assert salsa.kind == "prepared_product" and "USDA record" in salsa.note                                                   # 12.4.2: a sauce never passes as a plain food
    odd = validate_tag("x", "sometimes", "thing", "")
    assert (odd.role, odd.kind) == ("eaten", "plain_food") and "unknown role" in odd.note


def test_one_tag_call_per_dish_and_the_prompt_lists_every_line():
    llm = TaggingLLM(TAGS)
    est = estimate({"https://a.test/olives": OLIVE_PAGE}, OLIVES_ITEM, llm)
    assert llm.tag_calls == 1
    prompt = next(p for p in llm.prompts if p.startswith("You tag the ingredient lines"))
    assert '"MARINATED OLIVES"' in prompt and "   2. 1 cup olive oil" in prompt and "   6. 2 bay leaves" in prompt and "never write a quantity" in prompt
    assert any(n.startswith("line tags: 7 lines in 1 recipes") for n in est.notes), est.notes
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    by = {l.name: l for l in s.ingredients if l.origin == "recipe"}
    assert by["olive oil"].tag_role == "cooking_medium" and by["bay"].tag_role == "removed"           # the parser names "2 bay leaves" as "bay" (leaf is the unit) and by["green olives"].tag_role == "eaten" and by["green olives"].tag_kind == "plain_food"


def test_marinade_oil_is_not_counted_at_its_recipe_weight_and_a_sourced_row_fills_what_clings():
    """Zuni marinated olives, 2026-11-05: 216 g of marinade oil counted as eaten gave 4.8-19.3 g per bowl. The oil is a cooking medium (12.3.2):
    the published scenario leaves it open, the adapted pair takes the clinging share from a sourced row, the served mass leaves the marinade out."""
    est = estimate({"https://a.test/olives": OLIVE_PAGE}, OLIVES_ITEM, TaggingLLM(TAGS))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    oil = next(l for l in s.ingredients if l.name == "olive oil")
    assert oil.conversion.grams is None and "cooking_medium" in oil.flags and oil.blocker == "cooking_medium_unknown_amount" and oil.excluded_from_calculation is None
    assert s.completeness_by_nutrient["saturated_fat_g"] is False                                   # the published list is not complete without the eaten share
    bay = next(l for l in s.ingredients if l.name == "bay")
    assert bay.excluded_from_calculation == "removed_not_eaten" and bay.blocker is None
    assert any(i.kind == "excluded_not_eaten" and i.rule_id == "T-removed" for i in s.inferences)
    pair = next(p for p in est.adapted_pairs if p.derived_from == s.scenario_id)
    a = next(a for a in pair.assumptions if a.ingredient_id == oil.ingredient_id)
    # 12.14.2: every cooking medium gets W09's clinging amount, per plate
    assert a.gap == "G6_cooking_medium" and a.row_id == "W09" and (a.grams_low, a.grams_high) == (D("4.5"), D("13.5")) and a.amount_basis == "per_plate" and "clings" in a.basis
    assert pair.high.calculation_status == "complete"
    # P2 on the snack-bowl card: the served mass is the olives, garlic and the clinging oil, never the 216 g of the marinade
    ps = next(p for p in est.portioned if p.derived_from == pair.pair_id)
    assert ps.applicable and ps.model == "P2" and ps.portion_rule_id == "PR13" and ps.dish_type == "snack_bowl"
    assert D(ps.fraction_high.inputs["M_served_g"]) == D(300) + D(9) and ps.fraction_high.inputs["W_plate_g"] == "100"       # W09 enters per plate, not as recipe mass
    f_high = D(100) / D(ps.fraction_high.inputs["M_served_g"])
    expected = (D(300) * D("2.03") + D(9) * D("0.089")) * f_high / 100 + D("13.5") * D("13.808") / 100
    assert abs(D(ps.high.per_portion["saturated_fat_g"]["total_with_inferences"]) - expected) < D("0.01")
    assert "cooking_medium_open" in s.flags


def test_a_near_zero_brine_is_left_out_entirely_and_a_fatty_medium_stays_open():
    page = recipe_page("Brined Tomatoes", ["600 g tomatoes", "2 cups brine", "1 cup olive oil"], steps="Soak the tomatoes in the brine, drain, dress with the oil. Serve.")
    est = estimate({"https://a.test/b": page}, MenuItem(name="HEIRLOOM TOMATOES", description="", section="TO START"), TaggingLLM({"brine": ("cooking_medium", "plain_food")}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    brine = next(l for l in s.ingredients if l.name == "brine")
    assert brine.excluded_from_calculation == "cooking_medium_negligible" and brine.tag_role == "cooking_medium"       # salt record: 0 g, 0 mg: nothing to count
    oil = next(l for l in s.ingredients if l.name == "olive oil")
    assert oil.conversion.grams == D(216) and oil.tag_role == "eaten"                                                    # dressing oil is eaten, as the recipe says


def test_when_the_tag_call_fails_the_text_patterns_decide_and_the_near_zero_rule_is_off():
    page = recipe_page("Fried Olives", ["300 g green olives", "2 cups olive oil, for frying", "zest of lemon"], steps="Fry the olives in the oil. Serve.")
    est = estimate({"https://a.test/f": page}, MenuItem(name="CRISPY OLIVES", description="", section="BAR SNACKS"), TaggingLLM(TAGS, break_tags=True))
    assert any("line tags unavailable" in n and "12.3.4" in n for n in est.notes)
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    oil = next(l for l in s.ingredients if "oil" in l.name)
    assert oil.conversion.grams is None and "frying_fat_stated_not_consumed" in oil.flags and oil.tag_role == ""       # 3C pattern, not a tag
    zest = next(l for l in s.ingredients if "zest" in l.name)
    assert zest.excluded_from_calculation is None and zest.blocker == "seasoning_unknown_quantity"                         # 12.4(b) needs a tag: not applied


# -- 12.4: lines that cannot move the result; the P2 weight rule ------------------------------------------------------------------------


def test_lemon_zest_and_stand_in_salt_pass_the_composition_test_and_salsa_verde_is_held():
    page = recipe_page("Olives with Salsa Verde", ["300 g green olives", "zest of lemon", "Maldon sea salt", "salsa verde", "red onion"], steps="Mix. Serve.")
    est = estimate({"https://a.test/o": page}, OLIVES_ITEM, TaggingLLM(TAGS))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    by = {l.name: l for l in s.ingredients}
    assert by["zest of lemon"].excluded_from_calculation == "negligible_composition" and by["zest of lemon"].blocker is None       # lemon peel 0.039 g, 0 mg
    assert by["maldon sea salt"].excluded_from_calculation == "negligible_composition" and by["maldon sea salt"].match.match_type == "proxy"   # a stand-in is allowed
    assert by["salsa verde"].excluded_from_calculation is None and by["salsa verde"].blocker == "unknown_quantity" and by["salsa verde"].tag_kind == "prepared_product"
    assert by["red onion"].excluded_from_calculation == "negligible_composition"                                                     # onions 0.042 g, 0 mg, a plain food
    inf = [i for i in s.inferences if i.rule_id == "I04"]
    assert {i.name for i in inf} == {"zest of lemon", "maldon sea salt", "red onion"} and all("12.14.12" in i.detail for i in inf)
    assert s.completeness_basis["saturated_fat_g"] == "incomplete"                                                                 # salsa verde still holds it
    # P2 (12.4.4): salt and zest are weightless; the whole red onion still has mass and stops the plate-weight model
    ps = next(p for p in est.portioned if p.derived_from == s.scenario_id)
    assert not ps.applicable and "red onion" in ps.not_applicable_reason and "zest" not in ps.not_applicable_reason


def test_a_recipe_held_only_by_weightless_near_zero_lines_becomes_estimable():
    """The Greyhound's Sicilian olives (2026-11-05): the only open line was 'thin strips lemon peel'. With 12.4(b) the peel counts as zero, is weightless
    for P2, and the dish gets a range (complete_with_inferences, never source_complete)."""
    from roli_agent.recipes.compare_dishes import ExternalEvidence, scenario_interval
    page = recipe_page("Sicilian Olives", ["300 g green olives", "lemon zest", "Maldon sea salt"], steps="Toss. Serve.")     # no oil line: 12.12.1 makes it a medium, which is not this test
    est = estimate({"https://a.test/s": page}, MenuItem(name="SICILIAN OLIVES", description="Fine Herbs", section="BAR SNACKS"), TaggingLLM({}))
    (s,) = [x for x in est.scenarios if x.status == "calculated"]
    assert s.completeness_basis["saturated_fat_g"] == "complete_with_inferences" and s.calculation["totals"]["saturated_fat_g"]["complete"] is True
    pub = next(p for p in est.portioned if p.derived_from == s.scenario_id)
    assert pub.applicable and pub.portion_rule_id == "PR13"
    iv = scenario_interval(s, None, pub, None, "saturated_fat_g", ExternalEvidence.load())
    assert iv.tier == "complete_with_inferences" and iv.high is not None and (iv.served_mass_low, iv.served_mass_high) == (D(50), D(100))


# -- 12.2: cards, the evidence rule, the rebuilt record ------------------------------------------------------------------------------------


def test_dish_types_and_cards_for_the_new_families():
    assert dish_type_for(MenuItem(name="CORNISH FISH & CHIPS", description="Mushy Peas, Tartar sauce", section="PUB CLASSICS")) == "fish_and_chips"
    assert dish_type_for(MenuItem(name="Haddock and chips", description="", section="MAINS")) == "fish_and_chips"
    assert dish_type_for(MenuItem(name="Marinated olives", description="", section="")) == "snack_bowl"
    assert dish_type_for(MenuItem(name="SICILIAN OLIVES", description="Fine Herbs", section="BAR SNACKS")) == "snack_bowl"
    assert dish_type_for(MenuItem(name="Smoked almonds", description="", section="SNACKS")) == "snack_bowl"
    assert dish_type_for(MenuItem(name="Olive and tomato salad", description="", section="")) == "leaf_salad_starter"       # a salad stays a salad
    anchovies = MenuItem(name="House-cured anchovies with celery, Parmigiano-Reggiano, and coquillo olives", description="", section="")
    assert dish_type_for(anchovies) == "vegetable_starter"                                                                  # olives at the end of the name do not make a snack bowl (Zuni, 2026-11-05)
    rules = PortionRules.load()
    olives, nuts = rules.card_for("snack_bowl", "sicilian olives fine herbs"), rules.card_for("snack_bowl", "smoked almonds")
    assert olives.id == "PR13" and nuts.id == "PR14" and rules.card_for("snack_bowl", "crisps") is None
    assert [f.sat_fat_g for f in olives.figures_on("per_plate")] == [D("1.4")] and len({f.group for f in olives.figures_on("per_100g")}) == 5 and "Pizza Express" in olives.ref_sources
    fc = rules.card_for("fish_and_chips", "cornish fish & chips")
    assert fc.id == "PR15" and fc.figures_on("per_100g") == [] and len(fc.figures_on("per_plate")) == 12 and sorted(fc.choices) == ["fish", "oil", "potato"]
    assert [c.fdc_id for c in fc.choices["fish"]] == [171955, 171964, 175129] and fc.choices["oil"][1].named_in("fried in beef dripping") and not fc.choices["oil"][1].named_in("cod and chips")
    sea_bass = rules.card_for("fish_main", "sea bass")                                                                         # 3I: PR02 carries MenuStat figures, so it is a card and is checked
    assert sea_bass.id == "PR02" and len(sea_bass.figures_on("per_plate")) == 2 and "MenuStat" in sea_bass.ref_sources
    # the evidence rule (12.2.2) and 12.16.8: unsourced rows are listed and never used; after the second 3I rebuild (Bonefish, Wasabi, YO!, Zizzi, Vapiano sheets) they are the two with no USDA share
    assert {r.id for r in rules.unsourced()} == {"PR06", "PR08"}
    assert [r.id for r in rules.for_dish_type("crudo_starter", "bluefin crudo", allow_unsourced=False)] == ["PR03"] and [r.id for r in rules.for_dish_type("vegetable_starter", "padron peppers", allow_unsourced=False)] == ["PR10"]
    assert [r.id for r in rules.for_dish_type("snack_bowl", "olives", allow_unsourced=False)] == ["PR13"]
    assert rules.for_dish_type("fish_and_chips", "fish & chips")[0].id == "PR15" and rules.for_dish_type("fish_and_chips")[0].sourced


def test_parse_choices_reads_the_card_syntax():
    c = parse_choices("fish: 171955 Fish, cod, Atlantic, raw [cod] | 171964 Fish, haddock, raw; oil: 2710180 Vegetable oil, NFS [vegetable oil, rapeseed oil]")
    assert [x.keywords for x in c["fish"]] == [["cod"], ["haddock"]] and c["oil"][0].keywords == ["vegetable oil", "rapeseed oil"] and c["oil"][0].fdc_id == 2710180


def test_rebuild_falls_back_to_the_record_when_an_input_cannot_be_resolved():
    from roli_agent.recipes.adapt import WeightsTable
    from roli_agent.recipes.survey import estimate_survey_dish
    from test_mvp_local import SurveyFakeService
    svc = SurveyFakeService(rebuild=True)
    svc.default_searches.pop("salt, table")                                                     # one input no longer resolves by exact description
    est = estimate_survey_dish(MenuItem(name="FISH & CHIPS", description="", section="MAINS"), "fish_and_chips", service=svc, rules=PortionRules.load(), weights=WeightsTable.load())
    fish = est.components[0]
    assert fish.rebuilt is None and "input 'Salt, table' could not be resolved" in fish.choice and est.applicable
    chips = est.components[1]                                                                    # both records list salt, so neither can follow the fat
    assert chips.rebuilt is None and chips.description == "Potato, french fries, from fresh, fried" and est.choice_ranges == {}
    pr12 = next(r for r in PortionRules.load().rows if r.id == "PR12")
    assert abs(D(est.totals["saturated_fat_g"]["low"]) - (D("131.4") * D("2.83") + pr12.low * D("1.76")) / 100) < D("0.01")   # the records' own values; chips at PR12's low
