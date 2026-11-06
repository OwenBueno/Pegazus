"""System 2 item draft + SymPy verification — AI-only, topic-true to the skill.

One batched LLM call per problem spec, SymPy verification with reason codes, one
targeted repair call for fixable rejects, then a single top-up for empty slots.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import httpx

from app.config import settings
from app.services.component_catalog import COMPONENTS, hide_blanks, sanitize_part, sanitize_visual
from app.services.llm import chat_json
from app.services.subject_profile import is_math, profile_prompt
from app.workers.math_evaluator import evaluate_step_safe

_SLUG_SAFE = re.compile(r"[^a-z0-9.]+")
_log = logging.getLogger(__name__)
# Process-wide reject/dupe counts by reason, read by scripts/eval_lessons.py.
REJECTS: Counter[str] = Counter()
_rejects_lock = threading.Lock()

_ITEM_SHAPE = (
    '{"prompt":"short English instruction (REQUIRED for word/place/order problems)",'
    '"statement_latex":"...",'
    '"steps":[{"latex":"...","sympy":"...","operation":"GIVEN",'
    '"justification":"short reason","gap_latex":"optional partial"}],'
    '"distractors":["optional wrong final answers"],'
    '"pairs":[{"left":"...","right":"..."}],'
    '"visual":{"type":"...","props":{}}}'
)

# Static on purpose: identical system + context prefix across calls lets the provider cache it.
_SYSTEM_PROMPT = (
    'Return ONLY JSON: {"items":[ITEM, ...]} where ITEM is '
    + _ITEM_SHAPE
    + ". Write the requested number of practice items for the given skill/title.\n"
    "Rules:\n"
    "- Every item must be a DIFFERENT problem: vary the numbers AND the structure.\n"
    "- Match the SUBJECT of the skill (multiplication, fractions, arithmetic, "
    "geometry, algebra, place value, order of operations, etc.). Do NOT default to "
    "linear equations unless the skill is equations.\n"
    "- prompt: ALWAYS prefer a clear human instruction (1–2 sentences). "
    "Required for word problems, place value, order of operations, and 'which…' questions.\n"
    "- statement_latex: PURE KaTeX math only (e.g. 3,542 or -3+2\\cdot(-4)^{2}). "
    "NO prose, NO English sentences, NO \\( \\) or $ delimiters.\n"
    "- At least 2 steps. Step 0 (GIVEN): the statement or first form. Middle steps: REWRITTEN "
    "expressions (ASCII sympy like -3+2*16 or 3/12+8/12), NOT Eq(y, final). "
    "Final step ONLY may be Eq(y, N) or bare N.\n"
    "- Each step's latex and sympy must be the SAME math (\\frac{3}{4} <-> 3/4).\n"
    "- Never put the same Eq(y, N) on every step. Max 4 steps.\n"
    "- justification: short phrase per step (e.g. exponents, multiply) for faded UI.\n"
    "- gap_latex (optional): partial KaTeX for the blank, e.g. -3+2\\cdot\\square.\n"
    "- Algebra may use Eq(x, ...) on equation steps.\n"
    "- If a problem spec is given, follow its facet, difficulty (0 easy – 1 hard) and "
    "target misconception.\n"
    "- spec.widget QuickCheck: include 2-3 distractors = plausible WRONG final answers "
    "(KaTeX) produced by the target misconception.\n"
    "- spec.widget MatchPairs: include 3-4 pairs of equivalent forms on the same idea.\n"
    "- Otherwise omit distractors and pairs.\n"
    "- spec.visual set: include visual {type: spec.visual, props} drawn from THIS item's "
    "numbers (never its answer). Otherwise omit visual."
)

_REASON_TEXT = {
    "step_latex": "this step's latex and sympy are not the same math",
    "chain": "this step's value differs from the statement (arithmetic slip)",
    "final": "the final answer's latex and sympy disagree",
    "eq_intermediate": "middle steps must be rewritten expressions, not Eq(y, N)",
    "component": "use only the allowed answer components",
    "part": "the answer part is invalid",
    "exemplar": "the FreeResponse exemplar must fully meet its own rubric; fix the exemplar or rubric",
}

# Generic answer components (shipped in the frontend) → the profile answer_mode that allows them.
GENERIC_COMPONENTS = {
    "QuickCheck": "choice",
    "MatchPairs": "match",
    "OrderSteps": "order",
    "Categorize": "categorize",
    "Cloze": "cloze",
    "WorkedExample": "cloze",
    "ShortAnswer": "short_text",
    "Flashcards": "short_text",
    "FreeResponse": "free_text",
    "TranslationAnswer": "short_text",
    "Pronunciation": "speech",
    "QuantityAnswer": "numeric",
    "PredictOutput": "code",
    "CodeExercise": "code",
}

# Family-pack key formats the generator must follow (core rules are inline in _generic_system).
_PACK_RULES = {
    "TranslationAnswer": "- TranslationAnswer: source in the instruction language; lang = target language; "
    "accepted = every natural correct translation, with correct accents.\n",
    "Pronunciation": "- Pronunciation: phrase in the target language (one short sentence); lang = BCP-47 with region (es-ES).\n",
    "QuantityAnswer": "- QuantityAnswer: value = the correct numeric answer in `unit`; recompute it carefully.\n",
    "PredictOutput": "- PredictOutput: accepted = the exact printed output (no quotes), deterministic code only.\n",
    "CodeExercise": "- CodeExercise: starter defines the function signature with a stub body; tests call it; "
    "expect = Python repr() / JavaScript JSON.stringify() of the return value (e.g. \"5\", \"'ab'\", \"[1, 2]\"); "
    "for code that prints, use {call, stdout} with the exact printed lines instead of expecting None; "
    "an empty stub must fail the tests; "
    "solution = a complete reference solution that passes every test. No input(), files, network or randomness.\n",
}

_GENERIC_SHAPE = (
    '{"prompt_md":"the question in plain Markdown",'
    '"parts":[{"component":"QuickCheck","props":{"choices":[{"id":"a","label":"..."}]},'
    '"answer_spec":{"correctIds":["a"]}}],'
    '"explanation_md":"1-2 sentences: why the answer is right"}'
)


def allowed_components(profile: dict[str, Any] | None) -> list[str]:
    """Generic answer components the profile's ``answer_modes`` and categories allow (choice/match when none)."""
    modes = set((profile or {}).get("answer_modes") or []) or {"choice", "match"}
    cats = {"core", *((profile or {}).get("categories") or [])}
    return [
        c for c, m in GENERIC_COMPONENTS.items() if m in modes and COMPONENTS[c]["category"] in cats
    ] or ["QuickCheck", "MatchPairs"]


def _generic_system(profile: dict[str, Any], allowed: list[str]) -> str:
    others = "".join(
        f"- {c}: {COMPONENTS[c]['when']}. props (keys included; the server hides them): {COMPONENTS[c]['props']}\n"
        for c in allowed
        if c not in ("QuickCheck", "MatchPairs")
    )
    family = [c for c in allowed if COMPONENTS[c]["category"] != "core"]
    return (
        'Return ONLY JSON: {"items":[ITEM, ...]} where ITEM is '
        + _GENERIC_SHAPE
        + ". Write the requested number of practice items for the given skill.\n"
        + profile_prompt(profile)
        + "\nRules:\n"
        "- Every item asks something DIFFERENT about the skill; vary content and structure.\n"
        "- prompt_md: the whole question as plain Markdown. Never reveal the answer in it.\n"
        f"- Exactly one part. component ∈ {allowed}. Spread items across components: at most "
        "half may use the same component; prefer recall/explanation formats over QuickCheck.\n"
        '- QuickCheck: props.choices = 3-4 [{"id","label"}] with short distinct labels; '
        "answer_spec.correctIds = id(s) of the correct choice(s). Wrong choices come from the "
        "target misconception.\n"
        '- MatchPairs: props {"lefts":[...],"rights":[...]} with 3-5 entries each; '
        'answer_spec {"pairs":[[left_index,right_index],...]} one per left.\n'
        + others
        + "- Cloze/WorkedExample blanks: [[answer]] inline in props.text / steps only; prompt_md is just the "
        "instruction and never repeats that text. aliases (blank index → other accepted "
        "spellings) only when needed. ShortAnswer accepted: every reasonable correct spelling.\n"
        "- FreeResponse: the exemplar must meet every rubric criterion; key_terms appear in it.\n"
        + "".join(_PACK_RULES.get(c, "") for c in allowed)
        + "- If a problem spec is given, follow its facet, difficulty (0 easy - 1 hard) and target "
        "misconception, and use spec.widget as the component when it is allowed.\n"
        + (f"- About a third of the items (at least one) must use this subject's dedicated formats {family}, "
           "even where spec.widget names a core component.\n" if family else "")
        + "- Facts must be accurate; omit anything you are unsure about."
    )


def slugify_module(title: str, prefix: str = "math.generated") -> str:
    base = title.lower().strip()
    base = _SLUG_SAFE.sub("-", base).strip("-")[:48] or "module"
    return f"{prefix}.{base}"


def subject_slug(subject: str) -> str:
    return _SLUG_SAFE.sub("-", subject.lower()).strip("-.")[:32] or "subject"


def _is_eq_sympy(s: str) -> bool:
    return s.strip().startswith("Eq(")


def _norm_math(s: Any) -> str:
    """Zero-token fixes for formatting slips the parser would otherwise reject."""
    s = str(s or "").strip()
    s = re.sub(r"^(\$+|\\\(|\\\[)|(\$+|\\\)|\\\])$", "", s).strip()
    s = s.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    s = re.sub(r"\\left|\\right", "", s)
    s = s.replace("\\times", "\\cdot").replace("\u2212", "-").replace("\u00f7", "/")
    return s.rstrip(".").strip()


# ponytail: a digit right before a numeric \frac is read as a mixed number (2\frac{1}{3} = 7/3),
# matching school notation; a literal product 2·(1/3) must be written with \cdot.
_MIXED = re.compile(r"(?<![\d.}])(\d+)\s*\\frac\{(\d+)\}\{(\d+)\}")


def _equiv(a: str, b: str) -> bool:
    a, b = (_MIXED.sub(r"(\1+\\frac{\2}{\3})", s) for s in (a, b))
    return bool(evaluate_step_safe(a, b, use_pool=False).get("is_equivalent"))


def _render(sympy_s: str) -> str | None:
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr

        return sp.latex(
            parse_expr(
                sympy_s,
                local_dict={"x": sp.Symbol("x"), "y": sp.Symbol("y"), "Eq": sp.Eq},
                evaluate=False,
            )
        )
    except Exception:  # noqa: BLE001
        return None


def verify_item(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Verify a drafted item with SymPy. Returns ``(item, "")`` or ``(None, reason)``.

    Reasons: ``shape``, ``eq_intermediate:i``, ``chain:i``, ``step_latex:i``, ``final``.
    """
    statement = _norm_math(data.get("statement_latex"))
    prompt = str(data.get("prompt") or "").strip()[:500]
    steps = data.get("steps")
    if not statement or not isinstance(steps, list) or len(steps) < 2:
        # One step means the "answer" is the statement itself — nothing to practice.
        return None, "shape"
    cleaned: list[dict[str, str]] = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            return None, "shape"
        latex = _norm_math(s.get("latex"))
        sympy_s = _norm_math(s.get("sympy") or latex)
        if not latex or not sympy_s:
            return None, "shape"
        row: dict[str, str] = {
            "latex": latex,
            "sympy": sympy_s,
            "operation": str(s.get("operation") or ("GIVEN" if i == 0 else "STEP")),
        }
        just = str(s.get("justification") or "").strip()[:120]
        if just:
            row["justification"] = just
        gap = str(s.get("gap_latex") or "").strip()[:200]
        if gap:
            row["gap_latex"] = gap
        cleaned.append(row)

    sympy_vals = [c["sympy"] for c in cleaned]
    if len(set(sympy_vals)) == 1 and _is_eq_sympy(sympy_vals[0]):
        return None, "eq_intermediate:0"
    last = len(cleaned) - 1
    for i, row in enumerate(cleaned[:-1]):
        # Arithmetic/order-of-ops intermediates must be expressions, not Eq(y,N)
        if "Eq(y," in row["sympy"].replace(" ", "") and row["operation"].upper() != "GIVEN":
            return None, f"eq_intermediate:{i}"

    given = cleaned[0]["sympy"]
    for i, row in enumerate(cleaned):
        chained = False
        if 0 < i < last and row["operation"].upper() != "GIVEN":
            chained = _equiv(row["sympy"], statement) or _equiv(row["sympy"], given)
            # Eq intermediates (algebra) are not required to match the statement's value.
            if not chained and not _is_eq_sympy(row["sympy"]):
                return None, f"chain:{i}"
        if _equiv(row["latex"], row["sympy"]):
            continue
        if i == last:
            # Nothing ties the final sympy to the statement, so we can't tell which side is right.
            return None, "final"
        rendered = _render(row["sympy"]) if chained else None
        if not rendered:
            return None, f"step_latex:{i}"
        # ponytail: SymPy is the source of truth for a chained middle step; rendering may
        # reorder terms (8/12 + 3/12). Upgrade: ask the model to repair instead.
        row["latex"] = rendered
        row.pop("gap_latex", None)

    final = cleaned[-1]
    out: dict[str, Any] = {"statement_latex": statement, "steps": cleaned}
    if prompt:
        out["prompt"] = prompt

    distractors: list[str] = []
    for d in data.get("distractors") or []:
        d_s = str(d).strip()[:120]
        if not d_s or d_s == final["latex"] or d_s in distractors:
            continue
        # A "wrong" answer that SymPy says is right would make the QuickCheck unfair.
        if _equiv(d_s, final["sympy"]):
            continue
        distractors.append(d_s)
    if distractors:
        out["distractors"] = distractors[:3]
    pairs = [
        {"left": str(p["left"])[:200], "right": str(p["right"])[:200]}
        for p in (data.get("pairs") or [])
        if isinstance(p, dict) and p.get("left") and p.get("right")
    ][:4]
    if len(pairs) >= 2:
        out["pairs"] = pairs
    # ponytail: bounds-checked only; beyond FractionBars labels / BalanceScale parsing nothing
    # proves the picture matches the item's numbers (the critic reviews it after ready).
    visual = sanitize_visual(data.get("visual"))
    if visual and "problem" in COMPONENTS[visual["type"]]["where"]:
        out["visual"] = visual
    return out, ""


def verify_item_payload(data: dict[str, Any]) -> dict[str, Any] | None:
    return verify_item(data)[0]


def verify_generic_item(
    data: dict[str, Any], allowed: list[str], api_key: str | None = None
) -> tuple[dict[str, Any] | None, str]:
    """Per-grader check of a §6.2 item (Doc 10 §7.1). ``(item, "")`` or ``(None, reason)``.

    Structure comes from the catalog's part sanitizer (answer ⊂ options, unique labels, every
    blank answered); a FreeResponse exemplar must score ≥ 0.8 on its own rubric (needs ``api_key``).
    ponytail: whether a deterministic key is factually right is left to the lesson critic.
    """
    from app.graders.rubric_llm import grade_rubric_llm

    prompt = str(data.get("prompt_md") or data.get("prompt") or "").strip()[:1000]
    parts = data.get("parts")
    if not prompt or not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
        return None, "shape"
    p = parts[0]
    if str(p.get("component") or "") not in allowed:
        return None, "component"
    props = p.get("props") if isinstance(p.get("props"), dict) else {}
    if COMPONENTS[p["component"]]["grader"] == "cloze":  # models often repeat the [[answer]] text here
        prompt = hide_blanks(prompt)
    if p["component"] == "PredictOutput":  # the widget renders the code; a fenced copy would show twice
        prompt = re.sub(r"```[^\n]*\n[\s\S]*?```", "", prompt).strip() or prompt
    # The item prompt doubles as the widget's question unless the part brings its own.
    raw_part = {**p, "props": {"prompt": prompt, "question": prompt, **props}}
    part = sanitize_part(raw_part, hashlib.md5(prompt.encode()).hexdigest())
    if isinstance(part, str):
        return None, f"part:{part}"
    if part["grader"] == "rubric_llm" and api_key:
        spec = part["answer_spec"]
        if grade_rubric_llm(spec, {"text": spec["exemplar"]}, api_key=api_key).score < 0.8:
            return None, "exemplar"
    item: dict[str, Any] = {
        "prompt_md": prompt, "prompt": prompt[:500], "statement_latex": None, "steps": [], "parts": [part],
    }
    expl = str(data.get("explanation_md") or "").strip()[:1000]
    if expl:
        item["explanation_md"] = expl
    visual = sanitize_visual(data.get("visual"))
    if visual and "problem" in COMPONENTS[visual["type"]]["where"]:
        item["visual"] = visual
    return item, ""


def _norm_latex(s: str) -> str:
    # ponytail: textual match only; `8+2x=18` vs a demo's `2x+8=18` slips through.
    return re.sub(r"\s+|\\[,;!]|\\left|\\right", "", s or "")


def canonical_key(item: dict[str, Any]) -> str:
    """Structural SymPy form of the GIVEN step, so `2+x=5` and `x+2=5` dedupe.

    Not solution-set equivalence: `x+2=5` and `x+3=6` are different problems.
    Generic items (no statement) key on their normalized ``prompt_md``.
    """
    if not item.get("statement_latex") and item.get("prompt_md"):
        return " ".join(str(item["prompt_md"]).casefold().split())
    steps = item.get("steps") or []
    raw = str((steps[0].get("sympy") if steps else None) or item.get("statement_latex") or "")
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr

        expr = parse_expr(
            raw,
            local_dict={"x": sp.Symbol("x"), "y": sp.Symbol("y"), "Eq": sp.Eq},
            evaluate=False,
        )
        return sp.srepr(expr)
    except Exception:  # noqa: BLE001
        return re.sub(r"\s+", "", str(item.get("statement_latex") or raw))


def _explain(raw: dict[str, Any], reason: str) -> str:
    code, _, idx = reason.partition(":")
    steps = raw.get("steps") if isinstance(raw.get("steps"), list) else []
    if not steps:
        detail = f" ({idx})" if idx and not idx.isdigit() else ""
        return f"{_REASON_TEXT.get(code, code)}{detail}; fix only that"
    i = int(idx) if idx.isdigit() else len(steps) - 1
    st = steps[i] if 0 <= i < len(steps) and isinstance(steps[i], dict) else {}
    return (
        f"step {i}: {_REASON_TEXT.get(code, code)} "
        f"(latex `{st.get('latex')}`, sympy `{st.get('sympy')}`); fix only that"
    )


def request_items(
    *,
    context: str,
    task: str,
    api_key: str,
    client: httpx.Client | None = None,
    system: str = _SYSTEM_PROMPT,
) -> list[dict[str, Any]]:
    """One LLM call → raw item drafts. Static system + context first, per-call ``task`` last."""
    data = chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Skill / context:\n{context}"},
            {"role": "user", "content": task},
        ],
        api_key=api_key,
        task="fast",
        temperature=0.45,
        client=client,
    )
    items = (data or {}).get("items")
    return [x for x in items if isinstance(x, dict)][:8] if isinstance(items, list) else []


def _ask_task(n: int, spec: Any, avoid: list[str]) -> str:
    task = f"Write {n} DIFFERENT items."
    if isinstance(spec, list):
        task += " Item k follows spec k:\n" + json.dumps(spec)
    elif spec:
        task += "\nProblem spec (follow it):\n" + json.dumps(spec)
    for name in {s.get("visual") for s in (spec if isinstance(spec, list) else [spec]) if s}:
        if name in COMPONENTS:
            task += f"\n{name} props format: {COMPONENTS[name]['props']}"
    if avoid:
        task += "\nDo NOT reuse these statements: " + "; ".join(avoid)[:600]
    return task


def generate_items_for_node(
    *,
    node_title: str,
    api_key: str,
    count: int = 5,
    client: httpx.Client | None = None,
    specs: list[dict[str, Any]] | None = None,
    overshoot: int = 1,
    avoid: list[str] | None = None,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate up to `count` distinct verified items (AI only, no seed bank).

    Math profiles (default): SymPy-verified statement + steps. Other profiles: §6.2 items with
    one QuickCheck/MatchPairs part, structurally verified (``verify_generic_item``).
    Slot i follows ``specs[i % len(specs)]``; items carry ``spec_index`` (the spec's index,
    or the slot when there are no specs). One call per spec asks for its slots + `overshoot`.
    ``avoid``: statements already shown as worked examples (a practice copy leaks the answer).
    """
    if not api_key or count <= 0:
        return []
    if is_math(profile):
        system, verify = _SYSTEM_PROMPT, verify_item
    else:
        allowed = allowed_components(profile)
        system = _generic_system(profile or {}, allowed)

        def verify(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
            return verify_generic_item(raw, allowed, api_key)

    def text_of(item: dict[str, Any]) -> str:
        return str(item.get("statement_latex") or item.get("prompt_md") or "")

    avoid = [a for a in avoid or [] if a]
    blocked = {_norm_latex(a) for a in avoid}
    filled: dict[int, dict[str, Any]] = {}
    spare: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: Counter[str] = Counter()
    groups: dict[int | None, list[int]] = {}
    for slot in range(count):
        groups.setdefault(slot % len(specs) if specs else None, []).append(slot)
    fixes: dict[int | None, list[tuple[dict[str, Any], str]]] = {}

    def spec_of(si: int | None) -> dict[str, Any] | None:
        return specs[si] if specs and si is not None else None

    def accept(si: int | None, raw: dict[str, Any], *, repairable: bool) -> None:
        item, reason = verify(raw)
        if not item:
            code = reason.split(":")[0]
            stats[code] += 1
            if repairable and code in _REASON_TEXT:
                fixes.setdefault(si, []).append((raw, reason))
            return
        key = canonical_key(item)
        if key in seen:
            stats["duplicate"] += 1
            return
        if _norm_latex(text_of(item)) in blocked:
            stats["blocked"] += 1
            return
        seen.add(key)
        own = [s for s in groups.get(si, []) if s not in filled]
        if own:
            place(own[0], item)
        else:
            spare.append(item)  # only fills slots still empty once every spec had its turn

    def place(target: int, item: dict[str, Any]) -> None:
        spec = spec_of(target % len(specs)) if specs else None
        if spec:
            try:
                item["difficulty"] = round(min(0.95, max(0.05, float(spec.get("difficulty")))), 2)
            except (TypeError, ValueError):
                pass
        item["spec_index"] = target % len(specs) if specs else target
        filled[target] = item

    def use_spares() -> None:
        for s in range(count):
            if s not in filled and spare:
                place(s, spare.pop(0))

    def run(calls: list[tuple[int | None, Callable[[], list[dict[str, Any]]]]], repairable: bool) -> None:
        if not calls:
            return
        workers = max(1, min(len(calls), settings.llm_max_concurrency))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [(si, ex.submit(fn)) for si, fn in calls]
            for si, fut in futs:
                for raw in fut.result():
                    accept(si, raw, repairable=repairable)

    def ask(task: str) -> Callable[[], list[dict[str, Any]]]:
        return lambda: request_items(context=node_title, task=task, api_key=api_key, client=client, system=system)

    run(
        [(si, ask(_ask_task(len(slots) + overshoot, spec_of(si), avoid))) for si, slots in groups.items()],
        repairable=True,
    )
    if len(filled) < count and fixes:
        repair_calls = []
        for si, bad in fixes.items():
            payload = [{"item": raw, "error": _explain(raw, reason)} for raw, reason in bad[:4]]
            task = (
                "These items failed verification. Return the corrected items in the same "
                "order, changing only what each error names:\n" + json.dumps(payload)
            )
            repair_calls.append((si, ask(task)))
        run(repair_calls, repairable=False)
    use_spares()
    missing = [s for s in range(count) if s not in filled]
    if missing:
        used = avoid + [text_of(i) for i in filled.values()]
        miss_specs = [spec_of(s % len(specs)) for s in missing] if specs else None
        topup = ask(_ask_task(len(missing), miss_specs, used))()
        for j, raw in enumerate(topup):
            si = (missing[j] % len(specs)) if specs and j < len(missing) else None
            accept(si, raw, repairable=False)
        use_spares()
    stats["extra"] += len(spare)
    with _rejects_lock:
        REJECTS.update(stats)
    if len(filled) < count:
        _log.warning("items_short got=%d/%d %s", len(filled), count, dict(stats))
    return [filled[s] for s in sorted(filled)]
