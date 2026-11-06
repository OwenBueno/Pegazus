"""Generate and grade a short placement exam from learner context (not a PDF).

Questions are §6.2 parts graded by ``app.graders``; the answer key travels HMAC-signed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import re
import uuid
from datetime import date
from typing import Any

from app.config import settings
from app.graders import grade
from app.graders.numeric import UNITS
from app.services.llm import chat_json
from app.services.subject_profile import MATH_PROFILE, is_math, profile_prompt
from app.workers.math_evaluator import evaluate_step_safe

COMPONENT = {"choice": "QuickCheck", "sympy": "SymbolicStepEditor"}  # exact/numeric: plain text input


class PlacementError(RuntimeError):
    """The model could not produce a usable exam; the client shows Retry."""


def clean_latex(raw: str) -> str:
    """KaTeX expects body without \\( \\) / $ wrappers; drop English asides."""
    s = (raw or "").strip()
    if not s:
        return s
    # Collect delimiter-wrapped chunks; prefer the longest (usually the equation)
    chunks: list[str] = []
    for pat in (
        r"\$\$([\s\S]+?)\$\$",
        r"\\\[([\s\S]+?)\\\]",
        r"\\\(([\s\S]+?)\\\)",
        r"\$([^$]+)\$",
    ):
        chunks.extend(m.group(1).strip() for m in re.finditer(pat, s))
    if chunks:
        s = max(chunks, key=len)
    else:
        # "Solve for x: x+7=12" → keep after last colon when right side is math-ish
        if ":" in s and re.search(r"[=<>≤≥\\^_{}]", s):
            left, right = s.rsplit(":", 1)
            if re.search(r"[a-zA-Z]{3,}", left) and (
                re.search(r"[=<>]", right) or re.search(r"\\[a-zA-Z]", right)
            ):
                s = right.strip()
    # Drop parenthetical English asides
    s = re.sub(r"\([^)]*[a-zA-Z]{4,}[^)]*\)", "", s).strip()
    # Un-double escaped commands from JSON mistakes: \\\\ge → \\ge
    while r"\\\\" in s:
        s = s.replace(r"\\\\", r"\\")
    return s.strip()


# ponytail: the signed key stops tampering, not peeking (base64 JSON is readable client-side).
# Self-placement only, so that's acceptable; upgrade path = store the exam server-side by id.
def _mac(body: str) -> str:
    secret = (settings.supabase_jwt_secret + "|placement").encode()
    return hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()


def sign_key(qid: str, grader: str, spec: dict[str, Any], skill_hint: str) -> str:
    raw = json.dumps({"id": qid, "grader": grader, "spec": spec, "skill": skill_hint}, sort_keys=True)
    body = base64.urlsafe_b64encode(raw.encode()).decode()
    return f"{body}.{_mac(body)}"


def open_key(key: str, qid: str) -> dict[str, Any] | None:
    """The signed payload, or None when forged / swapped onto another question."""
    body, _, mac = (key or "").partition(".")
    if not body or not hmac.compare_digest(mac, _mac(body)):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(body.encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("id") == qid else None


def generate_placement_exam(
    *,
    goal_text: str,
    api_key: str | None,
    count: int = 5,
    birth_year: int | None = None,
    locale: str | None = None,
    prior_paths: list[str] | None = None,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Public questions ``{id, prompt_md, statement_latex, skill_hint, difficulty, parts, key}``.

    Ordered easy → hard. Raises ``PlacementError`` (no key, or two bad model answers).
    """
    if not api_key:
        raise PlacementError("no API key")
    profile = profile or MATH_PROFILE
    graders = _graders(profile)
    messages = _messages(
        goal=goal_text,
        count=count,
        age=_approx_age(birth_year),
        locale=locale or "en",
        prior_paths=prior_paths or [],
        profile=profile,
        graders=graders,
    )
    need = min(count, 3)
    for attempt in range(2):
        data = chat_json(messages, api_key=api_key, task="strong", temperature=0.35)
        rows = (data or {}).get("questions")
        out, errors = [], []
        for i, row in enumerate(rows if isinstance(rows, list) else []):
            q, err = clean_question(row, graders, math_mode=is_math(profile), index=i)
            if q:
                out.append(q)
            else:
                errors.append(f"question {i + 1}: {err}")
            if len(out) >= count:
                break
        if len(out) >= need:
            return _order_by_difficulty(out)
        if attempt == 0:
            messages = [
                *messages,
                {
                    "role": "user",
                    "content": "Your previous answer was invalid: "
                    + ("; ".join(errors[:5]) or "no questions")
                    + f". Return {count} questions that follow the shape exactly.",
                },
            ]
    raise PlacementError("placement exam generation failed")


def _graders(profile: dict[str, Any]) -> list[str]:
    if is_math(profile):
        return ["sympy", "choice", "numeric"]
    return ["choice", "exact"] + (["numeric"] if "numeric" in profile.get("answer_modes", []) else [])


def clean_question(
    row: Any, graders: list[str], *, math_mode: bool, index: int = 0
) -> tuple[dict[str, Any] | None, str]:
    """Validate one model question into the public shape (key signed), else (None, reason)."""
    if not isinstance(row, dict):
        return None, "not an object"
    grader = row.get("grader")
    if grader not in graders:
        return None, f"grader must be one of {graders}"
    prompt_md = str(row.get("prompt_md") or row.get("prompt") or "").strip()[:600]
    stmt = clean_latex(str(row.get("statement_latex") or ""))[:300] if math_mode else ""
    if not prompt_md and not stmt:
        return None, "missing prompt_md"
    props: dict[str, Any] = {}
    if grader == "choice":
        choices = row.get("choices")
        if not isinstance(choices, list) or not 2 <= len(choices) <= 6:
            return None, "choices must be 2-6 {id,label}"
        clean = [
            {"id": str(c.get("id"))[:40], "label": str(c.get("label")).strip()[:200]}
            for c in choices
            if isinstance(c, dict) and c.get("id") is not None and str(c.get("label") or "").strip()
        ]
        ids = [c["id"] for c in clean]
        if len(clean) != len(choices) or len(set(ids)) != len(ids):
            return None, "choices need unique ids and non-empty labels"
        if str(row.get("correct_id")) not in ids:
            return None, "correct_id is not one of the choice ids"
        props, spec = {"choices": clean}, {"correctIds": [str(row.get("correct_id"))]}
    elif grader == "exact":
        acc = row.get("accepted")
        if not isinstance(acc, list):
            return None, "accepted must be a list"
        acc = [str(a).strip()[:100] for a in acc if str(a or "").strip()][:5]
        if not acc:
            return None, "accepted needs at least one answer"
        spec = {"accepted": acc}
    elif grader == "numeric":
        try:
            value = float(row.get("value"))
        except (TypeError, ValueError):
            return None, "value must be a number"
        if not math.isfinite(value):
            return None, "value must be finite"
        unit = str(row.get("unit") or "").replace(" ", "")
        spec = {"value": value, "tolerance": 0.01}
        if unit in UNITS:
            spec["unit"] = props["unit"] = unit
    else:  # sympy
        target = str(row.get("target_sympy") or "").strip()[:300]
        if not stmt or not target:
            return None, "sympy needs statement_latex and target_sympy"
        spec = {
            "sympy": target,
            "latex": clean_latex(str(row.get("target_latex") or ""))[:300],
            "statement": stmt,
        }
    try:
        diff = max(1, min(10, int(row.get("difficulty") or index + 1)))
    except (TypeError, ValueError):
        diff = index + 1
    qid = str(uuid.uuid4())
    skill = str(row.get("skill_hint") or "general").strip()[:48].lower() or "general"
    return (
        {
            "id": qid,
            "prompt_md": prompt_md,
            "statement_latex": stmt,
            "skill_hint": skill,
            "difficulty": diff,
            "parts": [{"component": COMPONENT.get(grader), "grader": grader, "props": props}],
            "key": sign_key(qid, grader, spec, skill),
        },
        "",
    )


def grade_placement_exam(
    *,
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Raises ``ValueError`` when any answer key fails its signature check."""
    by_id = {str(q["id"]): q for q in questions}
    results: list[dict[str, Any]] = []
    correct = 0
    for ans in answers:
        qid = str(ans.get("id") or "")
        q = by_id.get(qid)
        if not q:
            continue
        key = open_key(str(q.get("key") or ""), qid)
        if key is None:
            raise ValueError("invalid placement key")
        answer = ans.get("answer") if isinstance(ans.get("answer"), dict) else {}
        ok = _correct(key["grader"], key["spec"], answer)
        correct += ok
        results.append(
            {
                "skill_hint": key.get("skill") or "general",
                "prompt": q.get("prompt_md") or "",
                "statement_latex": q.get("statement_latex") or "",
                "submitted": _shown(answer),
                "correct": ok,
                "difficulty": q.get("difficulty") or 1,
            }
        )

    weak = [r["skill_hint"] for r in results if not r["correct"]]
    strong = [r["skill_hint"] for r in results if r["correct"]]
    lines = ["# Placement exam", f"Goal context score: {correct}/{len(results)}", ""]
    for r in results:
        mark = "OK" if r["correct"] else "MISS"
        lines.append(
            f"- [{mark}] d{r['difficulty']} ({r['skill_hint']}) "
            f"{r['prompt']} {r['statement_latex']} → {r['submitted'] or '(blank)'}"
        )
    if weak:
        lines += ["", "Weak skills: " + ", ".join(dict.fromkeys(weak))]
    if strong:
        lines.append("Strong skills: " + ", ".join(dict.fromkeys(strong)))
    return {
        "summary_markdown": "\n".join(lines),
        "correct_count": correct,
        "total": len(results),
        "weak_skills": list(dict.fromkeys(weak)),
        "strong_skills": list(dict.fromkeys(strong)),
        "results": results,
    }


def _shown(answer: dict[str, Any]) -> str:
    v = answer.get("latex") or answer.get("text") or answer.get("value") or answer.get("ids") or ""
    return str(v)[:120]


def _correct(grader: str, spec: dict[str, Any], answer: dict[str, Any]) -> bool:
    if grader == "sympy":
        return _sympy_correct(spec, str(answer.get("latex") or "").strip())
    if grader == "numeric" and "value" not in answer and isinstance(answer.get("text"), str):
        answer = {"value": answer["text"].strip()}
    return grade(grader, spec, answer).is_success


def _sympy_correct(spec: dict[str, Any], submitted: str) -> bool:
    """Strict placement check: must match the answer, not merely parse or restate the problem."""
    if not submitted or len(submitted) > 500 or not _looks_like_math(submitted):
        return False
    target, target_latex = spec.get("sympy") or "", spec.get("latex") or ""
    stmt = spec.get("statement") or ""
    if target_latex and (_soft_match(submitted, target_latex) or _soft_match_rhs(submitted, target_latex)):
        return True
    if not target or not evaluate_step_safe(submitted, target, use_pool=False).get("is_equivalent"):
        return False
    # Restating the problem shares a solution set with Eq(x, …) — not a solved answer
    return not (stmt and evaluate_step_safe(submitted, stmt, use_pool=False).get("is_equivalent"))


def _looks_like_math(s: str) -> bool:
    """Reject prose / keyboard spam that sympy happily turns into free symbols."""
    if not re.search(r"[\d=<>≤≥+\-*/^\\]", s):
        return False
    # Must contain a digit or a relation (bare "x" / "asdf" fail)
    return bool(re.search(r"\d", s) or re.search(r"[=<>≤≥]", s))


def _soft_match(a: str, b: str) -> bool:
    def norm(s: str) -> str:
        s = s.lower().replace(" ", "").replace("\\", "")
        s = s.replace(r"left", "").replace(r"right", "")
        s = re.sub(r"[{}]", "", s)
        s = s.replace("geq", ">=").replace("leq", "<=").replace("ge", ">=").replace("le", "<=")
        return s

    return bool(a and b and norm(a) == norm(b))


def _soft_match_rhs(submitted: str, target_latex: str) -> bool:
    """Accept bare '7' when target is 'x = 7' / 'y=12'."""
    m = re.search(r"[=<>≤≥]\s*(.+)$", target_latex.strip())
    if not m:
        return False
    rhs = m.group(1).strip()
    return _soft_match(submitted, rhs) or _soft_match(submitted, target_latex)


def _approx_age(birth_year: int | None) -> int | None:
    if birth_year is None:
        return None
    return max(5, min(80, date.today().year - int(birth_year)))


_SHAPES = {
    "choice": '{"grader":"choice","choices":[{"id":"a","label":"..."}],"correct_id":"a"}',
    "exact": '{"grader":"exact","accepted":["main answer","accepted variant"]}',
    "numeric": '{"grader":"numeric","value":9.8,"unit":"m/s^2 or empty"}',
    "sympy": '{"grader":"sympy","statement_latex":"x+7=12","target_sympy":"Eq(x, 5)","target_latex":"x = 5"}',
}


def _messages(
    *,
    goal: str,
    count: int,
    age: int | None,
    locale: str,
    prior_paths: list[str],
    profile: dict[str, Any],
    graders: list[str],
) -> list[dict[str, str]]:
    age_line = (
        f"Learner age ≈ {age}. Pitch difficulty to that age."
        if age is not None
        else "Age unknown — prefer accessible beginner through intermediate."
    )
    shapes = "\n".join(f"- {_SHAPES[g]}" for g in graders)
    math_rule = (
        "- sympy: statement_latex is ONLY math (no prose, no $ delimiters); target_sympy is the final answer.\n"
        if is_math(profile)
        else "- Plain text only; no LaTeX.\n"
    )
    system = (
        "Return ONLY JSON: "
        '{"questions":[{"prompt_md":"short instruction/question in the instruction language",'
        '"skill_hint":"2-4 word skill label","difficulty":1, ...grader fields}]}\n'
        + profile_prompt(profile)
        + f"\nCreate exactly `count` placement questions for {profile['subject']}, "
        "ordered difficulty 1 (easiest) → `count` (hardest).\n"
        "Grader shapes (merge one into each question):\n"
        + shapes
        + "\nRules:\n"
        "- Easy→hard ramp so a beginner can show floor and a strong learner can show ceiling.\n"
        "- If prior courses overlap the goal, skip trivial items they already passed.\n"
        "- Every question has exactly one unambiguous correct answer; never reveal it in prompt_md.\n"
        + math_rule
        + "- skill_hint: short lowercase label, not a full sentence."
    )
    user = {
        "count": count,
        "locale": locale,
        "goal": goal.strip()[:500],
        "age_guidance": age_line,
        "prior_courses_or_paths": ", ".join(prior_paths[:8]) or "(none yet)",
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}]


def _order_by_difficulty(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda q: int(q.get("difficulty") or 1))
