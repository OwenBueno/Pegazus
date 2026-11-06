"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { Lightbulb } from "lucide-react";

export function SocraticDialogueBox({
  prompt,
  hintTier,
  highlightElementId,
}: {
  prompt: string;
  hintTier: 1 | 2 | 3;
  highlightElementId?: string;
}) {
  const t = useTranslations("session");

  useEffect(() => {
    if (!highlightElementId) return;
    const el = document.getElementById(highlightElementId);
    if (!el) return;
    el.classList.add("ring-2", "ring-neuro-teal/60");
    const tmr = window.setTimeout(() => {
      el.classList.remove("ring-2", "ring-neuro-teal/60");
    }, 2400);
    return () => {
      window.clearTimeout(tmr);
      el.classList.remove("ring-2", "ring-neuro-teal/60");
    };
  }, [highlightElementId]);

  return (
    <aside
      className="rounded-panel border border-amber-400/20 bg-amber-500/[0.05] px-4 py-3.5 animate-fade-in"
      aria-live="polite"
    >
      <div className="mb-1.5 flex items-center gap-1.5 font-mono text-micro uppercase tracking-[0.14em] text-amber-200/90">
        <Lightbulb className="h-3.5 w-3.5" aria-hidden />
        {t("hint")} · {t("hintTier", { n: hintTier })}
      </div>
      <p className="text-sm leading-relaxed text-slate-200">{prompt}</p>
    </aside>
  );
}
