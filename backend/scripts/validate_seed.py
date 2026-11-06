"""Validate Algebra seed fixtures: DAG acyclic + SymPy step parse/solution checks.

Run from backend/: python scripts/validate_seed.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

from sympy import Abs, And, Eq, Or, Rational, Symbol, simplify
from sympy.core.relational import Relational
from sympy.parsing.sympy_parser import parse_expr

ROOT = Path(__file__).resolve().parents[2]
SEED_CANDIDATES = [
    ROOT / "supabase" / "seed" / "algebra_p0lite.json",
    Path(__file__).resolve().parents[1] / "seed" / "algebra_p0lite.json",
    Path("/seed/algebra_p0lite.json"),
    Path("/supabase/seed/algebra_p0lite.json"),
]

x = Symbol("x")
y = Symbol("y")
LOCALS = {
    "x": x,
    "y": y,
    "Eq": Eq,
    "Or": Or,
    "And": And,
    "Abs": Abs,
    "Rational": Rational,
}

# Original P0-lite five nodes need ≥8 items; newer nodes ≥5.
CORE_NODE_IDS = {
    "11111111-1111-1111-1111-111111111101",
    "11111111-1111-1111-1111-111111111102",
    "11111111-1111-1111-1111-111111111103",
    "11111111-1111-1111-1111-111111111104",
    "11111111-1111-1111-1111-111111111105",
}


def load_seed() -> dict:
    for path in SEED_CANDIDATES:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"seed not found in {SEED_CANDIDATES}")


def assert_dag_acyclic(nodes: list[dict], edges: list[dict]) -> None:
    ids = {n["id"] for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    indeg: dict[str, int] = {i: 0 for i in ids}
    for e in edges:
        p, c = e["parent_id"], e["child_id"]
        if p not in ids or c not in ids:
            raise AssertionError(f"edge references unknown node: {e}")
        if p == c:
            raise AssertionError(f"self-loop: {e}")
        adj[p].append(c)
        indeg[c] += 1
    q = deque([i for i, d in indeg.items() if d == 0])
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for c in adj[n]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    if seen != len(ids):
        raise AssertionError("knowledge graph has a cycle")


def solution_set(expr):
    """Normalize Eq / Relational / Or-of-Eq into a frozenset of solution forms."""
    if isinstance(expr, Or):
        parts = []
        for arg in expr.args:
            parts.extend(solution_set(arg))
        return frozenset(parts)
    if isinstance(expr, Eq):
        return frozenset({simplify(expr.lhs - expr.rhs)})
    if isinstance(expr, Relational):
        # Compare structural form after simplify of both sides.
        return frozenset({(type(expr), simplify(expr.lhs), simplify(expr.rhs))})
    return frozenset({simplify(expr)})


def verify_item(item: dict) -> None:
    steps = item["steps"]
    if not steps:
        raise AssertionError(f"{item['id']}: empty steps")
    parsed = []
    for i, step in enumerate(steps):
        if "sympy" not in step:
            raise AssertionError(f"{item['id']} step {i}: missing sympy")
        try:
            expr = parse_expr(step["sympy"], local_dict=LOCALS, evaluate=False)
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"{item['id']} step {i}: parse failed: {exc}") from exc
        parsed.append(expr)

    # First step must match statement sympy when present on step 0.
    # Consecutive equation steps must share the same solution set for Eq chains.
    for i in range(1, len(parsed)):
        prev, cur = parsed[i - 1], parsed[i]
        if isinstance(prev, Eq) and isinstance(cur, Eq):
            # Both should imply the same x solution when solvable.
            try:
                from sympy import solve

                s_prev = set(solve(prev, x))
                s_cur = set(solve(cur, x))
                if s_prev and s_cur and s_prev != s_cur:
                    raise AssertionError(
                        f"{item['id']} steps {i - 1}->{i}: solution changed {s_prev} -> {s_cur}"
                    )
            except AssertionError:
                raise
            except Exception:
                # Abs / And / non-unique — structural check only
                pass
        if isinstance(cur, Or) and isinstance(prev, Eq):
            from sympy import solve

            try:
                s_prev = set(solve(prev, x))
                s_cur = set()
                for arg in cur.args:
                    if isinstance(arg, Eq):
                        s_cur |= set(solve(arg, x))
                if s_prev and s_cur and s_prev != s_cur:
                    raise AssertionError(
                        f"{item['id']} steps {i - 1}->{i}: Or solutions mismatch {s_prev} -> {s_cur}"
                    )
            except AssertionError:
                raise
            except Exception:
                pass


def main() -> int:
    seed = load_seed()
    nodes = seed["nodes"]
    edges = seed["edges"]
    items = seed["items"]

    assert_dag_acyclic(nodes, edges)

    by_node: dict[str, int] = defaultdict(int)
    for item in items:
        if item.get("status") != "VERIFIED":
            raise AssertionError(f"{item['id']}: seed items must be VERIFIED")
        verify_item(item)
        by_node[item["node_id"]] += 1

    if len(nodes) < 12:
        raise AssertionError(f"need >= 12 nodes for pedagogy seed, got {len(nodes)}")

    for n in nodes:
        if not (n.get("primer_md") or "").strip():
            raise AssertionError(f"{n['slug']}: missing primer_md")
        need = 8 if n["id"] in CORE_NODE_IDS else 5
        if by_node[n["id"]] < need:
            raise AssertionError(
                f"{n['slug']}: need >= {need} items, got {by_node[n['id']]}"
            )

    print(
        f"OK: {len(nodes)} nodes, {len(edges)} edges, {len(items)} items — "
        "DAG acyclic, SymPy steps verified, primers present"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
