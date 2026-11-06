"""Build lesson_beats + genui_plan once at materialize (AI-composed sequence)."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from typing import Any

from app.pipeline.item_gen import GENERIC_COMPONENTS, allowed_components
from app.services.component_catalog import (
    ANSWER_WIDGETS,
    COMPONENTS,
    LAYOUTS,
    SELECTION_PRIMARY,
    VISUALS,
    WORKSPACE_WIDGETS,
    catalog_prompt,
    norm_url,
    sanitize_visual,
)
from app.services.llm import chat_json
from app.services.subject_profile import MATH_PROFILE, is_math, profile_prompt
from app.workers.math_evaluator import evaluate_step_safe

_log = logging.getLogger(__name__)

# genui_plan widgets go through the workspace sanitizers below; other visuals ride on beat.visual.
ALLOWED_WIDGETS = WORKSPACE_WIDGETS

MAX_PLAN_WIDGETS = 4


def plan_is_selection_primary(genui_plan: dict[str, Any] | None) -> bool:
    if not genui_plan or not isinstance(genui_plan.get("widgets"), list):
        return False
    for w in genui_plan["widgets"]:
        name = w if isinstance(w, str) else (w.get("type") if isinstance(w, dict) else None)
        if name in SELECTION_PRIMARY:
            return True
    return False


def collapse_to_final_step(steps: list[Any]) -> list[dict[str, Any]]:
    """Selection-primary practice is single-step (final answer only)."""
    if not steps:
        return []
    last = steps[-1]
    if isinstance(last, dict):
        return [dict(last)]
    return [{"latex": str(last), "sympy": str(last), "operation": "FINAL"}]


def normalize_genui_plan(raw: Any) -> dict[str, Any]:
    """Accept name list or typed [{type, props}]; strip unknown.

    Force SymbolicStepEditor only when no selection-primary widget is present.
    """
    if isinstance(raw, dict):
        cand = raw.get("widgets") or []
    elif isinstance(raw, list):
        cand = raw
    else:
        cand = []

    widgets: list[Any] = []
    seen: set[str] = set()
    for w in cand:
        if isinstance(w, str):
            name = w.strip()
            if name in ALLOWED_WIDGETS and name not in seen:
                widgets.append(name)
                seen.add(name)
        elif isinstance(w, dict):
            name = str(w.get("type") or "").strip()
            if name not in ALLOWED_WIDGETS or name in seen:
                continue
            props = w.get("props") if isinstance(w.get("props"), dict) else {}
            if name in (
                "QuickCheck",
                "ConceptCard",
                "NumberLine",
                "MatchPairs",
                "FunctionPlotter",
                "SocraticDialogueBox",
            ):
                clean_props = _sanitize_widget_props(name, props)
                # Reject incomplete QuickCheck so we don't ship broken MC plans
                if name == "QuickCheck":
                    choices = clean_props.get("choices") or []
                    if len(choices) < 2 or not clean_props.get("correctId"):
                        continue
                    if clean_props["correctId"] not in {c["id"] for c in choices}:
                        continue
                if name == "NumberLine" and not {
                    "min",
                    "max",
                    "target",
                }.issubset(clean_props.keys()):
                    continue
                if name == "MatchPairs" and len(clean_props.get("pairs") or []) < 2:
                    continue
                widgets.append({"type": name, "props": clean_props})
            else:
                widgets.append(name)
            seen.add(name)
        if len(widgets) >= MAX_PLAN_WIDGETS:
            break

    selection = bool(seen & SELECTION_PRIMARY)
    if not selection:
        if "SymbolicStepEditor" not in seen:
            widgets.insert(0, "SymbolicStepEditor")
            seen.add("SymbolicStepEditor")
        if "VirtualMathKeyboard" not in seen and len(widgets) < MAX_PLAN_WIDGETS:
            widgets.append("VirtualMathKeyboard")
    out: dict[str, Any] = {"widgets": widgets[:MAX_PLAN_WIDGETS]}
    # Designer's chosen answer mode — kept only if that widget survived validation.
    primary = raw.get("primary") if isinstance(raw, dict) else None
    if isinstance(primary, str) and primary in seen:
        out["primary"] = primary
    return out


def _attach_correct_latex(out: dict[str, Any], props: dict[str, Any]) -> None:
    cl = props.get("correct_latex") or props.get("correctLatex")
    if cl:
        out["correct_latex"] = str(cl)[:200]


def _sanitize_widget_props(wtype: str, props: dict[str, Any]) -> dict[str, Any]:
    if wtype == "QuickCheck":
        choices = props.get("choices")
        clean = []
        if isinstance(choices, list):
            for c in choices[:6]:
                if isinstance(c, dict) and c.get("id") and c.get("label"):
                    clean.append(
                        {"id": str(c["id"])[:40], "label": str(c["label"])[:200]}
                    )
        out: dict[str, Any] = {
            "prompt": str(props.get("prompt") or "")[:400],
            "choices": clean,
            "correctId": str(props.get("correctId") or "")[:40],
        }
        if props.get("explanation"):
            out["explanation"] = str(props["explanation"])[:400]
        if props.get("labelsAreLatex"):
            out["labelsAreLatex"] = True
        _attach_correct_latex(out, props)
        return out
    if wtype == "ConceptCard":
        out_c: dict[str, Any] = {
            "title": str(props.get("title") or "")[:120],
            "body_md": str(props.get("body_md") or "")[:2500],
        }
        if props.get("latex"):
            out_c["latex"] = str(props["latex"])[:500]
        if props.get("gateLabel"):
            out_c["gateLabel"] = str(props["gateLabel"])[:80]
        return out_c
    if wtype == "NumberLine":
        out_n: dict[str, Any] = {}
        for k in ("min", "max", "target", "step", "tolerance"):
            if props.get(k) is not None:
                try:
                    out_n[k] = float(props[k])
                except (TypeError, ValueError):
                    pass
        if props.get("prompt"):
            out_n["prompt"] = str(props["prompt"])[:240]
        _attach_correct_latex(out_n, props)
        if "correct_latex" not in out_n and "target" in out_n:
            t = out_n["target"]
            out_n["correct_latex"] = (
                str(int(t)) if float(t).is_integer() else str(t)
            )[:200]
        return out_n
    if wtype == "MatchPairs":
        pairs = props.get("pairs")
        clean_p = []
        if isinstance(pairs, list):
            for p in pairs[:6]:
                if (
                    isinstance(p, dict)
                    and p.get("id")
                    and p.get("left")
                    and p.get("right")
                ):
                    clean_p.append(
                        {
                            "id": str(p["id"])[:40],
                            "left": str(p["left"])[:200],
                            "right": str(p["right"])[:200],
                        }
                    )
        out_m: dict[str, Any] = {"pairs": clean_p}
        if props.get("prompt"):
            out_m["prompt"] = str(props["prompt"])[:240]
        _attach_correct_latex(out_m, props)
        return out_m
    if wtype == "FunctionPlotter":
        out_f: dict[str, Any] = {}
        if isinstance(props.get("expressions"), list):
            out_f["expressions"] = [str(e)[:200] for e in props["expressions"][:4]]
        if isinstance(props.get("domain"), list) and len(props["domain"]) == 2:
            try:
                out_f["domain"] = [
                    float(props["domain"][0]),
                    float(props["domain"][1]),
                ]
            except (TypeError, ValueError):
                pass
        if props.get("textAlt"):
            out_f["textAlt"] = str(props["textAlt"])[:400]
        if isinstance(props.get("sliders"), list):
            out_f["sliders"] = props["sliders"][:4]
        return out_f
    if wtype == "SocraticDialogueBox":
        return {
            "prompt": str(props.get("prompt") or "")[:240],
            "hintTier": max(1, min(3, int(props.get("hintTier") or 1))),
        }
    return {}


def _normalize_demo_steps(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for row in raw[:6]:
        if isinstance(row, dict):
            latex = str(row.get("latex") or row.get("statement_latex") or "").strip()
        else:
            latex = str(row or "").strip()
        if latex:
            out.append({"latex": latex[:200]})
    return out


MIN_TEACH_BODY = 400


MAX_TEACH_BODY = 4000


def _teach_beat(row: dict[str, Any], kind: str, *, math_mode: bool = True) -> dict[str, Any] | None:
    label = str(row.get("type") or kind or "teach").strip()[:40] or "teach"
    if label in ("problem", "practice", "exercise", "teach"):
        label = "concept"
    body = str(row.get("body_md") or row.get("body") or "").strip()
    if not body:
        return None
    title = str(row.get("title") or label.replace("_", " ").title())[:80]
    beat: dict[str, Any] = {"type": label, "title": title, "body_md": body[:MAX_TEACH_BODY]}
    demo = _normalize_demo_steps(row.get("demo_steps")) if math_mode else []
    if demo:
        beat["demo_steps"] = demo[:6]
    return beat


def cited_urls(brief: dict[str, Any] | None) -> set[str]:
    """``norm_url`` keys of the URLs research returned: the only links lesson content may carry."""
    return {norm_url(s["url"]) for s in (brief or {}).get("sources") or [] if isinstance(s, dict) and s.get("url")}


def citable_sources(brief: dict[str, Any] | None) -> list[dict[str, str]]:
    """Research sources as prompt input: what may be linked, and the quote that backs it."""
    return [
        {k: str(s.get(k) or "") for k in ("title", "url", "quote")}
        for s in (brief or {}).get("sources") or []
        if isinstance(s, dict) and s.get("url")
    ]


def _attach_visual(
    beat: dict[str, Any], row: dict[str, Any], missing: list[str], dropped: list[str], urls: set[str]
) -> None:
    """Keep the designer's teach visual only if it validates; layout needs a surviving visual."""
    raw = row.get("visual")
    name = str(raw.get("type") or "").strip() if isinstance(raw, dict) else ""
    visual = sanitize_visual(raw, urls) if name in VISUALS and "teach" in COMPONENTS[name]["where"] else None
    if name and not visual:
        (dropped if name in VISUALS else missing).append(name[:60])
    layout = str(row.get("layout") or "stack")
    if visual:
        beat["visual"] = visual
        beat["layout"] = layout if layout in LAYOUTS else "stack"


def _valid_sequence(beats: list[dict[str, Any]]) -> bool:
    if len(beats) < 2 or len(beats) > 12:
        return False
    problems = [b for b in beats if b.get("type") == "problem"]
    if not problems:
        return False
    if beats[0].get("type") == "problem":
        return False
    return True


# ---------------------------------------------------------------------------
# Beats-first lesson design → items generated to spec → bind → critic
# ---------------------------------------------------------------------------

TEACH_TYPES = (
    "intro",
    "concept",
    "worked_example",
    "important_fact",
    "fun_fact",
    "common_mistake",
    "real_world",
    "more_learning",
    "reflection",
    "summary",
)

# Answer modes the designer may pick per problem (all exist in the GenUI registry).
PRIMARY_WIDGETS = ANSWER_WIDGETS

class LessonDesignError(RuntimeError):
    """No valid lesson design after one repair round (never replaced by a static lesson)."""


def _categories(profile: dict[str, Any]) -> list[str]:
    # Non-math notation: item_gen can only build core answers, so math widgets are not offered.
    cats = profile["categories"]
    return cats if is_math(profile) else [c for c in cats if c != "math"]


def _design_system(profile: dict[str, Any], max_problems: int) -> str:
    math_mode, katex = is_math(profile), profile["notation"] in ("math", "chem")
    cats = _categories(profile)
    allowed = [] if math_mode else allowed_components(profile)
    family = [
        n for n, c in COMPONENTS.items()
        if c["category"] in cats and c["category"] not in ("core", "math") and c["where"]
        and (c["role"] == "visual" or n in allowed)
    ]
    return (
        f"You design ONE lesson on a skill of {profile['subject']} as an ordered sequence of beats "
        "(like slides) for a cognitive tutor, grounded in the research brief. Return ONLY JSON: "
        '{"beats":[...],"problem_specs":[...]}.\n'
        + profile_prompt(profile) + "\n"
        'Teach beat: {"kind":"teach","type":"<type>","title":"...","body_md":"...",'
        + ('"demo_steps":[{"latex":"..."}],' if math_mode else "")
        + '"layout":"stack|split|focus","visual":{"type":"<visual component>","props":{...}}}\n'
        'Problem beat: {"kind":"problem","title":"...","spec_index":0}\n'
        'problem_specs[i]: {"facet":"what it practices","misconception":"error it targets",'
        '"difficulty":0.0-1.0,"widget":"<answer component>","visual":"<optional visual component>"}\n'
        "Teach-beat visual components:\n" + catalog_prompt("teach", cats) + "\n"
        "Problem components (widget = answer, visual = picture beside the problem):\n"
        + catalog_prompt("problem", cats) + "\n"
        + ("" if math_mode else f"problem_specs widget must be one of: {', '.join(allowed)}.\n")
        + (
            f"- This subject has dedicated components ({', '.join(family)}): use them wherever they "
            "fit better than a generic one (at least one visual and one answer widget when possible).\n"
            if family else ""
        )
        + f"Teach types: {', '.join(TEACH_TYPES)}.\n"
        "Guidelines (must follow):\n"
        "- 5-10 beats. Open with an intro hook; teach BEFORE the first problem; interleave "
        "teaching and practice (e.g. intro → concept → worked_example → problem → "
        "common_mistake or fun_fact → problem → more_learning → problem → summary). "
        "Vary the order to fit the skill; do not copy this example.\n"
        f"- 2 to {max_problems} problem beats, each pointing at its own spec. Difficulty rises "
        "along the brief's difficulty_ladder; target the brief's misconceptions.\n"
        "- Teach body_md: SUBSTANTIVE Markdown (≥400 chars, 2-4 short paragraphs) with concrete "
        + ("numbers and $...$ inline math" if katex else "examples")
        + ". Never reveal answers to the upcoming problems.\n"
        + (
            "- worked_example and important_fact beats: demo_steps with ≥3 correct KaTeX lines.\n"
            if math_mode
            else "- worked_example beats: walk through one concrete example step by step in body_md.\n"
        )
        + "- fun_fact / real_world: only accurate facts (use the brief's facts/hooks).\n"
        "- Never write URLs or links in any text; only a SourceExcerpt url may cite, and only a "
        "url from citable_sources (others are removed).\n"
        "- Pick the component that best EXPLAINS each beat; a visual's content must match the "
        "beat's text exactly. Omit visual when text alone is clearer. If a component that does "
        "not exist would be clearly better, name it anyway; unknown names are logged for future "
        "components.\n"
        "- layout: stack (text then visual, default), split (text beside visual; only with a "
        "visual), focus (visual carries the idea, short body as caption; only with a visual).\n"
        "- Use at least 2 different visuals per lesson when the topic allows, and at least 2 "
        "different answer widgets across the problems"
        + (
            " (e.g. a QuickCheck that catches the target misconception before multi-step "
            "SymbolicStepEditor practice)."
            if math_mode
            else " (e.g. a QuickCheck on the misconception, then Cloze or OrderSteps, ending with a "
            "ShortAnswer or FreeResponse where the learner explains in their own words)."
        )
    )


_DESIGN_RULES = (
    "Your lesson design was invalid. It must have 2-12 beats, start with a teach beat, have at "
    "least 2 problem beats, and a non-empty problem_specs list they point at. Return the full JSON again."
)


def design_lesson(
    *,
    title: str,
    brief: dict[str, Any] | None,
    context: str,
    api_key: str,
    primer_md: str | None = None,
    max_problems: int = 4,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{beats, specs, missing_widgets}``. Problem beats are ``pending`` until bound.

    One repair retry with the validation rules, then ``LessonDesignError`` (no static lesson).
    """
    profile = profile or MATH_PROFILE
    if not api_key:
        raise LessonDesignError("no API key")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _design_system(profile, max_problems)},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "skill": title,
                    "research_brief": {k: v for k, v in (brief or {}).items() if k != "sources"},
                    "citable_sources": citable_sources(brief),
                    "primer": (primer_md or "")[:1200],
                    "learner_context": context[:1500],
                }
            ),
        },
    ]
    ai = None
    for _ in range(2):
        ai = chat_json(messages, api_key=api_key, task="strong", temperature=0.45)
        if ai is None:
            break  # no_response already spent chat()'s own retries
        design = normalize_design(ai, brief=brief, max_problems=max_problems, profile=profile)
        if design is not None:
            return design
        messages = messages[:2] + [{"role": "user", "content": _DESIGN_RULES}]
    beats = (ai or {}).get("beats")
    _log.warning(
        "design_failed skill=%r reason=%s keys=%s beat_kinds=%s specs=%s",
        title,
        "no_response" if ai is None else "invalid",
        sorted(ai or {}),
        [str((b or {}).get("kind") or (b or {}).get("type")) for b in beats or [] if isinstance(b, dict)],
        len((ai or {}).get("problem_specs") or []),
    )
    raise LessonDesignError("no_response" if ai is None else "invalid design")


def _clean_spec(
    s: dict[str, Any], i: int, n: int, missing: list[str], *, math_mode: bool = True,
    allowed: list[str] | None = None,
) -> dict[str, Any]:
    allowed = allowed or ["QuickCheck"]
    default = "SymbolicStepEditor" if math_mode else allowed[0]
    widget = str(s.get("widget") or default).strip()
    raw_visual = s.get("visual")
    # Designers sometimes send a full {type, props}; the item generator draws the props.
    visual = str((raw_visual.get("type") if isinstance(raw_visual, dict) else raw_visual) or "").strip()
    if widget in VISUALS and not visual:
        visual = widget  # e.g. "FunctionPlotter" as widget: show it beside a step editor
    if widget not in PRIMARY_WIDGETS:
        if widget not in VISUALS:
            missing.append(widget[:60])
        widget = default
    elif math_mode and widget in GENERIC_COMPONENTS and widget not in ("QuickCheck", "MatchPairs"):
        widget = default  # math item_gen builds SymPy steps + QuickCheck/MatchPairs/NumberLine only
    elif not math_mode and widget not in allowed:
        widget = default  # off-profile answer (e.g. SymbolicStepEditor) that item_gen cannot build
    if visual and visual not in VISUALS:
        missing.append(visual[:60])
        visual = ""
    try:
        diff = float(s.get("difficulty"))
    except (TypeError, ValueError):
        diff = 0.25 + 0.5 * i / max(1, n - 1)
    spec = {
        "facet": str(s.get("facet") or "")[:200],
        "misconception": str(s.get("misconception") or "")[:200],
        "difficulty": round(min(0.95, max(0.05, diff)), 2),
        "widget": widget,
    }
    if visual and "problem" in COMPONENTS[visual]["where"]:
        spec["visual"] = visual
    return spec


def normalize_design(
    ai: dict[str, Any],
    *,
    brief: dict[str, Any] | None,
    max_problems: int = 4,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    urls = cited_urls(brief)
    math_mode = is_math(profile)
    raw_beats, raw_specs = ai.get("beats"), ai.get("problem_specs")
    if not isinstance(raw_beats, list) or not isinstance(raw_specs, list):
        return None
    missing: list[str] = []
    dropped: list[str] = []
    rows = [s for s in raw_specs if isinstance(s, dict)][:max_problems]
    allowed = None if math_mode else allowed_components(profile)
    specs = [_clean_spec(s, i, len(rows), missing, math_mode=math_mode, allowed=allowed) for i, s in enumerate(rows)]
    if not specs:
        return None
    beats: list[dict[str, Any]] = []
    used: set[int] = set()
    for row in raw_beats[:12]:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or row.get("type") or "").strip().lower()
        if kind in ("problem", "practice", "exercise"):
            try:
                idx = int(row.get("spec_index"))
            except (TypeError, ValueError):
                idx = -1
            if not (0 <= idx < len(specs)) or idx in used:
                idx = next((j for j in range(len(specs)) if j not in used), -1)
            if idx < 0:
                continue
            used.add(idx)
            beats.append(
                {
                    "type": "problem",
                    "title": str(row.get("title") or "Practice")[:80],
                    "spec_index": idx,
                    "pending": True,
                }
            )
        else:
            beat = _teach_beat(row, kind, math_mode=math_mode)
            if beat:
                _attach_visual(beat, row, missing, dropped, urls)
                beats.append(beat)
    if not _valid_sequence(beats) or sum(1 for b in beats if b["type"] == "problem") < 2:
        return None
    return {"beats": beats, "specs": specs, "missing_widgets": missing, "visuals_dropped": dropped}


def _numeric_value(step: dict[str, Any]) -> float | None:
    raw = str(step.get("sympy") or step.get("latex") or "").replace(" ", "")
    if raw.startswith("Eq(") and raw.endswith(")") and "," in raw:
        raw = raw[3:-1].split(",", 1)[1]
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def plan_for_item(widget: str | None, item: dict[str, Any]) -> dict[str, Any]:
    """Build the problem's GenUI plan from the spec widget + the verified item's extras.

    Falls back to symbolic entry when the item lacks what the widget needs. Generic (§6.2)
    items already carry their answer part: the plan only names it (props live in ``parts``).
    """
    parts = item.get("parts") or []
    if not item.get("statement_latex") and parts and parts[0].get("grader") != "sympy":
        return {"primary": parts[0]["component"], "widgets": [parts[0]["component"]]}
    steps = item.get("steps") or []
    final = steps[-1] if steps else {}
    final_latex = str(final.get("latex") or "")
    prompt = str(item.get("prompt") or "")[:400]
    if widget == "QuickCheck" and item.get("distractors") and final_latex:
        labels = [final_latex] + list(item["distractors"])[:3]
        order = sorted(
            range(len(labels)),
            key=lambda i: hashlib.md5(f"{item.get('id')}:{i}".encode()).hexdigest(),
        )
        choices = [{"id": chr(97 + k), "label": labels[i]} for k, i in enumerate(order)]
        return {
            "primary": "QuickCheck",
            "widgets": [
                {
                    "type": "QuickCheck",
                    "props": {
                        "prompt": prompt or "Choose the correct answer.",
                        "choices": choices,
                        "correctId": choices[order.index(0)]["id"],
                        "correct_latex": final_latex,
                        "labelsAreLatex": True,
                    },
                }
            ],
        }
    if widget == "NumberLine":
        v = _numeric_value(final)
        if v is not None:
            span = max(5.0, abs(v) / 2)
            integer = float(v).is_integer()
            return {
                "primary": "NumberLine",
                "widgets": [
                    {
                        "type": "NumberLine",
                        "props": {
                            "min": math.floor(v - span),
                            "max": math.ceil(v + span),
                            "target": v,
                            "step": 1 if integer else 0.5,
                            "tolerance": 0.5 if integer else 0.25,
                            "prompt": prompt or "Place the answer on the number line.",
                            "correct_latex": final_latex,
                        },
                    }
                ],
            }
    if widget == "MatchPairs" and item.get("pairs"):
        pairs = [{"id": f"p{i + 1}", **p} for i, p in enumerate(item["pairs"])]
        return {
            "primary": "MatchPairs",
            "widgets": [
                {
                    "type": "MatchPairs",
                    "props": {
                        "pairs": pairs,
                        "prompt": prompt or "Match the equivalent forms.",
                        "correct_latex": final_latex,
                    },
                }
            ],
        }
    if widget == "FadedWorkedExample":
        return {"primary": "FadedWorkedExample", "widgets": ["FadedWorkedExample", "VirtualMathKeyboard"]}
    if widget == "FunctionPlotter":
        return {
            "primary": "SymbolicStepEditor",
            "widgets": ["SymbolicStepEditor", "VirtualMathKeyboard", "FunctionPlotter"],
        }
    return {"primary": "SymbolicStepEditor", "widgets": ["SymbolicStepEditor", "VirtualMathKeyboard"]}


def should_collapse_steps(plan: dict[str, Any], steps: list[Any], *, has_attempts: bool) -> bool:
    """Selection answers are single-step — but never rewrite steps learners already answered."""
    return plan_is_selection_primary(plan) and len(steps) > 1 and not has_attempts


def plan_item_for_spec(spec: dict[str, Any] | None, item: dict[str, Any]) -> dict[str, Any]:
    """Set ``item['genui_plan']`` for the spec's widget (collapsing steps when allowed)."""
    plan = normalize_genui_plan(plan_for_item((spec or {}).get("widget"), item))
    if should_collapse_steps(plan, item.get("steps") or [], has_attempts=bool(item.get("has_attempts"))):
        item["steps"] = collapse_to_final_step(item["steps"])
    item["genui_plan"] = plan
    return plan


def bind_design(
    beats: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach verified items to pending problem beats (mutates items: genui_plan, steps).

    items: ``{id, statement_latex, steps, prompt?, spec_index?, distractors?, pairs?,
    has_attempts?}``. Problem beats with no available item are dropped.
    """
    unused = list(items)
    out: list[dict[str, Any]] = []
    for b in beats:
        if b.get("type") != "problem":
            out.append({k: v for k, v in b.items() if k != "pending"})
            continue
        si = b.get("spec_index")
        pick = next((it for it in unused if it.get("spec_index") == si), None) or (
            unused[0] if unused else None
        )
        if pick is None:
            continue
        unused.remove(pick)
        spec = specs[si] if isinstance(si, int) and 0 <= si < len(specs) else {}
        plan = plan_item_for_spec(spec, pick)
        out.append(
            {
                "type": "problem",
                "title": b.get("title") or "Practice",
                "item_id": str(pick["id"]),
                "genui_plan": plan,
                # Kept so the review can regenerate a flagged problem to the same spec.
                "spec_index": si if isinstance(si, int) else None,
                **({"visual": pick["visual"]} if pick.get("visual") else {}),
            }
        )
    return out


_CRITIC_SYSTEM = (
    "You are a strict reviewer of ONE math lesson for a cognitive tutor. Check: "
    "(1) math accuracy of every teach body and demo step; (2) topic fidelity to the skill "
    "and the brief's objectives; (3) cognitive load: one idea per beat, worked example "
    "before practice; (4) variety and flow of beats; (5) reading level for the learner; "
    "(6) teach beats must not leak answers to the practice problems; (7) each visual "
    "(FractionBars, ShapeDiagram, ...) matches its beat's numbers and clarifies it. "
    "Return ONLY JSON: "
    '{"score":0-10,"issues":["..."],'
    '"math_errors":[{"index":0,"claim":"the wrong statement, quoted"}],'
    '"bad_problems":[{"index":3,"reason":"off-skill / copies a worked example / unfair"}],'
    '"patched_teach":[{"index":0,"title":"...","body_md":"...","demo_steps":[{"latex":"..."}],'
    '"visual":"optional corrected {type,props}, or null to remove a misleading visual"}],'
    '"patched_primer_md":"optional full replacement"}. '
    "math_errors: EVERY factually wrong math claim in a teach body or demo step (recompute "
    "each one). sympy_flags lists demo lines a CAS says do not follow from the previous "
    "line: fix them unless the line is a deliberate 'spot the mistake'. Every beat in "
    "math_errors or sympy_flags MUST appear in patched_teach with corrected body_md and "
    "demo_steps. bad_problems: problem beats that are off-skill, near-copies of a worked "
    "example, or unsuitable for the learner; they will be regenerated. Never patch problem "
    "beats; only list them in bad_problems."
)


def _critic_system(profile: dict[str, Any]) -> str:
    if is_math(profile):
        return _CRITIC_SYSTEM
    return (
        f"You are a strict reviewer of ONE lesson on {profile['subject']} for a cognitive tutor.\n"
        + profile_prompt(profile)
        + "\nCheck: (1) factual accuracy of every teach body and of each problem's answer key; "
        "(2) topic fidelity to the skill and the brief's objectives; (3) cognitive load: one idea "
        "per beat, worked example before practice; (4) variety and flow of beats; (5) reading level "
        "for the learner; (6) teach beats must not leak answers to the practice problems; (7) each "
        "visual matches its beat's content and clarifies it; (8) grounding: a claim that contradicts "
        "the sources' quotes, or a SourceExcerpt whose quote/attribution the sources do not support, "
        "is a fact_error (patch the claim out; set visual to null for such a SourceExcerpt). "
        "Return ONLY JSON: "
        '{"score":0-10,"issues":["..."],'
        '"fact_errors":[{"index":0,"claim":"the wrong statement, quoted"}],'
        '"bad_problems":[{"index":3,"reason":"off-skill / wrong key / copies a worked example / unfair"}],'
        '"patched_teach":[{"index":0,"title":"...","body_md":"...",'
        '"visual":"optional corrected {type,props}, or null to remove a misleading visual"}],'
        '"patched_primer_md":"optional full replacement"}. '
        "fact_errors: EVERY factually wrong claim in a teach body. Every beat in fact_errors MUST "
        "appear in patched_teach with corrected body_md. bad_problems: problem beats that are "
        "off-skill, have a wrong or ambiguous answer key, near-copy a worked example, or are "
        "unsuitable for the learner; they will be regenerated. Never patch problem beats; only "
        "list them in bad_problems."
    )


REPAIR_BELOW = 8.0


_LABEL = re.compile(r"^\s*[A-Za-z][A-Za-z ]{0,30}:\s*")
_WORD = re.compile(r"[A-Za-z]{2,}")


def _math_part(line: str) -> str:
    """``"Simplify: 2x = 10"`` → ``"2x = 10"``; "" for prose, ellipses or chained equalities.

    ponytail: word heuristic; multi-letter variable names (``xy``) are skipped, not checked.
    """
    s = _LABEL.sub("", line.strip(), count=1)
    if not s or "..." in s or s.count("=") > 1 or "," in s:
        return ""
    rest = re.sub(r"\\[A-Za-z]+", "", s)
    if _WORD.search(rest) or not re.search(r"[0-9A-Za-z]", rest):
        return ""  # prose, or only commands like \ldots
    return s


def verify_demo_steps(beat: dict[str, Any]) -> list[int]:
    """Demo-step indices that SymPy says do not follow from the previous parseable line.

    Lines that do not parse (prose, ``\\ldots``) are skipped, not flagged. A numeric-only
    equation (a "check" line like ``2(5)+8=18``) is judged on its own truth.
    """
    from app.workers.math_evaluator import _parse

    bad: list[int] = []
    prev: str | None = None
    for i, step in enumerate(beat.get("demo_steps") or []):
        line = _math_part(str((step or {}).get("latex") or ""))
        if not line:
            continue  # placeholder / prose / chained line: not a single checkable claim
        try:
            expr = _parse(line) if line else None
        except Exception:  # noqa: BLE001
            expr = None
        if expr is None:
            continue
        if isinstance(expr, bool) or (getattr(expr, "is_Boolean", False) and not expr.free_symbols):
            if not bool(expr):
                bad.append(i)
            continue
        if prev is not None:
            r = evaluate_step_safe(line, prev, use_pool=False)
            if r.get("success") and not r.get("is_equivalent"):
                bad.append(i)
        prev = line
    return bad


def _sympy_flags(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for i, b in enumerate(beats):
        if b.get("type") == "problem" or not b.get("demo_steps"):
            continue
        for line in verify_demo_steps(b):
            flags.append({"index": i, "line": line, "latex": b["demo_steps"][line].get("latex")})
    return flags


def critique_lesson(
    *,
    title: str,
    brief: dict[str, Any] | None,
    primer_md: str | None,
    beats: list[dict[str, Any]],
    items_by_id: dict[str, dict[str, Any]],
    api_key: str,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One rubric review + at most one repair of teach beats / primer.

    Returns ``{score, issues, math_errors, sympy_flags, bad_problems, demos_dropped, error,
    repaired, beats, primer_md}``. Repair runs below ``REPAIR_BELOW`` or on any math error.
    Demo steps SymPy still rejects after repair are dropped (none beats wrong ones).
    Non-math profiles: no SymPy checks; ``math_errors`` holds the critic's ``fact_errors``.
    """
    math_mode = is_math(profile)
    flags = _sympy_flags(beats) if math_mode else []
    result: dict[str, Any] = {
        "score": None,
        "issues": [],
        "math_errors": [],
        "sympy_flags": flags,
        "bad_problems": [],
        "demos_dropped": [],
        "error": None,
        "repaired": False,
        "beats": beats,
        "primer_md": primer_md,
    }
    if not api_key:
        return _drop_bad_demos(result)
    view: list[dict[str, Any]] = []
    for i, b in enumerate(beats):
        if b.get("type") == "problem":
            it = items_by_id.get(str(b.get("item_id"))) or {}
            view.append(
                {
                    "index": i,
                    "kind": "problem",
                    "prompt": it.get("prompt"),
                    "statement_latex": it.get("statement_latex"),
                    "widget": (b.get("genui_plan") or {}).get("primary"),
                    "visual": b.get("visual"),
                    # Server-side only: the critic checks generic answer keys (Doc 10 §7.1).
                    **({} if math_mode else {"parts": it.get("parts")}),
                }
            )
        else:
            view.append(
                {
                    "index": i,
                    "kind": "teach",
                    "type": b.get("type"),
                    "title": b.get("title"),
                    "body_md": str(b.get("body_md") or ""),
                    "demo_steps": b.get("demo_steps") or [],
                    "layout": b.get("layout"),
                    "visual": b.get("visual"),
                }
            )
    data = chat_json(
        [
            {"role": "system", "content": _critic_system(profile or MATH_PROFILE)},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "skill": title,
                        "objectives": (brief or {}).get("objectives") or [],
                        # Full text: clipped input made the critic flag our own cuts as truncation.
                        "primer_md": primer_md or "",
                        "beats": view,
                        "sympy_flags": flags,
                        **({} if math_mode else {"sources": citable_sources(brief)}),
                    }
                ),
            },
        ],
        api_key=api_key,
        task="strong",
        temperature=0.1,
        # Runs after node_ready, so a slow review never delays the learner.
        timeout=90.0,
    )
    if not data:
        result["error"] = "no_response"
        return _drop_bad_demos(result)
    try:
        score = round(min(10.0, max(0.0, float(data.get("score")))), 1)
    except (TypeError, ValueError):
        score = None
    result["score"] = score
    result["issues"] = [str(x)[:300] for x in (data.get("issues") or []) if str(x).strip()][:8]
    result["math_errors"] = _indexed(
        data.get("math_errors") or data.get("fact_errors"), beats, "claim", problem=False
    )
    result["bad_problems"] = _indexed(data.get("bad_problems"), beats, "reason", problem=True)
    needs_repair = (
        score is None or score < REPAIR_BELOW or bool(result["math_errors"]) or bool(flags)
    )
    if not needs_repair:
        return _drop_bad_demos(result)

    patched = [dict(b) for b in beats]
    changed = False
    for p in data.get("patched_teach") or []:
        if not isinstance(p, dict):
            continue
        try:
            idx = int(p.get("index"))
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < len(patched)) or patched[idx].get("type") == "problem":
            continue
        b = patched[idx]
        if "visual" in p and p["visual"] is None and b.pop("visual", None) is not None:
            b["layout"] = "stack"
            changed = True
        elif fixed := sanitize_visual(p.get("visual"), cited_urls(brief)):
            b["visual"] = fixed
            b.setdefault("layout", "stack")
            changed = True
        body = str(p.get("body_md") or "").strip()
        if not body:
            continue
        b["title"] = str(p.get("title") or b.get("title") or "")[:80]
        b["body_md"] = body[:MAX_TEACH_BODY]
        demo = _normalize_demo_steps(p.get("demo_steps")) if math_mode else []
        if len(demo) >= 3:
            b["demo_steps"] = demo
        changed = True
    new_primer = str(data.get("patched_primer_md") or "").strip()
    if len(new_primer) >= MIN_TEACH_BODY:
        result["primer_md"] = new_primer[:5000]
        changed = True
    if changed:
        result["beats"] = patched
        result["repaired"] = True
    return _drop_bad_demos(result)


def _indexed(raw: Any, beats: list[dict[str, Any]], key: str, *, problem: bool) -> list[dict[str, Any]]:
    """Keep ``[{index, <key>}]`` rows that point at a real beat of the right kind."""
    out: list[dict[str, Any]] = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue
        try:
            idx = int(r.get("index"))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(beats) and (beats[idx].get("type") == "problem") == problem:
            out.append({"index": idx, key: str(r.get(key) or "")[:300]})
    return out[:8]


def _drop_bad_demos(result: dict[str, Any]) -> dict[str, Any]:
    bad = [
        i
        for i, b in enumerate(result["beats"])
        if b.get("type") != "problem" and b.get("demo_steps") and verify_demo_steps(b)
    ]
    if bad:
        result["beats"] = [
            {**b, "demo_steps": []} if i in bad else b for i, b in enumerate(result["beats"])
        ]
        result["demos_dropped"] = bad
    return result
