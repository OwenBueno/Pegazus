"""Unit tests for SymPy evaluator (Doc 04 §4.1)."""

from __future__ import annotations

from unittest.mock import patch

from app.workers import math_evaluator as me
from app.workers.math_evaluator import MAX_LATEX_LEN, evaluate_step_safe


def test_equivalent_linear_scaled_equation():
    # 2x = 6 ≡ x = 3
    result = evaluate_step_safe("x = 3", "Eq(2*x, 6)", use_pool=False)
    assert result["success"] is True
    assert result["is_equivalent"] is True
    assert result["error"] is None


def test_equivalent_seed_style_step():
    result = evaluate_step_safe("x = 7", "Eq(x, 7)", use_pool=False)
    assert result["success"] is True
    assert result["is_equivalent"] is True


def test_sign_error():
    result = evaluate_step_safe("x = -7", "Eq(x, 7)", use_pool=False)
    assert result["success"] is True
    assert result["is_equivalent"] is False
    assert result["sign_error"] is True


def test_calculation_slip_not_sign():
    result = evaluate_step_safe("x = 8", "Eq(x, 7)", use_pool=False)
    assert result["is_equivalent"] is False
    assert result["sign_error"] is False


def test_bare_number_not_eq_y_final():
    """Regression: EmptySet==EmptySet used to mark any constant CORRECT vs Eq(y, N)."""
    result = evaluate_step_safe("3", "Eq(y, 29)", use_pool=False)
    assert result["success"] is True
    assert result["is_equivalent"] is False


def test_bare_correct_value_vs_eq_y():
    result = evaluate_step_safe("29", "Eq(y, 29)", use_pool=False)
    assert result["is_equivalent"] is True
    result2 = evaluate_step_safe("y = 29", "Eq(y, 29)", use_pool=False)
    assert result2["is_equivalent"] is True


def test_wrong_intermediate_expression():
    result = evaluate_step_safe("1", "-3+2*(-4)**2", use_pool=False)
    assert result["is_equivalent"] is False
    result_ok = evaluate_step_safe("-3+2*16", "-3+2*(-4)**2", use_pool=False)
    assert result_ok["is_equivalent"] is True


def test_input_too_long():
    result = evaluate_step_safe("x" * (MAX_LATEX_LEN + 1), "Eq(x, 1)", use_pool=False)
    assert result["success"] is False
    assert result["error"] == "INPUT_TOO_LONG"


def test_timeout_path():
    class SlowFuture:
        def result(self, timeout=None):
            from concurrent.futures import TimeoutError as FutureTimeout

            raise FutureTimeout()

        def cancel(self):
            return True

    class FakePool:
        def submit(self, *args, **kwargs):
            return SlowFuture()

    with patch.object(me, "_get_pool", return_value=FakePool()):
        result = evaluate_step_safe("x = 1", "Eq(x, 1)", use_pool=True)
    assert result["success"] is False
    assert result["error"] == "EVALUATION_TIMEOUT"


def test_parse_error():
    result = evaluate_step_safe("\\\\notavalid{{{{", "Eq(x, 1)", use_pool=False)
    assert result["success"] is False
    assert result["error"] and "PARSE_ERROR" in result["error"]
