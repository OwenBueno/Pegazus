"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side: emits {value}; the session verdict banner shows the result. */
export function NumberLine({
  min,
  max,
  step = 1,
  prompt,
  widgetId = "nline",
  disabled = false,
  onAction,
}: {
  min: number;
  max: number;
  step?: number;
  prompt?: string;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [value, setValue] = useState(min);

  const ticks = useMemo(() => {
    const out: number[] = [];
    for (let x = min; x <= max + 1e-9; x += step) out.push(Number(x.toFixed(6)));
    return out;
  }, [min, max, step]);

  const pct = ((value - min) / (max - min)) * 100;

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">
        {t("numberLine")}
      </p>
      {prompt ? <p className="text-sm text-slate-200">{prompt}</p> : null}
      <div className="relative mx-4 h-12">
        <div className="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-white/10" />
        {ticks.map((x) => {
          const p = ((x - min) / (max - min)) * 100;
          return (
            <button
              key={x}
              type="button"
              disabled={disabled}
              aria-label={`${x}`}
              aria-pressed={value === x}
              onClick={() => setValue(x)}
              className="absolute top-1/2 grid h-11 w-6 -translate-x-1/2 -translate-y-1/2 place-items-center before:h-3 before:w-3 before:rounded-full before:border before:border-slate-500 before:bg-surface-raised before:content-[''] hover:before:border-neuro-teal"
              style={{ left: `${p}%` }}
            />
          );
        })}
        <div
          className="pointer-events-none absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white/80 bg-neuro-teal shadow-[0_0_16px_rgb(20_184_166/0.6)] transition-[left] duration-200 ease-out"
          style={{ left: `${pct}%` }}
          aria-hidden
        />
      </div>
      <p className="font-mono text-sm text-slate-300">
        {t("numberLineValue", { value: String(value) })}
      </p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction?.({ widgetId, type: "NUMBER_LINE", payload: { value } })}
        className={buttonClass("primary", "md", true)}
      >
        {t("checkPlace")}
      </button>
    </section>
  );
}
