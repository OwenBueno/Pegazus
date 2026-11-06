"""``match``: ``{"pairs": [[left, right], …]}`` by index vs the key's pairs; score = fraction."""

from __future__ import annotations

from typing import Any

from app.graders import MAX_ITEMS, GradeResult, bad_answer, int_list, scored


def _one_to_one(raw: Any) -> set[tuple[int, int]] | None:
    """Pairs where every left and every right appears once (no "match everything" answers)."""
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        return None
    pairs = set()
    for p in raw:
        ok = int_list(p)
        if ok is None or len(ok) != 2:
            return None
        pairs.add((ok[0], ok[1]))
    if len({a for a, _ in pairs}) != len(raw) or len({b for _, b in pairs}) != len(raw):
        return None
    return pairs


def grade_match(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    key, got = _one_to_one(spec["pairs"]), _one_to_one(answer.get("pairs"))
    if not key or got is None:
        return bad_answer()
    return scored(len(key & got) / len(key))
