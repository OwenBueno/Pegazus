"""``flashcards``: ``{"self": [0|1 per card]}`` self-rating (Again/Good) vs ``{"count": n}``."""

from __future__ import annotations

from typing import Any

from app.graders import GradeResult, bad_answer, int_list, scored


def grade_flashcards(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    rates = int_list(answer.get("self"))
    if not rates or len(rates) != spec["count"] or any(r > 1 for r in rates):
        return bad_answer()
    r = scored(sum(rates) / len(rates))
    r.decided_by = "CLIENT"  # the learner's own rating (Doc 11 MS-3.4)
    return r
