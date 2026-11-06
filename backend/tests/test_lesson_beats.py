"""Lesson beat assembly — AI-composed, flexible order."""

from app.services.lesson_beats import (
    normalize_genui_plan,
    _valid_sequence,
)
from app.services.session_genui import build_session_genui


def test_normalize_forces_step_editor_when_symbolic():
    plan = normalize_genui_plan({"widgets": ["FunctionPlotter"]})
    assert "SymbolicStepEditor" in plan["widgets"]
    assert plan["widgets"][0] == "SymbolicStepEditor"


def test_normalize_quickcheck_only_skips_step_editor():
    plan = normalize_genui_plan(
        {
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {
                        "prompt": "Which place?",
                        "choices": [
                            {"id": "a", "label": "tens"},
                            {"id": "b", "label": "hundreds"},
                        ],
                        "correctId": "b",
                        "correct_latex": "500",
                    },
                }
            ]
        }
    )
    types = [w if isinstance(w, str) else w["type"] for w in plan["widgets"]]
    assert "QuickCheck" in types
    assert "SymbolicStepEditor" not in types
    assert "VirtualMathKeyboard" not in types
    qc = next(w for w in plan["widgets"] if isinstance(w, dict))
    assert qc["props"]["correct_latex"] == "500"


def test_normalize_rejects_empty_quickcheck():
    plan = normalize_genui_plan(
        {
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {"prompt": "Broken", "choices": [], "correctId": "a"},
                }
            ]
        }
    )
    # Falls back to symbolic editor because incomplete QC was dropped
    types = [w if isinstance(w, str) else w["type"] for w in plan["widgets"]]
    assert "QuickCheck" not in types
    assert "SymbolicStepEditor" in types


def test_rejects_problem_first():
    assert not _valid_sequence(
        [
            {"type": "problem", "item_id": "x"},
            {"type": "concept", "body_md": "hi"},
        ]
    )


def test_normalize_typed_quickcheck_with_editor():
    plan = normalize_genui_plan(
        {
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {
                        "prompt": "What is 2+2?",
                        "choices": [
                            {"id": "a", "label": "3"},
                            {"id": "b", "label": "4"},
                        ],
                        "correctId": "b",
                    },
                },
                "FunctionPlotter",
            ]
        }
    )
    types = [w if isinstance(w, str) else w["type"] for w in plan["widgets"]]
    assert "QuickCheck" in types
    assert "SymbolicStepEditor" not in types  # selection-primary wins
    qc = next(w for w in plan["widgets"] if isinstance(w, dict) and w["type"] == "QuickCheck")
    assert qc["props"]["correctId"] == "b"


def test_session_merges_typed_quickcheck_without_forcing_editor():
    payload = build_session_genui(
        session_id="s",
        node_id="n",
        item_id="i",
        statement_latex="3542",
        steps=[{"latex": "3542"}, {"latex": "500"}],
        step_index=0,
        scaffold_level=2,
        genui_plan={
            "primary": "QuickCheck",
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {
                        "prompt": "Which digit is in the hundreds place?",
                        "choices": [
                            {"id": "a", "label": "3"},
                            {"id": "b", "label": "5"},
                        ],
                        "correctId": "b",
                        "correct_latex": "500",
                    },
                }
            ]
        },
    )
    types = [w["type"] for w in payload["widgets"]]
    assert "QuickCheck" in types
    assert "SymbolicStepEditor" not in types
    assert payload["answerMode"] == "selection"
    qc = next(w for w in payload["widgets"] if w["type"] == "QuickCheck")
    assert "correct_latex" not in qc["props"] and "correctId" not in qc["props"]  # graded server-side


def test_session_merges_typed_quickcheck():
    payload = build_session_genui(
        session_id="s",
        node_id="n",
        item_id="i",
        statement_latex="x=1",
        steps=[{"latex": "x=1"}],
        step_index=0,
        scaffold_level=2,
        genui_plan={
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {
                        "prompt": "Warm-up",
                        "choices": [
                            {"id": "a", "label": "1"},
                            {"id": "b", "label": "2"},
                        ],
                        "correctId": "a",
                    },
                },
                "SymbolicStepEditor",
            ]
        },
    )
    types = [w["type"] for w in payload["widgets"]]
    # A sympy item cannot grade a QuickCheck answer, so the side widget is dropped.
    assert "QuickCheck" not in types
    assert "SymbolicStepEditor" in types
    assert len(payload["widgets"]) <= 4


def test_genui_honors_plan_and_student_latex():
    payload = build_session_genui(
        session_id="s",
        node_id="n",
        item_id="i",
        statement_latex="x+1=2",
        steps=[{"latex": "x+1=2"}, {"latex": "x=1"}],
        step_index=1,
        scaffold_level=2,
        genui_plan={"widgets": ["SymbolicStepEditor", "VirtualMathKeyboard"]},
        student_latex_by_step={0: "x + 1 = 2"},
    )
    types = [w["type"] for w in payload["widgets"]]
    assert types[0] == "SymbolicStepEditor"
    assert "FadedWorkedExample" not in types
    assert payload["answerMode"] == "symbolic"
    steps = payload["widgets"][0]["props"]["initialSteps"]
    assert steps[0]["latexExpression"] == "x + 1 = 2"
    assert steps[1]["latexExpression"] == ""
