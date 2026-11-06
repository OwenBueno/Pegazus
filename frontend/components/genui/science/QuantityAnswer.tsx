"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import { cn } from "@/lib/cn";
import type { WidgetAction } from "@/lib/contracts/genui";

const NUMBER = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;

/** Graded server-side: emits {value, unit}. Accepts "9,81" as 9.81. */
export function QuantityAnswer({
  question,
  unit,
  units,
  widgetId = "quantity",
  disabled = false,
  onAction,
}: {
  question: string;
  unit: string;
  units: string[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const id = useId();
  const [raw, setRaw] = useState("");
  const [chosen, setChosen] = useState(unit);

  const normalized = raw.trim().replace(",", ".");
  const value = NUMBER.test(normalized) ? Number(normalized) : NaN;
  const valid = Number.isFinite(value);
  const options = units.includes(unit) ? units : [unit, ...units];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onAction?.({ widgetId, type: "ANSWER", payload: { value, unit: chosen } });
      }}
      className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl"
    >
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("quantityAnswer")}</p>
      <label htmlFor={`${id}-v`} className="block text-[17px] leading-relaxed text-slate-50">
        {question}
      </label>
      <div className="flex gap-2">
        <input
          id={`${id}-v`}
          type="text"
          inputMode="decimal"
          value={raw}
          maxLength={40}
          disabled={disabled}
          autoComplete="off"
          aria-describedby={`${id}-h`}
          aria-invalid={raw.trim() !== "" && !valid}
          onChange={(e) => setRaw(e.target.value)}
          className={cn(inputClass, "min-w-0 flex-1")}
        />
        <label htmlFor={`${id}-u`} className="sr-only">
          {t("quantityUnit")}
        </label>
        <select
          id={`${id}-u`}
          value={chosen}
          disabled={disabled}
          onChange={(e) => setChosen(e.target.value)}
          className={cn(inputClass, "w-auto")}
        >
          {options.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </div>
      <p id={`${id}-h`} className="text-xs text-slate-400">
        {t("quantityHint")}
      </p>
      <button type="submit" disabled={disabled || !valid} className={buttonClass("primary", "md", true)}>
        {t("checkAnswer")}
      </button>
    </form>
  );
}
