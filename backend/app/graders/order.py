"""``order``: ``{"order": [2, 0, 1]}`` vs canonical ``{"order": […]}``; score = normalized Kendall tau."""

from __future__ import annotations

from typing import Any

from app.graders import GradeResult, bad_answer, int_list, scored


def grade_order(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    key, got = int_list(spec["order"]), int_list(answer.get("order"))
    if not key or got is None or sorted(got) != sorted(key) or len(set(key)) != len(key):
        return bad_answer()
    rank = {v: i for i, v in enumerate(key)}
    r = [rank[v] for v in got]
    n = len(r)
    # ponytail: O(n²) pairwise inversion count; fine for OrderSteps' ≤ 7 items (bounded to 20).
    # Upgrade path: merge-sort inversion count if lists ever get long.
    inversions = sum(1 for i in range(n) for j in range(i + 1, n) if r[i] > r[j])
    total = n * (n - 1) // 2
    return scored(1 - inversions / total if total else 1.0)
