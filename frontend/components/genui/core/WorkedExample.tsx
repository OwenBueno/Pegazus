"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";
import { InlineBlanks } from "./Cloze";

/** Graded server-side: emits {blanks} flattened in step order. */
export function WorkedExample({
  title,
  steps,
  widgetId = "worked",
  disabled = false,
  onAction,
}: {
  title?: string;
  steps: { segments: string[] }[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const offsets = steps.map((_, s) => steps.slice(0, s).reduce((n, st) => n + st.segments.length - 1, 0));
  const total = steps.reduce((n, st) => n + st.segments.length - 1, 0);
  const [blanks, setBlanks] = useState(() => Array<string>(total).fill(""));

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("workedExample")}</p>
      {title ? <p className="font-display text-[15px] font-semibold text-slate-100">{title}</p> : null}
      <ol className="list-decimal space-y-2 pl-6 text-[15px] text-slate-100 marker:text-slate-500">
        {steps.map((st, s) => (
          <li key={s}>
            <InlineBlanks
              segments={st.segments}
              values={blanks}
              offset={offsets[s]}
              label={(n) => t("stepBlankN", { s: s + 1, n })}
              disabled={disabled}
              onChange={(i, v) => setBlanks((b) => b.map((x, j) => (j === i ? v : x)))}
            />
          </li>
        ))}
      </ol>
      <button
        type="button"
        disabled={disabled || blanks.some((b) => !b.trim())}
        onClick={() => onAction?.({ widgetId, type: "ANSWER", payload: { blanks: blanks.map((b) => b.trim()) } })}
        className={buttonClass("primary", "md", true)}
      >
        {t("checkAnswer")}
      </button>
    </section>
  );
}
