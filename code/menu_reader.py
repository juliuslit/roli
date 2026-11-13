"""The target function: photo + prompt file -> model via OpenRouter -> raw answer text.

read_menu() returns a dict:
  raw_text          exactly what the model returned (the scorers parse it)
  seconds           wall-clock time of the model call
  prompt_tokens, completion_tokens, cost_usd, provider   from OpenRouter's usage figures
  finish_reason     "stop" is normal; "length" means the answer was cut off by the token cap;
                    "deadline" means we closed the connection at DEADLINE_SECONDS
  error             empty, or the error message if the call failed

Parsing is left to scorers.parse_leniently(), so a bad answer is scored, not crashed on.
"""
import base64
import io
import time

import httpx
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import get_current_run_tree, traceable
from langsmith.wrappers import wrap_openai
from PIL import Image

from config import OPENROUTER_API_KEY, OPENROUTER_URL, TEST_SET, prompt_path

MAX_ANSWER_TOKENS = 24000           # hard cap on the answer, enforced by every host, so it caps cost everywhere.
                                    # 32,000 until 2026-10-29 morning, then 16,000 (DeepInfra's limit for Qwen3-VL is 16,384),
                                    # then 24,000 from 2026-10-29 evening: Qwen3.6 on Parasail wrote 186 sensible items for
                                    # photo 17 and still ran out at 16,000. Hosts whose limit is below the cap are skipped
                                    # by OpenRouter, so Qwen3-VL now goes to Novita (32,768), not DeepInfra.
DEADLINE_SECONDS = 300              # wall-clock limit per call: the answer is streamed and the connection is closed
                                    # at the deadline, which also stops generation and billing at hosts that support
                                    # cancellation (DeepInfra, Anthropic; not Google). TESTING VALUE - see the project notes' backlog.
PROVIDER_ORDER = ["deepinfra", "parasail"]   # default OpenRouter provider slugs for open-weight models; others allowed as fallback
PROVIDER_ORDER_BY_MODEL = {                  # per-model overrides, agreed 2026-10-29 after the Qwen3.6 batch on DeepInfra
    "anthropic/": ["anthropic"],                                  # Anthropic's own endpoint (supports cancellation)
    "google/": ["google-ai-studio", "google-vertex"],              # Google's own endpoints; NOTE: Google does not honour
                                                                  # cancellation, so a capped call bills in full
    "qwen/qwen3.6-35b-a3b": ["parasail", "deepinfra"],            # DeepInfra ran it at 20-30 tok/s, Parasail at ~100; same price
    "qwen/qwen3-vl-30b-a3b-instruct": ["novita", "siliconflow"],  # Parasail does not serve it; DeepInfra's 16,384 cap is below
                                                                  # ours; SiliconFlow allowed as fallback (slow: 25 tok/s in the smoke)
}
CLAUDE_PROVIDER_ORDER = PROVIDER_ORDER_BY_MODEL["anthropic/"]    # kept for older imports


def provider_order(model_id: str) -> list:
    """The hosts to try, in order, for this model (prefix match on the model id)."""
    for prefix, order in PROVIDER_ORDER_BY_MODEL.items():
        if model_id.startswith(prefix):
            return order
    return PROVIDER_ORDER
THINKING = False                    # hidden reasoning off: with it on, Qwen3.6 spent ~4 minutes thinking
                                    # and ran out of tokens before finishing the answer (smoke test, 2026-10-28)
REASONING_BY_MODEL = {              # endpoints where "off" is refused: the lowest setting they accept, hidden from the answer
    "anthropic/claude-sonnet-5.5": {"effort": "minimal", "exclude": True},   # "Reasoning is mandatory for this endpoint" (2026-10-30);
                                                                             # a trivial request at "minimal" used 0 reasoning tokens
    "google/gemini-3.8-flash": {"effort": "low", "exclude": True},             # same refusal (2026-10-30); at Google "minimal" still thought
                                                                             # (141 reasoning tokens on a 5-token answer), "low" gave 0
}


def reasoning_setting(model_id: str) -> dict:
    """The reasoning block sent to OpenRouter for this model: off, unless the endpoint refuses that."""
    return REASONING_BY_MODEL.get(model_id, {"enabled": THINKING})
CALL_TIMEOUT_SECONDS = 180          # NOT a deadline: the longest silence on the connection before giving up.
                                    # OpenRouter sends keep-alive bytes every 3 s, so this only catches a dead link.
TEMPERATURE = 0                     # most likely token every step; set 2026-10-28 after Haiku found 81 then 38
                                    # dishes on photo 06 at the default of 1.0 (same host, same prompt)


def load_prompt(version: str) -> str:
    return prompt_path(version).read_text().strip()


def photo_as_data_url(telegram_file: str) -> tuple:
    """Open the photo with Pillow (confirms it is a real image, gives its size) and encode it
    the way the API wants: a 'data:image/jpeg;base64,...' string. Returns (data_url, (width, height))."""
    path = TEST_SET / telegram_file
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as im:
        size = im.size
        mime = Image.MIME.get(im.format, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}", size


def make_model(model_id: str) -> ChatOpenAI:
    """LangChain's OpenAI-style client, pointed at OpenRouter."""
    return ChatOpenAI(
        model=model_id,
        base_url=OPENROUTER_URL,
        api_key=OPENROUTER_API_KEY,
        max_completion_tokens=MAX_ANSWER_TOKENS,
        temperature=TEMPERATURE,
        timeout=CALL_TIMEOUT_SECONDS,
        max_retries=1,
        stream_usage=True,                                        # token counts arrive in the last streamed chunk
        default_headers={"X-Title": "roli menu reader test"},
        extra_body={
            "usage": {"include": True},                           # ask OpenRouter to report cost
            "reasoning": reasoning_setting(model_id),
            "provider": {
                "order": provider_order(model_id),
                "allow_fallbacks": True,
                "data_collection": "deny",                        # no-training providers only
            },
        },
    )


def fetch_generation_stats(generation_id: str) -> dict:
    """OpenRouter keeps per-call stats (cost, provider) for a short while; fetch them by id."""
    if not generation_id:
        return {}
    for attempt in range(8):                 # stats can lag the answer by 10-20 s on long calls
        try:
            r = httpx.get(
                f"{OPENROUTER_URL}/generation",
                params={"id": generation_id},
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json().get("data", {}) or {}
        except httpx.HTTPError:
            pass
        time.sleep(3)
    return {}


@traceable(name="read_menu", run_type="chain")
def read_menu(telegram_file: str, prompt_version: str, model_id: str) -> dict:
    prompt = load_prompt(prompt_version)
    data_url, (width, height) = photo_as_data_url(telegram_file)
    message = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url}},
    ])
    out = {
        "model": model_id, "prompt_version": prompt_version, "telegram_file": telegram_file,
        "photo_size": [width, height], "raw_text": "", "seconds": None,
        "prompt_tokens": None, "completion_tokens": None, "cost_usd": None,
        "provider": None, "finish_reason": None, "generation_id": None, "error": "", "reasoning_tokens": None,
    }
    run = get_current_run_tree()                 # the LangSmith trace of this call
    if run is not None:                          # record the settings so runs at other temperatures can be told apart
        run.extra.setdefault("metadata", {}).update(
            {"model": model_id, "prompt_version": prompt_version, "temperature": TEMPERATURE, "thinking": reasoning_setting(model_id)})
    model = make_model(model_id)
    # Stream through the OpenAI-style client that LangChain built (traced by LangSmith's wrapper), not
    # through LangChain's own stream(): that one drops OpenRouter's generation id, host name and cost.
    client = wrap_openai(model.root_client)
    start = time.perf_counter()
    parts, usage, deadline_hit = [], {}, False
    stream = client.chat.completions.create(
        model=model_id, stream=True, temperature=TEMPERATURE, max_completion_tokens=MAX_ANSWER_TOKENS,
        messages=[{"role": "user", "content": message.content}],
        extra_body={**model.extra_body, "stream_options": {"include_usage": True}},
    )
    try:
        for chunk in stream:                     # one chunk per few tokens
            d = chunk.model_dump(exclude_none=True)
            out["generation_id"] = d.get("id") or out["generation_id"]
            out["provider"] = d.get("provider") or out["provider"]
            for choice in d.get("choices", []):
                parts.append((choice.get("delta") or {}).get("content") or "")
                if choice.get("finish_reason"):
                    out["finish_reason"] = choice["finish_reason"]
            if d.get("usage"):
                usage = d["usage"]
            if time.perf_counter() - start > DEADLINE_SECONDS:
                deadline_hit = True
                break
    except Exception as e:                       # the smoke test must survive one bad call
        out["error"] = f"{type(e).__name__}: {e}"
    finally:
        close = getattr(stream, "close", None)   # closes the connection: at supporting hosts this cancels the generation
        if close:
            close()
    out["seconds"] = time.perf_counter() - start
    out["raw_text"] = "".join(parts)
    if deadline_hit:
        out["finish_reason"] = "deadline"
    if out["error"] and not parts:
        return out

    out["prompt_tokens"] = usage.get("prompt_tokens")
    out["completion_tokens"] = usage.get("completion_tokens")
    out["reasoning_tokens"] = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")   # hidden thinking, billed as output
    if isinstance(usage.get("cost"), (int, float)):
        out["cost_usd"] = float(usage["cost"])

    stats = fetch_generation_stats(out["generation_id"]) if out["cost_usd"] is None else {}
    if stats:
        out["provider"] = stats.get("provider_name") or out["provider"]
        if out["cost_usd"] is None and stats.get("total_cost") is not None:
            out["cost_usd"] = float(stats["total_cost"])
        if out["prompt_tokens"] is None:
            out["prompt_tokens"] = stats.get("tokens_prompt")
            out["completion_tokens"] = stats.get("tokens_completion")
        if out["reasoning_tokens"] is None:
            out["reasoning_tokens"] = stats.get("native_tokens_reasoning")
    return out
