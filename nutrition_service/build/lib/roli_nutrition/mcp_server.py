"""Phase 1B: a thin MCP wrapper around ``NutritionService``.

Needs the ``[mcp]`` extra. Nothing in the rest of the package imports this
module, so LangGraph can install and use the core without MCP being present.

What this file adds on top of the service:
- two MCP tools whose JSON is exactly ``service.get_nutrition(...)`` and
  ``service.search_foods(...)`` turned into a dict; each call runs in a worker
  thread so the server's event loop never waits on USDA
- a bearer-token check (``ROLI_MCP_TOKEN``) that answers 401 before any tool
  or USDA code runs
- a ``main()`` that loads ``roli/.env`` and serves ``/mcp`` with uvicorn
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Annotated, Any, Mapping

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import ConfigError, Settings
from .service import DEFAULT_LIMIT, NutritionService

logger = logging.getLogger("roli_nutrition.mcp")

SERVER_NAME = "roli-nutrition"
MCP_PATH = "/mcp"
MIN_TOKEN_CHARS = 32

SEARCH_TOOL = "roli_search_usda_foods"
NUTRITION_TOOL = "roli_get_usda_nutrition"

# Spec 7.3, word for word.
SEARCH_DESCRIPTION = (
    "Search USDA FoodData Central for one ingredient. Returns candidate foods with FDC ID, "
    "USDA's exact description and data type, and no nutrient values; call roli_get_usda_nutrition "
    "with the chosen FDC ID to get those. Searches SR Legacy and Foundation foods only. USDA matches "
    "words, not synonyms: use USDA wording (food, then species or variety, then preparation), e.g. "
    "\"salmon chinook cooked dry heat\", not \"king salmon\". Results are in USDA's order, and the "
    "first is not necessarily right. Pick the candidate whose description names the same food and "
    "preparation. If none does, search again with different words or say that no match was found. "
    "Never invent an FDC ID. Inputs: query (1–200 characters), limit (1–10, default 5)."
)

# Spec 8.4, word for word.
NUTRITION_DESCRIPTION = (
    "Returns saturated fat (g) and cholesterol (mg) per 100 g for exactly one USDA food, identified "
    "by FDC ID. The values belong only to the food named in \"description\" and the \"fdc_id\" in the "
    "same response; never pair them with another food or ID. null means USDA reports no value for "
    "that nutrient: never replace it with zero or an estimate. status is \"complete\", \"partial\" "
    "(one or both values missing) or \"error\" (no values; see error_code). SR Legacy and Foundation "
    "foods only."
)

# Strict: the MCP layer accepts only real JSON integers (no "171999", no true, no 2.0).
# Value rules (>= 1, 1..10) stay in the service so range errors come back in our error shape.
StrictInt = Annotated[int, Field(strict=True)]

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


def read_mcp_token(env: Mapping[str, str] | None = None) -> str:
    """``ROLI_MCP_TOKEN`` from the environment; at least 32 characters. Never logged or echoed."""
    source = os.environ if env is None else env
    token = source.get("ROLI_MCP_TOKEN", "").strip()
    if not token:
        raise ConfigError("ROLI_MCP_TOKEN is missing or blank. The MCP server will not start without it.")
    if len(token) < MIN_TOKEN_CHARS:
        raise ConfigError(f"ROLI_MCP_TOKEN must be at least {MIN_TOKEN_CHARS} characters long.")
    return token


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def create_server(service: NutritionService) -> MCPServer:
    server = MCPServer(SERVER_NAME, instructions=(
        "Two tools for USDA nutrition data. Search first, then fetch by FDC ID. "
        "Every value returned belongs only to the fdc_id in the same response."
    ))

    @server.tool(name=SEARCH_TOOL, description=SEARCH_DESCRIPTION, annotations=READ_ONLY, structured_output=True)
    async def roli_search_usda_foods(query: str, limit: StrictInt = DEFAULT_LIMIT) -> dict[str, Any]:
        result = await anyio.to_thread.run_sync(service.search_foods, query, limit)
        return result.model_dump()

    @server.tool(name=NUTRITION_TOOL, description=NUTRITION_DESCRIPTION, annotations=READ_ONLY, structured_output=True)
    async def roli_get_usda_nutrition(fdc_id: StrictInt) -> dict[str, Any]:
        result = await anyio.to_thread.run_sync(service.get_nutrition, fdc_id)
        return result.model_dump()

    return server


# ---------------------------------------------------------------------------
# Bearer-token middleware (plain ASGI, no SDK auth machinery)
# ---------------------------------------------------------------------------


class BearerTokenMiddleware:
    """Rejects every HTTP request that does not carry ``Authorization: Bearer <token>``.

    Runs before routing, so an unauthorised request never reaches the MCP
    handler, a tool, or USDA. Non-HTTP scopes (lifespan) pass straight through.
    """

    def __init__(self, app, token: str) -> None:
        self._app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        reason = self._check(scope)
        if reason is not None:
            logger.warning(json.dumps({"event": "auth_rejected", "reason": reason, "path": scope.get("path")}))
            await _send_401(send)
            return
        await self._app(scope, receive, send)

    def _check(self, scope) -> str | None:
        """Return None if the header is right, otherwise a short reason (never the header value)."""
        values = [v for k, v in scope.get("headers", []) if k == b"authorization"]
        if not values:
            return "missing"
        if len(values) > 1:
            return "malformed"
        parts = values[0].split(b" ")
        if len(parts) != 2 or parts[0].lower() != b"bearer" or not parts[1]:
            return "malformed"
        if not hmac.compare_digest(parts[1], self._token):
            return "wrong"
        return None


async def _send_401(send) -> None:
    body = json.dumps({"error": "unauthorized", "message": "Missing or invalid bearer token."}).encode()
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"www-authenticate", b"Bearer"),
        ],
    })
    await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------------------
# App and entry point
# ---------------------------------------------------------------------------


def create_app(service: NutritionService, token: str):
    """The ASGI app: token check in front of the SDK's Streamable HTTP endpoint at ``/mcp``.

    ``stateless_http=True``: every request stands alone, no session to keep.
    ``json_response=True``: plain JSON replies instead of server-sent events.
    Returns the wrapped app; the inner Starlette app is reachable as ``.inner``
    because tests have to run its lifespan by hand.
    """
    server = create_server(service)
    inner = server.streamable_http_app(streamable_http_path=MCP_PATH, stateless_http=True, json_response=True)
    app = BearerTokenMiddleware(inner, token)
    app.inner = inner  # type: ignore[attr-defined]
    return app


def create_app_from_env(env: Mapping[str, str] | None = None):
    """Build the app from environment variables. Raises ``ConfigError`` if the key or token is unusable."""
    settings = Settings.from_env(env)
    token = read_mcp_token(env)
    return create_app(NutritionService(settings), token)


def main() -> None:
    import uvicorn
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx's own request lines: off here, untouched in the library

    try:
        app = create_app_from_env()
    except ConfigError as exc:
        raise SystemExit(f"Cannot start: {exc}") from None

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
