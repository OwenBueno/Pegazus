"""Shared OpenRouter chat helper: pooled client, retries, task-based model routing."""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from typing import Any, Literal

import httpx

from app.config import settings

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

Task = Literal["fast", "strong", "web"]
_RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504})

# Per-task call counter (read by scripts/eval_lessons.py).
CALLS: Counter[str] = Counter()
# Per-task token usage: "<task>.prompt" / ".completion" / ".cached" (provider prefix-cache hits).
TOKENS: Counter[str] = Counter()

_lock = threading.Lock()
_client: httpx.Client | None = None
_sem = threading.BoundedSemaphore(max(1, settings.llm_max_concurrency))


def model_for(task: Task) -> str:
    return settings.system2_model if task == "fast" else settings.system2_fallback_model


def _timeout_for(task: Task) -> float:
    return settings.item_timeout_s if task == "fast" else settings.system2_timeout_s


def shared_client() -> httpx.Client:
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(
                timeout=settings.system2_timeout_s,
                limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
            )
        return _client


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }


def _backoff(attempt: int, retry_after: str | None) -> None:
    try:
        wait = float(retry_after) if retry_after else 0.6 * (2**attempt)
    except ValueError:
        wait = 0.6 * (2**attempt)
    time.sleep(min(wait, 5.0))


def _post(
    http: httpx.Client, body: dict[str, Any], api_key: str, t: float
) -> tuple[int, str | None, bytes]:
    """POST with a wall-clock deadline. httpx timeouts are per-read, and OpenRouter pads slow
    non-streaming responses with keep-alive bytes, so a read timeout alone never fires."""
    deadline = time.monotonic() + t
    with http.stream(
        "POST", OPENROUTER_CHAT_URL, json=body, headers=_headers(api_key), timeout=t
    ) as resp:
        chunks: list[bytes] = []
        for chunk in resp.iter_bytes():
            if time.monotonic() > deadline:
                raise TimeoutError(f"{body['model']} exceeded {t:.0f}s")
            chunks.append(chunk)
        return resp.status_code, resp.headers.get("retry-after"), b"".join(chunks)


def chat(
    messages: list[dict[str, Any]],
    *,
    api_key: str,
    task: Task = "strong",
    temperature: float = 0.3,
    json_mode: bool = True,
    plugins: list[dict[str, Any]] | None = None,
    model: str | None = None,
    client: httpx.Client | None = None,
    timeout: float | None = None,
    retries: int = 2,
) -> dict[str, Any] | None:
    """POST a chat completion; return the raw response JSON or None. Retries 429/5xx/timeouts."""
    if not api_key:
        return None
    body: dict[str, Any] = {
        "model": model or model_for(task),
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if plugins:
        body["plugins"] = plugins
    if task == "fast":
        # SymPy verifies fast-task output, so reasoning tokens only add latency.
        body["reasoning"] = {"enabled": False}
    elif settings.llm_reasoning_effort:
        body["reasoning"] = {"effort": settings.llm_reasoning_effort}
    http = client or shared_client()
    t = timeout or _timeout_for(task)
    for attempt in range(retries + 1):
        with _lock:
            CALLS[task] += 1
        try:
            with _sem:
                status, retry_after, content = _post(http, body, api_key, t)
        except TimeoutError:
            # Slow provider: retry once on the fast model rather than wait out another deadline.
            fast = model_for("fast")
            if attempt >= retries or body["model"] == fast:
                return None
            body["model"] = fast
            body["reasoning"] = {"enabled": False}
            continue
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < retries:
                _backoff(attempt, None)
                continue
            return None
        except httpx.HTTPError:
            return None
        if status in _RETRY_STATUS and attempt < retries:
            _backoff(attempt, retry_after)
            continue
        if status >= 400:
            return None
        try:
            data = json.loads(content)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        _count_tokens(task, data.get("usage"))
        return data
    return None


def _count_tokens(task: str, usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    details = usage.get("prompt_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    with _lock:
        for key, val in (
            ("prompt", usage.get("prompt_tokens")),
            ("completion", usage.get("completion_tokens")),
            ("cached", cached),
        ):
            if isinstance(val, int):
                TOKENS[f"{task}.{key}"] += val


def parse_json_object(content: Any) -> dict[str, Any] | None:
    """Parse a JSON object from model output, tolerating ```json fences or stray prose."""
    s = str(content or "").strip()
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def content_json(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return parse_json_object(content)


def chat_json(messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any] | None:
    return content_json(chat(messages, **kwargs))


def cost_of(raw: dict[str, Any] | None) -> float:
    try:
        return float(((raw or {}).get("usage") or {}).get("cost") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def url_citations(raw: dict[str, Any] | None) -> list[dict[str, str]]:
    """Web-plugin citations: choices[0].message.annotations[].url_citation."""
    out: list[dict[str, str]] = []
    try:
        anns = raw["choices"][0]["message"].get("annotations") or []  # type: ignore[index]
    except (KeyError, IndexError, TypeError, AttributeError):
        return out
    for a in anns:
        c = a.get("url_citation") if isinstance(a, dict) else None
        if isinstance(c, dict) and c.get("url"):
            out.append({
                "url": str(c["url"])[:500],
                "title": str(c.get("title") or "")[:200],
                # The fetched snippet: what the critic checks claims against.
                "quote": " ".join(str(c.get("content") or "").split())[:400],
            })
    return out
