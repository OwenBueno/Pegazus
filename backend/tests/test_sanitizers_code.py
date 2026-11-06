"""Code pack (Doc 11 MS-4.4): CodeBlock, PredictOutput, CodeExercise (beta until a browser pass)."""

from app.graders import grade
from app.services.component_catalog import sanitize_part, sanitize_visual


def test_code_block_bounds():
    assert sanitize_visual({"type": "CodeBlock", "props": {"language": "python", "code": "print(1)"}})
    assert sanitize_visual({"type": "CodeBlock", "props": {"language": "ruby", "code": "puts 1"}}) is None
    assert sanitize_visual({"type": "CodeBlock", "props": {"language": "python", "code": "x\n" * 61}}) is None


def test_predict_output_is_case_sensitive_exact():
    p = sanitize_part({"component": "PredictOutput", "props": {"language": "python", "code": "print('Hi')"},
                       "answer_spec": {"accepted": ["Hi"]}})
    assert "accepted" not in p["props"]
    assert grade("exact", p["answer_spec"], {"text": "Hi"}).is_success
    assert not grade("exact", p["answer_spec"], {"text": "hi"}).is_success


def test_code_exercise_keeps_solution_server_side():
    raw = {"component": "CodeExercise", "props": {
        "language": "python", "starter": "def add(a, b):\n    pass",
        "tests": [{"call": "add(2, 3)", "expect": "5"}], "solution": "def add(a, b):\n    return a + b"}}
    p = sanitize_part(raw)
    assert p["grader"] == "code_tests" and p["props"]["beta"] is True and "solution" not in p["props"]
    assert p["answer_spec"] == {"total": 1, "solution": "def add(a, b):\n    return a + b", "beta": True}
    no_ref = {**raw, "props": {**raw["props"], "solution": raw["props"]["starter"]}}
    assert isinstance(sanitize_part(no_ref), str)  # reference solution required


def test_code_exercise_rejects_tests_an_empty_stub_passes():
    base = {"language": "python", "starter": "def main():\n    pass", "solution": "def main():\n    print('hi')"}
    weak = sanitize_part({"component": "CodeExercise", "props": {**base, "tests": [{"call": "main()", "expect": "None"}]}})
    assert isinstance(weak, str) and "empty stub" in weak
    ok = sanitize_part({"component": "CodeExercise", "props": {
        **base, "tests": [{"call": "main()", "stdout": "hi\n"}, {"call": "main()", "expect": "None"}]}})
    assert ok["props"]["tests"] == [{"call": "main()", "stdout": "hi"}, {"call": "main()", "expect": "None"}]
