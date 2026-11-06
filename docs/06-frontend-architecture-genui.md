# PROJECT COGNITIVE OS
## Document 06: Frontend Architecture & GenUI Component Catalog
**Version:** 1.2 (multi-subject; see §2.2, §6)
**Target:** Client-Side Topology, Next.js 16 PWA Scaffolding, GenUI Renderer, and Mobile-First Components (core + math/science/language/humanities/code packs)  
**Runtime:** Next.js 16.3.x (React 19, App Router) + Tailwind CSS v4 + MathLive + KaTeX + Dexie.js (IndexedDB)

> **Version pin:** use Next.js **≥ 16.3.6**. [16.3.6](https://nextjs.org/blog/upcoming-nextjs-security-release-september-22-2026) fixes a critical `ImageResponse` vulnerability affecting 16.2.0–16.3.5, and a further security release (16.3.7) is [scheduled for 2026-09-30](https://nextjs.org/blog/upcoming-nextjs-security-release-september-2026). Upgrade when it ships.

---

### 1. Client Architecture & Directory Layout

The frontend is a **Mobile-First Progressive Web App (PWA)** optimized for touch interaction, fast loading, and low cognitive friction.

```
frontend/
├── app/
│   ├── layout.tsx                     # Root layout (dark theme, fonts, i18n provider)
│   ├── globals.css                    # Tailwind v4 entry + @theme tokens (§5)
│   ├── manifest.ts                    # PWA manifest
│   ├── sw.ts                          # Service worker (Serwist) – caches app shell + active session
│   ├── (workspace)/
│   │   ├── session/[id]/page.tsx      # Deliberate practice workspace
│   │   └── path/[id]/page.tsx         # Living path DAG visualizer & milestone tracker
│   └── api/                           # Edge proxy handlers
├── contracts/
│   └── genui.ts                       # Shared GenUI types (Doc 04 §3) + Zod schema
├── components/
│   ├── genui/
│   │   ├── WorkspaceRenderer.tsx      # Validates payload, renders widgets in order
│   │   └── registry.ts                # Widget type → lazy component map
│   ├── math/
│   │   ├── MathText.tsx               # Read-only LaTeX via KaTeX (no innerHTML strings)
│   │   ├── SymbolicStepEditor.tsx     # Step-by-step derivation
│   │   ├── VirtualMathKeyboard.tsx    # MathLive virtual keyboard with custom layouts
│   │   ├── FadedWorkedExample.tsx     # Faded scaffolding container
│   │   └── FunctionPlotter.tsx        # 2D coordinate visualizer
│   ├── neuro/
│   │   ├── RestOverlay.tsx            # 15 s micro-break screen
│   │   ├── FocusPrimingModal.tsx      # Optional pre-session fixation
│   │   └── NSDRPlayer.tsx             # Optional post-session rest audio
│   ├── dialogue/
│   │   └── SocraticDialogueBox.tsx    # Single-hint drawer
│   └── ui/                            # Base components (Buttons, Dialogs, Cards)
├── messages/                          # i18n catalogs (en, es) – Doc 02 §5.4
└── lib/
    ├── db/                            # Dexie.js offline store + sync queue (Doc 04 §5.3)
    ├── fsrs/                          # ts-fsrs wrapper for offline scheduling fallback
    └── telemetry/                     # Latency marks, active-time tracker
```

---

### 2. The GenUI Client Resolver

The client receives a `GenUIWorkspacePayload` (flat, ordered widget list; [Doc 04 §3](04-system-architecture.md#3-component-driven-genui-schema-contract)), validates it, and renders pre-compiled components. No dynamic code is evaluated.

```
       [ GenUIWorkspacePayload (JSON from FastAPI) ]
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ WorkspaceRenderer                            │
        │ - Zod-validates the whole payload            │
        │ - Looks up each widget in the registry       │
        │ - Suspense fallback + ErrorBoundary          │
        └──────────────────────┬───────────────────────┘
                               │ (in order)
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    [ FadedWorkedExample ]  [ StepEditor ]   [ VirtualKeyboard ]
```

#### 2.1 Resolver Implementation

```tsx
// components/genui/WorkspaceRenderer.tsx
'use client';

import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { WORKSPACE_SCHEMA, type GenUIWorkspacePayload } from '@/contracts/genui';
import { WIDGET_REGISTRY } from './registry';

export type WidgetAction = { widgetId: string; type: string; payload: unknown };

export function WorkspaceRenderer({
  payload,
  onAction,
}: {
  payload: unknown;
  onAction: (action: WidgetAction) => void;
}) {
  const parsed = WORKSPACE_SCHEMA.safeParse(payload);
  if (!parsed.success) {
    // Reported to telemetry; the session runner requests a fresh payload.
    return <p role="alert" className="text-sm text-rose-400">Could not load this exercise.</p>;
  }
  const workspace: GenUIWorkspacePayload = parsed.data;

  return (
    <div className="flex flex-col gap-4">
      {workspace.widgets.filter((w) => w.visible).map((widget) => {
        const Component = WIDGET_REGISTRY[widget.type];
        return (
          <ErrorBoundary key={widget.id} fallback={<p role="alert">This part failed to load.</p>}>
            <Suspense fallback={<div className="h-16 w-full animate-pulse rounded-lg bg-surface" />}>
              <Component id={widget.id} {...widget.props} onAction={onAction} />
            </Suspense>
          </ErrorBoundary>
        );
      })}
    </div>
  );
}
```

```ts
// components/genui/registry.ts
import { lazy, type ComponentType } from 'react';
import type { CanvasWidgetType } from '@/contracts/genui';

export const WIDGET_REGISTRY: Record<CanvasWidgetType, ComponentType<any>> = {
  SymbolicStepEditor: lazy(() => import('../math/SymbolicStepEditor')),
  VirtualMathKeyboard: lazy(() => import('../math/VirtualMathKeyboard')),
  FadedWorkedExample: lazy(() => import('../math/FadedWorkedExample')),
  FunctionPlotter: lazy(() => import('../math/FunctionPlotter')),
  SocraticDialogueBox: lazy(() => import('../dialogue/SocraticDialogueBox')),
  RestOverlay: lazy(() => import('../neuro/RestOverlay')),
};
```

Typing the registry as `Record<CanvasWidgetType, …>` makes the build fail if a contract widget has no component.

#### 2.2 Multi-subject registry (v1.2, as built)
The registry above is the original math-only sketch. As built ([Doc 10 §4](10-multi-subject-spec.md)), one backend catalog `COMPONENTS` (`backend/app/services/component_catalog.py`) tags every component with a **category** (`core`, `math`, `science`, `language`, `humanities`, `code`, `media`), a **role** (`answer` / `visual` / `support`) and, for answers, a **grader**; `tests/test_component_catalog.py` keeps it in sync with the Zod schemas in `frontend/lib/contracts/genui.ts` and the `switch` in `frontend/components/genui/registry.tsx`. Core components live in `components/genui/core/`; family packs (`humanities/`, `language/`, `science/`, `code/`) load with `next/dynamic` so the core route bundle stays within +15 KB gz. Answer widgets emit only what the learner did (`{ids}`, `{pairs}`, `{order}`, `{text}`, `{code, passed, total}`, …); answer keys never reach the client (Doc 10 §6.4). Every component has a backend sanitizer; an invalid payload renders the beat as text. Lesson views list the node's research `sources` (`components/learn/SourcesList.tsx`); a SourceExcerpt only links a cited URL.

---

### 3. Math Domain Component Catalog
*(The math pack: rendered only for profiles whose `notation` is `math`.)*

#### 3.1 `MathText.tsx` (read-only LaTeX)
Renders LaTeX with KaTeX into a ref. `trust: false` blocks `\href`, `\url`, `\htmlData` and similar commands, so server- or LLM-provided LaTeX cannot inject markup. Never interpolate LaTeX into `dangerouslySetInnerHTML`.

```tsx
// components/math/MathText.tsx
'use client';

import { useEffect, useRef } from 'react';
import katex from 'katex';

export default function MathText({ latex, display = false }: { latex: string; display?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current) {
      katex.render(latex, ref.current, { throwOnError: false, trust: false, displayMode: display, output: 'htmlAndMathml' });
    }
  }, [latex, display]);
  return <span ref={ref} />;
}
```

`output: 'htmlAndMathml'` keeps MathML for screen readers (NFR 5.2).

#### 3.2 `SymbolicStepEditor.tsx`
Renders derivation lines. Locked steps use `MathText`; the active step is a MathLive `<math-field>`. Submission happens on **Enter** (or the keyboard's ⏎ key), not on every keystroke.

```tsx
// components/math/SymbolicStepEditor.tsx
'use client';

import 'mathlive';
import MathText from './MathText';
import type { DerivationStep } from '@/contracts/genui';
import type { WidgetAction } from '../genui/WorkspaceRenderer';

interface Props {
  id: string;
  targetVariable: string;
  inlineValidation: boolean;
  activeStepIndex: number;
  initialSteps: DerivationStep[];
  onAction: (a: WidgetAction) => void;
}

export default function SymbolicStepEditor({ id, initialSteps, activeStepIndex, onAction }: Props) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="mb-1 font-mono text-xs uppercase tracking-wider text-slate-500">Symbolic Derivation</div>

      {initialSteps.map((step, idx) => {
        const isActive = idx === activeStepIndex;
        return (
          <div
            key={step.stepNumber}
            className={`flex items-center gap-3 rounded-xl border p-3 ${
              isActive ? 'border-indigo-500/50 bg-indigo-950/20' : 'border-slate-800/60 bg-slate-900/40 opacity-70'
            }`}
          >
            <span className="w-6 font-mono text-xs text-slate-500">{step.stepNumber}.</span>

            {step.isLocked ? (
              <MathText latex={step.latexExpression} />
            ) : (
              <math-field
                id={`${id}-step-${idx}`}
                aria-label={`Step ${step.stepNumber}`}
                class="w-full bg-transparent text-lg text-slate-100 outline-none"
                onKeyDown={(e: React.KeyboardEvent<HTMLElement & { value: string }>) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onAction({ widgetId: id, type: 'SUBMIT_STEP', payload: { stepIndex: idx, latex: e.currentTarget.value } });
                  }
                }}
              >
                {step.latexExpression}
              </math-field>
            )}

            {step.status === 'VALID' && <span className="ml-auto text-xs text-emerald-400" aria-label="Correct">✓</span>}
            {step.status === 'INVALID' && <span className="ml-auto text-xs text-rose-400" aria-label="Incorrect">✗</span>}
          </div>
        );
      })}
    </div>
  );
}
```

#### 3.3 `VirtualMathKeyboard.tsx`
*ponytail: no hand-built keypad. MathLive ships a virtual keyboard (`window.mathVirtualKeyboard`) that already inserts into the focused `<math-field>`, handles backspace/cursor movement, and supports custom layouts.* This component only configures the layout and styling:

* `layout: 'algebra'` rows: `x y x² xⁿ √` / `7 8 9 ÷ (` / `4 5 6 × )` / `1 2 3 − =` / `0 . + ⌫ ⏎`.
* Every key ≥ **48×48 px** (NFR 5.2), styled via MathLive CSS variables to match the theme.
* ⏎ dispatches the same `SUBMIT_STEP` action as Enter.
* Optional haptic tick via `navigator.vibrate?.(10)` (not supported on iOS Safari; silently ignored).
* Upgrade path: a custom React keypad only if MathLive's layouts can't meet usability-test findings.

#### 3.4 `FadedWorkedExample.tsx`
Props: `problemStatement` (LaTeX), `steps: DerivationStep[]`, `activeStepIndex`. Renders the statement with `MathText`, steps before `activeStepIndex` as locked (with optional `justification` text), and the active step as an embedded `SymbolicStepEditor` row. Scaffold level 1 shows all steps with inline fill-in gaps; level 2 shows steps 1..N-1 solved.

#### 3.5 `FunctionPlotter.tsx`
Props: `expressions: string[]` (LaTeX), `domain: [number, number]`, optional `sliders[]`. Expressions are converted to evaluable form with MathLive's compute engine (no `eval`), sampled on an SVG canvas (~200 points), and redrawn on slider change. Provides a text alternative listing key features (intercepts, asymptotes) for screen readers.

#### 3.6 `SocraticDialogueBox.tsx`
Props: `hintTier`, `prompt` (plain text ≤ 240 chars, rendered as text, never as HTML), optional `highlightElementId` (the matching step gets an outline). One hint at a time; no free-form chat input in practice mode. Announced via `aria-live="polite"`.

---

### 4. Rest Components

#### 4.1 `RestOverlay.tsx`
Implements the 15-second micro-break ([Doc 03 §5.1](03-cognitive-engine-pedagogical.md#51-the-15-second-micro-break-wakeful-rest)). The timer is driven by a deadline timestamp (so background-tab throttling can't stretch it), uses a single interval, and guarantees `onComplete` fires exactly once.

```tsx
// components/neuro/RestOverlay.tsx
'use client';

import { useEffect, useRef, useState } from 'react';

interface RestOverlayProps {
  durationSeconds?: number;
  allowSkip?: boolean;
  breathCycleSeconds?: number;
  onComplete: () => void;
  onSkipLogged: () => void;
}

export default function RestOverlay({
  durationSeconds = 15,
  allowSkip = true,
  breathCycleSeconds = 10,
  onComplete,
  onSkipLogged,
}: RestOverlayProps) {
  const [secondsRemaining, setSecondsRemaining] = useState(durationSeconds);
  const [confirmingSkip, setConfirmingSkip] = useState(false);
  const done = useRef(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const finish = () => {
    if (done.current) return;
    done.current = true;
    onCompleteRef.current();
  };

  useEffect(() => {
    const deadline = Date.now() + durationSeconds * 1000;
    const timer = setInterval(() => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setSecondsRemaining(left);
      if (left === 0) {
        clearInterval(timer);
        finish();
      }
    }, 250);
    return () => clearInterval(timer);
  }, [durationSeconds]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rest-title"
      className="fixed inset-0 z-50 flex select-none flex-col items-center justify-center bg-background/95 p-6 backdrop-blur-md"
    >
      <div
        className="mb-8 flex h-40 w-40 items-center justify-center rounded-full border border-indigo-500/30 bg-gradient-to-tr from-indigo-500/20 to-teal-500/20 motion-safe:animate-breathe"
        style={{ animationDuration: `${breathCycleSeconds}s` }}
      >
        <span className="font-mono text-4xl font-bold text-slate-100" aria-live="off">{secondsRemaining}s</span>
      </div>

      <h2 id="rest-title" className="mb-2 text-center text-lg font-semibold text-slate-200">Short rest.</h2>
      <p className="mb-10 max-w-xs text-center text-sm leading-relaxed text-slate-400">
        Look away from the screen for a few seconds.
      </p>

      {allowSkip && (
        <button
          onClick={() => setConfirmingSkip(true)}
          className="min-h-12 min-w-12 px-4 font-mono text-xs uppercase tracking-wider text-slate-500 hover:text-slate-300"
        >
          Skip break
        </button>
      )}

      {confirmingSkip && (
        <div role="alertdialog" aria-labelledby="skip-title" className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 text-center">
            <h3 id="skip-title" className="mb-2 text-base font-bold text-slate-100">Skip this rest?</h3>
            <p className="mb-6 text-xs leading-relaxed text-slate-300">
              Short rests between practice help the brain consolidate what you just did.
            </p>
            <div className="flex gap-3">
              <button onClick={() => setConfirmingSkip(false)} className="min-h-12 flex-1 rounded-lg bg-indigo-600 text-xs font-medium text-white">
                Keep resting
              </button>
              <button
                onClick={() => { onSkipLogged(); finish(); }}
                className="min-h-12 rounded-lg bg-slate-800 px-4 text-xs font-medium text-slate-200"
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

Copy strings come from the i18n catalogs in production; they are inlined here for readability.

#### 4.2 `FocusPrimingModal.tsx`
Optional, off by default. Props: `durationSeconds` (default 120), `onComplete`, `onSkip`. Shows a single static fixation target; skippable at any time. Evidence level: hypothesis ([Doc 03 §7](03-cognitive-engine-pedagogical.md#7-claim-register)).

#### 4.3 `NSDRPlayer.tsx`
Optional post-session rest audio. Props: `trackUrl`, `durationSeconds`, `onComplete`. Uses a native `<audio controls>` element (accessible by default), with a transcript link. Shown after the session summary; never autoplays.

---

### 5. Theme (Tailwind CSS v4)

Tailwind v4 is configured in CSS with `@theme`; there is no `tailwind.config.js`.

```css
/* app/globals.css */
@import "tailwindcss";
@import "katex/dist/katex.min.css";

@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --color-background: #090D16;     /* deep slate, default dark theme */
  --color-surface: #0F172A;
  --color-surface-subtle: #1E293B;
  --color-surface-accent: #334155;
  --color-neuro-indigo: #6366F1;
  --color-neuro-teal: #14B8A6;
  --color-neuro-alert: #F43F5E;

  --animate-breathe: breathe 10s ease-in-out infinite;
  @keyframes breathe {
    0%, 100% { transform: scale(0.85); opacity: 0.7; }
    50%      { transform: scale(1.1);  opacity: 1; }
  }
}
```

The `breathe` animation is 5 s expand + 5 s contract; `RestOverlay` overrides the duration from `breathCycleSeconds`, and `motion-safe:` disables it under `prefers-reduced-motion`.

---

### 6. Revision history
| Version | Date | Change |
| :--- | :--- | :--- |
| 1.1 | 2026-09-24 | MVP frontend (math components). |
| 1.2 | 2026-10-09 | Multi-subject: two-axis catalog, core components + lazy family packs, server-only answer keys, research sources list (§2.2). §3 is now the math pack; offline queue records `{part_index, answer}` (Doc 04 §5.3). |
