"""Session tutor chat — conceptual help without revealing answers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.services.component_catalog import scrub_urls
from app.services.jev_intent import classify_intent
from app.services.leak_check import forbidden_from_item_steps, forbidden_from_parts, hint_leaks_answer
from app.services.subject_profile import MATH_PROFILE, is_math, profile_prompt

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_TURNS = 8
MAX_HISTORY = 12

_ANSWER_SEEKING = re.compile(
    r"\b(what\s+is\s+the\s+answer|give\s+me\s+the\s+answer|just\s+tell\s+me|"
    r"solve\s+it\s+for\s+me|what'?s\s+the\s+result|cu[aá]l\s+es\s+la\s+respuesta|"
    r"dame\s+la\s+respuesta|resu[eé]lvelo)\b",
    re.I,
)

_REFUSE = {
    "en": "I can help with the idea behind this skill, not with unrelated requests. Ask about the concept or a step you are unsure about.",
    "es": "Puedo ayudarte con la idea de esta habilidad, no con peticiones ajenas a ella. Pregunta por el concepto o un paso que no entiendas.",
}

_NO_ANSWER = {
    "en": "I will not give the final answer. What part of the idea is unclear—order of steps, a symbol, or why a rule applies?",
    "es": "No daré la respuesta final. ¿Qué parte de la idea no queda clara: el orden, un símbolo, o por qué aplica una regla?",
}


@dataclass
class TutorChatResult:
    reply: str
    refused: bool
    source: str  # SYSTEM2 | TEMPLATE
    turn_index: int
    capped: bool
    cost_usd: float


def templated_tutor_reply(*, node_title: str, locale: str, answer_seeking: bool) -> str:
    loc = "es" if locale.startswith("es") else "en"
    if answer_seeking:
        return _NO_ANSWER[loc]
    title = (node_title or "this skill").strip()[:80]
    if loc == "es":
        return (
            f"Piensa en la idea central de «{title}». "
            "¿Qué regla o principio debería guiar el siguiente movimiento, sin calcular aún el resultado?"
        )
    return (
        f"Focus on the core idea of “{title}”. "
        "Which rule or principle should guide your next move—before you compute a result?"
    )


def _system_prompt(locale: str, profile: dict[str, Any] | None = None) -> str:
    profile = profile or MATH_PROFILE
    if is_math(profile):
        rules = """1. NEVER reveal the numeric result, final answer, or a fully worked solution.
2. NEVER write the next completed equation step for them.
3. You MAY explain concepts (e.g. order of operations, exponents before multiplication) and ask guiding questions.
4. You MAY refer to the shape of the expression without evaluating it."""
    else:
        rules = """1. NEVER reveal the correct answer, the correct option, or a completed solution.
2. NEVER complete the learner's answer for them.
3. You MAY explain concepts and rules with a DIFFERENT example, and ask guiding questions.
4. You MAY refer to the structure of the question without answering it."""
    return f"""You are a Socratic {profile["subject"]} tutor inside a practice session.
{profile_prompt(profile)}
Help the learner UNDERSTAND the topic. Do NOT solve the problem.

NON-NEGOTIABLE:
{rules}
5. Max THREE short sentences.
6. Locale: {locale}.
7. If they ask for the answer directly, refuse and redirect to a conceptual question.

Return ONLY JSON: {{"reply":"...","refused":false}}
"""


def _parse_reply(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
        if isinstance(data, dict) and data.get("reply"):
            return data
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(content[start : end + 1])
            if isinstance(data, dict) and data.get("reply"):
                return data
        except json.JSONDecodeError:
            return None
    return None


def generate_tutor_reply(
    *,
    message: str,
    locale: str,
    node_title: str,
    primer_md: str | None,
    statement_latex: str,
    prompt: str | None,
    steps: list[dict[str, Any]],
    history: list[dict[str, str]],
    turn_index: int,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    profile: dict[str, Any] | None = None,
    parts: list[dict[str, Any]] | None = None,
) -> TutorChatResult:
    """
    turn_index is 1-based count of user messages including the current one.
    """
    loc = "es" if str(locale).startswith("es") else "en"
    msg = (message or "").strip()[:500]
    capped = turn_index > MAX_TURNS
    if capped:
        reply = (
            "You have used the tutor chat limit for this problem. "
            "Try Hint or write your next step."
            if loc == "en"
            else "Alcanzaste el límite del tutor en este problema. Usa una pista o escribe tu siguiente paso."
        )
        return TutorChatResult(
            reply=reply,
            refused=False,
            source="TEMPLATE",
            turn_index=turn_index,
            capped=True,
            cost_usd=0.0,
        )

    answer_seeking = bool(_ANSWER_SEEKING.search(msg))
    forbidden = forbidden_from_item_steps(steps) + forbidden_from_parts(parts)

    # Off-topic via JEV heuristic/model
    intent = classify_intent(user_query=msg, api_key=api_key, subject=(profile or MATH_PROFILE)["subject"])
    if intent.intent == "OFF_TOPIC":
        return TutorChatResult(
            reply=_REFUSE[loc],
            refused=True,
            source="TEMPLATE",
            turn_index=turn_index,
            capped=False,
            cost_usd=intent.cost_usd,
        )

    if answer_seeking and not api_key:
        return TutorChatResult(
            reply=_NO_ANSWER[loc],
            refused=True,
            source="TEMPLATE",
            turn_index=turn_index,
            capped=False,
            cost_usd=0.0,
        )

    key = settings.openrouter_api_key if api_key is None else api_key
    if settings.ai_enabled.lower() in ("0", "false", "no", "off") or not key:
        return TutorChatResult(
            reply=templated_tutor_reply(
                node_title=node_title, locale=loc, answer_seeking=answer_seeking
            ),
            refused=answer_seeking,
            source="TEMPLATE",
            turn_index=turn_index,
            capped=False,
            cost_usd=0.0,
        )

    hist = []
    for h in history[-MAX_HISTORY:]:
        role = str(h.get("role") or "")
        content = str(h.get("content") or "").strip()[:400]
        if role in ("user", "assistant") and content:
            hist.append({"role": role, "content": content})

    user_payload = {
        "node_title": (node_title or "")[:120],
        "primer_excerpt": (primer_md or "")[:800],
        "problem_prompt": (prompt or "")[:400],
        "statement_shape": (statement_latex or "")[:200],
        "learner_message": msg,
        "history": hist,
        "note": "Do not evaluate statement_shape; use it only for topic context.",
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }

    def _call(model: str, http: httpx.Client) -> tuple[str | None, bool, float]:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": _system_prompt(loc, profile)},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.35,
        }
        resp = http.post(OPENROUTER_CHAT_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        parsed = _parse_reply(content)
        if not parsed:
            return None, False, cost
        # ponytail: the tutor never links, even research citations (Doc 10 R4); pass cited_urls to allow them.
        reply = scrub_urls(str(parsed.get("reply") or "")[:600], set()).strip()
        refused = bool(parsed.get("refused"))
        return reply or None, refused, cost

    own = client is None
    http = client or httpx.Client(timeout=settings.system2_timeout_s)
    total_cost = intent.cost_usd
    try:
        for model in (settings.system2_model, settings.system2_fallback_model):
            try:
                reply, refused, cost = _call(model, http)
                total_cost += cost
                if not reply:
                    continue
                if hint_leaks_answer(reply, forbidden) or re.search(
                    r"=\s*-?\d+(\.\d+)?\b", reply
                ):
                    reply2, refused2, cost2 = _call(model, http)
                    total_cost += cost2
                    if reply2 and not hint_leaks_answer(reply2, forbidden):
                        if not re.search(r"=\s*-?\d+(\.\d+)?\b", reply2):
                            return TutorChatResult(
                                reply=reply2,
                                refused=refused2 or answer_seeking,
                                source="SYSTEM2",
                                turn_index=turn_index,
                                capped=False,
                                cost_usd=total_cost,
                            )
                    # fall through to template
                    continue
                return TutorChatResult(
                    reply=reply,
                    refused=refused or answer_seeking,
                    source="SYSTEM2",
                    turn_index=turn_index,
                    capped=False,
                    cost_usd=total_cost,
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                continue
    finally:
        if own:
            http.close()

    return TutorChatResult(
        reply=templated_tutor_reply(
            node_title=node_title, locale=loc, answer_seeking=answer_seeking
        ),
        refused=answer_seeking,
        source="TEMPLATE",
        turn_index=turn_index,
        capped=False,
        cost_usd=total_cost,
    )
