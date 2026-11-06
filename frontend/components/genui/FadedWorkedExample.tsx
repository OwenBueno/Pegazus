"use client";

import { MathText } from "@/components/math/MathText";
import { MathField } from "@/components/math/MathField";
import type { DerivationStep } from "@/lib/contracts/genui";

/** Real faded example: locked solved lines + gap fill on the active step. */
export function FadedWorkedExample({
  problemStatement,
  steps,
  activeStepIndex,
  scaffoldLevel = 1,
  gapLatex,
  gapValue,
  onGapChange,
}: {
  problemStatement: string;
  steps: DerivationStep[];
  activeStepIndex: number;
  scaffoldLevel?: 1 | 2 | 3;
  gapLatex?: string;
  gapValue?: string;
  onGapChange?: (latex: string) => void;
}) {
  // Λ3: statement only (caller may hide this widget)
  if (scaffoldLevel >= 3) {
    return (
      <section className="space-y-2 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
        <MathText latex={problemStatement} display className="text-xl text-slate-100" />
      </section>
    );
  }

  const fieldValue = gapValue !== undefined ? gapValue : (gapLatex ?? "");

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-neuro-teal">
        Worked example
      </p>
      <MathText latex={problemStatement} display className="text-xl text-slate-100" />
      <ol className="space-y-2">
        {steps.map((s, i) => {
          const isActive = i === activeStepIndex && !s.isLocked;
          const faded = scaffoldLevel === 2 && i > activeStepIndex;
          if (faded) {
            return (
              <li
                key={`${s.stepNumber}-${i}`}
                className="rounded-control border border-dashed border-line-strong px-3 py-2 opacity-40"
                aria-hidden
              >
                <span className="font-mono text-xs text-slate-600">{s.stepNumber}.</span>
              </li>
            );
          }
          return (
            <li
              key={`${s.stepNumber}-${i}`}
              className={
                isActive
                  ? "rounded-control border border-teal-400/40 bg-teal-500/[0.06] px-3 py-2.5 shadow-[0_0_0_4px_rgb(20_184_166/0.06)]"
                  : "rounded-control border border-line bg-surface-raised px-3 py-2"
              }
            >
              <div className="flex items-center gap-2">
                <span className="w-6 font-mono text-xs text-slate-500">
                  {s.stepNumber}.
                </span>
                {isActive && onGapChange ? (
                  <div className="min-w-0 flex-1">
                    <MathField
                      value={fieldValue}
                      onChange={onGapChange}
                      virtualKeyboardMode="onfocus"
                    />
                  </div>
                ) : (
                  <MathText
                    latex={s.latexExpression || "\\ldots"}
                    className="text-slate-200"
                  />
                )}
              </div>
              {s.justification && !isActive ? (
                <p className="mt-1 pl-8 text-xs text-slate-500">{s.justification}</p>
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
