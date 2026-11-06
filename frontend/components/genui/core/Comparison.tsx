"use client";

import { useTranslations } from "next-intl";

type Side = { title: string; points: string[] };

/** Two titled lists side by side (stacked on mobile). Display-only. */
export function Comparison({ left, right }: { left: Side; right: Side }) {
  const t = useTranslations("session");
  return (
    <section
      aria-label={t("comparison")}
      className="grid gap-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl sm:grid-cols-2"
    >
      {[left, right].map((s, k) => (
        <div key={k} className="space-y-2">
          <h3 className={`font-display text-[15px] font-semibold ${k ? "text-indigo-200" : "text-teal-200"}`}>
            {s.title}
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-200 marker:text-slate-500">
            {s.points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
