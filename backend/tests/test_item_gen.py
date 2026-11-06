"""Item generation — AI only, no seed banks."""

from unittest.mock import patch

from app.pipeline import item_gen
from app.pipeline.item_gen import generate_items_for_node, verify_item, verify_item_payload


def test_no_api_key_returns_empty_not_bank():
    items = generate_items_for_node(
        node_title="Multiplication Basics",
        api_key="",
        count=5,
    )
    assert items == []


def test_verify_still_accepts_good_payload():
    good = {
        "statement_latex": r"3 \times 4",
        "steps": [
            {"latex": r"3 \times 4", "sympy": "3*4", "operation": "GIVEN", "justification": "given"},
            {"latex": "12", "sympy": "Eq(y, 12)", "operation": "MULTIPLY", "justification": "multiply"},
        ],
    }
    out = verify_item_payload(good)
    assert out is not None
    assert out["steps"][0].get("justification") == "given"


def test_verify_order_of_ops_expression_intermediates():
    good = {
        "prompt": "Compute using order of operations.",
        "statement_latex": r"-3+2\cdot(-4)^{2}",
        "steps": [
            {
                "latex": r"-3+2\cdot(-4)^{2}",
                "sympy": "-3+2*(-4)**2",
                "operation": "GIVEN",
                "justification": "given",
            },
            {
                "latex": r"-3+2\cdot 16",
                "sympy": "-3+2*16",
                "operation": "EXPONENT",
                "justification": "exponents",
                "gap_latex": r"-3+2\cdot\square",
            },
            {
                "latex": "29",
                "sympy": "Eq(y, 29)",
                "operation": "FINAL",
                "justification": "simplify",
            },
        ],
    }
    out = verify_item_payload(good)
    assert out is not None
    assert out["steps"][1]["gap_latex"].endswith("square")


def test_verify_rejects_identical_eq_every_step():
    bad = {
        "statement_latex": r"-3+2\cdot(-4)^{2}",
        "steps": [
            {"latex": "29", "sympy": "Eq(y, 29)", "operation": "GIVEN"},
            {"latex": "29", "sympy": "Eq(y, 29)", "operation": "STEP"},
            {"latex": "29", "sympy": "Eq(y, 29)", "operation": "FINAL"},
        ],
    }
    assert verify_item_payload(bad) is None


def test_verify_rejects_middle_eq_y():
    bad = {
        "statement_latex": r"-3+2\cdot(-4)^{2}",
        "steps": [
            {"latex": r"-3+2\cdot(-4)^{2}", "sympy": "-3+2*(-4)**2", "operation": "GIVEN"},
            {"latex": "29", "sympy": "Eq(y, 29)", "operation": "STEP"},
            {"latex": "29", "sympy": "Eq(y, 29)", "operation": "FINAL"},
        ],
    }
    assert verify_item_payload(bad) is None


def test_verify_keeps_prompt():
    good = {
        "prompt": "What is the value of the digit in the hundreds place?",
        "statement_latex": "3542",
        "steps": [
            {"latex": "3542", "sympy": "Eq(y, 3542)", "operation": "GIVEN"},
            {"latex": "500", "sympy": "Eq(y, 500)", "operation": "PLACE"},
        ],
    }
    out = verify_item_payload(good)
    assert out is not None
    assert out["prompt"].startswith("What is the value")
    assert out["statement_latex"] == "3542"


def test_verify_rejects_junk():
    assert verify_item_payload({"statement_latex": "x", "steps": []}) is None


def _frac(step1_latex=r"\frac{3}{12}+\frac{8}{12}", given_sympy="1/4+2/3", stmt=r"\dfrac{1}{4}+\dfrac{2}{3}"):
    return {
        "statement_latex": stmt,
        "steps": [
            {"latex": stmt, "sympy": given_sympy, "operation": "GIVEN"},
            {"latex": step1_latex, "sympy": "3/12+8/12", "operation": "LCD"},
            {"latex": r"\frac{11}{12}", "sympy": "Eq(y, 11/12)", "operation": "FINAL"},
        ],
    }


def test_normalizer_accepts_dfrac():
    item, reason = verify_item(_frac())
    assert reason == "" and item["statement_latex"] == r"\frac{1}{4}+\frac{2}{3}"


def test_mixed_numbers_verify():
    stmt = r"2\frac{1}{3} + 1\frac{1}{4}"
    item, reason = verify_item(
        {
            "statement_latex": stmt,
            "steps": [
                {"latex": stmt, "sympy": "2 + 1/3 + 1 + 1/4", "operation": "GIVEN"},
                {"latex": r"\frac{7}{3} + \frac{5}{4}", "sympy": "7/3 + 5/4", "operation": "CONVERT"},
                {"latex": r"3\frac{7}{12}", "sympy": "43/12", "operation": "FINAL"},
            ],
        }
    )
    assert reason == "" and item["statement_latex"] == stmt


def test_bad_middle_latex_rerendered_but_bad_given_rejected():
    item, _ = verify_item(_frac(step1_latex=r"\frac{3}{12}+\frac{9}{12}"))
    assert item is not None and "8" in item["steps"][1]["latex"]
    assert verify_item(_frac(given_sympy="1/4+2/5")) == (None, "step_latex:0")


def test_batch_repair_topup_call_budget():
    good = lambda a: {  # noqa: E731
        "statement_latex": f"{a}+1",
        "steps": [
            {"latex": f"{a}+1", "sympy": f"{a}+1", "operation": "GIVEN"},
            {"latex": str(a + 1), "sympy": f"Eq(y, {a + 1})", "operation": "FINAL"},
        ],
    }
    fixable = {**good(5), "steps": [good(5)["steps"][0], {"latex": "7", "sympy": "Eq(y, 6)"}]}
    calls: list[str] = []

    def fake(*, task, **_):
        calls.append(task)
        if task.startswith("These items failed"):
            assert "step 1" in task
            return [good(5)]
        if len(calls) == 1:
            return [good(1), good(1), fixable]  # good + duplicate + fixable
        return [good(2), good(3)]  # top-up

    specs = [{"facet": "add"}]
    with patch.object(item_gen, "request_items", side_effect=fake):
        out = generate_items_for_node(node_title="Addition", api_key="k", count=4, specs=specs)
    assert [i["statement_latex"] for i in out] == ["1+1", "5+1", "2+1", "3+1"]
    assert len(calls) <= len(specs) + 1 + 1


def test_family_pack_components_follow_profile_categories():
    code = {"categories": ["core", "code"], "answer_modes": ["code", "choice", "short_text"]}
    allowed = item_gen.allowed_components(code)
    assert {"CodeExercise", "PredictOutput", "QuickCheck"} <= set(allowed) and "TranslationAnswer" not in allowed
    system = item_gen._generic_system({**code, "subject": "Python", "level": "beginner",
                                       "notation": "code", "instruction_language": "en"}, allowed)
    assert "dedicated formats ['PredictOutput', 'CodeExercise']" in system
    item, _ = item_gen.verify_generic_item({
        "prompt_md": "Write add(a, b).",
        "parts": [{"component": "CodeExercise", "props": {
            "language": "python", "starter": "def add(a, b):\n    pass", "tests": [{"call": "add(1, 2)", "expect": "3"}]},
            "answer_spec": {"solution": "def add(a, b):\n    return a + b"}}],
    }, allowed)
    assert item["parts"][0]["answer_spec"]["beta"] is True and "solution" not in item["parts"][0]["props"]


def test_predict_output_prompt_drops_the_fenced_code_copy():
    item, why = item_gen.verify_generic_item({
        "prompt_md": "What does this print?\n\n```python\nprint(1)\n```",
        "parts": [{"component": "PredictOutput", "props": {"language": "python", "code": "print(1)"},
                   "answer_spec": {"accepted": ["1"]}}],
    }, ["PredictOutput"])
    assert item, why
    assert item["prompt_md"] == item["parts"][0]["props"]["prompt"] == "What does this print?"


def test_spare_items_do_not_steal_another_specs_slot():
    item = lambda a: {  # noqa: E731
        "statement_latex": f"{a}+1",
        "steps": [
            {"latex": f"{a}+1", "sympy": f"{a}+1", "operation": "GIVEN"},
            {"latex": str(a + 1), "sympy": f"Eq(y, {a + 1})", "operation": "FINAL"},
        ],
    }

    def fake(*, task, **_):  # spec 0 answers first with an overshoot item
        return [item(1), item(2)] if '"a"' in task else [item(9)]

    specs = [{"facet": "a"}, {"facet": "b"}]
    with patch.object(item_gen, "request_items", side_effect=fake):
        out = generate_items_for_node(node_title="Addition", api_key="k", count=2, specs=specs)
    assert [(i["statement_latex"], i["spec_index"]) for i in out] == [("1+1", 0), ("9+1", 1)]
