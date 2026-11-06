from functools import partial

import app.graders.sympy as g
from app.graders import grade
from app.workers.math_evaluator import evaluate_step_safe

STEP = {"latex": "x = 5", "sympy": "Eq(x, 5)", "operation": "DIVIDE"}


def test_sympy_grader(monkeypatch) -> None:
    monkeypatch.setattr(g, "evaluate_step_safe", partial(evaluate_step_safe, use_pool=False))
    ok = grade("sympy", STEP, {"latex": "x=5"})
    assert ok.is_success and ok.verdict == "CORRECT_OPTIMAL" and ok.extra["eval_result"]["is_equivalent"]
    assert grade("sympy", STEP, {"latex": "x=-5"}).verdict == "SIGN_ERROR"
    assert grade("sympy", STEP, {"latex": "x=(("}).verdict == "SYNTAX_ERROR"
    assert grade("sympy", STEP, {"ids": ["a"]}).verdict == "SYNTAX_ERROR"
