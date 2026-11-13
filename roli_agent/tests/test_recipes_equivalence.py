"""D22: an equivalent USDA record with usable household measures may replace one that cannot weigh the line,
under five deterministic conditions. Real records: 748608 "Oil, olive, extra virgin" (Foundation), 171413
"Oil, olive, salad or cooking" (SR Legacy), 1750351 "Oil, olive, extra light" (Foundation)."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from roli_nutrition.portions import extract_portions

from roli_agent.recipes.convert import convert_with_portions
from roli_agent.recipes.equivalence import EquivalentRecordPolicy, equivalent_values, same_food_head
from roli_agent.recipes.models import MatchDecision
from roli_agent.recipes.parse import parse_line

from conftest import load, make_service, mutate

EVOO, OLIVE, LIGHT, CHINOOK, PINK, ROMANO = 748608, 171413, 1750351, 171999, 172001, 171249
D = Decimal


def service_with(overrides: dict | None = None):
    bodies = {fid: load(f"food_{fid}") for fid in (EVOO, OLIVE, LIGHT, CHINOOK, PINK, ROMANO)}
    bodies.update(overrides or {})

    def respond(request: httpx.Request) -> httpx.Response:
        import re
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        return httpx.Response(200, json=bodies[fid]) if fid in bodies else httpx.Response(404, content=b"")
    return make_service(respond)


def decision(fdc_id, description, data_type, candidates, match_type="direct"):
    return MatchDecision(name="extra virgin olive oil", preparation_hint="as_used", query="oil olive", fdc_id=fdc_id, description=description,
                         data_type=data_type, match_type=match_type, source="llm", candidates_seen=len(candidates),
                         candidates=[{"fdc_id": f, "description": d, "data_type": t} for f, d, t in candidates])


OLIVE_CANDIDATES = [(EVOO, "Oil, olive, extra virgin", "Foundation"), (OLIVE, "Oil, olive, salad or cooking", "SR Legacy"),
                    (LIGHT, "Oil, olive, extra light", "Foundation"), (171016, "Oil, sesame, salad or cooking", "SR Legacy")]


def test_the_real_olive_oil_records_are_not_equivalent_under_the_approved_tolerance():
    """The documented case, on USDA's own numbers: extra virgin (Foundation) reports 15.4 g saturated fat and no
    cholesterol row; salad-or-cooking (SR Legacy) reports 13.808 g and 0 mg. 11.5 % apart, and one value missing:
    rule 4 refuses. The grade difference is not nutritionally irrelevant here, as D22 warned."""
    service, _ = service_with()
    evoo, olive = service.get_nutrition(EVOO), service.get_nutrition(OLIVE)
    assert (evoo.saturated_fat_g, evoo.cholesterol_mg) == (15.4, None) and (olive.saturated_fat_g, olive.cholesterol_mg) == (13.808, 0.0)
    assert equivalent_values(evoo, olive) is False
    policy = EquivalentRecordPolicy(service)
    line = parse_line("2 tablespoons extra virgin olive oil")
    assert policy.find(line, decision(EVOO, "Oil, olive, extra virgin", "Foundation", OLIVE_CANDIDATES)) is None
    assert any(e.get("why", "").startswith("nutrient values not equivalent") for e in policy.log)


def test_the_extra_virgin_record_converts_from_its_own_millilitre_measure_instead():
    """USDA gives the Foundation record one measure: 100 millilitre = 90.7 g. That density is the record's own (D4)."""
    portions = extract_portions(EVOO, load(f"food_{EVOO}")).portions
    assert [(p.label, p.gram_weight) for p in portions] == [("100 milliliter", 90.7)]
    p = convert_with_portions(parse_line("2 tablespoons extra virgin olive oil"), portions, EVOO)
    assert p.grams == D(2) * D("14.78676478125") * (D("90.7") / D(100)) and "portion_derived_volume" in p.flags
    assert "0.9070 g/ml" in p.grams_reference and "748608" in p.grams_reference


def test_substitution_happens_only_when_all_five_conditions_hold():
    """Make the extra-virgin record equivalent (values copied from the SR Legacy one) and strip its measure: then
    the SR Legacy sibling from the same candidate list is used, recorded as a substitution."""
    def edit(b):
        b["foodPortions"] = []
        for row in b["foodNutrients"]:
            if row["nutrient"]["id"] == 1258:
                row["amount"] = 13.9
        b["foodNutrients"].append({"nutrient": {"id": 1253, "number": "601", "name": "Cholesterol", "unitName": "mg"}, "amount": 0.0})
    service, rec = service_with({EVOO: mutate(load(f"food_{EVOO}"), edit)})
    policy = EquivalentRecordPolicy(service)
    line = parse_line("2 tablespoons extra virgin olive oil")
    found = policy.find(line, decision(EVOO, "Oil, olive, extra virgin", "Foundation", OLIVE_CANDIDATES))
    assert found is not None
    replacement, converted = found
    assert (replacement.fdc_id, replacement.substituted_for, replacement.source, replacement.match_type) == (OLIVE, EVOO, "d22", "direct")
    assert converted.grams == D(27) and "d22_equivalent_record" in converted.flags and "171413" in converted.grams_reference
    assert "D22" in replacement.reason
    # the sesame-oil candidate was never considered: a different food head ("Oil, sesame")
    assert not any(e.get("rejected") == 171016 for e in policy.log)
    assert not any(str(r.url).endswith("/171016") for r in rec.requests)


def test_no_substitution_across_preparation_states_or_unrelated_foods():
    service, _ = service_with()
    policy = EquivalentRecordPolicy(service)
    line = parse_line("2 fillets salmon")
    # cooked chinook (no usable count measure for "2 fillets"? it has '0.5 fillet'): force the policy by giving a record with no measures
    cooked_no_measures = mutate(load(f"food_{CHINOOK}"), lambda b: b.__setitem__("foodPortions", []))
    service2, _ = service_with({CHINOOK: cooked_no_measures})
    policy2 = EquivalentRecordPolicy(service2, allow_whole_items=True)      # a count line: eligible only with the flag; the state rule is what this tests
    raw_sibling = [(CHINOOK, "Fish, salmon, chinook, cooked, dry heat", "SR Legacy"), (173688, "Fish, salmon, chinook, raw", "SR Legacy")]
    assert policy2.find(line, decision(CHINOOK, "Fish, salmon, chinook, cooked, dry heat", "SR Legacy", raw_sibling)) is None
    assert any(e.get("why") == "preparation state differs" for e in policy2.log)
    # pink salmon for chinook: same first two words ("Fish, salmon") but the values differ (0.971 vs 3.214 g): refused on the numbers
    other = [(CHINOOK, "Fish, salmon, chinook, cooked, dry heat", "SR Legacy"), (PINK, "Fish, salmon, pink, cooked, dry heat", "SR Legacy")]
    assert policy2.find(line, decision(CHINOOK, "Fish, salmon, chinook, cooked, dry heat", "SR Legacy", other)) is None
    # romano cheese for olive oil: different head, never looked at
    assert policy.find(parse_line("1 cup olive oil"), decision(EVOO, "Oil, olive, extra virgin", "Foundation", [(ROMANO, "Cheese, romano", "SR Legacy")])) is None
    assert same_food_head("Oil, olive, extra virgin", "Oil, olive, salad or cooking") and not same_food_head("Oil, olive", "Oil, sesame")


def test_policy_is_inert_when_nothing_needs_a_measure_or_when_disabled():
    service, rec = service_with()
    policy = EquivalentRecordPolicy(service)
    assert policy.find(parse_line("85 g extra virgin olive oil"), decision(EVOO, "Oil, olive, extra virgin", "Foundation", OLIVE_CANDIDATES)) is None
    assert policy.find(parse_line("olive oil, for drizzling"), decision(EVOO, "Oil, olive, extra virgin", "Foundation", OLIVE_CANDIDATES)) is None
    assert rec.requests == []
    off = EquivalentRecordPolicy(service, enabled=False)
    assert off.find(parse_line("2 tbsp extra virgin olive oil"), decision(EVOO, "Oil, olive, extra virgin", "Foundation", OLIVE_CANDIDATES)) is None


def test_candidates_are_carried_on_decisions_and_the_policy_never_leaves_them():
    from roli_agent.llm import parse_json_object
    from roli_agent.recipes.match import MatchRequest, UsdaMatcher
    from recipe_test_helpers import RuleLLM, make_usda, OLIVE as O
    svc, _ = make_usda()
    decisions, _ = UsdaMatcher(svc, RuleLLM(), parse_json_object=parse_json_object).match([MatchRequest("extra-virgin olive oil", "as_used")])
    d = decisions[MatchRequest("extra-virgin olive oil", "as_used").key]
    assert d.candidates == [{"fdc_id": O, "description": "Oil, olive, salad or cooking", "data_type": "SR Legacy"}]


def test_no_substitution_when_the_physical_form_differs_even_with_equivalent_values():
    """Found in the live replay: 'Oranges, raw, all commercial varieties' (sizes listed, line names none -> unresolved under D20)
    was replaced by 'Oranges, raw, with peel' (one unsized '1 fruit' label) because the nutrients are equivalent. A peeled
    and an unpeeled orange are different things to weigh; rule 3 now refuses it."""
    def orange(fid, description, portions):
        body = mutate(load(f"food_{OLIVE}"), lambda b: (b.__setitem__("fdcId", fid), b.__setitem__("description", description), b.__setitem__("foodPortions", portions)))
        for row in body["foodNutrients"]:
            if row["nutrient"]["id"] == 1258:
                row["amount"] = 0.02
        return body
    commercial = orange(169097, "Oranges, raw, all commercial varieties", [
        {"amount": 1.0, "modifier": 'small (2-3/8" dia)', "gramWeight": 96.0, "measureUnit": {"name": "undetermined"}},
        {"amount": 1.0, "modifier": 'large (3-1/16" dia)', "gramWeight": 184.0, "measureUnit": {"name": "undetermined"}}])
    with_peel = orange(169919, "Oranges, raw, with peel", [{"amount": 1.0, "modifier": "fruit without seeds", "gramWeight": 159.0, "measureUnit": {"name": "undetermined"}}])
    service, _ = service_with({169097: commercial, 169919: with_peel})
    policy = EquivalentRecordPolicy(service, allow_whole_items=True)      # even with whole items allowed, the form rule refuses it
    line = parse_line("1/2 orange (juiced)")
    cands = [(169097, "Oranges, raw, all commercial varieties", "SR Legacy"), (169919, "Oranges, raw, with peel", "SR Legacy")]
    d = MatchDecision(name="orange", preparation_hint="raw", query="oranges raw", fdc_id=169097, description="Oranges, raw, all commercial varieties",
                      data_type="SR Legacy", match_type="direct", source="llm", candidates=[{"fdc_id": f, "description": dd, "data_type": t} for f, dd, t in cands])
    assert policy.find(line, d) is None
    assert any(e.get("why") == "physical form differs" for e in policy.log)
    # and by default a count line is not eligible at all (rule 6): no lookups, no log entries
    strict, rec = service_with({169097: commercial, 169919: with_peel})
    default_policy = EquivalentRecordPolicy(strict)
    assert default_policy.find(line, d) is None and default_policy.log == [] and rec.requests == []
    from roli_agent.recipes.equivalence import form_words
    assert form_words("Oil, olive, extra virgin") == form_words("Oil, olive, salad or cooking") == frozenset()
    assert form_words("Fish, anchovy, european, canned in oil, drained solids") == {"canned", "in oil", "drained"}
