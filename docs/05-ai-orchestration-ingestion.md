# PROJECT COGNITIVE OS
## Document 05: AI Orchestration & Ingestion Pipeline
**Version:** 1.2 (multi-subject; see §7)  
**Target:** Dual-Process AI Architecture, OpenRouter Routing Topology, Jev Decision Questions, Deep Research Ingestion Pipeline, Adaptive Diagnostic  
**Runtime:** Python 3.12 (AsyncIO / Celery / Redis) + OpenRouter API (Decisions API + Chat Completions)

> Model facts verified on 2026-09-24 against OpenRouter: [Jev docs](https://openrouter.ai/docs/guides/community/jev), [Jev 1.13](https://openrouter.ai/typesafe/jev-1.13), [DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash), [GLM 5.3 Flash](https://openrouter.ai/z-ai/glm-5.3-flash). Re-check prices before budgeting.

---

### 1. Dual-Process AI Orchestration Topology

Cognitive OS splits processing into **deterministic code**, **System 1 (Jev, typed decisions)** and **System 2 (DeepSeek / GLM, text generation)**. Code owns anything that is arithmetic, counting, or time-based (rolling accuracy, thresholds, timers, attempt counts), in line with TypeSafe's guidance that such judgments stay in code. Jev owns the fuzzy judgments. System 2 only writes text.

```
                        [ Learner Submission / Action ]
                                       │
                                       ▼
                   [ Deterministic Layer: SymPy / AST Check ]
                                       │  (validation flags)
                                       ▼
                   [ Session Runner (code) ]
                   - Rolling accuracy A_K, scaffold matrix (Doc 03 §2.2)
                   - Attempt count → hint tier (FR-5.3)
                   - Active time → micro-break (Doc 03 §5.1)
                                       │
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │ SYSTEM 1: JEV (typesafe/jev-1.13, Decisions API)              │
       │ - Typed answers only: choice / noul / score + probabilities   │
       │ - Classifies the error, grades fluency, detects prereq gaps   │
       │ - Low confidence or timeout → rule engine decides instead     │
       └───────────────────────────────┬───────────────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             [ Action: Advance ]                [ Action: Intervene ]
             - Emits next GenUI payload         - Needs Socratic text
             - No generation cost               │
                                                ▼
       ┌───────────────────────────────────────────────────────────────┐
       │ SYSTEM 2: SOCRATIC SYNTHESIS (DeepSeek V4.1 Flash / GLM 5.3)  │
       │ - Structured output (JSON schema)                             │
       │ - One 1-2 sentence hint at the tier chosen by code            │
       │ - Zero answer disclosure (checked before display, §3.3)       │
       └───────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
                     [ Rendered GenUI Workspace ]
```

---

### 2. Jev (System 1) Decision Contract

Jev is not a chat model and does not accept a JSON output schema. Each request sends a `state` object plus a set of independent, typed `questions`; Jev returns one typed answer per question with probabilities, via `POST https://openrouter.ai/api/alpha/decisions`. Pricing: input tokens only (currently $0.042 / M), output free; every response includes `usage.cost`.

#### 2.1 Step Evaluation Request
Sent once per submitted step, after SymPy has run. All questions are answered in parallel in one round trip.

```json
{
  "model": "typesafe/jev-1.13",
  "state": {
    "problem": { "statement_latex": "3(x - 4) = 15", "node_title": "Solving linear equations with distribution" },
    "expected_step": { "latex": "3x - 12 = 15", "operation": "DISTRIBUTE" },
    "submitted_step": { "latex": "3x - 4 = 15" },
    "sympy": { "is_equivalent": false, "structure_ok": false, "error": null },
    "context": { "attempt_number": 1, "scaffold_level": 2, "latency_bucket": "normal" }
  },
  "questions": {
    "evaluation_verdict": {
      "type": "choice",
      "instructions": "Given `sympy`, `expected_step` and `submitted_step`, what best describes the learner's step?",
      "criteria": {
        "CORRECT_OPTIMAL": "Equivalent and performs the expected operation.",
        "CORRECT_SUBOPTIMAL": "Equivalent but skips or reorders the expected operation.",
        "SYNTAX_ERROR": "The input could not be read as mathematics.",
        "SIGN_ERROR": "Wrong only because a sign was flipped or dropped.",
        "DISTRIBUTION_SLIP": "A factor was not multiplied across every term.",
        "CALCULATION_SLIP": "An arithmetic mistake with the right method.",
        "STRUCTURAL_MISCONCEPTION": "The method itself is wrong for this step.",
        "PREREQUISITE_FAILURE": "The step shows a gap in an earlier skill, not in this one.",
        "none": "None of the above fits."
      }
    },
    "recommended_fsrs_grade": {
      "type": "score",
      "instructions": "How fluent was this attempt, considering correctness, `context.attempt_number` and `context.latency_bucket`?",
      "criteria": [
        "Again: failed or needed the operational hint.",
        "Hard: solved with hesitation or a conceptual hint.",
        "Good: solved correctly at normal pace with no hints.",
        "Easy: solved immediately with no hesitation."
      ]
    }
  }
}
```

* `latency_bucket` (`fast` / `normal` / `slow`) is computed in code from the learner's latency distribution; Jev never compares numbers.
* The score answer is zero-based, so `fsrs_grade = round(score) + 1`.
* **Code-owned decisions** (not Jev questions): `scaffold_action` (Doc 03 §2.2 matrix on $\bar{A}_K$), `hint_tier_required` (attempt count, FR-5.3), `trigger_micro_break` (active time, Doc 03 §5.1).

#### 2.2 Quick Socratic Intent Request (Journey 1)
```json
{
  "model": "typesafe/jev-1.13",
  "state": { "user_query": "Why do we divide by a when completing the square for ax^2+bx+c=0?" },
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "What is the learner asking for in `user_query`?",
      "criteria": {
        "CONCEPTUAL_EXPLANATION": "Wants to understand why a rule or step works.",
        "PROCEDURAL_STUCK": "Is stuck on a specific problem and wants the next step.",
        "CHECK_MY_WORK": "Wants their own solution checked.",
        "OFF_TOPIC": "Not a mathematics learning request.",
        "none": "None of the above fits."
      }
    }
  }
}
```

#### 2.3 Confidence Policy
* A `choice` answer is used only if its `confidence` ≥ **0.70**; a `score` answer only if its `confidence` ≥ **0.60**. Starting values; tune from a labeled sample of ~200 attempts (replay saved answers, no new calls).
* Below threshold, missing `confidence`/`probabilities`, timeout (400 ms), or HTTP error → the **rule engine** decides (§6.1) and the attempt is logged with `decided_by = 'RULES'`.
* Raw answers are stored so thresholds can be re-tuned by replay.

---

### 3. Socratic Prompting Guardrails (System 2)

System 2 is only invoked when code sets `hint_tier_required > 0`. It runs on **DeepSeek V4.1 Flash** (fallback **GLM 5.3 Flash**) through OpenRouter Chat Completions with structured output.

#### 3.1 Socratic System Prompt Specification
> **Multi-subject (v1.2):** every System 2 prompt (tutor, hints, `/ask`, outline, research, lesson design, critic, item generation) is built from the path's **subject profile** via `profile_prompt(profile)` (subject, level, notation, languages; [Doc 10 §3, §7](10-multi-subject-spec.md)). "Mathematical law", KaTeX and SymPy wording below apply only when `notation` is `math` (KaTeX also for `chem`); `tests/test_prompts_neutral.py` asserts that non-math prompts carry no math vocabulary.

```markdown
You are the Socratic Tutor Engine inside Cognitive OS. Your role is strictly to guide the learner to self-identify their error.

NON-NEGOTIABLE GUARDRAILS:
1. NEVER reveal the correct equation, numbers, calculation steps, or final answer.
2. NEVER use praise filler ("Good job!", "Almost there!").
3. Limit your output to a maximum of TWO (2) concise sentences.
4. Respond in the learner's locale: {locale}.
5. Strictly follow the Hint Tier specified:
   - TIER 1 (Conceptual): Direct attention to the underlying mathematical law or identity. Mention zero numbers.
   - TIER 2 (Strategic): Suggest a diagnostic verification technique (e.g., "Check the signs when distributing").
   - TIER 3 (Operational): Identify the exact line or term that failed without providing the correction.
```

#### 3.2 Output Schema for Socratic Engine
```python
# orchestrator/schemas.py
from typing import Literal
from pydantic import BaseModel, Field

class SocraticInterventionPayload(BaseModel):
    hint_tier: Literal[1, 2, 3]
    detected_error_category: Literal["SIGN_ERROR", "DISTRIBUTION_SLIP", "CALCULATION_SLIP",
                                     "STRUCTURAL_MISCONCEPTION", "PREREQUISITE_FAILURE", "OTHER"]
    pedagogical_focus: str = Field(max_length=120, description="The underlying concept being prompted.")
    socratic_prompt: str = Field(max_length=240, description="The 1-2 sentence guiding question.")
    highlight_element_id: str | None = Field(default=None, description="Target step ID to highlight.")
```

#### 3.3 Answer-Leak Check
Before display, code parses any math in `socratic_prompt` and rejects the hint if it contains the expected step or final answer (SymPy equivalence against `items.steps`). On rejection, retry once, then fall back to a templated hint for that error category and tier. *(Math items only; non-math answer keys never leave the server, Doc 10 §6.4.)*

---

### 4. The Deep Research Ingestion Pipeline ("Create on the Way")

When a user initiates **Path of Learning Mode**, the engine runs a multi-stage background process to build a verified DAG instead of relying on a single-prompt syllabus.

> **Multi-subject (v1.2):** before ingest, `POST /api/v1/paths/profile` infers a subject profile the learner confirms (Doc 10 §3); ingest stores it on the path and every node. The OpenStax algebra corpus grounds **math profiles only**. Per lesson, `build_research_brief` runs **web research with citations** (OpenRouter web plugin): it is forced for non-math profiles (one retry when no citation came back) and optional for math (`RESEARCH_WEB`). Only URLs returned as `url_citations` (http(s), not blocklisted) become brief `sources` (`{kind, title, url, license, quote}`, the quote being the fetched snippet); a cached non-math brief without web sources is re-researched. Downstream: the designer may link only `citable_sources` (SourceExcerpt `url`), the non-math critic treats claims contradicting the sources' quotes and unsupported SourceExcerpts as fact errors, item text is scrubbed of uncited URLs at write time, and lesson payloads (`SessionNodeOut`, `PathNodeOut`) return `sources` and drop every other URL at read time (`scrub_urls`; `tests/test_citation_leak.py`). Generation failures end in `FAILED` + learner-safe reason + Retry; there are no static fallback lessons or outlines.

```
       [ User Goal: "Master Calculus Limits & Continuity for Midterm" ]
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼ (<1.5s)                                       ▼ Asynchronous Job
     [ Optimistic Scaffold ]                       [ Deep Research Pipeline ]
     - GLM 5.3 Flash draft                         ├── 1. Retrieve licensed sources
     - Renders preview UI                          ├── 2. Structural decomposition
     - Match to existing nodes by slug             ├── 3. Acyclicity + prereq validation
                                                   ├── 4. Transitive reduction
                                                   └── 5. Item generation (Doc 03 §6)
                                                              │
                                                              ▼
                                                   [ SSE Stream: Live DAG Mutation ]
```

#### 4.1 Ingestion Pipeline Stages

##### Stage 1: Optimistic Draft Generator (Synchronous, $<1.5\text{ s}$)
Calls `z-ai/glm-5.3-flash` to return 4–6 milestone modules. Each draft module is matched to existing `knowledge_nodes` by slug or embedding similarity first; only unmatched ones become new draft nodes (`path_nodes.is_draft = TRUE`). The client shows an animated "Refining graph..." indicator.

##### Stage 2: Deep Curriculum Ingestion (Asynchronous Background Task)
1. **Source retrieval (licensed only, FR-1.4):**
   * Allowed: [OpenStax](https://openstax.org/) textbooks (CC BY 4.0), [Common Core State Standards](https://www.thecorestandards.org/) (public license with attribution), user-uploaded syllabi (user's own material), other CC-BY / public-domain sources.
   * Not allowed without a license agreement: Khan Academy content (non-commercial licensing and terms of service restrict reuse), MIT OpenCourseWare (CC BY-NC-SA, non-commercial only, conflicts with paid tiers), scraped commercial course sites.
   * Every node stores `source_url`, `source_license`, `source_attribution`.
2. **Deconstruction into Atomic Primitives:**
   * **Concepts ($C_i$):** mental models (e.g., *$\epsilon$-$\delta$ definition of a limit*).
   * **Skills ($S_j$):** procedures (e.g., *conjugate multiplication for indeterminate forms*).
   * **Misconception Signatures:** known error patterns for the node (e.g., treating $0/0$ as $0$).

##### Stage 3: DAG Topology Compilation & Validation
* **Cycle breaking:** repeatedly find a cycle and remove its lowest-weight edge until none remain.
* **Transitive Reduction:** if $A \to B$, $B \to C$ and $A \to C$, drop $A \to C$.

```python
# pipeline/dag_compiler.py
import networkx as nx

def compile_authoritative_dag(raw_nodes: list[dict], raw_edges: list[dict]) -> tuple[nx.DiGraph, list[tuple]]:
    G = nx.DiGraph()
    for node in raw_nodes:
        G.add_node(node["slug"], title=node["title"], node_type=node["node_type"],
                   interactivity_weight=node["element_interactivity_weight"])
    for edge in raw_edges:
        G.add_edge(edge["parent_slug"], edge["child_slug"], weight=edge.get("weight", 1.0))

    # 1. Break cycles: each pass removes the weakest edge of one cycle.
    # ponytail: O(E) per removal, O(E^2) worst case; fine for curricula of a few hundred edges.
    removed = []
    while True:
        try:
            cycle = nx.find_cycle(G)
        except nx.NetworkXNoCycle:
            break
        u, v = min(((u, v) for u, v, *_ in cycle), key=lambda e: G.edges[e]["weight"])
        G.remove_edge(u, v)
        removed.append((u, v))

    # 2. Transitive reduction (returns a graph without attributes, so copy them back).
    reduced = nx.transitive_reduction(G)
    reduced.add_nodes_from(G.nodes(data=True))
    reduced.add_edges_from((u, v, G.edges[u, v]) for u, v in reduced.edges)
    return reduced, removed  # removed edges are logged for human review
```

Check: `pipeline/test_dag_compiler.py` asserts that a 3-cycle loses its lowest-weight edge, that $A \to C$ is pruned when $A \to B \to C$ exists, and that node attributes survive.

##### Stage 4: Live Client Hydration via Server-Sent Events (SSE)
As nodes and edges are verified in PostgreSQL, the backend streams events (each with an `id` for `Last-Event-ID` resume):
```
id: 12
event: node_validated
data: {"slug": "math.calc.indeterminate-forms", "title": "Indeterminate Forms (0/0)", "parent": "math.calc.direct-substitution"}

id: 19
event: graph_complete
data: {"total_nodes": 18, "estimated_hours": 9.5, "critical_path_length": 6}
```

##### Stage 5: Item Generation
For each new node, generate and verify items as specified in [Doc 03 §6](03-cognitive-engine-pedagogical.md#6-item-bank--problem-generation). A node is not served in practice until it has ≥5 `VERIFIED` items. Non-math items use the §6.2 parts shape of Doc 10 (`prompt_md`, `parts[{component, grader, props, answer_spec}]`) and a structural check per grader instead of SymPy.

---

### 5. Adaptive Baseline Diagnostic Engine

**Single source of truth for the diagnostic cap: 3 to 5 probes.**

A prerequisite graph is a partial order, so binary search over a topological sort is not valid: failing node $n_k$ says nothing about later nodes in the sort that are not its descendants. The diagnostic instead follows [Knowledge Space Theory](https://en.wikipedia.org/wiki/Knowledge_space) (the approach behind ALEKS): the learner's state is a set of mastered nodes closed under prerequisites, and each probe is chosen to shrink the set of still-uncertain nodes as much as possible.

```
       [ Compiled DAG: every node starts UNKNOWN ]
                                  │
                                  ▼
       [ Pick probe: UNKNOWN node that best splits UNKNOWN set ]
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
          [ Solved Fluently ]             [ Failed / Stalled ]
                  │                               │
   Node + all ancestors → MASTERED       Node + all descendants → NOT_MASTERED
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
       [ Stop after 5 probes, or when no UNKNOWN nodes remain (min 3) ]
       Frontier = NOT_MASTERED nodes whose parents are all MASTERED
```

#### 5.1 Probe Selection Algorithm
1. For each UNKNOWN node $n$, let $a(n)$ = number of UNKNOWN ancestors (incl. $n$) and $d(n)$ = number of UNKNOWN descendants (incl. $n$).
2. **Pick** $n^* = \arg\max_n \min(a(n), d(n))$: the node whose worst-case outcome still resolves the most nodes (a balanced split). Ties go to the node with lower `element_interactivity_weight`.
3. **Fluency Score** $F \in [0, 1]$ from correctness and latency, computed in code:
   $$F = \text{Correct} \times \left(1 - \min\left(1, \frac{\text{Latency}}{\text{Latency}_{\text{threshold}}}\right)\right)$$
   Latency uses a generous threshold (e.g. 3× the item's median) so slow-but-correct learners are not punished; a correct answer with $F < 0.80$ counts as "pass, low confidence" and sets $P(\text{Mastery}) = 0.70$ on the node only, without propagating.
4. If $F \ge 0.80$: node and all ancestors → MASTERED ($P(\text{Mastery}) = 0.95$), written to `user_node_states.p_mastery`.
5. If failed: node and all descendants → NOT_MASTERED.
6. **Terminate** after 5 probes or when no UNKNOWN nodes remain (minimum 3 probes). Remaining UNKNOWN nodes are treated as NOT_MASTERED and get confirmed by early practice.

*ponytail: deterministic KST with no lucky-guess/careless-error modeling. Upgrade path: probabilistic KST (BLIM) with per-item guess/slip rates once item data exists.*

Check: `diagnostic/test_probe_selection.py` asserts, on a 7-node chain, that the first probe is the middle node and that a pass marks exactly its ancestors as MASTERED.

---

### 6. OpenRouter Inference Configuration & Fallback Rules

```python
# orchestrator/router.py
OPENROUTER_CONFIG = {
    "system_1_decision": {
        "endpoint": "https://openrouter.ai/api/alpha/decisions",
        "model": "typesafe/jev-1.13",          # pin; don't use ~typesafe/jev-latest in production
        "timeout_seconds": 0.400,
        "fallback": "RULE_ENGINE",              # a chat model cannot answer the Decisions API
    },
    "system_2_socratic": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "deepseek/deepseek-v4.1-flash",
        "fallback_model": "z-ai/glm-5.3-flash",
        "temperature": 0.2,
        "max_tokens": 200,
        "timeout_seconds": 1.200,
    },
    "ingestion_draft": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "z-ai/glm-5.3-flash",
        "temperature": 0.3,
        "max_tokens": 1500,
        "timeout_seconds": 3.000,
    },
}
```

Pricing snapshot (2026-09-24, per million tokens, input / output): Jev 1.13 $0.042 / free; DeepSeek V4.1 Flash $0.15 / $0.60; GLM 5.3 Flash from $0.075 / $0.25 (varies by provider).

#### 6.1 Rule-Engine Fallback
Used when Jev times out, errors, or is below the confidence threshold (§2.3):
* **Verdict:** `CORRECT_OPTIMAL` if SymPy equivalent and structure OK; `CORRECT_SUBOPTIMAL` if equivalent but structure not OK; `SYNTAX_ERROR` on parse error; otherwise `CALCULATION_SLIP`.
* **FSRS grade:** 1 if failed or Level 3 hint used; 2 if Level 1–2 hint or `latency_bucket = slow`; 3 if correct with no hints; 4 if correct, no hints and `latency_bucket = fast`.
* Scaffold, hint tier and micro-break are already code-owned, so they are unaffected.

* **Circuit Breaker:** if Jev's error or timeout rate exceeds 20% over 1 minute, skip Jev calls for 60 seconds and use the rule engine directly.
* **Non-sympy graders** never call Jev: their verdict is `CORRECT_OPTIMAL` / `PARTIAL` / `INCORRECT` / `SYNTAX_ERROR` from the grader, and `PARTIAL` maps to FSRS grade 2 (Doc 10 §5).

---

### 7. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.1 | 2026-09-24 | MVP orchestration (math). |
| 1.2 | 2026-10-09 | Multi-subject ([Doc 10](10-multi-subject-spec.md)): profile-parameterized prompts (§3.1), pre-ingest profile inference, corpus for math only, web research with citations and the cited-URL-only rule (§4), generic item shape (§4.1 Stage 5), non-sympy graders bypass Jev (§6.1). Math-specific examples above remain valid for math profiles. |
