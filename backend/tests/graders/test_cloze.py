from app.graders import grade

SPEC = {"answers": [["100", "100°C"], ["boils"]]}


def test_cloze() -> None:
    assert grade("cloze", SPEC, {"blanks": ["100°C", "Boils"]}).is_success
    half = grade("cloze", SPEC, {"blanks": ["100"]})  # second blank missing
    assert half.verdict == "PARTIAL" and half.score == 0.5


def test_cloze_garbage() -> None:
    assert grade("cloze", SPEC, {"blanks": "100"}).verdict == "SYNTAX_ERROR"
    assert grade("cloze", SPEC, {"blanks": [100, "boils"]}).verdict == "SYNTAX_ERROR"
