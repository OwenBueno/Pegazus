"""Parallel item generation, design → bind, readiness rule, and step-freeze checks."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

from app.api_session import needs_prior_steps
from app.pipeline import item_gen
from app.pipeline.item_gen import canonical_key, generate_items_for_node
from app.pipeline import materialize_node
from app.pipeline.materialize_node import (
    build_lesson_content,
    has_teach_beats,
    lesson_ready,
    review_lesson_content,
)
from app.services import lesson_beats
from app.services.lesson_beats import (
    bind_design,
    LessonDesignError,
    critique_lesson,
    normalize_design,
    plan_for_item,
    should_collapse_steps,
    verify_demo_steps,
)
from app.services.path_draft import clean_modules


def _item(stmt: str, sympy: str, final: str, **extra):
    return {
        "statement_latex": stmt,
        "steps": [
            {"latex": stmt, "sympy": sympy, "operation": "GIVEN"},
            {"latex": final, "sympy": f"Eq(x, {final})", "operation": "FINAL"},
        ],
        **extra,
    }


def test_parallel_generation_fills_exactly_count_and_dedupes():
    # Two variants are the same equation written differently → must count once.
    banks = iter(
        [
            [_item("x+2=5", "Eq(x + 2, 5)", "3"), _item("2+x=5", "Eq(2 + x, 5)", "3"),
             _item("x+3=7", "Eq(x + 3, 7)", "4"), _item("x+4=9", "Eq(x + 4, 9)", "5")],
            [_item("x+5=11", "Eq(x + 5, 11)", "6"), _item("x+6=13", "Eq(x + 6, 13)", "7"),
             _item("x+7=15", "Eq(x + 7, 15)", "8")],
        ]
    )
    lock = threading.Lock()
    threads: set[str] = set()

    def fake(**kwargs):
        time.sleep(0.05)  # keep calls overlapping so the pool uses >1 thread
        with lock:
            threads.add(threading.current_thread().name)
            return next(banks, [])

    specs = [{"facet": "a"}, {"facet": "b"}]
    with patch.object(item_gen, "request_items", side_effect=fake):
        out = generate_items_for_node(node_title="Linear", api_key="k", count=5, specs=specs)
    assert len(out) == 5
    assert len({canonical_key(i) for i in out}) == 5
    assert sorted(i["spec_index"] for i in out) == [0, 0, 0, 1, 1]
    assert len(threads) > 1, "specs should be generated concurrently"


def test_worked_example_statements_are_not_reused_as_practice():
    bank = [_item("x+2=5", "Eq(x + 2, 5)", "3"), _item("x+3=7", "Eq(x + 3, 7)", "4")]
    with patch.object(item_gen, "request_items", return_value=bank):
        out = generate_items_for_node(
            node_title="Linear", api_key="k", count=1, overshoot=1, avoid=["x + 2 = 5"]
        )
    assert [i["statement_latex"] for i in out] == ["x+3=7"]


def test_canonical_key_keeps_different_problems_apart():
    a = _item("x+2=5", "Eq(x + 2, 5)", "3")
    b = _item("x+3=6", "Eq(x + 3, 6)", "3")  # same solution, different problem
    c = _item("2+x=5", "Eq(2 + x, 5)", "3")
    assert canonical_key(a) != canonical_key(b)
    assert canonical_key(a) == canonical_key(c)


def test_design_bind_and_readiness():
    ai = {
        "beats": [
            {"kind": "teach", "type": "intro", "title": "Why", "body_md": "Balance scales."},
            {"kind": "problem", "title": "Try", "spec_index": 0},
            {"kind": "teach", "type": "fun_fact", "title": "Fact", "body_md": "Al-Khwarizmi."},
            {"kind": "problem", "title": "Pick", "spec_index": 1},
            {"kind": "teach", "type": "summary", "title": "Recap", "body_md": "Undo in reverse."},
        ],
        "problem_specs": [
            {"facet": "solve", "difficulty": 0.3, "widget": "SymbolicStepEditor"},
            {"facet": "check", "difficulty": 0.6, "widget": "QuickCheck"},
            {"facet": "x", "difficulty": 0.9, "widget": "HologramTable"},
        ],
    }
    design = normalize_design(ai, brief=None)
    assert design is not None
    assert design["missing_widgets"] == ["HologramTable"]
    assert design["specs"][2]["widget"] == "SymbolicStepEditor"
    teach_only = design["beats"]
    assert has_teach_beats(teach_only)
    assert not lesson_ready(item_count=5, beats=teach_only), "pending problems are not ready"

    items = [
        {"id": "i0", "spec_index": 0, **_item("x+2=5", "Eq(x + 2, 5)", "3")},
        {"id": "i1", "spec_index": 1, **_item("x+3=7", "Eq(x + 3, 7)", "4", distractors=["10", "-4"])},
    ] + [{"id": f"e{i}", **_item(f"x+{i}=9", f"Eq(x + {i}, 9)", str(9 - i))} for i in range(3)]
    beats = bind_design(design["beats"], design["specs"], items)
    problems = [b for b in beats if b["type"] == "problem"]
    assert [p["item_id"] for p in problems] == ["i0", "i1"]
    qc = problems[1]["genui_plan"]
    assert qc["primary"] == "QuickCheck"
    props = qc["widgets"][0]["props"]
    assert {c["label"] for c in props["choices"]} == {"4", "10", "-4"}
    assert next(c for c in props["choices"] if c["id"] == props["correctId"])["label"] == "4"
    # Selection item collapsed to the final step before insert
    assert len(items[1]["steps"]) == 1
    assert lesson_ready(item_count=5, beats=beats)


def test_bind_never_rewrites_steps_with_attempts():
    item = {"id": "old", "has_attempts": True, **_item("x+3=7", "Eq(x + 3, 7)", "4", distractors=["10"])}
    beats = [
        {"type": "intro", "title": "t", "body_md": "b"},
        {"type": "problem", "title": "p", "spec_index": 0, "pending": True},
    ]
    bind_design(beats, [{"widget": "QuickCheck"}], [item])
    assert len(item["steps"]) == 2, "answered steps must stay frozen"
    plan = item["genui_plan"]
    assert not should_collapse_steps(plan, item["steps"], has_attempts=True)
    # …and the final-step selection answer is accepted without "missing" earlier steps
    assert needs_prior_steps(plan, step_index=1, step_count=2) is False
    assert needs_prior_steps({"widgets": ["SymbolicStepEditor"]}, step_index=1, step_count=2) is True


def test_plan_for_item_falls_back_without_extras():
    plan = plan_for_item("QuickCheck", {"id": "x", **_item("x+1=2", "Eq(x + 1, 2)", "1")})
    assert plan["primary"] == "SymbolicStepEditor"
    nl = plan_for_item("NumberLine", {"id": "y", **_item("x+1=8", "Eq(x + 1, 8)", "7")})
    assert nl["primary"] == "NumberLine"
    assert nl["widgets"][0]["props"]["target"] == 7.0


def test_outline_prerequisites_only_point_backwards():
    mods = clean_modules(
        {
            "modules": [
                {"title": "A", "prerequisites": []},
                {"title": "", "prerequisites": [0]},
                {"title": "B", "prerequisites": [0, 5, 3]},
                {"title": "C", "prerequisites": [0, 2]},
            ]
        }
    )
    assert [m["title"] for m in mods] == ["A", "B", "C"]
    assert mods[1]["prerequisites"] == [0]
    assert mods[2]["prerequisites"] == [0, 1]


def test_build_lesson_without_ai_fails_instead_of_canned_lesson():
    teach_calls = []
    try:
        build_lesson_content(
            title="Linear equations",
            context="Goal: midterm",
            api_key="",
            on_teach_ready=lambda brief, beats: teach_calls.append(beats),
        )
        raise AssertionError("expected LessonDesignError")
    except LessonDesignError as e:
        safe = materialize_node.learner_safe(e, "es")
    assert not teach_calls
    assert "Traceback" not in safe and "LessonDesignError" not in safe and safe


def test_verify_demo_steps_flags_wrong_line_only():
    demo = lambda *ls: {"type": "worked_example", "demo_steps": [{"latex": x} for x in ls]}  # noqa: E731
    assert verify_demo_steps(demo("x-7=4", "x=3")) == [1]
    assert verify_demo_steps(demo("x-7=4", "x=11", "11-7=4")) == []
    assert verify_demo_steps(demo(r"\frac{1}{2}+\frac{1}{3}", r"\frac{2}{5}")) == [1]
    assert verify_demo_steps(demo("2x+8=18", r"\ldots", "x=5", "2(5)+8=19")) == [3]
    # Labelled lines are checked; prose and chained lines are skipped, never flagged.
    assert verify_demo_steps(
        demo("2x+8=18", "Simplify: 2x = 10", "Divide both sides by 2: x = 5", "Check: 2(5) + 8 = 18, which is true")
    ) == []
    assert verify_demo_steps(demo("Simplify: 2x+8=18", "Simplify: 2x = 12")) == [1]
    assert verify_demo_steps(
        demo(r"\frac{1}{4}+\frac{2}{3}", r"Rewrite: \frac{1}{4}=\frac{3}{12} and \frac{2}{3}=\frac{8}{12}", r"\frac{11}{12}")
    ) == []


def test_math_error_forces_repair_even_with_high_score():
    beats = [
        {"type": "concept", "title": "Undo", "body_md": "x - 7 = 4 gives x = 3."},
        {"type": "problem", "item_id": "a"},
    ]
    critic = {
        "score": 9,
        "math_errors": [{"index": 0, "claim": "x - 7 = 4 gives x = 3"}],
        "patched_teach": [{"index": 0, "body_md": "Add 7 to both sides: x - 7 = 4 gives x = 11."}],
    }
    with patch.object(lesson_beats, "chat_json", return_value=critic):
        r = critique_lesson(title="t", brief=None, primer_md="p", beats=beats, items_by_id={}, api_key="k")
    assert r["repaired"] and "x = 11" in r["beats"][0]["body_md"]
    assert r["math_errors"] == [{"index": 0, "claim": "x - 7 = 4 gives x = 3"}]


def test_review_swaps_only_flagged_problems_without_attempts():
    plan = {"widgets": ["SymbolicStepEditor"], "primary": "SymbolicStepEditor"}
    beats = [
        {"type": "intro", "body_md": "hi"},
        {"type": "problem", "item_id": "a", "genui_plan": plan, "spec_index": 0},
        {"type": "problem", "item_id": "b", "genui_plan": plan, "spec_index": 0},
    ]
    out = {
        "brief": {},
        "primer_md": "p",
        "beats": beats,
        "items": [{"id": "a", **_item("x+1=2", "Eq(x + 1, 2)", "1")}, {"id": "b", **_item("x+2=4", "Eq(x + 2, 4)", "2")}],
        "specs": [{"widget": "SymbolicStepEditor"}],
    }
    crit = {
        "score": 6, "issues": [], "math_errors": [], "sympy_flags": [], "demos_dropped": [],
        "error": None, "repaired": False, "primer_md": "p", "beats": beats,
        "bad_problems": [{"index": 1, "reason": "off-skill"}, {"index": 2, "reason": "copy"}],
    }
    with patch.object(materialize_node, "critique_lesson", return_value=crit), patch.object(
        materialize_node, "generate_items_for_node", return_value=[_item("x+5=9", "Eq(x + 5, 9)", "4")]
    ) as gen:
        rv = review_lesson_content(title="t", out=out, api_key="k", locked_item_ids={"a"})
    assert gen.call_count == 1
    assert rv["beats"][1]["item_id"] == "a"
    new_id = rv["beats"][2]["item_id"]
    assert new_id != "b" and [i["id"] for i in rv["new_items"]] == [new_id]
    assert rv["review"]["problems_swapped"] == [{"index": 2, "old_item_id": "b", "new_item_id": new_id}]
