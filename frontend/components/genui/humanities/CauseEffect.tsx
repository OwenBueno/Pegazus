"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";

/** Cause → effect pairs. Display-only. */
export function CauseEffect({ title, links }: { title?: string; links: { cause: string; effect: string }[] }) {
  const t = useTranslations("session");
  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{title ?? t("causeEffect")}</p>
      <ul className="space-y-2">
        {links.map((l, i) => (
          <li
            key={i}
            className="flex flex-col gap-2 rounded-control border border-line bg-surface-raised p-3 text-sm sm:flex-row sm:items-center"
          >
            <span className="flex-1 text-slate-100">{l.cause}</span>
            <ArrowRight className="h-4 w-4 shrink-0 rotate-90 text-teal-300 sm:rotate-0" aria-hidden />
            <span className="sr-only">{t("causeLeadsTo")}</span>
            <span className="flex-1 text-teal-100">{l.effect}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
