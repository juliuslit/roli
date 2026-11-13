"""Measurement for requirement 7: seconds per stage, LLM calls and tokens (and cost when the provider reports it),
USDA service calls and HTTP requests, cache hits. Nothing here changes any result."""

from __future__ import annotations

import time
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import httpx

from .models import DishCosts


class Meter:
    def __init__(self) -> None:
        self.stage_seconds: dict[str, float] = {}
        self.llm_calls_by_stage: dict[str, int] = {}
        self.llm_prompt_tokens = 0
        self.llm_completion_tokens = 0
        self.llm_cost_usd: Decimal | None = None
        self.llm_failures = 0
        self.counts: dict[str, int] = {}
        self._stage = "other"
        self._started = time.perf_counter()

    @contextmanager
    def stage(self, name: str):
        previous, self._stage = self._stage, name
        t = time.perf_counter()
        try:
            yield
        finally:
            self.stage_seconds[name] = round(self.stage_seconds.get(name, 0.0) + time.perf_counter() - t, 3)
            self._stage = previous

    def count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def record_llm(self, reply: Any) -> None:
        self.llm_calls_by_stage[self._stage] = self.llm_calls_by_stage.get(self._stage, 0) + 1
        usage = (getattr(reply, "usage_metadata", None) or {})
        meta = (getattr(reply, "response_metadata", None) or {}).get("token_usage") or {}
        self.llm_prompt_tokens += int(usage.get("input_tokens") or meta.get("prompt_tokens") or 0)
        self.llm_completion_tokens += int(usage.get("output_tokens") or meta.get("completion_tokens") or 0)
        cost = meta.get("cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            self.llm_cost_usd = (self.llm_cost_usd or Decimal(0)) + Decimal(str(cost))

    def costs(self, *, usda_http_requests: int | None = None, search_credits: int = 0, pages_fetched: int = 0, pages_from_cache: int = 0) -> DishCosts:
        return DishCosts(
            stage_seconds=dict(self.stage_seconds), llm_calls=sum(self.llm_calls_by_stage.values()), llm_calls_by_stage=dict(self.llm_calls_by_stage),
            llm_prompt_tokens=self.llm_prompt_tokens, llm_completion_tokens=self.llm_completion_tokens, llm_cost_usd=self.llm_cost_usd,
            llm_failures=self.llm_failures, usda_searches=self.counts.get("usda_searches", 0), usda_lookups=self.counts.get("usda_lookups", 0),
            usda_portion_lookups=self.counts.get("usda_portion_lookups", 0), usda_http_requests=usda_http_requests,
            match_cache_hits=self.counts.get("match_cache_hits", 0), search_credits=search_credits, pages_fetched=pages_fetched,
            pages_from_cache=pages_from_cache, seconds=round(time.perf_counter() - self._started, 1),
        )


class MeteredLLM:
    """Wraps any `.invoke(messages)` model so every call is counted against the current stage."""

    def __init__(self, inner: Any, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter

    def invoke(self, messages):
        try:
            reply = self._inner.invoke(messages)
        except Exception:
            self._meter.llm_failures += 1
            self._meter.llm_calls_by_stage[self._meter._stage] = self._meter.llm_calls_by_stage.get(self._meter._stage, 0) + 1
            raise
        self._meter.record_llm(reply)
        return reply


class MeteredService:
    """Counts service calls by kind; delegates everything to the real NutritionService."""

    def __init__(self, inner: Any, meter: Meter) -> None:
        self._inner = inner
        self._meter = meter

    def search_foods(self, query, limit=5, data_types=None):
        self._meter.count("usda_searches")
        return self._inner.search_foods(query, limit, data_types) if data_types is not None else self._inner.search_foods(query, limit)

    def get_inputs(self, fdc_id):
        self._meter.count("usda_lookups")
        return self._inner.get_inputs(fdc_id)

    def get_nutrition(self, fdc_id):
        self._meter.count("usda_lookups")
        return self._inner.get_nutrition(fdc_id)

    def get_portions(self, fdc_id):
        self._meter.count("usda_portion_lookups")
        return self._inner.get_portions(fdc_id)

    def __getattr__(self, name):
        """`usda_status`, `allowance_ok` and anything else (3D) fall through uncounted."""
        return getattr(self._inner, name)


class CountingTransport(httpx.BaseTransport):
    """For live runs: counts the HTTP requests the USDA client actually sends (cache hits send none)."""

    def __init__(self, inner: httpx.BaseTransport | None = None) -> None:
        self._inner = inner or httpx.HTTPTransport()
        self.requests = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()
