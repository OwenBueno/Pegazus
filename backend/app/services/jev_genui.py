"""JEV (or heuristic) chooses primary GenUI widget for a practice item."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.component_catalog import ANSWER_WIDGETS
from app.services.jev_client import OPENROUTER_DECISIONS_URL, _breaker, _parse_choice

PRIMARY_CHOICES = ANSWER_WIDGETS


def _looks_plottable(latex: str) -> bool:
    s = (latex or "").strip()
    if not s:
        return False
    return bool(
        "x^" in s.lower()
        or "x^{2}" in s
        or s.lower().startswith("y=")
        or "f(x)" in s.lower()
    )


def _plan_has_valid(plan: dict[str, Any] | None, wtype: str) -> bool:
    if not plan or not isinstance(plan.get("widgets"), list):
        return False
    for w in plan["widgets"]:
        if isinstance(w, str) and w == wtype:
            # string-only QuickCheck/NumberLine/MatchPairs are not valid without props
            return wtype in ("SymbolicStepEditor", "FadedWorkedExample", "VirtualMathKeyboard")
        if isinstance(w, dict) and w.get("type") == wtype:
            props = w.get("props") if isinstance(w.get("props"), dict) else {}
            if wtype == "QuickCheck":
                ch = props.get("choices") or []
                return len(ch) >= 2 and bool(props.get("correctId"))
            if wtype == "NumberLine":
                return all(k in props for k in ("min", "max", "target"))
            if wtype == "MatchPairs":
                return isinstance(props.get("pairs"), list) and len(props["pairs"]) >= 2
            return True
    return False


def heuristic_primary_widget(
    *,
    node_title: str,
    statement_latex: str,
    scaffold_level: int,
    genui_plan: dict[str, Any] | None,
    hint_tier: int | None = None,
) -> str:
    """Pedagogy-aligned fallback when JEV is off / unavailable."""
    del hint_tier  # reserved for socratic overlay elsewhere
    title = (node_title or "").lower()
    sc = max(1, min(3, int(scaffold_level)))

    # Lesson designer picked an answer mode for this problem: honor it, adjusted for scaffold.
    designed = genui_plan.get("primary") if isinstance(genui_plan, dict) else None
    if designed in ("SymbolicStepEditor", "FadedWorkedExample"):
        if sc == 1:
            return "FadedWorkedExample"
        return "SymbolicStepEditor" if sc >= 3 else designed
    if designed in PRIMARY_CHOICES and _plan_has_valid(genui_plan, designed):
        return designed

    place_ish = any(
        k in title for k in ("place value", "digit", "which place", "hundreds", "tens")
    )
    line_ish = any(k in title for k in ("number line", "magnitude", "locate", "estimate"))
    match_ish = any(k in title for k in ("expanded", "standard form", "match"))

    # Explicit symbolic in plan → keep hybrid/symbolic unless skill is clearly selection
    plan_types: set[str] = set()
    if genui_plan and isinstance(genui_plan.get("widgets"), list):
        for w in genui_plan["widgets"]:
            if isinstance(w, str):
                plan_types.add(w)
            elif isinstance(w, dict) and w.get("type"):
                plan_types.add(str(w["type"]))

    if sc == 1 and not place_ish and not line_ish and not match_ish:
        return "FadedWorkedExample"

    if place_ish and _plan_has_valid(genui_plan, "QuickCheck"):
        return "QuickCheck"
    if line_ish and _plan_has_valid(genui_plan, "NumberLine"):
        return "NumberLine"
    if match_ish and _plan_has_valid(genui_plan, "MatchPairs"):
        return "MatchPairs"

    if "SymbolicStepEditor" in plan_types and not (place_ish or line_ish or match_ish):
        return "SymbolicStepEditor"

    # Honor plan primary if selection-valid
    for pref in ("QuickCheck", "NumberLine", "MatchPairs"):
        if _plan_has_valid(genui_plan, pref) and pref in plan_types:
            # only if no competing symbolic for generic titles
            if "SymbolicStepEditor" in plan_types:
                return "SymbolicStepEditor"
            return pref

    if sc == 1:
        return "FadedWorkedExample"
    return "SymbolicStepEditor"


def choose_primary_widget(
    *,
    node_title: str,
    statement_latex: str,
    scaffold_level: int,
    genui_plan: dict[str, Any] | None,
    hint_tier: int | None = None,
    recent_verdict: str | None = None,
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> str:
    """
    Return a primary widget type. Never returns a selection widget without valid plan props.
    """
    fallback = heuristic_primary_widget(
        node_title=node_title,
        statement_latex=statement_latex,
        scaffold_level=scaffold_level,
        genui_plan=genui_plan,
        hint_tier=hint_tier,
    )

    if settings.ai_enabled.lower() in ("0", "false", "no", "off"):
        return fallback
    key = api_key or settings.openrouter_api_key
    if not key or not _breaker.allow():
        return fallback

    available = [c for c in PRIMARY_CHOICES if c == "SymbolicStepEditor" or c == "FadedWorkedExample" or _plan_has_valid(genui_plan, c)]
    if "SymbolicStepEditor" not in available:
        available.append("SymbolicStepEditor")

    payload = {
        "model": settings.jev_model,
        "state": {
            "node_title": (node_title or "")[:120],
            "statement_latex": (statement_latex or "")[:200],
            "scaffold_level": max(1, min(3, int(scaffold_level))),
            "hint_tier": hint_tier or 0,
            "recent_verdict": recent_verdict or "",
            "plan_has_quickcheck": _plan_has_valid(genui_plan, "QuickCheck"),
            "plan_has_numberline": _plan_has_valid(genui_plan, "NumberLine"),
            "plan_has_match": _plan_has_valid(genui_plan, "MatchPairs"),
            "plottable": _looks_plottable(statement_latex or ""),
            "designer_primary": (genui_plan or {}).get("primary") or "",
        },
        "questions": {
            "primary_widget": {
                "type": "choice",
                "instructions": (
                    "Pick the best primary answer widget for this learner right now. "
                    "Scaffold 1 → prefer FadedWorkedExample. "
                    "Place-value / MC → QuickCheck only if plan_has_quickcheck. "
                    "Equations / compute → SymbolicStepEditor. "
                    "Do not pick QuickCheck/NumberLine/MatchPairs unless the plan flag is true."
                ),
                "criteria": {c: c for c in available} | {"none": "None of the above"},
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pegazus.local",
        "X-Title": "Pegazus",
    }
    timeout = settings.jev_timeout_ms / 1000.0
    own = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.post(OPENROUTER_DECISIONS_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            _breaker.record(True)
            return fallback
        data = resp.json()
        answers = data.get("answers") or data.get("results") or data
        if not isinstance(answers, dict):
            _breaker.record(True)
            return fallback
        choice = _parse_choice(answers, "primary_widget", settings.jev_choice_confidence)
        _breaker.record(False)
        if not choice or choice == "none" or choice not in PRIMARY_CHOICES:
            return fallback
        if choice in ("QuickCheck", "NumberLine", "MatchPairs") and not _plan_has_valid(
            genui_plan, choice
        ):
            return fallback
        return choice
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, KeyError, TypeError):
        _breaker.record(True)
        return fallback
    finally:
        if own:
            http.close()


def reorder_plan_for_primary(
    plan_entries: list[dict[str, Any]],
    primary: str,
    *,
    scaffold_level: int = 2,
) -> list[dict[str, Any]]:
    """Put primary type first; faded-only at scaffold 1 (no competing blank editor)."""
    if not plan_entries:
        return [{"type": primary, "props": {}}]

    primary_entry = None
    rest: list[dict[str, Any]] = []
    for e in plan_entries:
        if e.get("type") == primary and primary_entry is None:
            primary_entry = e
        else:
            rest.append(e)
    if primary_entry is None:
        primary_entry = {"type": primary, "props": {}}

    out = [primary_entry] + rest
    sc = max(1, min(3, int(scaffold_level)))

    if primary == "FadedWorkedExample":
        # No competing SymbolicStepEditor while faded is primary (scaffold 1–2)
        if sc <= 2:
            out = [e for e in out if e["type"] != "SymbolicStepEditor"]
        types = {e["type"] for e in out}
        if "VirtualMathKeyboard" not in types:
            out.append(
                {"type": "VirtualMathKeyboard", "props": {"targetWidgetId": "faded"}}
            )
    elif primary == "SymbolicStepEditor":
        types = {e["type"] for e in out}
        if "VirtualMathKeyboard" not in types:
            out.append({"type": "VirtualMathKeyboard", "props": {}})
        if sc >= 2:
            out = [e for e in out if e["type"] != "FadedWorkedExample"]
    # Drop Symbolic/keyboard if primary is a selection widget (selection-primary mode)
    if primary in ("QuickCheck", "NumberLine", "MatchPairs"):
        out = [
            e
            for e in out
            if e["type"] not in ("SymbolicStepEditor", "VirtualMathKeyboard", "FadedWorkedExample")
        ]
    # Dedupe by type preserving order
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for e in out:
        t = e["type"]
        if t in seen:
            continue
        seen.add(t)
        deduped.append(e)
    return deduped
