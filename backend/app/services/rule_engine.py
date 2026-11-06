"""Rule-engine verdicts and FSRS grade mapping (Doc 05 §6.1) — RULES only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VERDICT_CORRECT_OPTIMAL = "CORRECT_OPTIMAL"
VERDICT_CORRECT_SUBOPTIMAL = "CORRECT_SUBOPTIMAL"
VERDICT_SYNTAX_ERROR = "SYNTAX_ERROR"
VERDICT_SIGN_ERROR = "SIGN_ERROR"
VERDICT_CALCULATION_SLIP = "CALCULATION_SLIP"
VERDICT_TIMEOUT = "TIMEOUT"
# Non-math graders (app/graders): success stays CORRECT_OPTIMAL so banners/JEV keep working.
VERDICT_PARTIAL = "PARTIAL"
VERDICT_INCORRECT = "INCORRECT"

# Latency buckets (ms) — Doc 03 style defaults for P1-lite
LATENCY_FAST_MS = 5000
LATENCY_SLOW_MS = 30000


@dataclass
class RuleDecision:
    verdict: str
    is_success: bool
    fsrs_grade: int | None
    decided_by: str = "RULES"
    structure_ok: bool = True


def structure_ok_for_operation(operation: str | None) -> bool:
    """P1-lite stub: GIVEN is always OK; full AST matrix deferred."""
    del operation
    return True


def decide_verdict(
    eval_result: dict[str, Any],
    *,
    operation: str | None = None,
    hint_level: int = 0,
    latency_ms: int = 0,
    is_final_step: bool = False,
) -> RuleDecision:
    err = eval_result.get("error")
    if err == "EVALUATION_TIMEOUT":
        return RuleDecision(
            verdict=VERDICT_TIMEOUT,
            is_success=False,
            fsrs_grade=_fsrs_grade(False, hint_level, latency_ms) if is_final_step else None,
            structure_ok=False,
        )
    if err == "INPUT_TOO_LONG" or (err and str(err).startswith("PARSE_ERROR")):
        return RuleDecision(
            verdict=VERDICT_SYNTAX_ERROR,
            is_success=False,
            fsrs_grade=_fsrs_grade(False, hint_level, latency_ms) if is_final_step else None,
            structure_ok=False,
        )
    if not eval_result.get("success"):
        return RuleDecision(
            verdict=VERDICT_SYNTAX_ERROR,
            is_success=False,
            fsrs_grade=_fsrs_grade(False, hint_level, latency_ms) if is_final_step else None,
            structure_ok=False,
        )

    struct_ok = structure_ok_for_operation(operation)
    if eval_result.get("is_equivalent"):
        verdict = VERDICT_CORRECT_OPTIMAL if struct_ok else VERDICT_CORRECT_SUBOPTIMAL
        return RuleDecision(
            verdict=verdict,
            is_success=True,
            fsrs_grade=_fsrs_grade(True, hint_level, latency_ms) if is_final_step else None,
            structure_ok=struct_ok,
        )

    if eval_result.get("sign_error"):
        return RuleDecision(
            verdict=VERDICT_SIGN_ERROR,
            is_success=False,
            fsrs_grade=_fsrs_grade(False, hint_level, latency_ms) if is_final_step else None,
            structure_ok=struct_ok,
        )

    return RuleDecision(
        verdict=VERDICT_CALCULATION_SLIP,
        is_success=False,
        fsrs_grade=_fsrs_grade(False, hint_level, latency_ms) if is_final_step else None,
        structure_ok=struct_ok,
    )


def _fsrs_grade(success: bool, hint_level: int, latency_ms: int, score: float = 1.0) -> int:
    """
    1 if failed or Level 3 hint; 2 if Level 1–2 hint, slow or partial credit (0 < score < 1);
    3 if correct no hints; 4 if correct, no hints, fast.
    """
    partial = 0 < score < 1
    if hint_level >= 3 or not (success or partial):
        return 1
    if partial or hint_level >= 1 or latency_ms >= LATENCY_SLOW_MS:
        return 2
    if latency_ms <= LATENCY_FAST_MS:
        return 4
    return 3
