"""Parse user uploads to plain text (no long-term file storage)."""

from __future__ import annotations

import re

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 80_000


def extract_text_from_bytes(data: bytes, filename: str | None = None) -> str:
    """Best-effort text extraction from PDF or plain/text-like uploads."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds 10 MB limit")
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return _pdf_to_text(data)[:MAX_TEXT_CHARS]
    # UTF-8 / latin-1 plaintext
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)[:MAX_TEXT_CHARS]
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]


def _pdf_to_text(data: bytes) -> str:
    """Minimal PDF text scrape without a heavy PDF library (ponytail: ceiling = scanned PDFs)."""
    # Decode latin-1 so binary stays 1:1; pull (...) string literals and Tj/TJ operators.
    raw = data.decode("latin-1", errors="ignore")
    chunks: list[str] = []
    for m in re.finditer(r"\((?:\\.|[^\\)])*\)", raw):
        s = m.group(0)[1:-1]
        s = (
            s.replace("\\n", "\n")
            .replace("\\r", "")
            .replace("\\t", " ")
            .replace("\\(", "(")
            .replace("\\)", ")")
            .replace("\\\\", "\\")
        )
        if s.strip():
            chunks.append(s)
    text = "\n".join(chunks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text.strip()) < 40:
        # Fallback: printable runs
        runs = re.findall(r"[\x20-\x7e\n]{4,}", raw)
        text = "\n".join(runs)
    return text.strip()


def digest_text(text: str, limit: int = 4000) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 20].rstrip() + "\n…[truncated]"
