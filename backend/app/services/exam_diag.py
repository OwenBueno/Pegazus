"""Apply lite mastery hints from a prior exam excerpt onto planned path nodes."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import psycopg

from app.config import settings
from app.services.kst_diagnostic import upsert_p_mastery
from app.services.llm import chat_json


def apply_exam_mastery_hints(
    conn: psycopg.Connection,
    *,
    path_id: UUID,
    user_id: UUID,
    exam_markdown: str,
    node_titles: list[dict[str, Any]],
    api_key: str,
) -> None:
    """
    node_titles: [{id, title}, ...]
    Sets p_mastery high for topics the exam suggests are already ok, low for weak ones.
    """
    if not exam_markdown.strip() or not node_titles:
        return
    titles = [n["title"] for n in node_titles]
    mapping = _llm_mastery_map(exam_markdown, titles, api_key) or _heuristic_map(
        exam_markdown, titles
    )
    by_title = {n["title"]: n["id"] for n in node_titles}
    for title, level in mapping.items():
        nid = by_title.get(title)
        if nid is None:
            # fuzzy: substring
            for t, i in by_title.items():
                if title.lower() in t.lower() or t.lower() in title.lower():
                    nid = i
                    break
        if nid is None:
            continue
        p = 0.92 if level == "mastered" else 0.12 if level == "weak" else 0.4
        upsert_p_mastery(conn, user_id=user_id, node_id=nid, p_mastery=p)


def _llm_mastery_map(
    exam: str, titles: list[str], api_key: str
) -> dict[str, str] | None:
    key = api_key or settings.openrouter_api_key
    if not key:
        return None
    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "From a prior exam excerpt and a list of planned skill titles, "
                    "return ONLY JSON: {\"ratings\":[{\"title\":\"...\",\"level\":\"mastered|weak|unknown\"}]}. "
                    "Infer weak from errors, blanks, or hard topics; mastered from clearly correct simple items. "
                    "Use exact titles from the list when possible."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"titles": titles, "exam_excerpt": exam[:3500]}),
            },
        ],
        api_key=key,
        task="strong",
        temperature=0.1,
    )
    if not data:
        return None
    out: dict[str, str] = {}
    for row in data.get("ratings") or []:
        if not isinstance(row, dict):
            continue
        t = str(row.get("title") or "").strip()
        lv = str(row.get("level") or "unknown").strip().lower()
        if t and lv in ("mastered", "weak", "unknown"):
            out[t] = lv
    return out or None


def _heuristic_map(exam: str, titles: list[str]) -> dict[str, str]:
    """Keyword overlap: titles mentioned in exam → unknown; others weak (need practice)."""
    el = exam.lower()
    out: dict[str, str] = {}
    for t in titles:
        toks = [w for w in re_split(t.lower()) if len(w) > 3]
        if toks and sum(1 for w in toks if w in el) >= max(1, len(toks) // 2):
            out[t] = "unknown"
        else:
            out[t] = "weak"
    return out


def re_split(s: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", s)
