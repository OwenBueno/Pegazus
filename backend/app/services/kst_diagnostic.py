"""Knowledge Space Theory diagnostic (Doc 05 §5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

import psycopg

# ponytail: fixed latency threshold instead of 3× item median; upgrade when we have item stats.
LATENCY_THRESHOLD_MS = 15_000
FLUENCY_PASS = 0.80
P_MASTERED = 0.95
P_LOW_CONF = 0.70
P_NOT = 0.05


class NodeStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    MASTERED = "MASTERED"
    NOT_MASTERED = "NOT_MASTERED"


@dataclass
class DiagnosticGraph:
    """In-memory KST state for one diagnostic run."""

    node_ids: list[UUID]
    # parent -> children (prerequisite edges: parent must be before child)
    children: dict[UUID, list[UUID]] = field(default_factory=dict)
    parents: dict[UUID, list[UUID]] = field(default_factory=dict)
    status: dict[UUID, NodeStatus] = field(default_factory=dict)
    weight: dict[UUID, float] = field(default_factory=dict)
    probe_count: int = 0

    def __post_init__(self) -> None:
        for nid in self.node_ids:
            self.status.setdefault(nid, NodeStatus.UNKNOWN)
            self.children.setdefault(nid, [])
            self.parents.setdefault(nid, [])
            self.weight.setdefault(nid, 0.5)


def build_diagnostic_graph(
    node_rows: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
) -> DiagnosticGraph:
    ids = [r["id"] for r in node_rows]
    id_set = set(ids)
    g = DiagnosticGraph(node_ids=ids)
    for r in node_rows:
        g.weight[r["id"]] = float(r.get("element_interactivity_weight") or 0.5)
    for e in edge_rows:
        p, c = e["parent_id"], e["child_id"]
        if p in id_set and c in id_set:
            g.children[p].append(c)
            g.parents[c].append(p)
    return g


def _unknown_ancestors(g: DiagnosticGraph, n: UUID) -> set[UUID]:
    out = {n}
    stack = list(g.parents.get(n, []))
    while stack:
        p = stack.pop()
        if p in out:
            continue
        if g.status.get(p) == NodeStatus.UNKNOWN:
            out.add(p)
            stack.extend(g.parents.get(p, []))
    return out


def _unknown_descendants(g: DiagnosticGraph, n: UUID) -> set[UUID]:
    out = {n}
    stack = list(g.children.get(n, []))
    while stack:
        c = stack.pop()
        if c in out:
            continue
        if g.status.get(c) == NodeStatus.UNKNOWN:
            out.add(c)
            stack.extend(g.children.get(c, []))
    return out


def select_probe(g: DiagnosticGraph) -> UUID | None:
    """Pick UNKNOWN node maximizing min(a,d); ties → lower interactivity weight."""
    unknown = [n for n in g.node_ids if g.status[n] == NodeStatus.UNKNOWN]
    if not unknown:
        return None
    best: UUID | None = None
    best_key: tuple[float, float] | None = None
    for n in unknown:
        a = len(_unknown_ancestors(g, n))
        d = len(_unknown_descendants(g, n))
        split = float(min(a, d))
        # maximize split; then minimize weight
        key = (-split, g.weight.get(n, 0.5))
        if best_key is None or key < best_key:
            best_key = key
            best = n
    return best


def fluency_score(*, correct: bool, latency_ms: int) -> float:
    if not correct:
        return 0.0
    return 1.0 - min(1.0, latency_ms / LATENCY_THRESHOLD_MS)


def apply_answer(g: DiagnosticGraph, node_id: UUID, *, correct: bool, latency_ms: int) -> float:
    """Update statuses; return fluency F."""
    F = fluency_score(correct=correct, latency_ms=latency_ms)
    g.probe_count += 1
    if not correct:
        for n in _all_descendants_incl(g, node_id):
            g.status[n] = NodeStatus.NOT_MASTERED
        return F
    if F >= FLUENCY_PASS:
        for n in _all_ancestors_incl(g, node_id):
            g.status[n] = NodeStatus.MASTERED
    else:
        # Slow-but-correct: node only, no ancestor propagation
        g.status[node_id] = NodeStatus.MASTERED
    return F


def _all_ancestors_incl(g: DiagnosticGraph, n: UUID) -> set[UUID]:
    out = {n}
    stack = list(g.parents.get(n, []))
    while stack:
        p = stack.pop()
        if p in out:
            continue
        out.add(p)
        stack.extend(g.parents.get(p, []))
    return out


def _all_descendants_incl(g: DiagnosticGraph, n: UUID) -> set[UUID]:
    out = {n}
    stack = list(g.children.get(n, []))
    while stack:
        c = stack.pop()
        if c in out:
            continue
        out.add(c)
        stack.extend(g.children.get(c, []))
    return out


def should_stop(g: DiagnosticGraph) -> bool:
    unknown = sum(1 for n in g.node_ids if g.status[n] == NodeStatus.UNKNOWN)
    if g.probe_count >= 5:
        return True
    if unknown == 0 and g.probe_count >= 3:
        return True
    # Fully classified before 3 probes (tiny graphs): stop anyway.
    if unknown == 0 and g.probe_count >= 1:
        return True
    return False


def finalize_unknown_as_not_mastered(g: DiagnosticGraph) -> None:
    for n in g.node_ids:
        if g.status[n] == NodeStatus.UNKNOWN:
            g.status[n] = NodeStatus.NOT_MASTERED


def frontier_nodes(g: DiagnosticGraph) -> list[UUID]:
    """NOT_MASTERED nodes whose parents are all MASTERED (or no parents)."""
    out: list[UUID] = []
    for n in g.node_ids:
        if g.status[n] != NodeStatus.NOT_MASTERED:
            continue
        parents = g.parents.get(n, [])
        if all(g.status.get(p) == NodeStatus.MASTERED for p in parents):
            out.append(n)
    return out


def p_mastery_for(status: NodeStatus, *, low_conf: bool = False) -> float:
    if status == NodeStatus.MASTERED:
        return P_LOW_CONF if low_conf else P_MASTERED
    if status == NodeStatus.NOT_MASTERED:
        return P_NOT
    return 0.0


def upsert_p_mastery(
    conn: psycopg.Connection,
    *,
    user_id: UUID,
    node_id: UUID,
    p_mastery: float,
) -> None:
    conn.execute(
        """
        INSERT INTO user_node_states (user_id, node_id, p_mastery)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, node_id) DO UPDATE SET p_mastery = EXCLUDED.p_mastery
        """,
        (user_id, node_id, p_mastery),
    )


def persist_graph_mastery(
    conn: psycopg.Connection,
    *,
    user_id: UUID,
    g: DiagnosticGraph,
    low_conf_nodes: set[UUID] | None = None,
) -> None:
    low = low_conf_nodes or set()
    for n in g.node_ids:
        if g.status[n] == NodeStatus.UNKNOWN:
            continue
        p = p_mastery_for(g.status[n], low_conf=n in low)
        upsert_p_mastery(conn, user_id=user_id, node_id=n, p_mastery=p)


# In-memory diagnostic sessions (path_id -> graph). Survives one API process.
# ponytail: lost on reload; upgrade to Redis/DB JSON if multi-worker.
_SESSIONS: dict[tuple[UUID, UUID], DiagnosticGraph] = {}
_LOW_CONF: dict[tuple[UUID, UUID], set[UUID]] = {}


def session_key(user_id: UUID, path_id: UUID) -> tuple[UUID, UUID]:
    return (user_id, path_id)


def store_session(user_id: UUID, path_id: UUID, g: DiagnosticGraph) -> None:
    _SESSIONS[session_key(user_id, path_id)] = g
    _LOW_CONF[session_key(user_id, path_id)] = set()


def get_session(user_id: UUID, path_id: UUID) -> DiagnosticGraph | None:
    return _SESSIONS.get(session_key(user_id, path_id))


def mark_low_conf(user_id: UUID, path_id: UUID, node_id: UUID) -> None:
    _LOW_CONF.setdefault(session_key(user_id, path_id), set()).add(node_id)


def get_low_conf(user_id: UUID, path_id: UUID) -> set[UUID]:
    return _LOW_CONF.get(session_key(user_id, path_id), set())
