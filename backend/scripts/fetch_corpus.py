"""CLI: refresh local corpus from allowlisted OpenStax URLs.

  python -m app.pipeline.fetch_corpus
  # or: python scripts/fetch_corpus.py
"""

from __future__ import annotations

import sys

from app.pipeline.openstax_fetch import fetch_allowlist


def main() -> int:
    try:
        paths = fetch_allowlist()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    for p in paths:
        print(f"wrote {p}")
    print(f"OK: {len(paths)} corpus files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
