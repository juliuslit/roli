"""2B-2 USDA matching (spec 7, D7): batched 1E path, the guard, the state check, the cache."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage

from roli_agent.llm import parse_json_object
from roli_agent.recipes.match import MatchCache, MatchRequest, UsdaMatcher

from recipe_test_helpers import BLUEFIN, CHINOOK, OLIVE, ROMANO, RuleLLM, make_usda


def matcher(llm=None, cache=None, searches=None):
    service, rec = make_usda(searches)
    return UsdaMatcher(service, llm or RuleLLM(), parse_json_object=parse_json_object, cache=cache), rec


def test_batch_matches_direct_proxy_and_unresolved_with_two_llm_calls():
    m, rec = matcher()
    llm = m._llm
    decisions, log = m.match([MatchRequest("sushi-grade bluefin tuna", "raw"), MatchRequest("extra-virgin olive oil", "as_used"),
                              MatchRequest("pecorino sardo", "as_used"), MatchRequest("flaky salt", "as_used"), MatchRequest("chives", "unknown"),
                              MatchRequest("extra-virgin olive oil", "as_used")])        # duplicate resolved once
    assert log.requested == 6 and log.distinct == 5 and log.llm_calls == 2 and log.usda_searches == 7   # 5 queries + 2 plain-name retries (salt, chives) that also find nothing
    tuna = decisions[MatchRequest("sushi-grade bluefin tuna", "raw").key]
    assert (tuna.fdc_id, tuna.match_type, tuna.record_state, tuna.query) == (BLUEFIN, "direct", "raw", "tuna bluefin raw")
    sardo = decisions[MatchRequest("pecorino sardo", "as_used").key]
    assert (sardo.fdc_id, sardo.match_type, sardo.description) == (ROMANO, "proxy", "Cheese, romano")
    salt = decisions[MatchRequest("flaky salt", "as_used").key]
    assert salt.fdc_id is None and salt.match_type == "unresolved" and salt.issue == "no_candidates"
    assert "test selection" in tuna.reason                                    # LLM sentence kept for provenance
    searched = [json.loads(r.content)["query"] for r in rec.requests if r.method == "POST"]
    assert len(searched) == 7 and "flaky salt" in searched and "chives" in searched


def test_guard_rejects_an_id_usda_did_not_return():
    m, rec = matcher(llm=RuleLLM(foreign_id=999999))
    decisions, _ = m.match([MatchRequest("extra-virgin olive oil", "as_used")])
    d = decisions[MatchRequest("extra-virgin olive oil", "as_used").key]
    assert d.fdc_id is None and d.issue == "guard_rejected" and d.match_type == "unresolved"
    assert not any(r.url.path.endswith("/999999") for r in rec.requests)        # the foreign ID is never looked up


def test_state_conflict_makes_the_ingredient_unresolved():
    m, _ = matcher()
    decisions, _ = m.match([MatchRequest("king salmon fillets", "raw")])          # only a cooked chinook record exists
    d = decisions[MatchRequest("king salmon fillets", "raw").key]
    assert d.fdc_id is None and d.issue == "state_conflict:raw_vs_cooked" and d.description == "Fish, salmon, chinook, cooked, dry heat"
    ok, _ = matcher()[0].match([MatchRequest("cooked chinook salmon", "cooked")])
    assert ok[MatchRequest("cooked chinook salmon", "cooked").key].fdc_id == CHINOOK


def test_cache_serves_validated_decisions_and_keeps_proxies_proxies(tmp_path):
    cache = MatchCache(tmp_path / "m.json", clock=lambda: 1_000.0)
    m, rec = matcher(cache=cache)
    m.match([MatchRequest("pecorino sardo", "as_used"), MatchRequest("flaky salt", "as_used")])
    assert len(cache) == 1                                                        # unresolved salt is not cached
    m2, rec2 = matcher(cache=MatchCache(tmp_path / "m.json", clock=lambda: 1_000.0))
    decisions, log = m2.match([MatchRequest("pecorino sardo", "as_used")])
    d = decisions[MatchRequest("pecorino sardo", "as_used").key]
    assert d.source == "cache" and d.match_type == "proxy" and d.fdc_id == ROMANO
    assert log.cache_hits == 1 and log.llm_calls == 0 and rec2.requests == []
    stale, _ = matcher(cache=MatchCache(tmp_path / "m.json", clock=lambda: 1_000.0 + 31 * 24 * 3600))
    _, log3 = stale.match([MatchRequest("pecorino sardo", "as_used")])
    assert log3.cache_hits == 0 and log3.llm_calls == 2                           # expired after 30 days


def test_cache_key_separates_preparation_states():
    assert MatchRequest("Salmon  Fillets", "raw").key == "salmon fillets|raw"
    assert MatchRequest("salmon fillets", "cooked").key != MatchRequest("salmon fillets", "raw").key


class BrokenQueryLLM(RuleLLM):
    def invoke(self, messages):
        text = messages[-1].content
        if text.startswith("You write search queries"):
            self.prompts.append(text)
            return AIMessage(content='{"queries": [{"id": 1, "usda_query": "oil olive 171413"}, {"id": 2, "usda_query": 5}]}')
        return super().invoke(messages)


def test_unusable_query_replies_fall_back_to_the_ingredient_name():
    m, rec = matcher(llm=BrokenQueryLLM(), searches={"olive oil": [OLIVE], "oil olive 171413": [ROMANO]})
    decisions, log = m.match([MatchRequest("olive oil", "as_used"), MatchRequest("pecorino sardo", "as_used")])
    searched = [json.loads(r.content)["query"] for r in rec.requests if r.method == "POST"]
    assert "olive oil" in searched and "oil olive 171413" not in searched        # digits in a query are refused; name used instead
    assert log.llm_failures == 0 and any("_QueryRow row rejected" in n for n in log.notes)   # only the malformed row (id 2) is dropped
    assert decisions[MatchRequest("olive oil", "as_used").key].fdc_id == OLIVE


def test_usda_error_is_recorded_not_fatal():
    import httpx

    def down(request):
        return httpx.Response(503, content=b"")
    from conftest import make_service
    service, _ = make_service(down)
    m = UsdaMatcher(service, RuleLLM(), parse_json_object=parse_json_object)
    decisions, log = m.match([MatchRequest("olive oil", "as_used")])
    d = decisions[MatchRequest("olive oil", "as_used").key]
    assert d.issue == "usda_error:usda_unavailable" and d.fdc_id is None and log.llm_calls == 1   # no selection call without candidates


def test_one_plain_name_retry_when_the_models_query_finds_nothing():
    """The model writes 'pork cured prosciutto', USDA returns nothing; the plain name 'prosciutto' is tried once, and the
    usual guards apply to what it returns. A query that already is the plain name is not retried."""
    class Prosciutto(RuleLLM):
        def __init__(self):
            super().__init__(queries={"prosciutto": ("pork cured prosciutto", ROMANO, "proxy"), "romano": ("romano", ROMANO, "direct")})
    m, rec = matcher(llm=Prosciutto(), searches={"pork cured prosciutto": [], "prosciutto": [ROMANO], "romano": []})
    decisions, log = m.match([MatchRequest("prosciutto", "as_used"), MatchRequest("romano", "as_used")])
    d = decisions[MatchRequest("prosciutto", "as_used").key]
    assert d.retried_with_plain_name is True and d.query == "prosciutto" and d.fdc_id == ROMANO and d.match_type == "proxy"
    r = decisions[MatchRequest("romano", "as_used").key]
    assert r.retried_with_plain_name is False and r.issue == "no_candidates"
    searched = [json.loads(x.content)["query"] for x in rec.requests if x.method == "POST"]
    assert searched == ["pork cured prosciutto", "prosciutto", "romano"] and log.usda_searches == 3
