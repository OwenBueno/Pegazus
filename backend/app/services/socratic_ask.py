"""Quick Socratic canvas builder (US-8.1)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.services.jev_intent import classify_intent
from app.services.leak_check import hint_leaks_answer
from app.services.llm import chat, content_json, cost_of
from app.services.system2_hints import templated_hint

_REFUSE = {
    "en": "That doesn't look like a learning question. Ask about a concept, a step, or something you're studying.",
    "es": "Eso no parece una pregunta de aprendizaje. Pregunta por un concepto, un paso o algo que estés estudiando.",
}


@dataclass
class AskResult:
    intent: str
    refused: bool
    socratic_prompt: str
    steps: list[dict[str, Any]]
    exchange_index: int
    cost_usd: float
    genui: dict[str, Any]


def _refuse_prompt(locale: str) -> str:
    return _REFUSE["es" if locale.startswith("es") else "en"]


def _build_genui(
    *,
    session_id: str,
    prompt: str,
    steps: list[dict[str, Any]],
    exchange_index: int,
) -> dict[str, Any]:
    widgets: list[dict[str, Any]] = []
    if steps:
        widgets.append(
            {
                "id": "steps",
                "type": "SymbolicStepEditor",
                "visible": True,
                "props": {
                    "targetVariable": "x",
                    "inlineValidation": False,
                    "activeStepIndex": max(0, len(steps) - 1),
                    "initialSteps": [
                        {
                            "stepNumber": i + 1,
                            "latexExpression": s.get("latex", ""),
                            "isLocked": bool(s.get("locked", i < len(steps) - 1)),
                            "status": "PENDING",
                        }
                        for i, s in enumerate(steps)
                    ],
                },
            }
        )
    widgets.append(
        {
            "id": "socratic",
            "type": "SocraticDialogueBox",
            "visible": True,
            "props": {
                "hintTier": min(3, max(1, exchange_index)),
                "prompt": prompt[:240],
            },
        }
    )
    if steps:  # math outline only; other subjects get the dialogue alone
        widgets.append(
            {
                "id": "kbd",
                "type": "VirtualMathKeyboard",
                "visible": True,
                "props": {"layout": "algebra", "targetWidgetId": "steps"},
            }
        )
    return {
        "sessionId": session_id,
        "nodeId": "00000000-0000-0000-0000-000000000000",
        "itemId": "00000000-0000-0000-0000-000000000000",
        "scaffoldLevel": 2,
        "widgets": widgets,
    }


def _ask_system2(
    *,
    query: str,
    locale: str,
    exchange_index: int,
    prior_prompts: list[str],
    api_key: str,
    client: httpx.Client | None = None,
) -> tuple[str, list[dict[str, Any]], float]:
    raw = chat(
        [
            {
                "role": "system",
                "content": (
                    "You are the Socratic Tutor for one-off learning questions in any subject. "
                    "NEVER give the final answer or full solution. "
                    "Return ONLY JSON: "
                    '{"socratic_prompt":"1-2 sentences","steps":[{"latex":"...","locked":true}]} '
                    "steps: only for questions written in math notation (0-3 KaTeX outlines without "
                    "answers); otherwise []. "
                    "Write in the given locale; exchange is n of 3."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "locale": locale,
                        "exchange": exchange_index,
                        "query": query,
                        "prior_prompts": prior_prompts[:3],
                    }
                ),
            },
        ],
        api_key=api_key,
        model=settings.system2_model,
        temperature=0.3,
        client=client,
    )
    parsed = content_json(raw)
    if parsed is None:
        return templated_hint(exchange_index, locale, math_mode=False), [], 0.0
    prompt = str(parsed.get("socratic_prompt") or "").strip()
    raw_steps = parsed.get("steps") or []
    steps: list[dict[str, Any]] = []
    if isinstance(raw_steps, list):
        for s in raw_steps[:3]:
            if isinstance(s, dict) and s.get("latex"):
                steps.append(
                    {
                        "latex": str(s["latex"])[:200],
                        "locked": bool(s.get("locked", True)),
                    }
                )
    # Soft leak: reject prompts that look like final answers "x = 7"
    if not prompt or hint_leaks_answer(prompt, ["x = 7", "x=7"]):
        # also reject if prompt is mostly an equation
        if re.search(r"=\s*-?\d+", prompt or ""):
            prompt = templated_hint(exchange_index, locale, math_mode=False)
            steps = []
        elif not prompt:
            prompt = templated_hint(exchange_index, locale, math_mode=False)
    return prompt[:240], steps, cost_of(raw)


def run_socratic_ask(
    *,
    query: str,
    locale: str,
    exchange_index: int,
    prior_prompts: list[str] | None = None,
    session_id: str,
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> AskResult:
    prior = prior_prompts or []
    intent_res = classify_intent(user_query=query, api_key=api_key, client=client)
    cost = intent_res.cost_usd

    if intent_res.intent == "OFF_TOPIC":
        prompt = _refuse_prompt(locale)
        return AskResult(
            intent=intent_res.intent,
            refused=True,
            socratic_prompt=prompt,
            steps=[],
            exchange_index=exchange_index,
            cost_usd=cost,
            genui=_build_genui(
                session_id=session_id, prompt=prompt, steps=[], exchange_index=exchange_index
            ),
        )

    key = api_key or settings.openrouter_api_key
    if not key or settings.ai_enabled.lower() in ("0", "false", "no", "off"):
        prompt = templated_hint(exchange_index, locale, math_mode=False)
        steps: list[dict[str, Any]] = []
    else:
        prompt, steps, c2 = _ask_system2(
            query=query,
            locale=locale,
            exchange_index=exchange_index,
            prior_prompts=prior,
            api_key=key,
            client=client,
        )
        cost += c2

    return AskResult(
        intent=intent_res.intent,
        refused=False,
        socratic_prompt=prompt,
        steps=steps,
        exchange_index=exchange_index,
        cost_usd=cost,
        genui=_build_genui(
            session_id=session_id,
            prompt=prompt,
            steps=steps,
            exchange_index=exchange_index,
        ),
    )
