"""Upload text extraction helpers."""

from app.services.upload_parse import digest_text, extract_text_from_bytes


def test_extract_plain_utf8():
    text = extract_text_from_bytes(b"Solve x + 1 = 2\n", "notes.txt")
    assert "Solve" in text


def test_digest_truncates():
    long = "a" * 5000
    d = digest_text(long, 100)
    assert len(d) <= 100
    assert d.endswith("…[truncated]")
