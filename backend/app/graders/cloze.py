"""``cloze``: ``{"blanks": ["100"]}`` vs ``{"answers": [["100", "100°C"], …]}``; ``exact`` per blank."""

from __future__ import annotations

from typing import Any

from app.graders import MAX_ITEMS, GradeResult, bad_answer, scored
from app.graders.exact import matches


def grade_cloze(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    keys, blanks = spec["answers"], answer.get("blanks")
    if not isinstance(keys, list) or not keys or not isinstance(blanks, list) or len(blanks) > MAX_ITEMS:
        return bad_answer()
    right = 0
    for i, accepted in enumerate(keys):
        ok = matches(blanks[i] if i < len(blanks) else "", accepted, spec)
        if ok is None:
            return bad_answer()
        right += ok
    return scored(right / len(keys))
