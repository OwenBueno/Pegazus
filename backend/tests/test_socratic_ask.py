"""Quick Socratic unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.config import settings
from app.services import socratic_ask as sa
from app.services.jev_intent import classify_intent


def test_heuristic_off_topic(monkeypatch):
    monkeypatch.setattr(settings, "ai_enabled", "false")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    r = classify_intent(user_query="What is the weather today?")
    assert r.intent == "OFF_TOPIC"


def test_ask_refuses_off_topic_no_system2(monkeypatch):
    monkeypatch.setattr(settings, "ai_enabled", "false")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    with patch("app.services.socratic_ask._ask_system2") as mock_s2:
        result = sa.run_socratic_ask(
            query="Tell me a joke about cats",
            locale="en",
            exchange_index=1,
            session_id="11111111-1111-1111-1111-111111111111",
        )
        mock_s2.assert_not_called()
    assert result.refused is True
    assert result.intent == "OFF_TOPIC"


def test_ask_ai_off_template(monkeypatch):
    monkeypatch.setattr(settings, "ai_enabled", "false")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    with patch("app.services.socratic_ask.httpx.Client") as Client:
        result = sa.run_socratic_ask(
            query="Why do we subtract from both sides of an equation?",
            locale="en",
            exchange_index=1,
            session_id="11111111-1111-1111-1111-111111111111",
        )
        Client.assert_not_called()
    assert result.refused is False
    assert result.socratic_prompt
    assert "widgets" in result.genui


def test_exchange_index_validated_by_schema():
    from pydantic import ValidationError

    from app.api_socratic import SocraticAskIn

    try:
        SocraticAskIn(query="why x", exchange_index=4)
        assert False, "should reject"
    except ValidationError:
        pass
