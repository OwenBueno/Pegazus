"""Robustness helpers: resume, lesson_ready, scrub predicate."""

from app.pipeline.materialize_node import lesson_ready
from scripts.scrub_identical_eq_items import _identical_eq_bank


def test_lesson_ready_requires_items_and_beats():
    assert lesson_ready(item_count=5, beats=[{}, {}, {}, {}]) is True
    assert lesson_ready(item_count=4, beats=[{}, {}, {}, {}]) is False
    assert lesson_ready(item_count=5, beats=[{}, {}, {}]) is False
    assert lesson_ready(item_count=5, beats=None) is False


def test_identical_eq_bank_detects_all_same():
    assert _identical_eq_bank(
        [
            {"latex": "29", "sympy": "Eq(y, 29)"},
            {"latex": "29", "sympy": "Eq(y, 29)"},
        ]
    )
    assert not _identical_eq_bank(
        [
            {"latex": "a", "sympy": "-3+2*16"},
            {"latex": "29", "sympy": "Eq(y, 29)"},
        ]
    )
