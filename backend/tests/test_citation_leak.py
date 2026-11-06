"""No uncited URL reaches a lesson payload (Doc 10 R4, Doc 11 MS-5.1)."""

from __future__ import annotations

import re
from uuid import uuid4

from app.pipeline.research_brief import _add_citations
from app.schemas import PathNodeOut, SessionNodeOut
from app.services.component_catalog import scrub_urls
from app.services.lesson_beats import cited_urls, normalize_design

CITED = "https://en.wikipedia.org/wiki/French_Revolution"
BRIEF = {"sources": [{"kind": "web", "title": "French Revolution", "url": CITED + "/", "quote": "1789"}]}
URL = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)[^\s\"'<>)\]]+", re.I)
BODY = (
    "The Estates-General met in 1789 ([source](" + CITED + "), [blog](https://evil.example/x)). "
    "See https://evil.example/y. or www.spam.example, ![img](https://evil.example/i.png) "
    "and [rel](/admin) and [x](javascript:alert(1)). Cited again: " + CITED + "#Causes."
) * 3


def _urls(blob: str) -> set[str]:
    return {u.rstrip(".,;:!?").split("#")[0].rstrip("/") for u in URL.findall(blob)}


def test_designed_lesson_keeps_only_cited_urls() -> None:
    teach = {"kind": "teach", "type": "concept", "title": "Causes", "body_md": BODY}
    excerpt = {**teach, "visual": {"type": "SourceExcerpt", "props": {
        "quote": "Men are born and remain free.", "source": "Declaration", "url": "https://evil.example/d"}}}
    cited = {**teach, "visual": {"type": "SourceExcerpt", "props": {
        "quote": "Men are born and remain free.", "source": "Declaration", "url": CITED + "#Rights"}}}
    ai = {
        "beats": [excerpt, cited, {"kind": "problem", "spec_index": 0}, {"kind": "problem", "spec_index": 1}],
        "problem_specs": [{"widget": "QuickCheck"}, {"widget": "QuickCheck"}],
    }
    profile = {"subject": "French Revolution", "categories": ["core", "humanities"], "notation": "none",
               "answer_modes": ["choice"], "level": "beginner", "instruction_language": "en"}
    design = normalize_design(ai, brief=BRIEF, profile=profile)
    assert "url" not in design["beats"][0]["visual"]["props"]
    assert design["beats"][1]["visual"]["props"]["url"] == CITED  # canonical cited spelling
    for out in (
        SessionNodeOut(id=uuid4(), slug="s", title="t", lesson_beats=design["beats"], primer_md=BODY,
                       sources=BRIEF["sources"]),
        PathNodeOut(node_id=uuid4(), slug="s", title="t", sequence_index=0, is_draft=False, p_mastery=0,
                    label="unknown", lesson_beats=design["beats"], primer_md=BODY, sources=BRIEF["sources"]),
    ):
        blob = out.model_dump_json()
        assert _urls(blob) == {CITED}, _urls(blob)
        assert "javascript:" not in blob and "(/admin)" not in blob and "[blog]" not in blob
        assert "blog" in blob  # uncited link keeps its text
    # No sources at all → no URL survives anywhere.
    assert not _urls(str(scrub_urls({"a": [BODY]}, set())))
    assert cited_urls(BRIEF) == {CITED}


def test_rubric_feedback_and_tutor_reply_drop_urls(monkeypatch) -> None:
    import json

    import httpx

    from app.graders import grade
    from app.services import llm, tutor_chat
    from app.services.jev_intent import IntentResult

    text = "Mention absorption, see [notes](https://evil.example/n) or www.spam.example."
    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"choices": [{"message": {"content": json.dumps(
        {"met": [True], "feedback": text})}}]})
    spec = {"rubric": [{"criterion": "names chlorophyll", "points": 1}], "question": "Why green?"}
    fb = grade("rubric_llm", spec, {"text": "Leaves contain chlorophyll which reflects green light."}, api_key="k").feedback
    assert fb and not _urls(fb) and "notes" in fb

    monkeypatch.setattr(tutor_chat, "classify_intent", lambda **k: IntentResult("ON_TOPIC", 0.0))
    monkeypatch.setattr(tutor_chat.settings, "ai_enabled", "true")
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
        "choices": [{"message": {"content": json.dumps({"reply": text, "refused": False})}}]})))
    out = tutor_chat.generate_tutor_reply(message="Why?", locale="en", node_title="Leaves", primer_md=None,
                                          statement_latex="", prompt=None, steps=[], history=[], turn_index=1,
                                          api_key="k", client=http)
    assert out.source == "SYSTEM2" and not _urls(out.reply) and "notes" in out.reply


def test_only_http_citations_become_sources() -> None:
    raw = {"choices": [{"message": {"annotations": [
        {"url_citation": {"url": CITED, "title": "FR", "content": "  The   Estates-General  "}},
        {"url_citation": {"url": "javascript:alert(1)", "title": "x"}},
        {"url_citation": {"url": CITED, "title": "dupe"}},
    ]}}]}
    sources: list[dict] = []
    _add_citations(sources, raw)
    assert sources == [{"kind": "web", "title": "FR", "url": CITED, "license": "", "quote": "The Estates-General"}]
