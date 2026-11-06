# PROJECT COGNITIVE OS
## Document 07: Epic & User Stories
**Version:** 1.1 (2026-10-09: multi-subject scope note; stories unchanged)  
**Scope:** MVP (Phase 1: Mathematics). *Multi-subject work (subject profile, graders, family packs, citations) is tracked as tickets MS-1.1 … MS-5.3 in [Doc 11](11-multi-subject-execution-plan.md), not as stories here; math-specific acceptance criteria below apply to math profiles.* Sources: [Doc 02 PRD](02-product-requirements.md), [Doc 03](03-cognitive-engine-pedagogical.md), [Doc 04](04-system-architecture.md), [Doc 05](05-ai-orchestration-ingestion.md), [Doc 06](06-frontend-architecture-genui.md). Delivery order: [Doc 08](08-delivery-phases.md).

---

### Conventions
* **Personas:** **Carlos**, exam candidate with 18 days and 45 min/day. **Elena**, STEM pivot who needs to skip what she knows. **Ops**, the internal team (engineering and content).
* **Size:** S ≈ 1–2 days, M ≈ 3–5 days, L ≈ 1–2 weeks (one engineer).
* **Trace:** FR/NFR IDs from Doc 02; `J1`–`J3` = Doc 02 journeys.
* **Definition of Done (every story):** acceptance criteria pass; the one runnable check named in the story exists and passes in CI; telemetry events emitted; copy in `en` and `es` catalogs; no accessibility regressions (axe clean on touched screens).

---

## EPIC-01: Cognitive OS MVP, Mastery-Based Math Engine

**Goal:** A learner can set a math goal, get an adaptive diagnostic and plan, and practice with deterministic step checking, calibrated scaffolding, Socratic hints, rest breaks, and FSRS-scheduled reviews on a mobile PWA.

**Success measure:** KPIs in [Doc 02 §1.2](02-product-requirements.md#12-core-success-metrics-kpis), measured by the protocol in [Doc 02 §7](02-product-requirements.md#7-kpi-measurement-protocol).

| Feature | Name | Phase |
| :--- | :--- | :--- |
| F1 | Deterministic Math Evaluation | P1 |
| F2 | Memory Engine (FSRS-6) | P1 |
| F3 | GenUI Renderer & Math Widgets | P2 |
| F4 | Session Runner & Cognitive Protocol | P2 |
| F5 | AI Orchestration (Jev + System 2) | P3 |
| F6 | Ingestion & Knowledge Graph | P0 (seed), P4 (pipeline) |
| F7 | Adaptive Diagnostic | P4 |
| F8 | Quick Socratic Mode | P3 |
| F9 | Platform: Auth, Privacy, Offline, Telemetry | P0, P5 |

---

### F1: Deterministic Math Evaluation

**US-1.1: Check a step for algebraic equivalence** · Carlos · M · FR-4.1, FR-4.3  
*As Carlos, I want each step I write checked instantly and correctly, so that I never trust a wrong step or get told a right one is wrong.*
* Given an expected expression step, when I submit an equivalent expression (e.g. `2(x+2)` vs `2x+4`), then the result is `is_equivalent = true`.
* Given an expected equation `2x = 6`, when I submit `x = 3`, then it is equivalent; when I submit `x = 4`, it is not.
* Given `simplify` returns non-zero but the expressions are numerically equal at 8 random points, then the step is treated as equivalent and logged for review.
* No LLM call occurs anywhere in this path.
* *Check:* `workers/test_math_evaluator.py`.

**US-1.2: Detect the right value with the wrong structure** · Elena · M · FR-4.2  
*As Elena, I want to be told when my answer is equal but I didn't do the asked operation, so that I actually practice the skill.*
* Given a step with `operation = FACTOR_COMMON_TERM`, when I submit `2x + 4` for `2(x + 2)`, then the verdict is `CORRECT_VALUE_WRONG_STRUCTURE`.
* Given the same step, when I submit `2(x + 2)`, then the verdict is `STEP_VERIFIED`.
* Supported operations for MVP: `FACTOR_COMMON_TERM`, `DISTRIBUTE`, `COMBINE_LIKE_TERMS`, `ISOLATE_VARIABLE`, `DIVIDE_BOTH_SIDES`.
* *Check:* one parametrized test per operation.

**US-1.3: Evaluation is fast and safe under bad input** · Ops · M · NFR 5.1, FR-4.1
*As Ops, I want evaluation isolated with hard limits, so that hostile or pathological input can't slow down or crash the service.*
* Given input over 500 chars, then the response is `INPUT_TOO_LONG` without parsing.
* Given an expression that takes longer than 150 ms, then the response is `EVALUATION_TIMEOUT` and the pool stays usable.
* Given 50 concurrent typical submissions, then P95 < 200 ms on the target container size.
* The expected step is always loaded server-side from `items`; the request has no answer field.
* *Check:* load script in `workers/bench_evaluator.py` reporting P95.

---

### F2: Memory Engine (FSRS-6)

**US-2.1: Schedule each node with FSRS-6** · Carlos · M · FR-6.1, FR-6.3
*As Carlos, I want reviews scheduled just before I would forget, so that I keep what I learned without wasting time.*
* Given a completed item with grade G, when the attempt is saved, then `user_node_states` is updated via py-fsrs (D, S, due date, state), with $R$ computed on read.
* Given default weights and `target_retention_rate = 0.90`, then intervals match py-fsrs output exactly.
* Given a user with `fsrs_weights` set, then those weights are used.
* *Check:* test comparing our wrapper against py-fsrs for a fixed review history.

**US-2.2: Due reviews come before new material** · Carlos · S · FR-6.2, J3
*As Carlos, I want due reviews first each day, so that old skills don't decay while I learn new ones.*
* Given 3 nodes due today and a frontier node, when a session starts, then the 3 due probes are served before the frontier node.
* Given more due reviews than the daily budget allows, then reviews are ordered by lowest current $R$ and the rest carry over.

**US-2.3: Derive the FSRS grade from attempt telemetry** · Ops · S · FR-6.1, Doc 03 §1.1
*As Ops, I want grades derived from hints, correctness and latency, so that learners never self-rate.*
* Given an item finished with a Level 3 hint, then grade = 1; with a Level 1–2 hint or slow latency, then 2; correct with no hints, then 3; fast and no hints, then 4 (rule-engine mapping, Doc 05 §6.1).
* When Jev supplies a confident grade, it is used instead; `attempts.decided_by` records which.

**US-2.4: Personalize FSRS weights** · Ops · M · FR-6.1
*As Ops, I want to re-optimize a user's FSRS weights once they have enough history, so that scheduling fits their memory.*
* Given a user with ≥ 400 reviews, when the weekly job runs, then py-fsrs's optimizer produces 21 weights stored in `users.fsrs_weights`.
* Given the new weights predict worse log-loss on the user's last 20% of reviews than the current ones, then they are discarded.

---

### F3: GenUI Renderer & Math Widgets

**US-3.1: Render a validated workspace payload** · Carlos · M · FR-3.2, FR-3.3
*As Carlos, I want the practice screen to appear instantly and never break, so that I stay focused.*
* Given a valid `GenUIWorkspacePayload`, then widgets render in order within 30 ms after data arrives (P95, mid-range Android).
* Given a payload that fails Zod validation, then an inline error is shown, a telemetry event is sent, and no widget renders.
* Given an unknown widget type, then the build fails (registry typed on `CanvasWidgetType`).
* No `eval`, `new Function`, or raw-HTML LaTeX rendering exists in the client (lint rule).
* *Check:* renderer unit test with one valid and one invalid payload.

**US-3.2: Write steps in a derivation editor** · Carlos · M · FR-3.1
*As Carlos, I want to type each step on its own line and submit with Enter, so that the app checks exactly the step I'm on.*
* Locked steps render via KaTeX with MathML; the active step is a MathLive field.
* Pressing Enter or ⏎ submits `SUBMIT_STEP` with the step index and LaTeX; nothing submits on intermediate keystrokes.
* Valid/invalid status icons have accessible labels.

**US-3.3: Touch-first math keyboard** · Carlos · S · FR-3.1, NFR 5.2
*As Carlos on my phone, I want a math keyboard with big keys, so that I can type fractions and exponents without fighting the OS keyboard.*
* Keys ≥ 48×48 px; algebra layout per Doc 06 §3.3; ⏎ submits.
* Implemented with MathLive's virtual keyboard and a custom layout (no custom keypad).

**US-3.4: Faded worked example** · Elena · M · FR-3.1, Doc 03 §2.2
*As Elena, I want worked examples where only the next step is blank, so that I learn the pattern without being overwhelmed.*
* Scaffold level 1: full worked example with inline gaps. Level 2: steps 1..N-1 shown, step N active. Level 3: blank `SymbolicStepEditor`.
* Justification text for locked steps is shown when present.

**US-3.5: Function plotter** · Elena · M · FR-3.1
*As Elena, I want to see and tweak function graphs, so that I build intuition for how parameters change the curve.*
* Plots 1–3 expressions over the given domain; sliders redraw at 60 fps on a mid-range phone.
* Provides a text description of intercepts/asymptotes for screen readers.

**US-3.6: Socratic hint drawer** · Carlos · S · FR-3.1, FR-5.3
*As Carlos, I want a single short hint next to the step I got wrong, so that I can fix it myself.*
* Shows one hint (≤ 240 chars, plain text) and highlights `highlightElementId`; announced via `aria-live`.
* No free-form chat input in practice mode.

---

### F4: Session Runner & Cognitive Protocol

**US-4.1: Calibrate scaffolding to my accuracy** · Carlos · M · FR-5.1
*As Carlos, I want the help to fade when I'm doing well and come back when I struggle, so that practice stays challenging but doable.*
* Given rolling accuracy over the last 20 attempts > 0.88, then scaffold level rises per the Doc 03 §2.2 matrix; < 0.75, it drops; at level 1 below 0.75, the runner steps down to the immediate prerequisite node.
* Given fewer than 5 attempts, no promotion occurs.
* *Check:* table-driven test covering every cell of the matrix.

**US-4.2: Hint ladder** · Carlos · S · FR-5.3
*As Carlos, I want hints that get more specific only if I keep failing, so that I do as much of the thinking as possible.*
* Attempt 1 fail → tier 1; attempt 2 → tier 2; attempt 3 → tier 3. Tier is set by code, never by an LLM.
* A step that needed tier 3 counts as $a_i = 0$ and grade 1.

**US-4.3: Micro-break after sustained work** · Carlos · M · FR-5.2, Doc 03 §5.1
*As Carlos, I want a short forced pause after several minutes of work, so that I don't grind without letting things settle.*
* Given 360 s of cumulative active time, when my current step is submitted, then `RestOverlay` shows for 15 s (not mid-step).
* The countdown uses a deadline timestamp; `onComplete` fires once.
* Skip shows the neutral confirmation (no "40%" claim); skips increment `micro_breaks_skipped`.
* Under `prefers-reduced-motion`, the breathing animation is static.
* *Check:* component test with fake timers asserting a single `onComplete`.

**US-4.4: Post-session wakeful rest** · Carlos · S · J3, Doc 03 §5.2
*As Carlos, I want a calm end to each session, so that I stop before I get tired and step away from screens.*
* After the planned session, a summary screen then a rest screen shows; new items are paused for 10 min by default, with one-tap override.
* Optional `NSDRPlayer` audio; never autoplays.

**US-4.5: Daily session plan within my time budget** · Carlos · M · J2 step 6, J3
*As Carlos, I want each day's session to fit my 45 minutes, so that I can rely on the plan.*
* Given `daily_budget_mins`, the runner plans due reviews + frontier items to fill ≤ budget using per-item time estimates.
* Given a deadline, the plan's critical path is recomputed after each session; if it no longer fits, the path screen says so and suggests a new daily budget.

---

### F5: AI Orchestration (Jev + System 2)

**US-5.1: Classify step errors with Jev** · Ops · M · FR-5.3, Doc 05 §2.1
*As Ops, I want error types classified with calibrated probabilities, so that hints target the actual mistake.*
* One Decisions API call per failed step with `evaluation_verdict` (choice) and `recommended_fsrs_grade` (score) questions against `typesafe/jev-1.13`.
* The answer is used only if confidence ≥ threshold (0.70 choice / 0.60 score); raw answers and `usage.cost` are stored.
* P95 latency is measured and reported; target < 150 ms, hard timeout 400 ms.

**US-5.2: Rule-engine fallback** · Carlos · M · NFR 5.3, Doc 05 §6.1
*As Carlos, I want practice to keep working when the AI is slow or down, so that my session is never blocked.*
* Given Jev times out, errors, or is low-confidence, then the rule engine decides verdict and grade, and `decided_by = 'RULES'`.
* Given Jev error rate > 20% over 1 minute, then Jev calls are skipped for 60 s (circuit breaker).
* *Check:* test with a mocked Jev client returning timeout, error, and low confidence.

**US-5.3: Generate one Socratic hint** · Carlos · M · FR-5.3, Doc 05 §3
*As Carlos, I want a hint that points me in the right direction without giving the answer, so that I learn to fix it myself.*
* System 2 (`deepseek/deepseek-v4.1-flash`, fallback `z-ai/glm-5.3-flash`) returns `SocraticInterventionPayload` at the code-chosen tier, in my locale.
* The answer-leak check rejects any hint containing the expected step or final answer; after one retry, a templated hint is used.
* P95 hint latency < 1.2 s.

**US-5.4: Cost tracking per session** · Ops · S · Doc 04 §7
*As Ops, I want LLM cost per session recorded, so that we can verify the low-cost claim and set credit prices.*
* Jev `usage.cost` and System 2 costs are summed into `session_logs.llm_cost_usd`.
* A dashboard shows cost per session and the share of attempts resolved without System 2.

---

### F6: Ingestion & Knowledge Graph

**US-6.1: Seed the Algebra graph and item bank** · Ops · L · FR-1.3, Doc 03 §6
*As Ops, I want a hand-built Algebra DAG with verified items, so that the deterministic core ships before any AI.*
* ~20 Algebra nodes with `PREREQUISITE_OF` edges, each with ≥ 10 items whose steps pass SymPy verification.
* Seed script is idempotent (upsert by slug).
* *Check:* seed validation test: DAG is acyclic; every item step verifies.

**US-6.2: Create a learning path with an instant preview** · Carlos · M · FR-1.1, FR-1.2, J2
*As Carlos, I want to type my goal and deadline and see a plan outline immediately, so that I know the app understood me.*
* Given a goal and at least one of deadline or daily budget, then a draft of 4–6 modules returns within 1.5 s (P95).
* Given neither deadline nor budget, then validation fails with a clear message.
* Draft modules are matched to existing nodes by slug/embedding before new drafts are created.

**US-6.3: Stream the refined graph live** · Carlos · M · FR-1.2, J2
*As Carlos, I want the plan to fill in as research completes, so that I can start without waiting.*
* SSE emits `node_validated` and `graph_complete` events; the client resumes with `Last-Event-ID` after a drop.
* Draft nodes are replaced in place without resetting my view.

**US-6.4: Compile a valid DAG** · Ops · M · FR-1.3, Doc 05 §4
*As Ops, I want generated graphs forced acyclic and minimal, so that learning order is always well-defined.*
* Cycles are broken by removing the lowest-weight edge; removed edges are logged for review.
* Transitive edges are pruned; node attributes survive.
* *Check:* `pipeline/test_dag_compiler.py`.

**US-6.5: Only licensed sources, with attribution** · Ops · M · FR-1.4
*As Ops, I want ingestion restricted to openly licensed sources, so that we don't infringe content rights.*
* The retriever allowlists sources (OpenStax, Common Core, user uploads, CC-BY/public domain); Khan Academy and MIT OCW are blocked.
* Every generated node has `source_url`, `source_license`, `source_attribution`; the path screen shows attributions.

**US-6.6: Generate and verify items for new nodes** · Ops · L · Doc 03 §6
*As Ops, I want new nodes to get practice items automatically but safely, so that any goal can be practiced.*
* System 2 drafts items; each step must pass SymPy; failing items are rejected.
* A node is not served until it has ≥ 5 `VERIFIED` items.

**US-6.7: Upload a syllabus** · Carlos · M · FR-1.1
*As Carlos, I want to upload my course syllabus, so that the plan matches my actual exam.*
* PDF/text up to 10 MB; parsed as text only; stored only until the graph is built.
* Disabled for accounts under the consent age (Doc 04 §6.2).

---

### F7: Adaptive Diagnostic

**US-7.1: Find my starting point in 3–5 questions** · Elena · M · FR-2.1, FR-2.3, J2
*As Elena, I want a short diagnostic that skips what I already know, so that I don't waste time on basics.*
* Each probe is the UNKNOWN node maximizing min(ancestors, descendants) (Doc 05 §5.1).
* The diagnostic stops after 5 probes or when nothing is UNKNOWN (minimum 3).
* *Check:* `diagnostic/test_probe_selection.py`.

**US-7.2: Infer mastery from each answer** · Elena · S · FR-2.2
*As Elena, I want a correct fluent answer to credit the prerequisites too, so that I skip everything beneath it.*
* Fluent pass ($F \ge 0.80$) → node + ancestors `p_mastery = 0.95`; fail → node + descendants NOT_MASTERED; slow correct → node only, `p_mastery = 0.70`.
* The resulting frontier is shown on the path screen.

---

### F8: Quick Socratic Mode

**US-8.1: Ask a one-off question** · Elena · M · J1
*As Elena, I want to ask a single math question and get guided to the insight, so that I can unblock myself without starting a course.*
* Jev classifies intent (Doc 05 §2.2); `OFF_TOPIC` gets a polite refusal.
* The answer is a single canvas (step breakdown + one Socratic question) and a follow-up input; at most 3 exchanges.
* Nothing is written to `user_node_states` or any learning path (`session_logs.path_id = NULL`).

---

### F9: Platform: Auth, Privacy, Offline, Telemetry

**US-9.1: Sign in without a password** · Carlos · M · Doc 04 §6.1
*As Carlos, I want to sign in with email link or Google/Apple, so that I don't manage another password.*
* JWTs are short-lived; rate limits apply per user and IP.

**US-9.2: Age screen and guardian consent** · Ops · M · NFR 5.5, Doc 04 §6.2
*As Ops, I want under-age users to require guardian consent, so that we comply with COPPA/GDPR Art. 8.*
* Neutral birth-year screen at sign-up; under the market's consent age, activation waits for verifiable guardian consent.
* BYO keys and uploads are disabled for minors.
* Legal review sign-off is recorded before launch in each market.

**US-9.3: Delete my account and data** · Carlos · S · Doc 04 §6.3
*As Carlos, I want to delete my account, so that my data is gone when I leave.*
* Deletion hard-deletes all user rows within 30 days; confirmation email sent.

**US-9.4: Bring my own API key** · Elena · S · Doc 01 §7, Doc 04 §6.3
*As Elena, I want to use my own OpenRouter key, so that I pay only for my compute.*
* Key is encrypted with KMS envelope encryption, never logged or returned; a test call validates it on save.

**US-9.5: Keep practicing offline** · Carlos · L · NFR 5.3
*As Carlos on a bad connection, I want my session to continue offline, so that I lose no work.*
* Session state and attempts are cached in IndexedDB; locked steps and verified items for the current node are available offline.
* Offline submissions are queued with idempotency keys and re-evaluated server-side on reconnect; the server result wins.
* Offline scheduling uses ts-fsrs; server state replaces it after sync.

**US-9.6: Installable, fast PWA** · Carlos · M · NFR 5.1, NFR 5.2
*As Carlos, I want the app to load fast on 4G and install to my home screen, so that starting a session is instant.*
* FCP < 1.2 s on emulated 4G (Lighthouse mobile); manifest + service worker installable; dark mode by default.

**US-9.7: English and Spanish** · Carlos · M · NFR 5.4
*As Carlos, I want the app in Spanish, so that I understand every instruction.*
* All copy from `messages/en` and `messages/es`; locale stored on `users.locale`; hints generated in that locale.

**US-9.8: Latency and pedagogy dashboards** · Ops · M · NFR 5.1, Doc 04 §7
*As Ops, I want traces and dashboards for every NFR, so that regressions are caught before users notice.*
* OpenTelemetry spans for SymPy, Jev, System 2, DB; alerts per Doc 04 §7.
* Pedagogy panel: fallback rate, scaffold transitions, skip rate, FSRS predicted vs. observed recall.

**US-9.9: Run the KPI pilot** · Ops · L · Doc 02 §7
*As Ops, I want a randomized pilot against a self-study control, so that our KPI claims are measured, not assumed.*
* 30–60 learners, 1:1 randomized, stratified by diagnostic score, pre-registered primary outcome.
* Report time-to-mastery and 14/30-day retention with confidence intervals.
* Includes a micro-break on/off arm or within-subject comparison to test the Claim Register hypothesis.

---

### Traceability Matrix

| Requirement | Stories |
| :--- | :--- |
| FR-1.1 Parameter ingestion | US-6.2, US-6.7 |
| FR-1.2 Two-phase graph generation | US-6.2, US-6.3 |
| FR-1.3 Graph topology | US-6.1, US-6.4 |
| FR-1.4 Source licensing | US-6.5 |
| FR-2.1 Adaptive probing | US-7.1 |
| FR-2.2 Prerequisite inference | US-7.2 |
| FR-2.3 Diagnostic cap | US-7.1 |
| FR-3.1 Component registry | US-3.2, US-3.3, US-3.4, US-3.5, US-3.6 |
| FR-3.2 Typed schema contract | US-3.1 |
| FR-3.3 Client resolution (no eval) | US-3.1 |
| FR-4.1 Symbolic equivalence | US-1.1, US-1.3 |
| FR-4.2 AST structure validation | US-1.2 |
| FR-4.3 Zero LLM grading | US-1.1 |
| FR-5.1 Accuracy-band calibration | US-4.1 |
| FR-5.2 Micro-break timer | US-4.3 |
| FR-5.3 Hint ladder | US-4.2, US-3.6, US-5.1, US-5.3 |
| FR-6.1 DSR tracking | US-2.1, US-2.3, US-2.4 |
| FR-6.2 Due probes first | US-2.2 |
| FR-6.3 Power-law decay | US-2.1 |
| NFR 5.1 Performance & latency | US-1.3, US-5.1, US-9.6, US-9.8 |
| NFR 5.2 Mobile usability & accessibility | US-3.3, US-9.6, (DoD for all UI stories) |
| NFR 5.3 Reliability, offline & fallback | US-5.2, US-9.5 |
| NFR 5.4 Localization | US-9.7 |
| NFR 5.5 Privacy & security | US-9.1, US-9.2, US-9.3, US-9.4 |
| J1 Quick Socratic | US-8.1 |
| J2 Path creation | US-6.2, US-6.3, US-7.1, US-4.5 |
| J3 Daily session | US-2.2, US-4.1–US-4.5 |
| KPI protocol (Doc 02 §7) | US-5.4, US-9.9 |
