from app.graders import grade

SPEC = {"assign": [0, 1, 0, 1]}


def test_categorize() -> None:
    assert grade("categorize", SPEC, {"assign": {"0": 0, "1": 1, "2": 0, "3": 1}}).is_success
    half = grade("categorize", SPEC, {"assign": {"0": 0, "1": 1}})  # unassigned items count wrong
    assert half.verdict == "PARTIAL" and half.score == 0.5


def test_categorize_garbage() -> None:
    for answer in ({"assign": [0, 1]}, {"assign": {"a": 0}}, {"assign": {"0": "1"}}):
        assert grade("categorize", SPEC, answer).verdict == "SYNTAX_ERROR"
