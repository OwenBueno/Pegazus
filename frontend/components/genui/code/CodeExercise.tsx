"use client";

import { useId, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import { Badge } from "@/components/ui/primitives";
import type { WidgetAction } from "@/lib/contracts/genui";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import { pythonLoaded, runTests, TIMEOUT, type RunResult, type Test } from "@/lib/runners/run";
import { LANGUAGE_NAME, type CodeLanguage } from "./CodeBlock";

/** Checked client-side in a Worker (Doc 10 R2, decided_by CLIENT): emits {passed, total, code}. */
export function CodeExercise({
  language,
  starter,
  tests,
  prompt,
  beta = false,
  widgetId = "code",
  disabled = false,
  onAction,
}: {
  language: CodeLanguage;
  starter: string;
  tests: Test[];
  prompt?: string;
  beta?: boolean;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const id = useId();
  const [code, setCode] = useState(starter);
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<{ code: string; result: RunResult } | null>(null);
  const escaped = useRef(false);
  const result = run?.result;
  const firstPythonLoad = running && language === "python" && !pythonLoaded();

  async function onRun() {
    setRunning(true);
    try {
      setRun({ code, result: await runTests(language, code, tests) });
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("codeExerciseTitle")}</p>
        <Badge tone="indigo">{LANGUAGE_NAME[language]}</Badge>
        {beta ? (
          <>
            <Badge tone="amber" aria-describedby={`${id}-beta`}>
              {t("codeBeta")}
            </Badge>
            <span id={`${id}-beta`} className="text-xs text-slate-400">
              {t("codeBetaHint")}
            </span>
          </>
        ) : null}
      </div>
      {prompt ? (
        <div className="text-[17px] [&_p]:text-[17px] [&_p]:text-slate-50">
          <PrimerMarkdown source={prompt} />
        </div>
      ) : null}

      <label htmlFor={id} className="block text-sm font-medium text-slate-200">
        {t("codeEditorLabel")}
      </label>
      <p id={`${id}-hint`} className="text-xs text-slate-400">
        {t("codeEditorHint")}
      </p>
      {/* ponytail: plain textarea editor (Tab = 4 spaces, Esc then Tab leaves). Upgrade = CodeMirror if learners ask. */}
      <textarea
        id={id}
        value={code}
        rows={Math.min(16, Math.max(6, code.split("\n").length + 1))}
        maxLength={3000}
        disabled={disabled}
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        aria-describedby={`${id}-hint`}
        onChange={(e) => setCode(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            escaped.current = true;
            return;
          }
          const wasEscaped = escaped.current;
          escaped.current = false;
          if (e.key !== "Tab" || e.shiftKey || wasEscaped) return;
          e.preventDefault();
          const el = e.currentTarget;
          el.setRangeText("    ", el.selectionStart, el.selectionEnd, "end");
          setCode(el.value);
        }}
        className={`${inputClass} py-3 font-mono text-sm leading-relaxed`}
      />

      <div aria-live="polite" className="space-y-2">
        <p className="text-sm font-medium text-slate-200">
          {result ? t("codeSummary", { passed: result.passed, total: result.total }) : t("codeTests")}
        </p>
        <ul className="space-y-1.5">
          {tests.map((tc, i) => {
            const r = result?.results[i];
            return (
              <li key={i} className="flex flex-wrap items-center gap-2 text-sm">
                {r ? (
                  r.ok ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-neuro-teal" aria-hidden />
                  ) : (
                    <XCircle className="h-4 w-4 shrink-0 text-neuro-alert" aria-hidden />
                  )
                ) : null}
                {r ? <span className="sr-only">{r.ok ? t("codePassed") : t("codeFailed")}</span> : null}
                <code className="rounded bg-white/5 px-1.5 font-mono text-slate-200">{tc.call}</code>
                <span aria-hidden className="text-slate-500">
                  →
                </span>
                <span className="sr-only">{t("codeExpected")}</span>
                {tc.stdout ? <span className="text-xs text-slate-400">{t("codeOutput")}:</span> : null}
                <code className="whitespace-pre-wrap rounded bg-white/5 px-1.5 font-mono text-slate-200">
                  {tc.stdout ?? tc.expect}
                </code>
                {r && !r.ok && (r.error || r.got) ? (
                  <span className="whitespace-pre-wrap font-mono text-xs text-rose-200">
                    {r.error ?? t("codeGot", { value: r.got ?? "" })}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
        {result?.error ? (
          <p className="text-sm text-neuro-alert">
            {result.error === TIMEOUT ? t("codeTimeout") : `${t("codeError")}: ${result.error}`}
          </p>
        ) : null}
        {result?.stdout ? (
          <div>
            <p id={`${id}-out`} className="text-xs text-slate-400">
              {t("codeOutput")}
            </p>
            <pre
              role="region"
              tabIndex={0}
              aria-labelledby={`${id}-out`}
              className="max-h-40 overflow-auto rounded-control bg-slate-950/70 p-3 font-mono text-xs text-slate-300">
              {result.stdout}
            </pre>
          </div>
        ) : null}
      </div>
      {firstPythonLoad ? (
        <p role="status" className="text-xs text-slate-400">
          {t("codeLoadingPython")}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" loading={running} disabled={disabled} onClick={onRun}>
          {running ? t("codeRunning") : t("codeRun")}
        </Button>
        <Button
          disabled={disabled || running || !result || run?.code !== code}
          aria-describedby={`${id}-submit`}
          onClick={() =>
            result && onAction?.({ widgetId, type: "ANSWER", payload: { passed: result.passed, total: result.total, code } })
          }
        >
          {t("codeSubmit")}
        </Button>
      </div>
      <p id={`${id}-submit`} className="text-xs text-slate-400">
        {t("codeSubmitHint")}
      </p>
    </section>
  );
}
