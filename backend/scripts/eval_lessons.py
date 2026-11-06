"""Benchmark lesson generation end to end (no DB): stage timings, LLM calls, reject rate, critic.

Run before/after pipeline changes and compare the JSON:

    docker compose exec api python scripts/eval_lessons.py --out eval.json
    docker compose exec api python scripts/eval_lessons.py --only 2

Needs OPENROUTER_API_KEY (falls back to deterministic content without it).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.pipeline.materialize_node import (  # noqa: E402
    ITEM_TARGET,
    build_lesson_content,
    lesson_ready,
    review_lesson_content,
)
from app.pipeline import item_gen  # noqa: E402
from app.services import llm  # noqa: E402

GOALS = [
    ("Pass my algebra midterm next month", "Solving two-step linear equations"),
    ("Get ready for 7th grade math", "Order of operations with integers"),
    ("Understand fractions before high school", "Adding fractions with unlike denominators"),
    ("Master simple quadratics", "Factoring quadratic trinomials"),
    ("Review place value for 4th grade", "Place value up to ten thousands"),
]


def run_one(goal: str, title: str, api_key: str) -> dict:
    llm.CALLS.clear()
    llm.TOKENS.clear()
    item_gen.REJECTS.clear()
    t0 = time.perf_counter()
    out = build_lesson_content(title=title, context=f"Goal: {goal}", api_key=api_key)
    ready_s = round(time.perf_counter() - t0, 2)
    new_items = [i for i in out["items"] if i.get("new")]
    # Before review: the review's critic/swap calls are not part of item generation.
    fast_calls = llm.CALLS.get("fast", 0)
    fast_tokens = llm.TOKENS.get("fast.prompt", 0) + llm.TOKENS.get("fast.completion", 0)
    fast_cached = llm.TOKENS.get("fast.cached", 0)
    fast_prompt = llm.TOKENS.get("fast.prompt", 0)
    rv = review_lesson_content(title=title, out=out, api_key=api_key)
    prompt = sum(v for k, v in llm.TOKENS.items() if k.endswith(".prompt"))
    cached = sum(v for k, v in llm.TOKENS.items() if k.endswith(".cached"))
    review = rv["review"]
    return {
        "goal": goal,
        "title": title,
        "ready_s": ready_s,
        "review_s": review["review_s"],
        "timings": out["timings"],
        "llm_calls": dict(llm.CALLS),
        "tokens": dict(llm.TOKENS),
        "items": len(new_items),
        "calls_per_verified_item": round(fast_calls / len(new_items), 2) if new_items else None,
        "tokens_per_verified_item": round(fast_tokens / len(new_items)) if new_items else None,
        "item_cache_hit_ratio": round(fast_cached / fast_prompt, 2) if fast_prompt else None,
        "cache_hit_ratio": round(cached / prompt, 2) if prompt else None,
        "item_reject_reasons": dict(item_gen.REJECTS),
        "beats": len(out["beats"]),
        "beat_types": [b.get("type") for b in out["beats"]],
        "widgets": [
            (b.get("genui_plan") or {}).get("primary") for b in out["beats"] if b.get("type") == "problem"
        ],
        "requested_widgets": [s.get("widget") for s in out["specs"]],
        "missing_widgets": out["missing_widgets"],
        "visuals_used": [b["visual"]["type"] for b in rv["beats"] if b.get("visual")],
        "layouts": [b.get("layout") for b in rv["beats"] if b.get("type") != "problem"],
        "visuals_dropped": out["visuals_dropped"],
        "sources": len(out["brief"].get("sources") or []),
        "critic_score": review["score"],
        "critic_error": review["error"],
        "critic_repaired": review["repaired"],
        "critic_issues": review["issues"],
        "math_errors": review["math_errors"],
        "sympy_flags": review["sympy_flags"],
        "demos_dropped": review["demos_dropped"],
        "problems_swapped": review["problems_swapped"],
        "ready": lesson_ready(item_count=len(out["items"]), beats=out["beats"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0, help="run only the first N goals")
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    key = settings.openrouter_api_key if settings.ai_on else ""
    goals = GOALS[: args.only] if args.only else GOALS
    results = []
    for goal, title in goals:
        r = run_one(goal, title, key)
        results.append(r)
        print(
            f"{r['title'][:40]:<40} ready_s={r['ready_s']:>6} review_s={r['review_s']:>6} "
            f"ready={r['ready']} items={r['items']}/{ITEM_TARGET} beats={r['beats']} "
            f"critic={r['critic_score']} math_errors={len(r['math_errors'])} "
            f"sympy_flags={len(r['sympy_flags'])} swapped={len(r['problems_swapped'])} "
            f"calls/item={r['calls_per_verified_item']} tok/item={r['tokens_per_verified_item']} "
            f"cache={r['item_cache_hit_ratio']} rejects={r['item_reject_reasons']} "
            f"visuals={r['visuals_used']} dropped={r['visuals_dropped']} missing={r['missing_widgets']} "
            f"stages={r['timings']}"
        )
    summary = {
        "model_fast": llm.model_for("fast"),
        "model_strong": llm.model_for("strong"),
        "web_research": settings.research_web_on,
        "avg_ready_s": round(sum(r["ready_s"] for r in results) / len(results), 2),
        "avg_review_s": round(sum(r["review_s"] for r in results) / len(results), 2),
        "ready_rate": round(sum(r["ready"] for r in results) / len(results), 2),
        "total_tokens": sum(sum(v for k, v in r["tokens"].items() if not k.endswith(".cached")) for r in results),
        "avg_critic": (
            round(sum(r["critic_score"] for r in results if r["critic_score"] is not None)
                  / max(1, sum(r["critic_score"] is not None for r in results)), 2)
        ),
        "results": results,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
