"""``choice``: ``{"ids": ["a"]}`` vs ``{"correctIds": ["a"], "explanation"?}`` — set equality."""

from __future__ import annotations

from typing import Any

from app.graders import MAX_ITEMS, GradeResult, bad_answer, scored


def grade_choice(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    ids = answer.get("ids")
    if not isinstance(ids, list) or not 0 < len(ids) <= MAX_ITEMS:
        return bad_answer()
    if not all(isinstance(i, str) and len(i) <= 40 for i in ids):
        return bad_answer()
    ok = set(ids) == {str(c) for c in spec["correctIds"]}
    return scored(1.0 if ok else 0.0, spec.get("explanation") if ok else None)
