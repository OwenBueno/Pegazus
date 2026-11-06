"""Unit tests for Jev client: timeout / low confidence → None (RULES path)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.config import settings
from app.services import jev_client as jc


def _eval_ok() -> dict:
    return {"success": True, "is_equivalent": False, "sign_error": True, "error": None}


def _base_kwargs(**over):
    kw = dict(
        statement_latex="x+5=12",
        node_title="One-step",
        expected_latex="x=7",
        expected_operation="SUBTRACT",
        submitted_latex="x=-7",
        eval_result=_eval_ok(),
        attempt_number=1,
        scaffold_level=2,
        latency_ms=2000,
        structure_ok=True,
    )
    kw.update(over)
    return kw


def test_ai_off_skips_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(settings, "ai_enabled", "false")
    with patch("app.services.jev_client.httpx.Client") as Client:
        assert jc.decide_with_jev(**_base_kwargs()) is None
        Client.assert_not_called()


def test_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_enabled", "true")
    jc.reset_circuit_breaker_for_tests()

    mock = MagicMock()
    mock.post.side_effect = httpx.TimeoutException("slow")
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)

    with patch("app.services.jev_client.httpx.Client", return_value=mock):
        assert jc.decide_with_jev(**_base_kwargs()) is None


def test_low_confidence_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_enabled", "true")
    jc.reset_circuit_breaker_for_tests()

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "answers": {
            "evaluation_verdict": {
                "type": "choice",
                "value": "SIGN_ERROR",
                "confidence": 0.40,
            },
            "recommended_fsrs_grade": {
                "type": "score",
                "value": 0.5,
                "confidence": 0.90,
            },
        },
        "usage": {"cost": 0.0001},
    }
    mock = MagicMock()
    mock.post.return_value = resp

    result = jc.decide_with_jev(**_base_kwargs(), client=mock)
    assert result is None


def test_high_confidence_returns_jev(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_enabled", "true")
    jc.reset_circuit_breaker_for_tests()

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "answers": {
            "evaluation_verdict": {
                "type": "choice",
                "value": "SIGN_ERROR",
                "confidence": 0.85,
            },
            "recommended_fsrs_grade": {
                "type": "score",
                "value": 0.2,
                "confidence": 0.80,
            },
        },
        "usage": {"cost": 0.0002},
    }
    mock = MagicMock()
    mock.post.return_value = resp

    result = jc.decide_with_jev(**_base_kwargs(), client=mock)
    assert result is not None
    assert result.verdict == "SIGN_ERROR"
    assert result.fsrs_grade == 1  # round(0.2)+1
    assert result.cost_usd == 0.0002


def test_clamp_rejects_correct_when_not_equivalent():
    assert (
        jc.clamp_jev_verdict("CORRECT_OPTIMAL", is_equivalent=False) is None
    )
    assert jc.clamp_jev_verdict("CALCULATION_SLIP", is_equivalent=False) == "CALCULATION_SLIP"
    assert jc.clamp_jev_verdict("CORRECT_SUBOPTIMAL", is_equivalent=True) == "CORRECT_SUBOPTIMAL"
    assert jc.clamp_jev_verdict("SIGN_ERROR", is_equivalent=True) is None


def test_jev_cannot_upgrade_failed_equivalence(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_enabled", "true")
    jc.reset_circuit_breaker_for_tests()

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "answers": {
            "evaluation_verdict": {
                "type": "choice",
                "value": "CORRECT_OPTIMAL",
                "confidence": 0.99,
            },
            "recommended_fsrs_grade": {
                "type": "score",
                "value": 0.9,
                "confidence": 0.90,
            },
        },
        "usage": {"cost": 0.0001},
    }
    mock = MagicMock()
    mock.post.return_value = resp

    result = jc.decide_with_jev(
        **_base_kwargs(
            eval_result={
                "success": True,
                "is_equivalent": False,
                "sign_error": False,
                "error": None,
            }
        ),
        client=mock,
    )
    assert result is None
