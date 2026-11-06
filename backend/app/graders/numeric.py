"""``numeric``: ``{"value": 9.81, "unit"?: "m/s^2"}`` vs ``{"value", "unit"?, "tolerance"?, "abs_tolerance"?}``.

``tolerance`` is relative (clamped 0–0.2); ``abs_tolerance`` is absolute (NumberLine snap width).
"""

from __future__ import annotations

import math
from typing import Any

from app.graders import GradeResult, bad_answer, scored

# ponytail: flat unit table, no compound-unit algebra (km/h listed explicitly).
# Upgrade path: `pint` when science items need arbitrary unit expressions.
UNITS: dict[str, tuple[str, float]] = {
    "mm": ("m", 0.001), "cm": ("m", 0.01), "m": ("m", 1.0), "km": ("m", 1000.0),
    "mg": ("kg", 1e-6), "g": ("kg", 0.001), "kg": ("kg", 1.0),
    "ms": ("s", 0.001), "s": ("s", 1.0), "min": ("s", 60.0), "h": ("s", 3600.0),
    "m/s": ("m/s", 1.0), "km/h": ("m/s", 1 / 3.6),
    "m/s^2": ("m/s^2", 1.0), "cm/s^2": ("m/s^2", 0.01),
    "mL": ("L", 0.001), "L": ("L", 1.0),
    "N": ("N", 1.0), "kN": ("N", 1000.0), "J": ("J", 1.0), "kJ": ("J", 1000.0),
    "W": ("W", 1.0), "kW": ("W", 1000.0), "Pa": ("Pa", 1.0), "kPa": ("Pa", 1000.0),
    "mol": ("mol", 1.0), "mmol": ("mol", 0.001), "K": ("K", 1.0), "%": ("%", 1.0),
    "mol/L": ("mol/L", 1.0), "M": ("mol/L", 1.0), "mmol/L": ("mol/L", 0.001), "mM": ("mol/L", 0.001),
    "g/mol": ("g/mol", 1.0), "atm": ("Pa", 101325.0),
}


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


def _base(value: float, unit: Any) -> tuple[float, str] | None:
    u = str(unit or "").replace(" ", "")
    if not u:
        return value, ""
    if u not in UNITS:
        return None
    base, factor = UNITS[u]
    return value * factor, base


def grade_numeric(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    want, got = _num(spec["value"]), _num(answer.get("value"))
    if want is None or got is None:
        return bad_answer()
    # A bare number is read in the spec's unit.
    target, mine = _base(want, spec.get("unit")), _base(got, answer.get("unit") or spec.get("unit"))
    if target is None or mine is None:
        return bad_answer()
    if target[1] != mine[1]:
        return scored(0.0)
    rel = min(0.2, max(0.0, _num(spec.get("tolerance", 0)) or 0.0))
    absolute = max(0.0, _num(spec.get("abs_tolerance", 0)) or 0.0)
    if spec.get("unit"):
        absolute = _base(absolute, spec.get("unit"))[0]  # type: ignore[index]
    ok = abs(mine[0] - target[0]) <= max(absolute, rel * abs(target[0])) + 1e-9 * max(1.0, abs(target[0]))
    return scored(1.0 if ok else 0.0)
