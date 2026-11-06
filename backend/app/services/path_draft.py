"""Propose the path outline: modules with objectives + prerequisite links (no items)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.llm import chat_json
from app.services.subject_profile import MATH_PROFILE, profile_prompt

MIN_MODULES = 4


class OutlineError(RuntimeError):
    """The model gave no usable outline after one repair round (never faked)."""


def _system(profile: dict[str, Any]) -> str:
    return (
        "You are a curriculum researcher. Return ONLY JSON: "
        '{"modules":[{"title":"short skill title",'
        '"objectives":["learner can ..."],"prerequisites":[0]}]}\n'
        f"{profile_prompt(profile)}\n"
        f"- 6 to 12 skill modules for {profile['subject']} at {profile['level']} level, "
        "ordered from prerequisites to the goal.\n"
        "- objectives: 1-3 measurable 'learner can ...' statements.\n"
        "- prerequisites: 0-based indices of EARLIER modules this one directly "
        "depends on (empty for roots). Do not just chain every module to the "
        "previous one; only list real dependencies.\n"
        "- Prefer skills implied by the exam and learner materials when present.\n"
        "- Titles only, no primers or problems."
    )


def propose_outline(
    *,
    goal_text: str,
    exam_markdown: str | None = None,
    source_markdowns: list[str] | None = None,
    api_key: str,
    client: httpx.Client | None = None,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return 6–12 modules ``{title, objectives, prerequisites}`` ordered prerequisites → goal.

    ``prerequisites`` holds indices of EARLIER modules only, so the result is always a DAG.
    One repair retry with the validation error, then ``OutlineError`` (no static fallback).
    """
    profile = profile or MATH_PROFILE
    sources = source_markdowns or []
    context_bits = [f"Goal: {goal_text.strip()}"]
    if exam_markdown and exam_markdown.strip():
        context_bits.append(f"Prior exam / problem set excerpt:\n{exam_markdown.strip()[:3000]}")
    if sources:
        joined = "\n---\n".join(s.strip()[:2000] for s in sources if s.strip())[:4000]
        context_bits.append(f"Learner materials:\n{joined}")

    key = api_key or (settings.openrouter_api_key if settings.ai_on else "")
    if not key:
        raise OutlineError("no API key")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system(profile)},
        {"role": "user", "content": "\n\n".join(context_bits)},
    ]
    error = ""
    for _ in range(2):
        data = chat_json(messages, api_key=key, task="strong", temperature=0.2, client=client)
        mods = clean_modules(data)
        if len(mods) >= MIN_MODULES:
            return mods
        error = "no response" if data is None else f"only {len(mods)} valid modules (need 6-12)"
        messages = messages[:2] + [
            {"role": "user", "content": f"Your previous answer was invalid: {error}. Return the full JSON again."}
        ]
    raise OutlineError(error)


def clean_modules(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Validate model modules; remap prerequisite indices after dropping bad rows."""
    raw = (data or {}).get("modules")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    new_index: dict[int, int] = {}
    for orig, m in enumerate(raw[:12]):
        if isinstance(m, str):
            title, objectives, pre = m, [], None
        elif isinstance(m, dict):
            title = m.get("title")
            objectives = [str(o).strip()[:200] for o in (m.get("objectives") or []) if str(o).strip()][:3]
            pre = m.get("prerequisites")
        else:
            continue
        title = str(title or "").strip()[:120]
        if not title:
            continue
        i = len(out)
        if isinstance(pre, list):
            prereqs = sorted(
                {
                    new_index[int(p)]
                    for p in pre
                    if str(p).strip().isdigit() and int(p) in new_index
                }
            )
        else:
            prereqs = [i - 1] if i else []
        new_index[orig] = i
        out.append({"title": title, "objectives": objectives, "prerequisites": prereqs})
    return out
