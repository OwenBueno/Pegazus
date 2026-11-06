"""evaluate-step / offline sync / diagnostic accept only {part_index, answer} (MS-5.3)."""

from __future__ import annotations

from functools import partial
from uuid import uuid4

import pytest
from pydantic import ValidationError

import app.graders.sympy as gs
from app.api_session import _grade_attempt, _grade_part
from app.graders.legacy import legacy_parts
from app.schemas import DiagnosticAnswerIn, EvaluateStepIn, OfflineAttemptIn
from app.workers.math_evaluator import evaluate_step_safe

QC_PLAN = {"primary": "QuickCheck", "widgets": [{"type": "QuickCheck", "props": {
    "prompt": "Solve", "choices": [{"id": "a", "label": "x=5"}, {"id": "b", "label": "x=6"}], "correctId": "a"}}]}
STEPS = [{"latex": "x+1=6", "sympy": "Eq(x+1, 6)"}, {"latex": "x=5", "sympy": "Eq(x, 5)"}]


def test_legacy_body_is_rejected() -> None:
    new = EvaluateStepIn(item_id=uuid4(), part_index=0, answer={"ids": ["b"]})
    assert new.answer == {"ids": ["b"]} and not hasattr(new, "submitted_latex")
    for model, extra in ((EvaluateStepIn, {}), (OfflineAttemptIn, {"client_attempt_id": uuid4()})):
        with pytest.raises(ValidationError):
            model(item_id=uuid4(), step_index=1, submitted_latex="x=5", **extra)
    off = OfflineAttemptIn(client_attempt_id=uuid4(), item_id=uuid4(), part_index=0, answer={"latex": "x=5"})
    assert off.part_index == 0 and off.answer == {"latex": "x=5"}


def test_contract_rejects_missing_and_oversized() -> None:
    with pytest.raises(ValidationError):
        EvaluateStepIn(item_id=uuid4())
    with pytest.raises(ValidationError):
        EvaluateStepIn(item_id=uuid4(), part_index=0)
    with pytest.raises(ValidationError):
        EvaluateStepIn(item_id=uuid4(), part_index=0, answer={"text": "x" * 5000})


def test_diagnostic_answer_contract() -> None:
    ids = dict(node_id=uuid4(), item_id=uuid4(), probe_index=1)
    assert DiagnosticAnswerIn(**ids, answer={"ids": ["a"]}).answer == {"ids": ["a"]}
    for bad in ({}, {"submitted_latex": "x=5"}, {"answer": {"text": "x" * 5000}}):
        with pytest.raises(ValidationError):
            DiagnosticAnswerIn(**ids, **bad)


def test_grade_part_per_grader() -> None:
    parts, grader = legacy_parts(STEPS[-1:], QC_PLAN, uuid4())
    assert grader == "choice"
    assert _grade_part(parts, 0, {"ids": ["a"]}).is_success
    assert _grade_part(parts, 0, {"ids": ["b"]}).verdict == "INCORRECT"
    assert _grade_part(parts, 3, {"ids": ["a"]}).verdict == "SYNTAX_ERROR"  # no such part
    match = [{"grader": "match", "answer_spec": {"pairs": [[0, 1], [1, 0]]}}]
    assert _grade_part(match, 0, {"pairs": [[0, 1], [1, 0]]}).is_success


def test_grade_attempt_selection_and_sympy(monkeypatch) -> None:
    monkeypatch.setattr(gs, "evaluate_step_safe", partial(evaluate_step_safe, use_pool=False))
    import app.api_session as api

    monkeypatch.setattr(api, "evaluate_step_safe", partial(evaluate_step_safe, use_pool=False))
    parts, _ = legacy_parts(STEPS[-1:], QC_PLAN, uuid4())
    wrong = _grade_attempt(STEPS[-1:], parts, 0, {"ids": ["b"]}, hint_level=0, latency_ms=1000)
    assert wrong.is_final and not wrong.decision.is_success and wrong.decision.fsrs_grade == 1
    sym, _ = legacy_parts(STEPS, None, uuid4())
    early = _grade_attempt(STEPS, sym, 0, {"latex": "x = 5"}, hint_level=0, latency_ms=1000)
    assert early.index == 1 and early.is_final and early.decision.is_success  # final-answer shortcut
    bad = _grade_attempt(STEPS, sym, 0, {"ids": ["a"]}, hint_level=0, latency_ms=1000)
    assert bad.decision.verdict == "SYNTAX_ERROR" and bad.eval_result is not None
