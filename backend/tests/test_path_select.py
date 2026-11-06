"""Path list / delete and path-scoped session picking."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.api_session import _pick_next_item


def _result(rows):
    m = MagicMock()
    m.fetchall.return_value = rows
    m.fetchone.return_value = rows[0] if rows else None
    return m


def test_pick_next_item_filters_to_path_nodes():
    path_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    node_id = uuid4()
    item_id = uuid4()

    conn = MagicMock()
    conn.execute.side_effect = [
        _result([]),  # done items
        _result([]),  # due on path
        _result(
            [{"node_id": node_id, "slug": "a", "title": "A", "sequence_index": 0}]
        ),
        _result(
            [
                {
                    "id": item_id,
                    "node_id": node_id,
                    "statement_latex": "x",
                    "steps": [{"latex": "x", "sympy": "x"}],
                }
            ]
        ),
    ]

    picked = _pick_next_item(conn, user_id, session_id, path_id=path_id)
    assert picked is not None
    item, node = picked
    assert item["id"] == item_id
    assert node["node_id"] == node_id
    third_sql = conn.execute.call_args_list[2].args[0]
    assert "path_nodes" in third_sql
    assert conn.execute.call_args_list[2].args[1] == (user_id, path_id)
