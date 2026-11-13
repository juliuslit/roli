"""A and B against the real USDA API. Runs only with ROLI_LIVE_TESTS=1 (four USDA calls)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("ROLI_LIVE_TESTS") != "1", reason="set ROLI_LIVE_TESTS=1 to call USDA")

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def live_service():
    from dotenv import load_dotenv

    from roli_nutrition import NutritionService, Settings

    load_dotenv(REPO_ROOT / ".env")
    return NutritionService(Settings.from_env())


def test_live_a_chinook(live_service):
    r = live_service.get_nutrition(171999)
    assert r.status == "complete", getattr(r, "message", None)
    assert r.description == "Fish, salmon, chinook, cooked, dry heat"
    assert r.data_type == "SR Legacy"
    assert (r.saturated_fat_g, r.cholesterol_mg) == (3.214, 85.0)


def test_live_b_pink(live_service):
    r = live_service.get_nutrition(172001)
    assert r.status == "complete", getattr(r, "message", None)
    assert r.description == "Fish, salmon, pink, cooked, dry heat"
    assert (r.saturated_fat_g, r.cholesterol_mg) == (0.971, 55.0)


def test_live_search_king_salmon(live_service):
    r = live_service.search_foods("king salmon cooked dry heat", 10)
    assert r.status == "complete", getattr(r, "message", None)
    assert all(c.data_type in ("SR Legacy", "Foundation") for c in r.candidates)


def test_live_not_found(live_service):
    r = live_service.get_nutrition(99999999)
    assert r.status == "error" and r.error_code == "not_found"
