"""Mark identical-Eq(y,N)-all-steps VERIFIED items as DRAFT so next open rematerializes.

Usage (from repo root, with DATABASE_URL):
  docker compose exec -T api python -m scripts.scrub_identical_eq_items
"""

from __future__ import annotations

import json
import sys

import psycopg
from psycopg.rows import dict_row

from app.config import settings


def _identical_eq_bank(steps: object) -> bool:
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            return False
    if not isinstance(steps, list) or len(steps) < 2:
        return False
    sympy_vals: list[str] = []
    for s in steps:
        if not isinstance(s, dict):
            return False
        sympy_vals.append(str(s.get("sympy") or s.get("latex") or "").strip())
    if len(set(sympy_vals)) != 1:
        return False
    s0 = sympy_vals[0].replace(" ", "")
    return s0.startswith("Eq(")


def main() -> int:
    url = settings.database_url
    if not url:
        print("DATABASE_URL missing", file=sys.stderr)
        return 1
    conn = psycopg.connect(url, row_factory=dict_row)
    try:
        rows = conn.execute(
            "SELECT id, steps FROM items WHERE status = 'VERIFIED'"
        ).fetchall()
        n = 0
        for r in rows:
            if not _identical_eq_bank(r["steps"]):
                continue
            conn.execute(
                "UPDATE items SET status = 'DRAFT' WHERE id = %s",
                (r["id"],),
            )
            n += 1
        conn.commit()
        print(f"scrubbed {n} identical-Eq banks to DRAFT")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
