"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side (exact, then rubric): emits {text}. */
export function TranslationAnswer({
  source,
  lang,
  prompt,
  widgetId = "translation",
  disabled = false,
  onAction,
}: {
  source: string;
  lang: string;
  prompt?: string;
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
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("translateTitle")}</p>
      {prompt && <p className="text-sm text-slate-300">{prompt}</p>}
      <p
        id={`${id}-src`}
        className="rounded-control border border-line-strong bg-surface-raised p-4 text-[17px] leading-relaxed text-slate-50"
      >
        {source}
      </p>
      <label htmlFor={id} className="block text-sm text-slate-300">
        {t("translateInputLabel")}
      </label>
      <input
        id={id}
        lang={lang}
        value={text}
        maxLength={500}
        disabled={disabled}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        aria-describedby={`${id}-src`}
        onChange={(e) => setText(e.target.value)}
        className={inputClass}
      />
      <button type="submit" disabled={disabled || !text.trim()} className={buttonClass("primary", "md", true)}>
        {t("checkAnswer")}
      </button>
    </form>
  );
}
