"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { WidgetAction } from "@/lib/contracts/genui";
import { MathText } from "@/components/math/MathText";

/** Graded server-side: emits {ids}; the session verdict banner shows the result. */
export function QuickCheck({
  prompt,
  choices,
  labelsAreLatex = false,
  widgetId = "quick",
  disabled = false,
  onAction,
}: {
  prompt: string;
  choices: { id: string; label: string }[];
  labelsAreLatex?: boolean;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [picked, setPicked] = useState<string | null>(null);

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">
        {t("quickCheck")}
      </p>
      <p className="text-[17px] leading-relaxed text-slate-50">{prompt}</p>
      <ul className="space-y-2">
        {choices.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              aria-pressed={picked === c.id}
              disabled={disabled}
              onClick={() => {
                setPicked(c.id);
                onAction?.({ widgetId, type: "QUICK_CHECK", payload: { ids: [c.id] } });
              }}
              className={`min-h-14 w-full rounded-control border px-4 py-3 text-left text-base font-medium transition-colors active:scale-[0.99] disabled:opacity-90 ${
                picked === c.id
                  ? "border-indigo-400/60 bg-indigo-500/10 text-indigo-100"
                  : "border-line-strong bg-surface-raised text-slate-100 hover:border-indigo-400/50 hover:bg-surface-subtle"
              }`}
            >
              {labelsAreLatex ? <MathText latex={c.label} /> : c.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
