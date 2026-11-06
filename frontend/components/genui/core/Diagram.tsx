"use client";

import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";

/** Mermaid or raw SVG, always DOMPurify-sanitized before injection. Display-only; loaded lazily. */
export function Diagram({ kind, source, alt }: { kind: "mermaid" | "svg"; source: string; alt: string }) {
  const t = useTranslations("session");
  const renderId = `diagram-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const key = `${kind}:${source}`;
  const [out, setOut] = useState<{ key: string; svg?: string; failed?: boolean }>({ key: "" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let svg = source;
        if (kind === "mermaid") {
          const mermaid = (await import("mermaid")).default;
          // DOMPurify's svg profile drops <foreignObject>, so labels must be plain SVG text.
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: "strict",
            theme: "dark",
            htmlLabels: false,
            flowchart: { htmlLabels: false },
          });
          svg = (await mermaid.render(renderId, source)).svg;
        }
        const DOMPurify = (await import("dompurify")).default;
        const clean = DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true } });
        if (!cancelled) setOut({ key, svg: clean, failed: !clean.trim() });
      } catch {
        if (!cancelled) setOut({ key, failed: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [key, kind, source, renderId]);

  const current = out.key === key ? out : null;
  if (current?.failed) return <p className="rounded-panel border border-line bg-surface-glass p-5 text-sm text-slate-300">{alt}</p>;
  return (
    <figure
      role="img"
      aria-label={alt}
      className="overflow-x-auto rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
    >
      {current?.svg ? (
        <div aria-hidden dangerouslySetInnerHTML={{ __html: current.svg }} />
      ) : (
        <p aria-hidden className="text-center text-sm text-slate-400">
          {t("diagramLoading")}
        </p>
      )}
      <figcaption className="sr-only">{alt}</figcaption>
    </figure>
  );
}
