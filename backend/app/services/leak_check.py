"""Answer-leak check: reject hints that reveal the expected step or final answer."""

from __future__ import annotations

import re
from typing import Any

from app.workers.math_evaluator import evaluate_step_safe

_MATH_CHUNK = re.compile(
    r"\$\$(.+?)\$\$|\\\((.+?)\\\)|\\\[(.+?)\\\]|\$([^$\n]+?)\$",
    re.DOTALL,
)


def extract_math_snippets(text: str) -> list[str]:
    snippets: list[str] = []
    for m in _MATH_CHUNK.finditer(text):
        snip = next((g for g in m.groups() if g), "")
        if snip.strip():
            snippets.append(snip.strip())
    # Also catch bare latex-ish equality fragments
    for m in re.finditer(r"\b[a-zA-Z0-9\\{}^_+\-*/=\s]{3,80}\b", text):
        frag = m.group(0).strip()
        if "=" in frag and any(c.isalpha() for c in frag):
            snippets.append(frag)
    return snippets


def hint_leaks_answer(hint: str, forbidden_targets: list[str]) -> bool:
    """True if any math in the hint is SymPy-equivalent to a forbidden target."""
    snippets = extract_math_snippets(hint)
    # Also compare raw hint substrings of targets (plain leak of latex)
    lowered = hint.replace(" ", "").lower()
    for target in forbidden_targets:
        t = (target or "").strip()
        if not t:
            continue
        if t.replace(" ", "").lower() in lowered:
            return True
        for snip in snippets:
            result = evaluate_step_safe(snip, t, use_pool=False)
            if result.get("is_equivalent"):
                return True
    return False


def forbidden_from_parts(parts: list[dict[str, Any]] | None) -> list[str]:
    """Answer texts of non-sympy parts (correct choice labels, accepted answers).

    ponytail: labels under 3 chars are skipped (substring false positives); a hint can still
    name a 1-2 char answer. Upgrade path = token-level match against the answer key.
    """
    out: list[str] = []
    for p in parts or []:
        spec, props = p.get("answer_spec") or {}, p.get("props") or {}
        if p.get("grader") == "choice":
            right = {str(i) for i in spec.get("correctIds") or []}
            out += [str(c.get("label")) for c in props.get("choices") or [] if str(c.get("id")) in right]
        elif p.get("grader") == "exact":
            out += [str(a) for a in spec.get("accepted") or []]
    return [t for t in out if len(t.strip()) >= 3]


def forbidden_from_item_steps(steps: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for s in steps:
        if s.get("latex"):
            out.append(str(s["latex"]))
        if s.get("sympy"):
            out.append(str(s["sympy"]))
    return out
