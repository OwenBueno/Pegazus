"use client";

import { useTranslations } from "next-intl";
import { ExternalLink } from "lucide-react";

/** Primary-source quote with attribution. Display-only. */
export function SourceExcerpt({
  quote,
  author,
  source,
  year,
  url,
}: {
  quote: string;
  author?: string;
  source?: string;
  year?: number;
  url?: string;
}) {
  const t = useTranslations("session");
  const meta = [
    author,
    source,
    year === undefined ? undefined : year < 0 ? t("timelineBce", { year: -year }) : String(year),
  ].filter(Boolean);
  const safeUrl = url && /^https?:\/\//i.test(url) ? url : undefined;

  return (
    <figure className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("sourceExcerpt")}</p>
      <blockquote className="border-l-2 border-teal-400/50 pl-4 text-[17px] italic leading-relaxed text-slate-50">
        {quote}
      </blockquote>
      {(meta.length > 0 || safeUrl) && (
        <figcaption className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-300">
          {meta.length > 0 && <span>— {meta.join(", ")}</span>}
          {safeUrl && (
            <a
              href={safeUrl}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="inline-flex items-center gap-1 text-teal-200 underline underline-offset-2 hover:text-teal-100"
            >
              {t("sourceOpen")}
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              <span className="sr-only">{t("sourceNewTab")}</span>
            </a>
          )}
        </figcaption>
      )}
    </figure>
  );
}
