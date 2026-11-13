"""Shared test helpers: fixture loader, mutate(), recording mock transport, fake clock.

All tests use a fake key, ``SENTINEL_KEY_123``. An autouse check asserts it never
appears in any log line.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Callable, Iterable

import httpx
import pytest

from roli_nutrition import NutritionService, Settings
from roli_nutrition.usda_client import UsdaClient

FIXTURES = Path(__file__).parent / "fixtures" / "usda"
SENTINEL_KEY = "SENTINEL_KEY_123"

FOOD_171999 = 171999  # Fish, salmon, chinook, cooked, dry heat
FOOD_172001 = 172001  # Fish, salmon, pink, cooked, dry heat


# -- fixtures on disk -------------------------------------------------------


def load(name: str) -> Any:
    """Load ``tests/fixtures/usda/<name>.json`` (a real saved USDA reply)."""
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Fixture {path.name} is missing. Run scripts/capture_fixtures.py with the real key first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(body: Any, edit: Callable[[Any], None]) -> Any:
    """Return a deep copy of ``body`` after applying ``edit`` to the copy."""
    clone = copy.deepcopy(body)
    edit(clone)
    return clone


def error_response(name: str) -> httpx.Response:
    """Turn a saved ``{status, body}`` error fixture back into an httpx.Response."""
    saved = load(name)
    body = saved["body"]
    if isinstance(body, str):
        return httpx.Response(saved["status"], content=body.encode("utf-8"))
    return httpx.Response(saved["status"], json=body)


# -- mock transport ---------------------------------------------------------


class Recorder:
    """A mock-transport handler that records every request it sees.

    ``responder`` is either a callable ``request -> Response`` or an iterable of
    items, each an ``httpx.Response`` to return or an ``Exception`` to raise.
    """

    def __init__(self, responder: Callable[[httpx.Request], httpx.Response] | Iterable) -> None:
        self.requests: list[httpx.Request] = []
        if callable(responder):
            self._next = responder
        else:
            items = iter(list(responder))

            def _next(request: httpx.Request) -> httpx.Response:
                item = next(items)
                if isinstance(item, Exception):
                    raise item
                return item

            self._next = _next

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._next(request)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)


def food_router(search_fixture: str = "search_king_salmon") -> Callable[[httpx.Request], httpx.Response]:
    """Serve the real saved replies for 171999, 172001 and one search; 404 for anything else."""
    bodies = {
        f"/fdc/v1/food/{FOOD_171999}": load("food_171999"),
        f"/fdc/v1/food/{FOOD_172001}": load("food_172001"),
    }
    search_body = load(search_fixture)

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/fdc/v1/foods/search":
            return httpx.Response(200, json=search_body)
        body = bodies.get(request.url.path)
        if body is None:
            return httpx.Response(404, content=b"")
        return httpx.Response(200, json=body)

    return respond


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def make_settings(**overrides) -> Settings:
    values = {"api_key": SENTINEL_KEY, "cache_ttl_seconds": 86400.0, "cache_max_entries": 1000}
    values.update(overrides)
    return Settings(**values)


def make_service(
    responder,
    *,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
    **settings_overrides,
) -> tuple[NutritionService, Recorder]:
    """A service wired to a recording mock transport instead of the real USDA."""
    recorder = Recorder(responder)
    client = UsdaClient(SENTINEL_KEY, transport=recorder.transport, sleep=sleep or SleepRecorder())
    service = NutritionService(make_settings(**settings_overrides), client=client, clock=clock or FakeClock())
    return service, recorder


# -- pytest fixtures ----------------------------------------------------------


@pytest.fixture(autouse=True)
def no_secret_in_logs(caplog):
    """Test K: the key never appears in any log line, in any test."""
    caplog.set_level(logging.DEBUG)
    yield
    assert SENTINEL_KEY not in caplog.text, "API key leaked into a log line"


@pytest.fixture
def chinook_body() -> dict:
    return load("food_171999")


@pytest.fixture
def pink_body() -> dict:
    return load("food_172001")
