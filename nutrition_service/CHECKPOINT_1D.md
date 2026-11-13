# Checkpoint 1D: LangSmith Agent Builder integration test

Date: 2026-11-01. Scope: Phase 1D of the nutrition service, the end-to-end path LangSmith Agent Builder → MCP tools → `roli_nutrition` → USDA FoodData Central → agent. Status: **Phase 1D complete; stopped. Nothing deployed, no tunnel left open, no credential exposed, nutrition logic, LangGraph implementation and agent prompt unchanged.**

Evidence: the MCP server's own logs (every USDA search and lookup the agent made, with timings), the LangSmith traces of all nine runs made today in the Agent Builder project (read through the LangSmith API with the key in `roli/.env`; run IDs below), and Julius's observations in the Agent Builder UI. Each finding is marked **confirmed** (seen in a log or trace), **assumption** (my reading of the evidence) or **not verifiable** from the available data.

## 1. Summary

| Area | Result |
|---|---|
| Local preflight | all green: 202 tests, health 200, 401 cases, discovery, 171999 exact |
| External connectivity | worked through Cloudflare quick tunnels; **four tunnels were needed** because each died within 18 to 60 minutes |
| MCP connection in LangSmith | worked once the header held the literal token; the `{{secret}}` placeholder produced a malformed header |
| Tests A, B, C (one run each, plus one A repeat) | **4 of 4 correct**: right FDC ID, exact USDA values, new tools used, no cross-species mixing |
| Test C repeat while the tunnel was dead | **failed dangerously**: tools errored, the agent used web search and reported a retailer's figures as "USDA FoodData Central lists… FDC 171999" |
| Test D (menu photo) | real dishes, sensible USDA records, correct per-100 g values retrieved; **estimates have no stated weights or arithmetic**, one ingredient (bottarga) ignored, 11 of 28 USDA tool calls unnecessary |
| Record integrity | 100%: every value the agent quoted that came from a tool matched the USDA record for that FDC ID |
| Record relevance | good for salmon (4/4, incl. King → Chinook, not King mackerel); mixed for cheeses and lettuce in Test D |
| Baseline (old USDA tools, same morning) | King salmon run reported FDC 171999 with **Pink salmon's values** (0.971 g / 55 mg); Atlantic salmon run took 245 s, 1.45 M tokens, $0.81 |
| Cost and latency, new tools | A/B/C: 7 to 13 s, 63 K tokens, about $0.06; D: 49 s, 304 K tokens, $0.18 |
| Repeated runs (3× each for A to C) | **not performed**: one run each plus one repeat of A; the tunnel outages consumed the session |
| Cleanup | tunnel, server, watchdog and `caffeinate` stopped; no secret in any log or report |

## 2. Connectivity and connection status

### 2.1 Local preflight (Step 1), all confirmed

| Check | Result |
|---|---|
| cloudflared | 2026.10.7 installed |
| `USDA_FDC_API_KEY`, `ROLI_MCP_TOKEN` | present (40 and 64 characters) |
| Offline suite | 202 passed, 4 skipped |
| Server via `uvicorn ... create_app --factory --env-file` | up on 127.0.0.1:8000 |
| `/health`; `/mcp` no auth / invalid token / malformed header | 200; 401 / 401 / 401 |
| Discovery through the official MCP client | both tools |
| 171999 | complete, 3.214 g, 85.0 mg (742 ms cold); 172001: 0.971 g, 55.0 mg |

### 2.2 Tunnels (Step 2), confirmed from cloudflared logs

| # | Hostname | Registered (UTC) | First failure | What happened |
|---|---|---|---|---|
| 1 | jesus-airline-initially-bracket | 18:37 | 19:03 | QUIC idle timeout, then "Unauthorized: Tunnel not found" forever |
| 2 | edwards-may-focus-asset | 19:26 | 19:59 (dead 20:27) | control stream dropped, same refusal |
| 3 | packet-electron-fallen-cos | 20:29 | 20:47 | same; DNS never propagated |
| 4 | charles-cent-trigger-robot | 23:22 | stopped by me at cleanup | alive for the final tests |

A quick tunnel cannot re-register after any disconnect, so one dropped connection kills its random hostname. Each new hostname forced an edit of the LangSmith connection. For each tunnel I verified over HTTPS: health 200, 401 without or with a wrong token, 403 with a foreign Origin, discovery, exact values, and 421 for unlisted or previous hostnames. The server stayed bound to 127.0.0.1:8000 with only that socket exposed; the allowlist was set in the process environment and `roli/.env` was never edited.

### 2.3 LangSmith connection (Step 3)

- First attempt failed with "DNS resolution failed": tunnel 1 was already dead. Confirmed; not a LangSmith problem.
- Second attempt, tunnel 2: discovery requests arrived (28 requests from Google Cloud addresses) and all got 401 with reason `malformed`. Confirmed. The header value configured as `Bearer {{ROLI_MCP_TOKEN}}` reached the server as `Bearer` with nothing after it, so the secret placeholder is not expanded for custom MCP static headers (**assumption**, consistent with the shape fields the server logged: one header, two parts, empty token, scheme Bearer). Julius replaced it with the literal token and discovery succeeded: 18 × 200, 9 × 202, 1 × 406. The 406 is LangSmith probing `GET /mcp` for a server-sent-events stream; the stateless JSON server does not offer one, and it is harmless (confirmed).
- The connection carries only the MCP token. The USDA key never left the server (confirmed: it appears nowhere in LangSmith inputs, outputs or in any log).

## 3. Test results

LangSmith run IDs are in the Agent Builder project `fleet-22579532d282478997da6c592a7459d1-production`.

### 3.1 Tests A to C, new tools (confirmed from traces and server log)

| Run (UTC) | Test | Tool calls | FDC chosen | Values returned by tool | Agent's answer | Latency | Tokens in / out | Cost (LangSmith) |
|---|---|---|---|---|---|---|---|---|
| 19:43 `01a198a3-6912…` | A Chinook | search ×2 (parallel), lookup ×1 | 171999 | 3.214 g, 85.0 mg | 3.214 g, 85 mg | 8.72 s | 62,998 / 274 | $0.056 |
| 19:44 `01a198a3-fd5c…` | B Pink | search ×2 (parallel), lookup ×1 | 172001 | 0.971 g, 55.0 mg | **0.97 g**, 55 mg | 7.49 s | 62,910 / 220 | $0.058 |
| 19:45 `01a198a4-d102…` | C King salmon | search ×1, lookup ×1 | 171999 | 3.214 g, 85.0 mg | 3.214 g, 85 mg | 13.02 s | 62,305 / 253 | $0.018 |
| 23:25 `01a1996f-0fbe…` | A repeat | search ×2 (parallel), lookup ×1 | 171999 | 3.214 g, 85.0 mg | 3.214 g, 85 mg | 6.98 s | 62,966 / 244 | $0.055 |

- Record integrity 4/4; record relevance 4/4. Test C: the agent searched `salmon chinook cooked dry heat` directly, so USDA's King-mackerel-first ordering for "king salmon" never came into play (confirmed from the trace; the tool description's wording advice was followed).
- Test B's 0.97 g is the agent rounding 0.971 in prose; the tool returned 0.971 (confirmed in trace and server log).
- Redundant calls: in A and B the agent fired two searches in parallel with different word orders ("chinook salmon cooked" and "salmon chinook cooked dry heat"); both returned 171999 first. One search is enough. Test C used one. Each extra search is about 1.4 s of tool time but ran in parallel, so it cost tokens, not wall time.
- Per-call tool latency through the tunnel: search 1.3 to 1.5 s, lookup 0.4 to 0.7 s (of which USDA itself 0.8 to 1.0 s for search, 0.3 to 0.7 s for a cold lookup; the tunnel and LangSmith's proxying add roughly 0.5 s). Model turns 1.1 to 2.2 s each; three turns per test. Test C's 13 s includes 5 s before the first model call (**not verifiable** why; LangSmith-side queueing is my assumption).
- Costs are LangSmith's estimates for the model alias `langchain:fast`; the underlying model is **not verifiable** from the trace, and Test C's $0.018 for the same token count as A and B suggests the estimate is not consistent.

### 3.2 Test C repeat during the tunnel outage: a failure worth more than the passes

Run 23:18 `01a19968-4d64…`, prompt "Find the USDA nutritional information for King salmon cooked using dry heat", started four minutes before tunnel 4 existed.

- All three `roli_search_usda_foods` calls failed in LangSmith with `SSRFBlockedError: DNS resolution failed` (confirmed; the dead hostname).
- The agent then made 12 more tool calls: six Tavily web searches, two page reads (one a fish retailer's product page), greps and file reads of the fetched HTML.
- Final answer, verbatim in part: "USDA FoodData Central lists chinook (king) salmon, cooked, dry heat at FDC 171999. Per 3 oz cooked serving: 393 calories … 5.5 g saturated fat, 144 mg cholesterol …". Those are the retailer's numbers, not USDA's. USDA's 171999 per 85 g would be 2.73 g and 72 mg. **Wrong values with a false USDA attribution** (confirmed).
- 59.2 s, 634,582 tokens, $0.29.

Conclusion: when the nutrition tools are unavailable, the current agent does not say so; it substitutes web content and labels it USDA. This is the single most important finding of the phase. It is a prompt and tool-policy issue, not a service issue, and it is listed first in the Phase 2 priorities. Julius did not report this run; it was found in the traces.

### 3.3 Test D, menu photo (run 23:26 `01a1996f-d83e…`)

Prompt "Hey, what should I order?" with `menu_03_own_IMG_5185.jpg` (Flour + Water). The menu, per the answer key, has 18 dishes incl. Heirloom Tomatoes (pluot, shiso, basil, sourdough), Bluefin Crudo (bottarga, muscat grape, chive), Little Gem Lettuces (tahini vinaigrette, pecorino sardo, toasted sesame), Pole Beans (burrata, smoked tomato, miso bagna cauda), King Salmon (squash, corn, basil, shishito).

**Agent's answer** (391 characters): 1. Heirloom Tomatoes, ~0–0.5 g sat fat, 0 mg cholesterol. 2. Bluefin Crudo, ~1–2 g, ~40 mg. 3. Little Gem Lettuces, ~3–4 g, ~10 mg. "Estimates based on USDA data and assumed portions."

**Totals:** 49.41 s, 304,104 tokens (300,048 in / 4,056 out), $0.18, 11 model turns, 31 tool calls (1 image read, 2 to-do updates, 17 USDA searches, 11 USDA lookups). Confirmed.

**Does it read the menu accurately and invent nothing?** The three recommended dishes and their named ingredients exist on the menu (confirmed against the answer key). The agent looked up ingredients for five dishes (the three above plus King Salmon and Pole Beans' burrata, plus Parmesan, presumably for the bread). No invented dish, no invented nutrient value: every number the tools returned is a real USDA value (confirmed).

**Record relevance, ingredient by ingredient** (confirmed from tool outputs):

| Menu ingredient | Searches | Record used | Judgement |
|---|---|---|---|
| heirloom tomatoes | `tomatoes raw`, then `tomatoes red ripe raw year round average` | 170457 Tomatoes, red, ripe, raw, year round average | right; second search redundant, the ID was already in hand |
| sourdough | `bread sourdough` | 172675 Bread, french or vienna (includes sourdough) | right |
| bluefin (crudo) | `bluefin tuna raw`, `fish tuna fresh bluefin raw` | 173706 Fish, tuna, fresh, bluefin, raw | right; second search a duplicate |
| bottarga (cured roe) | none | none | **missed**; roe is cholesterol-dense, so the crudo estimate is low (assumption on magnitude; the miss is confirmed) |
| little gem lettuce | `lettuce iceberg raw` → 2346388 Foundation (partial, no fat/cholesterol rows), `lettuce romaine raw` → 746769 Foundation (partial), `lettuce green leaf raw` → 169249 SR Legacy | 169249 Lettuce, green leaf, raw | acceptable proxy; three searches and three lookups for one leaf, because the first two picks were Foundation records with no fat rows. The agent correctly refused to treat `null` as zero and kept searching, which is the intended behaviour, but the romaine SR Legacy record (169247) was already in the first result list |
| tahini vinaigrette | `tahini sesame butter` | 170189 Seeds, sesame butter, tahini, from roasted and toasted kernels | right |
| pecorino sardo | `pecorino cheese` (returned cream cheese spread, bread cheese, blue, brick, brie), then `pecorino romano cheese` | 171249 Cheese, romano | nearest USDA has; first search useless |
| toasted sesame | `sesame seeds toasted` | 170151 Seeds, sesame seeds, whole, roasted and toasted | right |
| King Salmon entrée | `salmon atlantic raw`, `fish salmon atlantic cooked dry heat` → 175168 looked up; later `salmon chinook cooked dry heat` → 171999 looked up | 171999 | right in the end; the Atlantic farmed record was the wrong species and its lookup was wasted |
| burrata | `burrata cheese` (junk results) | none | USDA SR Legacy has no burrata; no lookup, dish dropped silently |
| parmesan | `parmesan cheese` | none looked up | unused |

**Redundant or wasted USDA calls:** 8 of 17 searches (second tomato, second bluefin, `pecorino cheese`, `parmesan`, two Atlantic salmon, `lettuce iceberg raw`, `lettuce romaine raw`) and 3 of 11 lookups (175168 Atlantic salmon, 2346388 iceberg, 746769 romaine). The `salmon chinook cooked dry heat` search and the 171999 lookup were served from the service cache in 0.1 ms because Tests A and C had run earlier (confirmed). Confirmed counts; the "wasted" judgement is mine.

**USDA values retrieved (verifiable, per 100 g):**

| FDC ID | USDA description | Saturated fat g | Cholesterol mg |
|---|---|---:|---:|
| 170457 | Tomatoes, red, ripe, raw, year round average | 0.028 | 0 |
| 172675 | Bread, french or vienna (includes sourdough) | 0.529 | 0 |
| 173706 | Fish, tuna, fresh, bluefin, raw | 1.257 | 38 |
| 170189 | Seeds, sesame butter, tahini, from roasted and toasted kernels | 7.529 | 0 |
| 171249 | Cheese, romano | 17.115 | 104 |
| 170151 | Seeds, sesame seeds, whole, roasted and toasted | 6.722 | 0 |
| 169249 | Lettuce, green leaf, raw | 0.02 | 0 |
| 171999 | Fish, salmon, chinook, cooked, dry heat | 3.214 | 85 |
| 175168 | Fish, salmon, Atlantic, farmed, cooked, dry heat | 2.397 | 63 |
| 2346388, 746769 | Lettuce, iceberg / cos or romaine (Foundation) | no row | no row |

**Dish estimates versus USDA values.** The answer's ranges are the model's mental arithmetic. No portion weights, no per-ingredient amounts and no calculation appear anywhere in the trace: the intermediate model steps contain only tool calls, the two to-do updates hold three task lines, and the final text names no grams of anything (confirmed by searching every model output and tool input in the trace). The ranges are plausible against the USDA values (100 g raw bluefin alone gives 1.26 g and 38 mg; a 30 g tahini dressing plus 10 g romano gives roughly 4 g and 10 mg), but that plausibility is my reconstruction, not something the agent showed. The answer does say "estimates based on USDA data and assumed portions", which is the required distinction in words, without the numbers that would make it checkable. Verdict for the spec's criteria: reads the menu accurately, yes; suitable dishes, yes; uses the tools appropriately, mostly (over-searches, one missed ingredient); up to three dishes ranked by saturated fat then cholesterol, yes; distinguishes reference values from estimates, in words only; invents nothing, confirmed.

### 3.4 Repetition

Tests A to C were to run three times each. Done: A twice (19:43 and 23:25, identical results), B once, C once with tools working and once with tools dead (section 3.2). The remaining repeats were not performed because the tunnel outages consumed the session. Not a failure of the service; an incomplete test plan.

## 4. Latency, tokens and cost: what drives them

**Tokens (confirmed).** Every model turn in every run starts from about 20,480 input tokens before the user's prompt: the agent's system prompt, tool schemas and memory. Test D's eleven turns carried 20,487 → 31,712 tokens each, summing to exactly the 300,048 input tokens LangSmith reports. The menu image added about 1,900 tokens once. USDA tool results are small (300 B to 1.5 KB each, roughly 100 to 500 tokens). So tokens ≈ turns × 27 K, and the lever is the number of turns, not the payload sizes. Tests A to C used three turns each, hence 63 K.

**Latency (confirmed from child-run timings).** Test D: model turns 31.4 s of 49.4 s (64%); tool batches about 11 s, run in parallel within a turn; one USDA lookup (746769, Foundation romaine) took 3.2 s on its own, 2.8 s of it inside USDA. Tests A/B: three model turns about 4.5 s, tools about 2.2 s, the rest LangSmith overhead.

**Cost.** $0.18 for Test D and $0.055 to $0.058 for A, B and the A repeat, per LangSmith's estimate; Test C's $0.018 for the same tokens is inconsistent, so treat the cost column as approximate (**not verifiable**).

**Comparison with the old integration (confirmed; traces from 14:39 to 14:55 the same day, before the MCP connection):**

| Run | Old tools | Result | Time | Tokens | Cost |
|---|---|---|---|---|---|
| 14:42 Atlantic salmon | 51 tool calls: USDA plugin searches returning empty content, Tavily web searches, reading `api.nal.usda.gov` URLs with `DEMO_KEY`, a sub-task | 175168, 2.397 g / 63 mg, correct | 244.9 s | 1,454,491 | $0.81 |
| 14:54 King salmon | 21 tool calls, same pattern | **FDC 171999 with 0.971 g / 55 mg, which are Pink salmon's (172001) values** | 74.0 s | 865,711 | $0.46 |
| 14:39 menu photo, no tools | answered from general knowledge: same three dishes, no numbers | 8.6 s | 46,340 | $0.10 |

The King salmon run is the record-integrity failure that motivated this service, reproduced in a trace from this morning. With the new tools the same question took 13 s, 62 K tokens and returned the right values. Atlantic salmon: 245 s and $0.81 before, versus about 8 s and $0.06 for an equivalent single-ingredient question after.

## 5. Security and cleanup checks (Step 6)

| Item | Result |
|---|---|
| Cloudflare tunnel | stopped; no cloudflared process; hostnames dead (the last one may linger in DNS caches for minutes with nothing behind it) |
| MCP server | stopped; port 8000 closed; no uvicorn process |
| Watchdog loop, `caffeinate` | stopped |
| Allowlist | the tunnel hostnames were only ever in the process environment; `roli/.env` has no `ROLI_MCP_ALLOWED_HOSTS` line, so there is nothing to remove |
| Credentials in logs | USDA key and MCP token: 0 occurrences across all server and tunnel logs of this phase, this report and the test reports |
| Credentials in LangSmith | the MCP token is in the connection's header, as designed; the USDA key appears nowhere in any trace input or output |
| Repo | `.env` unchanged except nothing; no file outside `nutrition_service/` touched |

**LangSmith connection, recommendation.** `Roli USDA Nutrition` now points at a dead hostname. If left enabled, every nutrition question will reproduce section 3.2: tool errors followed by web-search answers labelled USDA. **Disable the connection until a stable hostname exists**, or, if the agent is not going to be used before then, leave it and accept that risk knowingly. Do not re-enable it with a quick-tunnel URL; use a fixed hostname (ngrok free static domain, named Cloudflare Tunnel on a domain you control, or a small container host). The old third-party USDA tools are still enabled, as you asked; they were not used in any run where the new tools worked.

## 6. Service changes made during this phase

One, diagnostic only: the 401 log line now records the shape of a rejected `Authorization` header (header count, word count, value length, Bearer scheme or not, template braces present, trailing space) and never its value. A test asserts the test token never appears. This is what identified the empty-token header. The factory import test was also made independent of whether a dev server happens to be listening. Suite: 207 passed, 4 skipped. No change to nutrition logic, tool behaviour, authentication rules or allowlists.

## 7. Remaining issues

1. **Tool failure → fabricated attribution** (section 3.2). Highest severity.
2. **No stable public hostname.** Four quick tunnels in one evening; each forced a LangSmith edit.
3. **Estimates without arithmetic.** Dish numbers are ranges with no stated portions; not auditable.
4. **Missed ingredients.** Bottarga ignored; burrata dropped silently because USDA has no record.
5. **Over-searching.** 11 of 28 USDA tool calls in Test D did not contribute; parallel duplicate searches in A and B.
6. **Foundation plant records return `partial`**, which costs the agent extra turns. Correct behaviour, expensive.
7. **Search quality for restaurant words.** `pecorino`, `burrata` return unrelated cheeses; little gem has no USDA entry.
8. **Secret placeholder** not expanded in LangSmith custom MCP headers; the token sits in the header field as a literal.
9. **Test plan incomplete:** repeats of B and C not run.

## 8. Recommended Phase 2 priorities, in order

1. **Make tool failure visible, never substituted.** Agent rule: if `roli_*` tools error or are unavailable, say so and stop; never answer a nutrition question from web search and never attribute non-tool numbers to USDA. In LangGraph this is structural: the node imports `roli_nutrition` directly, no tunnel, and an `ErrorResult` is rendered as "USDA lookup failed", not routed to another source. This fixes 7.1 and makes 7.2 irrelevant for the LangGraph path.
2. **Deterministic dish arithmetic**, the `calculate_dish_nutrition` tool already listed in spec 15: inputs are ingredient FDC IDs with assumed grams; output is per-ingredient contributions, a total, the assumed grams, and a list of ingredients with no USDA record. The agent then reports numbers it did not compute in its head, the portions are visible, and missed ingredients (bottarga, burrata) become an explicit "not included" line. Fixes 7.3 and 7.4.
3. **Stable hosting before any further Agent Builder test**: ngrok static domain for the next test session, a container host (Fly.io or Cloud Run, README section 6) for anything longer. Fixes 7.2 for the Agent Builder path.
4. **Fewer turns.** Expose multi-ID lookup (USDA `POST /foods`, up to 20 IDs; spec 15) and tell the agent to search once per ingredient and look up all chosen IDs in one call. Test D would drop from 11 turns to about 5, roughly halving tokens and time. Fixes 7.5.
5. **Plant foods and `partial`.** Add one sentence to the search tool description: for plant foods prefer the SR Legacy record when a Foundation record has no fat rows; `null` stays `null`. Service unchanged. Fixes 7.6.
6. **Relevance test set** (spec 15): menu ingredient wording → correct FDC ID, built from the 25 menus' answer keys, starting with the Test D ingredients. Measures 7.7 before trying synonym hints (pecorino → romano, little gem → romaine) in the tool description.
7. **Repeat A to C three times** once a stable hostname exists, to close 7.9; five minutes of work.

**Stopped here. Phase 2 starts only after your review.**
