"""The chat model, built the way the harness builds it, plus two small helpers."""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from PIL import Image

from . import harness
from .config import LLM_TIMEOUT_SECONDS, MODEL_ID


def make_chat_model(model_id: str | None = None, *, max_tokens: int | None = None, timeout: float | None = None) -> ChatOpenAI:
    """LangChain's OpenAI-style client pointed at OpenRouter, with the harness's decisions:
    temperature 0, per-model provider order, no-training providers only, reasoning off where allowed."""
    model_id = model_id or MODEL_ID
    return ChatOpenAI(
        model=model_id,
        base_url=harness.OPENROUTER_URL,
        api_key=harness.OPENROUTER_API_KEY,
        max_completion_tokens=max_tokens or harness.MAX_ANSWER_TOKENS,
        temperature=harness.TEMPERATURE,
        timeout=timeout or LLM_TIMEOUT_SECONDS,
        max_retries=1,
        default_headers={"X-Title": "roli agent"},
        extra_body={
            "usage": {"include": True},
            "reasoning": harness.reasoning_setting(model_id),
            "provider": {
                "order": harness.provider_order(model_id),
                "allow_fallbacks": True,
                "data_collection": "deny",
            },
        },
    )


def image_data_url(path: str | Path) -> tuple[str, tuple[int, int]]:
    """Encode a photo as the API wants it (same approach as the harness, any path allowed)."""
    raw = Path(path).read_bytes()
    with Image.open(io.BytesIO(raw)) as im:
        size = im.size
        mime = Image.MIME.get(im.format, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}", size


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json_object(text: str) -> dict[str, Any] | None:
    """The LLM is asked for one JSON object. Accept it with or without code fences or
    surrounding prose; return None when nothing parses. Never raises."""
    if not isinstance(text, str):
        return None
    cleaned = _FENCE.sub("", text.strip())
    for candidate in (cleaned, cleaned[cleaned.find("{"): cleaned.rfind("}") + 1]):
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


# -- Phase 3: one rate limit for every model call of a process -----------------------------------------------------------------------

import threading as _threading
import time as _time


class RateLimitedLLM:
    """Wraps a chat model so that all threads together stay under `per_minute` requests (OpenRouter allows 20 per minute per model on this
    account) and a 429 is retried after a pause instead of failing the dish. `invoke` only; attribute access falls through to the model."""

    def __init__(self, model, *, per_minute: int = 16, max_retries: int = 4, sleep=_time.sleep, clock=_time.monotonic) -> None:
        self._model = model
        self.per_minute = per_minute
        self.max_retries = max_retries
        self._sleep, self._clock = sleep, clock
        self._lock = _threading.Lock()
        self._times: list[float] = []
        self.waits = 0
        self.retries = 0

    def _acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                self._times = [t for t in self._times if now - t < 60.0]
                if len(self._times) < self.per_minute:
                    self._times.append(now)
                    return
                wait = 60.0 - (now - self._times[0]) + 0.05
            self.waits += 1
            self._sleep(max(wait, 0.1))

    def invoke(self, messages, **kwargs):
        last = None
        for attempt in range(self.max_retries + 1):
            self._acquire()
            try:
                return self._model.invoke(messages, **kwargs)
            except Exception as exc:                        # noqa: BLE001
                text = f"{type(exc).__name__}: {exc}"
                if "429" not in text and "Rate limit" not in text and "RateLimit" not in type(exc).__name__:
                    raise
                last = exc
                self.retries += 1
                self._sleep(15.0 * (attempt + 1))
        raise last

    def __getattr__(self, name):
        return getattr(self._model, name)
