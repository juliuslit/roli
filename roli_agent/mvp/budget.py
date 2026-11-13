"""Phase 3 local-testing milestone: spending safeguards (Julius, 2026-11-04).

One `MenuBudget` per menu run, shared by every thread of that run. Every model call goes through `BudgetedLLM` (check before, charge after;
the menu-reading call included) and every live search through `BudgetedSource` (a cached search costs nothing and is never blocked). Limits:
a per-menu model-call budget (default $0.50), a per-menu search-credit limit, a daily model budget and a daily search-credit limit, the daily
figures from an append-only ledger of finished runs (`roli_agent/runs/spend_ledger.jsonl`). When a limit is reached the call raises
`BudgetExceeded`; the dish records `budget_stopped`, dishes not yet started are `skipped`, and the run still ranks what it has.

Costs: the provider reports the price of most calls (`usage.cost`); a call it does not price is ESTIMATED from its tokens and the model's
public per-token prices (fetched once from OpenRouter's public models endpoint, cached a week, no key sent; an env override exists), and
when no price is known a flat reserve per call is charged. Actual and estimated spending are reported separately and both count toward
the limits. Nothing here buys credit, changes billing or enables top-ups.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

PRICES_URL = "https://openrouter.ai/api/v1/models"
UNPRICED_CALL_RESERVE_USD = Decimal("0.01")        # charged for a call with neither a reported cost nor a known per-token price


class BudgetExceeded(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass
class Limits:
    menu_usd: Decimal = Decimal("0.50")
    menu_search_credits: int = 30
    daily_usd: Decimal = Decimal("5.00")
    daily_search_credits: int = 300

    @classmethod
    def from_env(cls, **overrides: Any) -> "Limits":
        """`ROLI_BUDGET_MENU_USD`, `ROLI_BUDGET_MENU_CREDITS`, `ROLI_BUDGET_DAILY_USD`, `ROLI_BUDGET_DAILY_CREDITS`; explicit overrides win."""
        env = os.environ
        values = dict(menu_usd=Decimal(env.get("ROLI_BUDGET_MENU_USD", "0.50")), menu_search_credits=int(env.get("ROLI_BUDGET_MENU_CREDITS", "30")),
                      daily_usd=Decimal(env.get("ROLI_BUDGET_DAILY_USD", "5.00")), daily_search_credits=int(env.get("ROLI_BUDGET_DAILY_CREDITS", "300")))
        for k, v in overrides.items():
            if v is not None:
                values[k] = Decimal(str(v)) if k.endswith("usd") else int(v)
        return cls(**values)

    def as_dict(self) -> dict[str, Any]:
        return {"menu_usd": str(self.menu_usd), "menu_search_credits": self.menu_search_credits, "daily_usd": str(self.daily_usd), "daily_search_credits": self.daily_search_credits}


class Prices:
    """Per-token prices used only to ESTIMATE a call the provider did not price. `source` says where they came from."""

    def __init__(self, prompt_per_token: Decimal | None, completion_per_token: Decimal | None, source: str) -> None:
        self.prompt, self.completion, self.source = prompt_per_token, completion_per_token, source

    @property
    def known(self) -> bool:
        return self.prompt is not None and self.completion is not None

    def estimate(self, prompt_tokens: int, completion_tokens: int) -> Decimal | None:
        if not self.known:
            return None
        return Decimal(prompt_tokens) * self.prompt + Decimal(completion_tokens) * self.completion

    @classmethod
    def unknown(cls) -> "Prices":
        return cls(None, None, "unknown")

    @classmethod
    def load(cls, model_id: str, cache_path: Path | None, *, fetch: Callable[[], dict] | None = None, ttl_seconds: float = 7 * 24 * 3600,
             clock: Callable[[], float] = time.time) -> "Prices":
        """Env override (`ROLI_PRICE_PROMPT_PER_M`, `ROLI_PRICE_COMPLETION_PER_M`, dollars per million tokens), else the cached public price
        list, else a fetch of the public endpoint (no key), else unknown. Never raises."""
        p, c = os.environ.get("ROLI_PRICE_PROMPT_PER_M"), os.environ.get("ROLI_PRICE_COMPLETION_PER_M")
        if p and c:
            return cls(Decimal(p) / 1_000_000, Decimal(c) / 1_000_000, "env ROLI_PRICE_*_PER_M")
        cached: dict[str, Any] = {}
        if cache_path is not None and cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except ValueError:
                cached = {}
        entry = cached.get(model_id)
        if entry and clock() - float(entry.get("fetched_at", 0)) <= ttl_seconds:
            return cls(Decimal(entry["prompt"]), Decimal(entry["completion"]), f"openrouter public price list, cached {entry.get('fetched_on', '')}")
        try:
            data = (fetch or _fetch_public_prices)()
            model = next((m for m in data.get("data", []) if m.get("id") == model_id), None)
            pricing = (model or {}).get("pricing") or {}
            if pricing.get("prompt") is None or pricing.get("completion") is None:
                return cls(Decimal(entry["prompt"]), Decimal(entry["completion"]), "openrouter public price list, stale cache") if entry else cls.unknown()
            prices = cls(Decimal(str(pricing["prompt"])), Decimal(str(pricing["completion"])), f"openrouter public price list, fetched {date.today()}")
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cached[model_id] = {"prompt": str(prices.prompt), "completion": str(prices.completion), "fetched_at": clock(), "fetched_on": str(date.today())}
                cache_path.write_text(json.dumps(cached, indent=1), encoding="utf-8")
            return prices
        except Exception:                                   # noqa: BLE001  prices are a convenience; the budget still works without them
            return cls(Decimal(entry["prompt"]), Decimal(entry["completion"]), "openrouter public price list, stale cache") if entry else cls.unknown()


def _fetch_public_prices() -> dict:
    import httpx
    return httpx.get(PRICES_URL, timeout=10.0).json()


class SpendLedger:
    """Append-only JSON lines, one per finished (or stopped) run; `today()` sums the lines dated today (local date)."""

    def __init__(self, path: Path | None) -> None:
        self.path = Path(path) if path is not None else None
        self._lock = threading.Lock()

    def today(self, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        usd, credits, runs = Decimal(0), 0, 0
        if self.path is not None and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("date") == str(today):
                    usd += Decimal(str(row.get("model_usd_actual", "0"))) + Decimal(str(row.get("model_usd_estimated", "0")))
                    credits += int(row.get("search_credits") or 0)
                    runs += 1
        return {"date": str(today), "model_usd": usd, "search_credits": credits, "runs": runs}

    def append(self, row: dict[str, Any]) -> None:
        if self.path is None:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")


def usage_of(reply: Any) -> tuple[int, int, Decimal | None]:
    """(prompt tokens, completion tokens, reported cost or None) from a LangChain reply, the way the Phase 2B meter reads it."""
    usage = (getattr(reply, "usage_metadata", None) or {})
    meta = (getattr(reply, "response_metadata", None) or {}).get("token_usage") or {}
    prompt = int(usage.get("input_tokens") or meta.get("prompt_tokens") or 0)
    completion = int(usage.get("output_tokens") or meta.get("completion_tokens") or 0)
    cost = meta.get("cost")
    reported = Decimal(str(cost)) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
    return prompt, completion, reported


@dataclass
class MenuBudget:
    limits: Limits
    ledger: SpendLedger
    prices: Prices
    run_id: str = ""
    model_usd_actual: Decimal = Decimal(0)
    model_usd_estimated: Decimal = Decimal(0)
    calls: int = 0
    calls_priced: int = 0
    calls_estimated: int = 0
    calls_unpriced: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    search_credits: int = 0
    interruptions: list[str] = field(default_factory=list)
    topups: int = 0                                                       # 3K: top-up searches run on this menu
    tripped_threads: set[int] = field(default_factory=set)
    closed: bool = False

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self.daily_before = self.ledger.today()

    # -- model calls ----------------------------------------------------------------------------------------------------------

    @property
    def model_usd(self) -> Decimal:
        return self.model_usd_actual + self.model_usd_estimated

    def _stop(self, kind: str, message: str) -> None:
        if message not in self.interruptions:
            self.interruptions.append(message)
        self.tripped_threads.add(threading.get_ident())
        raise BudgetExceeded(kind, message)

    def check_model(self, reserve: Decimal = Decimal(0)) -> None:
        with self._lock:
            spent = self.model_usd
            if spent + reserve > self.limits.menu_usd:
                self._stop("menu_usd", f"menu model budget reached: ${spent:.4f} spent of ${self.limits.menu_usd} (next call blocked)")
            daily = self.daily_before["model_usd"] + spent
            if daily + reserve > self.limits.daily_usd:
                self._stop("daily_usd", f"daily model budget reached: ${daily:.4f} today of ${self.limits.daily_usd} (next call blocked)")

    def charge_model(self, reply: Any) -> None:
        prompt, completion, reported = usage_of(reply)
        with self._lock:
            self.calls += 1
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            if reported is not None:
                self.calls_priced += 1
                self.model_usd_actual += reported
                return
            estimate = self.prices.estimate(prompt, completion)
            if estimate is not None and (prompt or completion):
                self.calls_estimated += 1
                self.model_usd_estimated += estimate
            else:
                self.calls_unpriced += 1
                self.model_usd_estimated += UNPRICED_CALL_RESERVE_USD

    # -- searches -------------------------------------------------------------------------------------------------------------

    def check_search(self, n: int = 1) -> None:
        with self._lock:
            if self.search_credits + n > self.limits.menu_search_credits:
                self._stop("menu_credits", f"menu search-credit limit reached: {self.search_credits} of {self.limits.menu_search_credits} used (next search blocked)")
            daily = self.daily_before["search_credits"] + self.search_credits
            if daily + n > self.limits.daily_search_credits:
                self._stop("daily_credits", f"daily search-credit limit reached: {daily} today of {self.limits.daily_search_credits} (next search blocked)")

    def charge_search(self, n: int) -> None:
        with self._lock:
            self.search_credits += max(0, n)

    # -- dishes and reporting -------------------------------------------------------------------------------------------------

    def allows_dish(self, reserve_usd: Decimal, reserve_credits: int) -> tuple[bool, str]:
        """Before a dish starts: is there room for a typical dish? (A dish that starts may still be stopped mid-way.)"""
        try:
            self.check_model(reserve_usd)
            self.check_search(reserve_credits)
        except BudgetExceeded as exc:
            self.tripped_threads.discard(threading.get_ident())      # a pre-check is not a stop inside a dish
            return False, str(exc)
        return True, ""

    def tripped_in_this_thread(self) -> bool:
        return threading.get_ident() in self.tripped_threads

    def note_topup(self) -> None:
        """3K (12.20): one more top-up search spent on this menu."""
        with self._lock:
            self.topups += 1

    def reserve_topup(self, cap: int, reserve_usd: Decimal, reserve_credits: int) -> bool:
        """3K: one atomic check-and-count for a top-up (the dishes of a menu run in parallel threads): True and counted when the menu still has room for a dish's reserve and
        fewer than `cap` top-ups have been counted."""
        with self._lock:
            if self.topups >= cap:
                return False
            self.topups += 1
        ok, _ = self.allows_dish(reserve_usd, reserve_credits)
        if not ok:
            with self._lock:
                self.topups -= 1
            return False
        return True

    def report(self) -> dict[str, Any]:
        with self._lock:
            return {
                "model_usd_actual": f"{self.model_usd_actual:.6f}", "model_usd_estimated": f"{self.model_usd_estimated:.6f}", "model_usd_total": f"{self.model_usd:.6f}",
                "model_calls": self.calls, "model_calls_priced_by_provider": self.calls_priced, "model_calls_estimated_from_tokens": self.calls_estimated,
                "model_calls_unpriced_flat_reserve": self.calls_unpriced, "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
                "price_source": self.prices.source, "search_credits": self.search_credits, "limits": self.limits.as_dict(),
                "daily_before_this_run": {"model_usd": f"{self.daily_before['model_usd']:.4f}", "search_credits": self.daily_before["search_credits"], "runs": self.daily_before["runs"]},
                "daily_after_this_run": {"model_usd": f"{self.daily_before['model_usd'] + self.model_usd:.4f}", "search_credits": self.daily_before["search_credits"] + self.search_credits},
                "interruptions": list(self.interruptions), "topups": self.topups,
            }

    def close(self) -> None:
        """Write this run's spending to the ledger (once)."""
        with self._lock:
            if self.closed:
                return
            self.closed = True
            row = {"date": str(date.today()), "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_id": self.run_id,
                   "model_usd_actual": f"{self.model_usd_actual:.6f}", "model_usd_estimated": f"{self.model_usd_estimated:.6f}", "model_calls": self.calls,
                   "search_credits": self.search_credits, "interruptions": len(self.interruptions)}
        self.ledger.append(row)


class BudgetedLLM:
    """Check the budget before a model call, charge its cost after. `invoke` only; other attributes fall through."""

    def __init__(self, inner: Any, budget: MenuBudget) -> None:
        self._inner, self._budget = inner, budget

    def invoke(self, messages, **kwargs):
        self._budget.check_model()
        reply = self._inner.invoke(messages, **kwargs)
        self._budget.charge_model(reply)
        return reply

    def __getattr__(self, name):
        return getattr(self._inner, name)


class BudgetedSource:
    """Check the search-credit limit before a search that would spend a credit; a search the cache can answer is free and never blocked."""

    def __init__(self, inner: Any, budget: MenuBudget) -> None:
        self._inner, self._budget = inner, budget

    @property
    def credits_used(self) -> int:
        return getattr(self._inner, "credits_used", 0)

    @property
    def hits(self) -> int:
        return getattr(self._inner, "hits", 0)

    def search(self, query: str, mode: str, max_results: int = 10) -> list[dict]:
        has = getattr(self._inner, "has", None)
        cached = bool(has(query, mode, max_results)) if callable(has) else False
        if not cached:
            self._budget.check_search(1)
        before = self.credits_used
        results = self._inner.search(query, mode, max_results)
        spent = self.credits_used - before
        self._budget.charge_search(spent if spent > 0 else (0 if cached or has is not None else 1))
        return results
