"""Optional end-to-end run with the real model (Gemini via OpenRouter) and the real USDA API.

    ROLI_LIVE_TESTS=1 .venv/bin/python -m pytest roli_agent/tests/test_live.py -v -s

Costs a few model calls and about six USDA requests. Latencies are printed for the checkpoint.
"""

from __future__ import annotations

import os
import time

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("ROLI_LIVE_TESTS") != "1", reason="set ROLI_LIVE_TESTS=1 for live calls")

from conftest import ROOT  # noqa: E402

PHOTO_03 = ROOT / "menu_test_set" / "telegram_1280" / "menu_03_own_IMG_5185.jpg"


@pytest.fixture(scope="module")
def graph():
    from roli_agent import build_graph
    return build_graph()


def timed(graph, **kwargs):
    t = time.perf_counter()
    state = graph.invoke({"trace": [], **kwargs})
    return state, time.perf_counter() - t


def test_live_chinook(graph):
    state, s = timed(graph, text="Using USDA, tell me the saturated fat and cholesterol per 100g of cooked Chinook salmon.", photo_path=None)
    print(f"\n[live] chinook {s:.1f}s | {state['trace']}\n{state['response']}")
    assert state["selected_fdc_id"] == 171999
    assert "- Saturated fat: 3.214 g" in state["response"] and "- Cholesterol: 85 mg" in state["response"]


def test_live_pink(graph):
    state, s = timed(graph, text="Using USDA, tell me the saturated fat and cholesterol per 100g of cooked Pink salmon.", photo_path=None)
    print(f"\n[live] pink {s:.1f}s | {state['trace']}\n{state['response']}")
    assert state["selected_fdc_id"] == 172001
    assert "- Saturated fat: 0.971 g" in state["response"] and "- Cholesterol: 55 mg" in state["response"]


def test_live_king_salmon(graph):
    state, s = timed(graph, text="Find the USDA nutritional information for King salmon cooked with dry heat.", photo_path=None)
    print(f"\n[live] king {s:.1f}s | {state['trace']}\n{state['response']}")
    assert state["selected_fdc_id"] == 171999
    assert "mackerel" not in state["response"].lower()


def test_live_menu_photo(graph):
    state, s = timed(graph, text="Hey, what should I order?", photo_path=str(PHOTO_03))
    print(f"\n[live] menu {s:.1f}s | {state['trace']}\n{state['response'][:1200]}")
    assert state["intent"] == "menu" and state["menu_error"] is None
    names = {i.get("name", "").upper() for i in state["menu"]["items"]}
    assert "BLUEFIN CRUDO" in names and len(names) >= 15
    assert "Nutrition for whole dishes is not available yet" in state["response"]
