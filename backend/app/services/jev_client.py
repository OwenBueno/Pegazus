"""Jev Decisions API client (Doc 05 §2) with confidence policy + circuit breaker."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.services.rule_engine import LATENCY_FAST_MS, LATENCY_SLOW_MS

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

_CORRECT = {"CORRECT_OPTIMAL", "CORRECT_SUBOPTIMAL"}
_INCORRECT = {
    "SYNTAX_ERROR",
    "SIGN_ERROR",
    "DISTRIBUTION_SLIP",
    "CALCULATION_SLIP",
    "STRUCTURAL_MISCONCEPTION",
    "PREREQUISITE_FAILURE",
    "TIMEOUT",
}


def clamp_jev_verdict(verdict: str, *, is_equivalent: bool) -> str | None:
    """
    JEV may refine within the SymPy bucket only:
    - equivalent → OPTIMAL / SUBOPTIMAL
    - not equivalent → non-success verdicts
    Returns None if JEV's choice is illegal for the sympy result.
    """
    v = (verdict or "").strip()
    if not v or v == "none":
        return None
    if is_equivalent:
        return v if v in _CORRECT else None
    return v if v in _INCORRECT else None


@dataclass
class JevDecision:
    verdict: str
    fsrs_grade: int | None
    cost_usd: float
    raw: dict[str, Any]


class _CircuitBreaker:
    """Skip Jev for 60s if error/timeout rate > 20% over a 1-minute window."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[tuple[float, bool]] = []  # (ts, is_error)
        self._open_until = 0.0

    def allow(self) -> bool:
        with self._lock:
            return time.monotonic() >= self._open_until

    def record(self, is_error: bool) -> None:
        now = time.monotonic()
        with self._lock:
            self._events.append((now, is_error))
            cutoff = now - 60.0
            self._events = [(t, e) for t, e in self._events if t >= cutoff]
            if len(self._events) < 5:
                return
            err_rate = sum(1 for _, e in self._events if e) / len(self._events)
            if err_rate > 0.20:
                self._open_until = now + 60.0


_breaker = _CircuitBreaker()


def _latency_bucket(latency_ms: int) -> str:
    if latency_ms <= LATENCY_FAST_MS:
        return "fast"
    if latency_ms >= LATENCY_SLOW_MS:
        return "slow"
    return "normal"


def _parse_choice(answers: dict[str, Any], key: str, min_conf: float) -> str | None:
    ans = answers.get(key) or {}
    if ans.get("type") != "choice" and "value" not in ans and "answer" not in ans:
        # Flexible shapes from Decisions API
        pass
    value = ans.get("value") or ans.get("answer") or ans.get("choice")
    conf = ans.get("confidence")
    if conf is None and isinstance(ans.get("probabilities"), dict) and value is not None:
        conf = ans["probabilities"].get(str(value))
    if value is None or value == "none":
        return None
    if conf is not None and float(conf) < min_conf:
        return None
    return str(value)


def _parse_score(answers: dict[str, Any], key: str, min_conf: float) -> int | None:
    ans = answers.get(key) or {}
    score = ans.get("value")
    if score is None:
        score = ans.get("score")
    conf = ans.get("confidence")
    if score is None:
        return None
    if conf is not None and float(conf) < min_conf:
        return None
    # Doc 05: fsrs_grade = round(score) + 1 (zero-based score)
    grade = int(round(float(score))) + 1
    return max(1, min(4, grade))


def decide_with_jev(
    *,
    statement_latex: str,
    node_title: str,
    expected_latex: str,
    expected_operation: str | None,
    submitted_latex: str,
    eval_result: dict[str, Any],
    attempt_number: int,
    scaffold_level: int,
    latency_ms: int,
    structure_ok: bool,
    client: httpx.Client | None = None,
    api_key: str | None = None,
) -> JevDecision | None:
    key = api_key or settings.openrouter_api_key
    if settings.ai_enabled.lower() in ("0", "false", "no", "off"):
        return None
    if not key or not _breaker.allow():
        return None

    payload = {
        "model": settings.jev_model,
        "state": {
            "problem": {
                "statement_latex": statement_latex,
                "node_title": node_title,
            },
            "expected_step": {
                "latex": expected_latex,
                "operation": expected_operation or "UNKNOWN",
            },
            "submitted_step": {"latex": submitted_latex},
            "sympy": {
                "is_equivalent": bool(eval_result.get("is_equivalent")),
                "structure_ok": structure_ok,
                "error": eval_result.get("error"),
            },
            "context": {
                "attempt_number": attempt_number,
                "scaffold_level": scaffold_level,
                "latency_bucket": _latency_bucket(latency_ms),
            },
        },
        "questions": {
            "evaluation_verdict": {
                "type": "choice",
                "instructions": (
                    "Given `sympy`, `expected_step` and `submitted_step`, "
                    "what best describes the learner's step? "
                    "If sympy.is_equivalent is false you MUST NOT choose CORRECT_OPTIMAL "
                    "or CORRECT_SUBOPTIMAL. If true, choose only CORRECT_OPTIMAL or "
                    "CORRECT_SUBOPTIMAL."
                ),
                "criteria": {
                    "CORRECT_OPTIMAL": "Equivalent and performs the expected operation.",
                    "CORRECT_SUBOPTIMAL": "Equivalent but skips or reorders the expected operation.",
                    "SYNTAX_ERROR": "The input could not be read in the expected notation.",
                    "SIGN_ERROR": "Wrong only because a sign was flipped or dropped.",
                    "DISTRIBUTION_SLIP": "A factor was not multiplied across every term.",
                    "CALCULATION_SLIP": "An arithmetic mistake with the right method.",
                    "STRUCTURAL_MISCONCEPTION": "The method itself is wrong for this step.",
                    "PREREQUISITE_FAILURE": "The step shows a gap in an earlier skill, not in this one.",
                    "none": "None of the above fits.",
                },
            },
            "recommended_fsrs_grade": {
                "type": "score",
                "instructions": (
                    "How fluent was this attempt, considering correctness, "
                    "`context.attempt_number` and `context.latency_bucket`?"
                ),
                "criteria": [
                    "Again: failed or needed the operational hint.",
                    "Hard: solved with hesitation or a conceptual hint.",
                    "Good: solved correctly at normal pace with no hints.",
                    "Easy: solved immediately with no hesitation.",
                ],
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }
    timeout = settings.jev_timeout_ms / 1000.0
    own_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.post(OPENROUTER_DECISIONS_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            _breaker.record(True)
            return None
        data = resp.json()
        answers = data.get("answers") or data.get("results") or data
        if not isinstance(answers, dict):
            _breaker.record(True)
            return None
        verdict = _parse_choice(answers, "evaluation_verdict", settings.jev_choice_confidence)
        grade = _parse_score(answers, "recommended_fsrs_grade", settings.jev_score_confidence)
        if verdict is None:
            _breaker.record(False)  # valid response, low confidence
            return None
        clamped = clamp_jev_verdict(
            verdict, is_equivalent=bool(eval_result.get("is_equivalent"))
        )
        if clamped is None:
            _breaker.record(False)
            return None
        usage = data.get("usage") or {}
        cost = float(usage.get("cost") or usage.get("total_cost") or 0.0)
        _breaker.record(False)
        return JevDecision(verdict=clamped, fsrs_grade=grade, cost_usd=cost, raw=data)
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, KeyError, TypeError):
        _breaker.record(True)
        return None
    finally:
        if own_client:
            http.close()


def jev_is_success(verdict: str) -> bool:
    return verdict in _CORRECT


def reset_circuit_breaker_for_tests() -> None:
    global _breaker
    _breaker = _CircuitBreaker()
