"""Per-lesson research brief: allowlisted corpus + optional web search → structured JSON.

The brief is cached on knowledge_nodes (shared by slug) and feeds the lesson designer,
primer, item specs and critic.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.pipeline.retriever import best_passage, is_blocked_url, retrieve_for_query
from app.services.llm import chat, content_json, url_citations
from app.services.subject_profile import MATH_PROFILE, is_math, profile_prompt

LIST_KEYS = (
    "objectives",
    "prerequisites",
    "key_ideas",
    "misconceptions",
    "real_world_hooks",
    "fun_facts",
    "difficulty_ladder",
)

def _system(profile: dict[str, Any]) -> str:
    katex = profile["notation"] in ("math", "chem")
    step = "latex step" if katex else "step"
    return (
        f"You are an education researcher for {profile['subject']} preparing ONE lesson.\n"
        + profile_prompt(profile)
        + "\nUse the provided corpus excerpts and any web results as references, but write "
        "everything in your own words (never copy text verbatim). Return ONLY JSON:\n"
        '{"objectives":["learner can ..."],"prerequisites":["..."],'
        '"key_ideas":["..."],"misconceptions":["typical error + why it happens"],'
        f'"worked_examples":[{{"problem_md":"...","steps":["{step}",...],"note":"..."}}],'
        '"real_world_hooks":["..."],"fun_facts":["true, checkable fact"],'
        '"difficulty_ladder":["easiest variant","...","hardest variant"]}\n'
        "Rules: stay strictly on the skill; 2-5 entries per list; 2-3 worked examples with "
        + ("3-5 correct KaTeX steps (no $ delimiters)" if katex else "3-5 clear steps")
        + "; fun facts must be accurate — omit if unsure; "
        "misconceptions must be specific to this skill."
    )


def build_research_brief(
    *,
    title: str,
    context: str,
    api_key: str,
    description: str = "",
    profile: dict[str, Any] | None = None,
    use_corpus: bool = True,
) -> dict[str, Any]:
    """Research one skill. No key → corpus-only brief for math, empty brief otherwise.

    The OpenStax corpus is algebra: it grounds only math profiles (and only with ``use_corpus``).
    """
    profile = profile or MATH_PROFILE
    corpus_on = use_corpus and "math" in profile["categories"]
    hits = retrieve_for_query(f"{title} {description}", limit=3) if corpus_on else []
    corpus = [
        {
            "title": h.title,
            "excerpt": best_passage(h.body, title),
            "license": h.license,
            "attribution": h.attribution,
        }
        for h in hits
    ]
    sources: list[dict[str, str]] = [
        {"kind": "corpus", "title": h.title, "url": h.source_url, "license": h.license}
        for h in hits
    ]
    if not api_key:
        return clean_brief({"key_ideas": [c["excerpt"][:300] for c in corpus]}, sources)

    messages = [
        {"role": "system", "content": _system(profile)},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "skill": title,
                    "skill_notes": description[:500],
                    "learner_context": context[:1500],
                    "corpus_excerpts": corpus,
                }
            ),
        },
    ]
    # Non-math lessons have no corpus: web research is their only grounding (Doc 10 §7).
    web_tries = 2 if not is_math(profile) else 1 if settings.research_web_on else 0
    data = None
    for _ in range(web_tries):
        raw = chat(
            messages,
            api_key=api_key,
            task="web",
            temperature=0.2,
            plugins=[{"id": "web", "max_results": 5}],
        )
        # Citations count even when the JSON body is unusable (the retry below re-asks).
        _add_citations(sources, raw)
        data = data or content_json(raw)
        if data is not None and any(s["kind"] == "web" for s in sources):
            break
    if data is None:
        # Web plugin unavailable / unparseable → same prompt without live search.
        data = content_json(chat(messages, api_key=api_key, task="strong", temperature=0.2))
    return clean_brief(data or {}, sources)


def _add_citations(sources: list[dict[str, str]], raw: dict[str, Any] | None) -> None:
    """Only URLs the web plugin returned as ``url_citations`` are citable (Doc 10 R4)."""
    for c in url_citations(raw):
        if c["url"].startswith(("https://", "http://")) and not is_blocked_url(c["url"]) and all(
            s.get("url") != c["url"] for s in sources
        ):
            sources.append(
                {"kind": "web", "title": c["title"], "url": c["url"], "license": "", "quote": c["quote"]}
            )


def clean_brief(data: dict[str, Any], sources: list[dict[str, str]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in LIST_KEYS:
        vals = data.get(k)
        out[k] = (
            [str(v).strip()[:300] for v in vals if str(v).strip()][:6]
            if isinstance(vals, list)
            else []
        )
    examples: list[dict[str, Any]] = []
    for ex in data.get("worked_examples") or []:
        problem = ex.get("problem_md") or ex.get("problem_latex") if isinstance(ex, dict) else None
        if not problem:
            continue
        steps = [str(s).strip()[:200] for s in (ex.get("steps") or []) if str(s).strip()][:6]
        examples.append(
            {
                "problem_md": str(problem)[:300],
                "steps": steps,
                "note": str(ex.get("note") or "")[:300],
            }
        )
    out["worked_examples"] = examples[:3]
    out["sources"] = sources[:8]
    return out


def brief_digest(brief: dict[str, Any] | None, max_chars: int = 2500) -> str:
    """Compact text form for prompts."""
    if not brief:
        return ""
    return json.dumps({k: v for k, v in brief.items() if k != "sources" and v})[:max_chars]


def attribution_from(brief: dict[str, Any] | None, fallback: str) -> str:
    srcs = (brief or {}).get("sources") or []
    names = [s.get("title") or s.get("url") for s in srcs if s.get("title") or s.get("url")]
    return ("Sources: " + "; ".join(names[:4]))[:500] if names else fallback
