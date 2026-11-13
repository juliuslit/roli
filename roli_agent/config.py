"""Settings for the agent. Secrets come from roli/.env through the harness's config module."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One model for interpretation, record selection and menu reading. Chosen 2026-11-02:
# Gemini 3.8 Flash was the best menu reader in round one. Override with ROLI_MODEL.
DEFAULT_MODEL_ID = "google/gemini-3.8-flash"
MODEL_ID = os.environ.get("ROLI_MODEL", DEFAULT_MODEL_ID)

# A user is waiting, so interpretation and selection calls get a short cap. Menu reading
# keeps the harness's longer limits because a dense menu takes a while to write out.
LLM_TIMEOUT_SECONDS = float(os.environ.get("ROLI_LLM_TIMEOUT_SECONDS", "60"))
SHORT_ANSWER_TOKENS = 1000
# Phase 2B-2 batched calls (relevance rubric, USDA queries and selections for up to 12 ingredients) write longer JSON.
BATCH_ANSWER_TOKENS = 6000
BATCH_TIMEOUT_SECONDS = float(os.environ.get("ROLI_BATCH_TIMEOUT_SECONDS", "120"))

MENU_PROMPT_VERSION = os.environ.get("ROLI_MENU_PROMPT", "v5")  # menu_reader_eval/prompts/menu_reader_v5.md
SEARCH_LIMIT = 10
