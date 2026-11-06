from app.graders import grade

S = {"total": 3, "solution": "...", "beta": True}


def test_trusts_client_counts_and_marks_client() -> None:
    r = grade("code_tests", S, {"passed": 3, "total": 3, "code": "def f(): ..."})
    assert r.is_success and r.decided_by == "CLIENT"
    r = grade("code_tests", S, {"passed": 1, "total": 3, "code": ""})
    assert r.verdict == "PARTIAL" and round(r.score, 2) == 0.33


def test_rejects_inconsistent_results() -> None:
    for bad in (
        {"passed": 4, "total": 3, "code": ""},
        {"passed": 3, "total": 4, "code": ""},  # total must match the item's tests
        {"passed": True, "total": 3, "code": ""},
        {"passed": 3, "total": 3},
        {"passed": 3, "total": 3, "code": "x" * 4000},
    ):
        assert grade("code_tests", S, bad).verdict == "SYNTAX_ERROR", bad
