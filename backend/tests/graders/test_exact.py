from app.graders import grade
from app.graders.exact import normalize


def test_exact() -> None:
    assert grade("exact", {"accepted": ["Paris"]}, {"text": "  PARIS. "}).is_success
    assert not grade("exact", {"accepted": ["Paris"]}, {"text": "Lyon"}).is_success
    assert not grade("exact", {"accepted": ["¿Dónde?"]}, {"text": "donde"}).is_success  # accents kept
    assert grade("exact", {"accepted": ["¿Dónde?"], "strip_accents": True}, {"text": "donde"}).is_success
    assert not grade("exact", {"accepted": ["NaCl"], "case": True}, {"text": "nacl"}).is_success
    assert normalize("ﬁne   day!") == "fine day"  # NFKC ligature, punctuation, whitespace


def test_exact_garbage() -> None:
    assert grade("exact", {"accepted": ["a"]}, {"text": 5}).verdict == "SYNTAX_ERROR"
    assert grade("exact", {"accepted": ["a"]}, {"text": "a" * 501}).verdict == "SYNTAX_ERROR"
    assert not grade("exact", {"accepted": ["!"]}, {"text": "?"}).is_success  # empty after normalize
