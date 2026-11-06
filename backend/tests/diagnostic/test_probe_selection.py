"""KST probe selection (Doc 05 §5.1)."""

from __future__ import annotations

from uuid import uuid4

from app.services.kst_diagnostic import (
    DiagnosticGraph,
    NodeStatus,
    apply_answer,
    select_probe,
)


def _chain7() -> DiagnosticGraph:
    ids = [uuid4() for _ in range(7)]
    g = DiagnosticGraph(node_ids=ids)
    for i, nid in enumerate(ids):
        g.weight[nid] = 0.5
        if i > 0:
            g.parents[nid] = [ids[i - 1]]
            g.children[ids[i - 1]] = [nid]
    return g


def test_first_probe_is_middle_of_chain():
    g = _chain7()
    probe = select_probe(g)
    # Middle of 7 is index 3
    assert probe == g.node_ids[3]


def test_pass_marks_ancestors_mastered():
    g = _chain7()
    mid = g.node_ids[3]
    F = apply_answer(g, mid, correct=True, latency_ms=1000)
    assert F >= 0.80
    for i in range(4):
        assert g.status[g.node_ids[i]] == NodeStatus.MASTERED
    for i in range(4, 7):
        assert g.status[g.node_ids[i]] == NodeStatus.UNKNOWN


def test_fail_marks_descendants():
    g = _chain7()
    mid = g.node_ids[3]
    apply_answer(g, mid, correct=False, latency_ms=1000)
    for i in range(3, 7):
        assert g.status[g.node_ids[i]] == NodeStatus.NOT_MASTERED
    for i in range(0, 3):
        assert g.status[g.node_ids[i]] == NodeStatus.UNKNOWN
