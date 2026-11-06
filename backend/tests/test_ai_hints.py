"""Leak check + System 2 fallback when AI disabled."""

from __future__ import annotations

from unittest.mock import patch

from app.config import settings
from app.services.leak_check import hint_leaks_answer
from app.services.system2_hints import generate_socratic_hint, templated_hint


STEPS = [
    {"latex": "x + 5 = 12", "sympy": "Eq(x + 5, 12)", "operation": "GIVEN"},
    {"latex": "x = 7", "sympy": "Eq(x, 7)", "operation": "SUBTRACT"},
]


def test_leak_rejects_expected_latex():
    assert hint_leaks_answer("Try thinking about $x = 7$", ["x = 7", "Eq(x, 7)"]) is True


def test_leak_allows_safe_prompt():
    assert hint_leaks_answer("What inverse operation undoes the last change?", ["x = 7"]) is False


def test_ai_off_returns_template(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "ai_enabled", "false")
    with patch("app.services.system2_hints.httpx.Client") as Client:
        prompt, cost, source = generate_socratic_hint(
            locale="en",
            hint_level=1,
            statement_latex="x+5=12",
            expected_latex="x=7",
            submitted_latex="x=8",
            steps=STEPS,
        )
        Client.assert_not_called()
    assert source == "TEMPLATE"
    assert cost == 0.0
    assert prompt == templated_hint(1, "en")


def test_leak_fixture_set_size():
    """P3-lite: ship ~10 leak fixtures (not full 50 red-team)."""
    fixtures = [
        ("The answer is $x = 7$", True),
        ("Remember $x=7$", True),
        ("Check both sides of the equation.", False),
        ("Look at the constant term.", False),
        ("Did you distribute across every term?", False),
        ("What happens if you subtract five from both sides?", False),
        ("$$x = 7$$ is correct", True),
        ("\\(x=7\\) might help", True),
        ("Which sign looks flipped?", False),
        ("Isolate the variable carefully.", False),
    ]
    forbidden = ["x = 7", "Eq(x, 7)"]
    assert len(fixtures) == 10
    for text, expect_leak in fixtures:
        assert hint_leaks_answer(text, forbidden) is expect_leak, text
