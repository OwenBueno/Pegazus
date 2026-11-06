"use client";

import { useTranslations } from "next-intl";

/** Glossary of terms. Display-only. */
export function KeyTerms({ terms }: { terms: { term: string; def: string }[] }) {
  const t = useTranslations("session");
  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("keyTerms")}</p>
      <dl className="space-y-2.5">
        {terms.map((k, i) => (
          <div key={i}>
            <dt className="text-sm font-semibold text-teal-200">{k.term}</dt>
            <dd className="text-sm text-slate-300">{k.def}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
