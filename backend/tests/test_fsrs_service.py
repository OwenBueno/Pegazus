"""FSRS wrapper matches library for a fixed review history."""

from __future__ import annotations

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler

from app.services.fsrs_service import schedule_review


def test_fsrs_matches_library_good_then_again():
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    lib = Scheduler()

    card = Card()
    card, _ = lib.review_card(card, Rating.Good, review_datetime=fixed_now)
    after_good = schedule_review(
        difficulty=None,
        stability=None,
        fsrs_state="LEARNING",
        due_date=None,
        last_review_at=None,
        reps=0,
        lapses=0,
        grade=3,
        now=fixed_now,
    )
    assert abs(after_good["stability"] - float(card.stability)) < 1e-6
    assert abs(after_good["difficulty"] - float(card.difficulty)) < 1e-6

    t2 = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    card2, _ = lib.review_card(card, Rating.Again, review_datetime=t2)
    after_again = schedule_review(
        difficulty=after_good["difficulty"],
        stability=after_good["stability"],
        fsrs_state=after_good["fsrs_state"],
        due_date=after_good["due_date"],
        last_review_at=after_good["last_review_at"],
        reps=after_good["reps"],
        lapses=after_good["lapses"],
        grade=1,
        now=t2,
    )
    assert abs(after_again["stability"] - float(card2.stability)) < 1e-6
    assert after_again["lapses"] == 1
    assert after_again["reps"] == 2


def test_rule_engine_grades():
    from app.services.rule_engine import decide_verdict

    ok = decide_verdict(
        {"success": True, "is_equivalent": True, "sign_error": False, "error": None},
        hint_level=0,
        latency_ms=1000,
        is_final_step=True,
    )
    assert ok.verdict == "CORRECT_OPTIMAL"
    assert ok.fsrs_grade == 4  # fast

    slow = decide_verdict(
        {"success": True, "is_equivalent": True, "sign_error": False, "error": None},
        hint_level=0,
        latency_ms=10_000,
        is_final_step=True,
    )
    assert slow.fsrs_grade == 3

    sign = decide_verdict(
        {"success": True, "is_equivalent": False, "sign_error": True, "error": None},
        is_final_step=True,
    )
    assert sign.verdict == "SIGN_ERROR"
    assert sign.fsrs_grade == 1
