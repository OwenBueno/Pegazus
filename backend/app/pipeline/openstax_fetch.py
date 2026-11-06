"""Allowlisted OpenStax chapter fetch → local corpus Markdown (FR-1.4).

Not a general crawler: only URLs in openstax_allowlist.json; blocked hosts refused;
polite delay between requests. Offline seed corpus remains the default when fetch is skipped.
"""

from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.pipeline.retriever import BLOCKED_HOST_FRAGMENTS

_PIPELINE = Path(__file__).resolve().parent
ALLOWLIST_PATH = _PIPELINE / "openstax_allowlist.json"
CORPUS_DIR = _PIPELINE / "corpus"
ALLOWED_HOSTS = ("openstax.org", "cnx.org")
USER_AGENT = "PegazusCorpusBot/0.1 (+local; allowlisted CC-BY fetch)"
DELAY_S = 1.0
TIMEOUT_S = 20.0


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        t = data.strip()
        if t:
            self._chunks.append(t)

    def text(self) -> str:
        return "\n\n".join(self._chunks)


def load_allowlist() -> list[dict]:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))["allowlist"]


def assert_url_allowed(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if any(b in host for b in BLOCKED_HOST_FRAGMENTS):
        raise ValueError(f"blocked host: {host}")
    if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        raise ValueError(f"host not in OpenStax allowlist hosts: {host}")
    allowed_urls = {e["url"] for e in load_allowlist()}
    if url not in allowed_urls:
        raise ValueError(f"URL not in allowlist: {url}")


def html_to_markdown_body(html: str, *, max_chars: int = 8000) -> str:
    p = _TextExtractor()
    p.feed(html)
    body = p.text()
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) > max_chars:
        body = body[:max_chars].rsplit("\n", 1)[0] + "\n\n…"
    return body


def write_corpus_md(
    *,
    slug: str,
    title: str,
    source_url: str,
    attribution: str,
    body: str,
    license_id: str = "CC-BY-4.0",
) -> Path:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    path = CORPUS_DIR / f"{slug}.md"
    text = (
        "---\n"
        f"title: {title}\n"
        f"slug_hint: math.algebra.{slug.replace('openstax_', '')}\n"
        f"license: {license_id}\n"
        f"source_url: {source_url}\n"
        f"attribution: {attribution}\n"
        "---\n\n"
        f"{body}\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def fetch_one(entry: dict, *, client: httpx.Client) -> Path:
    url = entry["url"]
    assert_url_allowed(url)
    resp = client.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    body = html_to_markdown_body(resp.text)
    if len(body) < 80:
        raise RuntimeError(f"fetched body too short for {url}")
    return write_corpus_md(
        slug=entry["slug"],
        title=entry["title"],
        source_url=url,
        attribution=entry.get("attribution", "OpenStax, CC BY 4.0"),
        body=body,
    )


def fetch_allowlist(*, delay_s: float = DELAY_S) -> list[Path]:
    written: list[Path] = []
    with httpx.Client(timeout=TIMEOUT_S) as client:
        for i, entry in enumerate(load_allowlist()):
            if i:
                time.sleep(delay_s)
            written.append(fetch_one(entry, client=client))
    return written
