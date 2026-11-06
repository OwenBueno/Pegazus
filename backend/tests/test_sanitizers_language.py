"""Language pack (Doc 11 MS-4.2): AudioClip, Pronunciation, TranslationAnswer."""

from app.graders import grade
from app.services.component_catalog import sanitize_part, sanitize_visual


def test_target_language_profile_gets_audio():
    from app.services.subject_profile import clamp_profile

    assert "media" in clamp_profile({"categories": ["language"], "target_language": "es"})["categories"]
    assert "media" not in clamp_profile({"categories": ["humanities"]})["categories"]


def test_audio_clip_lang_and_rate():
    ok = sanitize_visual({"type": "AudioClip", "props": {"text": "Bonjour", "lang": "fr-FR", "rate": 3}})
    assert ok["props"] == {"text": "Bonjour", "lang": "fr-FR", "rate": 1.5}
    assert sanitize_visual({"type": "AudioClip", "props": {"text": "Bonjour", "lang": "french!"}}) is None


def test_pronunciation_part():
    p = sanitize_part({"component": "Pronunciation", "props": {"phrase": "¿Dónde está el baño?", "lang": "es-ES"}})
    assert p["grader"] == "speech_match" and p["props"]["lang"] == "es-ES"
    assert grade("speech_match", p["answer_spec"], {"transcript": "donde esta el bano"}).is_success
    assert isinstance(sanitize_part({"component": "Pronunciation", "props": {"phrase": "hola", "lang": ""}}), str)


def test_translation_exact_then_rubric_spec():
    p = sanitize_part({
        "component": "TranslationAnswer",
        "props": {"source": "Where is the station?", "lang": "es"},
        "answer_spec": {"accepted": ["¿Dónde está la estación?"]},
    })
    assert p["props"] == {"source": "Where is the station?", "lang": "es"}  # no key in props
    spec = p["answer_spec"]
    assert spec["rubric"] and spec["exemplar"] == "¿Dónde está la estación?"
    assert grade("exact", spec, {"text": "dónde está la estación"}).is_success
    assert not grade("exact", spec, {"text": "donde esta la estacion"}).is_success  # accents count
    # Without a key a miss stays a miss (no LLM); with a key grade() would ask rubric_llm.
    assert not grade("exact", spec, {"text": "¿Dónde es la estación?"}).is_success
