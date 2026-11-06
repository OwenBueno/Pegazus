"""DAG cycle-break + transitive reduction (Doc 05 §4)."""

from __future__ import annotations

from typing import Any

import networkx as nx


def compile_authoritative_dag(
    raw_nodes: list[dict[str, Any]],
    raw_edges: list[dict[str, Any]],
) -> tuple[nx.DiGraph, list[tuple[str, str]]]:
    """
    Nodes need slug (+ optional title, node_type, interactivity_weight).
    Edges need parent_slug, child_slug, optional weight.
    """
    G = nx.DiGraph()
    for node in raw_nodes:
        G.add_node(
            node["slug"],
            title=node.get("title", node["slug"]),
            node_type=node.get("node_type", "SKILL"),
            interactivity_weight=float(node.get("interactivity_weight", 0.5)),
            id=node.get("id"),
        )
    for edge in raw_edges:
        u, v = edge["parent_slug"], edge["child_slug"]
        if u in G and v in G:
            G.add_edge(u, v, weight=float(edge.get("weight", 1.0)))

    # 1. Break cycles: each pass removes the weakest edge of one cycle.
    # ponytail: O(E) per removal, O(E^2) worst case; fine for small curricula.
    removed: list[tuple[str, str]] = []
    while True:
        try:
            cycle = nx.find_cycle(G)
        except nx.NetworkXNoCycle:
            break
        u, v = min(((a, b) for a, b, *_ in cycle), key=lambda e: G.edges[e]["weight"])
        G.remove_edge(u, v)
        removed.append((u, v))

    # 2. Transitive reduction (returns graph without attributes — copy back).
    reduced = nx.transitive_reduction(G)
    reduced.add_nodes_from(G.nodes(data=True))
    reduced.add_edges_from((u, v, G.edges[u, v]) for u, v in reduced.edges)
    return reduced, removed


def topological_slugs(G: nx.DiGraph) -> list[str]:
    return list(nx.topological_sort(G))
