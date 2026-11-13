# roli_nutrition: USDA saturated fat and cholesterol, checked by code

One small Python library that returns saturated fat (g) and cholesterol (mg) per 100 g for exactly one USDA FoodData Central food, plus a thin MCP server around it. The values are fetched and validated by plain code, so a number can never be attached to the wrong food record.

Two consumers, one copy of the logic:

- **LangGraph** (the code-based Roli implementation) imports the Python functions directly. No MCP involved.
- **LangSmith Agent Builder** calls the same functions through the MCP server over HTTPS.

Spec: `SPEC.md`. Build history and measurements: `CHECKPOINT_1A.md`, `CHECKPOINT_1B.md`, `CHECKPOINT_1C.md`.

## Layout

```text
nutrition_service/
  roli_nutrition/          the library
    config.py              Settings.from_env(): USDA key, cache settings
    usda_client.py         the only network code: two requests, retries, status mapping
    nutrients.py           pure functions: USDA reply -> validated result (rules V1-V15)
    schemas.py             result shapes (Pydantic): NutritionResult, SearchResult, ErrorResult
    service.py             NutritionService: input checks, cache, one JSON log line per call
    store.py               saved USDA answers on disk, release detection state, staging and snapshots (spec v2.3)
    mcp_server.py          MCP wrapper: two tools, bearer token, /health, Host/Origin allowlists
  scripts/                 capture_fixtures.py, demo.py, benchmark_mcp.py
  tests/                   pytest; real saved USDA replies under tests/fixtures/usda/
  pyproject.toml           package "roli-nutrition", extras [mcp] and [dev]
  requirements.txt         exact pins for the Docker image (core + [mcp])
  Dockerfile, .dockerignore
  .env.example             variable names with placeholders; real values live in roli/.env
```

## 1. Local setup

Python 3.11 or later. The Mac uses `/opt/anaconda3/bin/python3.13`.

```text
cd roli/nutrition_service
/opt/anaconda3/bin/python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev,mcp]"        # core + tests + MCP server
```

Secrets go in `roli/.env` (one level up, git-ignored). Copy the names from `.env.example`:

| Variable | Needed by | Meaning |
|---|---|---|
| `USDA_FDC_API_KEY` | everything | free key from https://fdc.nal.usda.gov/api-key-signup.html; 3,600 requests per rolling hour on this key (USDA's `x-ratelimit-limit` header, read 2026-11-05) |
| `ROLI_MCP_TOKEN` | MCP server | bearer token clients must send; at least 32 characters. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ROLI_MCP_ALLOWED_HOSTS` | MCP server | comma-separated `Host` values the server will answer on; default `127.0.0.1:*,localhost:*` |
| `ROLI_MCP_ALLOWED_ORIGINS` | MCP server | comma-separated browser origins allowed when an `Origin` header is present; default `http://127.0.0.1:*,http://localhost:*` |
| `ROLI_CACHE_TTL_SECONDS` | library | how long a USDA answer is kept in memory; default 86400 |
| `ROLI_CACHE_MAX_ENTRIES` | library | cache size; default 1000 |
| `ROLI_USDA_STORE_DIR` | library | directory of saved USDA answers (spec v2.3); unset = in-memory cache only |
| `ROLI_USDA_RESERVE_REQUESTS` | library | callers pause when the hourly allowance is down to this; default 200 |
| `ROLI_USDA_HALT_SECONDS` | library | after a 429, no request is sent for this long; default 3600 |
| `ROLI_USDA_STALE_MONTHS` | library | Foundation/Survey answers older than this are refreshed into staging by `scripts/refresh_usda.py --stage --stale-only`; default 7 |
| `HOST`, `PORT` | MCP server | where uvicorn listens; defaults `127.0.0.1`, `8000` |

The library itself never opens `.env`. Scripts, tests and `main()` load it with python-dotenv; in Docker the values arrive as plain environment variables.

## 2. Tests

```text
.venv/bin/python -m pytest -v                   # offline: real saved USDA replies, no network
ROLI_LIVE_TESTS=1 .venv/bin/python -m pytest tests/test_live.py -v   # 4 real USDA calls
.venv/bin/python scripts/demo.py                # prints real results for the two salmon records
.venv/bin/python scripts/benchmark_mcp.py       # direct Python vs MCP, local only
```

Run pytest from this folder. From the repo root it would also collect the menu reader's scripts.

Fixtures are real USDA replies captured once by `scripts/capture_fixtures.py` (15 files, SHA-256 in `tests/fixtures/usda/manifest.json`). Failure cases are edited copies made in the tests; no fixture is typed by hand. Re-capturing costs about 15 USDA calls and is only needed if USDA changes its format.

## 3. Using the library directly from LangGraph

Install the core only (no MCP) into the LangGraph environment:

```text
pip install -e /path/to/roli/nutrition_service
```

Then, with `USDA_FDC_API_KEY` in that process's environment:

```python
from roli_nutrition import get_nutrition, search_foods

r = get_nutrition(171999)                              # sync node
r = await asyncio.to_thread(get_nutrition, 171999)     # async node
state_update = r.model_dump()                          # plain dict, safe to put in graph state

s = search_foods("salmon chinook cooked dry heat", limit=5)
```

What comes back is always one of three shapes, never an exception:

```json
{"status": "complete", "fdc_id": 171999, "description": "Fish, salmon, chinook, cooked, dry heat",
 "data_type": "SR Legacy", "basis": "per_100g", "saturated_fat_g": 3.214, "cholesterol_mg": 85.0,
 "missing_nutrients": [], "nutrient_ids": {"saturated_fat_g": 1258, "cholesterol_mg": 1253},
 "source": "USDA FoodData Central"}
```

`status` is `complete`, `partial` (a value is `null` and listed in `missing_nutrients`; never treat it as zero) or `error` (`error_code` is one of `invalid_input`, `not_found`, `unsupported_data_type`, `id_mismatch`, `validation_failed`, `malformed_response`, `rate_limited`, `usda_auth_failed`, `usda_unavailable`). Search results carry `candidates` with `fdc_id`, `description`, `data_type` and nothing else.

The module-level functions share one `NutritionService` (one HTTP client, one in-memory cache). For several services or custom settings, build `NutritionService(Settings.from_env())` yourself. Calls are thread-safe.

## 4. Running the MCP server locally

```text
.venv/bin/python -m roli_nutrition.mcp_server              # loads roli/.env; http://127.0.0.1:8000/mcp
PORT=8765 .venv/bin/python -m roli_nutrition.mcp_server
```

Or exactly as the container does, with the environment already set (no `.env` load):

```text
.venv/bin/uvicorn roli_nutrition.mcp_server:create_app --factory --host 127.0.0.1 --port 8000
```

Endpoints:

| Path | Auth | Purpose |
|---|---|---|
| `GET /health` | none, any `Host` | `{"status": "ok"}`; touches nothing; for hosting-platform probes |
| `POST /mcp` | `Authorization: Bearer <ROLI_MCP_TOKEN>` | MCP Streamable HTTP, stateless, JSON responses |
| anything else | | 401 |

Order of checks on `/mcp`: bearer token (401) → `Host` allowlist (421) → `Origin` allowlist if an `Origin` header is present (403) → MCP. Server-to-server clients such as LangSmith send no `Origin` and are accepted on Host and token alone.

Quick check with curl (token read from `.env`, never pasted):

```text
TOK=$(grep '^ROLI_MCP_TOKEN=' ../.env | cut -d= -f2-)
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOK" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

MCP Inspector, CLI mode (needs Node):

```text
npx -y @modelcontextprotocol/inspector@latest --cli http://127.0.0.1:8000/mcp --transport http \
  --header "Authorization: Bearer $TOK" --method tools/list
npx -y @modelcontextprotocol/inspector@latest --cli http://127.0.0.1:8000/mcp --transport http \
  --header "Authorization: Bearer $TOK" --method tools/call \
  --tool-name roli_get_usda_nutrition --tool-arg fdc_id=171999
```

The two tools are `roli_search_usda_foods(query, limit=5)` and `roli_get_usda_nutrition(fdc_id)`. Their JSON is identical to the direct Python call. Type errors (`fdc_id: "171999"` or `true`) are rejected by the MCP layer; value errors (`fdc_id: 0`, `limit: 11`) come back as a normal result with `error_code: invalid_input`.

## 5. Temporary public HTTPS link for the first Agent Builder test

LangSmith needs a public HTTPS URL. For a short test, tunnel the local server. Nothing in this section has been run yet; do it only when ready to test, and close the tunnel afterwards.

**Cloudflare Tunnel (quick tunnel, no account):**

```text
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8000
```

It prints a hostname like `random-words.trycloudflare.com`. Add it to the allowlist and restart the server, because the SDK's DNS-rebinding protection rejects any `Host` that is not listed (HTTP 421):

```text
ROLI_MCP_ALLOWED_HOSTS="127.0.0.1:*,localhost:*,random-words.trycloudflare.com" \
  .venv/bin/python -m roli_nutrition.mcp_server
```

**ngrok:** `ngrok http 8000` prints an `https://....ngrok-free.app` URL; add that hostname the same way. ngrok's free tier shows an interstitial page to browsers but passes API calls through.

Then `curl -s https://<hostname>/health` must return `{"status": "ok"}`, and a `tools/list` with the bearer token must return the two tools. Keep the token out of shell history and logs.

## 6. Hosting options

Any host that runs a container and injects environment variables works. Set `USDA_FDC_API_KEY`, `ROLI_MCP_TOKEN`, `ROLI_MCP_ALLOWED_HOSTS` (the public hostname, plus `localhost:*` for local probes) and `PORT` if the platform dictates one.

| Option | Notes |
|---|---|
| Fly.io, Render, Railway, Google Cloud Run | container from the Dockerfile; secrets in the platform's secret store; health check on `GET /health` |
| Cloudflare | Workers cannot run this Python/uvicorn image; a Cloudflare Tunnel in front of a small VM or the Mac is the Cloudflare-shaped option |
| A small VM | `docker run` with `--restart unless-stopped` behind Caddy or nginx for TLS |

**Cold-start caveat.** Platforms that scale to zero (Cloud Run, Fly machines that auto-stop, Render free tier) take one to several seconds to start a container, and the in-memory cache starts empty, so the first `get_nutrition` after idle costs the start time plus a 200–650 ms USDA call. Agent Builder tool calls then look slow or time out on that first request. Either keep one instance always on, or accept the first-call delay.

The cache is per process. Two instances, or the MCP server and LangGraph, each keep their own.

## 7. Docker

Build from this folder (secrets are never part of the image; `.dockerignore` excludes `.env`, tests, fixtures and the venv):

```text
docker build -t roli-nutrition .
docker run --rm -p 8000:8000 \
  -e USDA_FDC_API_KEY="$(grep '^USDA_FDC_API_KEY=' ../.env | cut -d= -f2-)" \
  -e ROLI_MCP_TOKEN="$(grep '^ROLI_MCP_TOKEN=' ../.env | cut -d= -f2-)" \
  -e ROLI_MCP_ALLOWED_HOSTS="localhost:*,127.0.0.1:*" \
  roli-nutrition
curl -s http://127.0.0.1:8000/health
```

Verify the image carries no credentials (prints only pass/fail, never the values):

```text
KEY=$(grep '^USDA_FDC_API_KEY=' ../.env | cut -d= -f2-); TOK=$(grep '^ROLI_MCP_TOKEN=' ../.env | cut -d= -f2-)
docker history --no-trunc roli-nutrition | grep -q -F -e "$KEY" -e "$TOK" && echo "FAIL: history" || echo "pass: history"
docker inspect roli-nutrition | grep -q -F -e "$KEY" -e "$TOK" && echo "FAIL: config" || echo "pass: config"
docker run --rm --entrypoint sh roli-nutrition -c "grep -rqF -e '$KEY' -e '$TOK' / 2>/dev/null && echo FAIL: filesystem || echo pass: filesystem"
unset KEY TOK
```

The image runs as the unprivileged user `roli`, listens on `$PORT` (default 8000) and starts with `uvicorn roli_nutrition.mcp_server:create_app --factory`, which reads and validates the environment before serving and exits non-zero if the key, token or allowlist is unusable.

Docker was not installed on the development Mac when this was written, so the build has not been run here; see `CHECKPOINT_1C.md` for what was verified instead.

## 8. Connecting the remote MCP server in LangSmith Agent Builder

1. Have the server reachable over HTTPS (tunnel or hosting) with its hostname in `ROLI_MCP_ALLOWED_HOSTS`.
2. In LangSmith, add a remote MCP server (Streamable HTTP):
   - URL: `https://<host>/mcp`
   - Header: `Authorization: Bearer <ROLI_MCP_TOKEN>`
3. LangSmith should list `roli_search_usda_foods` and `roli_get_usda_nutrition`. Their descriptions tell the agent how to use them (USDA wording, pick the matching description, never invent an FDC ID, `null` is not zero).
4. Rotate the token by changing `ROLI_MCP_TOKEN` on the server and in LangSmith; old tokens stop working at the next request.

## 9. Security notes

- The USDA key and the MCP token live only in `roli/.env` locally and in the host's secret store in deployment. Nothing logs or echoes them; the tests assert this with a sentinel key and a test token.
- The USDA host is a constant in code. The server sends USDA only food names and FDC IDs.
- Error messages are fixed text owned by this library; USDA's raw text, URLs and stack traces never reach a client.
- Unauthenticated requests are answered before routing, so they never reach a tool, the SDK, or USDA, and they cannot learn which hosts are allowed.
- Rate limit: USDA allows 1,000 requests/hour per key and blocks the key for an hour on 429. The library never retries a 429; the cache keeps repeat lookups free.

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 `unauthorized` | header missing, not `Bearer`, wrong token | send exactly `Authorization: Bearer <ROLI_MCP_TOKEN>` |
| 421 `Invalid Host header` | hostname not in `ROLI_MCP_ALLOWED_HOSTS` (default allows only `127.0.0.1:*`, `localhost:*`) | add the exact hostname (or `name:*`) and restart |
| 403 `Invalid Origin header` | a browser-based client sent an `Origin` not in `ROLI_MCP_ALLOWED_ORIGINS` | add the origin (`https://app.example.com` or `http://localhost:*`) |
| `Cannot start: ROLI_MCP_TOKEN ...` | token missing or under 32 characters | set it in `.env` or the environment |
| `Cannot start: ROLI_MCP_ALLOWED_HOSTS: '*' is not allowed` | unrestricted wildcard | list real hostnames; only a trailing `:*` port wildcard is accepted |
| `error_code: rate_limited` | USDA 429, key blocked for an hour | wait; check nothing else is using the key |
| `status: partial` with `cholesterol_mg: null` | USDA has no cholesterol row (common for Foundation plant foods) | report "no value", never zero |

## 11. Recipe calculator (Phase 2A)

`roli_nutrition.recipe` turns a recipe (ingredients in grams with USDA FDC IDs, a serving count) into saturated fat and cholesterol per ingredient, per recipe and per serving, with exact Decimal arithmetic and every intermediate number in the output. Spec: `SPEC_2A_recipe_calculator.md`.

```python
from roli_nutrition import NutritionService, Settings
from roli_nutrition.recipe import RecipeCalculator, compare_scenarios

calc = RecipeCalculator(NutritionService(Settings.from_env()))
result = calc.calculate({
    "recipe_name": "Salmon for two", "servings": 2,
    "ingredients": [
        {"name": "Chinook, cooked", "fdc_id": 171999, "grams": "300", "preparation_state": "cooked",
         "assumption": "hypothetical: 150 g cooked per person"},
        {"name": "Olive oil", "fdc_id": 171413, "grams": "10", "preparation_state": "as_used"},
    ],
})
result.status                              # "complete" | "incomplete" | "invalid_recipe"
result.display["saturated_fat_g"]          # "5.51 g per serving (11.02 g for the whole recipe, 2 servings)"
result.model_dump(mode="json")             # every contribution, reference value, exclusion and assumption
```

Rules that matter when writing a recipe:

- `grams` as strings ("85") keep exact decimals; `null` means unknown, `"0"` means an explicit zero.
- `preparation_state`: `raw` or `cooked` must match the USDA record (read from its description); `as_used` is for oils, cheeses, condiments, seeds and bread, and is refused for meat, fish, poultry and egg; `unknown` leaves the ingredient unresolved.
- An ingredient without `fdc_id`, without grams, with a failed USDA lookup, or with a preparation mismatch is **unresolved**: its contribution is `null`, it is excluded from subtotals, and the result is `incomplete` with the reason listed. The display then says "at least X … from N of M ingredients; missing: …", never a dish total.
- Completeness is tracked per nutrient and means complete for the supplied list, not verified for the restaurant's dish.
- `compare_scenarios([a, b, c])` reports min, median and max of the complete per-serving results and flags fewer than two complete scenarios as insufficient for a range.

`scripts/demo_recipe.py` prints the worked examples; `scripts/capture_recipe_fixtures.py` captured the extra USDA records the tests use. From LangGraph: `run_roli(recipe={...})` takes the calculator path with no LLM call.

## 12. Household-measure weights (Phase 2B, read-only)

`service.get_portions(fdc_id)` returns the record's `foodPortions[]` as gram weights ("1 tablespoon" = 13.5 g for olive oil 171413; "1 medium whole" = 123 g for tomatoes 170457), validated the same way as nutrition lookups (same record identity rules, same error shape, its own cache entry). It reads *weights only*: nutrient values still come solely from `get_nutrition`, and the recipe calculator does not import this module. The LangGraph recipe pipeline uses it to turn "2 tablespoons olive oil" into grams with the FDC ID and portion label recorded as the reference.
