"use client";

import { useTranslations } from "next-intl";

/** Vertical chronology; events arrive sorted by year. Display-only. */
export function Timeline({
  title,
  events,
}: {
  title?: string;
  events: { date: string; year: number; label: string; detail?: string }[];
}) {
  const t = useTranslations("session");
  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{title ?? t("timeline")}</p>
      <ol>
        {events.map((e, i) => (
          <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
            {i < events.length - 1 && (
              <span aria-hidden className="absolute left-1.5 top-4 bottom-0 w-px -translate-x-1/2 bg-line-strong" />
            )}
            <span aria-hidden className="mt-1.5 h-3 w-3 shrink-0 rounded-full border border-teal-400/60 bg-teal-500/20" />
            <div className="min-w-0">
              <p className="font-mono text-xs text-teal-200">
                {/^-\d+$/.test(e.date.trim()) ? t("timelineBce", { year: e.date.trim().slice(1) }) : e.date}
              </p>
              <p className="text-sm font-semibold text-slate-100">{e.label}</p>
              {e.detail ? <p className="mt-0.5 text-sm text-slate-300">{e.detail}</p> : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
