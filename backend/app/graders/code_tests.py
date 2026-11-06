"""``code_tests``: ``{"passed": n, "total": m, "code": "..."}`` vs ``{"total": m, ...}``.

ponytail: trusts the browser's test result (Doc 10 R2, low-stakes practice); the code is stored
with the attempt (``submitted_answer``). Upgrade: re-run it in a server sandbox before it counts
toward FSRS mastery.
"""

from __future__ import annotations

from typing import Any

from app.graders import GradeResult, bad_answer, scored

MAX_CODE = 3500  # the whole answer is capped at 4 KB JSON anyway


def grade_code_tests(spec: dict[str, Any], answer: dict[str, Any]) -> GradeResult:
    passed, total, code = answer.get("passed"), answer.get("total"), answer.get("code")
    if type(passed) is not int or type(total) is not int or not isinstance(code, str) or len(code) > MAX_CODE:
        return bad_answer()
    if total != spec["total"] or not 0 <= passed <= total or total == 0:
        return bad_answer()
    r = scored(passed / total)
    r.decided_by = "CLIENT"
    return r
