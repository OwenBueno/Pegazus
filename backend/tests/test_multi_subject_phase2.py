"""Phase 2 multi-subject: profile clamp/inference, subject-neutral prompts, generic items."""

from __future__ import annotations

import re
from unittest.mock import patch

from app.pipeline import item_gen, research_brief
from app.services import lesson_beats, path_draft, subject_profile, system2_hints, tutor_chat
from app.services.subject_profile import MATH_PROFILE, clamp_profile, infer_subject_profile

SPANISH = clamp_profile(
    {"subject": "Spanish travel vocabulary", "categories": ["core", "language"], "notation": "none",
     "target_language": "es", "answer_modes": ["choice", "match"]}
)
MATHY = re.compile(r"\bmath|katex|sympy|latex|equation", re.I)


def _prompts(profile):
    return {
        "design": lesson_beats._design_system(profile, 4),
        "critic": lesson_beats._critic_system(profile),
        "outline": path_draft._system(profile),
        "research": research_brief._system(profile),
        "items": item_gen._generic_system(profile, ["QuickCheck", "MatchPairs"]),
        "tutor": tutor_chat._system_prompt("en", profile),
        "hint": system2_hints._system_prompt("en", 1, profile),
    }


def test_clamp_never_trusts_input():
    p = clamp_profile({"categories": ["math", "evil"], "notation": "rm -rf", "level": 9, "allowed": "no"})
    assert p["categories"] == ["core", "math"] and p["notation"] == "math"
    assert p["level"] == "beginner" and p["allowed"] is True
    assert clamp_profile(None, goal="  Learn   Greek ")["subject"] == "Learn Greek"
    assert clamp_profile({"allowed": False})["allowed"] is False


def test_infer_language_goal_with_mocked_model():
    raw = {"subject": "Spanish (ordering food)", "categories": ["language", "core"], "notation": "none",
           "target_language": "es", "instruction_language": "en", "allowed": True}
    with patch.object(subject_profile, "chat_json", return_value=raw):
        p = infer_subject_profile("Order food in Spanish", api_key="k")
    assert {"core", "language"} <= set(p["categories"]) and p["notation"] == "none"
    assert infer_subject_profile("anything", api_key="")["notation"] == "none"  # no key: neutral, not math


def test_prompts_are_neutral_for_non_math_and_unchanged_for_math():
    for name, text in _prompts(SPANISH).items():
        assert not MATHY.search(text), f"{name}: {MATHY.search(text).group(0)!r}"
        assert "Spanish travel vocabulary" in text or name in ("critic",), name
    math = _prompts(MATH_PROFILE)
    assert "KaTeX" in math["design"] and "math" in math["tutor"].lower()
    assert "mathematical law" in math["hint"]


def test_generic_item_verify():
    ok = {"prompt_md": "How do you say *thank you*?", "parts": [{"component": "QuickCheck",
          "props": {"choices": [{"id": "a", "label": "gracias"}, {"id": "b", "label": "hola"}]},
          "answer_spec": {"correctIds": ["a"]}}]}
    item, err = item_gen.verify_generic_item(ok, ["QuickCheck", "MatchPairs"])
    assert item and not err and item["statement_latex"] is None and item["parts"][0]["grader"] == "choice"
    bad = {**ok, "parts": [{**ok["parts"][0], "answer_spec": {"correctIds": ["z"]}}]}
    item, err = item_gen.verify_generic_item(bad, ["QuickCheck"])
    assert item is None and err.startswith("part:") and "correctIds" in err
    match = {"prompt_md": "Match", "parts": [{"component": "MatchPairs",
             "props": {"lefts": ["uno", "dos", "tres"], "rights": ["one", "two", "three"]},
             "answer_spec": {"pairs": [[0, 0], [1, 1], [2, 2]]}}]}
    m, _ = item_gen.verify_generic_item(match, ["MatchPairs"])
    rights = m["parts"][0]["props"]["rights"]
    assert all(rights[ri] == ["one", "two", "three"][li] for li, ri in m["parts"][0]["answer_spec"]["pairs"])
