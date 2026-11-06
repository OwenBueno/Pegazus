"""Quick Socratic API (US-8.1)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api import require_consent_if_minor
from app.auth import AuthUser, get_current_user
from app.db import get_conn
from app.services.ai_cost import add_session_cost
from app.services.openrouter_key import resolve_openrouter_key
from app.services.socratic_ask import run_socratic_ask

router = APIRouter(prefix="/api/v1/socratic", tags=["socratic"])


class SocraticAskIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    locale: str = Field(default="en", pattern="^(en|es)$")
    exchange_index: int = Field(ge=1, le=3)
    prior_prompts: list[str] = Field(default_factory=list)
    session_id: UUID | None = None


class SocraticStepOut(BaseModel):
    latex: str
    locked: bool = True


class SocraticAskOut(BaseModel):
    intent: str
    refused: bool
    socratic_prompt: str
    steps: list[SocraticStepOut]
    exchange_index: int
    session_id: UUID
    genui: dict[str, Any]


@router.post("/ask", response_model=SocraticAskOut)
def socratic_ask(
    body: SocraticAskIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SocraticAskOut:
    require_consent_if_minor(conn, user.id)

    if body.exchange_index > 3:
        raise HTTPException(status_code=400, detail="Max 3 exchanges")

    session_id = body.session_id
    if session_id is None:
        row = conn.execute(
            "INSERT INTO session_logs (user_id) VALUES (%s) RETURNING id",
            (user.id,),
        ).fetchone()
        assert row is not None
        session_id = row["id"]
        conn.commit()
    else:
        owned = conn.execute(
            "SELECT 1 FROM session_logs WHERE id = %s AND user_id = %s",
            (session_id, user.id),
        ).fetchone()
        if owned is None:
            raise HTTPException(status_code=404, detail="Session not found")

    api_key = resolve_openrouter_key(conn, user.id) or None
    result = run_socratic_ask(
        query=body.query.strip(),
        locale=body.locale,
        exchange_index=body.exchange_index,
        prior_prompts=body.prior_prompts,
        session_id=str(session_id),
        api_key=api_key,
    )
    add_session_cost(conn, session_id, result.cost_usd)
    conn.commit()

    return SocraticAskOut(
        intent=result.intent,
        refused=result.refused,
        socratic_prompt=result.socratic_prompt,
        steps=[SocraticStepOut(latex=s["latex"], locked=s.get("locked", True)) for s in result.steps],
        exchange_index=result.exchange_index,
        session_id=session_id,
        genui=result.genui,
    )
