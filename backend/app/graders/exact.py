"""``exact``: ``{"text": "Paris"}`` vs ``{"accepted": […], "case"?: bool, "strip_accents"?: bool}``."""

from __future__ import annotations

import unicodedata
from typing import Any

from app.graders import MAX_ITEMS, MAX_TEXT, GradeResult, bad_answer, scored


def normalize(s: str, strip_accents: bool = False, case: bool = False) -> str:
    """NFKC, optional accent strip, casefold (unless ``case``), drop punctuation, collapse spaces."""
    s = unicodedata.normalize("NFKC", s)
    if strip_accents:  # language items keep accents unless the spec says otherwise
        s = unicodedata.normalize(
            "NFC", "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        )
    if not case:
        s = s.casefold()
    s = "".join(c for c in s if not unicodedata.category(c).startswith("P"))
    return " ".join(s.split())


def matches(text: Any, accepted: Any, spec: dict[str, Any]) -> bool | None:
    """True/False, or None when ``text``/``accepted`` are malformed."""
    if not isinstance(text, str) or len(text) > MAX_TEXT or not isinstance(accepted, list):
        return None
    opts = dict(strip_accents=bool(spec.get("strip_accents")), case=bool(spec.get("case")))
    keys = {normalize(str(a), **opts) for a in accepted[:MAX_ITEMS]}
    return normalize(text, **opts) in keys - {""}


def grade_exact(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    ok = matches(answer.get("text"), spec["accepted"], spec)
    return bad_answer() if ok is None else scored(1.0 if ok else 0.0)
