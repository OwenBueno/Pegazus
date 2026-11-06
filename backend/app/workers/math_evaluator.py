"""SymPy step evaluator with a warm ProcessPool (Doc 04 §4.1)."""

from __future__ import annotations

import atexit
import random
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeout
from typing import Any

import sympy as sp

MAX_LATEX_LEN = 500
DEFAULT_TIMEOUT_S = 0.250  # Doc target 150 ms once warm; cold worker margin for P1-lite

_pool: ProcessPoolExecutor | None = None


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=4)
        atexit.register(shutdown_pool)
    return _pool


def warm_pool() -> None:
    """Prime workers so the first learner request does not pay import cost."""
    pool = _get_pool()
    fut = pool.submit(_evaluate, "x = 1", "Eq(x, 1)")
    fut.result(timeout=60.0)


def shutdown_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def _parse(expr_or_latex: str, *, evaluate: bool = True) -> sp.Expr:
    """Parse learner/target math. Prefer sympy ASCII; fall back to LaTeX."""
    text = expr_or_latex.strip()
    try:
        from sympy.parsing.sympy_parser import (
            convert_equals_signs,
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )

        local_dict = {
            "x": sp.Symbol("x"),
            "y": sp.Symbol("y"),
            "Eq": sp.Eq,
            "Or": sp.Or,
            "And": sp.And,
        }
        transformations = standard_transformations + (
            implicit_multiplication_application,
            convert_equals_signs,
        )
        return parse_expr(
            text,
            local_dict=local_dict,
            transformations=transformations,
            evaluate=evaluate,
        )
    except Exception:
        pass

    from sympy.parsing.latex import parse_latex

    return parse_latex(text)


def _to_zero_form(expr: sp.Expr) -> sp.Expr:
    return expr.lhs - expr.rhs if isinstance(expr, sp.Equality) else expr


def _numerically_equal(a: sp.Expr, b: sp.Expr, samples: int = 8) -> bool:
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    if not syms:
        try:
            return abs(complex(a.evalf()) - complex(b.evalf())) <= 1e-8
        except (ZeroDivisionError, TypeError, ValueError):
            return False
    hits = 0
    for _ in range(samples):
        point = {s: random.uniform(-10, 10) for s in syms}
        try:
            if abs(complex(a.evalf(subs=point)) - complex(b.evalf(subs=point))) > 1e-8:
                return False
            hits += 1
        except (ZeroDivisionError, TypeError, ValueError):
            continue
    return hits > 0


def _expr_equal(a: sp.Expr, b: sp.Expr) -> bool:
    return bool(sp.simplify(a - b) == 0 or _numerically_equal(a, b))


def _bare_vs_equation(user: sp.Expr, target_eq: sp.Equality) -> bool:
    """Bare value / var=rhs matches Eq(var, rhs) only via RHS (or full equation)."""
    if isinstance(user, sp.Equality):
        return False
    rhs = target_eq.rhs
    lhs = target_eq.lhs
    if _expr_equal(user, rhs):
        return True
    # Allow submitting the full left-hand side when lhs is a single symbol assignment form
    # already handled above; also accept lhs - rhs == 0 rewritten as value of rhs only.
    if user.free_symbols and _expr_equal(user, lhs - rhs):
        return True
    return False


def _equation_equivalent(u: sp.Expr, t: sp.Expr) -> bool:
    """Both sides are zero-forms of equations. Never EmptySet==EmptySet."""
    if t == 0:
        return sp.simplify(u) == 0
    try:
        ratio = sp.simplify(u / t)
        if ratio.is_number and ratio != 0:
            return True
    except Exception:
        pass
    shared = u.free_symbols & t.free_symbols
    if not shared:
        return _expr_equal(u, t)
    # Solve only in a symbol that appears in both; skip EmptySet==EmptySet traps.
    for sym in sorted(shared, key=str):
        try:
            su = sp.solveset(u, sym, domain=sp.Complexes)
            st = sp.solveset(t, sym, domain=sp.Complexes)
            if su == sp.EmptySet and st == sp.EmptySet:
                continue
            if su == st:
                return True
        except Exception:
            continue
    return _numerically_equal(u, t)


def _sign_error(user: sp.Expr, target: sp.Expr, *, both_equations: bool) -> bool:
    """True if the learner's answer is the sign-flipped form of the target."""
    if both_equations:
        u, t = _to_zero_form(user), _to_zero_form(target)
        shared = u.free_symbols & t.free_symbols
        for sym in sorted(shared, key=str) if shared else []:
            try:
                su = sp.solveset(u, sym, domain=sp.Complexes)
                st = sp.solveset(t, sym, domain=sp.Complexes)
                if su == st:
                    return False
                if (
                    isinstance(st, sp.FiniteSet)
                    and isinstance(su, sp.FiniteSet)
                    and len(st) > 0
                    and su == sp.FiniteSet(*(-s for s in st))
                ):
                    return True
            except Exception:
                continue
        if isinstance(target, sp.Equality) and not isinstance(user, sp.Equality):
            return _expr_equal(user, -target.rhs) and not _expr_equal(user, target.rhs)
        return False
    u, t = user if not isinstance(user, sp.Equality) else _to_zero_form(user), (
        target if not isinstance(target, sp.Equality) else _to_zero_form(target)
    )
    return bool(_expr_equal(-u, t)) and not _expr_equal(u, t)


def _evaluate(user_input: str, target_input: str) -> dict[str, Any]:
    user = _parse(user_input)
    target = _parse(target_input)
    user_is_eq = isinstance(user, sp.Equality)
    target_is_eq = isinstance(target, sp.Equality)
    both_eq = user_is_eq and target_is_eq

    if both_eq:
        equivalent = _equation_equivalent(_to_zero_form(user), _to_zero_form(target))
    elif target_is_eq and not user_is_eq:
        # Bare number / expression vs Eq(y, N): match RHS (or zero-form), not solveset(x).
        equivalent = _bare_vs_equation(user, target)
    elif user_is_eq and not target_is_eq:
        equivalent = _bare_vs_equation(target, user)
    else:
        equivalent = _expr_equal(user, target)

    sign_err = False
    if not equivalent:
        sign_err = _sign_error(user, target, both_equations=both_eq or target_is_eq or user_is_eq)

    return {
        "success": True,
        "is_equivalent": bool(equivalent),
        "sign_error": bool(sign_err),
        "is_factored": (not user_is_eq) and getattr(user, "is_Mul", False),
        "is_solved_form": _is_solved_form(user_input),
        "error": None,
    }


def _is_solved_form(text: str) -> bool:
    """`x = 5`, `5 = x`, or a bare number as typed — an answer, not an intermediate line."""
    try:
        expr = _parse(text, evaluate=False)
    except Exception:
        return False

    def value(e: sp.Expr) -> bool:
        return not e.free_symbols and not e.has(sp.Add)

    if isinstance(expr, sp.Equality):
        a, b = expr.lhs, expr.rhs
        return (isinstance(a, sp.Symbol) and value(b)) or (isinstance(b, sp.Symbol) and value(a))
    return value(expr)


def evaluate_step_safe(
    latex_user: str,
    latex_target: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_S,
    *,
    use_pool: bool = True,
) -> dict[str, Any]:
    if len(latex_user) > MAX_LATEX_LEN:
        return {
            "success": False,
            "is_equivalent": False,
            "sign_error": False,
            "error": "INPUT_TOO_LONG",
        }

    if not use_pool:
        try:
            return _evaluate(latex_user, latex_target)
        except Exception as e:  # noqa: BLE001
            return {
                "success": False,
                "is_equivalent": False,
                "sign_error": False,
                "error": f"PARSE_ERROR: {e}",
            }

    future = _get_pool().submit(_evaluate, latex_user, latex_target)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeout:
        # ponytail: stuck worker only replaced on pool recycle; upgrade: pebble kill
        return {
            "success": False,
            "is_equivalent": False,
            "sign_error": False,
            "error": "EVALUATION_TIMEOUT",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "is_equivalent": False,
            "sign_error": False,
            "error": f"PARSE_ERROR: {e}",
        }
