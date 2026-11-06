"""System 2 Socratic hints via OpenRouter (Doc 05 §3)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from app.services.leak_check import forbidden_from_item_steps, forbidden_from_parts, hint_leaks_answer
from app.services.subject_profile import MATH_PROFILE, is_math, profile_prompt

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

_TEMPLATES: dict[tuple[int, str], str] = {
    (1, "en"): "Which rule or principle should this step obey?",
    (2, "en"): "What check could tell you if both sides stayed balanced?",
    (3, "en"): "Which term looks inconsistent with the previous line?",
    (1, "es"): "¿Qué regla o principio debería respetar este paso?",
    (2, "es"): "¿Qué comprobación te diría si ambos lados siguieron equilibrados?",
    (3, "es"): "¿Qué término parece inconsistente con la línea anterior?",
}
# Non-math items have no "sides" or "lines": tiers 2-3 point at the options instead.
_GENERIC_TEMPLATES: dict[tuple[int, str], str] = {
    (2, "en"): "How could you check each option against the rule before choosing?",
    (3, "en"): "Which part of your answer conflicts with the key idea of this skill?",
    (2, "es"): "¿Cómo podrías comprobar cada opción con la regla antes de elegir?",
    (3, "es"): "¿Qué parte de tu respuesta contradice la idea clave de esta habilidad?",
}


def templated_hint(tier: int, locale: str, category: str = "OTHER", *, math_mode: bool = True) -> str:
    del category
    loc = "es" if locale.startswith("es") else "en"
    t = max(1, min(3, tier))
    return (_TEMPLATES if math_mode or t == 1 else _GENERIC_TEMPLATES)[(t, loc)]


def _system_prompt(locale: str, tier: int, profile: dict[str, Any] | None = None) -> str:
    profile = profile or MATH_PROFILE
    if is_math(profile):
        reveal = "the correct equation, numbers, calculation steps, or final answer"
        tier1 = "the underlying mathematical law. Mention zero numbers"
        tier3 = "the exact line or term that failed"
    else:
        reveal = "the correct answer, the correct option, or a completed solution"
        tier1 = "the underlying rule or idea of the skill"
        tier3 = "the exact part of the answer that failed"
    return f"""You are the Socratic Tutor Engine inside Cognitive OS. Your role is strictly to guide the learner to self-identify their error.
{profile_prompt(profile)}

NON-NEGOTIABLE GUARDRAILS:
1. NEVER reveal {reveal}.
2. NEVER use praise filler ("Good job!", "Almost there!").
3. Limit your output to a maximum of TWO (2) concise sentences.
4. Respond in the learner's locale: {locale}.
5. Strictly follow Hint Tier {tier}:
   - TIER 1 (Conceptual): Direct attention to {tier1}.
   - TIER 2 (Strategic): Suggest a diagnostic verification technique.
   - TIER 3 (Operational): Identify {tier3} without providing the correction.

Return ONLY valid JSON with keys:
hint_tier (1|2|3), detected_error_category (string), pedagogical_focus (string <=120), socratic_prompt (string <=240).
"""


def _parse_payload(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
        if isinstance(data, dict) and data.get("socratic_prompt"):
            return data
    except json.JSONDecodeError:
        pass
    # Try fenced json
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(content[start : end + 1])
            if isinstance(data, dict) and data.get("socratic_prompt"):
                return data
        except json.JSONDecodeError:
            return None
    return None


def generate_socratic_hint(
    *,
    locale: str,
    hint_level: int,
    statement_latex: str,
    expected_latex: str,
    submitted_latex: str,
    steps: list[dict[str, Any]],
    verdict: str | None = None,
    client: httpx.Client | None = None,
    api_key: str | None = None,
    profile: dict[str, Any] | None = None,
    parts: list[dict[str, Any]] | None = None,
) -> tuple[str, float, str]:
    """
    Returns (socratic_prompt, cost_usd, source) where source is 'SYSTEM2' | 'TEMPLATE'.
    """
    tier = max(1, min(3, hint_level))
    loc = locale if locale in ("en", "es") else "en"
    forbidden = forbidden_from_item_steps(steps) + forbidden_from_parts(parts)
    key = api_key or settings.openrouter_api_key
    fallback = templated_hint(tier, loc, verdict or "OTHER", math_mode=is_math(profile))

    if settings.ai_enabled.lower() in ("0", "false", "no", "off"):
        return fallback, 0.0, "TEMPLATE"
    if not key:
        return fallback, 0.0, "TEMPLATE"

    user_msg = {
        "statement_latex": statement_latex,
        "expected_step_latex": expected_latex,
        "submitted_latex": submitted_latex,
        "hint_tier": tier,
        "prior_verdict": verdict,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }

    def _call(model: str, http: httpx.Client) -> tuple[dict[str, Any] | None, float]:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": _system_prompt(loc, tier, profile)},
                {"role": "user", "content": json.dumps(user_msg)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        resp = http.post(OPENROUTER_CHAT_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        return _parse_payload(content), cost

    own = client is None
    http = client or httpx.Client(timeout=settings.system2_timeout_s)
    total_cost = 0.0
    try:
        for model in (settings.system2_model, settings.system2_fallback_model):
            try:
                payload, cost = _call(model, http)
                total_cost += cost
                if not payload:
                    continue
                prompt = str(payload["socratic_prompt"]).strip()
                if hint_leaks_answer(prompt, forbidden):
                    # one retry
                    payload2, cost2 = _call(model, http)
                    total_cost += cost2
                    if payload2:
                        prompt2 = str(payload2["socratic_prompt"]).strip()
                        if not hint_leaks_answer(prompt2, forbidden):
                            return prompt2, total_cost, "SYSTEM2"
                    continue
                return prompt, total_cost, "SYSTEM2"
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                continue
    finally:
        if own:
            http.close()

    return fallback, total_cost, "TEMPLATE"
