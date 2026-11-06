"""Learning path ingest, SSE stream, and KST diagnostic (P4-lite)."""

from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Any, Iterator
from uuid import UUID

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from psycopg.types.json import Json

from app.auth import AuthUser, get_current_user
from app.config import settings
from app.db import get_conn
from app.pipeline.materialize_node import (
    STALE_BUILD_MINUTES,
    is_materialize_inflight,
    lesson_ready,
    materialize_buffer_key,
    node_readiness,
    prefetch_next_path_node,
    schedule_materialize_node,
    shown_build_status,
)
from app.pipeline.research_job import run_research_job
from app.pipeline.sse_buffer import append_event, get_events_after, is_complete, reset_buffer, wait_for_events
from app.schemas import (
    DiagnosticAnswerIn,
    DiagnosticProbeOut,
    MaterializeOut,
    PathDraftNodeOut,
    PathProfileIn,
    PathImproveIn,
    PathIngestIn,
    PathIngestOut,
    PathNodeOut,
    PathOut,
    PathRebuildIn,
    PathSummaryOut,
    PlacementGenerateIn,
    PlacementGenerateOut,
    PlacementGradeIn,
    PlacementGradeOut,
    PlacementQuestionOut,
    SessionPartOut,
    SubjectProfile,
    UploadParseOut,
)
from app.services.kst_diagnostic import (
    FLUENCY_PASS,
    DiagnosticGraph,
    NodeStatus,
    apply_answer,
    build_diagnostic_graph,
    finalize_unknown_as_not_mastered,
    frontier_nodes,
    get_low_conf,
    get_session,
    mark_low_conf,
    persist_graph_mastery,
    select_probe,
    should_stop,
    store_session,
    upsert_p_mastery,
)
from app.api_session import _load_parts, hide_cloze
from app.graders import grade
from app.services.component_catalog import public_props
from app.services.openrouter_key import resolve_openrouter_key
from app.services.placement_exam import PlacementError, generate_placement_exam, grade_placement_exam
from app.services.subject_profile import MATH_PROFILE, clamp_profile, infer_subject_profile
from app.services.upload_parse import extract_text_from_bytes
from app.workers.math_evaluator import evaluate_step_safe

router = APIRouter(prefix="/api/v1/paths", tags=["paths"])


def _require_owned_path(
    conn: psycopg.Connection, path_id: UUID, user_id: UUID
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM learning_paths WHERE id = %s AND user_id = %s",
        (path_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")
    return dict(row)


def _path_nodes_with_mastery(
    conn: psycopg.Connection, path_id: UUID, user_id: UUID
) -> list[dict[str, Any]]:
    return conn.execute(
        """
        SELECT pn.node_id, pn.sequence_index, pn.is_draft, pn.build_status, pn.build_error,
               COALESCE(pn.build_started_at < NOW() - make_interval(mins => %s), TRUE) AS stale,
               n.slug, n.title, n.primer_md, n.lesson_beats, n.research_brief->'sources' AS sources,
               n.source_attribution, n.source_license, n.source_url,
               COALESCE(u.p_mastery, 0)::float AS p_mastery,
               (
                 SELECT COUNT(*)::int FROM items i
                 WHERE i.node_id = pn.node_id AND i.status = 'VERIFIED'
               ) AS verified_count
        FROM path_nodes pn
        JOIN knowledge_nodes n ON n.id = pn.node_id
        LEFT JOIN user_node_states u
          ON u.node_id = pn.node_id AND u.user_id = %s
        WHERE pn.path_id = %s
        ORDER BY pn.sequence_index ASC
        """,
        (STALE_BUILD_MINUTES, user_id, path_id),
    ).fetchall()


def _label_for(p: float, is_frontier: bool) -> str:
    if p >= 0.90:
        return "mastered"
    if is_frontier:
        return "frontier"
    if 0 < p < 0.90:
        return "locked" if p <= 0.10 else "unknown"
    return "unknown"


def _compute_frontier_ids(rows: list[dict[str, Any]], conn: psycopg.Connection) -> list[UUID]:
    """Frontier: low mastery nodes whose parents on the path are all mastered."""
    ids = {r["node_id"] for r in rows}
    mastery = {r["node_id"]: float(r["p_mastery"]) for r in rows}
    edges = conn.execute(
        """
        SELECT parent_id, child_id FROM knowledge_edges
        WHERE edge_type = 'PREREQUISITE_OF' AND parent_id = ANY(%s) AND child_id = ANY(%s)
        """,
        (list(ids), list(ids)),
    ).fetchall()
    parents: dict[UUID, list[UUID]] = {nid: [] for nid in ids}
    for e in edges:
        parents[e["child_id"]].append(e["parent_id"])
    frontier: list[UUID] = []
    for r in rows:
        nid = r["node_id"]
        if mastery[nid] >= 0.90:
            continue
        if mastery[nid] > 0.10 and mastery[nid] < 0.90:
            # low-conf mastered still not frontier
            if mastery[nid] >= 0.70:
                continue
        ps = parents.get(nid, [])
        if all(mastery.get(p, 0) >= 0.90 for p in ps):
            if mastery[nid] <= 0.10:
                frontier.append(nid)
    # If nothing diagnosed yet, treat roots as frontier
    if all(mastery[r["node_id"]] == 0 for r in rows):
        return [
            r["node_id"]
            for r in rows
            if not parents.get(r["node_id"])
        ]
    return frontier


@router.get("", response_model=list[PathSummaryOut])
def list_paths(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> list[PathSummaryOut]:
    rows = conn.execute(
        """
        SELECT lp.id, lp.title, lp.target_goal, lp.status,
               lp.deadline_date, lp.daily_budget_mins, lp.created_at,
               COUNT(pn.node_id)::int AS node_count
        FROM learning_paths lp
        LEFT JOIN path_nodes pn ON pn.path_id = lp.id
        WHERE lp.user_id = %s
        GROUP BY lp.id
        ORDER BY lp.updated_at DESC
        """,
        (user.id,),
    ).fetchall()
    out: list[PathSummaryOut] = []
    for r in rows:
        out.append(
            PathSummaryOut(
                path_id=r["id"],
                title=r["title"],
                target_goal=r["target_goal"],
                status=r["status"],
                deadline_date=r["deadline_date"].isoformat() if r["deadline_date"] else None,
                daily_budget_mins=r["daily_budget_mins"],
                node_count=r["node_count"],
                created_at=r["created_at"],
            )
        )
    return out


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path(
    path_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> Response:
    _require_owned_path(conn, path_id, user.id)
    conn.execute("DELETE FROM learning_paths WHERE id = %s AND user_id = %s", (path_id, user.id))
    conn.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/uploads/parse", response_model=UploadParseOut)
async def parse_upload(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    file: UploadFile = File(...),
) -> UploadParseOut:
    profile = conn.execute(
        "SELECT is_minor, guardian_consent_at FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    if profile and profile["is_minor"]:
        raise HTTPException(status_code=403, detail="Uploads disabled for minors")
    data = await file.read()
    try:
        text = extract_text_from_bytes(data, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")
    return UploadParseOut(text=text, char_count=len(text))


def _user_row(conn: psycopg.Connection, user_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        "SELECT is_minor, guardian_consent_at, locale FROM users WHERE id = %s", (user_id,)
    ).fetchone()
    return dict(row) if row else {}


@router.post("/profile", response_model=SubjectProfile)
def path_profile(
    body: PathProfileIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> SubjectProfile:
    """Pre-ingest subject profile for the wizard's confirm step (one fast model call)."""
    u = _user_row(conn, user.id)
    if u.get("is_minor") and (body.exam_markdown or body.source_markdowns):
        raise HTTPException(status_code=403, detail="Uploads disabled for minors")
    api_key = resolve_openrouter_key(conn, user.id) or settings.openrouter_api_key
    return SubjectProfile(
        **infer_subject_profile(
            body.goal_text.strip(),
            body.exam_markdown,
            body.source_markdowns,
            api_key=api_key,
            locale=u.get("locale") or "en",
        )
    )


@router.post("/placement/generate", response_model=PlacementGenerateOut)
def placement_generate(
    body: PlacementGenerateIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> PlacementGenerateOut:
    """Build a short goal-based placement exam (no PDF). Uses profile + prior paths."""
    api_key = resolve_openrouter_key(conn, user.id)
    profile = conn.execute(
        "SELECT birth_year, locale FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    prior_rows = conn.execute(
        """
        SELECT title, target_goal FROM learning_paths
        WHERE user_id = %s
        ORDER BY updated_at DESC
        LIMIT 8
        """,
        (user.id,),
    ).fetchall()
    prior_paths = []
    for r in prior_rows:
        label = (r["target_goal"] or r["title"] or "").strip()
        if label:
            prior_paths.append(label[:120])
    locale = (profile["locale"] if profile else None) or "en"
    subject = clamp_profile(body.subject_profile or MATH_PROFILE, goal=body.goal_text.strip(), locale=locale)
    try:
        qs = generate_placement_exam(
            goal_text=body.goal_text.strip(),
            api_key=api_key or settings.openrouter_api_key,
            count=5,
            birth_year=profile["birth_year"] if profile else None,
            locale=locale,
            prior_paths=prior_paths,
            profile=subject,
        )
    except PlacementError as e:
        raise HTTPException(status_code=503, detail="Placement exam unavailable — try again") from e
    return PlacementGenerateOut(questions=[PlacementQuestionOut(**q) for q in qs])


@router.post("/placement/grade", response_model=PlacementGradeOut)
def placement_grade(
    body: PlacementGradeIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> PlacementGradeOut:
    del user
    try:
        graded = grade_placement_exam(
            questions=[q.model_dump() for q in body.questions],
            answers=[a.model_dump() for a in body.answers],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid placement exam") from e
    return PlacementGradeOut(
        summary_markdown=graded["summary_markdown"],
        correct_count=int(graded["correct_count"]),
        total=int(graded["total"]),
        weak_skills=list(graded["weak_skills"]),
        strong_skills=list(graded["strong_skills"]),
    )


@router.post("/ingest", response_model=PathIngestOut)
def ingest_path(
    body: PathIngestIn,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> PathIngestOut:
    if not body.deadline_date and body.daily_budget_mins is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide deadline_date and/or daily_budget_mins",
        )
    profile = conn.execute(
        "SELECT is_minor, guardian_consent_at FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    if profile and profile["is_minor"] and profile["guardian_consent_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guardian consent required",
        )
    if profile and profile["is_minor"] and (
        body.exam_markdown or body.source_markdowns or body.optional_syllabus_markdown
    ):
        raise HTTPException(status_code=403, detail="Uploads disabled for minors")

    api_key = resolve_openrouter_key(conn, user.id)
    if not (settings.ai_on or api_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI or a BYO OpenRouter key is required to build a personalized path",
        )

    deadline: date | None = None
    if body.deadline_date:
        try:
            deadline = date.fromisoformat(body.deadline_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid deadline_date") from e

    exam = (body.exam_markdown or body.optional_syllabus_markdown or "").strip() or None
    sources = [s.strip() for s in body.source_markdowns if s and s.strip()][:5]

    goal = body.goal_text.strip()
    locale = _user_row(conn, user.id).get("locale") or "en"
    # The learner may edit categories/notation, but `allowed` is always re-decided server-side.
    inferred = infer_subject_profile(
        goal, exam, sources, api_key=api_key or settings.openrouter_api_key, locale=locale
    )
    subject = inferred
    if body.subject_profile:
        verdict = {"allowed": inferred["allowed"], "reason": inferred["reason"]}
        subject = clamp_profile({**body.subject_profile, **verdict}, goal=goal, locale=locale)
    if not subject["allowed"]:
        raise HTTPException(status_code=400, detail=subject["reason"] or "This goal can't be taught here")

    title = goal[:80]
    path = conn.execute(
        """
        INSERT INTO learning_paths (
            user_id, title, target_goal, deadline_date, daily_budget_mins, status, plan_context,
            subject_profile
        ) VALUES (%s, %s, %s, %s, %s, 'DRAFTING', '{}'::jsonb, %s)
        RETURNING id, status
        """,
        (
            user.id,
            title,
            goal,
            deadline,
            body.daily_budget_mins,
            Json(subject),
        ),
    ).fetchone()
    assert path is not None
    path_id = path["id"]
    conn.commit()

    reset_buffer(path_id)
    background_tasks.add_task(
        run_research_job,
        path_id=path_id,
        user_id=user.id,
        goal_text=body.goal_text.strip(),
        draft_titles=[],
        api_key=api_key,
        database_url=settings.database_url,
        exam_markdown=exam,
        source_markdowns=sources,
        use_corpus=body.use_corpus,
        subject_profile=subject,
    )

    return PathIngestOut(
        path_id=path_id,
        status="DRAFTING",
        initial_draft_nodes=[],
        stream_url=f"/api/v1/paths/{path_id}/stream",
    )


@router.get("/{path_id}", response_model=PathOut)
def get_path(
    path_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> PathOut:
    path = _require_owned_path(conn, path_id, user.id)
    rows = _path_nodes_with_mastery(conn, path_id, user.id)
    frontier = _compute_frontier_ids([dict(r) for r in rows], conn)
    fset = set(frontier)
    shown = {
        r["node_id"]: shown_build_status(
            r.get("build_status"),
            stale=bool(r.get("stale")),
            inflight=is_materialize_inflight(path_id, r["node_id"]),
        )
        for r in rows
    }
    nodes = [
        PathNodeOut(
            node_id=r["node_id"],
            slug=r["slug"],
            title=r["title"],
            sequence_index=r["sequence_index"],
            is_draft=r["is_draft"],
            content_ready=lesson_ready(
                item_count=int(r.get("verified_count") or 0), beats=r.get("lesson_beats")
            ),
            build_status=shown[r["node_id"]],
            build_error=r.get("build_error") if shown[r["node_id"]] == "FAILED" else None,
            p_mastery=float(r["p_mastery"]),
            label=_label_for(float(r["p_mastery"]), r["node_id"] in fset),
            primer_md=r.get("primer_md"),
            lesson_beats=list(r["lesson_beats"])
            if isinstance(r.get("lesson_beats"), list)
            else [],
            sources=r.get("sources") or [],
            source_attribution=r.get("source_attribution"),
            source_license=r.get("source_license"),
            source_url=r.get("source_url"),
        )
        for r in rows
    ]
    dd = path["deadline_date"]
    return PathOut(
        path_id=path["id"],
        title=path["title"],
        target_goal=path["target_goal"],
        status=path["status"],
        deadline_date=dd.isoformat() if dd else None,
        daily_budget_mins=path["daily_budget_mins"],
        nodes=nodes,
        frontier_node_ids=frontier,
        refining=path["status"] == "DRAFTING",
    )


def _replace_path_graph(
    conn: psycopg.Connection,
    *,
    path_id: UUID,
    user_id: UUID,
    goal_text: str,
    background_tasks: BackgroundTasks,
    exam_markdown: str | None = None,
    source_markdowns: list[str] | None = None,
    use_corpus: bool = True,
    subject_profile: dict[str, Any] | None = None,
) -> PathIngestOut:
    """Rebuild outline-only path via Deep Research (no seed)."""
    api_key = resolve_openrouter_key(conn, user_id)
    if not (settings.ai_on or api_key):
        raise HTTPException(
            status_code=400,
            detail="AI or a BYO OpenRouter key is required to rebuild a path",
        )

    title = goal_text.strip()[:80]
    conn.execute("DELETE FROM path_nodes WHERE path_id = %s", (path_id,))
    conn.execute(
        """
        UPDATE learning_paths
        SET title = %s, target_goal = %s, status = 'DRAFTING', updated_at = now()
        WHERE id = %s
        """,
        (title, goal_text.strip(), path_id),
    )
    conn.commit()

    reset_buffer(path_id)
    background_tasks.add_task(
        run_research_job,
        path_id=path_id,
        user_id=user_id,
        goal_text=goal_text.strip(),
        draft_titles=[],
        api_key=api_key,
        database_url=settings.database_url,
        exam_markdown=exam_markdown,
        source_markdowns=source_markdowns or [],
        use_corpus=use_corpus,
        subject_profile=subject_profile,
    )

    return PathIngestOut(
        path_id=path_id,
        status="DRAFTING",
        initial_draft_nodes=[],
        stream_url=f"/api/v1/paths/{path_id}/stream",
    )


@router.post("/{path_id}/improve", response_model=PathIngestOut)
def improve_path(
    path_id: UUID,
    body: PathImproveIn,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> PathIngestOut:
    """Merge an improvement prompt into the goal and rebuild the path graph."""
    path = _require_owned_path(conn, path_id, user.id)
    prompt = body.improvement_prompt.strip()
    combined = f"{path['target_goal'].strip()}\n\nImprove: {prompt}".strip()
    if len(combined) > 500:
        combined = combined[:500]
    ctx = path.get("plan_context") if isinstance(path.get("plan_context"), dict) else {}
    return _replace_path_graph(
        conn,
        path_id=path_id,
        user_id=user.id,
        goal_text=combined,
        background_tasks=background_tasks,
        exam_markdown=ctx.get("exam_digest") if isinstance(ctx, dict) else None,
        source_markdowns=list(ctx.get("source_digests") or []) if isinstance(ctx, dict) else [],
        use_corpus=bool(ctx.get("use_corpus", True)) if isinstance(ctx, dict) else True,
        subject_profile=path.get("subject_profile"),
    )


@router.post("/{path_id}/rebuild", response_model=PathIngestOut)
def rebuild_path(
    path_id: UUID,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    body: PathRebuildIn = PathRebuildIn(),
) -> PathIngestOut:
    """Redo path drafting from the current (or provided) goal; resets node mastery on the path."""
    path = _require_owned_path(conn, path_id, user.id)
    goal = (body.goal_text or path["target_goal"]).strip()
    ctx = path.get("plan_context") if isinstance(path.get("plan_context"), dict) else {}
    exam = ctx.get("exam_digest") if isinstance(ctx, dict) else None
    sources = ctx.get("source_digests") if isinstance(ctx, dict) else None
    use_corpus = bool(ctx.get("use_corpus", True)) if isinstance(ctx, dict) else True
    return _replace_path_graph(
        conn,
        path_id=path_id,
        user_id=user.id,
        goal_text=goal,
        background_tasks=background_tasks,
        exam_markdown=exam,
        source_markdowns=list(sources) if sources else [],
        use_corpus=use_corpus,
        subject_profile=path.get("subject_profile"),
    )


def _sse_format(event_id: int, event: str, data: dict[str, Any]) -> str:
    return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/{path_id}/stream")
def stream_path(
    path_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    _require_owned_path(conn, path_id, user.id)
    start_after = 0
    if last_event_id:
        try:
            start_after = int(last_event_id)
        except ValueError:
            start_after = 0

    def gen() -> Iterator[str]:
        cursor = start_after
        idle_rounds = 0
        while True:
            batch = wait_for_events(path_id, cursor, timeout_s=0.4)
            if not batch:
                idle_rounds += 1
                if is_complete(path_id) or idle_rounds > 75:
                    if not is_complete(path_id):
                        append_event(
                            path_id,
                            "graph_failed",
                            {
                                "total_nodes": 0,
                                "timeout": True,
                                "error": "Path draft timed out waiting for research",
                            },
                        )
                        batch = get_events_after(path_id, cursor)
                    else:
                        break
                else:
                    continue
            idle_rounds = 0
            for ev in batch:
                cursor = ev["id"]
                yield _sse_format(ev["id"], ev["event"], ev["data"])
                if ev["event"] in ("graph_complete", "graph_failed"):
                    return

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{path_id}/nodes/{node_id}/materialize", response_model=MaterializeOut)
def materialize_node(
    path_id: UUID,
    node_id: UUID,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> MaterializeOut:
    del background_tasks
    _require_owned_path(conn, path_id, user.id)
    r = node_readiness(conn, path_id, node_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Node not on path")

    stream_url = f"/api/v1/paths/{path_id}/nodes/{node_id}/materialize/stream"
    api_key = resolve_openrouter_key(conn, user.id)

    def _out(status_label: str) -> MaterializeOut:
        return MaterializeOut(
            path_id=path_id,
            node_id=node_id,
            status=status_label,
            stream_url=stream_url,
            item_count=r["item_count"],
            build_status=r["status"],
            teach_ready=r["teach_ready"],
        )

    def _prefetch_next() -> None:
        prefetch_next_path_node(
            conn, path_id=path_id, current_node_id=node_id, user_id=user.id, api_key=api_key
        )

    if r["ready"]:
        _prefetch_next()
        return _out("READY")

    if not (settings.ai_on or api_key):
        raise HTTPException(
            status_code=400,
            detail="AI or BYO key required to generate practice content",
        )

    # Join a live build instead of restarting it (path prefetch + session open race).
    # A BUILDING row with no live job (restart, or older than the stale window) is re-queued.
    if not r["building"]:
        schedule_materialize_node(
            path_id=path_id,
            node_id=node_id,
            user_id=user.id,
            api_key=api_key or settings.openrouter_api_key,
        )
    return _out("STARTED")


@router.get("/{path_id}/nodes/{node_id}/materialize/stream")
def materialize_stream(
    path_id: UUID,
    node_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    _require_owned_path(conn, path_id, user.id)
    key = materialize_buffer_key(path_id, node_id)
    start_after = 0
    if last_event_id:
        try:
            start_after = int(last_event_id)
        except ValueError:
            start_after = 0

    def gen() -> Iterator[str]:
        cursor = start_after
        idle_rounds = 0
        # ~4 minutes of quiet before timeout (LLM item gen can be slow)
        max_idle = 600
        while True:
            batch = wait_for_events(key, cursor, timeout_s=0.4)
            if not batch:
                idle_rounds += 1
                if is_complete(key):
                    # Drain any events that arrived as we marked complete
                    batch = get_events_after(key, cursor)
                    if not batch:
                        return
                elif idle_rounds > max_idle:
                    yield _sse_format(
                        cursor + 1,
                        "materialize_failed",
                        {"error": "timeout"},
                    )
                    return
                else:
                    continue
            idle_rounds = 0
            for ev in batch:
                cursor = ev["id"]
                yield _sse_format(ev["id"], ev["event"], ev["data"])
                if ev["event"] in ("node_ready", "materialize_failed"):
                    return

    return StreamingResponse(gen(), media_type="text/event-stream")


def _probe_item(conn: psycopg.Connection, node_id: UUID) -> dict[str, Any] | None:
    # Quick single-answer graders first (every widget renders, but a probe should be fast);
    # self-rated flashcards and key-term-graded free text are the weakest evidence, so last.
    return conn.execute(
        """
        SELECT id, statement_latex, prompt_md, parts, steps, genui_plan FROM items
        WHERE node_id = %s AND status = 'VERIFIED'
        ORDER BY (grader IN ('flashcards', 'rubric_llm')) ASC,
                 (grader IN ('match', 'order', 'categorize', 'cloze')) ASC, created_at ASC, id ASC
        LIMIT 1
        """,
        (node_id,),
    ).fetchone()


def _nodes_with_verified_items(
    conn: psycopg.Connection, path_id: UUID
) -> list[dict[str, Any]]:
    """Path nodes that can be probed (need ≥5 VERIFIED items — Doc 05 / US-6.6)."""
    return conn.execute(
        """
        SELECT n.id, n.element_interactivity_weight
        FROM path_nodes pn
        JOIN knowledge_nodes n ON n.id = pn.node_id
        WHERE pn.path_id = %s
          AND pn.is_draft = FALSE
          AND (
            SELECT COUNT(*) FROM items i
            WHERE i.node_id = n.id AND i.status = 'VERIFIED'
          ) >= 5
        ORDER BY pn.sequence_index
        """,
        (path_id,),
    ).fetchall()


def _probe_response(
    conn: psycopg.Connection,
    node_id: UUID,
    probe_index: int,
) -> DiagnosticProbeOut:
    item = _probe_item(conn, node_id)
    if item is None:
        raise HTTPException(status_code=500, detail="No verified item for probe node")
    title = conn.execute(
        "SELECT title, subject_profile->>'notation' AS notation FROM knowledge_nodes WHERE id = %s", (node_id,)
    ).fetchone()
    parts = _load_parts(dict(item))
    return DiagnosticProbeOut(
        done=False,
        probe_index=probe_index,
        node_id=node_id,
        node_title=title["title"] if title else None,
        item_id=item["id"],
        statement_latex=item["statement_latex"],
        prompt_md=hide_cloze(parts, item.get("prompt_md")),
        parts=[SessionPartOut(**public_props(p)) for p in parts[:1]],
        notation=title["notation"] if title else None,
    )


def _pick_probe_with_item(
    conn: psycopg.Connection, g: DiagnosticGraph
) -> UUID | None:
    """select_probe, skipping UNKNOWN nodes that lack a VERIFIED item."""
    tried: set[UUID] = set()
    while True:
        probe = select_probe(g)
        if probe is None or probe in tried:
            return None
        if _probe_item(conn, probe) is not None:
            return probe
        # Can't probe this node — mark NOT_MASTERED so selection moves on.
        tried.add(probe)
        g.status[probe] = NodeStatus.NOT_MASTERED


@router.post("/{path_id}/diagnostic/start", response_model=DiagnosticProbeOut)
def diagnostic_start(
    path_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> DiagnosticProbeOut:
    _require_owned_path(conn, path_id, user.id)
    path_nodes = _nodes_with_verified_items(conn, path_id)
    if not path_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No practice-ready nodes yet. Open a Planned skill to generate content first.",
        )

    ids = [r["id"] for r in path_nodes]
    edges = conn.execute(
        """
        SELECT parent_id, child_id FROM knowledge_edges
        WHERE edge_type = 'PREREQUISITE_OF'
          AND parent_id = ANY(%s) AND child_id = ANY(%s)
        """,
        (ids, ids),
    ).fetchall()

    # Reset mastery for practice-ready path nodes for a fresh diagnostic
    for r in path_nodes:
        upsert_p_mastery(conn, user_id=user.id, node_id=r["id"], p_mastery=0.0)

    g = build_diagnostic_graph([dict(r) for r in path_nodes], [dict(e) for e in edges])
    store_session(user.id, path_id, g)
    probe = _pick_probe_with_item(conn, g)
    if probe is None:
        raise HTTPException(status_code=500, detail="No probe available")
    conn.commit()
    return _probe_response(conn, probe, probe_index=1)


@router.post("/{path_id}/diagnostic/answer", response_model=DiagnosticProbeOut)
def diagnostic_answer(
    path_id: UUID,
    body: DiagnosticAnswerIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> DiagnosticProbeOut:
    _require_owned_path(conn, path_id, user.id)
    g = get_session(user.id, path_id)
    if g is None:
        raise HTTPException(status_code=400, detail="Start diagnostic first")

    item = conn.execute(
        "SELECT id, node_id, steps, genui_plan, parts FROM items WHERE id = %s AND status = 'VERIFIED'",
        (body.item_id,),
    ).fetchone()
    if item is None or item["node_id"] != body.node_id:
        raise HTTPException(status_code=400, detail="Invalid item for probe")

    answer = body.answer or {}
    part = (_load_parts(dict(item)) or [{}])[0]
    steps = item["steps"]
    if isinstance(steps, str):
        steps = json.loads(steps)
    if part.get("grader") == "sympy" and steps:
        # Probe = the whole problem: compare against the final step, not part 0.
        final = steps[-1]
        latex = str(answer.get("latex") or "")[:500]
        result = evaluate_step_safe(latex, final.get("sympy") or final.get("latex") or "") if latex else {}
        correct = bool(result.get("is_equivalent"))
    else:
        # ponytail: no API key here, so a FreeResponse probe is graded by key terms (no LLM cost
        # outside a session's cap). Upgrade: open a session_logs row and pass the learner's key.
        correct = grade(str(part.get("grader") or ""), part.get("answer_spec"), answer).is_success

    F = apply_answer(g, body.node_id, correct=correct, latency_ms=body.latency_ms)
    if correct and F < FLUENCY_PASS:
        mark_low_conf(user.id, path_id, body.node_id)

    persist_graph_mastery(
        conn,
        user_id=user.id,
        g=g,
        low_conf_nodes=get_low_conf(user.id, path_id),
    )

    next_id = _pick_probe_with_item(conn, g)
    if should_stop(g) or next_id is None:
        finalize_unknown_as_not_mastered(g)
        persist_graph_mastery(
            conn,
            user_id=user.id,
            g=g,
            low_conf_nodes=get_low_conf(user.id, path_id),
        )
        conn.commit()
        return DiagnosticProbeOut(
            done=True,
            probe_index=g.probe_count,
            frontier_node_ids=frontier_nodes(g),
        )

    conn.commit()
    return _probe_response(conn, next_id, probe_index=g.probe_count + 1)
