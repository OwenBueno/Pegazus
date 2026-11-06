"""No answer key reaches the client: session GenUI, item parts, lesson beats (MS-1.10)."""

from __future__ import annotations

import json
import re
from uuid import uuid4

from app.graders.legacy import legacy_parts
from app.schemas import PathNodeOut, SessionItemOut, SessionNodeOut
from app.services.component_catalog import public_props
from app.services.session_genui import build_session_genui

KEYS = re.compile(r'answer_spec|correctIds?|"target"|correct_latex|correctLatex|"tolerance"|explanation|"pairs"')
FINAL = [{"latex": "x=5", "sympy": "Eq(x, 5)"}]
PLANS = [
    {"primary": "QuickCheck", "widgets": [{"type": "QuickCheck", "props": {
        "prompt": "Solve", "choices": [{"id": "a", "label": "x=5"}, {"id": "b", "label": "x=6"}],
        "correctId": "a", "correct_latex": "x=5", "explanation": "undo +1", "labelsAreLatex": True}}]},
    {"primary": "NumberLine", "widgets": [{"type": "NumberLine", "props": {
        "min": 0, "max": 10, "target": 5, "tolerance": 0.5, "correct_latex": "5"}}]},
    {"primary": "MatchPairs", "widgets": [{"type": "MatchPairs", "props": {"pairs": [
        {"id": "p1", "left": "1/2", "right": "0.5"}, {"id": "p2", "left": "1/4", "right": "0.25"},
        {"id": "p3", "left": "3/4", "right": "0.75"}], "correct_latex": "0.5"}}]},
]


def test_selection_payloads_carry_no_keys() -> None:
    for plan in PLANS:
        iid = uuid4()
        parts, _ = legacy_parts(FINAL, plan, iid)
        genui = build_session_genui(
            session_id="s", node_id="n", item_id=str(iid), statement_latex="x+1=6", steps=FINAL,
            step_index=0, scaffold_level=2, genui_plan=plan, parts=parts, use_jev_layout=False,
        )
        assert genui["answerMode"] == "selection" and genui["widgets"][0]["type"] == plan["primary"]
        item = SessionItemOut(id=iid, statement_latex="", steps=[], step_count=1,
                              parts=[public_props(p) for p in parts])
        blob = json.dumps(genui) + item.model_dump_json()
        assert not KEYS.search(blob), (plan["primary"], KEYS.search(blob))


CLOZE_PARTS = [
    {"component": "Cloze", "props": {"text": "Run [[python3]] [[hello.py]]"}},
    {"component": "WorkedExample", "props": {"steps": [{"text": "Call [[print]]"}, {"text": "Pass [[hello]]"}]}},
]


def test_cloze_answers_never_ship() -> None:
    from app.api_paths import DiagnosticProbeOut
    from app.api_session import _load_parts, hide_cloze
    from app.pipeline.item_gen import verify_generic_item

    for raw in CLOZE_PARTS:
        text = raw["props"].get("text") or "Call [[print]] Pass [[hello]]"
        fresh, why = verify_generic_item({"prompt_md": f"Fill in: {text}", "parts": [raw]}, [raw["component"]])
        assert fresh, why
        # A row saved before write-time masking: the [[answer]] text sits in prompt_md and props.prompt.
        legacy = {**fresh, "id": uuid4(), "prompt_md": f"Fill in: {text}",
                  "parts": [{**fresh["parts"][0], "props": {**fresh["parts"][0]["props"], "prompt": text}}]}
        for row in (fresh, legacy):
            parts = _load_parts(row)
            genui = build_session_genui(
                session_id="s", node_id="n", item_id=str(uuid4()), statement_latex="", steps=[],
                step_index=0, scaffold_level=2, genui_plan=None, parts=parts, use_jev_layout=False,
            )
            item = SessionItemOut(id=uuid4(), statement_latex="", steps=[], step_count=1,
                                  prompt=hide_cloze(parts, row.get("prompt")),
                                  prompt_md=hide_cloze(parts, row["prompt_md"]), parts=[public_props(p) for p in parts])
            probe = DiagnosticProbeOut(prompt_md=hide_cloze(parts, row["prompt_md"]),
                                       parts=[public_props(p) for p in parts])
            blob = json.dumps(genui) + item.model_dump_json() + probe.model_dump_json()
            assert "[[" not in blob and "python3" not in blob and "print" not in blob, blob
            assert parts[0]["answer_spec"]["answers"]  # grading key intact server-side


def test_code_brackets_survive() -> None:
    from app.api_session import hide_cloze

    parts = [{"grader": "exact", "props": {"code": "print([[1, 2]])"}}]
    assert hide_cloze(parts, "x = [[1, 2]]") == "x = [[1, 2]]"


def test_lesson_beats_are_stripped() -> None:
    beats = [{"type": "intro", "body_md": "Hi"}] + [
        {"type": "problem", "item_id": "x", "genui_plan": plan} for plan in PLANS
    ]
    for out in (
        SessionNodeOut(id=uuid4(), slug="s", title="t", lesson_beats=beats),
        PathNodeOut(node_id=uuid4(), slug="s", title="t", sequence_index=0, is_draft=False,
                    p_mastery=0, label="unknown", lesson_beats=beats),
    ):
        blob = out.model_dump_json()
        assert not KEYS.search(blob), KEYS.search(blob)
        assert out.lesson_beats[1]["genui_plan"]["widgets"] == ["QuickCheck"]
