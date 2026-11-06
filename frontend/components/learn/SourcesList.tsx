"use client";

import { useTranslations } from "next-intl";
import { ExternalLink } from "lucide-react";
import type { LessonSource } from "@/lib/api";

/** Research citations of a lesson (server already limits these to fetched http(s) sources). */
export function SourcesList({ sources }: { sources?: LessonSource[] | null }) {
  const t = useTranslations("session");
  const safe = (sources ?? []).filter((s) => /^https?:\/\//i.test(s.url));
  if (!safe.length) return null;
  return (
    <section aria-label={t("sourcesTitle")} className="space-y-1.5 border-t border-line pt-3">
      <h3 className="font-mono text-micro uppercase tracking-[0.14em] text-slate-500">{t("sourcesTitle")}</h3>
      <ul className="space-y-1 text-xs">
        {safe.map((s) => (
          <li key={s.url}>
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="inline-flex min-h-6 items-center gap-1 text-teal-200 underline underline-offset-2 hover:text-teal-100"
            >
              {s.title || s.url}
              <ExternalLink className="h-3 w-3" aria-hidden />
              <span className="sr-only">{t("sourceNewTab")}</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
