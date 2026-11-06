# PROJECT COGNITIVE OS
## Document 03: Cognitive Engine & Pedagogical Specification
**Version:** 1.2 (multi-subject; see §8)  
**Phase:** Core Engine & Mathematical Domain (math is now one subject pack; Doc 10)  
**Target:** Algorithmic Runtime, Psychometric State Machines, & Deterministic Evaluators

---

### 1. The DSR Memory Engine (FSRS-6 Specification)

The cognitive engine tracks and schedules every atomic node in the user's personal Knowledge Graph using the **DSR (Difficulty, Stability, Retrievability) Three-Component Model of Memory**, utilizing the 21-parameter Free Spaced Repetition Scheduler (FSRS-6).

```
                 ┌──────────────────────────────────────┐
                 │       LEARNER ATTEMPTS PROBE         │
                 └──────────────────┬───────────────────┘
                                    │
                     [ Evaluated Grade: G ∈ {1,2,3,4} ]
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
     [ RECALL SUCCESS (G ≥ 2) ]                      [ LAPSE (G = 1) ]
            │                                               │
   Update Stability:                               Update Stability:
   S' = S_r'(D, S, R, G)                           S' = S_f'(D, S, R)
            │                                               │
            └───────────────────────┬───────────────────────┘
                                    │
                     Update Difficulty: D' = D'(D, G)
                                    │
                                    ▼
                     Calculate Optimal Next Interval:
                     I(S', r_target) = (S'/FACTOR) * (r_target^(-1/w20) - 1)
```

> **Source of truth:** formulas below follow the official [FSRS algorithm wiki](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm) (FSRS-6, 21 parameters). Implementation MUST use the maintained libraries, `fsrs` ([py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)) on the backend and [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) for the offline client fallback, rather than hand-rolled math. The equations are reproduced here for review only.

#### 1.1 State Variables
For every user-concept pair $(u, c)$, the engine stores:
* **Difficulty ($D \in [1, 10]$):** Inherent cognitive friction of the item for this user.
* **Stability ($S \in (0, \infty)$):** Time in days required for retrievability to drop from $100\%$ down to $90\%$ ($S = t$ when $R = 0.90$).
* **Retrievability ($R(t, S) \in [0, 1]$):** Current probability of successful recall at elapsed time $t$ (days) since the last review.
* **Review Grade ($G \in \{1, 2, 3, 4\}$):**
  * $G = 1$ (**Again**): Complete lapse, incorrect solution, or required Level 3 hint.
  * $G = 2$ (**Hard**): Solved with notable hesitation, required a Level 1 hint, or latency $> 2\sigma$ above mean.
  * $G = 3$ (**Good**): Solved correctly with standard processing latency and zero hints.
  * $G = 4$ (**Easy**): Solved immediately with high fluency and complete structural confidence.

#### 1.2 Retrievability Decay Function
FSRS-6 models forgetting with a power function whose decay is a **trainable** parameter $w_{20}$:
$$R(t, S) = \left(1 + \text{FACTOR} \cdot \frac{t}{S}\right)^{-w_{20}}, \qquad \text{FACTOR} = 0.9^{-1/w_{20}} - 1$$
This guarantees $R(S, S) = 0.90$. Default $w_{20} = 0.1542$ (FSRS-4.5 used a fixed decay of 0.5; FSRS-6 learns it per user).

#### 1.3 State Update Equations
When a review occurs at elapsed time $t$ with current Retrievability $R = R(t, S)$ and performance grade $G$ ($w_i$ denotes `w[i]`):

##### 1. Initial State (first review):
$$S_0(G) = w_{G-1}, \qquad D_0(G) = w_4 - e^{w_5 \cdot (G - 1)} + 1$$

##### 2. Difficulty Update (linear damping + mean reversion toward $D_0(4)$):
$$\Delta D(G) = -w_6 \cdot (G - 3), \qquad D' = D + \Delta D \cdot \frac{10 - D}{9}$$
$$D'' = w_7 \cdot D_0(4) + (1 - w_7) \cdot D'$$
*(Clamped to $[1, 10]$.)*

##### 3. Stability Update on Successful Recall ($G \ge 2$):
$$S'_r(D, S, R, G) = S \cdot \left(e^{w_8} \cdot (11 - D) \cdot S^{-w_9} \cdot \left(e^{w_{10} \cdot (1 - R)} - 1\right) \cdot \alpha_G + 1\right)$$
$$\alpha_G = \begin{cases} w_{15} & G = 2 \text{ (Hard)} \\ 1 & G = 3 \text{ (Good)} \\ w_{16} & G = 4 \text{ (Easy)} \end{cases}$$

##### 4. Stability Update on Memory Lapse ($G = 1$):
$$S'_f(D, S, R) = w_{11} \cdot D^{-w_{12}} \cdot \left((S + 1)^{w_{13}} - 1\right) \cdot e^{w_{14} \cdot (1 - R)}$$
*(A lapse on a high-stability item retains more residual stability than a lapse on a new item.)*

##### 5. Same-Day Review (short-term stability):
$$S'(S, G) = S \cdot e^{w_{17} \cdot (G - 3 + w_{18})} \cdot S^{-w_{19}}$$
*(Relevant here because a single session can revisit a node several times; ensure $S' \ge S$ when $G \ge 2$.)*

##### 6. Interval Calculation for Target Retention $r_{\text{target}}$:
Default $r_{\text{target}} = 0.90$ (per-user `users.target_retention_rate`):
$$I(S', r_{\text{target}}) = \frac{S'}{\text{FACTOR}} \cdot \left(r_{\text{target}}^{-1/w_{20}} - 1\right)$$

#### 1.4 Default Parameters (FSRS-6)
```
[0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542]
```
Per-user weights are stored in `users.fsrs_weights` ([Doc 04](04-system-architecture.md)) and re-optimized with the library's optimizer once a user has enough review history (library guidance; start with ~400+ reviews).

#### 1.5 Grade Mapping from Math Attempts
FSRS was designed for self-rated flashcards; here the grade is **derived** from attempt telemetry (§1.1 Review Grade), not self-reported. This mapping is itself a hypothesis and is checked in the pilot by comparing predicted $R$ against observed probe accuracy. *(v1.2: the same mapping applies to every grader; a `PARTIAL` score, 0 < score < 1, maps to grade 2 "Hard" — Doc 10 §5.)*

---

### 2. Real-Time Dynamic Difficulty Adjustment (Accuracy-Band Engine)

The runtime engine monitors a rolling window of attempts and calibrates challenge so the learner's accuracy stays in a **75–88% band** (centered near 85%).

> **Evidence scope:** [Wilson et al., 2019](https://www.nature.com/articles/s41467-019-12552-4) derived an optimal training error rate of ~15.87% for stochastic-gradient-descent learners on **binary classification** tasks (the optimum shifts to ~82% or ~75% under other noise assumptions). The authors note that transfer to humans and multi-class or multi-step tasks is untested. We use the band as a tunable design heuristic, consistent with desirable-difficulty and ZPD ideas, and tune the thresholds from pilot data.

```
       Learner Accuracy (W_k)
                 ▲
       100% ────┼─────────────────────────── [ ZONE 3: COGNITIVE UNDERLOAD ]
        88% ────┼─────────────────────────── Action: Strip Scaffolding, Inject Edge Cases
                │                            [ TARGET BAND 75–88% ]
                │                            Action: Maintain Deliberate Practice Loop
        75% ────┼─────────────────────────── [ ZONE 1: COGNITIVE OVERLOAD ]
          0 ────┴─────────────────────────── Action: Insert Faded Steps, Prerequisite Step-Down
                └──────────────────────────► Time / Trials
```

#### 2.1 The Rolling Accuracy Metric
The engine maintains a sliding window of the last $K = 20$ atomic interaction attempts:
$$\bar{A}_K = \frac{1}{K} \sum_{i=0}^{K-1} a_{t-i}, \quad a_i \in \{0, 1\}$$
Where:
* $a_i = 1$ if the step was completed without Level 2/3 hints and passed symbolic validation.
* $a_i = 0$ if the step failed validation or required escalated intervention.

Attempts are persisted in the `attempts` table ([Doc 04](04-system-architecture.md)); the window is per user across sessions. Until $K$ attempts exist, use the available ones and do not promote with fewer than 5.

#### 2.2 Scaffolding State Transition Matrix

**Single source of truth for thresholds** ($\theta_{\text{low}} = 0.75$, $\theta_{\text{high}} = 0.88$). The UI scaffolding level $\Lambda \in \{1, 2, 3\}$ transitions dynamically based on $\bar{A}_K$:

| Current Scaffold Level ($\Lambda$) | Condition: $\bar{A}_K < 0.75$ (Overload) | Condition: $0.75 \le \bar{A}_K \le 0.88$ (Optimal) | Condition: $\bar{A}_K > 0.88$ (Underload) |
| :--- | :--- | :--- | :--- |
| **Level 3: Independent Execution** (Blank canvas, multi-step derivation) | Transition $\rightarrow \Lambda = 2$ | Maintain $\Lambda = 3$ | Retain $\Lambda = 3$, increase item structural depth / reduce time limit. |
| **Level 2: Faded Worked Example** (Intermediate steps 1 & 2 pre-filled; solve step 3) | Transition $\rightarrow \Lambda = 1$ | Maintain $\Lambda = 2$ | Transition $\rightarrow \Lambda = 3$ |
| **Level 1: High Scaffolding** (Full worked example with inline fill-in checks) | Step down Knowledge Graph to immediate prerequisite node. | Transition $\rightarrow \Lambda = 2$ | Transition $\rightarrow \Lambda = 2$ |

---

### 3. Deterministic Mathematical Evaluation & AST Parsing Engine

> **Multi-subject (v1.2):** this section is the `sympy` grader, used by math items. Other subjects are graded deterministically from a stored `answer_spec` (`choice`, `match`, `order`, `categorize`, `exact`, `cloze`, `numeric`, `speech_match`); only open answers use `rubric_llm` (temperature 0, deterministic pre-checks, per-session cost cap), and `code_tests` trusts the browser runner (`decided_by = CLIENT`). See [Doc 10 §5](10-multi-subject-spec.md).

Large Language Models (LLMs) are strictly prohibited from evaluating mathematical validity. Mathematical validation is executed deterministically on the backend via **SymPy** and **Abstract Syntax Tree (AST)** structural diffing.

```
                [ Learner Expression Input (LaTeX / MathJSON) ]
                                       │
                                       ▼
                       [ AST Sanitization & Tokenization ]
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        [ SYMBOLIC EQUIVALENCE CHECK ]          [ STRUCTURAL AST TRANSFORMATION ]
        simplify(E_user - E_target) == 0        Compare AST(E_user) vs AST(E_target)
                    │                                     │
           Is it equivalent?                    Did they execute the intended rule?
           ├── NO  ──► SYNTAX / CALC ERROR       ├── NO  ──► MISCONCEPTION IDENTIFIED
           └── YES ──► Check Structure           └── YES ──► STEP VALIDATED (Pass)
```

#### 3.1 Symbolic Equivalence Verification
Given an expected canonical expression $E_{\text{target}}$ and the learner's submitted expression $E_{\text{user}}$:
$$\Delta E = \text{simplify}\left(E_{\text{user}} - E_{\text{target}}\right)$$
* If $\Delta E == 0$: The input is algebraically equivalent, but may not be structurally complete (e.g., student submitted $2x + 4$ instead of factoring out $2(x + 2)$).
* If $\Delta E \neq 0$: `simplify` is heuristic, so a non-zero result is **not** proof of inequivalence. Confirm with numeric sampling at random points (e.g. 8 points; inequivalent if any differ beyond tolerance). If sampling says equal, treat as equivalent and log the case for review.
* **Equations** (`=`): compare $(\text{lhs}_u - \text{rhs}_u)$ with $(\text{lhs}_t - \text{rhs}_t)$; they are equivalent if their ratio is a non-zero constant (so $2x = 6$ and $x = 3$ match); otherwise compare solution sets with `solveset` over the node's domain.
* Domain restrictions (division by zero, square roots of negatives) are checked separately against the node's declared domain assumptions.

#### 3.2 AST Structural Diffing & Diagnostic Rules
To evaluate intermediate algebraic transformations, the engine compares tree properties:

```python
# Conceptual Implementation: AST Transformation Evaluator
def evaluate_algebraic_step(user_ast, expected_ast, expected_operation):
    """
    Evaluates whether the user's AST transformation matches
    the pedagogical intent of the step (e.g., Factoring, Expansion, Division).
    """
    # 1. Check algebraic correctness
    diff = simplify(user_ast.to_sympy() - expected_ast.to_sympy())
    if diff != 0:
        # Classify the specific algebraic failure
        if user_ast.sign_mismatch(expected_ast):
            return {"status": "FAIL", "code": "SIGN_ERROR", "node": user_ast.failed_subnode}
        if user_ast.distribution_mismatch(expected_ast):
            return {"status": "FAIL", "code": "DISTRIBUTION_SLIP", "node": user_ast.failed_subnode}
        return {"status": "FAIL", "code": "CALCULATION_ERROR"}

    # 2. Check structural compliance (Did they actually perform the operation?)
    if expected_operation == "FACTOR_COMMON_TERM":
        if not user_ast.is_multiplication_of_factors():
            return {
                "status": "FAIL", 
                "code": "CORRECT_VALUE_WRONG_STRUCTURE", 
                "hint": "Expression is equivalent, but you have not factored out the greatest common divisor."
            }

    return {"status": "SUCCESS", "code": "STEP_VERIFIED"}
```

---

### 4. The 3-Tier Socratic Hint Ladder

When an algebraic failure or conceptual stall occurs, the system triggers the Socratic coaching pipeline. The session runner (code) sets the tier from the attempt count, Jev classifies the error category ([Doc 05 §2](05-ai-orchestration-ingestion.md#2-jev-system-1-decision-contract)), and a structured prompt is sent to the generation layer (`deepseek/deepseek-v4.1-flash`, fallback `z-ai/glm-5.3-flash`). Hint ladders that withhold the answer follow the "assistance dilemma" literature ([Koedinger & Aleven, 2007](https://doi.org/10.1007/s10648-007-9049-0)).

```
                    [ Evaluation Engine Reports Failure ]
                                      │
                                      ▼
                        [ Jev Failure Classification ]
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
     Attempt 1 Fail             Attempt 2 Fail             Attempt 3 Fail
     [ LEVEL 1 HINT ]           [ LEVEL 2 HINT ]           [ LEVEL 3 HINT ]
     - Pure conceptual          - Strategic diagnostic      - Operational pointer
     - Zero numbers/symbols     - Suggests tool/method     - Highlights exact region
     - Focuses attention        - Asks check question      - Leaves calculation to user
```

#### 4.1 Strict Hint Schemas

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SocraticIntervention",
  "type": "object",
  "properties": {
    "hint_level": { "type": "integer", "enum": [1, 2, 3] },
    "detected_error_category": { 
      "type": "string", 
      "enum": ["SIGN_ERROR", "DISTRIBUTION_SLIP", "CALCULATION_SLIP", "STRUCTURAL_MISCONCEPTION", "PREREQUISITE_FAILURE", "OTHER"] 
    },
    "socratic_prompt": {
      "type": "string",
      "description": "Strictly limited to a maximum of 2 sentences. Must prompt self-correction without stating values or the solution."
    },
    "target_focus_element_id": {
      "type": "string",
      "description": "ID of the specific step or UI component to visually illuminate."
    }
  },
  "required": ["hint_level", "detected_error_category", "socratic_prompt"],
  "additionalProperties": false
}
```

* **Level 1 (Conceptual):** *"Notice what happens to the signs inside the parentheses when you distribute a negative coefficient across subtraction."*
* **Level 2 (Strategic):** *"Check your distribution of $-3$ against the second term inside the bracket. Does a negative multiplied by a negative yield a negative?"*
* **Level 3 (Operational):** *"Look at line 2, term $+12$. Re-evaluate $(-3) \times (-4)$ specifically."*

---

### 5. Wakeful Rest Protocols (Micro-Breaks & Post-Session Rest)

The interface builds short offline rest periods into practice. These are motivated by consolidation research but their effect on multi-step math learning is a **hypothesis** measured in the pilot (see [§7 Claim Register](#7-claim-register)).

```
                  [ Focus Bout Running (default 45 min) ]
                                   │
              ┌────────────────────┴────────────────────┐
              │ After 360 s of Active Derivation         │
              ▼                                         ▼
   [ 15-Second RestOverlay ]                 [ Continue Practice ]
   - Low-stimulation overlay
   - Slow breathing pulse (10 s cycle)
   - "Look away and rest"
              │
              ▼
   [ Bout Concludes ]
              │
              ▼
   [ 5-10 Minute Post-Session Wakeful Rest ]
   - New items paused (soft default)
   - Suggests avoiding other screens
```

#### 5.1 The 15-Second Micro-Break (Wakeful Rest)
**Single source of truth for micro-break timing.**
* **Evidence:** [Buch et al., 2021 (Cell Reports)](https://doi.org/10.1016/j.celrep.2021.109193) recorded MEG during a motor-sequence typing task with **10-second** rests and found hippocampo-neocortical replay compressed ~20x relative to behavior; replay rate predicted micro-offline skill gains. The link is correlational and was shown for motor skill, not algebra. Our 15 s default is a design choice.
* **Trigger Condition:** Cumulative active problem-solving time $T_{\text{active}} \ge 360\text{ s}$ (default; configurable 300–420 s), or immediately after resolving a task that required $\ge 2$ error-recovery cycles. Never interrupts mid-step: it waits for the current step submission.
* **UI Behavior (`RestOverlay`):**
  * Displays `#090D16` overlay at $95\%$ opacity.
  * Central visual: an SVG circle with a sine-eased breathing animation, **5 s expand + 5 s contract (10 s cycle, 0.1 Hz, ~6 breaths/min)**. Respects `prefers-reduced-motion` (static circle + countdown).
  * Copy: *"Short rest. Look away from the screen for 15 seconds."*
  * Audio: none.
  * Skip Interaction: a low-contrast but accessible button (≥48×48 px touch target, keyboard reachable). If clicked, renders a confirmation:  
    *"Short rests between practice help the brain consolidate what you just did. Skip this one?"*  
    Skips are logged to `session_logs.micro_breaks_skipped`.

#### 5.2 Post-Session Wakeful Rest
* **Evidence:** Brief post-learning wakeful rest improved retention of verbal material in [Dewar et al., 2012](https://doi.org/10.1177/0956797612441220). Claims about NSDR specifically and "protecting synaptic tags" are **hypotheses** and must not be presented to users as fact.
* **Trigger Condition:** Completion of the planned daily session (typically 30–45 minutes).
* **UI Behavior:**
  * Pauses new practice items for 10 minutes by default (soft default: the learner can continue after a single confirmation).
  * Offers an optional, audio-guided rest / slow-breathing track (`NSDRPlayer`).
  * Suggests avoiding other demanding screen activity for ~10–15 minutes.

---

### 6. Item Bank & Problem Generation

Every practice step needs a problem statement plus a verified canonical step sequence. Items are **generated offline and verified before use**, never generated live during a session.

```
 [ Node (slug, canonical_equation_latex, operations) ]
                     │
                     ▼
 [ System 2 LLM drafts N items: statement + step list + expected operation per step ]
                     │
                     ▼
 [ SymPy verification: each step equivalent to previous, final answer correct,
   declared operation matches AST (e.g. FACTOR_COMMON_TERM) ]
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     [ Reject ]         [ Store in `items` (status = VERIFIED) ]
                                │
                                ▼
                  [ Calibrate difficulty from attempt data ]
```

* **Storage:** `items` table linked to `knowledge_nodes` ([Doc 04 §2.1](04-system-architecture.md#21-core-schema-ddl)): `statement_latex`, `steps JSONB` (latex + operation per step), `difficulty_estimate`, `status` (`DRAFT` / `VERIFIED` / `RETIRED`), `source` (`SEEDED` / `GENERATED`).
* **Seed:** Phase P0 hand-authors items for ~20 Algebra nodes (≥10 items per node) so the deterministic core can ship without any LLM.
* **Variants:** Numeric parameters are randomized from templates where possible so retrieval probes are not memorized answers.
* **Difficulty calibration:** `difficulty_estimate` starts from the generator's label and is updated from observed first-attempt accuracy (simple running mean per item; upgrade path: IRT 1PL/2PL once data volume allows).
* **Guardrail:** An item is served only if `status = VERIFIED`. LLMs never judge correctness (FR-4.3) — except `rubric_llm` open answers (v1.2).
* **Non-math items (v1.2):** stored as `prompt_md` + `parts[{component, grader, props, answer_spec}]` (Doc 10 §6.2), verified structurally per grader (key ⊂ options, unique labels, ≥ 1 accepted blank answer, rubric exemplar scores ≥ 0.8) plus one repair round; `statement_latex`/`steps` stay NULL. Item text may only link research-cited URLs.

---

### 8. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.1 | 2026-09-24 | Core engine and math domain. |
| 1.2 | 2026-10-09 | Multi-subject ([Doc 10](10-multi-subject-spec.md)): §3 is the `sympy` grader among a registry; PARTIAL → FSRS grade 2 (§1.5); generic item shape and verification (§6). FSRS, accuracy band, hint ladder and rest protocols are subject-independent; "math" in §2 wording reads as "the item's grader". |

---

### 7. Claim Register

Every scientific claim used in product copy or design decisions, with its evidence level. **Strong** = replicated, directly applicable; **Moderate** = solid evidence in a related setting; **Hypothesis** = plausible, untested for this use; validate in the pilot.

| Claim | Where used | Evidence | Source |
| :--- | :--- | :--- | :--- |
| Spaced retrieval practice improves long-term retention | FSRS scheduling, probes | Strong | [Cepeda et al., 2006](https://doi.org/10.1037/0033-2909.132.3.354); [Roediger & Karpicke, 2006](https://doi.org/10.1111/j.1467-9280.2006.01693.x) |
| FSRS predicts recall better than SM-2 | Doc 01 §3, §1 | Strong (flashcards) | [SRS benchmark](https://github.com/open-spaced-repetition/srs-benchmark) |
| FSRS reduces review load 20–30% vs SM-2 for this product | Removed from Doc 01 | Hypothesis | To be measured |
| Worked examples, faded over time, help novices | Scaffold levels, `FadedWorkedExample` | Strong | [Sweller, 1988](https://doi.org/10.1207/s15516709cog1202_4); [Renkl & Atkinson, 2003](https://doi.org/10.1207/S15326985EP3801_3) |
| Optimal training accuracy is ~85% | §2 accuracy band | Moderate (derived for SGD learners, binary tasks) | [Wilson et al., 2019](https://www.nature.com/articles/s41467-019-12552-4) |
| Short wakeful rests during practice support rapid consolidation via replay | §5.1 micro-breaks | Moderate (motor skill, correlational) | [Buch et al., 2021](https://doi.org/10.1016/j.celrep.2021.109193) |
| 15 s rest every ~6 min helps multi-step math learning | §5.1 defaults | Hypothesis | Pilot A/B (micro-breaks on/off) |
| Skipping a rest drops retention by up to 40% | Removed from all copy | Unsupported | None found |
| Brief post-learning wakeful rest improves retention | §5.2 | Moderate (verbal memory) | [Dewar et al., 2012](https://doi.org/10.1177/0956797612441220) |
| NSDR protects synaptic tags / LTP | Removed | Hypothesis | None found |
| 45-minute ultradian focus bouts are optimal | Session default | Hypothesis | Configurable default only |
| Pre-study visual fixation elevates alertness | `FocusPrimingModal` | Hypothesis | Optional feature |
| Hint ladders that withhold answers improve learning vs. giving answers | §4 | Moderate | [Koedinger & Aleven, 2007](https://doi.org/10.1007/s10648-007-9049-0) (assistance dilemma) |