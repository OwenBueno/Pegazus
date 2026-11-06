"""ProblemStatement prose vs math heuristics."""

from app.schemas import SessionItemOut
from uuid import uuid4


def test_session_item_out_accepts_prompt():
    item = SessionItemOut(
        id=uuid4(),
        statement_latex="3,542",
        prompt="In the number 3,542, which digit is in the hundreds place?",
        steps=[],
        step_count=0,
    )
    assert item.prompt
    assert item.statement_latex == "3,542"


def test_session_item_out_prompt_optional():
    item = SessionItemOut(
        id=uuid4(),
        statement_latex="x+1=2",
        steps=[],
        step_count=0,
    )
    assert item.prompt is None
