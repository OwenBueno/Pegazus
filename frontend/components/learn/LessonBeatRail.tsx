"use client";

import {
  AlertTriangle,
  BookOpen,
  Check,
  ClipboardCheck,
  Globe2,
  Lightbulb,
  ListOrdered,
  MessageCircle,
  PencilLine,
  Sparkles,
  Star,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { createElement } from "react";
import { useTranslations } from "next-intl";
import type { LessonBeat } from "@/lib/api";
import { cn } from "@/lib/cn";

const ICONS: Record<string, LucideIcon> = {
  intro: Sparkles,
  hook: Sparkles,
  concept: Lightbulb,
  worked_example: ListOrdered,
  try_it: ListOrdered,
  important_fact: Star,
  important: Star,
  fun_fact: Zap,
  common_mistake: AlertTriangle,
  real_world: Globe2,
  more_learning: BookOpen,
  reflection: MessageCircle,
  summary: ClipboardCheck,
  problem: PencilLine,
};

export function BeatIcon({ type, className = "h-3.5 w-3.5" }: { type: string; className?: string }) {
  return createElement(ICONS[type] ?? Lightbulb, { className, "aria-hidden": true });
}

export function beatLabel(b: LessonBeat, problemLabel: string): string {
  return b.title?.trim() || (b.type === "problem" ? problemLabel : b.type.replace(/_/g, " "));
}

export function LessonBeatRail({
  beats,
  currentIndex,
  onSelect,
}: {
  beats: LessonBeat[];
  currentIndex: number;
  /** Jump to an already-visited beat. */
  onSelect?: (index: number) => void;
}) {
  const t = useTranslations("session");
  return (
    <aside className="hidden w-64 shrink-0 lg:block" aria-label={t("beatRail")}>
      <div className="sticky top-20 rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl">
        <p className="mb-3 px-2 font-mono text-micro uppercase tracking-[0.14em] text-slate-500">{t("beatRail")}</p>
        <ol className="relative space-y-0.5">
          {beats.map((b, i) => {
            const active = i === currentIndex;
            const done = i < currentIndex;
            const pending = b.type === "problem" && !b.item_id;
            const body = (
              <>
                <span
                  className={cn(
                    "relative z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full border text-[11px] transition-colors",
                    active
                      ? "border-indigo-400/60 bg-neuro-indigo text-white"
                      : done
                        ? "border-teal-500/40 bg-teal-500/15 text-teal-300"
                        : "border-line-strong bg-surface text-slate-500",
                    pending && "animate-pulse",
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" aria-hidden /> : <BeatIcon type={b.type} />}
                </span>
                <span className="min-w-0 truncate capitalize">{beatLabel(b, t("beatProblem"))}</span>
              </>
            );
            return (
              <li key={`${b.type}-${i}`} aria-current={active ? "step" : undefined} className="relative">
                {active ? (
                  <motion.span
                    layoutId="beat-active"
                    className="absolute inset-0 rounded-xl bg-white/[0.05]"
                    transition={{ type: "spring", stiffness: 420, damping: 36 }}
                  />
                ) : null}
                {done && onSelect ? (
                  <button
                    type="button"
                    onClick={() => onSelect(i)}
                    className="relative flex min-h-11 w-full items-center gap-3 rounded-xl px-2 text-left text-sm text-slate-400 hover:text-slate-100"
                  >
                    {body}
                  </button>
                ) : (
                  <div
                    className={cn(
                      "relative flex min-h-11 items-center gap-3 px-2 text-sm",
                      active ? "font-medium text-slate-50" : "text-slate-500",
                    )}
                  >
                    {body}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </aside>
  );
}
