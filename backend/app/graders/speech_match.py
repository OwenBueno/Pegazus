"""``speech_match``: ``{"transcript": "..."}`` (browser SpeechRecognition) or ``{"self": 0|1}``
(self-rating when the browser has no recognition) vs ``{"phrase": "..."}``.
"""

from __future__ import annotations

from typing import Any

from app.graders import MAX_TEXT, GradeResult, bad_answer, scored
from app.graders.exact import normalize


def _distance(a: str, b: str) -> int:
    """Levenshtein edit distance (O(len·len), phrases are ≤ 160 chars)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def grade_speech_match(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    if "self" in answer:
        rate = answer["self"]
        if type(rate) is not int or rate not in (0, 1):
            return bad_answer()
        r = scored(float(rate))
        r.decided_by = "CLIENT"  # the learner's own rating (Doc 10 R5: speech never blocks)
        return r
    text = answer.get("transcript")
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        return bad_answer()
    # Recognizers drop punctuation and sometimes accents; compare without either.
    want, got = normalize(str(spec["phrase"]), strip_accents=True), normalize(text, strip_accents=True)
    if not want or not got:
        return scored(0.0)
    return scored(1.0 if _distance(want, got) <= 0.2 * len(want) else 0.0)
