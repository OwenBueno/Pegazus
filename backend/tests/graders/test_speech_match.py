from app.graders import grade

S = {"phrase": "¿Dónde está el baño?"}


def test_transcript_within_edit_distance() -> None:
    assert grade("speech_match", S, {"transcript": "Dónde está el baño"}).is_success
    assert grade("speech_match", S, {"transcript": "donde esta el vano"}).is_success  # 1 edit
    r = grade("speech_match", S, {"transcript": "donde esta la playa"})
    assert not r.is_success and r.decided_by == "RULES"


def test_self_rating_never_blocks() -> None:
    r = grade("speech_match", S, {"self": 1})
    assert r.is_success and r.decided_by == "CLIENT"
    assert not grade("speech_match", S, {"self": 0}).is_success
    for bad in ({"self": 2}, {"self": True}, {"transcript": 5}, {}):
        assert grade("speech_match", S, bad).verdict == "SYNTAX_ERROR", bad
