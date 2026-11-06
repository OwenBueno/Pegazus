# PROJECT COGNITIVE OS
## Document 02: Product Requirements Document (PRD)
**Version:** 1.2 (multi-subject; see §8)  
**Phase:** MVP (Phase 1 — Universal Engine & Mathematics Foundation), extended to any subject by [Doc 10](10-multi-subject-spec.md)  
**Target Platform:** Mobile-First Responsive Web App (PWA)

---

### 1. Executive Product Overview & Objectives

#### 1.1 Objective
Build an adaptive, mastery-based cognitive platform that ingests any learning target (started with College/Pre-Calculus Mathematics; since v1.2 any subject, grounded in cited web research), autonomously compiles a living dependency graph, and guides the learner to durable schema acquisition through **Component-Driven Generative UI (GenUI)**, **Jev-driven sub-second diagnostics**, and **neurobiologically grounded study cycles**.

#### 1.2 Core Success Metrics (KPIs)
How each KPI is measured is defined in [Section 7: KPI Measurement Protocol](#7-kpi-measurement-protocol).
* **Time-to-Mastery Velocity:** $\ge 25\%$ reduction in study hours required to achieve verifiable mastery on target topics compared to standard self-study or linear online courses.
* **Long-Term Retention Rate:** $\ge 88\text{–}90\%$ successful recall on FSRS-scheduled spaced retrieval probes after 14 and 30 days.
* **Cognitive Efficiency Index:** Ratio of active derivation time vs. idle/passive reading time exceeds $4:1$ (80% active cognitive work).
* **System Latency (P95):** 
  * Jev typed diagnostic decisions: $< 150\text{ ms}$ (target; OpenRouter publishes no latency figure for Jev, so this is validated in Phase P3).
  * SymPy symbolic algebraic verification: $< 200\text{ ms}$.
  * GenUI client layout re-render: $< 30\text{ ms}$ (smooth 60 fps).

---

### 2. User Personas

#### Persona A: The High-Stakes Exam Candidate ("Carlos", 20)
* **Context:** Preparing for an engineering university entrance exam or university Calculus midterm in 18 days.
* **Pain Points:** Overwhelmed by massive 500-page syllabi; doesn't know what he doesn't know; wastes hours re-watching YouTube explanations without knowing if he can actually solve problems under time constraints.
* **Needs:** Needs to know his exact knowledge gaps immediately, a strict daily plan that fits his 45-minute daily window, and rigorous practice that stops him from fooling himself.

#### Persona B: The Self-Directed STEM Pivot ("Elena", 28)
* **Context:** Software engineer transitioning into Machine Learning; needs to rebuild her intuition for Linear Algebra and Multivariate Calculus.
* **Pain Points:** Finds introductory materials too slow and patronizing, but advanced textbooks jump too quickly without explaining intermediate steps.
* **Needs:** Fast diagnostic that skips basics she already knows; step-by-step intermediate verification so she can pinpoint the exact mathematical step where her logic fails.

---

### 3. Core User Journeys

#### Journey 1: Quick Socratic Query (Mode A)
1. User opens the app on mobile or desktop.
2. Selects **"Quick Socratic"** input box.
3. Inputs an isolated problem, formula, or question: *"Why do we divide by $a$ when completing the square for $ax^2 + bx + c = 0$?"*
4. Jev answers a `choice` question classifying the intent (e.g. `CONCEPTUAL_EXPLANATION`, `PROCEDURAL_STUCK`, `CHECK_MY_WORK`) (target $<150\text{ ms}$).
5. System renders a single interactive canvas: a dynamic algebraic step breakdown paired with a concise, targeted Socratic question guiding the user to recognize the coefficient normalization.
6. User solves the prompt $\rightarrow$ session ends without polluting their long-term learning graphs.

#### Journey 2: Path of Learning Creation & Ingestion (Mode B)
1. User clicks **"Create Learning Path"**.
2. **Parameters Captured:**
   * **Subject/Goal:** e.g., *"Polynomials, Rational Functions & Limits"*.
   * **Constraint:** Target Date (e.g., *14 days*) AND/OR Daily Time Allocation (e.g., *40 mins/day*). At least one is required.
   * **Optional Upload:** PDF syllabus or problem set.
3. **Instant Preview:** Within $1.5\text{ seconds}$, a preliminary high-level topic path appears with a smooth "Refining Graph..." background indicator.
4. **Deep Research Pipeline:** In the background, the agent analyzes curriculum standards, decomposes concepts into atomic nodes, and compiles the Directed Acyclic Graph (DAG).
5. **Adaptive Baseline Diagnostic:** Prompts: *"Let's calibrate your starting point."* Serves 3–5 targeted problems, each chosen to best split the remaining uncertain part of the graph (see [Doc 05 §5](05-ai-orchestration-ingestion.md#5-adaptive-baseline-diagnostic-engine)).
6. **Plan Finalization:** The system presents the finalized **Living Mutable Plan**, showing the critical path to completion, daily milestones, and expected retention.

#### Journey 3: The Daily Deliberate Practice Session
1. **Pre-Study Priming (optional, 2 mins):** Minimalist visual focus target on screen to settle attention before work (hypothesis; see Claim Register).
2. **Due Reviews First:** FSRS-due retrieval probes are served before any new frontier concept (FR-6.2).
3. **Active Work Bout (default 45 mins, configurable):**
   * GenUI dynamically renders the required workspace (`FadedWorkedExample` or `SymbolicStepEditor`).
   * Learner writes/inputs algebraic steps via the virtual math keyboard.
   * SymPy verifies each step deterministically. Jev gates feedback: if correct, advance; if incorrect, trigger a Level 1 Socratic hint.
4. **Micro-Break:** After ~6 minutes of active work (default 360 s, configurable 5–7 min; see [Doc 03 §5.1](03-cognitive-engine-pedagogical.md#51-the-15-second-micro-break-wakeful-rest)), a full-screen **15-second `RestOverlay`** with a slow breathing pulse triggers. User looks away and rests. (Skip button available with a neutral explanation.)
5. **Post-Session Wakeful Rest (default 5–10 mins):** A low-stimulation rest screen suggests quiet wakefulness before switching to other screen activities.
6. **FSRS Scheduling:** Performance data updates each node's Stability ($S$) and Difficulty ($D$) in PostgreSQL; Retrievability ($R$) is computed on read.

---

### 4. Functional Requirements

#### Module 1: Ingestion & Knowledge Graph Engine (KGE)
* **FR-1.1: Parameter Ingestion:** Must accept free-text goals, structured syllabus uploads (PDF/text), target completion dates, and daily time constraints (in minutes). At least one of target date or daily budget is required; uploads are size-limited and treated as untrusted input.
* **FR-1.2: Two-Phase Graph Generation:**
  * *Phase 1 (Optimistic Draft):* Return a coarse-grained sequence within $< 2\text{ seconds}$ using fast LLM generation (`glm-5.3-flash`).
  * *Phase 2 (Deep Verification):* Asynchronous agent runs multi-source extraction, validates prerequisite dependencies, and updates the graph into atomic `(:Concept)` and `(:Skill)` nodes.
* **FR-1.3: Graph Topology:** Knowledge must be stored as a Directed Acyclic Graph (DAG) enforcing:
  * Prerequisite constraints, stored in one direction only (`PREREQUISITE_OF`: parent must be learned before child). "Requires" is the same edge read backwards.
  * Element interactivity weight (metadata tracking working memory load for that node).
* **FR-1.4: Source Licensing:** Deep research may only ingest openly licensed or public-standard sources (e.g. OpenStax CC-BY, Common Core State Standards) and must store attribution per node.

#### Module 2: Adaptive Diagnostic Engine (ADE)
* **FR-2.1: Graph-Based Adaptive Probing:** The diagnostic must not administer a linear test. Each probe is the node that best splits the set of still-uncertain nodes (Knowledge Space Theory; see [Doc 05 §5](05-ai-orchestration-ingestion.md#5-adaptive-baseline-diagnostic-engine)).
* **FR-2.2: Prerequisite Inference:** 
  * If a probe is solved with high fluency (measured by correctness and response latency), the node and all its ancestors are marked as mastered ($P(\text{Mastery}) \ge 0.95$).
  * If failed, the node and all its descendants are marked as not mastered.
* **FR-2.3: Diagnostic Cap:** Diagnostic must conclude within 3 to 5 probes (single source: [Doc 05 §5](05-ai-orchestration-ingestion.md#5-adaptive-baseline-diagnostic-engine)), establishing the learner's initial frontier without inducing fatigue.

#### Module 3: Component-Driven Generative UI (GenUI)
* **FR-3.1: Component Registry:** The client must maintain a pre-compiled registry of standard, mobile-first widgets:
  * `SymbolicStepEditor`: Multi-line algebraic input with inline validation indicators.
  * `VirtualMathKeyboard`: Custom touch keyboard (variables, exponents, fractions, square roots, operational symbols).
  * `FadedWorkedExample`: Scaffolded container where steps 1 to $N-1$ are pre-solved and step $N$ requires active input.
  * `FunctionPlotter`: Dynamic 2D coordinate grid with function sliders.
  * `SocraticDialogueBox`: Minimalist inline chat drawer restricted to single-question interactions.
  * `RestOverlay`: Full-screen 15-second offline replay visualizer.
* **FR-3.2: Typed Schema Contract:** UI states must be delivered from the backend as strict JSON conformant to the `GenUIWorkspacePayload` contract ([Doc 04 §3](04-system-architecture.md#3-component-driven-genui-schema-contract)). The client rejects payloads that fail validation.
* **FR-3.3: Client Resolution:** The client must resolve and render the JSON tree deterministically without evaluating arbitrary JavaScript or executing client-side `eval()`.

#### Module 4: Deterministic Mathematical Evaluation Engine (MEE)
* **FR-4.1: Symbolic Equivalence:** Must evaluate user mathematical expressions using SymPy on the backend. For expressions, a step is valid if:
  $$\text{simplify}(E_{\text{user}} - E_{\text{expected}}) == 0$$
  For equations, both sides are normalized to $\text{lhs} - \text{rhs}$ and compared up to a non-zero constant factor. Because `simplify` is not a complete decision procedure, a non-zero result is confirmed by numeric sampling before the step is marked invalid (see [Doc 04 §4](04-system-architecture.md#4-deterministic-math--sympy-worker-architecture)).
* **FR-4.2: AST Intermediate Step Validation:** The engine must parse user input into an Abstract Syntax Tree (AST) to verify that the student actually performed the intended structural operation (e.g., verifying that a student factored out a common term rather than simply re-typing the original expression).
* **FR-4.3: Zero LLM Math Grading:** Large Language Models must **never** be used to grade math correctness. Grading is 100% deterministic via SymPy/AST.
* **FR-4.4 (v1.2): Grader registry.** Non-math parts are graded server-side from a stored `answer_spec` by deterministic graders (choice, match, order, categorize, exact, cloze, numeric with units, speech match); only open answers use a temperature-0 rubric LLM with deterministic pre-checks and a per-session cost cap; code runs in the browser and is marked `decided_by = CLIENT`. Answer keys never reach the client ([Doc 10 §5, §6.4](10-multi-subject-spec.md)).
* **FR-4.5 (v1.2): Cited grounding.** Non-math lessons are researched on the web; every URL shown to the learner must be one the research step returned as a citation, and each lesson lists its sources.

#### Module 5: Cognitive Protocol & Session Runner (CPR)
* **FR-5.1: Accuracy-Band Calibration:** The session runner monitors rolling accuracy over the last $K = 20$ attempts. Above $0.88$, scaffolding is stripped (e.g., Faded Worked Example to blank derivation); below $0.75$, intermediate scaffolding steps are inserted. Thresholds and the full transition matrix are defined once in [Doc 03 §2.2](03-cognitive-engine-pedagogical.md#22-scaffolding-state-transition-matrix).
* **FR-5.2: Micro-Break Timer:**
  * Tracks cumulative active derivation time.
  * Triggers the `RestOverlay` after 360 s of active problem solving (configurable 5–7 min; [Doc 03 §5.1](03-cognitive-engine-pedagogical.md#51-the-15-second-micro-break-wakeful-rest)).
  * Enforces a 15-second countdown accompanied by a slow breathing cue.
  * Includes a "Skip" button. If clicked, displays: *"Short rests between practice help the brain consolidate what you just did. Skip this one?"* Skips are logged.
* **FR-5.3: Hint Ladder Escalation:**
  * *Attempt 1 Failure:* Level 1 Hint (Conceptual focus only; zero numbers/symbols).
  * *Attempt 2 Failure:* Level 2 Hint (Strategic approach suggested).
  * *Attempt 3 Failure:* Level 3 Hint (Pinpoints the exact operational error region; leaves final calculation to user).

#### Module 6: Memory Maintenance Engine (FSRS-6)
* **FR-6.1: DSR Parameter Tracking:** Every node in the Knowledge Graph maintains Difficulty ($D$), Stability ($S$), and Retrievability ($R$) variables per user.
* **FR-6.2: Scheduled Probes:** Daily sessions must query the FSRS-6 engine to inject due retrieval probes *before* introducing new frontier concepts.
* **FR-6.3: Power-Law Decay Calculation:** Retrievability must be calculated dynamically based on elapsed days $t$ using the FSRS-6 power function with trainable decay $w_{20}$:
  $$R(t,S) = \left(1 + \text{FACTOR} \cdot \frac{t}{S}\right)^{-w_{20}}, \quad \text{FACTOR} = 0.9^{-1/w_{20}} - 1$$
  Implemented via the maintained `fsrs` (py-fsrs) library; see [Doc 03 §1](03-cognitive-engine-pedagogical.md#1-the-dsr-memory-engine-fsrs-6-specification).

---

### 5. Non-Functional Requirements (NFRs)

#### 5.1 Performance & Latency
* **Jev Decision Latency:** $P95 < 150\text{ ms}$ target via the OpenRouter Decisions API (hard timeout 400 ms, then rule-based fallback).
* **SymPy Backend Evaluation:** $P95 < 200\text{ ms}$ execution time on standard container infrastructure.
* **First Contentful Paint (FCP):** $< 1.2\text{ s}$ on 4G mobile connections.
* **Client Frame Rate:** Steady $60\text{ fps}$ during canvas transitions and touch-keyboard interactions.

#### 5.2 Mobile-First Usability & Accessibility
* Touch targets on the virtual math keyboard must measure $\ge 48 \times 48\text{ px}$.
* High-contrast dark mode support by default (minimizes optical fatigue during extended study bouts).
* Fully accessible mathematical outputs formatted via standard MathML / KaTeX ARIA labels.

#### 5.3 Reliability & Data Integrity
* **Offline Resilience:** Active practice sessions must cache current state in browser `IndexedDB`. If the user loses network connectivity mid-session, local inputs are preserved and re-synchronized upon reconnection.
* **Deterministic Fallback:** If OpenRouter / Jev experiences an outage, times out, or returns a low-confidence answer, the system falls back to rule-based pedagogical state transitions without crashing the user session.

#### 5.4 Localization
* MVP ships in English and Spanish (both personas and the initial target market are Spanish-speaking). All UI copy lives in message catalogs from day one; Socratic prompts are generated in the learner's selected locale.
* Math notation follows the locale where it differs (e.g. decimal comma display), while evaluation always uses a canonical internal form.
* *Decision owner: product. If Spanish is deferred, keep the catalogs and ship English only.*

#### 5.5 Privacy & Security
* Secondary-school learners may be minors. Age gating, parental consent, and data-retention rules are defined in [Doc 04 §6](04-system-architecture.md#6-authentication-privacy--minors).

---

### 6. Out of Scope for Phase 1 (MVP)

The following capabilities are explicitly deferred to subsequent phases:
* **Ephemeral MicroVM Terminals (DevOps Engine):** Firecracker / Docker sandbox orchestration. *(v1.2: beginner Python/JS run in an in-browser Pyodide / JS worker instead; server sandboxes stay out of scope.)*
* **Real-Time Speech & GOP Analysis (Language Engine):** WebRTC audio pipelines and phoneme forced alignment. *(v1.2: language lessons use browser Web Speech TTS/recognition with self-rating fallback; GOP stays out of scope.)*
* **B2B / Multi-Tenant Enterprise Portals:** Team analytics, enterprise single sign-on (SSO), and manager dashboards.
* **P2P Social Features:** Leaderboards, study groups, public chat feeds (omitted intentionally to prevent vanity engagement loops).

---

### 7. KPI Measurement Protocol

KPIs are only claimed once measured in the Phase P5 pilot ([Doc 08](08-delivery-phases.md)).

| KPI | Measurement | Baseline / Comparison |
| :--- | :--- | :--- |
| Time-to-Mastery Velocity | Active study minutes (from `attempts` + `session_logs`) until the learner passes a held-out mastery test on the target topic set (≥80% on fresh, SymPy-verified items, no hints). | Randomized control arm of the pilot doing linear self-study on the same topic set (textbook chapter + worked solutions), same mastery test. |
| Long-Term Retention | Accuracy on unannounced retrieval probes for mastered nodes at day 14 and day 30 after mastery. | Same probes for the control arm; FSRS predicted $R$ is logged alongside to check calibration. |
| Cognitive Efficiency Index | Ratio of time with an active input widget focused vs. time on read-only content, from client telemetry. | None; absolute target 4:1. |
| System Latency | P95 from server spans (SymPy, Jev) and client performance marks (GenUI render). | NFR thresholds in §5.1. |

**Pilot design (minimum viable):**
* 30–60 learners matched to the personas, randomized 1:1 to product vs. control, stratified by diagnostic score.
* Topic set: the seeded Algebra DAG from Phase P0 (~20 nodes).
* Pre-registered primary outcome: time-to-mastery. Secondary: 14/30-day retention.
* Report effect sizes with confidence intervals; with this sample, treat results as directional, not confirmatory.

---

### 8. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.1 | 2026-09-24 | MVP PRD (math). |
| 1.2 | 2026-10-09 | Multi-subject ([Doc 10](10-multi-subject-spec.md)): objective widened (§1.1); FR-4.4 grader registry and FR-4.5 cited grounding; §6 notes the in-browser code runner and Web Speech in place of the deferred engines. Math-specific FRs (Module 4, math keyboard, KaTeX a11y) apply to math profiles. The pilot (§7) still uses the algebra DAG. |
