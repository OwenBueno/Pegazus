"""Prefetch, rich beats, and JEV GenUI layout heuristics."""

from app.pipeline.materialize_node import (
    is_materialize_inflight,
    materialize_buffer_key,
    node_content_incomplete,
)
from app.services.jev_genui import (
    choose_primary_widget,
    heuristic_primary_widget,
    reorder_plan_for_primary,
)
from app.services.session_genui import build_session_genui


def test_heuristic_scaffold_1_prefers_faded():
    w = heuristic_primary_widget(
        node_title="Linear equations",
        statement_latex="x+1=2",
        scaffold_level=1,
        genui_plan=None,
    )
    assert w == "FadedWorkedExample"


def test_heuristic_place_value_quickcheck_when_props_valid():
    plan = {
        "widgets": [
            {
                "type": "QuickCheck",
                "props": {
                    "prompt": "Which?",
                    "choices": [{"id": "a", "label": "1"}, {"id": "b", "label": "2"}],
                    "correctId": "a",
                },
            }
        ]
    }
    w = heuristic_primary_widget(
        node_title="Place Value",
        statement_latex="3542",
        scaffold_level=2,
        genui_plan=plan,
    )
    assert w == "QuickCheck"


def test_choose_primary_without_key_uses_heuristic():
    w = choose_primary_widget(
        node_title="Algebra",
        statement_latex="x=1",
        scaffold_level=3,
        genui_plan={"widgets": ["SymbolicStepEditor"]},
        api_key="",
    )
    assert w == "SymbolicStepEditor"


def test_reorder_drops_symbolic_for_selection_primary():
    entries = [
        {"type": "SymbolicStepEditor", "props": {}},
        {
            "type": "QuickCheck",
            "props": {
                "choices": [{"id": "a", "label": "1"}, {"id": "b", "label": "2"}],
                "correctId": "a",
            },
        },
    ]
    out = reorder_plan_for_primary(entries, "QuickCheck")
    types = [e["type"] for e in out]
    assert types[0] == "QuickCheck"
    assert "SymbolicStepEditor" not in types


def test_build_session_respects_jev_disabled_via_heuristic():
    payload = build_session_genui(
        session_id="s",
        node_id="n",
        item_id="i",
        statement_latex="x+1=2",
        steps=[{"latex": "x+1=2"}, {"latex": "x=1"}],
        step_index=0,
        scaffold_level=1,
        node_title="Equations",
        use_jev_layout=True,
        api_key="",
    )
    types = [w["type"] for w in payload["widgets"]]
    assert "FadedWorkedExample" in types or "SymbolicStepEditor" in types


def test_materialize_buffer_key_stable():
    from uuid import UUID

    p = UUID("00000000-0000-0000-0000-000000000001")
    n = UUID("00000000-0000-0000-0000-000000000002")
    assert materialize_buffer_key(p, n) == f"mat:{p}:{n}"
    assert is_materialize_inflight(p, n) is False
