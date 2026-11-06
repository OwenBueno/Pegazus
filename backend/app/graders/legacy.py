"""``(parts, grader)`` for an item from its math ``steps`` + ``genui_plan``.

Python twin of the item backfill in supabase/migrations/20261009180000_multi_subject.sql
(tests/test_multi_subject_backfill.py asserts both produce the same JSON).
"""

from __future__ import annotations

import hashlib
from typing import Any

SELECTION = ("QuickCheck", "MatchPairs", "NumberLine")


def _strip_nulls(v: Any) -> Any:
    """jsonb_strip_nulls: drop null object fields recursively (array elements stay)."""
    if isinstance(v, dict):
        return {k: _strip_nulls(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [_strip_nulls(x) for x in v]
    return v


def _without(p: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {k: v for k, v in p.items() if k not in keys}


def _selection_part(plan: Any, item_id: Any) -> dict[str, Any] | None:
    if not isinstance(plan, dict) or plan.get("primary") not in SELECTION:
        return None
    widgets = plan.get("widgets") if isinstance(plan.get("widgets"), list) else []
    w = next((w for w in widgets if isinstance(w, dict) and w.get("type") == plan["primary"]), None)
    p = w.get("props") if w else None
    if not isinstance(p, dict):
        return None
    t = plan["primary"]
    if t == "QuickCheck":
        cid = p.get("correctId")
        choices = p.get("choices") if isinstance(p.get("choices"), list) else []
        if cid in (None, "") or not any(isinstance(c, dict) and c.get("id") == cid for c in choices):
            return None
        return {
            "component": t, "grader": "choice",
            "props": _without(p, "correctId", "correct_latex", "correctLatex", "explanation"),
            "answer_spec": {"correctIds": [cid], "explanation": p.get("explanation")},
        }
    if t == "NumberLine":
        if isinstance(p.get("target"), bool) or not isinstance(p.get("target"), (int, float)):
            return None
        step = p.get("step")
        return {
            "component": t, "grader": "numeric",
            "props": _without(p, "target", "tolerance", "correct_latex", "correctLatex"),
            "answer_spec": {
                "value": p["target"],
                "abs_tolerance": p["tolerance"] if "tolerance" in p else (float(step) if step is not None else 1.0) / 2,
            },
        }
    pairs = p.get("pairs")
    if not isinstance(pairs, list) or len(pairs) < 2:
        return None
    # Rights are shown shuffled; the shuffle lives in answer_spec, never in props.
    order = sorted(range(len(pairs)), key=lambda k: hashlib.md5(f"{item_id}:{k}".encode()).hexdigest())
    pos = {k: i for i, k in enumerate(order)}
    side = lambda e, s: e.get(s) if isinstance(e, dict) else None  # noqa: E731
    return {
        "component": t, "grader": "match",
        "props": {
            **_without(p, "pairs", "correct_latex", "correctLatex"),
            "lefts": [side(e, "left") for e in pairs],
            "rights": [side(pairs[k], "right") for k in order],
        },
        "answer_spec": {"pairs": [[k, pos[k]] for k in range(len(pairs))]},
    }


def legacy_parts(steps: Any, genui_plan: Any, item_id: Any) -> tuple[list[dict[str, Any]], str]:
    part = _selection_part(genui_plan, str(item_id))
    if part:
        return [_strip_nulls(part)], part["grader"]
    parts = []
    for s in steps if isinstance(steps, list) else []:
        s = s if isinstance(s, dict) else {}
        parts.append(_strip_nulls({
            "component": "SymbolicStepEditor", "grader": "sympy", "props": {},
            "answer_spec": {"latex": s.get("latex"), "sympy": s.get("sympy"), "operation": s.get("operation")},
            "justification": s.get("justification"),
        }))
    return parts, "sympy"
