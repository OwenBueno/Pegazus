# PROJECT COGNITIVE OS (Working Title)
## Document 01: Executive Summary & Project Charter

---

### 1. Vision & Mission Statement
**Cognitive OS** is a domain-agnostic, mastery-based adaptive learning platform designed to maximize human learning speed and long-term retention. 

By replacing engagement-driven subscription traps (streaks, gamified vanity XP, artificial cooldown timers) with an infrastructure rooted strictly in **neurobiology, cognitive load theory, and high-speed probabilistic decision models (Jev)**, the platform shifts the core metric of EdTech from *Time Spent on App* to *Time to Verifiable Mastery*.

The platform treats human knowledge not as linear video playlists, but as a **living, dynamic Directed Acyclic Graph (DAG)**. It adapts to any curriculum, exam, or career goal on the fly, autonomously compiling custom learning paths that meet the learner precisely at their Zone of Proximal Development (ZPD).

---

### 2. The Problem: The EdTech Dark Pattern Crisis
Modern commercial educational platforms operate on business incentives fundamentally misaligned with cognitive science:
* **The Fluency Heuristic & Illusion of Competence:** Video-based and multiple-choice platforms exploit passive recognition. Learners feel like they understand the material while their brains fail to encode durable schemas, resulting in rapid forgetting.
* **Retention-Maximizing Dark Patterns:** Subscription models prioritize Monthly Active Users (MAU) and churn reduction. Features like streak freezes, energy mechanics, and bloated curricula are engineered to artificially prolong the billing cycle rather than accelerate learning completion.
* **Static, Siloed Courses:** Current solutions isolate disciplines (e.g., Duolingo for languages, Brilliant for math, various bootcamps for coding). None provide a unified cognitive engine that dynamically handles the multi-domain reality of technical mastery.

---

### 3. Core Scientific Moat: The Neurobiological Engine
Cognitive OS builds research-backed learning mechanisms directly into the software. Evidence strength varies; every claim is graded in the [Claim Register](03-cognitive-engine-pedagogical.md#7-claim-register) and weaker ones are treated as hypotheses to validate in the pilot.

* **Desirable-Difficulty Calibration (the "85% Rule" heuristic):** Real-time calibration scales challenge so the learner stays at roughly 75–88% accuracy. The target comes from [Wilson et al., 2019](https://www.nature.com/articles/s41467-019-12552-4), who derived an ~85% optimum for gradient-descent learners on binary tasks. Transfer to multi-step human math learning is untested, so the band is a tunable heuristic, not a law.
* **Micro-Break Wakeful Rest:** The UI embeds short (default 15-second) wakeful rest pauses after ~6 minutes of active work. Motivated by [Buch et al., 2021](https://doi.org/10.1016/j.celrep.2021.109193), who observed ~20x time-compressed hippocampo-neocortical replay during 10-second rests in a motor-sequence task, and found it predicted skill gains (correlational; not yet shown for math).
* **Modern Memory Modeling (FSRS-6):** Implements the DSR model of memory—Difficulty ($D$), Stability ($S$), and Retrievability ($R$)—with the 21-parameter [FSRS-6](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm) scheduler and its trainable power-law forgetting curve. FSRS outperforms SM-2 at predicting recall in the open [SRS benchmark](https://github.com/open-spaced-repetition/srs-benchmark); the review-load saving for this product will be measured, not assumed.
* **Cognitive Load Theory & Faded Worked Examples:** Complex tasks are dynamically scaffolded; intermediate steps are progressively removed ("faded") as the learner demonstrates mastery ([Sweller, 1988](https://doi.org/10.1207/s15516709cog1202_4); [Renkl & Atkinson, 2003](https://doi.org/10.1207/S15326985EP3801_3)).
* **Post-Session Wakeful Rest:** A default 5–10 minute low-stimulation pause after each session. Brief post-learning wakeful rest improves retention of verbal material ([Dewar et al., 2012](https://doi.org/10.1177/0956797612441220)); the NSDR framing is a hypothesis.

---

### 4. Architectural Innovation: Dual-Process AI & GenUI

The platform abandons the standard, high-latency approach of using a single large conversational LLM to handle everything. Instead, it deploys a **Dual-Process AI Architecture**:

```
                       [ Learner Action / Input ]
                                   │
                                   ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ SYSTEM 1: JEV (TypeSafe decision model via OpenRouter)          │
  │ - Latency target: <150ms (to be measured)                       │
  │ - Cost: $0.042 / M input tokens; output tokens free             │
  │ - Non-generative, typed answers (Choice, Noul, Score)           │
  │ - Evaluates errors, gates Socratic hints, selects UI layout     │
  └───────────────────────────────┬─────────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
  [ Advance / Silent Pass ]                      [ Complex Socratic Intervention ]
  - Pure GenUI re-render                         - Calls System 2 (DeepSeek / GLM)
  - Zero LLM generation cost                     - Generates single targeted prompt
```

#### Component-Driven Generative UI (GenUI):
The platform does not generate raw code on the fly. It maintains a robust, pre-built library of mobile-first UI primitives (`SymbolicStepEditor`, `FunctionPlotter`, `FadedWorkedExample`, `VirtualMathKeyboard`, `RestOverlay`). 
Jev returns typed decisions (verdict, scaffold action, hint tier); the backend maps those decisions to a **typed JSON component contract** that the client validates and renders, composing domain-specific workspaces in under 200ms without runtime code generation.

---

### 5. Product Lifecycle: "Create on the Way"

```
[ User Entry ] ──► Choice: Quick Socratic Mode OR Path of Learning Mode
                                                    │
    ┌───────────────────────────────────────────────┘
    ▼
[ Path Configuration ] ──► Inputs Goal, Target Date / Daily Time Budget, Optional Docs
    │
    ▼
[ Instant Draft + Deep Research ] ──► Immediate preview shown in 1.5s; Agent refines 
    │                                 authoritative DAG (curriculum/exams) in background
    ▼
[ Baseline Diagnostic ] ──► Fast Graph-Binary Search (3–5 questions) pinpoints ZPD
    │
    ▼
[ The Living Mutable Plan ] ──► Critical-path mathematical schedule generated & saved
    │
    ▼
[ Deliberate Practice Loop ] ──► Focus bouts (default 45 min) with 15s micro-breaks
    │
    ▼
[ Real-Time Mutation ] ──► Plan dynamically recalculates if user accelerates or struggles
```

---

### 6. MVP Scope (Phase 1 Target: Mathematics)
> **Superseded (2026-10-09):** the engine now teaches any subject a learner names (language, sciences, humanities, programming, math…) via a confirmed **subject profile**, a two-axis component catalog and a grader registry; lessons are grounded in web research with citations. Math stays the deepest pack (SymPy step checking). See [Doc 10](10-multi-subject-spec.md) and [Doc 11](11-multi-subject-execution-plan.md). The text below records the original MVP rationale.

To test and validate the end-to-end engine before expanding into DevOps or language acquisition, the MVP will focus exclusively on **Secondary to College-Level Mathematics** (Algebra, Pre-Calculus, Calculus foundations):
* **Why Math First?** Highly structured, deterministic, and ideal for proving:
  1. Deterministic step validation via **SymPy** and Abstract Syntax Tree (AST) comparison (preventing LLM math hallucinations).
  2. The efficacy of **Faded Worked Examples**.
  3. Real-time **Component-Driven GenUI** assembly on mobile screens.
* **Platform Delivery:** Mobile-first, responsive Progressive Web App (PWA) built on Next.js 16, Tailwind CSS v4, and Python (FastAPI).

---

### 7. Ethical Business Model & Sustainability
The platform rejects predatory subscription mechanics:
* **Infrastructure Cost Efficiency:** Jev-driven UI routing and deterministic grading resolve up to 90% of user interactions without calling frontier LLMs, dropping operational compute costs by orders of magnitude.
* **Transparent Compute Metering:** Core curriculum access is open; advanced cloud resources (ephemeral sandboxes, high-volume LLM inference) are funded via non-expiring compute credits or Bring-Your-Own-API-Key (BYO-API) configurations.
* **Pay-Per-Mastery:** Premium monetization is linked directly to authenticated, cheat-resistant assessment verification and micro-credentials, directly aligning company revenue with student success.

---

### 8. Project Documentation Roadmap
To engineer this system systematically, we will produce the following foundational documents in sequence:

1. **[Document 01: Executive Summary & Project Charter](01-executive-summary.md)** *(Current)*
2. **[Document 02: Product Requirements Document (PRD)](02-product-requirements.md)** *(User personas, journeys, functional/non-functional specs, KPI measurement protocol)*
3. **[Document 03: Cognitive Engine & Pedagogical Specification](03-cognitive-engine-pedagogical.md)** *(FSRS-6 memory model, 85% calibration heuristic, AST error-grading rules, rest-screen mechanics, item bank, claim register)*
4. **[Document 04: System Architecture & Data Schemas](04-system-architecture.md)** *(Database models, Knowledge Graph DAG schema, GenUI JSON contracts, API endpoints, privacy, observability)*
5. **[Document 05: AI Orchestration & Ingestion Pipeline](05-ai-orchestration-ingestion.md)** *(Jev decision questions, Socratic guardrails, Deep Research agent workflow, adaptive diagnostic, OpenRouter routing)*
6. **[Document 06: Frontend Architecture & GenUI Component Catalog](06-frontend-architecture-genui.md)** *(Next.js project setup, mobile-first math primitives, MathLive/KaTeX integration)*
7. **[Document 07: Epic & User Stories](07-epics-user-stories.md)** *(EPIC-01, features F1–F9, stories with acceptance criteria, traceability matrix)*
8. **[Document 08: Delivery Phases](08-delivery-phases.md)** *(Phases P0–P6 with goals, exit criteria, risks, dependencies)*
9. **[Document 09: UI / UX Specification](09-ui-ux-specification.md)** *(Screen inventory, design system, GenUI widget UX, a11y, i18n, phase mapping)*
10. **[Document 10: Multi-Subject Migration Specification](10-multi-subject-spec.md)** *(Subject profile, two-axis catalog, graders, citations)*
11. **[Document 11: Multi-Subject Execution Plan](11-multi-subject-execution-plan.md)** *(Tickets MS-1.1 … MS-5.3)*

---

### 9. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.0 | 2026-09-24 | Charter (math MVP). |
| 1.1 | 2026-10-09 | Multi-subject scope: §6 marked superseded, Docs 10–11 added to the roadmap. |
