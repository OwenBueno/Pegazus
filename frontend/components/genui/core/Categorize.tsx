"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side: emits {assign: {"<item>": bucket}}. Tap-select or native drag both write `assign`. */
export function Categorize({
  prompt,
  buckets,
  items,
  widgetId = "categorize",
  disabled = false,
  onAction,
}: {
  prompt?: string;
  buckets: string[];
  items: string[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [selected, setSelected] = useState<number | null>(null);
  const [assign, setAssign] = useState<Record<number, number>>({});
  const complete = items.every((_, i) => assign[i] != null);

  function put(item: number, bucket: number) {
    setAssign((a) => ({ ...a, [item]: bucket }));
    setSelected(null);
  }

  const chip = (i: number) => (
    <button
      key={i}
      type="button"
      draggable={!disabled}
      disabled={disabled}
      aria-pressed={selected === i}
      onClick={() => setSelected(selected === i ? null : i)}
      onDragStart={(e) => e.dataTransfer.setData("text/plain", String(i))}
      className={`min-h-10 rounded-control border px-3 py-1.5 text-left text-sm transition-colors ${
        selected === i
          ? "border-teal-400/60 bg-teal-500/10 text-teal-200"
          : "border-line-strong bg-surface-raised text-slate-200 hover:border-slate-500"
      }`}
    >
      {items[i]}
    </button>
  );

  const unassigned = items.map((_, i) => i).filter((i) => assign[i] == null);

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("categorize")}</p>
      {prompt ? <p className="text-sm text-slate-200">{prompt}</p> : null}
      <p className="text-xs text-slate-400">{t("categorizeHint")}</p>
      {unassigned.length > 0 && (
        <div role="group" aria-label={t("unassigned")} className="flex flex-wrap gap-2">
          {unassigned.map(chip)}
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {buckets.map((b, bi) => (
          <div
            key={bi}
            role="group"
            aria-label={b}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const i = Number(e.dataTransfer.getData("text/plain"));
              if (!disabled && Number.isInteger(i) && i >= 0 && i < items.length) put(i, bi);
            }}
            className="min-h-24 space-y-2 rounded-control border border-dashed border-line-strong bg-surface-subtle/40 p-3"
          >
            <button
              type="button"
              disabled={disabled || selected == null}
              onClick={() => selected != null && put(selected, bi)}
              className="w-full rounded-control border border-line px-3 py-1.5 text-left text-sm font-semibold text-slate-100 hover:border-teal-400/50 disabled:text-slate-400 disabled:hover:border-line"
            >
              {t("putIn", { bucket: b })}
            </button>
            <div className="flex flex-wrap gap-2">
              {items.map((_, i) => i).filter((i) => assign[i] === bi).map(chip)}
            </div>
          </div>
        ))}
      </div>
      <button
        type="button"
        disabled={disabled || !complete}
        onClick={() =>
          onAction?.({
            widgetId,
            type: "ANSWER",
            payload: { assign: Object.fromEntries(items.map((_, i) => [String(i), assign[i]])) },
          })
        }
        className={buttonClass("primary", "md", true)}
      >
        {t("checkCategories")}
      </button>
    </section>
  );
}
