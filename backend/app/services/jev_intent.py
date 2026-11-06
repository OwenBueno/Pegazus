"""Jev Quick Socratic intent classification (Doc 05 §2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.services.jev_client import OPENROUTER_DECISIONS_URL, _breaker, _parse_choice

_OFF_TOPIC_KEYWORDS = (
    "weather",
    "recipe",
    "stock",
    "crypto",
    "dating",
    "joke",
    "clima",
    "receta",
)


@dataclass
class IntentResult:
    intent: str
    cost_usd: float
    raw: dict[str, Any] | None = None


def _heuristic_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in _OFF_TOPIC_KEYWORDS):
        return "OFF_TOPIC"
    # Learning cues for any subject; very short queries without one are treated as chatter.
    learning = any(
        t in q
        for t in (
            "equation",
            "algebra",
            "solve",
            "derivative",
            "integral",
            "why",
            "how",
            "what",
            "mean",
            "say",
            "translat",
            "explain",
            "x =",
            "math",
            "ecuaci",
            "álgebra",
            "por qué",
            "porque",
            "cómo",
            "como",
            "qué",
            "significa",
            "traduc",
        )
    )
    if not learning and len(query.split()) < 3:
        return "OFF_TOPIC"
    if "check" in q or "wrong" in q or "revisa" in q:
        return "CHECK_MY_WORK"
    if "why" in q or "por qué" in q or "porque" in q:
        return "CONCEPTUAL_EXPLANATION"
    return "PROCEDURAL_STUCK"


def classify_intent(
    *,
    user_query: str,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    subject: str = "the current subject",
) -> IntentResult:
    """Return intent string. Falls back to heuristic when AI off / low conf / error."""
    if settings.ai_enabled.lower() in ("0", "false", "no", "off"):
        return IntentResult(intent=_heuristic_intent(user_query), cost_usd=0.0)

    key = api_key or settings.openrouter_api_key
    if not key or not _breaker.allow():
        return IntentResult(intent=_heuristic_intent(user_query), cost_usd=0.0)

    payload = {
        "model": settings.jev_model,
        "state": {"user_query": user_query},
        "questions": {
            "intent": {
                "type": "choice",
                "instructions": "What is the learner asking for in `user_query`?",
                "criteria": {
                    "CONCEPTUAL_EXPLANATION": "Wants to understand why a rule or step works.",
                    "PROCEDURAL_STUCK": "Is stuck on a specific problem and wants the next step.",
                    "CHECK_MY_WORK": "Wants their own solution checked.",
                    "OFF_TOPIC": f"Unsafe, or not a request to learn {subject[:120]}.",
                    "none": "None of the above fits.",
                },
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }
    timeout = settings.jev_timeout_ms / 1000.0
    own = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.post(OPENROUTER_DECISIONS_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            _breaker.record(True)
            return IntentResult(intent=_heuristic_intent(user_query), cost_usd=0.0)
        data = resp.json()
        answers = data.get("answers") or data.get("results") or data
        if not isinstance(answers, dict):
            _breaker.record(True)
            return IntentResult(intent=_heuristic_intent(user_query), cost_usd=0.0)
        intent = _parse_choice(answers, "intent", settings.jev_choice_confidence)
        usage = data.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        _breaker.record(False)
        if intent is None:
            return IntentResult(
                intent=_heuristic_intent(user_query), cost_usd=cost, raw=data
            )
        return IntentResult(intent=intent, cost_usd=cost, raw=data)
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, KeyError, TypeError):
        _breaker.record(True)
        return IntentResult(intent=_heuristic_intent(user_query), cost_usd=0.0)
    finally:
        if own:
            http.close()
