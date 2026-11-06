"""``sympy``: ``{"latex": "x=5"}`` vs one derivation step ``{latex, sympy, operation}`` (today's math path)."""

from __future__ import annotations

import re
from typing import Any

from app.graders import MAX_TEXT, GradeResult, bad_answer
from app.services.rule_engine import decide_verdict
from app.workers.math_evaluator import evaluate_step_safe


def _step_target(step: dict[str, Any]) -> str:
    # Prefer sympy ASCII for deterministic parse; fall back to latex.
    return step.get("sympy") or step.get("latex") or ""


def _norm_latex(s: str) -> str:
    return re.sub(r"\s+|\\[,;!: ]|\\left|\\right", "", s or "")


def final_answer_shortcut(submitted: str, final_step: dict[str, Any]) -> dict[str, Any] | None:
    """Eval result if `submitted` is already the final answer, else None.

    Equations compare by solution set, so every valid intermediate line is "equivalent" to
    the answer; only a solved form (`x = 5`) or the literal last line counts as finishing.
    """
    res = evaluate_step_safe(submitted, _step_target(final_step))
    if not res.get("is_equivalent"):
        return None
    literal = _norm_latex(submitted) in {
        _norm_latex(str(final_step.get("latex") or "")),
        _norm_latex(str(final_step.get("sympy") or "")),
    } - {""}
    return res if literal or res.get("is_solved_form") else None


def grade_sympy(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    """One step, no JEV: `evaluate_step` keeps the shortcut/prior-step/JEV order around this."""
    latex, target = answer.get("latex"), _step_target(spec)
    if not isinstance(latex, str) or not latex.strip() or len(latex) > MAX_TEXT or not target:
        return bad_answer()
    eval_result = evaluate_step_safe(latex, target)
    d = decide_verdict(eval_result, operation=spec.get("operation"))
    return GradeResult(
        d.verdict, d.is_success, 1.0 if d.is_success else 0.0, extra={"eval_result": eval_result}
    )
