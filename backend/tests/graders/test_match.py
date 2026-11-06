from app.graders import grade

SPEC = {"pairs": [[0, 2], [1, 0], [2, 1]]}


def test_match() -> None:
    assert grade("match", SPEC, {"pairs": [[2, 1], [0, 2], [1, 0]]}).is_success  # order-free
    part = grade("match", SPEC, {"pairs": [[0, 2], [1, 1], [2, 0]]})
    assert not part.is_success and part.verdict == "PARTIAL" and abs(part.score - 1 / 3) < 1e-9


def test_match_rejects_cheats_and_garbage() -> None:
    every = [[left, right] for left in range(3) for right in range(3)]
    assert grade("match", SPEC, {"pairs": every}).verdict == "SYNTAX_ERROR"  # not one-to-one
    for answer in ({"pairs": [[0, "2"]]}, {"pairs": [[0, True]]}, {"pairs": [[-1, 0]]}, {"pairs": "x"}):
        assert grade("match", SPEC, answer).verdict == "SYNTAX_ERROR"
