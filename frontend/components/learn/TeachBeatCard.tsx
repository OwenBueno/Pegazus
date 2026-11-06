"use client";

import type { ReactNode } from "react";
import { BeatIcon } from "@/components/learn/LessonBeatRail";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

const TEAL = "text-neuro-teal bg-teal-500/10 border-teal-500/25";
const INDIGO = "text-indigo-300 bg-indigo-500/10 border-indigo-400/25";
const AMBER = "text-amber-200 bg-amber-500/10 border-amber-400/25";
const MUTED = "text-slate-400 bg-white/[0.03] border-line";

const TYPE_TONE: Record<string, string> = {
  hook: TEAL,
  intro: TEAL,
  real_world: TEAL,
  fun_fact: TEAL,
  worked_example: TEAL,
  try_it: TEAL,
  important_fact: INDIGO,
  important: INDIGO,
  common_mistake: AMBER,
};

/** Icon chip + beat-type label shown above teach content. */
export function BeatEyebrow({ type }: { type: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-micro uppercase tracking-[0.12em]",
        TYPE_TONE[type] ?? MUTED,
      )}
    >
      <BeatIcon type={type} />
      {type.replace(/_/g, " ")}
    </span>
  );
}

export function TeachBeatCard({
  type,
  title,
  children,
}: {
  type: string;
  title?: string;
  children: ReactNode;
}) {
  return (
    <Card variant="glass" className="space-y-3">
      <BeatEyebrow type={type} />
      {title?.trim() ? (
        <h2 className="font-display text-xl font-semibold text-slate-50">{title}</h2>
      ) : null}
      {children}
    </Card>
  );
}
