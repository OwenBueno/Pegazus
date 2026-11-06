"""Session endpoints: evaluate-step, hints, due queue (P1–P3 lite)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Any, NamedTuple
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.types.json import Json

from app.auth import AuthUser, get_current_user
from app.config import settings
from app.db import get_conn
from app.schemas import (
    DueNodeOut,
    DueQueueOut,
    EvaluateStepIn,
    EvaluateStepOut,
    SessionCompleteIn,
    SessionCompleteOut,
    SessionHintIn,
    SessionHintOut,
    SessionItemOut,
    SessionNodeOut,
    SessionStartIn,
    SessionStartOut,
    SessionStepOut,
    SessionSyncIn,
    SessionSyncOut,
    SessionSyncAttemptOut,
    SessionTutorChatIn,
    SessionTutorChatOut,
)
from app.services.ai_cost import add_session_cost
from app.services.component_catalog import hide_blanks, public_props
from app.services.fsrs_service import upsert_node_state_after_review
from app.services.jev_client import decide_with_jev, jev_is_success
from app.services.openrouter_key import resolve_openrouter_key
from app.services.rule_engine import RuleDecision, _fsrs_grade, decide_verdict
from app.services.subject_profile import clamp_profile
from app.services.system2_hints import generate_socratic_hint
from app.services.session_genui import (
    build_session_genui,
    demo_steps_for_item,
    update_scaffold_from_band,
)
from app.services.lesson_beats import plan_is_selection_primary
from app.services.tutor_chat import MAX_TURNS, generate_tutor_reply
from app.pipeline.materialize_node import (
    first_unready_node,
    node_readiness,
    prefetch_next_path_node,
)
from app.graders import GradeResult, grade
from app.graders.legacy import legacy_parts
from app.graders.sympy import _norm_latex, _step_target, final_answer_shortcut  # noqa: F401 (re-export)
from app.telemetry import span
from app.workers.math_evaluator import evaluate_step_safe

router = APIRouter(prefix="/api/v1/session", tags=["session"])


def _lesson_beats_for_node(conn: psycopg.Connection, node_id: UUID) -> list[Any] | None:
    row = conn.execute(
        "SELECT lesson_beats FROM knowledge_nodes WHERE id = %s",
        (node_id,),
    ).fetchone()
    if not row:
        return None
    beats = row.get("lesson_beats")
    if isinstance(beats, str):
        try:
            beats = json.loads(beats)
        except json.JSONDecodeError:
            return None
    return beats if isinstance(beats, list) else None


def _student_latex_map(
    conn: psycopg.Connection, *, session_id: UUID, item_id: UUID
) -> dict[int, str]:
    rows = conn.execute(
        """
        SELECT DISTINCT ON (step_index) step_index, submitted_latex
        FROM attempts
        WHERE session_id = %s AND item_id = %s AND is_success = TRUE
        ORDER BY step_index ASC, created_at DESC
        """,
        (session_id, item_id),
    ).fetchall()
    return {int(r["step_index"]): str(r["submitted_latex"] or "") for r in rows}


def _parse_item_steps(raw: Any) -> list[dict[str, Any]]:
    steps = raw
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed item steps: {e}",
            ) from e
    if not isinstance(steps, list) or not steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed item steps",
        )
    return steps


def _resume_step_index(
    conn: psycopg.Connection, *, session_id: UUID, item_id: UUID, step_count: int
) -> int:
    """First missing successful step in 0..n-1 (contiguous), not MAX+1 with holes."""
    if step_count <= 0:
        return 0
    rows = conn.execute(
        """
        SELECT DISTINCT step_index
        FROM attempts
        WHERE session_id = %s AND item_id = %s AND is_success = TRUE
        ORDER BY step_index ASC
        """,
        (session_id, item_id),
    ).fetchall()
    done = {int(r["step_index"]) for r in rows}
    if step_count - 1 in done:  # final answer accepted (possibly via shortcut)
        return step_count - 1
    for i in range(step_count):
        if i not in done:
            return i
    return max(0, step_count - 1)


def needs_prior_steps(genui_plan: Any, *, step_index: int, step_count: int) -> bool:
    """Selection widgets (QuickCheck/NumberLine/MatchPairs) answer the final step in one go.

    Items whose steps were frozen (learners already had attempts) keep several steps, so the
    final-step submission must not be rejected for "missing" earlier steps.
    """
    if step_index <= 0:
        return False
    is_final = step_index == step_count - 1
    plan = genui_plan if isinstance(genui_plan, dict) else None
    return not (is_final and plan_is_selection_primary(plan))


def _require_prior_steps_success(
    conn: psycopg.Connection,
    *,
    session_id: UUID,
    item_id: UUID,
    step_index: int,
) -> None:
    if step_index <= 0:
        return
    rows = conn.execute(
        """
        SELECT DISTINCT step_index
        FROM attempts
        WHERE session_id = %s AND item_id = %s AND is_success = TRUE
          AND step_index < %s
        """,
        (session_id, item_id, step_index),
    ).fetchall()
    done = {int(r["step_index"]) for r in rows}
    missing = [i for i in range(step_index) if i not in done]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Complete earlier steps first (missing {missing[0]})",
        )


def _load_parts(item: dict[str, Any]) -> list[dict[str, Any]]:
    """``items.parts``, or the legacy mapping for rows written before the backfill."""
    parts = item.get("parts")
    if isinstance(parts, list) and parts:
        return [{**p, "props": hide_cloze(parts, p.get("props") or {})} for p in parts]
    return legacy_parts(item.get("steps"), item.get("genui_plan"), item["id"])[0]


def hide_cloze(parts: list[dict[str, Any]], v: Any) -> Any:
    """Cloze answers are ``[[x]]`` in generator text; rows saved before masking repeat them in
    prompt_md / props.prompt, so mask at read time too (answer_spec is untouched)."""
    return hide_blanks(v) if any(p.get("grader") == "cloze" for p in parts) else v


def _grade_part(parts: list[dict[str, Any]], part_index: int, answer: Any, **llm: Any) -> GradeResult:
    part = parts[part_index] if 0 <= part_index < len(parts) else {}
    return grade(str(part.get("grader") or ""), part.get("answer_spec"), answer, **llm)


def _under_rubric_cap(conn: psycopg.Connection, session_id: UUID) -> bool:
    """LLM rubric grading stops once the session has spent ``rubric_session_cap_usd``."""
    row = conn.execute("SELECT llm_cost_usd FROM session_logs WHERE id = %s", (session_id,)).fetchone()
    return float((row or {}).get("llm_cost_usd") or 0) < settings.rubric_session_cap_usd


class _Graded(NamedTuple):
    index: int  # may jump to the last step (final answer typed early)
    is_final: bool
    decision: RuleDecision
    score: float
    feedback: str | None
    eval_result: dict[str, Any] | None  # sympy only (feeds JEV)
    cost_usd: float = 0.0  # rubric_llm only


def _grade_attempt(
    steps: list[dict[str, Any]],
    parts: list[dict[str, Any]],
    index: int,
    answer: dict[str, Any],
    *,
    hint_level: int,
    latency_ms: int,
    check_prior: Callable[[int], None] | None = None,
    api_key: str | None = None,
    cache_key: str | None = None,
) -> _Graded:
    """RULES verdict for one part. Sympy keeps today's order: shortcut → prior steps → evaluate.

    Callers validate ``index`` (against ``steps`` for sympy items, else ``parts``). ``api_key``
    (None over the session cap) lets ``rubric_llm`` call the LLM; otherwise it grades by key terms.
    """
    if parts and parts[0].get("grader") != "sympy":
        r = _grade_part(parts, index, answer, api_key=api_key, cache_key=cache_key)
        is_final = index == len(parts) - 1
        fsrs = _fsrs_grade(r.is_success, hint_level, latency_ms, r.score) if is_final else None
        decision = RuleDecision(r.verdict, r.is_success, fsrs, r.decided_by)
        return _Graded(index, is_final, decision, r.score, r.feedback, None, float(r.extra.get("cost_usd") or 0))
    latex = answer.get("latex") if isinstance(answer.get("latex"), str) else ""
    eval_result = None
    if index < len(steps) - 1:
        with span("sympy.evaluate_final"):
            eval_result = final_answer_shortcut(latex, steps[-1])
        if eval_result is not None:
            index = len(steps) - 1
    if eval_result is None:
        if check_prior:
            check_prior(index)
        with span("sympy.evaluate"):
            eval_result = evaluate_step_safe(latex, _step_target(steps[index]))
    is_final = index == len(steps) - 1
    with span("jev.decide"):
        decision = decide_verdict(
            eval_result,
            operation=steps[index].get("operation"),
            hint_level=hint_level,
            latency_ms=latency_ms,
            is_final_step=is_final,
        )
    return _Graded(index, is_final, decision, 1.0 if decision.is_success else 0.0, None, eval_result)


def _load_item_node(
    conn: psycopg.Connection, *, item_id: UUID, node_id: UUID | None = None
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    item = conn.execute(
        """
        SELECT id, node_id, statement_latex, prompt, steps, genui_plan, parts, prompt_md, stimulus
        FROM items WHERE id = %s AND status = 'VERIFIED'
        """,
        (item_id,),
    ).fetchone()
    if item is None:
        return None
    if node_id is not None and item["node_id"] != node_id:
        return None
    node = conn.execute(
        """
        SELECT id AS node_id, slug, title, primer_md, source_attribution, lesson_beats
        FROM knowledge_nodes WHERE id = %s
        """,
        (item["node_id"],),
    ).fetchone()
    if node is None:
        return None
    return dict(item), dict(node)


def _display_steps(steps: list[dict[str, Any]]) -> list[SessionStepOut]:
    out: list[SessionStepOut] = []
    for s in steps:
        just = s.get("justification")
        gap = s.get("gap_latex")
        out.append(
            SessionStepOut(
                latex=str(s.get("latex") or ""),
                operation=s.get("operation"),
                justification=str(just)[:120] if just else None,
                gap_latex=str(gap)[:200] if gap else None,
            )
        )
    return out


def _pick_next_item(
    conn: psycopg.Connection,
    user_id: UUID,
    session_id: UUID,
    path_id: UUID | None = None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Due node first, else earliest seed/path node; skip items finished this session."""
    done_items = conn.execute(
        """
        SELECT DISTINCT item_id
        FROM attempts
        WHERE session_id = %s AND is_success = TRUE AND fsrs_grade IS NOT NULL
        """,
        (session_id,),
    ).fetchall()
    done_ids = {r["item_id"] for r in done_items}

    if path_id is not None:
        due = conn.execute(
            """
            SELECT n.id AS node_id, n.slug, n.title, n.primer_md, n.source_attribution, pn.sequence_index
            FROM path_nodes pn
            JOIN knowledge_nodes n ON n.id = pn.node_id
            JOIN user_node_states u ON u.node_id = pn.node_id AND u.user_id = %s
            WHERE pn.path_id = %s AND u.due_date <= NOW()
              AND pn.is_draft = FALSE
              AND (
                SELECT COUNT(*) FROM items i
                WHERE i.node_id = pn.node_id AND i.status = 'VERIFIED'
              ) >= 5
            ORDER BY u.due_date ASC
            LIMIT 20
            """,
            (user_id, path_id),
        ).fetchall()
        candidates: list[dict[str, Any]] = list(due)
        if not candidates:
            candidates = conn.execute(
                """
                SELECT n.id AS node_id, n.slug, n.title, n.primer_md, n.source_attribution, pn.sequence_index
                FROM path_nodes pn
                JOIN knowledge_nodes n ON n.id = pn.node_id
                LEFT JOIN user_node_states u
                  ON u.node_id = pn.node_id AND u.user_id = %s
                WHERE pn.path_id = %s
                  AND pn.is_draft = FALSE
                  AND (
                    SELECT COUNT(*) FROM items i
                    WHERE i.node_id = pn.node_id AND i.status = 'VERIFIED'
                  ) >= 5
                  AND COALESCE(u.p_mastery, 0) < 0.90
                ORDER BY pn.sequence_index ASC
                """,
                (user_id, path_id),
            ).fetchall()
    else:
        due = conn.execute(
            """
            SELECT n.id AS node_id, n.slug, n.title, n.primer_md, n.source_attribution
            FROM user_node_states u
            JOIN knowledge_nodes n ON n.id = u.node_id
            WHERE u.user_id = %s AND u.due_date <= NOW()
            ORDER BY u.due_date ASC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()

        candidates = list(due)
        if not candidates:
            # Topological-ish: roots (no incoming prerequisite) first, then by slug.
            candidates = conn.execute(
                """
                SELECT n.id AS node_id, n.slug, n.title, n.primer_md, n.source_attribution
                FROM knowledge_nodes n
                LEFT JOIN knowledge_edges e
                  ON e.child_id = n.id AND e.edge_type = 'PREREQUISITE_OF'
                GROUP BY n.id, n.slug, n.title, n.primer_md, n.source_attribution
                ORDER BY COUNT(e.parent_id) ASC, n.slug ASC
                """
            ).fetchall()

    for node in candidates:
        items = conn.execute(
            """
            SELECT id, node_id, statement_latex, prompt, steps, genui_plan, parts, prompt_md, stimulus
            FROM items
            WHERE node_id = %s AND status = 'VERIFIED'
            ORDER BY created_at ASC, id ASC
            """,
            (node["node_id"],),
        ).fetchall()
        for item in items:
            if item["id"] in done_ids:
                continue
            return item, node
    return None


@router.post("/start", response_model=SessionStartOut)
def start_session(
    body: SessionStartIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SessionStartOut:
    from app.api import require_consent_if_minor

    require_consent_if_minor(conn, user.id)
    path_id = body.path_id
    if path_id is not None:
        owned_path = conn.execute(
            "SELECT 1 FROM learning_paths WHERE id = %s AND user_id = %s",
            (path_id, user.id),
        ).fetchone()
        if owned_path is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")

    session_id = body.session_id
    if session_id is None:
        row = conn.execute(
            "INSERT INTO session_logs (user_id, path_id) VALUES (%s, %s) RETURNING id, path_id",
            (user.id, path_id),
        ).fetchone()
        assert row is not None
        session_id = row["id"]
        path_id = row["path_id"]
        conn.commit()
    else:
        owned = conn.execute(
            """
            SELECT path_id FROM session_logs
            WHERE id = %s AND user_id = %s AND completed_at IS NULL
            """,
            (session_id, user.id),
        ).fetchone()
        if owned is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        # Prefer body path_id only on create; resume uses stored path_id
        path_id = owned["path_id"] if owned["path_id"] is not None else path_id

    # Prefer explicit lesson item when provided
    picked = None
    if body.item_id is not None:
        loaded = _load_item_node(conn, item_id=body.item_id, node_id=body.node_id)
        if loaded:
            picked = loaded
    if picked is None and body.node_id is not None and path_id is not None:
        readiness = node_readiness(conn, path_id, body.node_id)
        if readiness is not None and not readiness["ready"]:
            # Not fully built: hand back teach beats (if designed) so the learner can start
            # reading while problems finish; the client keeps streaming materialize.
            teach_node = None
            if readiness["teach_ready"]:
                nrow = conn.execute(
                    """
                    SELECT id, slug, title, primer_md, source_attribution, subject_profile->>'notation' AS notation,
                           research_brief->'sources' AS sources
                    FROM knowledge_nodes WHERE id = %s
                    """,
                    (body.node_id,),
                ).fetchone()
                if nrow:
                    teach_node = SessionNodeOut(
                        id=nrow["id"],
                        slug=nrow["slug"],
                        title=nrow["title"],
                        primer_md=nrow.get("primer_md"),
                        source_attribution=nrow.get("source_attribution"),
                        lesson_beats=readiness["beats"],
                        notation=nrow.get("notation"),
                        sources=nrow.get("sources") or [],
                    )
            return SessionStartOut(
                session_id=session_id,
                item=None,
                node=teach_node,
                step_index=0,
                done=False,
                ai_enabled=settings.ai_on,
                path_id=path_id,
                scaffold_level=2,
                genui=None,
                needs_materialize=True,
                materialize_node_id=body.node_id,
                teach_ready=teach_node is not None,
                build_status=readiness["status"],
                build_error=readiness["error"] if readiness["status"] == "FAILED" else None,
            )
        # First VERIFIED item on that path node not finished this session
        node_row = conn.execute(
            """
            SELECT n.id AS node_id, n.slug, n.title, n.primer_md, n.source_attribution, n.lesson_beats
            FROM path_nodes pn
            JOIN knowledge_nodes n ON n.id = pn.node_id
            WHERE pn.path_id = %s AND pn.node_id = %s
            """,
            (path_id, body.node_id),
        ).fetchone()
        if node_row:
            items = conn.execute(
                """
                SELECT id, node_id, statement_latex, prompt, steps, genui_plan, parts, prompt_md, stimulus
                FROM items
                WHERE node_id = %s AND status = 'VERIFIED'
                ORDER BY created_at ASC, id ASC
                """,
                (body.node_id,),
            ).fetchall()
            done_items = conn.execute(
                """
                SELECT DISTINCT item_id FROM attempts
                WHERE session_id = %s AND is_success = TRUE AND fsrs_grade IS NOT NULL
                """,
                (session_id,),
            ).fetchall()
            done_ids = {r["item_id"] for r in done_items}
            for it in items:
                if it["id"] not in done_ids:
                    picked = (dict(it), dict(node_row))
                    break
            if picked is None and items:
                # All finished — still return first for lesson review UI
                picked = (dict(items[0]), dict(node_row))
            if picked is None:
                # Explicit lesson requested but content not built yet — stay on that node
                return SessionStartOut(
                    session_id=session_id,
                    item=None,
                    node=None,
                    step_index=0,
                    done=False,
                    ai_enabled=settings.ai_on,
                    path_id=path_id,
                    scaffold_level=2,
                    genui=None,
                    needs_materialize=True,
                    materialize_node_id=body.node_id,
                )

    if picked is None:
        picked = _pick_next_item(conn, user.id, session_id, path_id=path_id)
    if picked is None:
        mat_node = first_unready_node(conn, path_id) if path_id is not None else None
        return SessionStartOut(
            session_id=session_id,
            item=None,
            node=None,
            step_index=0,
            done=mat_node is None,
            ai_enabled=settings.ai_on,
            path_id=path_id,
            scaffold_level=2,
            genui=None,
            needs_materialize=mat_node is not None,
            materialize_node_id=mat_node,
        )

    item, node = picked
    lb = conn.execute(
        """
        SELECT lesson_beats, subject_profile->>'notation' AS notation, research_brief->'sources' AS sources
        FROM knowledge_nodes WHERE id = %s
        """,
        (node["node_id"],),
    ).fetchone()
    node.setdefault("lesson_beats", lb["lesson_beats"] if lb else [])
    notation = lb["notation"] if lb else None
    sources = (lb["sources"] if lb else None) or []

    beats = node.get("lesson_beats") or []
    if isinstance(beats, str):
        try:
            beats = json.loads(beats)
        except json.JSONDecodeError:
            beats = []
    # Do NOT block practice when items exist but beats are still empty —
    # materialize may have written items first; session can run problem-only.

    steps = item["steps"]
    if isinstance(steps, str):
        steps = json.loads(steps)

    sc_row = conn.execute(
        """
        SELECT current_scaffold_level FROM user_node_states
        WHERE user_id = %s AND node_id = %s
        """,
        (user.id, node["node_id"]),
    ).fetchone()
    scaffold_level = int(sc_row["current_scaffold_level"]) if sc_row else 1

    genui_plan = item.get("genui_plan")
    if isinstance(genui_plan, str):
        try:
            genui_plan = json.loads(genui_plan)
        except json.JSONDecodeError:
            genui_plan = None
    parts = _load_parts({**item, "steps": steps, "genui_plan": genui_plan})
    is_sympy = parts[0].get("grader") == "sympy" if parts else True
    step_index = _resume_step_index(
        conn, session_id=session_id, item_id=item["id"], step_count=len(steps) if is_sympy else len(parts)
    )
    student_map = _student_latex_map(conn, session_id=session_id, item_id=item["id"])

    demo = demo_steps_for_item(beats if isinstance(beats, list) else None, item["id"])
    or_key = resolve_openrouter_key(conn, user.id)
    genui = build_session_genui(
        session_id=str(session_id),
        node_id=str(node["node_id"]),
        item_id=str(item["id"]),
        statement_latex=item["statement_latex"] or "",
        steps=steps,
        parts=parts,
        step_index=step_index,
        scaffold_level=scaffold_level,
        genui_plan=genui_plan if isinstance(genui_plan, dict) else None,
        student_latex_by_step=student_map,
        node_title=str(node.get("title") or ""),
        demo_steps=demo,
        api_key=or_key,
    )

    # Keep one lesson ahead warm while the learner practices
    if path_id is not None:
        prefetch_next_path_node(
            conn,
            path_id=path_id,
            current_node_id=node["node_id"],
            user_id=user.id,
            api_key=or_key,
        )

    beats = node.get("lesson_beats") or []
    if isinstance(beats, str):
        try:
            beats = json.loads(beats)
        except json.JSONDecodeError:
            beats = []

    return SessionStartOut(
        session_id=session_id,
        item=SessionItemOut(
            id=item["id"],
            statement_latex=item["statement_latex"] or "",
            prompt=hide_cloze(parts, item.get("prompt")),
            steps=_display_steps(steps) if is_sympy else [],
            step_count=len(steps) if is_sympy else len(parts),
            prompt_md=hide_cloze(parts, item.get("prompt_md")),
            stimulus=hide_cloze(parts, item.get("stimulus")),
            parts=[public_props(p) for p in parts],
        ),
        node=SessionNodeOut(
            id=node["node_id"],
            slug=node["slug"],
            title=node["title"],
            primer_md=node.get("primer_md"),
            source_attribution=node.get("source_attribution"),
            lesson_beats=list(beats) if isinstance(beats, list) else [],
            notation=notation,
            sources=sources,
        ),
        step_index=step_index,
        done=False,
        ai_enabled=settings.ai_on,
        path_id=path_id,
        scaffold_level=scaffold_level,
        genui=genui,
    )


@router.post("/{session_id}/complete", response_model=SessionCompleteOut)
def complete_session(
    session_id: UUID,
    body: SessionCompleteIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SessionCompleteOut:
    owned = conn.execute(
        "SELECT id FROM session_logs WHERE id = %s AND user_id = %s",
        (session_id, user.id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    counts = conn.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN is_success THEN 1 ELSE 0 END), 0)::int AS correct_count,
          COALESCE(SUM(CASE WHEN NOT is_success THEN 1 ELSE 0 END), 0)::int AS incorrect_count
        FROM attempts
        WHERE session_id = %s
        """,
        (session_id,),
    ).fetchone()
    assert counts is not None

    updated = conn.execute(
        """
        UPDATE session_logs SET
          completed_at = NOW(),
          active_seconds = %s,
          micro_breaks_triggered = %s,
          micro_breaks_skipped = %s,
          post_session_rest_completed = %s
        WHERE id = %s
        RETURNING id, completed_at, active_seconds
        """,
        (
            body.active_seconds,
            body.micro_breaks_triggered,
            body.micro_breaks_skipped,
            body.post_session_rest_completed,
            session_id,
        ),
    ).fetchone()
    conn.commit()
    assert updated is not None

    return SessionCompleteOut(
        session_id=updated["id"],
        completed_at=updated["completed_at"],
        active_seconds=updated["active_seconds"],
        correct_count=counts["correct_count"],
        incorrect_count=counts["incorrect_count"],
    )


@router.post("/hint", response_model=SessionHintOut)
def session_hint(
    body: SessionHintIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SessionHintOut:
    owned = conn.execute(
        "SELECT 1 FROM session_logs WHERE id = %s AND user_id = %s",
        (body.session_id, user.id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    item = conn.execute(
        """
        SELECT i.id, i.statement_latex, i.prompt_md, i.steps, i.genui_plan, i.parts,
               n.title AS node_title, n.subject_profile
        FROM items i
        JOIN knowledge_nodes n ON n.id = i.node_id
        WHERE i.id = %s AND i.status = 'VERIFIED'
        """,
        (body.item_id,),
    ).fetchone()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    steps = item["steps"]
    if isinstance(steps, str):
        steps = json.loads(steps)
    parts = _load_parts({**item, "steps": steps})
    # Non-sympy items have no steps: step_index addresses the part instead.
    if body.step_index < 0 or body.step_index >= max(len(steps or []), len(parts)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid step_index")

    expected = steps[body.step_index] if body.step_index < len(steps or []) else {}
    with span("system2.hint"):
        prompt, cost, source = generate_socratic_hint(
            locale=body.locale,
            hint_level=body.hint_level,
            statement_latex=item["statement_latex"] or item.get("prompt_md") or "",
            expected_latex=str(expected.get("latex") or ""),
            submitted_latex=body.submitted_latex or "",
            steps=steps or [],
            verdict=body.verdict,
            api_key=resolve_openrouter_key(conn, user.id) or None,
            profile=clamp_profile(item["subject_profile"]) if item.get("subject_profile") else None,
            parts=parts,
        )
    add_session_cost(conn, body.session_id, cost)
    conn.commit()

    return SessionHintOut(
        socratic_prompt=prompt,
        source=source,
        ai_enabled=settings.ai_on,
        hint_level=body.hint_level,
    )


@router.post("/tutor-chat", response_model=SessionTutorChatOut)
def session_tutor_chat(
    body: SessionTutorChatIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SessionTutorChatOut:
    owned = conn.execute(
        "SELECT 1 FROM session_logs WHERE id = %s AND user_id = %s",
        (body.session_id, user.id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    item = conn.execute(
        """
        SELECT i.id, i.statement_latex, i.prompt, i.prompt_md, i.steps, i.genui_plan, i.parts,
               n.title AS node_title, n.primer_md, n.subject_profile
        FROM items i
        JOIN knowledge_nodes n ON n.id = i.node_id
        WHERE i.id = %s AND i.status = 'VERIFIED'
        """,
        (body.item_id,),
    ).fetchone()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    steps = item["steps"]
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            steps = []
    if not isinstance(steps, list):
        steps = []

    # turn_index = prior user messages in history + this message
    prior_user = sum(1 for h in body.history if h.role == "user")
    turn_index = prior_user + 1

    hist = [{"role": h.role, "content": h.content} for h in body.history]

    with span("system2.tutor_chat"):
        result = generate_tutor_reply(
            message=body.message,
            locale=body.locale,
            node_title=str(item.get("node_title") or ""),
            primer_md=item.get("primer_md"),
            statement_latex=str(item.get("statement_latex") or ""),
            prompt=item.get("prompt_md") or item.get("prompt"),
            steps=steps,
            history=hist,
            turn_index=turn_index,
            api_key=resolve_openrouter_key(conn, user.id) or None,
            profile=clamp_profile(item["subject_profile"]) if item.get("subject_profile") else None,
            parts=_load_parts({**item, "steps": steps}),
        )
    add_session_cost(conn, body.session_id, result.cost_usd)
    conn.commit()

    return SessionTutorChatOut(
        reply=result.reply,
        refused=result.refused,
        source=result.source,
        ai_enabled=settings.ai_on,
        turn_index=result.turn_index,
        capped=result.capped,
        max_turns=MAX_TURNS,
    )


@router.post("/evaluate-step", response_model=EvaluateStepOut)
def evaluate_step(
    body: EvaluateStepIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> EvaluateStepOut:
    item = conn.execute(
        """
        SELECT i.id, i.node_id, i.statement_latex, i.steps, i.genui_plan, i.parts,
               n.title AS node_title
        FROM items i
        JOIN knowledge_nodes n ON n.id = i.node_id
        WHERE i.id = %s AND i.status = 'VERIFIED'
        """,
        (body.item_id,),
    ).fetchone()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    genui_plan = item.get("genui_plan")
    if isinstance(genui_plan, str):
        try:
            genui_plan = json.loads(genui_plan)
        except json.JSONDecodeError:
            genui_plan = None
    parts = _load_parts({**item, "genui_plan": genui_plan})
    is_sympy = parts[0].get("grader") == "sympy" if parts else True
    # §6.2 items carry no steps; only sympy items need them.
    steps = _parse_item_steps(item["steps"]) if is_sympy else []
    assert body.part_index is not None and body.answer is not None  # AnswerIn guarantees both
    if body.part_index >= (len(steps) if is_sympy else len(parts)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid part_index")
    if is_sympy and not _step_target(steps[body.part_index]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Malformed item step")
    latex = body.answer.get("latex") if isinstance(body.answer.get("latex"), str) else None

    session_id = body.session_id
    if session_id is None:
        row = conn.execute(
            """
            INSERT INTO session_logs (user_id) VALUES (%s)
            RETURNING id
            """,
            (user.id,),
        ).fetchone()
        assert row is not None
        session_id = row["id"]
    else:
        owned = conn.execute(
            "SELECT 1 FROM session_logs WHERE id = %s AND user_id = %s",
            (session_id, user.id),
        ).fetchone()
        if owned is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    def check_prior(index: int) -> None:
        if needs_prior_steps(genui_plan, step_index=index, step_count=len(steps)):
            _require_prior_steps_success(conn, session_id=session_id, item_id=body.item_id, step_index=index)

    or_key = resolve_openrouter_key(conn, user.id)
    graded = _grade_attempt(
        steps, parts, body.part_index, body.answer,
        hint_level=body.hint_level, latency_ms=body.latency_ms, check_prior=check_prior,
        api_key=or_key if _under_rubric_cap(conn, session_id) else None,
        cache_key=str(body.item_id),
    )
    step_index, is_final, decision = graded.index, graded.is_final, graded.decision
    grader = parts[step_index].get("grader") if step_index < len(parts) else "sympy"

    llm_cost = graded.cost_usd
    # JEV judges math only; other graders are deterministic (Doc 10 §5).
    if or_key and graded.eval_result is not None:
        expected = steps[step_index]
        attempt_number = conn.execute(
            """
            SELECT COUNT(*)::int AS n FROM attempts
            WHERE session_id = %s AND item_id = %s AND step_index = %s
            """,
            (session_id, body.item_id, step_index),
        ).fetchone()
        n = int(attempt_number["n"]) + 1 if attempt_number else 1
        jev = decide_with_jev(
            statement_latex=item["statement_latex"],
            node_title=item["node_title"],
            expected_latex=str(expected.get("latex") or _step_target(expected)),
            expected_operation=expected.get("operation"),
            submitted_latex=latex or "",
            eval_result=graded.eval_result,
            attempt_number=n,
            scaffold_level=body.scaffold_level,
            latency_ms=body.latency_ms,
            structure_ok=decision.structure_ok,
            api_key=or_key,
        )
        if jev is not None:
            fsrs = jev.fsrs_grade
            if fsrs is None and is_final:
                fsrs = decision.fsrs_grade
            elif not is_final:
                fsrs = None
            decision = RuleDecision(
                verdict=jev.verdict,
                is_success=jev_is_success(jev.verdict),
                fsrs_grade=fsrs,
                decided_by="JEV",
                structure_ok=decision.structure_ok,
            )
            llm_cost = jev.cost_usd
    score = graded.score if graded.eval_result is None else (1.0 if decision.is_success else 0.0)

    fsrs_due_at = None
    if is_final and decision.fsrs_grade is not None:
        scheduled = upsert_node_state_after_review(
            conn,
            user_id=user.id,
            node_id=item["node_id"],
            grade=decision.fsrs_grade,
        )
        fsrs_due_at = scheduled["due_date"]

    attempt = conn.execute(
        """
        INSERT INTO attempts (
            session_id, user_id, node_id, item_id, step_index,
            submitted_latex, verdict, is_success, hint_level,
            latency_ms, scaffold_level, fsrs_grade, decided_by,
            submitted_answer, grader, score
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            session_id,
            user.id,
            item["node_id"],
            body.item_id,
            step_index,
            latex,
            decision.verdict,
            decision.is_success,
            body.hint_level,
            body.latency_ms,
            body.scaffold_level,
            decision.fsrs_grade,
            decision.decided_by,
            Json(body.answer),
            grader,
            score,
        ),
    ).fetchone()
    add_session_cost(conn, session_id, llm_cost)
    if grader == "code_tests" and decision.is_success and (parts[step_index].get("answer_spec") or {}).get("beta"):
        # ponytail: a learner's all-green browser run proves the tests are passable (Doc 10 §7.1);
        # client-trusted like the grade itself. Upgrade: server sandbox runs the reference solution.
        conn.execute(
            """
            UPDATE items SET parts = jsonb_set(jsonb_set(parts, ARRAY[%s, 'answer_spec', 'beta'], 'false'),
                                               ARRAY[%s, 'props', 'beta'], 'false')
            WHERE id = %s
            """,
            (str(step_index), str(step_index), body.item_id),
        )

    # Accuracy-band scaffold update (lite US-4.1)
    recent = conn.execute(
        """
        SELECT is_success FROM attempts
        WHERE user_id = %s AND node_id = %s
        ORDER BY created_at DESC
        LIMIT 8
        """,
        (user.id, item["node_id"]),
    ).fetchall()
    rate = (
        sum(1 for r in recent if r["is_success"]) / len(recent) if recent else 0.5
    )
    sc_row = conn.execute(
        """
        SELECT current_scaffold_level FROM user_node_states
        WHERE user_id = %s AND node_id = %s
        """,
        (user.id, item["node_id"]),
    ).fetchone()
    cur_sc = int(sc_row["current_scaffold_level"]) if sc_row else body.scaffold_level
    new_sc = update_scaffold_from_band(current=cur_sc, recent_success_rate=rate)
    if sc_row:
        conn.execute(
            """
            UPDATE user_node_states SET current_scaffold_level = %s
            WHERE user_id = %s AND node_id = %s
            """,
            (new_sc, user.id, item["node_id"]),
        )
    else:
        # Ensure row exists for scaffold even before FSRS final
        conn.execute(
            """
            INSERT INTO user_node_states (user_id, node_id, current_scaffold_level)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, node_id) DO UPDATE
              SET current_scaffold_level = EXCLUDED.current_scaffold_level
            """,
            (user.id, item["node_id"], new_sc),
        )

    n_parts = len(steps) if is_sympy else len(parts)
    next_step = step_index + 1 if decision.is_success and not is_final else step_index
    if next_step >= n_parts:
        next_step = n_parts - 1
    active_status = "VALID" if decision.is_success else "INVALID"
    # Include this successful submit in student map for next genui
    student_map = _student_latex_map(conn, session_id=session_id, item_id=body.item_id)
    if decision.is_success and latex:
        student_map[step_index] = latex

    genui = build_session_genui(
        session_id=str(session_id),
        node_id=str(item["node_id"]),
        item_id=str(body.item_id),
        statement_latex=item["statement_latex"] or "",
        steps=steps,
        parts=parts,
        # Past the last index renders every line locked + VALID (worked solution).
        step_index=(
            n_parts if decision.is_success and is_final
            else next_step if decision.is_success else step_index
        ),
        scaffold_level=new_sc,
        hint_tier=body.hint_level if body.hint_level > 0 else None,
        hint_prompt=None,
        active_status=active_status if not decision.is_success else "PENDING",
        genui_plan=genui_plan if isinstance(genui_plan, dict) else None,
        student_latex_by_step=student_map,
        node_title=str(item.get("node_title") or ""),
        recent_verdict=decision.verdict,
        demo_steps=demo_steps_for_item(
            _lesson_beats_for_node(conn, item["node_id"]), body.item_id
        ),
        api_key=or_key,
    )

    # After a successful final step, warm the next path node if any
    if decision.is_success and is_final:
        path_row = conn.execute(
            "SELECT path_id FROM session_logs WHERE id = %s",
            (session_id,),
        ).fetchone()
        if path_row and path_row.get("path_id"):
            prefetch_next_path_node(
                conn,
                path_id=path_row["path_id"],
                current_node_id=item["node_id"],
                user_id=user.id,
                api_key=resolve_openrouter_key(conn, user.id),
            )

    conn.commit()
    assert attempt is not None

    return EvaluateStepOut(
        verdict=decision.verdict,
        is_success=decision.is_success,
        decided_by=decision.decided_by,
        structure_ok=decision.structure_ok,
        session_id=session_id,
        attempt_id=int(attempt["id"]),
        fsrs_grade=decision.fsrs_grade,
        fsrs_due_at=fsrs_due_at,
        is_final_step=is_final,
        scaffold_level=new_sc,
        genui=genui,
        score=score,
        feedback=graded.feedback,
        grader=grader,
    )


@router.get("/due", response_model=DueQueueOut)
def due_queue(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> DueQueueOut:
    rows = conn.execute(
        """
        SELECT u.node_id, n.slug, n.title, u.due_date, u.fsrs_state::text, u.reps
        FROM user_node_states u
        JOIN knowledge_nodes n ON n.id = u.node_id
        WHERE u.user_id = %s AND u.due_date <= NOW()
        ORDER BY u.due_date ASC
        """,
        (user.id,),
    ).fetchall()
    return DueQueueOut(
        nodes=[
            DueNodeOut(
                node_id=r["node_id"],
                slug=r["slug"],
                title=r["title"],
                due_date=r["due_date"],
                fsrs_state=r["fsrs_state"],
                reps=r["reps"],
            )
            for r in rows
        ]
    )


@router.post("/{session_id}/sync", response_model=SessionSyncOut)
def sync_offline_attempts(
    session_id: UUID,
    body: SessionSyncIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SessionSyncOut:
    """Re-evaluate offline queue server-side; client verdicts are never trusted."""
    owned = conn.execute(
        "SELECT 1 FROM session_logs WHERE id = %s AND user_id = %s",
        (session_id, user.id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=404, detail="Session not found")

    results: list[SessionSyncAttemptOut] = []
    for att in body.attempts:
        existing = conn.execute(
            """
            SELECT attempt_id FROM offline_sync_keys
            WHERE user_id = %s AND client_attempt_id = %s
            """,
            (user.id, att.client_attempt_id),
        ).fetchone()
        if existing and existing["attempt_id"]:
            prev = conn.execute(
                "SELECT id, verdict, is_success FROM attempts WHERE id = %s",
                (existing["attempt_id"],),
            ).fetchone()
            if prev:
                results.append(
                    SessionSyncAttemptOut(
                        client_attempt_id=att.client_attempt_id,
                        status="accepted",
                        attempt_id=int(prev["id"]),
                        verdict=prev["verdict"],
                        is_success=prev["is_success"],
                    )
                )
                continue

        item = conn.execute(
            "SELECT id, node_id, steps, genui_plan, parts FROM items WHERE id = %s AND status = 'VERIFIED'",
            (att.item_id,),
        ).fetchone()
        if item is None:
            results.append(
                SessionSyncAttemptOut(
                    client_attempt_id=att.client_attempt_id,
                    status="skipped",
                    reason="item_not_found",
                )
            )
            continue
        steps = item["steps"]
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except json.JSONDecodeError:
                results.append(
                    SessionSyncAttemptOut(
                        client_attempt_id=att.client_attempt_id,
                        status="failed",
                        reason="malformed_steps",
                    )
                )
                continue
        steps = steps if isinstance(steps, list) else []
        parts = _load_parts({**item, "steps": steps})
        assert att.part_index is not None and att.answer is not None  # AnswerIn guarantees both
        is_sympy = parts[0].get("grader") == "sympy" if parts else True
        if att.part_index >= (len(steps) if is_sympy else len(parts)):
            results.append(
                SessionSyncAttemptOut(
                    client_attempt_id=att.client_attempt_id,
                    status="skipped",
                    reason="bad_step_index",
                )
            )
            continue
        if is_sympy and not _step_target(steps[att.part_index]):
            results.append(
                SessionSyncAttemptOut(
                    client_attempt_id=att.client_attempt_id,
                    status="failed",
                    reason="empty_target",
                )
            )
            continue
        graded = _grade_attempt(
            steps, parts, att.part_index, att.answer,
            hint_level=att.hint_level, latency_ms=att.latency_ms,
        )
        is_final, decision = graded.is_final, graded.decision
        if is_final and decision.fsrs_grade is not None:
            upsert_node_state_after_review(
                conn,
                user_id=user.id,
                node_id=item["node_id"],
                grade=decision.fsrs_grade,
            )
        row = conn.execute(
            """
            INSERT INTO attempts (
                session_id, user_id, node_id, item_id, step_index,
                submitted_latex, verdict, is_success, hint_level,
                latency_ms, scaffold_level, fsrs_grade, decided_by,
                submitted_answer, grader, score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                session_id,
                user.id,
                item["node_id"],
                att.item_id,
                graded.index,
                att.answer.get("latex") if isinstance(att.answer.get("latex"), str) else None,
                decision.verdict,
                decision.is_success,
                att.hint_level,
                att.latency_ms,
                att.scaffold_level,
                decision.fsrs_grade,
                decision.decided_by,
                Json(att.answer),
                parts[graded.index].get("grader") if graded.index < len(parts) else "sympy",
                graded.score,
            ),
        ).fetchone()
        assert row is not None
        conn.execute(
            """
            INSERT INTO offline_sync_keys (user_id, client_attempt_id, attempt_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, client_attempt_id) DO UPDATE SET attempt_id = EXCLUDED.attempt_id
            """,
            (user.id, att.client_attempt_id, row["id"]),
        )
        results.append(
            SessionSyncAttemptOut(
                client_attempt_id=att.client_attempt_id,
                status="accepted",
                attempt_id=int(row["id"]),
                verdict=decision.verdict,
                is_success=decision.is_success,
            )
        )
    conn.commit()
    return SessionSyncOut(results=results)
