"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import type { WidgetAction } from "@/lib/contracts/genui";
import { PrimerMarkdown, stripFences } from "@/components/learn/PrimerMarkdown";
import { CodeBlock, type CodeLanguage } from "./CodeBlock";

/** Graded server-side (exact): emits {text}. */
export function PredictOutput({
  language,
  code,
  prompt,
  widgetId = "predict",
  disabled = false,
  onAction,
}: {
  language: CodeLanguage;
  code: string;
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
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("predictTitle")}</p>
      {prompt && stripFences(prompt) ? (
        <div className="text-[17px] [&_p]:text-[17px] [&_p]:text-slate-50">
          <PrimerMarkdown source={stripFences(prompt)} />
        </div>
      ) : null}
      <CodeBlock language={language} code={code} />
      <label htmlFor={id} className="block text-sm font-medium text-slate-200">
        {t("predictLabel")}
      </label>
      <textarea
        id={id}
        value={text}
        rows={3}
        maxLength={200}
        disabled={disabled}
        spellCheck={false}
        autoComplete="off"
        onChange={(e) => setText(e.target.value)}
        className={`${inputClass} py-3 font-mono`}
      />
      <button type="submit" disabled={disabled || !text.trim()} className={buttonClass("primary", "md", true)}>
        {t("checkAnswer")}
      </button>
    </form>
  );
}
