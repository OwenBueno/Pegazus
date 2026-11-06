"""Allowlisted local corpus retriever (FR-1.4). No live web scrape."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

BLOCKED_HOST_FRAGMENTS = (
    "khanacademy.org",
    "ocw.mit.edu",
    "coursera.org",
    "udemy.com",
)

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class CorpusDoc:
    title: str
    slug_hint: str
    license: str
    source_url: str
    attribution: str
    body: str
    path: str


def _parse_meta(raw: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def load_corpus() -> list[CorpusDoc]:
    docs: list[CorpusDoc] = []
    if not _CORPUS_DIR.is_dir():
        return docs
    for path in sorted(_CORPUS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = _FRONT_MATTER.match(text)
        if not m:
            continue
        meta = _parse_meta(m.group(1))
        url = meta.get("source_url", "")
        if any(b in url.lower() for b in BLOCKED_HOST_FRAGMENTS):
            continue
        docs.append(
            CorpusDoc(
                title=meta.get("title", path.stem),
                slug_hint=meta.get("slug_hint", f"math.generated.{path.stem}"),
                license=meta.get("license", "CC-BY-4.0"),
                source_url=url,
                attribution=meta.get("attribution", "Pegazus corpus"),
                body=m.group(2).strip(),
                path=str(path.name),
            )
        )
    return docs


def _token_list(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _tokens(text: str) -> set[str]:
    return set(_token_list(text))


def retrieve_for_query(query: str, *, limit: int = 3) -> list[CorpusDoc]:
    """BM25 over the local allowlisted corpus (no live web)."""
    # ponytail: re-tokenizes the corpus per query; fine for tens of docs, cache or pgvector past ~1k.
    q = _tokens(query)
    docs = load_corpus()
    if not q or not docs:
        return []
    toks = [_token_list(f"{d.title} {d.title} {d.slug_hint} {d.body}") for d in docs]
    n = len(docs)
    avgdl = sum(len(t) for t in toks) / n or 1.0
    df = Counter(t for ts in toks for t in set(ts))
    k1, b = 1.5, 0.75
    scored: list[tuple[float, CorpusDoc]] = []
    for doc, ts in zip(docs, toks):
        tf = Counter(ts)
        norm = k1 * (1 - b + b * len(ts) / avgdl)
        score = sum(
            math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) * tf[t] * (k1 + 1) / (tf[t] + norm)
            for t in q
            if tf[t]
        )
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: (-x[0], x[1].slug_hint))
    return [d for _, d in scored[:limit]]


def best_passage(body: str, query: str, *, max_chars: int = 700) -> str:
    """Most query-relevant paragraphs of a doc, kept in original order."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    q = _tokens(query)
    ranked = sorted(range(len(paras)), key=lambda i: -len(q & _tokens(paras[i])))
    keep: list[int] = []
    used = 0
    for i in ranked:
        if used + len(paras[i]) > max_chars and keep:
            break
        keep.append(i)
        used += len(paras[i])
    return "\n\n".join(paras[i] for i in sorted(keep))[:max_chars]


def is_blocked_url(url: str) -> bool:
    u = (url or "").lower()
    return any(b in u for b in BLOCKED_HOST_FRAGMENTS)
