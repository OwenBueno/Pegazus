# PROJECT COGNITIVE OS
## Document 04: System Architecture & Data Schemas
**Version:** 1.2 (multi-subject; see §8)  
**Target:** Infrastructure Topology, Relational Data Models, Knowledge Graph Serialization, API Contracts, Privacy, Observability  
**Runtime:** Next.js 16 (Edge/Client) + Python 3.12 (FastAPI / SymPy worker pool) + PostgreSQL 18

---

### 1. High-Level System Topology

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT TIER (Mobile-First PWA)                         │
│  - Next.js 16 (App Router, React Server Components)                              │
│  - Local State & Offline Cache: IndexedDB (TanStack Query + Dexie.js)            │
│  - GenUI Host Renderer (validates + resolves typed JSON widget lists)            │
│  - Math Input/Output: MathLive (Virtual Touch Keyboard) + KaTeX                  │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTPS / SSE
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY & ORCHESTRATION (FastAPI)                       │
│  - Authentication, Rate Limiting, Request Validation (Pydantic v2)               │
│  - SSE Streamer for Background Knowledge Graph Generation                        │
│  - Session Runner: accuracy band, hint ladder, micro-break timer, rule fallback  │
└───────────────┬────────────────────────┬─────────────────────────┬───────────────┘
                │                        │                         │
                ▼                        ▼                         ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│ DETERMINISTIC WORKERS   │ │ OPENROUTER              │ │ PERSISTENCE TIER        │
│ - SymPy Evaluation Pool │ │ - Jev 1.13 (Decisions)  │ │ - PostgreSQL 18         │
│ - AST Diff Engine       │ │ - deepseek-v4.1-flash   │ │ - Graph Adjacency DAG   │
│ - FSRS-6 (py-fsrs)      │ │ - glm-5.3-flash         │ │ - FSRS Memory States    │
└─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
```

---

### 2. Relational & Graph Data Models (PostgreSQL 18)

Storing the DAG in PostgreSQL via adjacency tables and recursive CTEs gives transactional consistency with FSRS state updates and keeps MVP infrastructure to one database. *ponytail: no graph DB; recursive CTEs are fine for curricula of hundreds to low thousands of nodes. Upgrade path: materialized ancestor closure table, then a graph DB, only if traversal latency shows up in traces.*

```
                 ┌──────────────┐
                 │    users     │
                 └──────┬───────┘
          ┌─────────────┼──────────────────────┐
          │ 1:N         │ 1:N                  │ 1:N
 ┌────────┴───────┐ ┌───┴────────────┐ ┌───────┴──────────┐
 │ learning_paths │ │ session_logs   │ │ user_node_states │
 └───────┬────────┘ └───┬────────────┘ │  (FSRS-6 memory) │
         │ 1:N          │ 1:N          └───────┬──────────┘
 ┌───────┴────────┐ ┌───┴────────────┐         │ N:1
 │   path_nodes   │ │    attempts    │─────────┤
 └───────┬────────┘ └───┬────────────┘         │
         │ N:1          │ N:1                  │
 ┌───────┴──────────────┴──────┐      ┌────────┴────────┐
 │       knowledge_nodes       │──1:N─│      items      │
 └───────┬─────────────────────┘      └─────────────────┘
         │ N:N (self)
 ┌───────┴────────┐
 │ knowledge_edges│
 └────────────────┘
```

#### 2.1 Core Schema DDL

```sql
-- gen_random_uuid() is built in since PostgreSQL 13; pgcrypto is used for key encryption.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS & COGNITIVE PROFILES
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Age & consent (see §6)
    birth_year SMALLINT NULL,
    is_minor BOOLEAN NOT NULL DEFAULT FALSE,
    guardian_consent_at TIMESTAMPTZ NULL,

    -- Memory model settings
    target_retention_rate NUMERIC(3, 2) NOT NULL DEFAULT 0.90,
    fsrs_weights REAL[] NULL,          -- 21 FSRS-6 weights; NULL = library defaults
    preferred_session_duration_mins INT NOT NULL DEFAULT 45,

    -- BYO API key, encrypted at the application layer (see §6.3)
    custom_openrouter_api_key_encrypted BYTEA NULL,

    CONSTRAINT chk_fsrs_weights_len CHECK (fsrs_weights IS NULL OR array_length(fsrs_weights, 1) = 21)
);

-- 2. KNOWLEDGE GRAPH: ATOMIC NODES
CREATE TYPE node_type_enum AS ENUM ('CONCEPT', 'SKILL');
CREATE TYPE domain_enum AS ENUM ('MATHEMATICS', 'DEVOPS', 'LANGUAGE');
-- v1.2: legacy; 'GENERAL' added (20261009200000_domain_general.sql) and derived from subject_profile
-- (math notation → MATHEMATICS, target language → LANGUAGE, else GENERAL). New code reads subject_profile.
-- Multi-subject columns (subject_profile, items.parts/grader/prompt_md, attempts.submitted_answer/score)
-- are listed in Doc 10 §6.1; this DDL block is the original MVP schema.

CREATE TABLE knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain domain_enum NOT NULL DEFAULT 'MATHEMATICS',
    slug VARCHAR(255) UNIQUE NOT NULL, -- global, shared across paths: 'math.algebra.factoring-quadratics'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    node_type node_type_enum NOT NULL DEFAULT 'CONCEPT',

    -- Cognitive Load & Working Memory Metadata
    element_interactivity_weight NUMERIC(3, 2) NOT NULL DEFAULT 0.50, -- 0.1 (low) to 1.0 (high)
    canonical_equation_latex TEXT NULL,
    expected_ast_signature JSONB NULL,

    -- Provenance (FR-1.4)
    source_url TEXT NULL,
    source_license VARCHAR(64) NULL,   -- e.g. 'CC-BY-4.0'
    source_attribution TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. KNOWLEDGE GRAPH: DEPENDENCY EDGES (DAG)
-- One direction only: parent must be learned before child. "Requires" is the reverse read.
CREATE TYPE edge_type_enum AS ENUM ('PREREQUISITE_OF', 'TRANSFERS_TO');

CREATE TABLE knowledge_edges (
    parent_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    edge_type edge_type_enum NOT NULL DEFAULT 'PREREQUISITE_OF',
    weight NUMERIC(3, 2) NOT NULL DEFAULT 1.00, -- confidence; lowest weight is cut first when breaking cycles

    PRIMARY KEY (parent_id, child_id, edge_type),
    CONSTRAINT chk_no_self_loops CHECK (parent_id <> child_id)
);

CREATE INDEX idx_edges_child ON knowledge_edges(child_id);
-- Acyclicity is enforced by the DAG compiler (Doc 05 §4) before insert, not by a trigger.

-- 4. ITEM BANK (Doc 03 §6)
CREATE TYPE item_status_enum AS ENUM ('DRAFT', 'VERIFIED', 'RETIRED');
CREATE TYPE item_source_enum AS ENUM ('SEEDED', 'GENERATED');

CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    statement_latex TEXT NOT NULL,
    steps JSONB NOT NULL,                  -- [{ "latex": "...", "operation": "FACTOR_COMMON_TERM" }, ...]
    difficulty_estimate NUMERIC(3, 2) NOT NULL DEFAULT 0.50,
    status item_status_enum NOT NULL DEFAULT 'DRAFT',
    source item_source_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_items_node_verified ON items(node_id) WHERE status = 'VERIFIED';

-- 5. FSRS-6 USER MEMORY STATE
-- Mirrors py-fsrs Card fields. R is computed on read from S and elapsed time.
CREATE TYPE fsrs_state_enum AS ENUM ('LEARNING', 'REVIEW', 'RELEARNING');

CREATE TABLE user_node_states (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,

    fsrs_state fsrs_state_enum NOT NULL DEFAULT 'LEARNING',
    difficulty NUMERIC(4, 2) NULL,          -- D ∈ [1, 10]; NULL until first review
    stability NUMERIC(10, 4) NULL,          -- S in days; NULL until first review
    last_review_at TIMESTAMPTZ NULL,
    due_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Mastery & scaffolding
    p_mastery NUMERIC(3, 2) NOT NULL DEFAULT 0.00,   -- set by diagnostic inference (Doc 05 §5)
    reps INT NOT NULL DEFAULT 0,
    lapses INT NOT NULL DEFAULT 0,
    current_scaffold_level SMALLINT NOT NULL DEFAULT 2,   -- 1 = Worked, 2 = Faded, 3 = Blank

    PRIMARY KEY (user_id, node_id),
    CONSTRAINT chk_scaffold CHECK (current_scaffold_level BETWEEN 1 AND 3)
);

CREATE INDEX idx_user_node_states_due ON user_node_states(user_id, due_date ASC);

-- 6. LIVING MUTABLE LEARNING PLANS
CREATE TYPE plan_status_enum AS ENUM ('DRAFTING', 'ACTIVE', 'COMPLETED', 'ARCHIVED');

CREATE TABLE learning_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    target_goal TEXT NOT NULL,
    deadline_date DATE NULL,
    daily_budget_mins INT NULL,
    status plan_status_enum NOT NULL DEFAULT 'DRAFTING',
    estimated_total_minutes INT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- PRD Journey 2: target date AND/OR daily budget, at least one
    CONSTRAINT chk_path_constraint CHECK (deadline_date IS NOT NULL OR daily_budget_mins IS NOT NULL)
);

-- Which nodes belong to a path, and in what critical-path order
CREATE TABLE path_nodes (
    path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    sequence_index INT NOT NULL,           -- position on the critical path
    is_draft BOOLEAN NOT NULL DEFAULT TRUE, -- TRUE until Deep Research verifies it

    PRIMARY KEY (path_id, node_id),
    UNIQUE (path_id, sequence_index)
);

-- 7. SESSIONS (one row per practice session)
CREATE TABLE session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    path_id UUID NULL REFERENCES learning_paths(id) ON DELETE CASCADE, -- NULL for Quick Socratic mode

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    active_seconds INT NOT NULL DEFAULT 0,

    -- Rest protocol events
    micro_breaks_triggered INT NOT NULL DEFAULT 0,
    micro_breaks_skipped INT NOT NULL DEFAULT 0,
    post_session_rest_completed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Cost telemetry (§7)
    llm_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0
);

CREATE INDEX idx_session_logs_user_recent ON session_logs(user_id, started_at DESC);

-- 8. ATTEMPTS (one row per submitted step; feeds the K = 20 rolling window, Doc 03 §2.1)
CREATE TABLE attempts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_logs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    step_index SMALLINT NOT NULL,

    submitted_latex TEXT NOT NULL,
    verdict VARCHAR(40) NOT NULL,          -- e.g. CORRECT_OPTIMAL, SIGN_ERROR (Doc 05 §2)
    is_success BOOLEAN NOT NULL,           -- a_i in the rolling accuracy metric
    hint_level SMALLINT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL,
    scaffold_level SMALLINT NOT NULL,
    fsrs_grade SMALLINT NULL,              -- set on the final step of an item: 1..4
    decided_by VARCHAR(10) NOT NULL,       -- 'JEV' | 'RULES'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attempts_user_recent ON attempts(user_id, created_at DESC);
```

---

### 3. Component-Driven GenUI Schema Contract

The API passes typed layouts to the client. The contract is a **flat, ordered list of widgets** (no nesting). The client validates every payload against this contract (e.g. with a Zod schema generated from the same types) and against its widget registry before rendering. *ponytail: flat list, no recursive tree; add `children` only if a real layout needs nesting.*

#### 3.1 TypeScript GenUI Contract
```typescript
// contracts/genui.ts

export type CanvasWidgetType =
  | 'SymbolicStepEditor'
  | 'VirtualMathKeyboard'
  | 'FadedWorkedExample'
  | 'FunctionPlotter'
  | 'SocraticDialogueBox'
  | 'RestOverlay';

interface BaseWidgetConfig<T extends CanvasWidgetType, P> {
  id: string;
  type: T;
  visible: boolean;
  props: P;
}

export interface DerivationStep {
  stepNumber: number;
  latexExpression: string;
  isLocked: boolean;
  status?: 'VALID' | 'INVALID' | 'PENDING';
  justification?: string;
}

export type SymbolicStepEditorConfig = BaseWidgetConfig<'SymbolicStepEditor', {
  targetVariable: string;
  inlineValidation: boolean;
  activeStepIndex: number;
  initialSteps: DerivationStep[];
}>;

export type VirtualMathKeyboardConfig = BaseWidgetConfig<'VirtualMathKeyboard', {
  layout: 'algebra' | 'calculus';
  targetWidgetId: string;           // editor that receives key input
}>;

export type FadedWorkedExampleConfig = BaseWidgetConfig<'FadedWorkedExample', {
  problemStatement: string;         // LaTeX
  steps: DerivationStep[];          // steps before activeStepIndex are locked
  activeStepIndex: number;
}>;

export type FunctionPlotterConfig = BaseWidgetConfig<'FunctionPlotter', {
  expressions: string[];            // LaTeX, rendered read-only
  domain: [number, number];
  sliders?: Array<{ name: string; min: number; max: number; step: number; value: number }>;
}>;

export type SocraticDialogueBoxConfig = BaseWidgetConfig<'SocraticDialogueBox', {
  hintTier: 1 | 2 | 3;
  prompt: string;                   // plain text, max 240 chars (Doc 05 §3.2)
  highlightElementId?: string;
}>;

export type RestOverlayConfig = BaseWidgetConfig<'RestOverlay', {
  durationSeconds: number;          // default 15
  allowSkip: boolean;
  breathCycleSeconds: number;       // default 10 (5 s in, 5 s out)
}>;

export type AnyWidgetConfig =
  | SymbolicStepEditorConfig
  | VirtualMathKeyboardConfig
  | FadedWorkedExampleConfig
  | FunctionPlotterConfig
  | SocraticDialogueBoxConfig
  | RestOverlayConfig;

export interface GenUIWorkspacePayload {
  sessionId: string;
  nodeId: string;
  itemId: string;
  scaffoldLevel: 1 | 2 | 3;
  layoutMode: 'mobile_stacked' | 'desktop_split';
  widgets: AnyWidgetConfig[];       // rendered in order
}
```

---

### 4. Deterministic Math & SymPy Worker Architecture

> **Multi-subject (v1.2):** SymPy is now one grader (`sympy`) in the `backend/app/graders/` registry ([Doc 10 §5](10-multi-subject-spec.md)); `choice`, `match`, `order`, `categorize`, `exact`, `cloze`, `numeric`, `rubric_llm`, `speech_match` and `code_tests` grade non-math parts from the stored `answer_spec`. This section still describes the `sympy` grader, which math items use unchanged.

To meet the P95 < 200 ms NFR, SymPy checks run in a **pre-warmed process pool**. Spawning a process plus a `multiprocessing.Manager` on every call costs tens to hundreds of milliseconds on its own and must be avoided.

```
       [ Client submits step (session_id, item_id, step_index, LaTeX) ]
                          │
                          ▼
            [ FastAPI Controller ]  ── loads expected step from `items` (never from the client)
                          │
                          ▼
     ┌──────────────────────────────────────────┐
     │  ProcessPoolExecutor (pre-warmed)        │
     │  - Input length cap (e.g. 500 chars)     │
     │  - Per-task timeout: 150 ms              │
     │  - Worker recycled on timeout            │
     │  - Memory limit per worker (RLIMIT_AS)   │
     └────────────────────┬─────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
   [ Equivalence Check ]           [ AST Structure Check ]
   simplify + numeric sampling     operation-specific rules (Doc 03 §3.2)
```

#### 4.1 Evaluation Service Implementation

```python
# workers/math_evaluator.py
# Requires: sympy, antlr4-python3-runtime (version pinned to match SymPy's LaTeX parser).
import random
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeout

import sympy as sp
from sympy.parsing.latex import parse_latex

MAX_LATEX_LEN = 500
_pool = ProcessPoolExecutor(max_workers=4)  # created at app startup; workers stay warm


def _to_zero_form(expr):
    """Equations become lhs - rhs; expressions pass through."""
    return expr.lhs - expr.rhs if isinstance(expr, sp.Equality) else expr


def _numerically_equal(a, b, samples: int = 8) -> bool:
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    for _ in range(samples):
        point = {s: random.uniform(-10, 10) for s in syms}
        try:
            if abs(complex(a.evalf(subs=point)) - complex(b.evalf(subs=point))) > 1e-8:
                return False
        except (ZeroDivisionError, TypeError, ValueError):
            continue
    return True


def _evaluate(latex_user: str, latex_target: str) -> dict:
    user, target = parse_latex(latex_user), parse_latex(latex_target)
    is_equation = isinstance(target, sp.Equality)
    u, t = _to_zero_form(user), _to_zero_form(target)

    if is_equation:
        # Equivalent if one side-difference is a non-zero constant multiple of the other.
        ratio = sp.simplify(u / t) if t != 0 else None
        equivalent = ratio is not None and ratio.is_number and ratio != 0
    else:
        equivalent = sp.simplify(u - t) == 0 or _numerically_equal(u, t)

    return {
        "success": True,
        "is_equivalent": bool(equivalent),
        "is_factored": (not is_equation) and user.is_Mul,
        "error": None,
    }


def evaluate_step_safe(latex_user: str, latex_target: str, timeout_seconds: float = 0.150) -> dict:
    if len(latex_user) > MAX_LATEX_LEN:
        return {"success": False, "is_equivalent": False, "error": "INPUT_TOO_LONG"}
    future = _pool.submit(_evaluate, latex_user, latex_target)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeout:
        future.cancel()  # ponytail: a stuck worker is only replaced when the pool is recycled; upgrade path: pebble.ProcessPool with per-task kill
        return {"success": False, "is_equivalent": False, "error": "EVALUATION_TIMEOUT"}
    except Exception as e:  # parse errors
        return {"success": False, "is_equivalent": False, "error": f"PARSE_ERROR: {e}"}
```

**Notes:**
* `parse_latex` builds a SymPy tree from a grammar and does **not** call `eval`. Never pass learner input to `sympify()` / `parse_expr()` on raw strings; if a non-LaTeX path is added, use `parse_expr` with an explicit `local_dict`, no `global_dict` builtins, and a whitelisted `transformations` tuple.
* When an equation's side-differences are not constant multiples (e.g. after squaring both sides), fall back to comparing `solveset` results over the node's domain (Doc 03 §3.1).
* The unit test for this module lives next to it (`workers/test_math_evaluator.py`) and covers: equivalent expressions, `2x=6` vs `x=3`, a sign error, a timeout, an oversized input.

---

### 5. Core API Endpoints & Interfaces

#### 5.1 Learning Path Ingestion & Live Streaming
* **`POST /api/v1/paths/ingest`**
  * **Payload** (`deadline_date` and `daily_budget_mins` are each optional, but at least one is required):
    ```json
    {
      "goal_text": "Master Polynomial & Rational Functions for Pre-Calculus",
      "deadline_date": "2026-10-15",
      "daily_budget_mins": 45,
      "optional_syllabus_markdown": null
    }
    ```
  * **Response (Immediate optimistic preview within $<1.5\text{ s}$):**
    ```json
    {
      "path_id": "8b9e67a4-4340-4fc7-bf84-7a1a45747f5d",
      "status": "DRAFTING",
      "initial_draft_nodes": [
        { "slug": "math.algebra.polynomial-roots", "title": "Roots of Polynomials" },
        { "slug": "math.algebra.rational-asymptotes", "title": "Rational Functions & Asymptotes" }
      ],
      "stream_url": "/api/v1/paths/8b9e67a4-4340-4fc7-bf84-7a1a45747f5d/stream"
    }
    ```

* **`GET /api/v1/paths/:path_id/stream`**
  * **Protocol:** Server-Sent Events (SSE). Supports `Last-Event-ID` so the client can resume after a dropped connection.
  * **Behavior:** Streams node-by-node topological updates as the Deep Research Agent constructs and validates dependencies in PostgreSQL (event types in Doc 05 §4).

#### 5.2 Real-Time Step Evaluation & Jev Gate
* **`POST /api/v1/session/evaluate-step`**
  * **Payload** (the expected answer is looked up server-side from `items.parts[part_index].answer_spec`; the client never receives or sends the key). `answer` is grader-specific (`{latex}`, `{ids}`, `{pairs}`, `{value, unit?}`, `{text}`, `{code, passed, total}`, …) and capped at 4 KB. The legacy `step_index` / `submitted_latex` body was removed in Doc 11 MS-5.3 (422):
    ```json
    {
      "session_id": "3c4d5e6f-1234-5678-90ab-cdef12345678",
      "item_id": "5e6f7a8b-1234-4c5d-9e0f-a1b2c3d4e5f6",
      "part_index": 2,
      "answer": { "latex": "3x - 12 = 15" },
      "hint_level": 0,
      "latency_ms": 8400
    }
    ```
  * **Processing Lifecycle:**
    1. Loads the part and grades it with its grader: for `sympy`, the final-answer shortcut then `evaluate_step_safe` in the SymPy pool ($<200\text{ ms}$); other graders are pure functions, no Jev (`decided_by = RULES`, or `CLIENT` for `code_tests`).
    2. Inserts an `attempts` row and recomputes rolling accuracy $\bar{A}_K$.
    3. Calls Jev via the Decisions API for verdict / scaffold / hint / grade / micro-break (target $<150\text{ ms}$, hard timeout 400 ms). On timeout or low confidence, the rule engine decides (Doc 05 §6).
    4. If a hint is required, calls System 2 for the Socratic prompt.
    5. Maps the decision to a `GenUIWorkspacePayload`.
  * **Response (GenUI JSON Contract):**
    ```json
    {
      "step_status": "VALID",
      "scaffold_level": 2,
      "next_action": "ADVANCE_STEP",
      "decided_by": "JEV",
      "genui_payload": {
        "sessionId": "3c4d5e6f-1234-5678-90ab-cdef12345678",
        "nodeId": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "itemId": "5e6f7a8b-1234-4c5d-9e0f-a1b2c3d4e5f6",
        "scaffoldLevel": 2,
        "layoutMode": "mobile_stacked",
        "widgets": [
          {
            "id": "step_editor_1",
            "type": "SymbolicStepEditor",
            "visible": true,
            "props": {
              "targetVariable": "x",
              "inlineValidation": true,
              "activeStepIndex": 2,
              "initialSteps": [
                { "stepNumber": 1, "latexExpression": "3(x - 4) = 15", "isLocked": true },
                { "stepNumber": 2, "latexExpression": "3x - 12 = 15", "isLocked": true, "status": "VALID" },
                { "stepNumber": 3, "latexExpression": "", "isLocked": false }
              ]
            }
          },
          {
            "id": "keyboard_1",
            "type": "VirtualMathKeyboard",
            "visible": true,
            "props": { "layout": "algebra", "targetWidgetId": "step_editor_1" }
          }
        ]
      }
    }
    ```

#### 5.3 Offline Sync
* **`POST /api/v1/session/:session_id/sync`**: accepts a batch of attempts captured offline (each with a client-generated idempotency key and the same `{part_index, answer}` as evaluate-step). Server re-grades every attempt with the part's grader (client results are never trusted) and returns the authoritative state. The client converts records queued by pre-MS-5.3 builds (`step_index`/`submitted_latex`) to `{part_index, answer: {latex}}` before sending.

---

### 6. Authentication, Privacy & Minors

#### 6.1 Authentication
* Email magic-link or OAuth (Google/Apple) via a managed provider; the API validates short-lived JWTs. No passwords stored by us.
* Rate limits per user and per IP on `evaluate-step`, `ingest`, and all LLM-backed routes.

#### 6.2 Minors & Consent
Secondary-school learners may be under 13 (US COPPA) or under the local digital-consent age (GDPR Art. 8: 13–16 depending on member state).
* Collect birth year at sign-up (neutral age screen, no pre-filled value).
* Under the applicable consent age: block account activation until verifiable guardian consent (`guardian_consent_at`), disable BYO API keys and optional uploads, and exclude from any analytics beyond what is needed to run the service.
* No advertising, no third-party tracking, no sale of data for any user.
* *Legal review required before launch in each market.*

#### 6.3 Data Handling
* **BYO API keys:** encrypted with an envelope key from a managed KMS (AES-256-GCM, application layer), never logged, never returned to the client after save.
* **Retention:** attempt-level telemetry kept 24 months for FSRS optimization, then aggregated; account deletion hard-deletes all user rows (`ON DELETE CASCADE`) within 30 days.
* **LLM data:** send only the minimum state to OpenRouter (no email or name); prefer providers with zero-data-retention routing where available.
* **Uploads:** syllabus uploads are size-limited, virus-scanned, parsed as text only, and stored no longer than needed to build the graph.

---

### 7. Observability

* **Tracing:** OpenTelemetry spans for every request, with child spans for `sympy.evaluate`, `jev.decide`, `system2.hint`, `db.*`. P95 dashboards per span map directly to the NFRs in [Doc 02 §5.1](02-product-requirements.md#51-performance--latency).
* **SLO alerts:** SymPy P95 > 200 ms, Jev P95 > 150 ms, Jev fallback rate > 5%, GenUI validation failures > 0.
* **Cost:** every Jev response includes `usage.cost` (USD); System 2 cost comes from OpenRouter usage accounting. Both are summed into `session_logs.llm_cost_usd` to track cost per session and verify the "90% of interactions resolved without a frontier LLM" claim in [Doc 01 §7](01-executive-summary.md).
* **Pedagogy metrics:** fallback decisions (`attempts.decided_by = 'RULES'`), scaffold transitions, micro-break skip rate, FSRS predicted $R$ vs. observed probe accuracy.

---

### 8. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.1 | 2026-09-24 | MVP architecture (math). |
| 1.2 | 2026-10-09 | Multi-subject ([Doc 10](10-multi-subject-spec.md)): SymPy is the `sympy` grader of a registry (§4); evaluate-step and offline sync take `{part_index, answer}` only, legacy body removed (§5.2–5.3, Doc 11 MS-5.3); `domain_enum` legacy + `GENERAL` (§2.1). Lesson payloads carry `sources` and only research-cited URLs (Doc 10 R4). Math-only statements elsewhere in this doc describe the math pack. |
