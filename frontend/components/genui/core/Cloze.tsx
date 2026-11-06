"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

const blankClass =
  "mx-1 inline-block h-9 w-32 max-w-full rounded-control border border-line-strong bg-background/60 px-2 align-baseline text-slate-100 outline-none focus:border-neuro-indigo focus:ring-4 focus:ring-neuro-indigo/15";

/** Text segments with an input between each consecutive pair; `offset` indexes into the shared blanks array. */
export function InlineBlanks({
  segments,
  values,
  offset = 0,
  label,
  disabled,
  onChange,
}: {
  segments: string[];
  values: string[];
  offset?: number;
  label: (n: number) => string;
  disabled?: boolean;
  onChange: (index: number, value: string) => void;
}) {
  return (
    <span className="leading-[2.6]">
      {segments.map((seg, i) => (
        <span key={i}>
          {seg}
          {i < segments.length - 1 && (
            <input
              aria-label={label(i + 1)}
              value={values[offset + i] ?? ""}
              maxLength={100}
              disabled={disabled}
              autoComplete="off"
              onChange={(e) => onChange(offset + i, e.target.value)}
              className={blankClass}
            />
          )}
        </span>
      ))}
    </span>
  );
}

/** Graded server-side: emits {blanks}. */
export function Cloze({
  prompt,
  segments,
  widgetId = "cloze",
  disabled = false,
  onAction,
}: {
  prompt?: string;
  segments: string[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [blanks, setBlanks] = useState(() => Array<string>(segments.length - 1).fill(""));

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("fillBlanks")}</p>
      {prompt ? <p className="text-sm text-slate-200">{prompt}</p> : null}
      <p className="text-[17px] text-slate-50">
        <InlineBlanks
          segments={segments}
          values={blanks}
          label={(n) => t("blankN", { n })}
          disabled={disabled}
          onChange={(i, v) => setBlanks((b) => b.map((x, j) => (j === i ? v : x)))}
        />
      </p>
      <button
        type="button"
        disabled={disabled || blanks.some((b) => !b.trim())}
        onClick={() => onAction?.({ widgetId, type: "ANSWER", payload: { blanks: blanks.map((b) => b.trim()) } })}
        className={buttonClass("primary", "md", true)}
      >
        {t("checkAnswer")}
      </button>
    </section>
  );
}
