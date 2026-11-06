"""llm.chat: wall-clock deadline survives keep-alive padding; slow model falls back to fast."""

from __future__ import annotations

import json
import time

import httpx

from app.services import llm


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_trickling_response_hits_deadline_then_falls_back_to_fast():
    models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        models.append(body["model"])
        if body["model"] == llm.model_for("fast"):
            payload = {"choices": [{"message": {"content": '{"ok": true}'}}]}
            return httpx.Response(200, json=payload)

        def trickle():
            for _ in range(100):  # 5 s of OpenRouter-style keep-alive whitespace
                time.sleep(0.05)
                yield b" "

        return httpx.Response(200, content=trickle())

    t0 = time.monotonic()
    out = llm.chat_json(
        [{"role": "user", "content": "x"}],
        api_key="k",
        task="strong",
        client=_client(handler),
        timeout=0.3,
    )
    assert time.monotonic() - t0 < 2.0
    assert out == {"ok": True}
    assert models == [llm.model_for("strong"), llm.model_for("fast")]


def test_fast_task_disables_reasoning_and_parses_fenced_json():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        payload = {"choices": [{"message": {"content": '```json\n{"a": 1}\n```'}}]}
        return httpx.Response(200, json=payload)

    out = llm.chat_json([{"role": "user", "content": "x"}], api_key="k", task="fast", client=_client(handler))
    assert out == {"a": 1}
    assert seen["reasoning"] == {"enabled": False}
