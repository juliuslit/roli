"""Direct Python vs MCP: latency and response size for the same food, warmed cache.

    nutrition_service/.venv/bin/python scripts/benchmark_mcp.py [--calls 50]

Fully local: USDA is replaced by the saved real reply for 171999 served through
an httpx mock transport, so the numbers measure our code and the MCP layer, not
the network. Three paths are timed:

1. direct      : service.get_nutrition(171999) in the same process
2. mcp-inproc  : the official MCP client over an in-process ASGI transport (no sockets)
3. mcp-tcp     : the official MCP client over HTTP to uvicorn on 127.0.0.1 (what a real client sees)

Sizes: the application-level JSON payload (what the tool returns) versus the
full HTTP response body for a tools/call (JSON-RPC envelope + text block +
structuredContent), for both tools. Uses a test-only token, never the real one.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import socket
import statistics
import sys
import threading
import time
from pathlib import Path

import httpx
import httpx2
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from roli_nutrition import NutritionService, Settings  # noqa: E402
from roli_nutrition.mcp_server import NUTRITION_TOOL, SEARCH_TOOL, create_app  # noqa: E402
from roli_nutrition.usda_client import UsdaClient  # noqa: E402

FIXTURES = SERVICE_DIR / "tests" / "fixtures" / "usda"
TOKEN = "benchmark-only-token-" + "b" * 43
FDC_ID = 171999
QUERY = "king salmon cooked dry heat"


def local_service() -> NutritionService:
    food = json.loads((FIXTURES / "food_171999.json").read_text())
    search = json.loads((FIXTURES / "search_king_salmon.json").read_text())

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/foods/search"):
            return httpx.Response(200, json=search)
        return httpx.Response(200, json=food)

    client = UsdaClient("benchmark-key", transport=httpx.MockTransport(respond))
    return NutritionService(Settings(api_key="benchmark-key"), client=client)


def stats(samples_ms: list[float]) -> dict:
    return {
        "calls": len(samples_ms),
        "mean_ms": statistics.fmean(samples_ms),
        "median_ms": statistics.median(samples_ms),
        "p95_ms": sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1],
    }


def bench_direct(service: NutritionService, calls: int) -> dict:
    service.get_nutrition(FDC_ID)  # warm the cache
    samples = []
    for _ in range(calls):
        t = time.perf_counter()
        service.get_nutrition(FDC_ID)
        samples.append((time.perf_counter() - t) * 1000)
    return stats(samples)


async def bench_session(session: ClientSession, calls: int) -> dict:
    await session.call_tool(NUTRITION_TOOL, {"fdc_id": FDC_ID})  # warm
    samples = []
    for _ in range(calls):
        t = time.perf_counter()
        await session.call_tool(NUTRITION_TOOL, {"fdc_id": FDC_ID})
        samples.append((time.perf_counter() - t) * 1000)
    return stats(samples)


async def bench_mcp_inprocess(app, calls: int) -> dict:
    async with app.inner.router.lifespan_context(app.inner):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8000",
            headers={"Authorization": f"Bearer {TOKEN}"},
        ) as hc:
            async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=hc) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await bench_session(session, calls)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerThread:
    def __init__(self, app, port: int) -> None:
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started:
            if time.time() > deadline:
                raise RuntimeError("uvicorn did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=5)


async def bench_mcp_tcp(port: int, calls: int) -> dict:
    url = f"http://127.0.0.1:{port}/mcp"
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"}) as hc:
        async with streamable_http_client(url, http_client=hc) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                return await bench_session(session, calls)


async def measure_sizes(port: int, service: NutritionService) -> list[dict]:
    """Application payload vs full HTTP body for one tools/call per tool (stateless, raw JSON-RPC)."""
    url = f"http://127.0.0.1:{port}/mcp"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    cases = [
        (NUTRITION_TOOL, {"fdc_id": FDC_ID}, service.get_nutrition(FDC_ID)),
        (SEARCH_TOOL, {"query": QUERY, "limit": 10}, service.search_foods(QUERY, 10)),
    ]
    rows = []
    async with httpx2.AsyncClient() as c:
        for name, args, direct in cases:
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}
            r = await c.post(url, json=body, headers=headers)
            r.raise_for_status()
            envelope = r.json()
            structured = envelope["result"]["structuredContent"]
            text_block = envelope["result"]["content"][0]["text"]
            payload_compact = json.dumps(direct.model_dump(), separators=(",", ":"))
            assert structured == direct.model_dump(), f"{name}: MCP structured content differs from direct call"
            assert json.loads(text_block) == direct.model_dump()
            rows.append({
                "tool": name,
                "payload_compact_bytes": len(payload_compact.encode()),
                "payload_pretty_text_block_bytes": len(text_block.encode()),
                "http_body_bytes": len(r.content),
                "protocol_overhead_bytes": len(r.content) - len(payload_compact.encode()),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=50)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)  # keep timing output clean; nothing here needs the logs

    service = local_service()

    direct = bench_direct(service, args.calls)
    # The SDK's session manager can be started only once per app, so each MCP phase gets its own app
    # around the same service (same cache, same fixtures).
    inproc = asyncio.run(bench_mcp_inprocess(create_app(service=service, token=TOKEN, env={}), args.calls))

    port = free_port()
    with ServerThread(create_app(service=service, token=TOKEN, env={}), port):
        tcp = asyncio.run(bench_mcp_tcp(port, args.calls))
        sizes = asyncio.run(measure_sizes(port, service))

    print(f"## Latency, get_nutrition({FDC_ID}), warmed cache, {args.calls} timed calls each, local only\n")
    print("| Path | Mean | Median | p95 | Extra vs direct (median) |")
    print("|---|---:|---:|---:|---:|")
    for label, s in (("direct Python", direct), ("MCP in-process (no sockets)", inproc), ("MCP over HTTP to uvicorn on 127.0.0.1", tcp)):
        extra = s["median_ms"] - direct["median_ms"]
        print(f"| {label} | {s['mean_ms']:.3f} ms | {s['median_ms']:.3f} ms | {s['p95_ms']:.3f} ms | {extra:+.3f} ms |")

    print("\n## Response size, one tools/call each\n")
    print("| Tool | App payload, compact JSON | Text block (pretty JSON) | Full HTTP body | Protocol overhead |")
    print("|---|---:|---:|---:|---:|")
    for row in sizes:
        print(f"| `{row['tool']}` | {row['payload_compact_bytes']:,} B | {row['payload_pretty_text_block_bytes']:,} B | "
              f"{row['http_body_bytes']:,} B | {row['protocol_overhead_bytes']:,} B |")
    nutrition_payload = next(r for r in sizes if r["tool"] == NUTRITION_TOOL)["payload_compact_bytes"]
    print(f"\nNutrition payload under 2 KB: {'yes' if nutrition_payload < 2048 else 'NO'} ({nutrition_payload} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
