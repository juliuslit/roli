"""Folder paths and secret keys, in one place.

Every other script imports from here, so a moved folder is fixed once.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # the repo folder
load_dotenv(ROOT / ".env")                             # reads keys into the environment

TEST_SET = ROOT / "menu_test_set"
PHOTOS = TEST_SET / "telegram_1280"                    # the photos the models see
EVAL = ROOT / "menu_reader_eval"
PROMPTS = EVAL / "prompts"
EXPECTED = EVAL / "expected"
RESULTS = ROOT / "results"                             # raw answers and scores land here

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")

DATASET_NAME = "roli-menu-reader"                      # name of the LangSmith dataset


def keys_look_real() -> list[str]:
    """Return a list of problems with the keys; empty list means both look filled in."""
    problems = []
    if not OPENROUTER_API_KEY or "REPLACE_ME" in OPENROUTER_API_KEY:
        problems.append("OPENROUTER_API_KEY is still a placeholder in .env")
    if not LANGSMITH_API_KEY or "REPLACE_ME" in LANGSMITH_API_KEY:
        problems.append("LANGSMITH_API_KEY is still a placeholder in .env")
    return problems


def photo_number(n) -> str:
    """'6' or 6 -> '06'."""
    return f"{int(n):02d}"


def expected_path(n) -> Path:
    return EXPECTED / f"menu_{photo_number(n)}.json"


def prompt_path(version: str) -> Path:
    """'v1' -> menu_reader_eval/prompts/menu_reader_v1.md"""
    return PROMPTS / f"menu_reader_{version}.md"
