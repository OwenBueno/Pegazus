"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side: emits {text}. */
export function ShortAnswer({
  question,
  widgetId = "short",
  disabled = false,
  onAction,
}: {
  question: string;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const id = useId();
  const [text, setText] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) onAction?.({ widgetId, type: "ANSWER", payload: { text: text.trim() } });
      }}
      className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl"
    >
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("shortAnswer")}</p>
      <label htmlFor={id} className="block text-[17px] leading-relaxed text-slate-50">
        {question}
      </label>
      <input
        id={id}
        value={text}
        maxLength={500}
        disabled={disabled}
        autoComplete="off"
        onChange={(e) => setText(e.target.value)}
        className={inputClass}
      />
      <button type="submit" disabled={disabled || !text.trim()} className={buttonClass("primary", "md", true)}>
        {t("checkAnswer")}
      </button>
    </form>
  );
}
