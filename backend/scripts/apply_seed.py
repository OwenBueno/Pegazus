"""Apply supabase/seed.sql using DATABASE_URL."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

CANDIDATES = [
    Path("/supabase/seed.sql"),
    Path(__file__).resolve().parents[2] / "supabase" / "seed.sql",
]


def main() -> int:
    path = next((p for p in CANDIDATES if p.is_file()), None)
    if path is None:
        print("seed.sql not found", file=sys.stderr)
        return 1
    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(sql)
        conn.commit()
        n = conn.execute(
            "select count(*) from items where status = %s", ("VERIFIED",)
        ).fetchone()[0]
        print(f"applied {path}; verified items={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
