"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import "katex/dist/katex.min.css";

/** mhchem formula/equation via KaTeX (lazy). Display-only; falls back to raw source on render failure. */
export function ChemFormula({ latex, caption }: { latex: string; caption?: string }) {
  const t = useTranslations("session");
  const [out, setOut] = useState<{ key: string; html?: string; failed?: boolean }>({ key: "" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const katex = (await import("katex")).default;
        // @ts-expect-error -- katex ships no types for contrib/mhchem; side-effect import registers \ce / \pu
        await import("katex/contrib/mhchem");
        // ponytail: server skips mhchem validation, so a bad formula only surfaces here → raw-text fallback.
        const html = katex.renderToString(latex, {
          throwOnError: true,
          trust: false,
          displayMode: true,
          output: "htmlAndMathml",
        });
        if (!cancelled) setOut({ key: latex, html });
      } catch {
        if (!cancelled) setOut({ key: latex, failed: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [latex]);

  const current = out.key === latex ? out : null;
  return (
    <figure className="space-y-2 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("chemFormula")}</p>
      {current?.html ? (
        // KaTeX output with trust:false is safe to inject; MathML half gives screen readers text.
        <div className="overflow-x-auto text-slate-50" dangerouslySetInnerHTML={{ __html: current.html }} />
      ) : current?.failed ? (
        <code className="block overflow-x-auto rounded-control border border-line bg-surface-raised px-3 py-2 font-mono text-sm text-slate-200">
          {latex}
        </code>
      ) : (
        <p className="text-center text-sm text-slate-400">{t("chemLoading")}</p>
      )}
      {caption ? <figcaption className="text-sm text-slate-300">{caption}</figcaption> : null}
    </figure>
  );
}
