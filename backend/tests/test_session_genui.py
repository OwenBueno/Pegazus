"""Server session GenUI builder + scaffold band."""

from app.services.session_genui import build_session_genui, update_scaffold_from_band


def test_scaffold_band_bumps_up_on_high_accuracy():
    assert update_scaffold_from_band(current=1, recent_success_rate=0.9) == 2
    assert update_scaffold_from_band(current=2, recent_success_rate=0.85) == 3
    assert update_scaffold_from_band(current=3, recent_success_rate=1.0) == 3


def test_scaffold_band_drops_on_overload():
    assert update_scaffold_from_band(current=3, recent_success_rate=0.2) == 2
    assert update_scaffold_from_band(current=2, recent_success_rate=0.0) == 1
    assert update_scaffold_from_band(current=1, recent_success_rate=0.1) == 1


def test_build_includes_faded_at_lambda_1():
    payload = build_session_genui(
        session_id="s1",
        node_id="n1",
        item_id="i1",
        statement_latex=r"2x+1=5",
        steps=[
            {"latex": r"2x=4", "gap_latex": r"2x=\square", "justification": "subtract"},
            {"latex": r"x=2"},
        ],
        step_index=0,
        scaffold_level=1,
    )
    types = [w["type"] for w in payload["widgets"]]
    assert "FadedWorkedExample" in types
    assert "SymbolicStepEditor" not in types
    assert payload["scaffoldLevel"] == 1
    assert payload["answerMode"] == "symbolic"
    faded = next(w for w in payload["widgets"] if w["type"] == "FadedWorkedExample")
    assert faded["props"].get("gapLatex") == r"2x=\square"


def test_build_faded_at_lambda_2_no_dual_editor():
    payload = build_session_genui(
        session_id="s1",
        node_id="n1",
        item_id="i1",
        statement_latex=r"2x=4",
        steps=[{"latex": r"2x=4"}, {"latex": r"x=2"}],
        step_index=0,
        scaffold_level=2,
        use_jev_layout=False,
    )
    types = [w["type"] for w in payload["widgets"]]
    assert "FadedWorkedExample" in types
    assert "SymbolicStepEditor" not in types


def test_fail_marks_active_invalid():
    payload = build_session_genui(
        session_id="s1",
        node_id="n1",
        item_id="i1",
        statement_latex="x=1",
        steps=[{"latex": "x=1"}],
        step_index=0,
        scaffold_level=3,
        active_status="INVALID",
        use_jev_layout=False,
    )
    editor = next(w for w in payload["widgets"] if w["type"] == "SymbolicStepEditor")
    steps = editor["props"]["initialSteps"]
    assert steps[0]["status"] == "INVALID"


def test_generic_item_renders_only_its_part():
    part = {"component": "Cloze", "grader": "cloze", "props": {"segments": ["Plants make ", "."]},
            "answer_spec": {"answers": [["glucose"]]}}
    payload = build_session_genui(
        session_id="s1", node_id="n1", item_id="i1", statement_latex="", steps=[], step_index=0,
        scaffold_level=1, genui_plan={"primary": "Cloze", "widgets": ["Cloze"]}, parts=[part],
    )
    assert payload["answerMode"] == "selection"
    assert [w["type"] for w in payload["widgets"]] == ["Cloze"]  # no step editor / math keyboard
    assert "glucose" not in str(payload)
