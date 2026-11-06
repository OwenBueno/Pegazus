"""Tutor chat — conceptual help without answer leaks."""

from app.services.leak_check import forbidden_from_item_steps, hint_leaks_answer
from app.services.tutor_chat import (
    MAX_TURNS,
    generate_tutor_reply,
    templated_tutor_reply,
)


def test_templated_reply_mentions_topic():
    r = templated_tutor_reply(
        node_title="Order of Operations with Integers",
        locale="en",
        answer_seeking=False,
    )
    assert "Order of Operations" in r
    assert "answer" not in r.lower() or "final" not in r.lower()


def test_templated_refuses_answer_seeking():
    r = templated_tutor_reply(
        node_title="PEMDAS", locale="en", answer_seeking=True
    )
    assert "will not give the final answer" in r.lower() or "not give" in r.lower()


def test_generate_without_api_key_uses_template():
    steps = [
        {"latex": r"-3+2\cdot(-4)^{2}", "sympy": "Eq(y, -3+2*(-4)**2)"},
        {"latex": "-35", "sympy": "Eq(y, -35)"},
    ]
    out = generate_tutor_reply(
        message="Why do I square before multiplying?",
        locale="en",
        node_title="Order of Operations with Integers",
        primer_md="Exponents before multiplication.",
        statement_latex=r"-3+2\cdot(-4)^{2}",
        prompt="Compute the value.",
        steps=steps,
        history=[],
        turn_index=1,
        api_key="",
    )
    assert out.source == "TEMPLATE"
    assert not out.capped
    assert "Order of Operations" in out.reply or "core idea" in out.reply.lower()
    assert not hint_leaks_answer(out.reply, forbidden_from_item_steps(steps))


def test_answer_seeking_without_key_refuses():
    out = generate_tutor_reply(
        message="What is the answer?",
        locale="en",
        node_title="Order of Operations",
        primer_md=None,
        statement_latex="1+2",
        prompt=None,
        steps=[{"latex": "3", "sympy": "Eq(y, 3)"}],
        history=[],
        turn_index=1,
        api_key="",
    )
    assert out.refused
    assert "final answer" in out.reply.lower() or "not" in out.reply.lower()


def test_cap_after_max_turns():
    out = generate_tutor_reply(
        message="Tell me more about exponents",
        locale="en",
        node_title="Ops",
        primer_md=None,
        statement_latex="1+1",
        prompt=None,
        steps=[{"latex": "2"}],
        history=[],
        turn_index=MAX_TURNS + 1,
        api_key="",
    )
    assert out.capped
    assert out.source == "TEMPLATE"


def test_leak_check_catches_final_step():
    forbidden = forbidden_from_item_steps(
        [{"latex": "-35", "sympy": "Eq(y, -35)"}]
    )
    assert hint_leaks_answer("The value is $-35$.", forbidden)
    assert not hint_leaks_answer(
        "Do exponents before multiplying.", forbidden
    )
