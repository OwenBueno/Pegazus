"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";

/** Optional sanitized SVG with numbered label markers at fractional x,y; ordered list is the text alternative. */
export function LabeledDiagram({
  source,
  labels,
  alt,
}: {
  source?: string;
  labels: { x: number; y: number; text: string }[];
  alt: string;
}) {
  const t = useTranslations("session");
  const [out, setOut] = useState<{ key: string; svg: string }>({ key: "", svg: "" });

  useEffect(() => {
    if (!source) return;
    let cancelled = false;
    (async () => {
      try {
        const DOMPurify = (await import("dompurify")).default;
        const clean = DOMPurify.sanitize(source, { USE_PROFILES: { svg: true, svgFilters: true } });
        if (!cancelled) setOut({ key: source, svg: clean });
      } catch {
        if (!cancelled) setOut({ key: source, svg: "" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source]);

  const svg = source && out.key === source ? out.svg : "";

  return (
    <figure className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("labeledDiagram")}</p>
      <div
        role="img"
        aria-label={alt}
        className="relative aspect-[4/3] w-full overflow-hidden rounded-control border border-line bg-surface-raised"
      >
        {svg ? (
          <div aria-hidden className="absolute inset-0 [&_svg]:h-full [&_svg]:w-full" dangerouslySetInnerHTML={{ __html: svg }} />
        ) : null}
        {labels.map((l, i) => {
          const flip = l.x > 0.6;
          return (
            <div
              key={i}
              aria-hidden
              style={{ left: `${l.x * 100}%`, top: `${l.y * 100}%` }}
              className={cn(
                "absolute flex -translate-y-1/2 items-center gap-1",
                flip ? "flex-row-reverse -translate-x-[calc(100%-0.625rem)]" : "-translate-x-2.5",
              )}
            >
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-indigo-400 text-micro font-semibold text-slate-950">
                {i + 1}
              </span>
              <span className="max-w-[10rem] rounded-control border border-line-strong bg-surface-glass px-1.5 py-0.5 text-micro leading-tight text-slate-100 backdrop-blur">
                {l.text}
              </span>
            </div>
          );
        })}
      </div>
      <figcaption className="space-y-1">
        <span className="sr-only">{alt}</span>
        <span className="block font-mono text-micro uppercase tracking-[0.14em] text-slate-400">{t("labeledLegend")}</span>
        <ol className="list-decimal space-y-0.5 pl-5 text-sm text-slate-300 marker:text-indigo-300">
          {labels.map((l, i) => (
            <li key={i}>{l.text}</li>
          ))}
        </ol>
      </figcaption>
    </figure>
  );
}
