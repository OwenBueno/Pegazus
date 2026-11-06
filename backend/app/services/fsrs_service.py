"""FSRS-6 wrapper around the `fsrs` package + DB helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fsrs import Card, Rating, Scheduler, State

if TYPE_CHECKING:
    import psycopg

_scheduler = Scheduler()

_RATING_MAP = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}

_STATE_TO_DB = {
    State.Learning: "LEARNING",
    State.Review: "REVIEW",
    State.Relearning: "RELEARNING",
}

_DB_TO_STATE = {v: k for k, v in _STATE_TO_DB.items()}


def schedule_review(
    *,
    difficulty: float | None,
    stability: float | None,
    fsrs_state: str,
    due_date: datetime | None,
    last_review_at: datetime | None,
    reps: int,
    lapses: int,
    grade: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply one FSRS review; return fields to persist on user_node_states."""
    now = now or datetime.now(timezone.utc)
    card = Card()
    if difficulty is not None:
        card.difficulty = float(difficulty)
    if stability is not None:
        card.stability = float(stability)
    card.state = _DB_TO_STATE.get(fsrs_state, State.Learning)
    if due_date is not None:
        card.due = due_date if due_date.tzinfo else due_date.replace(tzinfo=timezone.utc)
    if last_review_at is not None:
        card.last_review = (
            last_review_at if last_review_at.tzinfo else last_review_at.replace(tzinfo=timezone.utc)
        )

    rating = _RATING_MAP.get(grade, Rating.Good)
    updated, _log = _scheduler.review_card(card, rating, review_datetime=now)

    new_reps = reps + 1
    new_lapses = lapses + (1 if rating == Rating.Again else 0)

    return {
        "fsrs_state": _STATE_TO_DB.get(updated.state, "LEARNING"),
        "difficulty": float(updated.difficulty) if updated.difficulty is not None else None,
        "stability": float(updated.stability) if updated.stability is not None else None,
        "due_date": updated.due,
        "last_review_at": updated.last_review or now,
        "reps": new_reps,
        "lapses": new_lapses,
    }


def upsert_node_state_after_review(
    conn: "psycopg.Connection",
    *,
    user_id: UUID,
    node_id: UUID,
    grade: int,
) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT difficulty, stability, fsrs_state::text, due_date, last_review_at, reps, lapses
        FROM user_node_states
        WHERE user_id = %s AND node_id = %s
        """,
        (user_id, node_id),
    ).fetchone()

    if row is None:
        scheduled = schedule_review(
            difficulty=None,
            stability=None,
            fsrs_state="LEARNING",
            due_date=None,
            last_review_at=None,
            reps=0,
            lapses=0,
            grade=grade,
        )
        conn.execute(
            """
            INSERT INTO user_node_states (
                user_id, node_id, fsrs_state, difficulty, stability,
                due_date, last_review_at, reps, lapses
            ) VALUES (
                %s, %s, %s::fsrs_state_enum, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                user_id,
                node_id,
                scheduled["fsrs_state"],
                scheduled["difficulty"],
                scheduled["stability"],
                scheduled["due_date"],
                scheduled["last_review_at"],
                scheduled["reps"],
                scheduled["lapses"],
            ),
        )
    else:
        scheduled = schedule_review(
            difficulty=float(row["difficulty"]) if row["difficulty"] is not None else None,
            stability=float(row["stability"]) if row["stability"] is not None else None,
            fsrs_state=row["fsrs_state"],
            due_date=row["due_date"],
            last_review_at=row["last_review_at"],
            reps=int(row["reps"]),
            lapses=int(row["lapses"]),
            grade=grade,
        )
        conn.execute(
            """
            UPDATE user_node_states SET
                fsrs_state = %s::fsrs_state_enum,
                difficulty = %s,
                stability = %s,
                due_date = %s,
                last_review_at = %s,
                reps = %s,
                lapses = %s
            WHERE user_id = %s AND node_id = %s
            """,
            (
                scheduled["fsrs_state"],
                scheduled["difficulty"],
                scheduled["stability"],
                scheduled["due_date"],
                scheduled["last_review_at"],
                scheduled["reps"],
                scheduled["lapses"],
                user_id,
                node_id,
            ),
        )
    return scheduled
