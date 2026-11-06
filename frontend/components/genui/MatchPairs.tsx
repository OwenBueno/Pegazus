"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side: emits {pairs: [[left, right]]} by index; rights arrive pre-shuffled. */
export function MatchPairs({
  prompt,
  lefts,
  rights,
  widgetId = "match",
  disabled = false,
  onAction,
}: {
  prompt?: string;
  lefts: string[];
  rights: string[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [assigned, setAssigned] = useState<Record<number, number>>({});
  const complete = lefts.every((_, i) => assigned[i] != null);

  function pickRight(r: number) {
    if (selectedLeft == null) return;
    // One right per left: drop r from any other left first.
    const next = Object.fromEntries(Object.entries(assigned).filter(([, v]) => v !== r));
    setAssigned({ ...next, [selectedLeft]: r });
    setSelectedLeft(null);
  }

  const btn = "min-h-12 w-full rounded-control border px-3 py-2 text-left text-sm transition-colors";
  const idle = "border-line-strong bg-surface-raised text-slate-200 hover:border-slate-500";
  const active = "border-teal-400/60 bg-teal-500/10 text-teal-200";

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">
        {t("matchPairs")}
      </p>
      {prompt ? <p className="text-sm text-slate-200">{prompt}</p> : null}
      <div className="grid grid-cols-2 gap-3">
        <ul className="space-y-2">
          {lefts.map((label, i) => (
            <li key={i}>
              <button
                type="button"
                disabled={disabled}
                aria-pressed={selectedLeft === i}
                onClick={() => setSelectedLeft(i)}
                className={`${btn} ${selectedLeft === i ? active : idle}`}
              >
                {label}
                {assigned[i] != null && (
                  <span className="mt-1 block text-xs text-slate-400">→ {rights[assigned[i]]}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
        <ul className="space-y-2">
          {rights.map((label, r) => {
            const used = Object.values(assigned).includes(r);
            return (
              <li key={r}>
                <button
                  type="button"
                  disabled={disabled || selectedLeft == null}
                  onClick={() => pickRight(r)}
                  className={`${btn} ${used ? "border-line bg-transparent text-slate-400" : idle}`}
                >
                  {label}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      <button
        type="button"
        disabled={disabled || !complete}
        onClick={() =>
          onAction?.({
            widgetId,
            type: "MATCH_PAIRS",
            payload: { pairs: lefts.map((_, i) => [i, assigned[i]]) },
          })
        }
        className={buttonClass("primary", "md", true)}
      >
        {t("checkMatches")}
      </button>
    </section>
  );
}
