"""Grader registry (Doc 10 §5): pure ``(answer_spec, answer) -> GradeResult`` functions.

The client only sends what the learner did (``answer``); keys live in ``answer_spec`` server-side.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.services.rule_engine import (
    VERDICT_CORRECT_OPTIMAL,
    VERDICT_INCORRECT,
    VERDICT_PARTIAL,
    VERDICT_SYNTAX_ERROR,
)

MAX_ITEMS = 20  # ids / pairs / items / blanks per answer
MAX_TEXT = 500


@dataclass
class GradeResult:
    verdict: str
    is_success: bool
    score: float  # 0..1
    feedback: str | None = None  # short, learner-facing
    decided_by: str = "RULES"
    extra: dict[str, Any] = field(default_factory=dict)  # sympy: eval_result for JEV


def scored(score: float, feedback: str | None = None) -> GradeResult:
    """Fraction-correct result; success only at 1.0."""
    score = max(0.0, min(1.0, float(score)))
    if score >= 1:
        return GradeResult(VERDICT_CORRECT_OPTIMAL, True, 1.0, feedback)
    return GradeResult(VERDICT_PARTIAL if score > 0 else VERDICT_INCORRECT, False, score, feedback)


def bad_answer() -> GradeResult:
    return GradeResult(VERDICT_SYNTAX_ERROR, False, 0.0)


def int_list(raw: Any) -> list[int] | None:
    """Bounded list of non-negative ints (bools rejected), else None."""
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        return None
    if not all(type(v) is int and v >= 0 for v in raw):
        return None
    return raw


from app.graders.categorize import grade_categorize  # noqa: E402
from app.graders.choice import grade_choice  # noqa: E402
from app.graders.cloze import grade_cloze  # noqa: E402
from app.graders.code_tests import grade_code_tests  # noqa: E402
from app.graders.exact import grade_exact  # noqa: E402
from app.graders.flashcards import grade_flashcards  # noqa: E402
from app.graders.match import grade_match  # noqa: E402
from app.graders.numeric import grade_numeric  # noqa: E402
from app.graders.order import grade_order  # noqa: E402
from app.graders.rubric_llm import grade_rubric_llm  # noqa: E402
from app.graders.speech_match import grade_speech_match  # noqa: E402
from app.graders.sympy import grade_sympy  # noqa: E402

GRADERS: dict[str, Callable[..., GradeResult]] = {
    "choice": grade_choice,
    "match": grade_match,
    "order": grade_order,
    "categorize": grade_categorize,
    "exact": grade_exact,
    "cloze": grade_cloze,
    "numeric": grade_numeric,
    "sympy": grade_sympy,
    "flashcards": grade_flashcards,
    "rubric_llm": grade_rubric_llm,
    "speech_match": grade_speech_match,
    "code_tests": grade_code_tests,
}


def grade(
    grader: str, spec: Any, answer: Any, *, api_key: str | None = None, cache_key: str | None = None
) -> GradeResult:
    """Never raises: unknown grader or malformed spec/answer → SYNTAX_ERROR.

    ``api_key``/``cache_key`` only reach ``rubric_llm`` (FreeResponse, and ShortAnswer answers
    that ``exact`` missed when the spec has a rubric). Without a key it grades by key terms.
    """
    fn = GRADERS.get(grader)
    if fn is None or not isinstance(spec, dict) or not isinstance(answer, dict):
        return bad_answer()
    try:
        if grader == "rubric_llm":
            return fn(spec, answer, api_key=api_key, cache_key=cache_key)
        r = fn(spec, answer)
        if grader == "exact" and r.verdict != VERDICT_SYNTAX_ERROR and not r.is_success and spec.get("rubric") and api_key:
            return grade_rubric_llm(spec, answer, api_key=api_key, cache_key=cache_key)
        return r
    except Exception:  # noqa: BLE001 — garbage in must never 500
        return bad_answer()
