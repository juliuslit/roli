"""O: the core pulls in none of MCP, LangGraph, LangChain, uvicorn or python-dotenv."""

from __future__ import annotations

import json
import subprocess
import sys

FORBIDDEN = {"mcp", "langgraph", "langchain", "uvicorn", "dotenv"}

PROBE = """
import json, sys
import roli_nutrition
roli_nutrition.get_nutrition  # touch the module-level function without calling it
loaded = sorted({m.split(".")[0] for m in sys.modules})
print(json.dumps(loaded))
"""


def test_o_core_imports_no_forbidden_modules():
    completed = subprocess.run(
        [sys.executable, "-I", "-c", PROBE],
        capture_output=True, text=True, check=True, timeout=60,
    )
    loaded = set(json.loads(completed.stdout.strip().splitlines()[-1]))
    assert "roli_nutrition" in loaded
    assert loaded & FORBIDDEN == set(), f"core imported: {loaded & FORBIDDEN}"
    assert "httpx" in loaded and "pydantic" in loaded
