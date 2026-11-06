"""Subject profile (Doc 10 §3): one trust-boundary clamp for every profile write + inference."""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings
from app.services.component_catalog import CATEGORIES
from app.services.llm import chat_json

NOTATIONS = ("none", "math", "chem", "code")
LEVELS = ("beginner", "intermediate", "advanced")
CODE_LANGUAGES = ("python", "javascript")
ANSWER_MODES = (
    "choice", "match", "order", "categorize", "short_text", "cloze", "numeric", "math", "code", "speech",
    "free_text",
)
_BCP47 = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,3}$")

MATH_PROFILE: dict[str, Any] = {
    "subject": "Mathematics",
    "family_hint": "Math",
    "categories": ["core", "math"],
    "notation": "math",
    "code_language": None,
    "target_language": None,
    "instruction_language": "en",
    "answer_modes": ["math", "choice", "match", "numeric"],
    "level": "intermediate",
    "allowed": True,
    "reason": "",
}


def _lang(v: Any) -> str | None:
    s = str(v or "").strip()
    return s if _BCP47.match(s) else None


def _pick(v: Any, allowed: tuple[str, ...]) -> list[str]:
    vals = v if isinstance(v, list) else []
    return list(dict.fromkeys(s for s in (str(x).strip().lower() for x in vals) if s in allowed))


def clamp_profile(raw: Any, *, goal: str = "", locale: str = "en") -> dict[str, Any]:
    """Any dict (or None) → a valid profile. Unknown values are dropped, never trusted."""
    r = raw if isinstance(raw, dict) else {}
    cats = ["core", *(c for c in _pick(r.get("categories"), CATEGORIES) if c != "core")]
    if _lang(r.get("target_language")) and "media" not in cats:
        cats.append("media")  # learning a language means hearing it (AudioClip lives in media)
    notation = str(r.get("notation") or "").strip().lower()
    if notation not in NOTATIONS:
        notation = "math" if "math" in cats else "none"
    code_lang = str(r.get("code_language") or "").strip().lower()
    level = str(r.get("level") or "").strip().lower()
    subject = " ".join(str(r.get("subject") or "").split())[:120] or " ".join(goal.split())[:120] or "General"
    return {
        "subject": subject,
        "family_hint": " ".join(str(r.get("family_hint") or "").split())[:40],
        "categories": cats,
        "notation": notation,
        "code_language": code_lang if code_lang in CODE_LANGUAGES else None,
        "target_language": _lang(r.get("target_language")),
        "instruction_language": _lang(r.get("instruction_language")) or _lang(locale) or "en",
        "answer_modes": _pick(r.get("answer_modes"), ANSWER_MODES) or ["choice", "match"],
        "level": level if level in LEVELS else "beginner",
        "allowed": r.get("allowed") is not False,
        "reason": str(r.get("reason") or "").strip()[:300],
    }


def is_math(profile: dict[str, Any] | None) -> bool:
    return (profile or MATH_PROFILE).get("notation") == "math"


def profile_prompt(profile: dict[str, Any] | None) -> str:
    """Three lines injected into every generation prompt."""
    p = profile or MATH_PROFILE
    code = f" ({p['code_language']})" if p.get("code_language") else ""
    target = f"; target language {p['target_language']}" if p.get("target_language") else ""
    return (
        f"Subject: {p['subject']} (level: {p['level']}).\n"
        f"Notation: {p['notation']}{code}.\n"
        f"Write for the learner in {p['instruction_language']}{target}."
    )


_INFER_SYSTEM = (
    "You classify a learner's study goal into a subject profile. Return ONLY JSON: "
    '{"subject":"short human label","family_hint":"e.g. Language, History, Math",'
    '"categories":["core", ...],"notation":"none|math|chem|code",'
    '"code_language":"python|javascript|null","target_language":"BCP-47 or null",'
    '"instruction_language":"BCP-47","answer_modes":["choice","match",...],'
    '"level":"beginner|intermediate|advanced","allowed":true,"reason":""}\n'
    f"categories ⊂ {list(CATEGORIES)} (always include core). answer_modes ⊂ {list(ANSWER_MODES)}.\n"
    "notation: math for mathematics (equations, arithmetic, calculus, statistics), chem for "
    "chemical formulas, code for programming, otherwise none.\n"
    "free_text = short written explanations graded by rubric; include it for conceptual "
    "subjects (sciences, history, humanities).\n"
    "target_language: only for learning a foreign language. instruction_language: the language "
    "the learner wrote the goal in (default to the given locale).\n"
    "allowed=false ONLY for unsafe, harmful, sexual, hateful or clearly non-educational requests; "
    "then reason = one short, kind sentence for the learner in the instruction language."
)


def infer_subject_profile(
    goal: str,
    exam_text: str | None = None,
    sources: list[str] | None = None,
    *,
    api_key: str,
    locale: str = "en",
) -> dict[str, Any]:
    """One LLM call, then ``clamp_profile``. No key / no answer → a neutral core profile."""
    key = api_key or (settings.openrouter_api_key if settings.ai_on else "")
    data = None
    if key:
        data = chat_json(
            [
                {"role": "system", "content": _INFER_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "goal": goal.strip()[:500],
                            "locale": locale,
                            "exam_excerpt": (exam_text or "").strip()[:1500],
                            "materials": [s.strip()[:500] for s in sources or [] if s and s.strip()][:3],
                        }
                    ),
                },
            ],
            api_key=key,
            task="fast",
            temperature=0.0,
        )
    return clamp_profile(data or {"categories": ["core"], "notation": "none"}, goal=goal, locale=locale)
