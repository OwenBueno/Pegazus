"""Outline proposal: repair once, then fail (no static fallback titles)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings
from app.services import path_draft as pd
from app.services.subject_profile import clamp_profile


def test_no_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    with pytest.raises(pd.OutlineError):
        pd.propose_outline(goal_text="Master simple quadratics", api_key="")


def test_invalid_twice_raises_after_repair_message():
    with patch.object(pd, "chat_json", return_value={"modules": ["only one"]}) as chat:
        with pytest.raises(pd.OutlineError):
            pd.propose_outline(goal_text="linear equations exam", api_key="k")
    assert chat.call_count == 2
    assert "previous answer was invalid" in chat.call_args_list[1].args[0][-1]["content"]


def test_repair_succeeds_and_prompt_follows_profile():
    good = {"modules": [{"title": f"Phrase set {i}"} for i in range(6)]}
    spanish = clamp_profile({"subject": "Spanish travel", "categories": ["core", "language"], "notation": "none"})
    with patch.object(pd, "chat_json", side_effect=[None, good]) as chat:
        mods = pd.propose_outline(goal_text="Order food in Spanish", api_key="k", profile=spanish)
    assert len(mods) == 6
    system = chat.call_args_list[0].args[0][0]["content"]
    assert "Spanish travel" in system and "math" not in system.lower()
