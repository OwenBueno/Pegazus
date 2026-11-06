"""Unit tests for DAG compiler (Doc 05 §4)."""

from __future__ import annotations

import networkx as nx

from app.pipeline.dag_compiler import compile_authoritative_dag


def test_three_cycle_loses_weakest_edge():
    nodes = [
        {"slug": "a", "title": "A", "interactivity_weight": 0.5},
        {"slug": "b", "title": "B", "interactivity_weight": 0.5},
        {"slug": "c", "title": "C", "interactivity_weight": 0.5},
    ]
    edges = [
        {"parent_slug": "a", "child_slug": "b", "weight": 1.0},
        {"parent_slug": "b", "child_slug": "c", "weight": 1.0},
        {"parent_slug": "c", "child_slug": "a", "weight": 0.1},
    ]
    G, removed = compile_authoritative_dag(nodes, edges)
    assert ("c", "a") in removed
    assert nx.is_directed_acyclic_graph(G)
    assert G.has_edge("a", "b")
    assert G.has_edge("b", "c")
    assert not G.has_edge("c", "a")
    assert G.nodes["a"]["title"] == "A"


def test_transitive_edge_pruned():
    nodes = [{"slug": s, "title": s.upper()} for s in ("a", "b", "c")]
    edges = [
        {"parent_slug": "a", "child_slug": "b", "weight": 1.0},
        {"parent_slug": "b", "child_slug": "c", "weight": 1.0},
        {"parent_slug": "a", "child_slug": "c", "weight": 1.0},
    ]
    G, removed = compile_authoritative_dag(nodes, edges)
    assert removed == []
    assert G.has_edge("a", "b")
    assert G.has_edge("b", "c")
    assert not G.has_edge("a", "c")
    assert G.nodes["b"]["title"] == "B"
