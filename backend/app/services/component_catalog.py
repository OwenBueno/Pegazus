"""Single source of truth for GenUI components the lesson designer may pick.

Each entry: ``role`` (answer = how the learner responds, visual = display-only picture,
support = helper chrome), ``where`` (teach / problem beats), ``when`` (guidance for the AI)
and ``props`` (compact example the AI copies). Frontend twin: components/genui/registry.tsx
(tests/test_component_catalog.py keeps the two in sync).
"""

from __future__ import annotations

import ast
import hashlib
import re
from datetime import date
from fractions import Fraction
from typing import Any

from app.graders.numeric import UNITS

# (lon_min, lon_max, lat_min, lat_max); frontend twin: humanities/MapPins.tsx.
MAP_REGIONS: dict[str, tuple[float, float, float, float]] = {
    "world": (-180, 180, -60, 80),
    "europe": (-25, 45, 34, 72),
    "africa": (-20, 55, -37, 38),
    "asia": (25, 150, -12, 60),
    "middle_east": (25, 65, 10, 43),
    "north_america": (-170, -50, 5, 75),
    "south_america": (-85, -30, -57, 14),
    "oceania": (105, 180, -50, 5),
}

COMPONENTS: dict[str, dict[str, Any]] = {
    "SymbolicStepEditor": {
        "role": "answer",
        "category": "math",
        "grader": "sympy",
        "lazy": False,
        "where": ("problem",),
        "when": "multi-step compute or equations; learner writes each step",
        "props": "{}",
    },
    "FadedWorkedExample": {
        "role": "answer",
        "category": "math",
        "grader": "sympy",
        "lazy": False,
        "where": ("problem",),
        "when": "first guided problem; learner fills the blank in a worked solution",
        "props": "{}",
    },
    "QuickCheck": {
        "role": "answer",
        "category": "core",
        "grader": "choice",
        "lazy": False,
        "where": ("problem",),
        "when": "choose the right answer; concept checks that catch a misconception",
        "props": "{}",
    },
    "NumberLine": {
        "role": "answer",
        "category": "math",
        "grader": "numeric",
        "lazy": False,
        "where": ("problem",),
        "when": "magnitude, ordering, locate a value",
        "props": "{}",
    },
    "MatchPairs": {
        "role": "answer",
        "category": "core",
        "grader": "match",
        "lazy": False,
        "where": ("problem",),
        "when": "match related items (term/definition, equivalent forms, cause/effect)",
        "props": "{}",
    },
    "FunctionPlotter": {
        "role": "visual",
        "category": "math",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "graphs of functions, lines, slopes, intersections",
        "props": '{"expressions":["2*x+1"],"domain":[-5,5],"textAlt":"line rising"}',
    },
    "FractionBars": {
        "role": "visual",
        "category": "math",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "fractions as bar/area models: compare, equivalent, add with common parts",
        "props": '{"bars":[{"parts":4,"shaded":3,"label":"3/4"},{"parts":8,"shaded":6,"label":"6/8"}]}',
    },
    "BalanceScale": {
        "role": "visual",
        "category": "math",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "equations as a balance: do the same to both sides",
        "props": '{"left":"2x+3","right":"11","note":"remove 3 from both sides"}',
    },
    "DataTable": {
        "role": "visual",
        "category": "core",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "patterns, input/output, ratios, organized data, small comparison grids",
        "props": '{"headers":["x","y"],"rows":[["1","3"],["2","5"]],"highlight_col":1}',
    },
    # Alias kept because stored lesson_beats reference it; never offered to the designer.
    "ValueTable": {
        "role": "visual", "category": "core", "lazy": False,
        "where": (), "when": "alias of DataTable", "props": "{}",
    },
    "Comparison": {
        "role": "visual",
        "category": "core",
        "lazy": False,
        "where": ("teach",),
        "when": "contrast two related things side by side (mitosis vs meiosis)",
        "props": '{"left":{"title":"Mitosis","points":["2 cells"]},"right":{"title":"Meiosis","points":["4 cells"]}}',
    },
    "ProcessSteps": {
        "role": "visual",
        "category": "core",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "a process or cycle as ordered stages",
        "props": '{"steps":[{"title":"Evaporation","body":"..."}],"cyclic":true}',
    },
    "KeyTerms": {
        "role": "visual",
        "category": "core",
        "lazy": False,
        "where": ("teach",),
        "when": "vocabulary: up to 8 terms with short definitions",
        "props": '{"terms":[{"term":"Photosynthesis","def":"..."}]}',
    },
    "Diagram": {
        "role": "visual",
        "category": "media",
        "lazy": True,
        "where": ("teach", "problem"),
        "when": "a structure or flow best shown as a Mermaid flowchart",
        "props": '{"kind":"mermaid","source":"flowchart LR; A[Light]-->B[Chlorophyll]","alt":"what the diagram shows"}',
    },
    "ShortAnswer": {
        "role": "answer",
        "category": "core",
        "grader": "exact",
        "lazy": False,
        "where": ("problem",),
        "when": "recall one word, name or short phrase",
        "props": '{"question":"...","accepted":["Paris"],"rubric":null}',
    },
    "FreeResponse": {
        "role": "answer",
        "category": "core",
        "grader": "rubric_llm",
        "lazy": False,
        "where": ("problem",),
        "when": "explain why/how in a few sentences, graded against a rubric",
        "props": (
            '{"question":"Explain why...","rubric":[{"criterion":"mentions X","points":1}],'
            '"max_words":120,"exemplar":"model answer","key_terms":["X","Y"]}'
        ),
    },
    "Cloze": {
        "role": "answer",
        "category": "core",
        "grader": "cloze",
        "lazy": False,
        "where": ("problem",),
        "when": "fill missing words/terms in a sentence or definition",
        "props": '{"text":"Water boils at [[100]] °C.","aliases":{"0":["100°C"]}}',
    },
    "OrderSteps": {
        "role": "answer",
        "category": "core",
        "grader": "order",
        "lazy": False,
        "where": ("problem",),
        "when": "put events or process stages in order",
        "props": '{"prompt":"Oldest first","items":["first","second","third"]} (items in the CORRECT order)',
    },
    "Categorize": {
        "role": "answer",
        "category": "core",
        "grader": "categorize",
        "lazy": False,
        "where": ("problem",),
        "when": "sort examples into 2-4 groups",
        "props": '{"buckets":["Metal","Non-metal"],"items":[{"label":"Fe","bucket":0}]}',
    },
    "Flashcards": {
        "role": "answer",
        "category": "core",
        "grader": "flashcards",
        "lazy": False,
        "where": ("problem",),
        "when": "self-check recall of 3-12 term/meaning pairs",
        "props": '{"cards":[{"front":"chlorophyll","back":"green pigment that absorbs light"}]}',
    },
    "WorkedExample": {
        "role": "answer",
        "category": "core",
        "grader": "cloze",
        "lazy": False,
        "where": ("problem",),
        "when": "guided problem: a worked solution in steps with 1-4 key words blanked",
        "props": '{"title":"...","steps":[{"text":"Light hits the [[chlorophyll]]."},{"text":"..."}]}',
    },
    # Family packs (Doc 10 §4.2); the frontend loads each pack lazily.
    "Timeline": {
        "role": "visual", "category": "humanities", "lazy": True,
        "where": ("teach", "problem"),
        "when": "2-12 dated events in chronological context (BCE = negative year)",
        "props": '{"title":"...","events":[{"date":"1789-07-14","label":"Storming of the Bastille","detail":"..."}]}',
    },
    "MapPins": {
        "role": "visual", "category": "humanities", "lazy": True,
        "where": ("teach", "problem"),
        "when": f"1-12 places on a simple regional map; region one of {list(MAP_REGIONS)}",
        "props": '{"region":"europe","pins":[{"lat":48.85,"lon":2.35,"label":"Paris"}],"caption":"..."}',
    },
    "SourceExcerpt": {
        "role": "visual", "category": "humanities", "lazy": True,
        "where": ("teach",),
        "when": "a short primary-source quote (<=600 chars); url only from citable_sources",
        "props": '{"quote":"...","author":"...","source":"...","year":1791,"url":"https://..."}',
    },
    "CauseEffect": {
        "role": "visual", "category": "humanities", "lazy": True,
        "where": ("teach",),
        "when": "1-6 cause -> effect links explaining why something happened",
        "props": '{"title":"...","links":[{"cause":"...","effect":"..."}]}',
    },
    "AudioClip": {
        "role": "visual", "category": "media", "lazy": True,
        "where": ("teach", "problem"),
        "when": "hear a word or phrase spoken (browser text-to-speech) in its language",
        "props": '{"text":"el aeropuerto","lang":"es-ES","rate":0.9,"label":"the airport"}',
    },
    "Pronunciation": {
        "role": "answer", "category": "language", "grader": "speech_match", "lazy": True,
        "where": ("problem",),
        "when": "say a phrase aloud in the target language (speech check or self-rating)",
        "props": '{"phrase":"¿Dónde está el baño?","lang":"es-ES"}',
    },
    "TranslationAnswer": {
        "role": "answer", "category": "language", "grader": "exact", "lazy": True,
        "where": ("problem",),
        "when": "translate a short sentence into the target language",
        "props": '{"source":"Where is the station?","lang":"es","accepted":["¿Dónde está la estación?"]}',
    },
    "ChemFormula": {
        "role": "visual", "category": "science", "lazy": True,
        "where": ("teach", "problem"),
        "when": "a chemical formula or equation in mhchem \\ce{} notation",
        "props": '{"latex":"\\\\ce{2H2 + O2 -> 2H2O}","caption":"..."}',
    },
    "QuantityAnswer": {
        "role": "answer", "category": "science", "grader": "numeric", "lazy": True,
        "where": ("problem",),
        "when": f"compute a quantity with a unit; unit one of {list(UNITS)}",
        "props": '{"question":"...","value":9.8,"unit":"m/s^2","tolerance":0.02}',
    },
    "ParameterExplorer": {
        "role": "visual", "category": "science", "lazy": True,
        "where": ("teach",),
        "when": "explore y = f(x) with 1-3 parameter sliders (explicit * and ^, no implicit products)",
        "props": (
            '{"expr":"v0*t - 4.9*t^2","x":"t","domain":[0,6],'
            '"params":[{"name":"v0","min":0,"max":30,"value":15}],"textAlt":"height of a thrown ball over time"}'
        ),
    },
    "LabeledDiagram": {
        "role": "visual", "category": "science", "lazy": True,
        "where": ("teach", "problem"),
        "when": "a simple SVG picture with up to 12 labelled points (x, y as 0-1 fractions)",
        "props": '{"source":"<svg viewBox=\\"0 0 100 75\\">...</svg>","labels":[{"x":0.4,"y":0.2,"text":"Nucleus"}],"alt":"..."}',
    },
    "CodeBlock": {
        "role": "visual", "category": "code", "lazy": True,
        "where": ("teach", "problem"),
        "when": "show a short code example (<= 60 lines)",
        "props": '{"language":"python","code":"for i in range(3):\\n    print(i)","caption":"..."}',
    },
    "PredictOutput": {
        "role": "answer", "category": "code", "grader": "exact", "lazy": True,
        "where": ("problem",),
        "when": "read code and type exactly what it prints",
        "props": '{"language":"python","code":"print(2**3)","accepted":["8"]}',
    },
    "CodeExercise": {
        "role": "answer", "category": "code", "grader": "code_tests", "lazy": True,
        "where": ("problem",),
        "when": "write a small function; tests run in the learner's browser",
        "props": (
            '{"language":"python","prompt":"...","starter":"def add(a, b):\\n    pass",'
            '"tests":[{"call":"add(2, 3)","expect":"5"}],"solution":"def add(a, b):\\n    return a + b"}'
        ),
    },
    "Callout": {
        "role": "visual",
        "category": "core",
        "lazy": False,
        "where": ("teach",),
        "when": "one key tip, warning (common mistake) or fact that must stand out",
        "props": '{"tone":"tip|warning|fact","title":"Watch the sign","body_md":"..."}',
    },
    "ShapeDiagram": {
        "role": "visual",
        "category": "math",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "geometry: labeled triangle/rectangle/circle/polygon, sides and angles",
        "props": (
            '{"shape":"triangle","labels":{"a":"5","b":"12","c":"13"},"angles":[90,67.4,22.6]} '
            '(rectangle labels: width,height; circle: r; polygon: {"sides":6,"labels":{"side":"4"}})'
        ),
    },
    "CoordinateGrid": {
        "role": "visual",
        "category": "math",
        "lazy": False,
        "where": ("teach", "problem"),
        "when": "plot points, segments, distance/midpoint, quadrants",
        "props": '{"range":[-5,5],"points":[{"x":2,"y":3,"label":"A"},{"x":-1,"y":1,"label":"B"}],"segments":[[0,1]]}',
    },
    "VirtualMathKeyboard": {
        "role": "support", "category": "math", "lazy": False,
        "where": ("problem",), "when": "auto with step editor", "props": "{}",
    },
    "SocraticDialogueBox": {
        "role": "support", "category": "core", "lazy": False,
        "where": ("problem",), "when": "auto hints", "props": "{}",
    },
    "ConceptCard": {
        "role": "support", "category": "core", "lazy": False,
        "where": ("teach",), "when": "auto: the teach body", "props": "{}",
    },
}

CATEGORIES = ("core", "math", "science", "language", "humanities", "code", "media")
ANSWER_WIDGETS = tuple(n for n, c in COMPONENTS.items() if c["role"] == "answer")
VISUALS = frozenset(n for n, c in COMPONENTS.items() if c["role"] == "visual")
# Session workspace widgets (genui_plan): everything but visuals, plus the plotter.
WORKSPACE_WIDGETS = frozenset(n for n, c in COMPONENTS.items() if c["role"] != "visual") | {"FunctionPlotter"}
# Answered by tap/choice and graded from answer_spec (no step editor alongside).
SELECTION_PRIMARY = frozenset(
    n for n, c in COMPONENTS.items() if c["role"] == "answer" and c["grader"] != "sympy"
)
LAYOUTS = ("stack", "split", "focus")


def public_props(part: dict[str, Any]) -> dict[str, Any]:
    """A stored part as the client may see it: component, props, grader (no answer_spec)."""
    return {"component": part.get("component"), "grader": part.get("grader"), "props": part.get("props") or {}}


def strip_beats(beats: Any) -> list[Any]:
    """Lesson beats for the client: problem plans keep widget names only (props carry keys)."""
    out = []
    for b in beats if isinstance(beats, list) else []:
        plan = b.get("genui_plan") if isinstance(b, dict) else None
        if isinstance(plan, dict):
            widgets = [w.get("type") if isinstance(w, dict) else w for w in plan.get("widgets") or []]
            b = {**b, "genui_plan": {**{k: v for k, v in plan.items() if k != "widgets"}, "widgets": widgets}}
        out.append(b)
    return out


_MD_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(\s*<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\s*\)")
_BARE_URL = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>()\"'\]]+", re.I)


def norm_url(u: Any) -> str:
    """Comparison key for citations: trimmed, no fragment, no trailing slash."""
    return str(u or "").strip().split("#", 1)[0].rstrip("/")


def scrub_urls(obj: Any, urls: set[str] | frozenset[str]) -> Any:
    """Drop every URL that is not a research citation (Doc 10 R4) from AI text, recursively.

    Uncited markdown links keep their text, uncited images vanish, bare uncited URLs are removed.
    ``urls`` are ``norm_url`` keys. ponytail: regex over Markdown, not a parser; HTML is never
    rendered raw client-side, so href-in-HTML only needs its URL text removed.
    """
    if isinstance(obj, dict):
        return {k: scrub_urls(v, urls) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_urls(v, urls) for v in obj]
    if not isinstance(obj, str) or ("://" not in obj and "www." not in obj.lower() and "](" not in obj):
        return obj

    def link(m: re.Match[str]) -> str:
        if norm_url(m.group(3)) in urls and m.group(3).startswith(("https://", "http://")):
            return m.group(0)
        return "" if m.group(1) else m.group(2)

    def bare(m: re.Match[str]) -> str:
        u = m.group(0).rstrip(".,;:!?")
        keep = norm_url(u) in urls and u.startswith(("https://", "http://"))
        return (u if keep else "") + m.group(0)[len(u):]

    return _BARE_URL.sub(bare, _MD_LINK.sub(link, obj))


def catalog_prompt(where: str, categories: list[str] | tuple[str, ...] | None = None) -> str:
    """Prompt lines for the components usable in ``where`` ("teach" or "problem").

    ``categories`` (a subject profile's) pre-filters the list; ``core`` is always included.
    """
    allowed = None if categories is None else {*categories, "core"}
    lines = []
    for name, c in COMPONENTS.items():
        if allowed is not None and c["category"] not in allowed:
            continue
        if where in c["where"] and c["role"] != "support":
            props = "" if c["props"] == "{}" else f" props: {c['props']}"
            lines.append(f"- {name} ({c['role']}): {c['when']}.{props}")
    return "\n".join(lines)


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) < 1e6 else None


def _s(v: Any, n: int) -> str:
    return str(v if v is not None else "").strip()[:n]


_FRAC = re.compile(r"^\s*(?:\\frac\{(\d+)\}\{(\d+)\}|(\d+)\s*/\s*(\d+))\s*$")


def _fraction_bars(p: dict[str, Any]) -> dict[str, Any] | None:
    bars = []
    for b in (p.get("bars") or [])[:4]:
        if not isinstance(b, dict):
            return None
        parts, shaded = _num(b.get("parts")), _num(b.get("shaded"))
        if parts is None or shaded is None or not parts.is_integer() or not shaded.is_integer():
            return None
        if not (1 <= parts <= 12 and 0 <= shaded <= parts):
            return None
        row: dict[str, Any] = {"parts": int(parts), "shaded": int(shaded)}
        label = _s(b.get("label"), 20)
        m = _FRAC.match(label)
        # A label that names a fraction must match the picture (2/4 for 1/2 of 4 parts is fine).
        if m:
            num, den = (int(x) for x in (m.group(1) or m.group(3), m.group(2) or m.group(4)))
            if den == 0 or Fraction(num, den) != Fraction(int(shaded), int(parts)):
                return None
        if label:
            row["label"] = label
        bars.append(row)
    return {"bars": bars} if bars else None


def _balance(p: dict[str, Any]) -> dict[str, Any] | None:
    from app.workers.math_evaluator import _parse

    left, right = _s(p.get("left"), 80), _s(p.get("right"), 80)
    if not left or not right:
        return None
    # The LaTeX fallback parser is lenient (``2x+(`` → 2x), so check brackets first.
    for side in (left, right):
        if side.count("(") != side.count(")") or side.count("{") != side.count("}"):
            return None
    try:
        _parse(left)
        _parse(right)
    except Exception:  # noqa: BLE001
        return None
    out = {"left": left, "right": right}
    if p.get("note"):
        out["note"] = _s(p["note"], 160)
    return out


def _table(p: dict[str, Any]) -> dict[str, Any] | None:
    headers = [_s(h, 30) for h in (p.get("headers") or [])[:6]]
    rows = p.get("rows") or []
    if not headers or not isinstance(rows, list) or not rows:
        return None
    clean = []
    for r in rows[:12]:
        if not isinstance(r, list) or len(r) != len(headers):
            return None
        clean.append([_s(c, 40) for c in r])
    out: dict[str, Any] = {"headers": headers, "rows": clean}
    hc = _num(p.get("highlight_col"))
    if hc is not None and hc.is_integer() and 0 <= hc < len(headers):
        out["highlight_col"] = int(hc)
    return out


def _callout(p: dict[str, Any]) -> dict[str, Any] | None:
    body = _s(p.get("body_md"), 600)
    if not body:
        return None
    tone = p.get("tone") if p.get("tone") in ("tip", "warning", "fact") else "tip"
    return {"tone": tone, "title": _s(p.get("title"), 80), "body_md": body}


def _shape(p: dict[str, Any]) -> dict[str, Any] | None:
    shape = p.get("shape")
    if shape not in ("triangle", "rectangle", "circle", "polygon"):
        return None
    labels = p.get("labels") if isinstance(p.get("labels"), dict) else {}
    out: dict[str, Any] = {
        "shape": shape,
        "labels": {_s(k, 12): _s(v, 20) for k, v in list(labels.items())[:8] if _s(v, 20)},
    }
    sides = 3 if shape == "triangle" else 4 if shape == "rectangle" else None
    if shape == "polygon":
        n = _num(p.get("sides"))
        if n is None or not n.is_integer() or not 3 <= n <= 10:
            return None
        sides = out["sides"] = int(n)
    angles = p.get("angles")
    if angles and shape in ("triangle", "polygon"):
        vals = [_num(a) for a in angles] if isinstance(angles, list) else [None]
        # Interior angles must add up to (n-2)·180 or the picture teaches wrong geometry.
        if None in vals or len(vals) != sides or abs(sum(vals) - (sides - 2) * 180) > 1:
            return None
        out["angles"] = [round(v, 1) for v in vals]
    return out


def _grid(p: dict[str, Any]) -> dict[str, Any] | None:
    rng = p.get("range") or [-5, 5]
    lo, hi = (_num(rng[0]), _num(rng[1])) if isinstance(rng, list) and len(rng) == 2 else (None, None)
    if lo is None or hi is None or not lo < hi or hi - lo > 40:
        return None
    pts = []
    for q in (p.get("points") or [])[:12]:
        x, y = (_num(q.get("x")), _num(q.get("y"))) if isinstance(q, dict) else (None, None)
        if x is None or y is None or not (lo <= x <= hi and lo <= y <= hi):
            return None
        pt: dict[str, Any] = {"x": x, "y": y}
        if q.get("label"):
            pt["label"] = _s(q["label"], 8)
        pts.append(pt)
    segs = [
        [int(s[0]), int(s[1])]
        for s in (p.get("segments") or [])[:12]
        if isinstance(s, list) and len(s) == 2
        and all(isinstance(i, int) and 0 <= i < len(pts) for i in s)
    ]
    if not pts:
        return None
    return {"range": [lo, hi], "points": pts, "segments": segs}


def _plotter(p: dict[str, Any]) -> dict[str, Any] | None:
    exprs = [_s(e, 200) for e in (p.get("expressions") or [])[:4] if _s(e, 200)]
    if not exprs:
        return None
    dom = p.get("domain") or [-10, 10]
    lo, hi = (_num(dom[0]), _num(dom[1])) if isinstance(dom, list) and len(dom) == 2 else (None, None)
    out: dict[str, Any] = {
        "expressions": exprs,
        "domain": [lo, hi] if lo is not None and hi is not None and lo < hi else [-10, 10],
    }
    if p.get("textAlt"):
        out["textAlt"] = _s(p["textAlt"], 400)
    return out


def _strs(v: Any, n: int, lo: int, hi: int) -> list[str] | None:
    """``lo..hi`` non-empty strings (≤ ``n`` chars), unique ignoring case; else None."""
    if not isinstance(v, list) or not lo <= len(v) <= hi:
        return None
    out = [_s(x, n) for x in v]
    return out if all(out) and len({s.casefold() for s in out}) == len(out) else None


def _comparison(p: dict[str, Any]) -> dict[str, Any] | None:
    out = {}
    for k in ("left", "right"):
        side = p.get(k) if isinstance(p.get(k), dict) else {}
        title, points = _s(side.get("title"), 60), _strs(side.get("points"), 160, 1, 6)
        if not title or not points:
            return None
        out[k] = {"title": title, "points": points}
    return out


def _process_steps(p: dict[str, Any]) -> dict[str, Any] | None:
    raw = p.get("steps")
    if not isinstance(raw, list) or not 2 <= len(raw) <= 8:
        return None
    steps = []
    for s in raw:
        title = _s(s.get("title"), 80) if isinstance(s, dict) else ""
        if not title:
            return None
        body = _s(s.get("body"), 300)
        steps.append({"title": title, **({"body": body} if body else {})})
    return {"steps": steps, **({"cyclic": True} if p.get("cyclic") is True else {})}


def _key_terms(p: dict[str, Any]) -> dict[str, Any] | None:
    raw = p.get("terms")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 8:
        return None
    terms = [{"term": _s(t.get("term"), 60), "def": _s(t.get("def"), 300)} for t in raw if isinstance(t, dict)]
    return {"terms": terms} if len(terms) == len(raw) and all(t["term"] and t["def"] for t in terms) else None


# Mermaid directives (%%{init}) could loosen securityLevel and `click` binds links/callbacks;
# SVG must not carry script, event handlers, foreignObject or javascript: URLs. DOMPurify runs
# client-side as well; this check keeps unsafe sources out of the database in the first place.
_UNSAFE_DIAGRAM = re.compile(
    r"<\s*script|<\s*foreignObject|<\s*iframe|\bon[a-z]+\s*=|javascript:|%%\{|^\s*click\s|\bhref\s*=",
    re.I | re.M,
)


def _diagram(p: dict[str, Any]) -> dict[str, Any] | None:
    kind, alt = p.get("kind"), _s(p.get("alt"), 300)
    source = str(p.get("source") or "").strip()
    if kind not in ("mermaid", "svg") or not alt or not source or len(source) > 2000:
        return None
    if _UNSAFE_DIAGRAM.search(source) or (kind == "svg" and not source.lstrip().startswith("<svg")):
        return None
    return {"kind": kind, "source": source, "alt": alt}


_BCP47 = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,3}$")
_DATE = re.compile(r"^(-?\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?$")
_BCE = re.compile(r"^(\d{1,4})\s*(?:BCE|BC|a\.?\s?C\.?)$", re.I)


def _year(v: Any) -> tuple[str, int] | None:
    """Year, ``YYYY-MM(-DD)``, negative year or ``490 BCE`` → (normalized date, year)."""
    if isinstance(v, int) and not isinstance(v, bool):
        v = str(v)
    s = _s(v, 20)
    if m := _BCE.match(s):
        s = f"-{m.group(1)}"
    m = _DATE.match(s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1)
    if y > 0:
        try:
            date(y, mo, d)
        except ValueError:
            return None
    elif not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return s, y


def _timeline(p: dict[str, Any]) -> dict[str, Any] | None:
    raw = p.get("events")
    if not isinstance(raw, list) or not 2 <= len(raw) <= 12:
        return None
    events = []
    for e in raw:
        parsed = _year(e.get("date", e.get("year"))) if isinstance(e, dict) else None
        label = _s(e.get("label"), 120) if isinstance(e, dict) else ""
        if not parsed or not label:
            return None
        detail = _s(e.get("detail"), 240)
        events.append({"date": parsed[0], "year": parsed[1], "label": label, **({"detail": detail} if detail else {})})
    events.sort(key=lambda e: (e["year"], e["date"]))
    return {"events": events, **({"title": _s(p["title"], 120)} if p.get("title") else {})}


def _map_pins(p: dict[str, Any]) -> dict[str, Any] | None:
    region, raw = p.get("region"), p.get("pins")
    if region not in MAP_REGIONS or not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        return None
    lo_x, hi_x, lo_y, hi_y = MAP_REGIONS[region]
    pins = []
    for q in raw:
        lat, lon = (_num(q.get("lat")), _num(q.get("lon"))) if isinstance(q, dict) else (None, None)
        label = _s(q.get("label"), 60) if isinstance(q, dict) else ""
        # A pin off the region's map means the model picked the wrong region (or swapped lat/lon).
        if lat is None or lon is None or not label or not (lo_y <= lat <= hi_y and lo_x <= lon <= hi_x):
            return None
        pins.append({"lat": lat, "lon": lon, "label": label})
    return {"region": region, "pins": pins, **({"caption": _s(p["caption"], 200)} if p.get("caption") else {})}


def _source_excerpt(p: dict[str, Any], urls: frozenset[str] | set[str] = frozenset()) -> dict[str, Any] | None:
    quote = str(p.get("quote") or "").strip()
    if not quote or len(quote) > 600:
        return None
    out: dict[str, Any] = {"quote": quote}
    for k, n in (("author", 120), ("source", 160)):
        if v := _s(p.get(k), n):
            out[k] = v
    y = _num(p.get("year"))
    if y is not None and y.is_integer():
        out["year"] = int(y)
    # Only URLs the research step actually returned are citable (Doc 10 §4.2, R4); ``urls`` are
    # ``norm_url`` keys, so the emitted link is the cited one, not the model's spelling of it.
    url = norm_url(p.get("url"))
    if url in urls and url.startswith(("https://", "http://")):
        out["url"] = url
    return out


def _cause_effect(p: dict[str, Any]) -> dict[str, Any] | None:
    raw = p.get("links")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 6:
        return None
    links = [{"cause": _s(x.get("cause"), 200), "effect": _s(x.get("effect"), 200)} for x in raw if isinstance(x, dict)]
    if len(links) != len(raw) or not all(x["cause"] and x["effect"] for x in links):
        return None
    return {"links": links, **({"title": _s(p["title"], 120)} if p.get("title") else {})}


def _audio_clip(p: dict[str, Any]) -> dict[str, Any] | None:
    text, lang = _s(p.get("text"), 200), _s(p.get("lang"), 35)
    if not text or not _BCP47.match(lang):
        return None
    out: dict[str, Any] = {"text": text, "lang": lang}
    rate = _num(p.get("rate"))
    if rate is not None:
        out["rate"] = min(1.5, max(0.5, rate))
    if label := _s(p.get("label"), 120):
        out["label"] = label
    return out


# KaTeX runs with trust:false, but keep link/macro commands out of stored content anyway.
_UNSAFE_TEX = re.compile(r"\\(?:href|url|html\w*|includegraphics|def|gdef|edef|newcommand|renewcommand|let|input|include)\b")


def _chem_formula(p: dict[str, Any]) -> dict[str, Any] | None:
    latex = str(p.get("latex") or "").strip()
    # ponytail: mhchem itself is not parsed server-side; a client render failure shows the text.
    # Upgrade: run KaTeX+mhchem in a node sidecar at write time.
    if not latex or len(latex) > 300 or not re.search(r"\\(?:ce|pu)\{", latex):
        return None
    if latex.count("{") != latex.count("}") or _UNSAFE_TEX.search(latex):
        return None
    return {"latex": latex, **({"caption": _s(p["caption"], 200)} if p.get("caption") else {})}


_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,7}$")
_FUNCS = frozenset({"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "sqrt", "abs", "Abs", "exp", "log", "ln"})
_CONSTS = frozenset({"pi", "E", "e"})


def expr_ok(expr: str, names: set[str]) -> bool:
    """Same grammar as frontend/lib/safeExpr.ts: numbers, ``names``, pi/e, + - * / ^ **, 1-arg
    functions. Checked on Python's AST (parsed, never evaluated); implicit products are syntax errors.
    """
    try:
        tree = ast.parse(expr.replace("^", "**"), mode="eval")
    except (SyntaxError, ValueError):
        return False
    ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in _FUNCS and len(node.args) == 1 and not node.keywords):
                return False
        elif isinstance(node, ast.Name):
            if node.id not in names | _CONSTS | _FUNCS:
                return False
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                return False
        elif not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Load, *ops)):
            return False
    return True


def _param_explorer(p: dict[str, Any]) -> dict[str, Any] | None:
    expr, x, alt = _s(p.get("expr"), 160), _s(p.get("x") or "x", 8), _s(p.get("textAlt"), 400)
    raw = p.get("params")
    if not expr or not alt or not _NAME.match(x) or not isinstance(raw, list) or not 1 <= len(raw) <= 3:
        return None
    params = []
    for q in raw:
        name = _s(q.get("name"), 8) if isinstance(q, dict) else ""
        lo, hi = (_num(q.get("min")), _num(q.get("max"))) if isinstance(q, dict) else (None, None)
        if not _NAME.match(name) or name in _FUNCS | _CONSTS | {x} or lo is None or hi is None or not lo < hi:
            return None
        v = _num(q.get("value"))
        params.append({"name": name, "min": lo, "max": hi, "value": v if v is not None and lo <= v <= hi else (lo + hi) / 2})
    names = {q["name"] for q in params}
    if len(names) != len(params) or x in _FUNCS | _CONSTS or not expr_ok(expr, names | {x}):
        return None
    dom = p.get("domain") or [-10, 10]
    lo, hi = (_num(dom[0]), _num(dom[1])) if isinstance(dom, list) and len(dom) == 2 else (None, None)
    if lo is None or hi is None or not lo < hi:
        return None
    return {"expr": expr, "x": x, "domain": [lo, hi], "params": params, "textAlt": alt}


def _labeled_diagram(p: dict[str, Any]) -> dict[str, Any] | None:
    alt, raw = _s(p.get("alt"), 300), p.get("labels")
    source = str(p.get("source") or "").strip()
    if not alt or not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        return None
    if source and (len(source) > 3000 or _UNSAFE_DIAGRAM.search(source) or not source.startswith("<svg")):
        return None
    labels = []
    for q in raw:
        xy = (_num(q.get("x")), _num(q.get("y"))) if isinstance(q, dict) else (None, None)
        text = _s(q.get("text"), 60) if isinstance(q, dict) else ""
        if None in xy or not text or not all(0 <= c <= 1 for c in xy):  # type: ignore[operator]
            return None
        labels.append({"x": xy[0], "y": xy[1], "text": text})
    return {"labels": labels, "alt": alt, **({"source": source} if source else {})}


def _code(p: dict[str, Any], key: str = "code") -> tuple[str, str] | None:
    """(language, code) with ≤ 60 lines / 3000 chars, else None."""
    lang, code = p.get("language"), str(p.get(key) or "").rstrip()
    if lang not in ("python", "javascript") or len(code) > 3000 or code.count("\n") >= 60:
        return None
    return lang, code


def _code_block(p: dict[str, Any]) -> dict[str, Any] | None:
    lc = _code(p)
    if not lc or not lc[1].strip():
        return None
    return {"language": lc[0], "code": lc[1], **({"caption": _s(p["caption"], 200)} if p.get("caption") else {})}


_SANITIZERS = {
    "FractionBars": _fraction_bars,
    "BalanceScale": _balance,
    "DataTable": _table,
    "ValueTable": _table,
    "Callout": _callout,
    "ShapeDiagram": _shape,
    "CoordinateGrid": _grid,
    "FunctionPlotter": _plotter,
    "Comparison": _comparison,
    "ProcessSteps": _process_steps,
    "KeyTerms": _key_terms,
    "Diagram": _diagram,
    "Timeline": _timeline,
    "MapPins": _map_pins,
    "SourceExcerpt": _source_excerpt,
    "CauseEffect": _cause_effect,
    "AudioClip": _audio_clip,
    "ChemFormula": _chem_formula,
    "ParameterExplorer": _param_explorer,
    "LabeledDiagram": _labeled_diagram,
    "CodeBlock": _code_block,
}


# ---------------------------------------------------------------------------
# Answer parts: generator output {component, props, answer_spec} → (public props, answer_spec).
# Each sanitizer gets props and answer_spec merged (the generator may put keys in either) and
# returns ``(props, spec)`` or an error string the item repair prompt quotes back.
# ---------------------------------------------------------------------------

_BLANK = re.compile(r"\[\[(.+?)\]\]")


def hide_blanks(v: Any) -> Any:
    """``[[answer]]`` → ``____`` in every string of ``v``. Only for cloze-graded items: code
    props legitimately contain ``[[1, 2]]``."""
    if isinstance(v, str):
        return _BLANK.sub("____", v)
    if isinstance(v, list):
        return [hide_blanks(x) for x in v]
    if isinstance(v, dict):
        return {k: hide_blanks(x) for k, x in v.items()}
    return v


def _shuffled(n: int, seed: str) -> list[int]:
    """Deterministic permutation that never leaves the canonical order in place."""
    order = sorted(range(n), key=lambda k: hashlib.md5(f"{seed}:{k}".encode()).hexdigest())
    return order[1:] + order[:1] if order == list(range(n)) else order


def _blanks(text: str, aliases: Any, offset: int = 0) -> tuple[list[str], list[list[str]]]:
    """``"a [[x]] b"`` → segments ``["a ", " b"]`` + answers ``[["x", *aliases]]``."""
    al = aliases if isinstance(aliases, dict) else {}
    answers = []
    for i, m in enumerate(_BLANK.finditer(text)):
        extra = al.get(str(offset + i)) or al.get(offset + i) or []
        answers.append([_s(m.group(1), 80)] + [_s(a, 80) for a in extra[:9] if _s(a, 80)])
    return [seg[:300] for seg in _BLANK.split(text)[::2]], answers


def _quick_check(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    raw = p.get("choices") if isinstance(p.get("choices"), list) else []
    ids = _strs([c.get("id") for c in raw if isinstance(c, dict)], 40, 2, 6)
    labels = _strs([c.get("label") for c in raw if isinstance(c, dict)], 200, 2, 6)
    if not ids or not labels or len(ids) != len(raw) or len(labels) != len(raw):
        return "QuickCheck needs 2-6 choices with unique ids and unique labels"
    keys = p.get("correctIds") or []
    correct = [str(c) for c in keys if str(c) in ids] if isinstance(keys, list) else []
    if not correct or len(correct) != len(keys):
        return "answer_spec.correctIds must be ids of the given choices"
    props: dict[str, Any] = {
        "prompt": _s(p.get("prompt"), 400) or "Choose the best answer",
        "choices": [{"id": i, "label": lab} for i, lab in zip(ids, labels)],
    }
    if len(correct) > 1:
        props["multi"] = True
    spec = {"correctIds": correct, **({"explanation": _s(p["explanation"], 400)} if p.get("explanation") else {})}
    return props, spec


def _match_pairs(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    lefts, rights = _strs(p.get("lefts"), 200, 2, 6), _strs(p.get("rights"), 200, 2, 6)
    pairs = p.get("pairs") if isinstance(p.get("pairs"), list) else []
    err = "MatchPairs needs 2-6 unique lefts, as many unique rights, and pairs mapping every left to one right"
    try:
        mapping = {int(lr[0]): int(lr[1]) for lr in pairs}
    except (TypeError, ValueError, IndexError, KeyError):
        return err
    n = len(lefts or [])
    if not lefts or not rights or len(rights) != n or len(pairs) != n or sorted(mapping) != list(range(n)) \
            or sorted(mapping.values()) != list(range(n)):
        return err
    # The model often lists rights in left order; reshuffle so the layout never gives it away.
    order = _shuffled(n, seed)
    pos = {k: i for i, k in enumerate(order)}
    props = {"prompt": _s(p.get("prompt"), 240) or "Match each item", "lefts": lefts, "rights": [rights[k] for k in order]}
    return props, {"pairs": [[li, pos[ri]] for li, ri in sorted(mapping.items())]}


def _rubric(v: Any) -> list[dict[str, Any]] | None:
    if not isinstance(v, list) or not 1 <= len(v) <= 5:
        return None
    out = []
    for c in v:
        crit = _s(c.get("criterion"), 200) if isinstance(c, dict) else ""
        pts = _num(c.get("points", 1)) if isinstance(c, dict) else None
        if not crit or pts is None or not 0 < pts <= 5:
            return None
        out.append({"criterion": crit, "points": pts})
    return out


def _short_answer(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    question = _s(p.get("question") or p.get("prompt"), 400)
    accepted = _strs(p.get("accepted"), 120, 1, 10)
    if not question or not accepted:
        return "ShortAnswer needs a question and 1-10 unique accepted answers"
    spec: dict[str, Any] = {"accepted": accepted}
    if p.get("strip_accents"):
        spec["strip_accents"] = True
    if rubric := _rubric(p.get("rubric")):  # rubric_llm fallback for answers exact misses
        spec.update(rubric=rubric, question=question, min_words=1)
    return {"question": question}, spec


def _free_response(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    question = _s(p.get("question") or p.get("prompt"), 600)
    rubric, exemplar = _rubric(p.get("rubric")), _s(p.get("exemplar"), 1500)
    terms = _strs(p.get("key_terms"), 60, 1, 8)
    mw = _num(p.get("max_words")) or 120
    if not question or not rubric or not exemplar or not terms:
        return "FreeResponse needs question, rubric (1-5 criteria with points), exemplar and 1-8 key_terms"
    max_words = int(min(300, max(10, mw)))
    spec = {"rubric": rubric, "exemplar": exemplar, "key_terms": terms, "question": question}
    return {"question": question, "max_words": max_words}, spec


def _cloze(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    segments, answers = _blanks(str(p.get("text") or "")[:1200], p.get("aliases"))
    if not 1 <= len(answers) <= 4 or not all(a[0] for a in answers):
        return "Cloze text needs 1-4 [[answer]] blanks"
    props = {"segments": segments, **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}
    return props, {"answers": answers}


def _worked_example(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    raw = p.get("steps")
    if not isinstance(raw, list) or not 2 <= len(raw) <= 8:
        return "WorkedExample needs 2-8 steps"
    steps, answers = [], []
    for s in raw:
        text = str((s.get("text") if isinstance(s, dict) else s) or "")[:600]
        segs, ans = _blanks(text, p.get("aliases"), len(answers))
        if not text.strip() or len(ans) > 2:
            return "each WorkedExample step needs text with at most 2 [[blanks]]"
        steps.append({"segments": segs})
        answers += ans
    if not 1 <= len(answers) <= 4 or not all(a[0] for a in answers):
        return "WorkedExample needs 1-4 [[answer]] blanks in total"
    props = {"steps": steps, **({"title": _s(p["title"], 120)} if p.get("title") else {})}
    return props, {"answers": answers}


def _order_steps(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    items = _strs(p.get("items"), 160, 3, 7)
    if not items:
        return "OrderSteps needs 3-7 unique items in the correct order"
    shown = _shuffled(len(items), seed)  # shown[i] = canonical index displayed at i
    props = {"items": [items[k] for k in shown], **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}
    return props, {"order": [shown.index(k) for k in range(len(items))]}


def _categorize(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    buckets = _strs(p.get("buckets"), 60, 2, 4)
    raw = p.get("items") if isinstance(p.get("items"), list) else []
    labels = _strs([i.get("label") for i in raw if isinstance(i, dict)], 120, 4, 10)
    err = "Categorize needs 2-4 unique buckets and 4-10 unique items, each with a valid bucket index"
    if not buckets or not labels or len(labels) != len(raw):
        return err
    assign = [i.get("bucket") for i in raw]
    if not all(type(b) is int and 0 <= b < len(buckets) for b in assign) or len(set(assign)) < 2:
        return err
    props = {"buckets": buckets, "items": labels, **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}
    return props, {"assign": assign}


def _flashcards(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    raw = p.get("cards") if isinstance(p.get("cards"), list) else []
    cards = [{"front": _s(c.get("front"), 160), "back": _s(c.get("back"), 160)} for c in raw if isinstance(c, dict)]
    if not 3 <= len(cards) <= 12 or len(cards) != len(raw) or not all(c["front"] and c["back"] for c in cards):
        return "Flashcards needs 3-12 cards with front and back"
    # ponytail: self-study cards show their back on flip, so backs are public props and the
    # score is the learner's self-rating (decided_by CLIENT). Upgrade: typed answers graded `exact`.
    return {"cards": cards}, {"count": len(cards)}


def _pronunciation(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    phrase, lang = _s(p.get("phrase"), 160), _s(p.get("lang"), 35)
    if not phrase or not _BCP47.match(lang):
        return "Pronunciation needs a phrase and a BCP-47 lang like es-ES"
    props = {"phrase": phrase, "lang": lang, **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}
    return props, {"phrase": phrase}  # the phrase is shown on purpose: the learner reads it aloud


def _translation(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    source, lang = _s(p.get("source"), 300), _s(p.get("lang"), 35)
    accepted = _strs(p.get("accepted"), 200, 1, 10)
    if not source or not _BCP47.match(lang) or not accepted:
        return "TranslationAnswer needs source, a BCP-47 lang and 1-10 unique accepted translations"
    # `exact` first; a miss falls back to rubric_llm (grade()) so valid paraphrases still pass.
    spec = {
        "accepted": accepted,
        "question": f"Translate into {lang}: {source}",
        "exemplar": accepted[0],
        "rubric": [
            {"criterion": f"means the same as: {accepted[0]}", "points": 2},
            {"criterion": f"grammatical {lang} with correct spelling and accents", "points": 1},
        ],
        "min_words": 1,
    }
    return {"source": source, "lang": lang, **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}, spec


def _quantity(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    question, unit, value = _s(p.get("question") or p.get("prompt"), 400), _s(p.get("unit"), 12), _num(p.get("value"))
    if not question or value is None or unit not in UNITS:
        return f"QuantityAnswer needs question, a finite value and unit one of {list(UNITS)}"
    tol = _num(p.get("tolerance"))
    base = UNITS[unit][0]
    props = {"question": question, "unit": unit, "units": [u for u, (b, _) in UNITS.items() if b == base][:12]}
    return props, {"value": value, "unit": unit, "tolerance": min(0.2, max(0.0, tol if tol is not None else 0.02))}


def _predict_output(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    lc, accepted = _code(p), _strs(p.get("accepted"), 200, 1, 5)
    if not lc or not lc[1].strip() or not accepted:
        return "PredictOutput needs language python|javascript, code (<= 60 lines) and 1-5 accepted outputs"
    # ponytail: `exact` ignores punctuation, so "[1, 2]" == "1 2"; fine for print-the-value drills.
    # Upgrade: a `raw` flag in exact.normalize when items need bracket-precise output.
    props = {"language": lc[0], "code": lc[1], **({"prompt": _s(p["prompt"], 240)} if p.get("prompt") else {})}
    return props, {"accepted": accepted, "case": True}


_STUB_RESULTS = {"None", "null", "undefined", "''", '""', "[]", "{}"}


def _code_exercise(p: dict[str, Any], seed: str) -> tuple[dict[str, Any], dict[str, Any]] | str:
    lc, sol = _code(p, "starter"), _code(p, "solution")
    raw = p.get("tests")
    err = ("CodeExercise needs language, starter, a reference solution different from the starter and "
           "1-8 tests {call, expect} or {call, stdout}")
    if not lc or not sol or not sol[1].strip() or sol[1].strip() == lc[1].strip():
        return err
    if not isinstance(raw, list) or not 1 <= len(raw) <= 8:
        return err
    tests = [
        {k: v for k, v in (("call", _s(t.get("call"), 200)), ("expect", _s(t.get("expect"), 200)),
                           ("stdout", _s(t.get("stdout"), 500))) if v}
        for t in raw if isinstance(t, dict)
    ]
    if len(tests) != len(raw) or not all(t.get("call") and ("expect" in t or "stdout" in t) for t in tests):
        return err
    # An empty stub returns None and prints nothing; tests it passes can't tell a solution from no work.
    # ponytail: only catches stub-shaped keys; a starter returning e.g. 0 needs a server sandbox run.
    if all("stdout" not in t and t["expect"] in _STUB_RESULTS for t in tests):
        return ("CodeExercise tests only expect None/empty, so an empty stub passes: assert return values, "
                "or {call, stdout} for the exact printed text")
    # The server never runs AI code: the reference solution is checked by the first passing
    # browser run (api_session clears `beta`); until then the session shows a beta chip.
    props = {
        "language": lc[0], "starter": lc[1], "tests": tests, "beta": True,
        **({"prompt": _s(p["prompt"], 400)} if p.get("prompt") else {}),
    }
    return props, {"total": len(tests), "solution": sol[1], "beta": True}


_ANSWER_SANITIZERS = {
    "Pronunciation": _pronunciation,
    "TranslationAnswer": _translation,
    "QuantityAnswer": _quantity,
    "PredictOutput": _predict_output,
    "CodeExercise": _code_exercise,
    "QuickCheck": _quick_check,
    "MatchPairs": _match_pairs,
    "ShortAnswer": _short_answer,
    "FreeResponse": _free_response,
    "Cloze": _cloze,
    "WorkedExample": _worked_example,
    "OrderSteps": _order_steps,
    "Categorize": _categorize,
    "Flashcards": _flashcards,
}


def sanitize_part(raw: Any, seed: str = "") -> dict[str, Any] | str:
    """Generator part → stored ``{component, grader, props, answer_spec}``, or an error string."""
    if not isinstance(raw, dict):
        return "part must be an object"
    name = str(raw.get("component") or "")
    fn = _ANSWER_SANITIZERS.get(name)
    if fn is None:
        return f"unknown answer component {name[:40]!r}"
    props = raw.get("props") if isinstance(raw.get("props"), dict) else {}
    spec = raw.get("answer_spec") if isinstance(raw.get("answer_spec"), dict) else {}
    out = fn({**props, **spec}, seed)
    if isinstance(out, str):
        return out
    return {"component": name, "grader": COMPONENTS[name]["grader"], "props": out[0], "answer_spec": out[1]}


def sanitize_visual(raw: Any, urls: frozenset[str] | set[str] = frozenset()) -> dict[str, Any] | None:
    """``{"type", "props"}`` with bounded, checked props, or None (beat renders as text).

    ``urls``: the node's research source URLs, the only ones a SourceExcerpt may link.
    """
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("type") or "").strip()
    props = raw.get("props") if isinstance(raw.get("props"), dict) else None
    fn = _SANITIZERS.get(name)
    if not fn or props is None:
        return None
    clean = _source_excerpt(props, urls) if name == "SourceExcerpt" else fn(props)
    return {"type": name, "props": clean} if clean else None
