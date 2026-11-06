"""Path improve / rebuild schema smoke."""

from pydantic import ValidationError

from app.schemas import PathImproveIn, PathRebuildIn


def test_improve_prompt_min_length():
    try:
        PathImproveIn(improvement_prompt="ab")
        assert False
    except ValidationError:
        pass
    assert PathImproveIn(improvement_prompt="add more inequalities").improvement_prompt


def test_rebuild_optional_goal():
    assert PathRebuildIn().goal_text is None
    assert PathRebuildIn(goal_text="linear equations for midterm").goal_text
