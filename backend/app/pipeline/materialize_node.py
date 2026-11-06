"""On-demand lesson build: research brief → design → primer ‖ items → bind → node_ready,
then a background review (critic + SymPy demo check, flagged-problem swap).

``build_lesson_content`` is DB-free (used by scripts/eval_lessons.py); ``run_materialize_node``
wraps it with persistence, durable build_status and SSE progress events.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Callable, Iterator
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.config import settings
from app.graders.legacy import legacy_parts
from app.pipeline.item_gen import generate_items_for_node
from app.pipeline.research_brief import attribution_from, brief_digest, build_research_brief
from app.pipeline.sse_buffer import append_event, get_events_after, is_complete, reset_buffer
from app.services.component_catalog import scrub_urls
from app.services.lesson_beats import (
    LessonDesignError,
    bind_design,
    cited_urls,
    critique_lesson,
    design_lesson,
    plan_item_for_spec,
)
from app.services.llm import chat_json
from app.services.path_draft import OutlineError
from app.services.subject_profile import MATH_PROFILE, clamp_profile, is_math, profile_prompt
from app.telemetry import span

_log = logging.getLogger(__name__)


class LessonIncomplete(RuntimeError):
    """Fewer verified items / beats than a playable lesson needs after repair."""


_SAFE = {
    OutlineError: {
        "en": "We couldn't plan this topic right now. Please try again.",
        "es": "No pudimos planificar este tema ahora. Inténtalo de nuevo.",
    },
    LessonDesignError: {
        "en": "We couldn't design this lesson right now. Please try again.",
        "es": "No pudimos diseñar esta lección ahora. Inténtalo de nuevo.",
    },
    LessonIncomplete: {
        "en": "We couldn't write enough practice questions for this lesson. Please try again.",
        "es": "No pudimos crear suficientes ejercicios para esta lección. Inténtalo de nuevo.",
    },
}
_SAFE_DEFAULT = {
    "en": "Something went wrong while building this. Please try again.",
    "es": "Algo salió mal al prepararlo. Inténtalo de nuevo.",
}


def learner_safe(e: BaseException, lang: str = "en") -> str:
    """Short reason a learner may see; the raw exception only goes to the log."""
    _log.error("build failed: %s", e, exc_info=e)
    texts = next((v for t, v in _SAFE.items() if isinstance(e, t)), _SAFE_DEFAULT)
    return texts["es" if str(lang).lower().startswith("es") else "en"]

ITEM_TARGET = 5
MIN_BEATS = 4
STALE_BUILD_MINUTES = 10

# ponytail: in-process pool + in-memory inflight set; one API process. Multi-worker deploys
# need a shared queue (Postgres SKIP LOCKED / Redis) — build_status already lives in the DB.
_executor = ThreadPoolExecutor(max_workers=max(1, settings.lesson_workers), thread_name_prefix="lesson")
_job_lock = threading.Lock()
_inflight_jobs: set[str] = set()

Emit = Callable[[str, dict[str, Any]], None]


def materialize_buffer_key(path_id: UUID, node_id: UUID) -> str:
    return f"mat:{path_id}:{node_id}"


def is_materialize_inflight(path_id: UUID, node_id: UUID) -> bool:
    with _job_lock:
        return materialize_buffer_key(path_id, node_id) in _inflight_jobs


def _claim(key: str) -> bool:
    with _job_lock:
        if key in _inflight_jobs:
            return False
        _inflight_jobs.add(key)
        return True


def _release(key: str) -> None:
    with _job_lock:
        _inflight_jobs.discard(key)


# ---------------------------------------------------------------------------
# Readiness — the single rule used by api_paths, api_session and prefetch
# ---------------------------------------------------------------------------


def lesson_ready(*, item_count: int, beats: Any) -> bool:
    """Ready: ≥5 verified items and ≥4 beats with every problem beat bound to an item."""
    if item_count < ITEM_TARGET:
        return False
    if not isinstance(beats, list) or len(beats) < MIN_BEATS:
        return False
    return not any(
        isinstance(b, dict) and b.get("type") == "problem" and (b.get("pending") or not b.get("item_id"))
        for b in beats
    )


def has_teach_beats(beats: Any) -> bool:
    return isinstance(beats, list) and any(
        isinstance(b, dict) and b.get("type") != "problem" for b in beats
    )


_READINESS_SQL = """
    SELECT pn.node_id, pn.is_draft, pn.sequence_index, pn.build_status, pn.build_error,
           COALESCE(pn.build_started_at < NOW() - make_interval(mins => %s), TRUE) AS stale,
           (SELECT COUNT(*)::int FROM items i
            WHERE i.node_id = pn.node_id AND i.status = 'VERIFIED') AS item_count,
           n.lesson_beats
    FROM path_nodes pn
    JOIN knowledge_nodes n ON n.id = pn.node_id
    WHERE pn.path_id = %s
"""


def shown_build_status(status: str | None, *, stale: bool, inflight: bool) -> str | None:
    # ponytail: a BUILDING row past STALE_BUILD_MINUTES with no live job (aborted build, API
    # restart) is reported as FAILED so the UI offers Retry; slower builds than that also flip.
    return "FAILED" if status == "BUILDING" and stale and not inflight else status


def _readiness_from_row(row: dict[str, Any], path_id: UUID) -> dict[str, Any]:
    beats = row.get("lesson_beats") or []
    count = int(row.get("item_count") or 0)
    # Nodes are shared by slug: another path may already have built this lesson.
    ready = lesson_ready(item_count=count, beats=beats)
    inflight = is_materialize_inflight(path_id, row["node_id"])
    status = "READY" if ready else str(
        shown_build_status(row.get("build_status"), stale=bool(row.get("stale")), inflight=inflight)
        or "PLANNED"
    )
    buf = materialize_buffer_key(path_id, row["node_id"])
    building = inflight or (
        status in ("BUILDING", "TEACH_READY")
        and not row.get("stale")
        and bool(get_events_after(buf, 0))
        and not is_complete(buf)
    )
    return {
        "node_id": row["node_id"],
        "ready": ready,
        "teach_ready": (not ready) and has_teach_beats(beats),
        "building": (not ready) and building,
        "status": status,
        "error": row.get("build_error"),
        "item_count": count,
        "beats": beats if isinstance(beats, list) else [],
        "sequence_index": int(row.get("sequence_index") or 0),
        "is_draft": bool(row.get("is_draft")),
    }


def node_readiness(conn: psycopg.Connection, path_id: UUID, node_id: UUID) -> dict[str, Any] | None:
    row = conn.execute(
        _READINESS_SQL + " AND pn.node_id = %s", (STALE_BUILD_MINUTES, path_id, node_id)
    ).fetchone()
    return _readiness_from_row(dict(row), path_id) if row else None


def path_readiness(conn: psycopg.Connection, path_id: UUID) -> list[dict[str, Any]]:
    rows = conn.execute(
        _READINESS_SQL + " ORDER BY pn.sequence_index ASC", (STALE_BUILD_MINUTES, path_id)
    ).fetchall()
    return [_readiness_from_row(dict(r), path_id) for r in rows]


def first_unready_node(conn: psycopg.Connection, path_id: UUID) -> UUID | None:
    return next((r["node_id"] for r in path_readiness(conn, path_id) if not r["ready"]), None)


def node_content_incomplete(conn: psycopg.Connection, path_id: UUID, node_id: UUID) -> bool:
    r = node_readiness(conn, path_id, node_id)
    return bool(r and not r["ready"])


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------


def schedule_materialize_node(
    *,
    path_id: UUID,
    node_id: UUID,
    user_id: UUID,
    api_key: str,
    database_url: str | None = None,
) -> bool:
    """Queue a build on the bounded lesson pool. False if already queued/running."""
    key = materialize_buffer_key(path_id, node_id)
    if not _claim(key):
        return False
    reset_buffer(key)

    def job() -> None:
        try:
            _run_materialize_body(
                path_id=path_id,
                node_id=node_id,
                user_id=user_id,
                api_key=api_key,
                database_url=database_url or settings.database_url,
                key=key,
            )
        finally:
            _release(key)

    _executor.submit(job)
    return True


def prefetch_next_path_node(
    conn: psycopg.Connection,
    *,
    path_id: UUID,
    current_node_id: UUID,
    user_id: UUID,
    api_key: str | None,
) -> UUID | None:
    """Keep one node ahead warm. Returns next node_id if a build was queued."""
    key = api_key or (settings.openrouter_api_key if settings.ai_on else "")
    if not key:
        return None
    cur = node_readiness(conn, path_id, current_node_id)
    if cur is None:
        return None
    nxt = conn.execute(
        "SELECT node_id FROM path_nodes WHERE path_id = %s AND sequence_index = %s",
        (path_id, cur["sequence_index"] + 1),
    ).fetchone()
    if nxt is None:
        return None
    r = node_readiness(conn, path_id, nxt["node_id"])
    if r is None or r["ready"] or r["building"]:
        return None
    queued = schedule_materialize_node(
        path_id=path_id, node_id=nxt["node_id"], user_id=user_id, api_key=key
    )
    return nxt["node_id"] if queued else None


def run_materialize_node(
    *,
    path_id: UUID,
    node_id: UUID,
    user_id: UUID,
    api_key: str,
    database_url: str | None = None,
) -> None:
    """Synchronous build (idempotent via the inflight set)."""
    key = materialize_buffer_key(path_id, node_id)
    if not _claim(key):
        return
    try:
        _run_materialize_body(
            path_id=path_id,
            node_id=node_id,
            user_id=user_id,
            api_key=api_key,
            database_url=database_url or settings.database_url,
            key=key,
        )
    finally:
        _release(key)


# ---------------------------------------------------------------------------
# DB-free lesson build
# ---------------------------------------------------------------------------


@contextmanager
def _stage(name: str, timings: dict[str, float]) -> Iterator[None]:
    t0 = time.perf_counter()
    with span(f"materialize.{name}"):
        try:
            yield
        finally:
            timings[name] = round(time.perf_counter() - t0, 2)


def build_lesson_content(
    *,
    title: str,
    context: str,
    api_key: str,
    description: str = "",
    brief: dict[str, Any] | None = None,
    primer_md: str | None = None,
    existing_items: list[dict[str, Any]] | None = None,
    on_event: Emit | None = None,
    on_teach_ready: Callable[[dict[str, Any], list[dict[str, Any]]], None] | None = None,
    profile: dict[str, Any] | None = None,
    use_corpus: bool = True,
) -> dict[str, Any]:
    """Build one lesson up to node_ready. Returns brief, primer, beats, items (new + existing),
    specs, timings; ``review_lesson_content`` runs afterwards.

    New items carry ``new=True`` and a fresh ``id``; nothing is persisted here.
    Raises ``LessonDesignError`` when no design survives repair (no static lesson).
    """
    profile = profile or MATH_PROFILE
    emit = on_event or (lambda _e, _d: None)
    timings: dict[str, float] = {}
    existing = list(existing_items or [])

    brief_cached = brief is not None
    with _stage("research", timings):
        if brief is None:
            brief = build_research_brief(
                title=title, context=context, api_key=api_key, description=description,
                profile=profile, use_corpus=use_corpus,
            )
    emit("research_ready", {"sources": len(brief.get("sources") or []), "cached": brief_cached})

    with _stage("design", timings):
        design = design_lesson(
            title=title, brief=brief, context=context, api_key=api_key, primer_md=primer_md, profile=profile
        )
    emit("design_ready", {"beats": len(design["beats"]), "problems": len(design["specs"])})
    if design["missing_widgets"]:
        _log.warning("widget_requested_missing skill=%r widgets=%s", title, design["missing_widgets"])
    if on_teach_ready:
        on_teach_ready(brief, design["beats"])

    need = max(0, ITEM_TARGET - len(existing))
    shown = [b["demo_steps"][0]["latex"] for b in design["beats"] if b.get("demo_steps")]
    item_context = (
        f"{title}\nResearch brief:\n{brief_digest(brief, 1200)}\nLearner context:\n{context[:800]}"
        + (f"\nDo NOT reuse these worked-example expressions: {'; '.join(shown)[:300]}" if shown else "")
    )
    with _stage("generate", timings):
        with ThreadPoolExecutor(max_workers=2) as ex:
            primer_f = (
                ex.submit(_generate_primer, title, context, api_key, brief, profile)
                if not primer_md
                else None
            )
            items_f = ex.submit(
                generate_items_for_node,
                node_title=item_context,
                api_key=api_key,
                count=need,
                specs=design["specs"],
                avoid=shown,
                profile=profile,
            )
            new_items = items_f.result()
            primer = primer_f.result() if primer_f else primer_md
    for it in new_items:
        it["id"] = str(uuid4())
        it["new"] = True
    emit("item_verified", {"count": len(existing) + len(new_items), "target": ITEM_TARGET})
    if primer and not primer_md:
        emit("primer_ready", {"chars": len(primer)})

    # Spec-matched new items bind first; existing (legacy) items fill remaining beats.
    all_items = new_items + existing
    with _stage("bind", timings):
        beats = bind_design(design["beats"], design["specs"], all_items)
    return {
        "brief": brief,
        "brief_cached": brief_cached,
        "primer_md": primer,
        "beats": beats,
        "items": all_items,
        "specs": design["specs"],
        "missing_widgets": design["missing_widgets"],
        "visuals_dropped": design.get("visuals_dropped") or [],
        "item_context": item_context,
        "shown": shown,
        "timings": timings,
        "profile": profile,
    }


def _text_of(item: dict[str, Any]) -> str:
    return str(item.get("statement_latex") or item.get("prompt_md") or "")


def _is_generic(item: dict[str, Any]) -> bool:
    """§6.2 item (no LaTeX statement): its stored parts are the source of truth."""
    return not item.get("statement_latex") and bool(item.get("parts"))


def review_lesson_content(
    *,
    title: str,
    out: dict[str, Any],
    api_key: str,
    locked_item_ids: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Post-ready review of a built lesson (``out`` from ``build_lesson_content``). DB-free.

    Critic + SymPy demo check repair teach beats/primer; problems the critic flags are
    regenerated to their spec unless the item already has attempts (``locked_item_ids``).
    Returns ``{beats, primer_md, new_items, review}``.
    """
    t0 = time.perf_counter()
    items_by_id = {str(i["id"]): i for i in out["items"]}
    with span("materialize.review"):
        crit = critique_lesson(
            title=title,
            brief=out["brief"],
            primer_md=out["primer_md"],
            beats=out["beats"],
            items_by_id=items_by_id,
            api_key=api_key,
            profile=out.get("profile"),
        )
    beats = [dict(b) for b in crit["beats"]]
    specs = out.get("specs") or []
    avoid = list(out.get("shown") or []) + [_text_of(i) for i in out["items"]]
    new_items: list[dict[str, Any]] = []
    swapped: list[dict[str, Any]] = []
    for bp in crit["bad_problems"]:
        beat = beats[bp["index"]]
        old_id = str(beat.get("item_id") or "")
        if not old_id or old_id in locked_item_ids:
            continue
        si = beat.get("spec_index")
        spec = specs[si] if isinstance(si, int) and 0 <= si < len(specs) else None
        got = generate_items_for_node(
            node_title=f"{out.get('item_context') or title}\nThe previous problem was rejected: {bp['reason']}",
            api_key=api_key,
            count=1,
            specs=[spec] if spec else None,
            avoid=avoid,
            profile=out.get("profile"),
        )
        if not got:
            continue
        item = {**got[0], "id": str(uuid4()), "new": True}
        plan = plan_item_for_spec(spec, item)
        beat = {k: v for k, v in beat.items() if k != "visual"}  # old item's picture
        beats[bp["index"]] = {
            **beat,
            "item_id": item["id"],
            "genui_plan": plan,
            **({"visual": item["visual"]} if item.get("visual") else {}),
        }
        avoid.append(_text_of(item))
        new_items.append(item)
        swapped.append({"index": bp["index"], "old_item_id": old_id, "new_item_id": item["id"]})
    review = {
        k: crit[k]
        for k in ("score", "issues", "math_errors", "sympy_flags", "bad_problems", "demos_dropped", "repaired", "error")
    }
    review["problems_swapped"] = swapped
    review["review_s"] = round(time.perf_counter() - t0, 2)
    return {"beats": beats, "primer_md": crit["primer_md"], "new_items": new_items, "review": review}


# ---------------------------------------------------------------------------
# Persistence wrapper
# ---------------------------------------------------------------------------


def _set_status(
    conn: psycopg.Connection, path_id: UUID, node_id: UUID, status: str, error: str | None = None
) -> None:
    conn.execute(
        """
        UPDATE path_nodes
        SET build_status = %s,
            build_error = %s,
            build_started_at = CASE WHEN %s = 'BUILDING' THEN NOW() ELSE build_started_at END,
            is_draft = CASE WHEN %s = 'READY' THEN FALSE ELSE is_draft END
        WHERE path_id = %s AND node_id = %s
        """,
        (status, error, status, status, path_id, node_id),
    )
    conn.commit()


def _run_materialize_body(
    *,
    path_id: UUID,
    node_id: UUID,
    user_id: UUID,
    api_key: str,
    database_url: str,
    key: str,
) -> None:
    def emit(event: str, data: dict[str, Any]) -> None:
        append_event(key, event, data)

    emit("materialize_started", {"node_id": str(node_id)})
    conn = psycopg.connect(database_url, row_factory=dict_row)
    lang = "en"
    try:
        pn = conn.execute(
            """
            SELECT n.title, n.description, n.primer_md, n.research_brief,
                   COALESCE(n.research_brief_at > NOW() - make_interval(days => %s), FALSE)
                     AS brief_fresh,
                   lp.plan_context, n.subject_profile, lp.subject_profile AS path_profile
            FROM path_nodes pn
            JOIN knowledge_nodes n ON n.id = pn.node_id
            JOIN learning_paths lp ON lp.id = pn.path_id
            WHERE pn.path_id = %s AND pn.node_id = %s AND lp.user_id = %s
            """,
            (settings.research_brief_ttl_days, path_id, node_id, user_id),
        ).fetchone()
        if pn is None:
            emit("materialize_failed", {"error": "Node not on path"})
            return

        r = node_readiness(conn, path_id, node_id)
        if r and r["ready"]:
            _set_status(conn, path_id, node_id, "READY")
            emit("beats_ready", {"count": len(r["beats"]), "cached": True})
            emit("node_ready", {"node_id": str(node_id), "item_count": r["item_count"], "cached": True})
            return

        _set_status(conn, path_id, node_id, "BUILDING")
        ctx = pn["plan_context"] if isinstance(pn["plan_context"], dict) else {}
        profile = clamp_profile(
            pn.get("subject_profile") or pn.get("path_profile") or MATH_PROFILE, goal=str(pn["title"])
        )
        lang = profile["instruction_language"]
        key_or = api_key or settings.openrouter_api_key
        existing = _existing_items(conn, node_id)

        def on_teach_ready(brief: dict[str, Any], beats: list[dict[str, Any]]) -> None:
            # Learner can start reading while problems are still generated.
            conn.execute(
                "UPDATE knowledge_nodes SET lesson_beats = %s WHERE id = %s",
                (Json(beats), node_id),
            )
            _set_status(conn, path_id, node_id, "TEACH_READY")
            emit("teach_ready", {"beats": len(beats)})
            prefetch_next_path_node(
                conn, path_id=path_id, current_node_id=node_id, user_id=user_id, api_key=key_or
            )

        out = build_lesson_content(
            title=str(pn["title"]),
            description=str(pn.get("description") or ""),
            context=_context_blob(ctx),
            api_key=key_or,
            brief=pn["research_brief"] if _reusable_brief(pn, profile) else None,
            primer_md=pn.get("primer_md"),
            existing_items=existing,
            on_event=emit,
            on_teach_ready=on_teach_ready,
            profile=profile,
            use_corpus=bool(ctx.get("use_corpus", True)),
        )
        ready = _persist(conn, path_id=path_id, node_id=node_id, ctx=ctx, out=out, emit=emit, lang=lang)
        if ready:
            # ponytail: inline on the build thread (keeps the node in-flight a bit longer);
            # move to its own queue if reviews ever need to outlive the process.
            try:
                _store_review(conn, node_id=node_id, title=str(pn["title"]), out=out, api_key=key_or, emit=emit)
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                _log.exception("lesson review failed node=%s", node_id)
                conn.execute(
                    "UPDATE knowledge_nodes SET lesson_review = COALESCE(lesson_review, '{}'::jsonb) || %s WHERE id = %s",
                    (Json({"status": "failed", "error": str(e)[:300]}), node_id),
                )
                conn.commit()
    except Exception as e:  # noqa: BLE001
        reason = learner_safe(e, lang)
        try:
            conn.rollback()
            _set_status(conn, path_id, node_id, "FAILED", reason)
        except Exception:  # noqa: BLE001
            pass
        emit("materialize_failed", {"error": reason})
    finally:
        conn.close()


def _reusable_brief(pn: dict[str, Any], profile: dict[str, Any]) -> bool:
    """Fresh cached brief; a non-math one must also carry web citations (else re-research)."""
    brief = pn.get("research_brief")
    if not (pn.get("brief_fresh") and brief):
        return False
    return is_math(profile) or any(s.get("kind") == "web" for s in brief.get("sources") or [])


def _existing_items(conn: psycopg.Connection, node_id: UUID) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT i.id, i.statement_latex, i.prompt, i.steps, i.parts, i.prompt_md,
               EXISTS (SELECT 1 FROM attempts a WHERE a.item_id = i.id) AS has_attempts
        FROM items i
        WHERE i.node_id = %s AND i.status = 'VERIFIED'
        ORDER BY i.created_at ASC, i.id ASC
        """,
        (node_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["original_steps"] = d["steps"]
        out.append(d)
    return out


def _persist(
    conn: psycopg.Connection,
    *,
    path_id: UUID,
    node_id: UUID,
    ctx: dict[str, Any],
    out: dict[str, Any],
    emit: Emit,
    lang: str = "en",
) -> bool:
    """One transaction: new items, plan/step updates, beats, primer, brief, READY.

    Returns True when the node is READY (the background review then runs).
    """
    items = out["items"]
    for it in items:
        plan = it.get("genui_plan")
        if it.get("new"):
            _insert_item(conn, node_id, it, cited_urls(out["brief"]))
        elif plan and _is_generic(it):
            conn.execute("UPDATE items SET genui_plan = %s WHERE id = %s", (Json(plan), it["id"]))
        elif plan:
            # bind_design only collapses steps for items without attempts (frozen otherwise).
            steps_changed = it["steps"] != it.get("original_steps") and not it.get("has_attempts")
            parts, grader = legacy_parts(it["steps"], plan, it["id"])
            conn.execute(
                """
                UPDATE items SET genui_plan = %s, steps = CASE WHEN %s THEN %s ELSE steps END,
                  parts = %s, grader = %s
                WHERE id = %s
                """,
                (Json(plan), steps_changed, Json(it["steps"]), Json(parts), grader, it["id"]),
            )
    beats = out["beats"]
    brief = out["brief"]
    conn.execute(
        """
        UPDATE knowledge_nodes
        SET lesson_beats = %s,
            primer_md = COALESCE(primer_md, %s),
            source_attribution = COALESCE(source_attribution, %s),
            research_brief = %s,
            research_brief_at = CASE WHEN %s THEN research_brief_at ELSE NOW() END,
            lesson_review = %s
        WHERE id = %s
        """,
        (
            Json(beats),
            out["primer_md"],
            attribution_from(brief, ctx.get("attribution") or "Pegazus research + learner materials"),
            Json(brief),
            out["brief_cached"],
            Json({"status": "pending", "missing_widgets": out["missing_widgets"], "timings": out["timings"]}),
            node_id,
        ),
    )
    count = len(items)
    if lesson_ready(item_count=count, beats=beats):
        conn.execute(
            """
            UPDATE path_nodes SET is_draft = FALSE, build_status = 'READY', build_error = NULL
            WHERE path_id = %s AND node_id = %s
            """,
            (path_id, node_id),
        )
        conn.commit()
        emit("beats_ready", {"count": len(beats)})
        emit("node_ready", {"node_id": str(node_id), "item_count": count, "timings": out["timings"]})
        return True
    # Keep verified items so a retry only generates the shortfall.
    err = learner_safe(LessonIncomplete(f"items={count}, beats={len(beats)}"), lang)
    conn.execute(
        "UPDATE path_nodes SET build_status = 'FAILED', build_error = %s WHERE path_id = %s AND node_id = %s",
        (err, path_id, node_id),
    )
    conn.commit()
    emit("materialize_failed", {"error": err, "item_count": count})
    return False


def _insert_item(
    conn: psycopg.Connection, node_id: UUID, it: dict[str, Any], urls: set[str] | frozenset[str] = frozenset()
) -> None:
    plan = it.get("genui_plan")
    # Rendered item text may only link research citations (Doc 10 R4); answer_spec never renders.
    # ponytail: a URL inside a code part's props (e.g. a string literal) is stripped too.
    it = {**it, **scrub_urls({k: it.get(k) for k in ("prompt", "prompt_md", "explanation_md")}, urls)}
    if _is_generic(it):
        parts = [{**p, "props": scrub_urls(p.get("props") or {}, urls)} for p in it["parts"]]
        grader = parts[0]["grader"]
    else:
        parts, grader = legacy_parts(it["steps"], plan, it["id"])
    conn.execute(
        """
        INSERT INTO items
          (id, node_id, statement_latex, prompt, steps, genui_plan,
           difficulty_estimate, status, source, prompt_md, parts, grader, explanation_md)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'VERIFIED', 'GENERATED', %s, %s, %s, %s)
        """,
        (
            it["id"],
            node_id,
            it.get("statement_latex") or None,
            it.get("prompt"),
            Json(it.get("steps") or []),
            Json(plan) if plan else None,
            float(it.get("difficulty") or 0.4),
            it.get("prompt_md") or it.get("prompt"),
            Json(parts),
            grader,
            it.get("explanation_md"),
        ),
    )


def _store_review(
    conn: psycopg.Connection,
    *,
    node_id: UUID,
    title: str,
    out: dict[str, Any],
    api_key: str,
    emit: Emit,
) -> None:
    """Background review after node_ready; patches beats/primer and swaps flagged problems."""
    ids = [str(i["id"]) for i in out["items"]]
    # Re-read attempts now: the learner may have started practising since node_ready.
    locked = {
        str(r["item_id"])
        for r in conn.execute(
            "SELECT DISTINCT item_id FROM attempts WHERE item_id = ANY(%s::uuid[])", (ids,)
        ).fetchall()
    }
    rv = review_lesson_content(title=title, out=out, api_key=api_key, locked_item_ids=locked)
    for it in rv["new_items"]:
        _insert_item(conn, node_id, it, cited_urls(out["brief"]))
    review = {
        **rv["review"],
        "status": "done",
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "missing_widgets": out["missing_widgets"],
        "timings": out["timings"],
    }
    conn.execute(
        """
        UPDATE knowledge_nodes
        SET lesson_beats = %s,
            primer_md = CASE WHEN %s THEN %s ELSE primer_md END,
            lesson_review = %s
        WHERE id = %s
        """,
        (
            Json(rv["beats"]),
            rv["primer_md"] != out["primer_md"] and bool(rv["primer_md"]),
            rv["primer_md"],
            Json(review),
            node_id,
        ),
    )
    conn.commit()
    emit(
        "review_ready",
        {
            "score": review["score"],
            "repaired": review["repaired"],
            "swapped": len(review["problems_swapped"]),
        },
    )


def _context_blob(ctx: dict[str, Any]) -> str:
    parts: list[str] = []
    if ctx.get("goal"):
        parts.append(f"Goal: {ctx['goal']}")
    if ctx.get("exam_digest"):
        parts.append(f"Exam excerpt:\n{ctx['exam_digest']}")
    for i, s in enumerate(ctx.get("source_digests") or []):
        parts.append(f"Source {i + 1}:\n{s}")
    if ctx.get("corpus_hints"):
        parts.append(f"Research notes:\n{ctx['corpus_hints']}")
    return "\n\n".join(parts)[:5000]


def _generate_primer(
    title: str,
    context: str,
    api_key: str,
    brief: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> str | None:
    """Optional reading; None when the model fails (never a canned primer)."""
    profile = profile or MATH_PROFILE
    example = (
        "a concrete number example in $...$" if profile["notation"] in ("math", "chem") else "a concrete example"
    )
    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Return ONLY JSON: {\"primer_md\":\"...\"}.\n"
                    + profile_prompt(profile)
                    + "\nWrite a RICH Markdown primer (aim 2500–4000 characters) with these ## sections:\n"
                    f"1. The idea — what the skill is, with {example}\n"
                    "2. Why it matters — when learners need it (use the brief's real-world hooks)\n"
                    "3. Worked outline — prose walkthrough of 3–5 steps (no full graded answer dump)\n"
                    "4. Common mistake — the brief's top misconception and how to catch it\n"
                    "5. Check yourself — one reflective question (no answer key)\n"
                    "Write in your own words; stay on the skill topic."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "skill": title,
                        "research_brief": brief_digest(brief, 2000),
                        "learner_context": context[:2000],
                    }
                ),
            },
        ],
        api_key=api_key,
        task="strong",
        temperature=0.35,
    )
    md = str((data or {}).get("primer_md") or "").strip()
    return md[:5000] or None
