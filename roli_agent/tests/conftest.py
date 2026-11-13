"""Test helpers: a scripted LLM, and the nutrition service on the saved real USDA replies.

No network anywhere. USDA is the same httpx mock transport the nutrition service's own
tests use, serving the fixtures captured in Phase 1A; the LLM is a queue of canned answers.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx
import pytest
from langchain_core.messages import AIMessage

from roli_nutrition import NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

from roli_agent.graph import build_graph

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "nutrition_service" / "tests" / "fixtures" / "usda"
MENU_EXPECTED = ROOT / "menu_reader_eval" / "expected"
SENTINEL_KEY = "SENTINEL_KEY_123"

CHINOOK, PINK, MACKEREL = 171999, 172001, 174236


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def mutate(body: Any, edit: Callable[[Any], None]) -> Any:
    clone = copy.deepcopy(body)
    edit(clone)
    return clone


def menu_expected(n: int) -> dict:
    """The answer key for photo n in the menu reader's answer format (readable, problems, items)."""
    return json.loads((MENU_EXPECTED / f"menu_{n:02d}.json").read_text(encoding="utf-8"))["expected"]


# -- scripted LLM -------------------------------------------------------------


class FakeLLM:
    """Returns canned replies in order; records every prompt it was given."""

    def __init__(self, replies: Iterable[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    def invoke(self, messages) -> AIMessage:
        content = messages[-1].content
        self.prompts.append(content if isinstance(content, str) else json.dumps([p.get("type") for p in content]))
        if not self.replies:
            raise AssertionError("FakeLLM was asked for more replies than scripted")
        return AIMessage(content=self.replies.pop(0))


def interpret_reply(food: str, query: str, preparation: str = "cooked", intent: str = "food_lookup") -> str:
    return json.dumps({"intent": intent, "food": food, "usda_query": query, "preparation": preparation})


def select_reply(fdc_id, reason: str = "same food and preparation") -> str:
    return json.dumps({"fdc_id": fdc_id, "reason": reason})


# -- USDA on fixtures ---------------------------------------------------------


class Recorder:
    def __init__(self, responder) -> None:
        self.requests: list[httpx.Request] = []
        if callable(responder):
            self._next = responder
        else:
            items = iter(list(responder))

            def _next(request):
                item = next(items)
                if isinstance(item, Exception):
                    raise item
                return item
            self._next = _next

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._next(request)


SEARCH_FIXTURES = {
    "salmon chinook cooked dry heat": "search_salmon_chinook",
    "king salmon cooked dry heat": "search_king_salmon",
    "salmon pink cooked dry heat": "search_salmon_chinook",  # same list; 172001 is in it
}
FOOD_FIXTURES = {CHINOOK: "food_171999", PINK: "food_172001"}


def usda_router(*, food_override: dict | None = None, search_override: dict | None = None):
    """Serve saved replies: searches by query text, foods by ID; 404 for unknown IDs, empty list for unknown queries."""
    foods = {fid: load(name) for fid, name in FOOD_FIXTURES.items()}
    foods.update(food_override or {})
    searches = {q: load(name) for q, name in SEARCH_FIXTURES.items()}
    searches.update(search_override or {})

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/foods/search"):
            query = json.loads(request.content)["query"]
            return httpx.Response(200, json=searches.get(query, {"totalHits": 0, "foods": []}))
        m = re.search(r"/food/(\d+)$", request.url.path)
        fid = int(m.group(1)) if m else None
        if fid in foods:
            body = foods[fid]
            return body if isinstance(body, httpx.Response) else httpx.Response(200, json=body)
        return httpx.Response(404, content=b"")
    return respond


def make_service(responder) -> tuple[NutritionService, Recorder]:
    rec = Recorder(responder)
    client = UsdaClient(SENTINEL_KEY, transport=httpx.MockTransport(rec), sleep=lambda s: None)
    return NutritionService(Settings(api_key=SENTINEL_KEY), client=client), rec


def make_graph(llm_replies: list[str], responder=None):
    """A compiled graph on a scripted LLM and a fixture-backed USDA; returns (graph, llm, recorder)."""
    service, rec = make_service(responder or usda_router())
    llm = FakeLLM(llm_replies)
    graph = build_graph(llm=llm, service=service, load_prompt=lambda v: "MENU PROMPT " + v)
    return graph, llm, rec


def run(graph, text: str = "", photo_path: str | None = None) -> dict:
    return graph.invoke({"text": text, "photo_path": photo_path, "trace": []})


# -- assertions ---------------------------------------------------------------

_DIGITS = re.compile(r"\d")


def assert_no_nutrition_numbers(response: str, *allowed_ids: int) -> None:
    """A failure reply may show FDC IDs (so the user can see which record) but no other digit:
    no grams, no milligrams, no per-100 g, nothing that could read as a nutrition value."""
    cleaned = response
    for fid in allowed_ids:
        cleaned = cleaned.replace(str(fid), "")
    assert not _DIGITS.search(cleaned), f"unexpected number in a no-values reply:\n{response}"
    for word in (" g\n", " mg", "saturated fat:", "cholesterol:"):
        assert word.lower() not in cleaned.lower(), f"nutrition wording in a no-values reply:\n{response}"


@pytest.fixture
def chinook_body():
    return load("food_171999")
