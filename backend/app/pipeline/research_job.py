"""Deep Research background job: outline-only DAG (no eager items)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.config import settings
from app.pipeline.dag_compiler import compile_authoritative_dag, topological_slugs
from app.pipeline.item_gen import slugify_module, subject_slug
from app.pipeline.materialize_node import learner_safe
from app.pipeline.retriever import retrieve_for_query
from app.pipeline.sse_buffer import append_event, reset_buffer
from app.services.exam_diag import apply_exam_mastery_hints
from app.services.path_draft import propose_outline
from app.services.subject_profile import MATH_PROFILE, clamp_profile
from app.services.upload_parse import digest_text


def _domain(profile: dict[str, Any]) -> str:
    """Legacy ``domain_enum`` derived from the profile (new code reads ``subject_profile``).

    Twin of ``20261009200100_domain_backfill.sql``.
    """
    if profile["notation"] == "math":
        return "MATHEMATICS"
    return "LANGUAGE" if profile.get("target_language") or "language" in profile["categories"] else "GENERAL"


def run_research_job(
    *,
    path_id: UUID,
    user_id: UUID,
    goal_text: str,
    draft_titles: list[str] | None = None,
    api_key: str,
    database_url: str | None = None,
    exam_markdown: str | None = None,
    source_markdowns: list[str] | None = None,
    use_corpus: bool = True,
    subject_profile: dict[str, Any] | None = None,
) -> None:
    """Build planned nodes (titles + edges only). Items generated on materialize."""
    from app.config import settings as cfg

    url = database_url or cfg.database_url
    reset_buffer(path_id)
    sources = [s for s in (source_markdowns or []) if s and s.strip()]
    exam = (exam_markdown or "").strip() or None
    profile = clamp_profile(subject_profile or MATH_PROFILE, goal=goal_text)
    # The OpenStax corpus is algebra only: never ground a non-math path in it.
    use_corpus = use_corpus and "math" in profile["categories"]
    prefix = "math.generated" if profile["notation"] == "math" else subject_slug(profile["subject"])

    conn = psycopg.connect(url, row_factory=dict_row)
    try:
        # Clear any prior nodes (rebuild / fresh outline)
        conn.execute("DELETE FROM path_nodes WHERE path_id = %s", (path_id,))
        conn.commit()

        titles = draft_titles or []
        if len(titles) >= 4:
            modules = [
                {"title": t, "objectives": [], "prerequisites": [i - 1] if i else []}
                for i, t in enumerate(titles)
            ]
        else:
            modules = propose_outline(
                goal_text=goal_text,
                exam_markdown=exam,
                source_markdowns=sources,
                api_key=api_key or settings.openrouter_api_key,
                profile=profile,
            )

        corpus_hits = retrieve_for_query(goal_text, limit=3) if use_corpus else []
        corpus_hints = "\n\n".join(
            f"{h.title}: {h.body[:400]}" for h in corpus_hits
        )[:3000]

        # Persist digests for later materialize
        plan_context = {
            "goal": goal_text.strip()[:500],
            "exam_digest": digest_text(exam, 4000) if exam else None,
            "source_digests": [digest_text(s, 3000) for s in sources][:5],
            "corpus_hints": corpus_hints or None,
            "use_corpus": use_corpus,
            "attribution": (
                corpus_hits[0].attribution if corpus_hits else "Learner materials + Pegazus research"
            ),
        }
        conn.execute(
            """
            UPDATE learning_paths
            SET plan_context = %s::jsonb, updated_at = NOW()
            WHERE id = %s
            """,
            (__import__("json").dumps(plan_context), path_id),
        )
        conn.commit()

        # Prefer user materials as description source
        user_blob = "\n".join(
            ([exam] if exam else []) + sources
        )[:2000]

        candidates: list[dict[str, Any]] = []
        known: dict[str, int] = {}
        module_to_candidate: dict[int, int] = {}
        for mi, module in enumerate(modules[:12]):
            title = module["title"]
            slug = slugify_module(title, prefix)
            if slug in known:
                module_to_candidate[mi] = known[slug]
                continue
            known[slug] = len(candidates)
            module_to_candidate[mi] = len(candidates)
            hit = next(
                (
                    c
                    for c in corpus_hits
                    if any(t in c.title.lower() for t in title.lower().split()[:2] if len(t) > 2)
                ),
                corpus_hits[0] if corpus_hits else None,
            )
            objectives = module.get("objectives") or []
            if objectives:
                desc = "Objectives: " + "; ".join(objectives)
            else:
                desc = user_blob[:400] if user_blob else (
                    hit.body[:400] if hit else f"Planned skill for: {goal_text}"
                )
            candidates.append(
                {
                    "slug": slug,
                    "title": title[:120],
                    "prerequisites": [
                        module_to_candidate[p]
                        for p in module.get("prerequisites") or []
                        if p in module_to_candidate
                    ],
                    "description": desc[:500],
                    "source_url": hit.source_url if hit else None,
                    "source_license": hit.license if hit else "CC-BY-4.0",
                    "source_attribution": (
                        hit.attribution
                        if hit
                        else ("Learner upload" if user_blob else "Pegazus research (planned)")
                    ),
                }
            )

        created: list[dict[str, Any]] = []

        for seq, cand in enumerate(candidates):
            row = conn.execute(
                """
                INSERT INTO knowledge_nodes (
                    domain, slug, title, description, node_type,
                    source_url, source_license, source_attribution, subject_profile
                ) VALUES (
                    %s, %s, %s, %s, 'SKILL', %s, %s, %s, %s
                )
                ON CONFLICT (slug) DO UPDATE SET
                    domain = EXCLUDED.domain,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    subject_profile = EXCLUDED.subject_profile,
                    source_url = COALESCE(EXCLUDED.source_url, knowledge_nodes.source_url),
                    source_license = COALESCE(EXCLUDED.source_license, knowledge_nodes.source_license),
                    source_attribution = COALESCE(
                        EXCLUDED.source_attribution, knowledge_nodes.source_attribution
                    )
                RETURNING id, slug, title
                """,
                (
                    _domain(profile),
                    cand["slug"],
                    cand["title"],
                    cand["description"],
                    cand["source_url"],
                    cand["source_license"],
                    cand["source_attribution"],
                    Json(profile),
                ),
            ).fetchone()
            assert row is not None
            node_id = row["id"]
            conn.execute(
                """
                INSERT INTO path_nodes (path_id, node_id, sequence_index, is_draft, build_status)
                VALUES (%s, %s, %s, TRUE, 'PLANNED')
                ON CONFLICT (path_id, node_id) DO UPDATE SET sequence_index = EXCLUDED.sequence_index
                """,
                (path_id, node_id, seq),
            )
            parents = [created[p] for p in cand["prerequisites"] if p < len(created)]
            for parent in parents:
                if parent["id"] == node_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO knowledge_edges (parent_id, child_id, edge_type, weight)
                    VALUES (%s, %s, 'PREREQUISITE_OF', 1.0)
                    ON CONFLICT DO NOTHING
                    """,
                    (parent["id"], node_id),
                )
            parent_slug = parents[-1]["slug"] if parents else None
            append_event(
                path_id,
                "node_planned",
                {
                    "slug": row["slug"],
                    "title": row["title"],
                    "parent": parent_slug,
                    "parents": [p["slug"] for p in parents],
                    "node_id": str(node_id),
                },
            )
            # Compat: older clients listen for node_validated
            append_event(
                path_id,
                "node_validated",
                {
                    "slug": row["slug"],
                    "title": row["title"],
                    "parent": parent_slug,
                    "planned": True,
                },
            )
            created.append({"id": node_id, "title": row["title"], "slug": row["slug"]})
            conn.commit()

        # Topo sanity
        path_nodes = conn.execute(
            """
            SELECT n.slug, n.title, n.node_type, n.element_interactivity_weight, n.id
            FROM path_nodes pn JOIN knowledge_nodes n ON n.id = pn.node_id
            WHERE pn.path_id = %s
            """,
            (path_id,),
        ).fetchall()
        slugs = {r["slug"] for r in path_nodes}
        edges = conn.execute(
            """
            SELECT p.slug AS parent_slug, c.slug AS child_slug, e.weight
            FROM knowledge_edges e
            JOIN knowledge_nodes p ON p.id = e.parent_id
            JOIN knowledge_nodes c ON c.id = e.child_id
            WHERE e.edge_type = 'PREREQUISITE_OF'
            """
        ).fetchall()
        raw_nodes = [
            {
                "slug": r["slug"],
                "title": r["title"],
                "node_type": r["node_type"],
                "interactivity_weight": float(r["element_interactivity_weight"]),
                "id": r["id"],
            }
            for r in path_nodes
        ]
        raw_edges = [
            dict(e) for e in edges if e["parent_slug"] in slugs and e["child_slug"] in slugs
        ]
        G, _removed = compile_authoritative_dag(raw_nodes, raw_edges)
        order = topological_slugs(G)

        if exam:
            apply_exam_mastery_hints(
                conn,
                path_id=path_id,
                user_id=user_id,
                exam_markdown=exam,
                node_titles=[{"id": c["id"], "title": c["title"]} for c in created],
                api_key=api_key or settings.openrouter_api_key,
            )
            conn.commit()

        if not order:
            append_event(
                path_id,
                "graph_failed",
                {"total_nodes": 0, "error": learner_safe(RuntimeError("no nodes"), profile["instruction_language"])},
            )
            return

        conn.execute(
            "UPDATE learning_paths SET status = 'ACTIVE', updated_at = NOW() WHERE id = %s",
            (path_id,),
        )
        conn.commit()
        append_event(
            path_id,
            "graph_complete",
            {
                "total_nodes": len(order),
                "estimated_hours": round(len(order) * 0.5, 1),
                "critical_path_length": len(order),
                "outline_only": True,
            },
        )

        # Auto-start the first lesson; its teach_ready stage warms the next one (1 ahead).
        if created:
            from app.pipeline.materialize_node import schedule_materialize_node

            first_id = created[0]["id"]
            schedule_materialize_node(
                path_id=path_id,
                node_id=first_id,
                user_id=user_id,
                api_key=api_key or settings.openrouter_api_key,
                database_url=url,
            )
            append_event(
                path_id,
                "prefetch_started",
                {"node_id": str(first_id), "sequence_index": 0},
            )
    except Exception as exc:
        append_event(
            path_id,
            "graph_failed",
            {"total_nodes": 0, "error": learner_safe(exc, profile["instruction_language"])},
        )
        # Leave path in DRAFTING / non-ACTIVE so FE can retry; never ACTIVE with 0 nodes.
    finally:
        conn.close()
