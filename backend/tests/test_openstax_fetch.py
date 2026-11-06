"""Allowlisted OpenStax fetch unit tests (no live network)."""

from __future__ import annotations

import pytest

from app.pipeline import openstax_fetch as of


def test_assert_url_allowed_rejects_unknown():
    with pytest.raises(ValueError, match="not in allowlist"):
        of.assert_url_allowed("https://openstax.org/books/fake/pages/1")


def test_assert_url_allowed_rejects_blocked_host():
    with pytest.raises(ValueError, match="blocked|not in OpenStax"):
        of.assert_url_allowed("https://www.khanacademy.org/math")


def test_html_to_markdown_strips_script():
    html = "<html><script>evil()</script><p>Solve x + 1 = 2</p></html>"
    body = of.html_to_markdown_body(html)
    assert "evil" not in body
    assert "Solve" in body


def test_write_corpus_md(tmp_path, monkeypatch):
    monkeypatch.setattr(of, "CORPUS_DIR", tmp_path)
    path = of.write_corpus_md(
        slug="test_doc",
        title="Test",
        source_url="https://openstax.org/details/books/elementary-algebra-2e",
        attribution="OpenStax",
        body="Linear equations overview.",
    )
    text = path.read_text(encoding="utf-8")
    assert "license: CC-BY-4.0" in text
    assert "source_url:" in text
    assert "Linear equations" in text
