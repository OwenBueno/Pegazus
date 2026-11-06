"""multi_subject.sql backfill == graders.legacy.legacy_parts (runs in a rolled-back transaction)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.config import settings
from app.graders.legacy import legacy_parts
from app.pipeline.materialize_node import _insert_item

SQL = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20261009180000_multi_subject.sql"

STEPS = [
    {"latex": "2x+1=5", "sympy": "Eq(2*x+1, 5)", "operation": "GIVEN"},
    {"latex": "2x=4", "sympy": "Eq(2*x, 4)", "operation": "SUBTRACT", "justification": "subtract 1"},
    {"latex": "x=2", "sympy": "Eq(x, 2)"},
]
FINAL = [{"latex": "x=5", "sympy": "Eq(x, 5)", "operation": "FINAL"}]
QC = {"primary": "QuickCheck", "widgets": [{"type": "QuickCheck", "props": {
    "prompt": "Solve", "choices": [{"id": "a", "label": "x=5"}, {"id": "b", "label": "x=6"}],
    "correctId": "a", "correct_latex": "x=5", "labelsAreLatex": True, "explanation": "undo +1"}}]}
NL = {"primary": "NumberLine", "widgets": [{"type": "NumberLine", "props": {
    "min": 0.0, "max": 10.0, "target": 7.0, "step": 1.0, "prompt": "Place it", "correct_latex": "7"}}]}
MP = {"primary": "MatchPairs", "widgets": [{"type": "MatchPairs", "props": {"prompt": "Match", "pairs": [
    {"id": "p1", "left": "1/2", "right": "0.5"}, {"id": "p2", "left": "1/4", "right": "0.25"},
    {"id": "p3", "left": "3/4", "right": "0.75"}], "correct_latex": "0.5"}}]}
BROKEN_QC = {"primary": "QuickCheck", "widgets": [
    {"type": "QuickCheck", "props": {"prompt": "", "choices": [], "correctId": "b"}}]}


def _connect() -> psycopg.Connection:
    try:
        return psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=3)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"database unreachable: {e}")


def test_backfill_matches_legacy_parts() -> None:
    conn = _connect()
    try:
        node = conn.execute("SELECT id FROM knowledge_nodes LIMIT 1").fetchone()
        user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if not node or not user:
            pytest.skip("needs one knowledge node and one user")
        fixtures = {uuid4(): (STEPS, None), uuid4(): (FINAL, QC), uuid4(): (FINAL, NL),
                    uuid4(): (FINAL, MP), uuid4(): (STEPS, BROKEN_QC)}
        for iid, (steps, plan) in fixtures.items():
            conn.execute(
                """INSERT INTO items (id, node_id, statement_latex, prompt, steps, genui_plan,
                   difficulty_estimate, status, source) VALUES (%s,%s,'2x+1=5','Solve',%s,%s,0.4,'VERIFIED','GENERATED')""",
                (iid, node["id"], Json(steps), Json(plan) if plan else None),
            )
        if conn.execute("SELECT 1 FROM information_schema.columns WHERE table_name='items' AND column_name='parts'").fetchone():
            conn.execute("UPDATE items SET parts = NULL, grader = NULL WHERE id = ANY(%s)", (list(fixtures),))
        sid = conn.execute("INSERT INTO session_logs (user_id) VALUES (%s) RETURNING id", (user["id"],)).fetchone()["id"]
        first = next(iter(fixtures))
        aid = conn.execute(
            """INSERT INTO attempts (session_id, user_id, node_id, item_id, step_index, submitted_latex,
               verdict, is_success, latency_ms, scaffold_level, decided_by)
               VALUES (%s,%s,%s,%s,0,'2x=4','CORRECT_OPTIMAL',TRUE,10,2,'RULES') RETURNING id""",
            (sid, user["id"], node["id"], first),
        ).fetchone()["id"]
        if conn.execute("SELECT 1 FROM information_schema.columns WHERE table_name='attempts' AND column_name='grader'").fetchone():
            conn.execute("UPDATE attempts SET grader = NULL, submitted_answer = NULL WHERE id = %s", (aid,))

        sql = SQL.read_text(encoding="utf-8")
        conn.execute(sql)
        rows = {r["id"]: r for r in conn.execute(
            "SELECT id, parts, grader, prompt_md, statement_latex FROM items WHERE id = ANY(%s)", (list(fixtures),)
        ).fetchall()}
        for iid, (steps, plan) in fixtures.items():
            parts, grader = legacy_parts(steps, plan, iid)
            assert rows[iid]["parts"] == parts, (plan and plan["primary"], rows[iid]["parts"], parts)
            assert rows[iid]["grader"] == grader and rows[iid]["prompt_md"] == "Solve"

        multi, qc, nl, mp, broken = (rows[i]["parts"] for i in fixtures)
        assert len(multi) == 3 and multi[1]["answer_spec"] == {"latex": "2x=4", "sympy": "Eq(2*x, 4)", "operation": "SUBTRACT"}
        assert multi[1]["justification"] == "subtract 1" and "justification" not in multi[0]
        assert qc == [{"component": "QuickCheck", "grader": "choice",
                       "props": {"prompt": "Solve", "choices": QC["widgets"][0]["props"]["choices"], "labelsAreLatex": True},
                       "answer_spec": {"correctIds": ["a"], "explanation": "undo +1"}}]
        assert nl[0]["answer_spec"] == {"value": 7.0, "abs_tolerance": 0.5} and "target" not in nl[0]["props"]
        m = mp[0]
        assert m["props"]["lefts"] == ["1/2", "1/4", "3/4"] and sorted(m["props"]["rights"]) == ["0.25", "0.5", "0.75"]
        assert all(m["props"]["rights"][r] == MP["widgets"][0]["props"]["pairs"][l]["right"] for l, r in m["answer_spec"]["pairs"])
        assert "pairs" not in m["props"] and len(broken) == 3 and broken[0]["grader"] == "sympy"

        att = conn.execute("SELECT grader, submitted_answer FROM attempts WHERE id = %s", (aid,)).fetchone()
        assert att == {"grader": "sympy", "submitted_answer": {"latex": "2x=4"}}

        conn.execute(sql)  # re-runnable: second pass changes nothing
        again = {r["id"]: r["parts"] for r in conn.execute(
            "SELECT id, parts FROM items WHERE id = ANY(%s)", (list(fixtures),)).fetchall()}
        assert again == {i: r["parts"] for i, r in rows.items()}

        # MS-1.6: freshly materialized items are born with the same parts.
        new = {"id": uuid4(), "statement_latex": "x+1=6", "prompt": "Solve", "steps": FINAL, "genui_plan": QC}
        _insert_item(conn, node["id"], new)
        row = conn.execute("SELECT parts, grader, prompt_md FROM items WHERE id = %s", (new["id"],)).fetchone()
        assert (row["parts"], row["grader"]) == legacy_parts(FINAL, QC, new["id"]) and row["prompt_md"] == "Solve"
    finally:
        conn.rollback()
        conn.close()
