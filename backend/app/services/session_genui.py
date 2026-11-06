"""Build GenUI workspace payloads for practice sessions (server-side)."""

from __future__ import annotations

import re
from typing import Any

from app.graders.legacy import legacy_parts
from app.services.component_catalog import SELECTION_PRIMARY, WORKSPACE_WIDGETS

MAX_WIDGETS = 4

ALLOWED_TYPES = WORKSPACE_WIDGETS


def plot_expressions_from_latex(latex: str) -> list[str] | None:
    s = latex.strip()
    if re.match(r"^(?:y|f\s*\(\s*x\s*\))\s*=", s, re.I):
        return [s]
    if re.search(r"x\s*\^\s*\{?\s*2\s*\}?", s, re.I) or "x^{2}" in s:
        return [s]
    # Strip \times / \div so "x" inside times does not look like a variable
    plain = re.sub(r"\\(?:times|div|cdot|left|right)\b", "", s)
    plain = plain.replace("\\", "")
    if "=" in plain and not re.search(r"[<>]", plain) and re.search(r"(?<![a-z])x(?![a-z])", plain, re.I):
        return [s]
    return None


def build_session_genui(
    *,
    session_id: str,
    node_id: str,
    item_id: str,
    statement_latex: str,
    steps: list[dict[str, Any]],
    step_index: int,
    scaffold_level: int,
    hint_tier: int | None = None,
    hint_prompt: str | None = None,
    active_status: str = "PENDING",
    genui_plan: dict[str, Any] | None = None,
    student_latex_by_step: dict[int, str] | None = None,
    node_title: str = "",
    recent_verdict: str | None = None,
    api_key: str | None = None,
    use_jev_layout: bool = True,
    demo_steps: list[dict[str, Any]] | None = None,
    parts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Merge cached genui_plan (typed widgets+props or name list) with live session state.
    Caps at MAX_WIDGETS. Student latex wins for prior steps.
    Optionally JEV/heuristic picks primary widget order.
    Scaffold 1 = faded complete-the-blank (no competing blank editor).
    """
    student = student_latex_by_step or {}
    sc = max(1, min(3, int(scaffold_level)))

    def _latex_for(i: int, canonical: str, *, blank_active: bool) -> str:
        if i < step_index:
            return student.get(i) or canonical
        if blank_active:
            return ""
        return canonical

    # Symbolic editor always blanks the active step; faded uses gap_latex at scaffold 1.
    blank_symbolic = True
    blank_faded = sc >= 2

    display_steps = []
    for i, s in enumerate(steps[: step_index + 1]):
        canonical = str(s.get("latex") or "")
        row: dict[str, Any] = {
            "stepNumber": i + 1,
            "latexExpression": _latex_for(i, canonical, blank_active=blank_symbolic),
            "isLocked": i < step_index,
            "status": "VALID" if i < step_index else active_status,
        }
        just = s.get("justification")
        if just:
            row["justification"] = str(just)
        display_steps.append(row)
    if not display_steps:
        display_steps.append(
            {
                "stepNumber": 1,
                "latexExpression": "",
                "isLocked": False,
                "status": active_status,
            }
        )

    faded_steps = _build_faded_steps(
        steps=steps,
        step_index=step_index,
        student=student,
        blank_active=blank_faded,
        active_status=active_status,
        demo_steps=demo_steps,
    )

    active_gap = ""
    if 0 <= step_index < len(steps):
        active_gap = str(steps[step_index].get("gap_latex") or "").strip()
    if sc == 1 and not active_gap and demo_steps and step_index < len(demo_steps):
        demo = demo_steps[step_index]
        if isinstance(demo, dict):
            active_gap = str(demo.get("gap_latex") or demo.get("latex") or "").strip()
        elif isinstance(demo, str):
            active_gap = demo.strip()
    # Scaffold 1 prefers partial gap; never dump the full answer into the field.
    if sc == 1 and active_gap and 0 <= step_index < len(steps):
        full = str(steps[step_index].get("latex") or "").strip()
        if active_gap == full:
            active_gap = ""

    if parts is None:
        parts = legacy_parts(steps, genui_plan, item_id)[0]
    part = parts[min(max(step_index, 0), len(parts) - 1)] if parts else None
    sel_part = part if part and part.get("component") in SELECTION_PRIMARY else None
    # Selection widgets render only from the item's own part (public props, graded server-side);
    # a QuickCheck/NumberLine riding along a sympy item could not be graded, so it is dropped.
    plan_entries = [e for e in _parse_plan_entries(genui_plan) if e["type"] not in SELECTION_PRIMARY]
    if sel_part:
        plan_entries.insert(0, {"type": sel_part["component"], "props": sel_part.get("props") or {}})
    if not plan_entries:
        plan_entries = _default_plan_entries(sc, statement_latex)

    if sel_part:
        from app.services.jev_genui import reorder_plan_for_primary

        primary = sel_part["component"]
        plan_entries = reorder_plan_for_primary(plan_entries, primary, scaffold_level=sc)
    elif use_jev_layout:
        from app.services.jev_genui import choose_primary_widget, reorder_plan_for_primary

        primary = choose_primary_widget(
            node_title=node_title,
            statement_latex=statement_latex,
            scaffold_level=sc,
            genui_plan=genui_plan,
            hint_tier=hint_tier,
            recent_verdict=recent_verdict,
            api_key=api_key,
        )
        plan_entries = reorder_plan_for_primary(plan_entries, primary, scaffold_level=sc)
    else:
        primary = plan_entries[0]["type"] if plan_entries else "SymbolicStepEditor"

    widgets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in plan_entries:
        wtype = entry["type"]
        if wtype not in ALLOWED_TYPES or wtype in seen:
            continue
        if wtype == "SocraticDialogueBox" and not (hint_tier and hint_prompt):
            continue
        if wtype == "FadedWorkedExample" and sc >= 3:
            continue
        # Scaffold ≤2: faded-only composition (no competing blank SymbolicStepEditor)
        if sc <= 2 and wtype == "SymbolicStepEditor" and (
            primary == "FadedWorkedExample"
            or any(e.get("type") == "FadedWorkedExample" for e in plan_entries)
        ):
            continue

        built = _build_widget(
            wtype,
            entry.get("props") or {},
            statement_latex=statement_latex,
            display_steps=display_steps,
            faded_steps=faded_steps,
            step_index=step_index,
            scaffold_level=sc,
            hint_tier=hint_tier,
            hint_prompt=hint_prompt,
            gap_latex=active_gap,
        )
        if built:
            widgets.append(built)
            seen.add(wtype)
        if len(widgets) >= MAX_WIDGETS:
            break

    selection = bool(seen & SELECTION_PRIMARY)
    # Do not force SymbolicStepEditor when faded is the scaffold-1 primary
    if (
        not selection
        and "SymbolicStepEditor" not in seen
        and "FadedWorkedExample" not in seen
    ):
        built_ed = _build_widget(
            "SymbolicStepEditor",
            {},
            statement_latex=statement_latex,
            display_steps=display_steps,
            faded_steps=faded_steps,
            step_index=step_index,
            scaffold_level=sc,
            hint_tier=hint_tier,
            hint_prompt=hint_prompt,
            gap_latex=active_gap,
        )
        if built_ed:
            widgets.insert(0, built_ed)
            seen.add("SymbolicStepEditor")

    kbd_target = "faded" if "FadedWorkedExample" in seen and "SymbolicStepEditor" not in seen else "steps"
    if (
        not selection
        and ("SymbolicStepEditor" in seen or "FadedWorkedExample" in seen)
        and "VirtualMathKeyboard" not in seen
        and len(widgets) < MAX_WIDGETS
    ):
        built_kbd = _build_widget(
            "VirtualMathKeyboard",
            {"targetWidgetId": kbd_target},
            statement_latex=statement_latex,
            display_steps=display_steps,
            faded_steps=faded_steps,
            step_index=step_index,
            scaffold_level=sc,
            hint_tier=hint_tier,
            hint_prompt=hint_prompt,
            gap_latex=active_gap,
        )
        if built_kbd:
            widgets.append(built_kbd)

    final = [w for w in widgets[:MAX_WIDGETS] if w]
    answer_mode = (
        "selection"
        if any(w["type"] in SELECTION_PRIMARY for w in final)
        and not any(w["type"] == "SymbolicStepEditor" for w in final)
        and not any(w["type"] == "FadedWorkedExample" for w in final)
        else "symbolic"
    )
    return {
        "sessionId": session_id,
        "nodeId": node_id,
        "itemId": item_id,
        "scaffoldLevel": sc,
        "answerMode": answer_mode,
        "widgets": final,
    }


def _build_faded_steps(
    *,
    steps: list[dict[str, Any]],
    step_index: int,
    student: dict[int, str],
    blank_active: bool,
    active_status: str,
    demo_steps: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Prior steps show canonical (or student); active blanks unless gap/demo fills display."""
    out: list[dict[str, Any]] = []
    slice_steps = steps[: step_index + 1] if steps else []
    # If item steps are thin but teach beat left demo_steps, seed structure at start
    if not slice_steps and demo_steps:
        slice_steps = [
            d if isinstance(d, dict) else {"latex": str(d)} for d in demo_steps[: step_index + 1]
        ]
    for i, s in enumerate(slice_steps):
        if not isinstance(s, dict):
            s = {"latex": str(s)}
        canonical = str(s.get("latex") or "")
        if i < step_index:
            latex = student.get(i) or canonical
        elif blank_active:
            latex = ""
        else:
            # scaffold 1: show empty MathField line (gapLatex prop holds partial)
            latex = ""
        row_f: dict[str, Any] = {
            "stepNumber": i + 1,
            "latexExpression": latex,
            "isLocked": i < step_index,
            "status": "VALID" if i < step_index else (
                active_status if active_status in ("VALID", "INVALID", "PENDING") else "PENDING"
            ),
        }
        just = s.get("justification")
        if just:
            row_f["justification"] = str(just)
        out.append(row_f)
    if not out:
        out.append(
            {
                "stepNumber": 1,
                "latexExpression": "",
                "isLocked": False,
                "status": "PENDING",
            }
        )
    return out


def _parse_plan_entries(genui_plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not genui_plan or not isinstance(genui_plan.get("widgets"), list):
        return []
    out: list[dict[str, Any]] = []
    for w in genui_plan["widgets"]:
        if isinstance(w, str):
            name = w.strip()
            if name in ALLOWED_TYPES:
                out.append({"type": name, "props": {}})
        elif isinstance(w, dict):
            name = str(w.get("type") or "").strip()
            if name in ALLOWED_TYPES:
                props = w.get("props") if isinstance(w.get("props"), dict) else {}
                out.append({"type": name, "props": props})
    return out


def _default_plan_entries(scaffold_level: int, statement_latex: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if scaffold_level == 1:
        out.append({"type": "FadedWorkedExample", "props": {}})
        out.append({"type": "VirtualMathKeyboard", "props": {"targetWidgetId": "faded"}})
    elif scaffold_level == 2:
        out.append({"type": "FadedWorkedExample", "props": {}})
        out.append({"type": "VirtualMathKeyboard", "props": {"targetWidgetId": "faded"}})
    else:
        out.append({"type": "SymbolicStepEditor", "props": {}})
        out.append({"type": "VirtualMathKeyboard", "props": {}})
    if plot_expressions_from_latex(statement_latex):
        out.append({"type": "FunctionPlotter", "props": {}})
    return out


def _build_widget(
    wtype: str,
    props: dict[str, Any],
    *,
    statement_latex: str,
    display_steps: list[dict[str, Any]],
    faded_steps: list[dict[str, Any]],
    step_index: int,
    scaffold_level: int,
    hint_tier: int | None,
    hint_prompt: str | None,
    gap_latex: str = "",
) -> dict[str, Any] | None:
    if wtype == "SymbolicStepEditor":
        return {
            "id": "steps",
            "type": "SymbolicStepEditor",
            "visible": True,
            "props": {
                "targetVariable": str(props.get("targetVariable") or "x"),
                "inlineValidation": True,
                "activeStepIndex": min(step_index, len(display_steps) - 1),
                "initialSteps": display_steps,
            },
        }
    if wtype == "VirtualMathKeyboard":
        return {
            "id": "kbd",
            "type": "VirtualMathKeyboard",
            "visible": True,
            "props": {
                "layout": props.get("layout") if props.get("layout") in ("algebra", "calculus") else "algebra",
                "targetWidgetId": str(props.get("targetWidgetId") or "steps"),
            },
        }
    if wtype == "FadedWorkedExample":
        fs = faded_steps or [
            {"stepNumber": 1, "latexExpression": "", "isLocked": False, "status": "PENDING"}
        ]
        fprops: dict[str, Any] = {
            "problemStatement": str(props.get("problemStatement") or statement_latex),
            "steps": fs,
            "activeStepIndex": min(step_index, max(0, len(fs) - 1)),
            "scaffoldLevel": scaffold_level,
        }
        if gap_latex:
            fprops["gapLatex"] = gap_latex[:200]
        return {
            "id": "faded",
            "type": "FadedWorkedExample",
            "visible": True,
            "props": fprops,
        }
    if wtype == "FunctionPlotter":
        exprs = props.get("expressions")
        if not isinstance(exprs, list) or not exprs:
            exprs = plot_expressions_from_latex(statement_latex) or [statement_latex]
        domain = props.get("domain")
        if not (isinstance(domain, list) and len(domain) == 2):
            domain = [-10, 10]
        out_props: dict[str, Any] = {
            "expressions": [str(e) for e in exprs[:4]],
            "domain": [float(domain[0]), float(domain[1])],
        }
        if isinstance(props.get("sliders"), list):
            out_props["sliders"] = props["sliders"][:4]
        if props.get("textAlt"):
            out_props["textAlt"] = str(props["textAlt"])[:400]
        return {"id": "plot", "type": "FunctionPlotter", "visible": True, "props": out_props}
    if wtype == "SocraticDialogueBox":
        return {
            "id": "socratic",
            "type": "SocraticDialogueBox",
            "visible": True,
            "props": {
                "hintTier": max(1, min(3, int(hint_tier or props.get("hintTier") or 1))),
                "prompt": str(hint_prompt or props.get("prompt") or "")[:240],
                **(
                    {"highlightElementId": str(props["highlightElementId"])}
                    if props.get("highlightElementId")
                    else {}
                ),
            },
        }
    # Selection widgets get a part's public props: no answer keys (graded from answer_spec).
    if wtype == "QuickCheck":
        choices = props.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            return None
        clean = []
        for c in choices[:6]:
            if isinstance(c, dict) and c.get("id") and c.get("label"):
                clean.append({"id": str(c["id"])[:40], "label": str(c["label"])[:200]})
        if len(clean) < 2:
            return None
        qprops: dict[str, Any] = {
            "prompt": str(props.get("prompt") or "Choose the best answer")[:400],
            "choices": clean,
        }
        if props.get("labelsAreLatex"):
            qprops["labelsAreLatex"] = True
        return {"id": "quick", "type": "QuickCheck", "visible": True, "props": qprops}
    if wtype == "ConceptCard":
        body = str(props.get("body_md") or "").strip()
        title = str(props.get("title") or "").strip()
        if not body or not title:
            return None
        out: dict[str, Any] = {
            "id": "concept",
            "type": "ConceptCard",
            "visible": True,
            "props": {"title": title[:120], "body_md": body[:2500]},
        }
        if props.get("latex"):
            out["props"]["latex"] = str(props["latex"])[:500]
        if props.get("gateLabel"):
            out["props"]["gateLabel"] = str(props["gateLabel"])[:80]
        return out
    if wtype == "NumberLine":
        try:
            mn = float(props["min"])
            mx = float(props["max"])
        except (KeyError, TypeError, ValueError):
            return None
        if mx <= mn:
            return None
        out_nl: dict[str, Any] = {
            "id": "nline",
            "type": "NumberLine",
            "visible": True,
            "props": {"min": mn, "max": mx},
        }
        if props.get("step") is not None:
            out_nl["props"]["step"] = float(props["step"])
        if props.get("prompt"):
            out_nl["props"]["prompt"] = str(props["prompt"])[:240]
        return out_nl
    if wtype == "MatchPairs":
        lefts, rights = props.get("lefts"), props.get("rights")
        if not (isinstance(lefts, list) and isinstance(rights, list) and 2 <= len(lefts) == len(rights) <= 6):
            return None
        out_m: dict[str, Any] = {
            "id": "match",
            "type": "MatchPairs",
            "visible": True,
            "props": {"lefts": [str(s)[:200] for s in lefts], "rights": [str(s)[:200] for s in rights]},
        }
        if props.get("prompt"):
            out_m["props"]["prompt"] = str(props["prompt"])[:240]
        return out_m
    # Core answer components (ShortAnswer, Cloze, …): props were sanitized key-free at write time.
    if wtype in SELECTION_PRIMARY:
        return {"id": "answer", "type": wtype, "visible": True, "props": dict(props)}
    return None


def update_scaffold_from_band(
    *,
    current: int,
    recent_success_rate: float,
) -> int:
    """Lite US-4.1: high accuracy → less scaffold; low → more support."""
    cur = max(1, min(3, int(current)))
    if recent_success_rate >= 0.8 and cur < 3:
        return cur + 1
    if recent_success_rate <= 0.4 and cur > 1:
        return cur - 1
    return cur


def demo_steps_for_item(
    beats: list[Any] | None,
    item_id: Any,
) -> list[dict[str, Any]] | None:
    """Nearest prior teach beat demo_steps for this problem beat (course insight reuse)."""
    if not beats:
        return None
    last_demo: list[dict[str, Any]] | None = None
    target = str(item_id)
    for b in beats:
        if not isinstance(b, dict):
            continue
        if b.get("kind") == "teach" or b.get("type") in ("worked_example", "try_it", "important"):
            raw = b.get("demo_steps")
            if isinstance(raw, list) and raw:
                last_demo = [d if isinstance(d, dict) else {"latex": str(d)} for d in raw[:6]]
        if b.get("kind") == "problem" and str(b.get("item_id") or "") == target:
            return last_demo
    return last_demo
