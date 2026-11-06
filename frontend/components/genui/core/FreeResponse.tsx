"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import type { WidgetAction } from "@/lib/contracts/genui";

const MIN_WORDS = 5;

/** Graded server-side (rubric): emits {text}. */
export function FreeResponse({
  question,
  max_words,
  widgetId = "free",
  disabled = false,
  onAction,
}: {
  question: string;
  max_words: number;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const id = useId();
  const [text, setText] = useState("");
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const ok = words >= MIN_WORDS && words <= max_words;

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("freeResponse")}</p>
      <label htmlFor={id} className="block text-[17px] leading-relaxed text-slate-50">
        {question}
      </label>
      <textarea
        id={id}
        value={text}
        rows={5}
        maxLength={1500}
        disabled={disabled}
        aria-describedby={`${id}-count`}
        onChange={(e) => setText(e.target.value)}
        className={`${inputClass} py-3`}
      />
      <div className="flex flex-wrap justify-between gap-2 text-xs">
        <span className="text-slate-400">{words < MIN_WORDS ? t("tooFewWords") : null}</span>
        <span
          id={`${id}-count`}
          aria-live="polite"
          className={words > max_words ? "text-neuro-alert" : "text-slate-400"}
        >
          {t("wordCount", { count: words, max: max_words })}
        </span>
      </div>
      <button
        type="button"
        disabled={disabled || !ok}
        onClick={() => onAction?.({ widgetId, type: "ANSWER", payload: { text: text.trim() } })}
        className={buttonClass("primary", "md", true)}
      >
        {t("checkAnswer")}
      </button>
    </section>
  );
}
