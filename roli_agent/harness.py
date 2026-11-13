"""Bridge to the menu-reader evaluation harness in code/.

The harness is a set of scripts, not a package, and its modules import each other by bare
name (``from config import ...``). This shim puts ``code/`` on ``sys.path`` once and re-exports
the pieces the agent reuses, so the OpenRouter routing, privacy and temperature decisions
recorded in code/menu_reader.py are used, not copied. Nothing in code/ is changed.
"""

from __future__ import annotations

import sys

from .config import ROOT

CODE_DIR = ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import config as harness_config  # noqa: E402  (code/config.py: paths, keys, loads roli/.env)
import menu_reader as harness_menu_reader  # noqa: E402  (code/menu_reader.py: model settings)

OPENROUTER_URL = harness_config.OPENROUTER_URL
OPENROUTER_API_KEY = harness_config.OPENROUTER_API_KEY
TEST_SET = harness_config.TEST_SET

TEMPERATURE = harness_menu_reader.TEMPERATURE
MAX_ANSWER_TOKENS = harness_menu_reader.MAX_ANSWER_TOKENS
CALL_TIMEOUT_SECONDS = harness_menu_reader.CALL_TIMEOUT_SECONDS
provider_order = harness_menu_reader.provider_order
reasoning_setting = harness_menu_reader.reasoning_setting
load_prompt = harness_menu_reader.load_prompt  # 'v5' -> text of menu_reader_eval/prompts/menu_reader_v5.md
