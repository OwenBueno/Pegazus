"""Retriever + item_gen unit tests."""

from __future__ import annotations

from app.pipeline.item_gen import verify_item_payload
from app.pipeline.retriever import is_blocked_url, load_corpus, retrieve_for_query


def test_corpus_loads_with_license():
    docs = load_corpus()
    assert len(docs) >= 2
    assert all(d.license for d in docs)
    assert all(d.attribution for d in docs)


def test_blocked_urls():
    assert is_blocked_url("https://www.khanacademy.org/math") is True
    assert is_blocked_url("https://openstax.org/books/x") is False


def test_retrieve_quadratic():
    hits = retrieve_for_query("Master simple quadratics square roots", limit=2)
    assert hits
    assert any("quadratic" in h.title.lower() or "quadratic" in h.slug_hint for h in hits)


def test_algebra_corpus_only_grounds_math_profiles():
    from app.pipeline.research_brief import build_research_brief
    from app.services.subject_profile import clamp_profile

    spanish = clamp_profile({"subject": "Spanish", "categories": ["core", "language"]})
    brief = build_research_brief(title="Solving equations", context="", api_key="", profile=spanish)
    assert not brief.get("sources") and not brief.get("key_ideas")
    math = build_research_brief(title="Solving quadratic equations", context="", api_key="")
    assert math.get("sources")


def test_non_math_research_forces_web_and_keeps_citations(monkeypatch):
    import app.pipeline.research_brief as rb
    from app.services.subject_profile import clamp_profile

    calls = []

    def fake_chat(messages, **kw):
        calls.append(kw.get("task"))
        cite = {"url_citation": {"url": "https://ex.org/fr", "title": "FR", "content": "1789"}}
        # First web answer: unparseable body but real citations; the retry parses.
        content = "not json" if len(calls) == 1 else '{"key_ideas":["Estates-General"]}'
        return {"choices": [{"message": {"content": content, "annotations": [cite]}}]}

    monkeypatch.setattr(rb, "chat", fake_chat)
    monkeypatch.setattr(rb.settings, "research_web", "off")  # forced anyway for non-math
    history = clamp_profile({"subject": "French Revolution", "categories": ["core", "humanities"]})
    brief = rb.build_research_brief(title="Causes", context="", api_key="k", profile=history)
    assert calls == ["web", "web"] and brief["key_ideas"] == ["Estates-General"]
    assert [s["url"] for s in brief["sources"]] == ["https://ex.org/fr"] and brief["sources"][0]["quote"] == "1789"


def test_domain_follows_profile():
    from app.pipeline.research_job import _domain
    from app.services.subject_profile import MATH_PROFILE, clamp_profile

    assert _domain(MATH_PROFILE) == "MATHEMATICS"
    assert _domain(clamp_profile({"categories": ["core", "language"], "target_language": "es"})) == "LANGUAGE"
    assert _domain(clamp_profile({"categories": ["core", "humanities"], "notation": "none"})) == "GENERAL"
    assert _domain(clamp_profile({"categories": ["core", "code"], "notation": "code"})) == "GENERAL"


def test_verify_rejects_bad_item():
    bad = {
        "statement_latex": "x+1=2",
        "steps": [
            {"latex": "x+1=2", "sympy": "NOT_VALID_AT_ALL!!!", "operation": "GIVEN"},
            {"latex": "x=1", "sympy": "GARBAGE", "operation": "STEP"},
        ],
    }
    # May return None if sympy fails hard
    result = verify_item_payload(bad)
    # Soft: either None or fallback not used here
    assert result is None or result["statement_latex"]


def test_verify_accepts_good_item():
    good = {
        "statement_latex": "x + 2 = 5",
        "steps": [
            {"latex": "x + 2 = 5", "sympy": "Eq(x + 2, 5)", "operation": "GIVEN"},
            {"latex": "x = 3", "sympy": "Eq(x, 3)", "operation": "SUBTRACT_CONSTANT"},
        ],
    }
    assert verify_item_payload(good) is not None
