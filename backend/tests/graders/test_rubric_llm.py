import json

from app.graders import grade
from app.graders import rubric_llm
from app.services import llm

SPEC = {
    "rubric": [{"criterion": "names chlorophyll", "points": 2}, {"criterion": "says light is absorbed", "points": 1}],
    "exemplar": "Chlorophyll absorbs red and blue light and reflects green.",
    "key_terms": ["chlorophyll", "light", "green"],
    "question": "Why are most leaves green?",
}
ANSWER = {"text": "Leaves contain chlorophyll which reflects green light."}


def _fake_chat(met, calls):
    def chat(messages, **kw):
        calls.append((messages, kw))
        content = json.dumps({"met": met, "feedback": "Mention absorption."})
        return {"choices": [{"message": {"content": content}}], "usage": {"cost": 0.0002}}
    return chat


def test_llm_scores_criteria_and_caches(monkeypatch):
    rubric_llm._cache.clear()
    calls = []
    monkeypatch.setattr(llm, "chat", _fake_chat([True, False], calls))
    r = grade("rubric_llm", SPEC, ANSWER, api_key="k", cache_key="item1")
    assert r.verdict == "PARTIAL" and abs(r.score - 2 / 3) < 1e-9 and r.decided_by == "JEV"
    assert r.feedback == "Mention absorption." and r.extra["cost_usd"] == 0.0002
    assert calls[0][1]["temperature"] == 0.0
    again = grade("rubric_llm", SPEC, {"text": "  leaves CONTAIN chlorophyll, which reflects green light "}, api_key="k", cache_key="item1")
    assert len(calls) == 1 and again.score == r.score and again.extra["cost_usd"] == 0.0


def test_pre_checks_never_call_the_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "chat", _fake_chat([True, True], calls))
    for text in ("", "chlorophyll is green", SPEC["question"]):
        assert grade("rubric_llm", SPEC, {"text": text}, api_key="k").score == 0
    assert grade("rubric_llm", SPEC, {"text": 5}, api_key="k").verdict == "SYNTAX_ERROR"
    assert calls == []


def test_no_key_or_bad_reply_falls_back_to_key_terms(monkeypatch):
    r = grade("rubric_llm", SPEC, ANSWER)  # chlorophyll + light + green = all 3 key terms
    assert r.is_success and r.decided_by == "RULES"
    assert grade("rubric_llm", SPEC, {"text": "plants are nice and they grow tall"}).score == 0
    monkeypatch.setattr(llm, "chat", _fake_chat([True], []))  # wrong length → fallback
    assert grade("rubric_llm", SPEC, ANSWER, api_key="k").decided_by == "RULES"


def test_short_answer_falls_back_to_rubric_only_with_key(monkeypatch):
    spec = {"accepted": ["chlorophyll"], "rubric": [{"criterion": "green pigment", "points": 1}],
            "question": "What pigment?", "min_words": 1}
    assert grade("exact", spec, {"text": "Chlorophyll"}).is_success
    assert not grade("exact", spec, {"text": "the green pigment"}).is_success  # no key: exact only
    monkeypatch.setattr(llm, "chat", _fake_chat([True], []))
    assert grade("exact", spec, {"text": "the green pigment"}, api_key="k").is_success
