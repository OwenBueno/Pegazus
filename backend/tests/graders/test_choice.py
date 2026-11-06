from app.graders import grade
from app.services.rule_engine import _fsrs_grade

SPEC = {"correctIds": ["a"], "explanation": "undo +1"}


def test_choice() -> None:
    ok = grade("choice", SPEC, {"ids": ["a"]})
    assert ok.is_success and ok.score == 1 and ok.verdict == "CORRECT_OPTIMAL" and ok.feedback == "undo +1"
    bad = grade("choice", SPEC, {"ids": ["b"]})
    assert not bad.is_success and bad.verdict == "INCORRECT" and bad.feedback is None
    assert not grade("choice", SPEC, {"ids": ["a", "b"]}).is_success  # picking everything is wrong
    assert grade("choice", {"correctIds": ["a", "c"]}, {"ids": ["c", "a"]}).is_success


def test_garbage_never_raises() -> None:
    for answer in (None, {}, {"ids": "a"}, {"ids": []}, {"ids": [1]}, {"ids": ["x"] * 99}):
        assert grade("choice", SPEC, answer).verdict == "SYNTAX_ERROR"
    assert grade("nope", SPEC, {"ids": ["a"]}).verdict == "SYNTAX_ERROR"
    assert grade("choice", {}, {"ids": ["a"]}).verdict == "SYNTAX_ERROR"  # malformed spec


def test_partial_score_is_hard() -> None:
    assert _fsrs_grade(False, 0, 1000, score=0.5) == 2
    assert _fsrs_grade(False, 3, 1000, score=0.5) == 1
    assert _fsrs_grade(False, 0, 1000, score=0.0) == 1
    assert _fsrs_grade(True, 0, 1000) == 4
