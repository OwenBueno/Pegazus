"use client";

import { AlertTriangle, Lightbulb, Star } from "lucide-react";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";

const TONES = {
  tip: { box: "border-teal-500/25 bg-teal-500/[0.06]", title: "text-teal-200", Icon: Lightbulb },
  warning: { box: "border-amber-500/25 bg-amber-500/[0.06]", title: "text-amber-200", Icon: AlertTriangle },
  fact: { box: "border-indigo-400/25 bg-indigo-500/[0.07]", title: "text-indigo-200", Icon: Star },
} as const;

/** One highlighted tip / warning / fact. Display-only. */
export function Callout({
  tone,
  title,
  body_md,
}: {
  tone: keyof typeof TONES;
  title?: string;
  body_md: string;
}) {
  const t = TONES[tone] ?? TONES.tip;
  return (
    <aside role="note" className={`flex gap-3 rounded-panel border p-4 sm:p-5 ${t.box}`}>
      <t.Icon className={`mt-0.5 h-5 w-5 shrink-0 ${t.title}`} aria-hidden />
      <div className="min-w-0">
        {title ? <p className={`mb-1.5 font-display text-[15px] font-semibold ${t.title}`}>{title}</p> : null}
        <PrimerMarkdown source={body_md} />
      </div>
    </aside>
  );
}
