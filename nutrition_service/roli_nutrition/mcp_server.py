"""Phase 1B/1C: a thin MCP wrapper around ``NutritionService``.

Needs the ``[mcp]`` extra. Nothing in the rest of the package imports this
module, so LangGraph can install and use the core without MCP being present.
Importing this module has no side effects: no credentials are read, no
connections are opened, no server starts. Everything happens in ``create_app()``.

What this file adds on top of the service:
- two MCP tools whose JSON is exactly ``service.get_nutrition(...)`` and
  ``service.search_foods(...)`` turned into a dict; each call runs in a worker
  thread so the server's event loop never waits on USDA
- a bearer-token check (``ROLI_MCP_TOKEN``) that answers 401 before any tool
  or USDA code runs
- ``GET /health``: the one public endpoint, ``{"status": "ok"}``, any Host
- Host and Origin allowlists (``ROLI_MCP_ALLOWED_HOSTS``,
  ``ROLI_MCP_ALLOWED_ORIGINS``) passed to the SDK's DNS-rebinding protection
- ``create_app()``: an application factory for ``uvicorn --factory``
- ``main()``: loads ``roli/.env`` and serves locally with uvicorn
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Annotated, Any, Mapping

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import ConfigError, Settings
from .service import DEFAULT_LIMIT, NutritionService

logger = logging.getLogger("roli_nutrition.mcp")

SERVER_NAME = "roli-nutrition"
MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
MIN_TOKEN_CHARS = 32

SEARCH_TOOL = "roli_search_usda_foods"
NUTRITION_TOOL = "roli_get_usda_nutrition"

# Hosts a request may be addressed to (the HTTP ``Host`` header). ``name:*`` means any port.
# Local development only; a tunnel or deployment hostname goes into ROLI_MCP_ALLOWED_HOSTS.
DEFAULT_ALLOWED_HOSTS = ["127.0.0.1:*", "localhost:*"]
# Browser origins allowed when an ``Origin`` header is present. Server-to-server clients send none.
DEFAULT_ALLOWED_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*"]

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
# Configuration read from the environment
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


def parse_allowlist(raw: str | None, *, name: str, default: list[str], kind: str) -> list[str]:
    """Comma-separated allowlist. Empty or unset means ``default``.

    Each entry is an exact value or ends in ``:*`` (any port). No other wildcard is
    accepted, so ``*`` and ``*.example.com`` are rejected: DNS-rebinding protection
    only works when the list names real hosts.
    """
    if raw is None or raw.strip() == "":
        return list(default)
    entries = [item.strip() for item in raw.split(",")]
    for entry in entries:
        if not entry:
            raise ConfigError(f"{name} has an empty entry. Separate values with commas and no trailing comma.")
        base = entry[:-2] if entry.endswith(":*") else entry
        if not base or "*" in base:
            raise ConfigError(
                f"{name}: '{entry}' is not allowed. Use an exact value or a trailing ':*' for any port; "
                "no other wildcards."
            )
        if any(ch.isspace() for ch in entry):
            raise ConfigError(f"{name}: '{entry}' contains whitespace.")
        if kind == "host" and "/" in entry:
            raise ConfigError(f"{name}: '{entry}' must be a hostname (optionally :port or :*), not a URL.")
        if kind == "origin" and not (entry.startswith("http://") or entry.startswith("https://")):
            raise ConfigError(f"{name}: '{entry}' must start with http:// or https://.")
    return entries


def read_security_settings(env: Mapping[str, str] | None = None) -> TransportSecuritySettings:
    """Host and Origin allowlists for the SDK's DNS-rebinding protection, which stays enabled."""
    source = os.environ if env is None else env
    hosts = parse_allowlist(source.get("ROLI_MCP_ALLOWED_HOSTS"), name="ROLI_MCP_ALLOWED_HOSTS",
                            default=DEFAULT_ALLOWED_HOSTS, kind="host")
    origins = parse_allowlist(source.get("ROLI_MCP_ALLOWED_ORIGINS"), name="ROLI_MCP_ALLOWED_ORIGINS",
                              default=DEFAULT_ALLOWED_ORIGINS, kind="origin")
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins)


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
# Front door: health check, then bearer token (plain ASGI, no SDK auth machinery)
# ---------------------------------------------------------------------------


class FrontDoor:
    """Runs before the SDK's routing for every HTTP request.

    1. ``GET /health`` answers ``{"status": "ok"}`` with no token and under any
       Host header, so a hosting platform's probe can reach it. It touches nothing.
    2. Everything else must carry ``Authorization: Bearer <token>`` or gets a 401.
       Host and Origin checks happen afterwards, inside the SDK, so an
       unauthenticated request never gets far enough to learn which hosts are allowed.
    Non-HTTP scopes (lifespan) pass straight through.
    """

    def __init__(self, app, token: str) -> None:
        self._app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if scope["path"] == HEALTH_PATH and scope["method"] == "GET":
            await _send_json(send, 200, {"status": "ok"})
            return
        reason = self._check(scope)
        if reason is not None:
            logger.warning(json.dumps({"event": "auth_rejected", "reason": reason, "path": scope.get("path"),
                                       **self._shape(scope)}))
            await _send_json(send, 401, {"error": "unauthorized", "message": "Missing or invalid bearer token."},
                             extra_headers=[(b"www-authenticate", b"Bearer")])
            return
        await self._app(scope, receive, send)

    @staticmethod
    def _shape(scope) -> dict:
        """Diagnostics that describe the Authorization header's shape without revealing any of it:
        how many headers, how many space-separated parts, the value's length, whether an unresolved
        template marker is present, and whether the first word is 'bearer'. Never the value itself."""
        values = [v for k, v in scope.get("headers", []) if k == b"authorization"]
        if not values:
            return {"auth_headers": 0}
        first = values[0]
        parts = first.split(b" ")
        return {
            "auth_headers": len(values),
            "parts": len(parts),
            "value_len": len(first),
            "scheme_is_bearer": parts[0].lower() == b"bearer",
            "has_template_braces": b"{{" in first or b"}}" in first,
            "trailing_space": first.endswith(b" "),
        }

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


async def _send_json(send, status: int, payload: dict, extra_headers: list | None = None) -> None:
    body = json.dumps(payload).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers + (extra_headers or [])})
    await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------------------
# Application factory and entry point
# ---------------------------------------------------------------------------


def create_app(
    *,
    service: NutritionService | None = None,
    token: str | None = None,
    security: TransportSecuritySettings | None = None,
    env: Mapping[str, str] | None = None,
):
    """Build the ASGI app. With no arguments everything comes from the environment,
    which is what ``uvicorn roli_nutrition.mcp_server:create_app --factory`` does.

    Reads and validates ``USDA_FDC_API_KEY``, ``ROLI_MCP_TOKEN`` and the two
    allowlists here, at construction, and raises ``ConfigError`` if any is unusable.
    Tests pass their own ``service``, ``token`` or ``security`` to skip the
    corresponding environment read.

    ``stateless_http=True``: every request stands alone, no session to keep.
    ``json_response=True``: plain JSON replies instead of server-sent events.
    The inner Starlette app is kept as ``.inner`` because tests run its lifespan by hand.
    """
    source = os.environ if env is None else env
    if service is None:
        service = NutritionService(Settings.from_env(source))
    if token is None:
        token = read_mcp_token(source)
    if security is None:
        security = read_security_settings(source)

    server = create_server(service)
    inner = server.streamable_http_app(
        streamable_http_path=MCP_PATH, stateless_http=True, json_response=True, transport_security=security,
    )
    app = FrontDoor(inner, token)
    app.inner = inner  # type: ignore[attr-defined]
    app.security = security  # type: ignore[attr-defined]
    logger.info(json.dumps({"event": "app_created", "allowed_hosts": security.allowed_hosts,
                            "allowed_origins": security.allowed_origins}))
    return app


def main() -> None:
    """Local run: load ``roli/.env``, then serve. Docker uses ``uvicorn --factory`` directly instead."""
    import uvicorn
    from dotenv import load_dotenv
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx's own request lines: off here, untouched in the library

    try:
        app = create_app()
    except ConfigError as exc:
        raise SystemExit(f"Cannot start: {exc}") from None

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
