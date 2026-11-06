"""SymPy evaluate P95 bench — exit 1 if P95 >= 200 ms (US-1.3)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.workers.math_evaluator import evaluate_step_safe, shutdown_pool, warm_pool

N = 50
P95_LIMIT_MS = 200.0


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main() -> int:
    warm_pool()
    # Warm again with a few sync calls so pool workers are hot
    for _ in range(5):
        evaluate_step_safe("x = 3", "Eq(2*x, 6)")

    pairs = [("x = 3", "Eq(2*x, 6)"), ("x = 5", "Eq(3*x, 15)"), ("x = 4", "Eq(2*x + 3, 11)")] * (
        N // 3 + 1
    )
    pairs = pairs[:N]
    latencies: list[float] = []

    def one(u: str, t: str) -> dict:
        t0 = time.perf_counter()
        r = evaluate_step_safe(u, t, use_pool=True)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        return r

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(one, u, t) for u, t in pairs]
        results = [f.result() for f in as_completed(futures)]

    ok = sum(1 for r in results if r.get("is_equivalent"))
    latencies.sort()
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    print(
        f"OK {ok}/{len(results)}; P50={p50:.1f}ms P95={p95:.1f}ms "
        f"(limit {P95_LIMIT_MS:.0f}ms, n={N})"
    )
    shutdown_pool()
    if ok != len(results):
        return 1
    if p95 >= P95_LIMIT_MS:
        print(f"FAIL: P95 {p95:.1f} >= {P95_LIMIT_MS}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
