"""Optional OpenRouter draft generator for seed items.

Requires OPENROUTER_API_KEY. Output is DRAFT JSON — run SymPy validation before marking VERIFIED.
Not wired into docker compose.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "supabase" / "seed" / "generated_drafts.json"


def main() -> int:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY not set; nothing to do.", file=sys.stderr)
        return 1

    prompt = (
        "Generate 1 algebra practice item as JSON with keys "
        "statement_latex, steps (list of {latex, sympy, operation}). "
        "Topic: one-step linear equation. sympy must use Eq(...) and symbol x."
    )
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    draft = json.loads(content)
    draft["status"] = "DRAFT"
    draft["source"] = "GENERATED"
    OUT.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} — verify with SymPy before promoting to VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
