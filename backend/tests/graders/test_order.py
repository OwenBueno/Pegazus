from app.graders import grade

SPEC = {"order": [1, 0, 2]}


def test_order() -> None:
    assert grade("order", SPEC, {"order": [1, 0, 2]}).is_success
    swap = grade("order", SPEC, {"order": [0, 1, 2]})  # one inversion of three pairs
    assert swap.verdict == "PARTIAL" and abs(swap.score - 2 / 3) < 1e-9
    assert grade("order", SPEC, {"order": [2, 0, 1]}).score == 0  # fully reversed


def test_order_garbage() -> None:
    for answer in ({"order": [1, 0]}, {"order": [1, 1, 2]}, {"order": [1, 0, 9]}, {"order": None}):
        assert grade("order", SPEC, answer).verdict == "SYNTAX_ERROR"
