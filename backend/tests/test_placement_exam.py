"""Goal-based placement exam: model questions on graders, HMAC-signed keys, no fallback bank."""

from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest

from app.services import placement_exam as pe
from app.services.placement_exam import (
    PlacementError,
    clean_latex,
    clean_question,
    generate_placement_exam,
    grade_placement_exam,
)
from app.services.subject_profile import clamp_profile

SPANISH = clamp_profile(
    {"subject": "Spanish", "categories": ["core", "language"], "notation": "none", "answer_modes": ["choice", "numeric"]}
)

_SPANISH_QS = {
    "questions": [
        {"prompt_md": "Translate *hello*", "grader": "exact", "accepted": ["hola"], "difficulty": 1,
         "skill_hint": "greetings"},
        {"prompt_md": "Which means *thank you*?", "grader": "choice", "difficulty": 2, "skill_hint": "courtesy",
         "choices": [{"id": "a", "label": "gracias"}, {"id": "b", "label": "adiós"}], "correct_id": "a"},
        {"prompt_md": "How many is *doce*?", "grader": "numeric", "value": 12, "difficulty": 3,
         "skill_hint": "numbers"},
        {"prompt_md": "Bad", "grader": "sympy", "statement_latex": "x=1", "target_sympy": "Eq(x,1)"},
    ]
}


def _mathq(**over):
    row = {"prompt_md": "Solve for x", "grader": "sympy", "statement_latex": "x + 5 = 12",
           "target_sympy": "Eq(x, 7)", "target_latex": "x = 7", "skill_hint": "one-step"}
    q, err = clean_question({**row, **over}, ["sympy", "choice", "numeric"], math_mode=True)
    assert q, err
    return q


def test_clean_latex_strips_delimiters():
    assert clean_latex(r"Solve for \(x\): \(x + 7 = 12\)") == "x + 7 = 12"
    assert clean_latex(r"$x^2=4$") == "x^2=4"
    assert "find smaller" not in clean_latex(r"x^{2}=0 (find smaller root)")


def test_no_key_and_bad_model_output_raise():
    with pytest.raises(PlacementError):
        generate_placement_exam(goal_text="linear equations", api_key="")
    with patch.object(pe, "chat_json", return_value={"questions": []}) as chat:
        with pytest.raises(PlacementError):
            generate_placement_exam(goal_text="linear equations", api_key="k")
    assert chat.call_count == 2


def test_non_math_exam_hides_keys_and_grades_each_grader():
    with patch.object(pe, "chat_json", return_value=_SPANISH_QS) as chat:
        qs = generate_placement_exam(goal_text="Spanish travel", api_key="k", profile=SPANISH)
    system = chat.call_args.args[0][0]["content"]
    assert "sympy" not in system and "LaTeX" in system  # "no LaTeX" rule only
    assert [q["parts"][0]["grader"] for q in qs] == ["exact", "choice", "numeric"]  # sympy rejected
    assert all("answer_spec" not in q["parts"][0] and "hola" not in json.dumps(q["parts"]) for q in qs)
    answers = [
        {"id": qs[0]["id"], "answer": {"text": "Hola!"}},
        {"id": qs[1]["id"], "answer": {"ids": ["b"]}},
        {"id": qs[2]["id"], "answer": {"text": "12"}},
    ]
    g = grade_placement_exam(questions=qs, answers=answers)
    assert (g["correct_count"], g["total"]) == (2, 3)
    assert g["weak_skills"] == ["courtesy"]


def test_tampered_or_swapped_key_is_rejected():
    q1, q2 = _mathq(), _mathq(target_sympy="Eq(x, 1)", target_latex="x = 1")
    body, _, mac = q1["key"].partition(".")
    data = json.loads(base64.urlsafe_b64decode(body))
    data["spec"]["sympy"] = "Eq(x, 1)"
    forged = base64.urlsafe_b64encode(json.dumps(data, sort_keys=True).encode()).decode()
    for key in (f"{forged}.{mac}", q2["key"]):
        with pytest.raises(ValueError):
            grade_placement_exam(questions=[{**q1, "key": key}], answers=[{"id": q1["id"], "answer": {"latex": "x=1"}}])


def test_sympy_grade_rejects_garbage_and_restatement():
    q = _mathq()
    for sub in ["", "whatever", "asdf", "1", "x=1", "x+5=12", "x + 5 = 12"]:
        g = grade_placement_exam(questions=[q], answers=[{"id": q["id"], "answer": {"latex": sub}}])
        assert g["correct_count"] == 0, f"should miss for {sub!r}"
    for sub in ["x = 7", "x=7", "7"]:
        g = grade_placement_exam(questions=[q], answers=[{"id": q["id"], "answer": {"latex": sub}}])
        assert g["correct_count"] == 1, f"should accept {sub!r}"
