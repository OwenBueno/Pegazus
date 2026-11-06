"use client";

import { useTranslations } from "next-intl";
import { RotateCcw } from "lucide-react";

/** Numbered steps with connectors; optional cycle note. Display-only. */
export function ProcessSteps({
  steps,
  cyclic,
}: {
  steps: { title: string; body?: string }[];
  cyclic?: boolean;
}) {
  const t = useTranslations("session");
  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("process")}</p>
      <ol>
        {steps.map((s, i) => (
          <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
            {i < steps.length - 1 && (
              <span aria-hidden className="absolute left-4 top-8 bottom-0 w-px -translate-x-1/2 bg-line-strong" />
            )}
            <span
              aria-hidden
              className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-teal-400/40 bg-teal-500/10 font-mono text-xs text-teal-200"
            >
              {i + 1}
            </span>
            <div className="min-w-0 pt-1">
              <p className="text-sm font-semibold text-slate-100">{s.title}</p>
              {s.body ? <p className="mt-0.5 text-sm text-slate-300">{s.body}</p> : null}
            </div>
          </li>
        ))}
      </ol>
      {cyclic && (
        <p className="flex items-center gap-2 text-xs text-slate-400">
          <RotateCcw className="h-4 w-4" aria-hidden />
          {t("repeatsCycle")}
        </p>
      )}
    </section>
  );
}
