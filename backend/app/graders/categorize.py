"""``categorize``: ``{"assign": {"0": 1}}`` (item → bucket) vs ``{"assign": [bucket per item]}``."""

from __future__ import annotations

from typing import Any

from app.graders import MAX_ITEMS, GradeResult, bad_answer, int_list, scored


def grade_categorize(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    key, got = int_list(spec["assign"]), answer.get("assign")
    if not key or not isinstance(got, dict) or len(got) > MAX_ITEMS:
        return bad_answer()
    if not all(isinstance(k, str) and k.isdigit() and type(v) is int for k, v in got.items()):
        return bad_answer()
    right = sum(1 for i, bucket in enumerate(key) if got.get(str(i)) == bucket)
    return scored(right / len(key))
