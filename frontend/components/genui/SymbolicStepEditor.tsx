"use client";

import { CheckCircle2, CopyPlus, Eye, Flag, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { MathText } from "@/components/math/MathText";
import { MathField } from "@/components/math/MathField";
import type { DerivationStep, WidgetAction } from "@/lib/contracts/genui";

const chip =
  "inline-flex min-h-9 items-center gap-1.5 rounded-full border border-line-strong bg-surface-raised px-3 text-xs font-medium text-slate-300 transition-colors hover:border-indigo-400/50 hover:text-slate-100";

export function SymbolicStepEditor({
  targetVariable,
  initialSteps,
  activeStepIndex,
  value,
  onChange,
  onAction,
  widgetId = "steps",
}: {
  targetVariable: string;
  inlineValidation: boolean;
  activeStepIndex: number;
  initialSteps: DerivationStep[];
  value?: string;
  onChange?: (latex: string) => void;
  onAction?: (a: WidgetAction) => void;
  widgetId?: string;
}) {
  const t = useTranslations("session");
  const v = targetVariable || "x";
  return (
    <ol className="space-y-2" aria-label="Symbolic derivation">
      {initialSteps.map((step, i) => {
        const locked = step.isLocked || i < activeStepIndex;
        const active = i === activeStepIndex && !locked;
        const prev = initialSteps[i - 1]?.latexExpression;
        return (
          <li
            key={`${step.stepNumber}-${i}`}
            id={`${widgetId}-step-${i}`}
            className={
              active
                ? "rounded-control border border-indigo-400/40 bg-neuro-indigo/[0.07] px-3 py-3 shadow-[0_0_0_4px_rgb(99_102_241/0.07)]"
                : "rounded-control border border-line bg-surface-raised px-3 py-2"
            }
          >
            <div className="flex items-start gap-2">
              <span className="mt-1 w-6 font-mono text-xs text-slate-500">
                {step.stepNumber}.
              </span>
              {active && onChange ? (
                <div className="min-w-0 flex-1">
                  <MathField
                    value={value ?? ""}
                    onChange={onChange}
                    placeholder={`\\text{${t("stepPlaceholder")}}`}
                    virtualKeyboardMode="onfocus"
                    onSubmit={(latex) =>
                      onAction?.({
                        widgetId,
                        type: "SUBMIT_STEP",
                        payload: { stepIndex: i, latex },
                      })
                    }
                  />
                </div>
              ) : (
                <MathText
                  latex={step.latexExpression}
                  className="min-w-0 flex-1 text-slate-200"
                />
              )}
              {step.status === "VALID" && (
                <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-neuro-teal" aria-label="Correct" />
              )}
              {step.status === "INVALID" && (
                <XCircle className="mt-1 h-4 w-4 shrink-0 text-neuro-alert" aria-label="Incorrect" />
              )}
            </div>
            {step.justification ? (
              <p className="mt-1 pl-8 text-xs text-slate-500">{step.justification}</p>
            ) : null}
            {active && onChange ? (
              <div className="mt-3 flex flex-wrap gap-2 pl-8" role="group" aria-label={t("stepOptions")}>
                {prev ? (
                  <button type="button" className={chip} onClick={() => onChange(prev)}>
                    <CopyPlus className="h-3.5 w-3.5" aria-hidden />
                    {t("startFromPrevious")}
                  </button>
                ) : null}
                <button type="button" className={chip} onClick={() => onChange(`${v}=\\placeholder{}`)}>
                  <Flag className="h-3.5 w-3.5" aria-hidden />
                  {t("finalAnswerTemplate", { v })}
                </button>
                <button
                  type="button"
                  className={chip}
                  onClick={() => onAction?.({ widgetId, type: "REVEAL_STEP", payload: { stepIndex: i } })}
                >
                  <Eye className="h-3.5 w-3.5" aria-hidden />
                  {t("revealStep")}
                </button>
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
