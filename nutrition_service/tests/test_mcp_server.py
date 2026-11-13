"""Phase 1B: tests L (discovery), M (calls), N (auth) through the MCP interface.

The ASGI app runs in-process: an httpx2 ``ASGITransport`` stands in for the
network, the official MCP client talks Streamable HTTP over it, and USDA is the
same recording mock transport the Phase 1A tests use. No sockets, no USDA.

Skipped automatically where the ``[mcp]`` extra is not installed (the LangGraph
environment installs the core only).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager

import httpx
import pytest

pytest.importorskip("mcp")
import httpx2  # noqa: E402  (dependency of the MCP SDK)
from mcp import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402

from roli_nutrition import NutritionService  # noqa: E402
from roli_nutrition.config import ConfigError  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from roli_nutrition.mcp_server import (  # noqa: E402
    NUTRITION_DESCRIPTION,
    NUTRITION_TOOL,
    SEARCH_DESCRIPTION,
    SEARCH_TOOL,
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_ALLOWED_ORIGINS,
    create_app,
    parse_allowlist,
    read_mcp_token,
    read_security_settings,
)
from roli_nutrition.usda_client import UsdaClient  # noqa: E402

from conftest import FOOD_171999, SENTINEL_KEY, Recorder, error_response, food_router, make_settings  # noqa: E402

# A test-only token, never the real one from roli/.env.
TEST_TOKEN = "test-only-token-" + "0123456789abcdef" * 3  # 64 characters
BASE_URL = "http://127.0.0.1:8000"  # the SDK's DNS-rebinding guard wants host:port
JSONRPC_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


# -- wiring ---------------------------------------------------------------------


def make_app(responder):
    """App + recorder + a direct service on identical fixtures (to compare outputs)."""
    recorder = Recorder(responder)
    client = UsdaClient(SENTINEL_KEY, transport=recorder.transport, sleep=lambda s: None)
    service = NutritionService(make_settings(), client=client)
    return create_app(service=service, token=TEST_TOKEN, env={}), recorder, service


@asynccontextmanager
async def running(app):
    """Run the inner Starlette app's lifespan (the SDK's session manager needs it)."""
    async with app.inner.router.lifespan_context(app.inner):
        yield


def http_client(app, token: str | None = TEST_TOKEN, **kw) -> httpx2.AsyncClient:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    headers.update(kw.pop("headers", {}))
    return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE_URL, headers=headers, **kw)


@asynccontextmanager
async def mcp_session(app, token: str | None = TEST_TOKEN):
    async with running(app):
        async with http_client(app, token) as hc:
            async with streamable_http_client(f"{BASE_URL}/mcp", http_client=hc) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    yield session


def run(coro):
    return asyncio.run(coro)


def tool_result(result) -> dict:
    """Both views of a tool result: structured content and the parsed text block."""
    d = result.model_dump(exclude_none=True)
    return {
        "is_error": d["is_error"],
        "structured": d.get("structured_content"),
        "text": _parse_text(d["content"]),
    }


def _parse_text(content: list) -> dict | str | None:
    """The text block is JSON for tool results; the SDK's own type-rejection message is plain text."""
    if not content or content[0]["type"] != "text":
        return None
    try:
        return json.loads(content[0]["text"])
    except json.JSONDecodeError:
        return content[0]["text"]


# -- L: discovery ------------------------------------------------------------------


def test_l_exactly_two_tools_with_spec_names_and_descriptions():
    app, _, _ = make_app(food_router())

    async def go():
        async with mcp_session(app) as session:
            return (await session.list_tools()).tools

    tools = {t.name: t for t in run(go())}
    assert set(tools) == {SEARCH_TOOL, NUTRITION_TOOL}
    assert tools[SEARCH_TOOL].description == SEARCH_DESCRIPTION
    assert tools[NUTRITION_TOOL].description == NUTRITION_DESCRIPTION
    # Spot-check that the spec's key sentences survived into the constants.
    assert "Never invent an FDC ID." in SEARCH_DESCRIPTION
    assert "never replace it with zero or an estimate" in NUTRITION_DESCRIPTION


def test_l_input_schemas():
    app, _, _ = make_app(food_router())

    async def go():
        async with mcp_session(app) as session:
            return {t.name: t.model_dump(exclude_none=True) for t in (await session.list_tools()).tools}

    tools = run(go())
    search = tools[SEARCH_TOOL]["input_schema"]
    assert set(search["properties"]) == {"query", "limit"}
    assert search["properties"]["query"]["type"] == "string"
    assert search["properties"]["limit"] == {"default": 5, "title": "Limit", "type": "integer"}
    assert search["required"] == ["query"]

    nutrition = tools[NUTRITION_TOOL]["input_schema"]
    assert set(nutrition["properties"]) == {"fdc_id"}
    assert nutrition["properties"]["fdc_id"]["type"] == "integer"
    assert nutrition["required"] == ["fdc_id"]

    for name in (SEARCH_TOOL, NUTRITION_TOOL):
        assert tools[name]["output_schema"]["type"] == "object"
        annotations = tools[name]["annotations"]
        assert annotations.get("readOnlyHint", annotations.get("read_only_hint")) is True


# -- M: calls -------------------------------------------------------------------------


def test_m_nutrition_tool_equals_service_output():
    app, recorder, service = make_app(food_router())
    expected = service.get_nutrition(FOOD_171999).model_dump()  # direct Python call, same fixture
    assert expected["saturated_fat_g"] == 3.214

    async def go():
        async with mcp_session(app) as session:
            return await session.call_tool(NUTRITION_TOOL, {"fdc_id": FOOD_171999})

    r = tool_result(run(go()))
    assert r["is_error"] is False
    assert r["structured"] == expected
    assert r["text"] == expected


def test_m_search_tool_equals_service_output():
    app, _, service = make_app(food_router("search_king_salmon"))
    expected = service.search_foods("king salmon cooked dry heat", 10).model_dump()
    assert len(expected["candidates"]) == 10

    async def go():
        async with mcp_session(app) as session:
            return await session.call_tool(SEARCH_TOOL, {"query": "king salmon cooked dry heat", "limit": 10})

    r = tool_result(run(go()))
    assert r["is_error"] is False
    assert r["structured"] == expected
    assert r["text"] == expected


def test_m_search_default_limit_through_mcp():
    app, recorder, _ = make_app(food_router())

    async def go():
        async with mcp_session(app) as session:
            return await session.call_tool(SEARCH_TOOL, {"query": "salmon"})

    r = tool_result(run(go()))
    assert len(r["structured"]["candidates"]) == 5
    assert json.loads(recorder.requests[0].content)["pageSize"] == 5


def test_m_service_error_is_a_normal_tool_result():
    app, _, _ = make_app([error_response("error_404")])

    async def go():
        async with mcp_session(app) as session:
            return await session.call_tool(NUTRITION_TOOL, {"fdc_id": 99999999})

    r = tool_result(run(go()))
    assert r["is_error"] is False  # spec 9: errors are results, not protocol failures
    assert r["structured"] == {
        "status": "error", "fdc_id": 99999999, "error_code": "not_found",
        "message": "USDA has no food with this FDC ID.",
    }


def test_m_value_rules_come_back_in_our_error_shape():
    app, recorder, _ = make_app(food_router())

    async def go():
        async with mcp_session(app) as session:
            a = await session.call_tool(NUTRITION_TOOL, {"fdc_id": 0})
            b = await session.call_tool(SEARCH_TOOL, {"query": "salmon", "limit": 11})
            return a, b

    a, b = (tool_result(x) for x in run(go()))
    assert a["structured"]["error_code"] == "invalid_input" and a["structured"]["fdc_id"] == 0
    assert b["structured"]["error_code"] == "invalid_input" and b["structured"]["query"] == "salmon"
    assert recorder.requests == []


@pytest.mark.parametrize("bad", [True, "171999", 2.0, None])
def test_m_json_type_errors_are_rejected_by_the_mcp_layer(bad):
    """Strict integers: true must not become food 1, "171999" must not become an int."""
    app, recorder, _ = make_app(food_router())

    async def go():
        async with mcp_session(app) as session:
            return await session.call_tool(NUTRITION_TOOL, {"fdc_id": bad})

    r = tool_result(run(go()))
    assert r["is_error"] is True
    assert isinstance(r["text"], str) and "fdc_id" in r["text"]  # the SDK names the rejected argument
    assert r["structured"] is None
    assert recorder.requests == []


def test_m_calls_run_in_a_worker_thread_and_do_not_block_the_loop():
    loop_thread = threading.get_ident()
    seen_threads: list[int] = []
    body = httpx.Response(200, json=__import__("conftest").load("food_171999"))

    def slow(request):
        seen_threads.append(threading.get_ident())
        time.sleep(0.25)  # a slow USDA; blocking sleep on purpose
        return body

    app, _, _ = make_app(slow)

    async def go():
        async with mcp_session(app) as session:
            started = time.perf_counter()
            # Two different IDs so the cache cannot merge them; both hit the slow handler.
            a, b = await asyncio.gather(
                session.call_tool(NUTRITION_TOOL, {"fdc_id": FOOD_171999}),
                session.call_tool(NUTRITION_TOOL, {"fdc_id": 172001}),
            )
            return time.perf_counter() - started

    elapsed = run(go())
    assert len(seen_threads) == 2
    assert all(t != loop_thread for t in seen_threads), "USDA call ran on the event-loop thread"
    assert elapsed < 0.45, f"two 0.25 s calls took {elapsed:.2f} s: they did not overlap"


# -- N: authentication -------------------------------------------------------------------


def rpc(method: str, params: dict | None = None, id_: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}


@pytest.mark.parametrize("header", [
    None,                                   # missing
    "Bearer wrong-token-" + "x" * 40,       # wrong
    f"Token {TEST_TOKEN}",                  # not Bearer
    "Bearer",                               # no token
    f"Bearer {TEST_TOKEN} extra",           # extra part
    f"Bearer{TEST_TOKEN}",                  # no space
    TEST_TOKEN,                             # raw token, no scheme
    "",                                     # empty header
])
def test_n_unauthorised_requests_get_401_before_any_tool_runs(header):
    app, recorder, _ = make_app(food_router())

    async def go():
        async with running(app):
            headers = {} if header is None else {"Authorization": header}
            async with http_client(app, token=None, headers=headers) as c:
                call = rpc("tools/call", {"name": NUTRITION_TOOL, "arguments": {"fdc_id": FOOD_171999}})
                return await c.post("/mcp", json=call, headers=JSONRPC_HEADERS)

    response = run(go())
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": "unauthorized", "message": "Missing or invalid bearer token."}
    assert TEST_TOKEN not in response.text
    assert recorder.requests == []  # USDA was never contacted


def test_n_right_token_works_and_scheme_is_case_insensitive():
    app, recorder, _ = make_app(food_router())

    async def go():
        async with running(app):
            out = []
            for scheme in ("Bearer", "bearer", "BEARER"):
                async with http_client(app, token=None, headers={"Authorization": f"{scheme} {TEST_TOKEN}"}) as c:
                    r = await c.post("/mcp", json=rpc("tools/list"), headers=JSONRPC_HEADERS)
                    out.append((r.status_code, [t["name"] for t in r.json()["result"]["tools"]]))
            return out

    for status, names in run(go()):
        assert status == 200
        assert set(names) == {SEARCH_TOOL, NUTRITION_TOOL}


def test_n_other_methods_and_paths_are_also_protected():
    app, recorder, _ = make_app(food_router())

    async def go():
        async with running(app):
            async with http_client(app, token=None) as c:
                return [
                    (await c.get("/mcp", headers=JSONRPC_HEADERS)).status_code,
                    (await c.delete("/mcp")).status_code,
                    (await c.post("/anything-else", json={})).status_code,
                    (await c.get("/")).status_code,
                ]

    assert run(go()) == [401, 401, 401, 401]
    assert recorder.requests == []


def test_n_wrong_token_through_official_client_fails_and_never_reaches_usda():
    app, recorder, _ = make_app(food_router())

    async def go():
        async with mcp_session(app, token="not-the-right-token-" + "y" * 40) as session:
            await session.call_tool(NUTRITION_TOOL, {"fdc_id": FOOD_171999})

    with pytest.raises(Exception):
        run(go())
    assert recorder.requests == []


def test_n_server_refuses_to_start_without_a_usable_token():
    base = {"USDA_FDC_API_KEY": SENTINEL_KEY}
    with pytest.raises(ConfigError, match="ROLI_MCP_TOKEN"):
        read_mcp_token(base)
    with pytest.raises(ConfigError, match="ROLI_MCP_TOKEN"):
        read_mcp_token({**base, "ROLI_MCP_TOKEN": "   "})
    with pytest.raises(ConfigError, match="32"):
        read_mcp_token({**base, "ROLI_MCP_TOKEN": "short-token-1234567890"})  # 22 chars
    with pytest.raises(ConfigError, match="ROLI_MCP_TOKEN"):
        create_app(env=base)
    with pytest.raises(ConfigError, match="USDA_FDC_API_KEY"):
        create_app(env={"ROLI_MCP_TOKEN": TEST_TOKEN})
    assert read_mcp_token({**base, "ROLI_MCP_TOKEN": TEST_TOKEN}) == TEST_TOKEN
    assert create_app(env={**base, "ROLI_MCP_TOKEN": TEST_TOKEN}) is not None


def test_n_token_never_appears_in_logs(caplog):
    app, _, _ = make_app(food_router())

    async def go():
        async with running(app):
            async with http_client(app, token=None, headers={"Authorization": f"Bearer {TEST_TOKEN}x"}) as c:
                await c.post("/mcp", json=rpc("tools/list"), headers=JSONRPC_HEADERS)
            async with http_client(app) as c:
                await c.post("/mcp", json=rpc("tools/list"), headers=JSONRPC_HEADERS)

    run(go())
    assert TEST_TOKEN not in caplog.text
    assert "auth_rejected" in caplog.text


# -- Phase 1C: health endpoint ----------------------------------------------------------------


def make_app_with_security(responder, hosts: list[str], origins: list[str] | None = None):
    recorder = Recorder(responder)
    client = UsdaClient(SENTINEL_KEY, transport=recorder.transport, sleep=lambda s: None)
    service = NutritionService(make_settings(), client=client)
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts,
        allowed_origins=origins if origins is not None else DEFAULT_ALLOWED_ORIGINS,
    )
    return create_app(service=service, token=TEST_TOKEN, security=security, env={}), recorder


async def raw_post(app, path: str, json_body: dict, *, host: str, token: str | None = TEST_TOKEN, origin: str | None = None):
    headers = dict(JSONRPC_HEADERS)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["Origin"] = origin
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=f"http://{host}") as c:
        return await c.post(path, json=json_body, headers=headers)


async def raw_get(app, path: str, *, host: str, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=f"http://{host}") as c:
        return await c.get(path, headers=headers)


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:8000", "10.0.0.7:8080", "internal.platform.local", "evil.example"])
def test_health_is_public_under_any_host(host):
    app, recorder = make_app_with_security(food_router(), ["localhost:*"])

    async def go():
        async with running(app):
            return await raw_get(app, "/health", host=host)

    r = run(go())
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["content-type"] == "application/json"
    assert recorder.requests == []


def test_health_with_a_token_also_works_and_reveals_nothing(caplog):
    app, recorder = make_app_with_security(food_router(), ["localhost:*"])

    async def go():
        async with running(app):
            return await raw_get(app, "/health", host="localhost:8000", token=TEST_TOKEN)

    r = run(go())
    assert r.status_code == 200 and r.text == '{"status": "ok"}'
    assert recorder.requests == []
    assert TEST_TOKEN not in caplog.text and SENTINEL_KEY not in caplog.text


def test_health_exception_is_limited_to_get_health():
    app, recorder = make_app_with_security(food_router(), ["localhost:*"])

    async def go():
        async with running(app):
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost:8000") as c:
                return [
                    (await c.post("/health", json={})).status_code,     # wrong method
                    (await c.get("/healthz")).status_code,              # similar path
                    (await c.get("/health/")).status_code,              # trailing slash
                    (await c.get("/health/x")).status_code,
                    (await c.get("/mcp")).status_code,
                    (await c.get("/")).status_code,
                ]

    assert run(go()) == [401, 401, 401, 401, 401, 401]
    assert recorder.requests == []


# -- Phase 1C: Host allowlist (DNS-rebinding protection) ---------------------------------------------


TOOLS_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}


@pytest.mark.parametrize("host", ["mcp.example.com", "localhost:8000", "localhost:65000", "tunnel.trycloudflare.com:443"])
def test_hosts_listed_are_accepted(host):
    app, _ = make_app_with_security(food_router(), ["mcp.example.com", "localhost:*", "tunnel.trycloudflare.com:*"])

    async def go():
        async with running(app):
            return await raw_post(app, "/mcp", TOOLS_LIST, host=host)

    r = run(go())
    assert r.status_code == 200
    assert {t["name"] for t in r.json()["result"]["tools"]} == {SEARCH_TOOL, NUTRITION_TOOL}


@pytest.mark.parametrize("host", [
    "evil.example", "mcp.example.com:8443", "127.0.0.1:8000", "localhost", "notlocalhost:8000", "mcp.example.com.evil.net",
])
def test_hosts_unlisted_get_421_even_with_a_valid_token(host):
    app, recorder = make_app_with_security(food_router(), ["mcp.example.com", "localhost:*"])

    async def go():
        async with running(app):
            return await raw_post(app, "/mcp", {**TOOLS_LIST, "method": "tools/call",
                                                 "params": {"name": NUTRITION_TOOL, "arguments": {"fdc_id": FOOD_171999}}}, host=host)

    r = run(go())
    assert r.status_code == 421
    assert recorder.requests == []


def test_hosts_unauthenticated_request_to_bad_host_gets_401_not_421():
    """Auth runs first, so an attacker without the token learns nothing about allowed hosts."""
    app, _ = make_app_with_security(food_router(), ["mcp.example.com"])

    async def go():
        async with running(app):
            return await raw_post(app, "/mcp", TOOLS_LIST, host="evil.example", token=None)

    assert run(go()).status_code == 401


def test_health_works_where_mcp_rejects_the_host():
    app, recorder = make_app_with_security(food_router(), ["mcp.example.com"])

    async def go():
        async with running(app):
            health = await raw_get(app, "/health", host="10.1.2.3:9000")
            mcp = await raw_post(app, "/mcp", TOOLS_LIST, host="10.1.2.3:9000")
            return health.status_code, mcp.status_code

    assert run(go()) == (200, 421)
    assert recorder.requests == []


# -- Phase 1C: Origin handling ----------------------------------------------------------------------


def test_origin_absent_is_accepted_for_server_to_server_clients():
    app, _ = make_app_with_security(food_router(), ["mcp.example.com"], origins=["https://agent.example.com"])

    async def go():
        async with running(app):
            return await raw_post(app, "/mcp", TOOLS_LIST, host="mcp.example.com")  # no Origin header

    assert run(go()).status_code == 200


@pytest.mark.parametrize("origin, expected", [
    ("https://agent.example.com", 200),
    ("http://localhost:5173", 200),       # port wildcard
    ("http://localhost", 403),            # no port: not matched by "http://localhost:*"
    ("https://evil.example", 403),
    ("http://agent.example.com", 403),    # scheme differs
])
def test_origin_present_is_checked_against_the_allowlist(origin, expected):
    app, recorder = make_app_with_security(food_router(), ["mcp.example.com"],
                                           origins=["https://agent.example.com", "http://localhost:*"])

    async def go():
        async with running(app):
            return await raw_post(app, "/mcp", TOOLS_LIST, host="mcp.example.com", origin=origin)

    assert run(go()).status_code == expected
    assert recorder.requests == []


# -- Phase 1C: allowlist configuration ---------------------------------------------------------------


def test_allowlist_defaults_when_unset_or_blank():
    s = read_security_settings({})
    assert s.enable_dns_rebinding_protection is True
    assert s.allowed_hosts == DEFAULT_ALLOWED_HOSTS == ["127.0.0.1:*", "localhost:*"]
    assert s.allowed_origins == DEFAULT_ALLOWED_ORIGINS
    assert read_security_settings({"ROLI_MCP_ALLOWED_HOSTS": "   "}).allowed_hosts == DEFAULT_ALLOWED_HOSTS


def test_allowlist_parsing_trims_and_keeps_order():
    s = read_security_settings({
        "ROLI_MCP_ALLOWED_HOSTS": " localhost:* , abc.trycloudflare.com,mcp.example.com:8443 ",
        "ROLI_MCP_ALLOWED_ORIGINS": "https://smith.langchain.com, http://localhost:*",
    })
    assert s.allowed_hosts == ["localhost:*", "abc.trycloudflare.com", "mcp.example.com:8443"]
    assert s.allowed_origins == ["https://smith.langchain.com", "http://localhost:*"]


@pytest.mark.parametrize("raw", ["*", "*:*", "*.example.com", "localhost:*,*", "a.com,", ",a.com", "a.com,,b.com", "a com", "https://a.com", ":*"])
def test_allowlist_rejects_unrestricted_wildcards_and_junk_hosts(raw):
    with pytest.raises(ConfigError, match="ROLI_MCP_ALLOWED_HOSTS"):
        parse_allowlist(raw, name="ROLI_MCP_ALLOWED_HOSTS", default=DEFAULT_ALLOWED_HOSTS, kind="host")


@pytest.mark.parametrize("raw", ["*", "https://*", "agent.example.com", "ftp://a.com", "https://a.com,"])
def test_allowlist_rejects_bad_origins(raw):
    with pytest.raises(ConfigError, match="ROLI_MCP_ALLOWED_ORIGINS"):
        parse_allowlist(raw, name="ROLI_MCP_ALLOWED_ORIGINS", default=DEFAULT_ALLOWED_ORIGINS, kind="origin")


def test_allowlist_from_env_reaches_the_sdk_settings():
    env = {"USDA_FDC_API_KEY": SENTINEL_KEY, "ROLI_MCP_TOKEN": TEST_TOKEN,
           "ROLI_MCP_ALLOWED_HOSTS": "mcp.example.com,localhost:*"}
    app = create_app(env=env)
    assert app.security.allowed_hosts == ["mcp.example.com", "localhost:*"]
    assert app.security.enable_dns_rebinding_protection is True

    async def go():
        async with running(app):
            ok = await raw_post(app, "/mcp", TOOLS_LIST, host="mcp.example.com")
            bad = await raw_post(app, "/mcp", TOOLS_LIST, host="127.0.0.1:8000")
            return ok.status_code, bad.status_code

    assert run(go()) == (200, 421)


def test_bad_allowlist_stops_app_construction():
    env = {"USDA_FDC_API_KEY": SENTINEL_KEY, "ROLI_MCP_TOKEN": TEST_TOKEN, "ROLI_MCP_ALLOWED_HOSTS": "*"}
    with pytest.raises(ConfigError, match="ROLI_MCP_ALLOWED_HOSTS"):
        create_app(env=env)


# -- Phase 1C: application factory ---------------------------------------------------------------------


def test_factory_module_imports_without_any_secrets():
    """Fresh interpreter, empty environment: import succeeds, no server starts, no credentials needed."""
    probe = (
        "import json, os, threading\n"
        "assert not any(k.startswith(('USDA_', 'ROLI_')) for k in os.environ)\n"
        "before = threading.active_count()\n"
        "import roli_nutrition.mcp_server as m\n"
        "print(json.dumps({'has_factory': callable(m.create_app), 'new_threads': threading.active_count() - before}))\n"
    )
    completed = subprocess.run([sys.executable, "-I", "-c", probe], env={"PATH": os.environ.get("PATH", "")},
                               capture_output=True, text=True, check=True, timeout=60)
    out = json.loads(completed.stdout.strip().splitlines()[-1])
    assert out == {"has_factory": True, "new_threads": 0}


def test_factory_with_no_arguments_reads_the_environment(monkeypatch):
    """This is exactly what `uvicorn roli_nutrition.mcp_server:create_app --factory` calls."""
    for name in ("USDA_FDC_API_KEY", "ROLI_MCP_TOKEN", "ROLI_MCP_ALLOWED_HOSTS", "ROLI_MCP_ALLOWED_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigError, match="USDA_FDC_API_KEY"):
        create_app()
    monkeypatch.setenv("USDA_FDC_API_KEY", SENTINEL_KEY)
    with pytest.raises(ConfigError, match="ROLI_MCP_TOKEN"):
        create_app()
    monkeypatch.setenv("ROLI_MCP_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("ROLI_MCP_ALLOWED_HOSTS", "mcp.example.com")
    app = create_app()
    assert app.security.allowed_hosts == ["mcp.example.com"]
    assert hasattr(app.inner.router, "lifespan_context")  # lifespan wired for uvicorn


@pytest.mark.parametrize("header, expect", [
    ("Bearer ", {"reason": "malformed", "parts": 2, "scheme_is_bearer": True, "trailing_space": True}),
    ("Bearer {{ROLI_MCP_TOKEN}}", {"reason": "wrong", "has_template_braces": True}),
    ("Bearer {{ ROLI_MCP_TOKEN }}", {"reason": "malformed", "parts": 4, "has_template_braces": True}),
    (f"Bearer Bearer {TEST_TOKEN}", {"reason": "malformed", "parts": 3}),
    (f"Token {TEST_TOKEN}", {"reason": "malformed", "scheme_is_bearer": False}),
])
def test_n_rejection_log_describes_header_shape_without_the_value(caplog, header, expect):
    app, _, _ = make_app(food_router())

    async def go():
        async with running(app):
            async with http_client(app, token=None, headers={"Authorization": header}) as c:
                return await c.post("/mcp", json=rpc("tools/list"), headers=JSONRPC_HEADERS)

    assert run(go()).status_code == 401
    line = next(json.loads(r.message) for r in caplog.records if r.name == "roli_nutrition.mcp" and "auth_rejected" in r.message)
    for key, value in expect.items():
        assert line[key] == value, (key, line)
    assert line["auth_headers"] == 1 and line["value_len"] == len(header)
    assert TEST_TOKEN not in caplog.text
