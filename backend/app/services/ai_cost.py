"""Accumulate OpenRouter costs onto session_logs.llm_cost_usd."""

from __future__ import annotations

from uuid import UUID

import psycopg


def add_session_cost(conn: psycopg.Connection, session_id: UUID, cost_usd: float) -> None:
    if cost_usd <= 0:
        return
    conn.execute(
        """
        UPDATE session_logs
        SET llm_cost_usd = llm_cost_usd + %s
        WHERE id = %s
        """,
        (cost_usd, session_id),
    )
