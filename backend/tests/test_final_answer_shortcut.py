"""Final answer typed early finishes the item; valid intermediate lines do not."""

from __future__ import annotations

from functools import partial

import app.graders.sympy as sg
from app.workers.math_evaluator import evaluate_step_safe

FINAL = {"latex": "x = 5", "sympy": "Eq(x, 5)"}


def test_final_answer_shortcut(monkeypatch) -> None:
    monkeypatch.setattr(sg, "evaluate_step_safe", partial(evaluate_step_safe, use_pool=False))
    assert sg.final_answer_shortcut("x = 5", FINAL) is not None
    assert sg.final_answer_shortcut("5 = x", FINAL) is not None
    assert sg.final_answer_shortcut("5", FINAL) is not None
    # Equivalent by solution set, but still an intermediate line.
    assert sg.final_answer_shortcut("x + 4 - 4 = 9 - 4", FINAL) is None
    assert sg.final_answer_shortcut("x = 9 - 4", FINAL) is None
    assert sg.final_answer_shortcut("x = 6", FINAL) is None
    frac = {"latex": "x=-\\frac{3}{2}", "sympy": "Eq(x, -3/2)"}
    assert sg.final_answer_shortcut("x=-\\frac{3}{2}", frac) is not None
    assert sg.final_answer_shortcut("x = -1.5", frac) is not None
    assert sg.final_answer_shortcut("2x=-3", frac) is None
    # Expression items only shortcut on the literal last line.
    expr = {"latex": "5x", "sympy": "5*x"}
    assert sg.final_answer_shortcut("5x", expr) is not None
    assert sg.final_answer_shortcut("3x + 2x", expr) is None
