# Running the Roli prototype

## Local use on Julius's Mac (current milestone, 2026-11-04)

Decision (Julius, 2026-11-04): one user, no deployment, no tunnel, no token. The app binds to 127.0.0.1 only; keys stay in `.env`.

    ./roli_local.sh start      # starts uvicorn on http://127.0.0.1:8008/ in the background, log in roli_agent/runs/web.log
    ./roli_local.sh status     # is it running, and where
    ./roli_local.sh log        # last 50 log lines
    ./roli_local.sh stop       # stops it
    ./roli_local.sh restart    # after a code change

Then open http://127.0.0.1:8008/ in a browser, upload a menu photo, watch the progress page (it refreshes every 5 seconds and shows each dish
as it finishes with the running spend), read the recommendation, open "Internal diagnostics" for every recipe, USDA match, assumption, portion
model, interval, pairwise verdict, the dish selection table and the spending report. Past runs: http://127.0.0.1:8008/runs. Raw JSON: `/run/<id>/json`.

Spending safeguards (`roli_agent/mvp/budget.py`): $0.50 of model calls per menu (menu reading included), 30 Tavily credits per menu, $5.00 and 300
credits per day across runs (ledger `roli_agent/runs/spend_ledger.jsonl`). Override with `ROLI_BUDGET_MENU_USD`, `ROLI_BUDGET_MENU_CREDITS`,
`ROLI_BUDGET_DAILY_USD`, `ROLI_BUDGET_DAILY_CREDITS` in the environment (or `MvpConfig`). A run that hits a limit stops the dish in flight, skips
the rest, ranks what it has and says so on the page. Nothing buys credit or changes billing.

Without `ROLI_WEB_TOKEN` the app is in local mode (no sign-in; never bind it to anything but 127.0.0.1). Setting `ROLI_WEB_TOKEN` restores the
shared-token lock for the day testers are invited. The rest of this file is the earlier recommendation for that day; nothing in it is done.

# Sharing the Roli prototype (invited testers, later)

Recommendation (2026-11-03): **run the app on Julius's Mac and expose it through a Cloudflare Tunnel protected by Cloudflare Access.** Nothing is
deployed by this document; it describes the simplest private, access-controlled setup and why.

## Why this and not a hosted server

| Option | Cost | Access control | Effort | Fit |
|---|---|---|---|---|
| **Mac + Cloudflare Tunnel + Access** (recommended) | $0 (free tier) | Access policy: only listed e-mail addresses, one-time code by e-mail; plus Roli's own shared token | 30 min once; `cloudflared` runs while the Mac is awake | the caches, the `.env` and the test set already live on the Mac; no secrets leave it; invited testers only |
| Small VPS (Fly.io, Railway, a $5 droplet) | $5-10/month | HTTP basic auth or the token | 1-2 hours; copy caches; keys on a third-party box | fine later, when the Mac must not be the server |
| Tailscale Funnel | $0 | Tailscale identity | 20 min | good for 2-3 testers who install Tailscale; a step more than a link |

The tunnel keeps the OpenRouter, Tavily and USDA keys on the Mac, needs no open port, and gives every tester a plain link plus an e-mail code.
The app's own shared token (`ROLI_WEB_TOKEN`) stays as a second lock: a leaked link without the token shows nothing.

## Steps (not done yet; each needs Julius's go-ahead where it touches accounts)

1. Add `ROLI_WEB_TOKEN=<a long random string>` to `.env` (never commit `.env`).
2. Start the app: `.venv/bin/uvicorn roli_agent.mvp.web:app --host 127.0.0.1 --port 8008`. Check `http://127.0.0.1:8008/?token=<token>` locally.
3. Install `cloudflared` (`brew install cloudflared`), log in to the Cloudflare account, create a named tunnel for a hostname under a domain Julius controls, route it to `http://127.0.0.1:8008`.
4. In Cloudflare Zero Trust, add an Access application for that hostname with a policy "allow e-mails in this list" (the testers), one-time PIN login.
5. Send each tester the link **with** the token (`https://roli.<domain>/?token=<token>`); the token is then kept in a cookie for 30 days.
6. Keep the Mac awake while testing (or run on a schedule); runs take 1-5 minutes per menu, so testers see the progress page.

## Operating notes

- Every run is saved under `roli_agent/runs/<run_id>/` (photo, `run.json`); feedback goes to `roli_agent/runs/feedback.jsonl`. Both are local files; back them up before clearing.
- Cost ceiling per menu: `max_dishes` (12) × 2 Tavily credits cold, 1-3 model calls per dish at under half a cent each; the menu-reading call is the largest single call.
- Caches under `.cache/roli_mvp/` make a repeated menu nearly free and fast; clearing them means a cold run.
- `experimental=True` is the only configuration that ranks anything today (every portion-rule and weights row is unapproved); the banner says so on every page.
