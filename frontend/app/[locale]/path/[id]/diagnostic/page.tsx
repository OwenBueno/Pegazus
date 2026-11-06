"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { Target } from "lucide-react";
import { motion } from "motion/react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageHeader, Skeleton } from "@/components/ui/primitives";
import { MathField } from "@/components/math/MathField";
import { MathText } from "@/components/math/MathText";
import { MathNotation, PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import { WorkspaceRenderer } from "@/components/genui/WorkspaceRenderer";
import { inputClass } from "@/components/ui/FormField";
import { ANSWER_ACTIONS, AnyWidgetSchema, type WidgetAction } from "@/lib/contracts/genui";
import {
  answerDiagnostic,
  answerFor,
  getMe,
  isProfileComplete,
  startDiagnostic,
  type DiagnosticProbe,
  type PartAnswer,
} from "@/lib/api";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";

export default function DiagnosticPage() {
  const t = useTranslations("diagnostic");
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const pathId = typeof params.id === "string" ? params.id : params.id?.[0];
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [probe, setProbe] = useState<DiagnosticProbe | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef(0);

  useEffect(() => {
    if (!pathId) return;
    let cancelled = false;
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const tok = data.session?.access_token;
      if (!tok) {
        router.replace("/signin");
        return;
      }
      try {
        const me = await getMe(tok);
        if (!isProfileComplete(me)) {
          router.replace("/age");
          return;
        }
        setToken(tok);
        const first = await startDiagnostic(tok, pathId);
        if (!cancelled) {
          setProbe(first);
          startedAt.current = Date.now();
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("error"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pathId, router, t]);

  const part = probe?.parts?.[0];
  // Same widgets as the session (QuickCheck, MatchPairs, OrderSteps, Cloze, …): each owns its
  // submit. sympy → MathField; anything without a widget (e.g. numeric) → plain text input.
  const parsed =
    part && part.grader !== "sympy"
      ? AnyWidgetSchema.safeParse({ id: "probe", type: part.component, visible: true, props: part.props })
      : null;
  const widget = parsed?.success ? parsed.data : null;

  function onWidgetAction(a: WidgetAction) {
    if (ANSWER_ACTIONS.has(a.type) && a.payload && typeof a.payload === "object") void submit(a.payload as PartAnswer);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void submit(answerFor(part?.grader ?? "sympy", input));
  }

  async function submit(answer: PartAnswer) {
    if (!token || !pathId || !probe || probe.done || busy) return;
    if (!probe.node_id || !probe.item_id) return;
    setBusy(true);
    setError(null);
    try {
      const next = await answerDiagnostic(token, pathId, {
        node_id: probe.node_id,
        item_id: probe.item_id,
        answer,
        latency_ms: Date.now() - startedAt.current,
        probe_index: probe.probe_index,
      });
      setProbe(next);
      setInput("");
      startedAt.current = Date.now();
      if (next.done) {
        router.push(`/path/${pathId}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell width="narrow">
      <PageHeader eyebrow={probe ? t("probe", { n: probe.probe_index }) : undefined} title={t("title")} description={t("subtitle")} />
      {!probe && !error && (
        <div role="status" className="space-y-4">
          <span className="sr-only">…</span>
          <Skeleton className="h-32 rounded-panel" />
          <Skeleton className="h-12" />
        </div>
      )}
      {probe && !probe.done && (
        <motion.div
          key={probe.probe_index}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-5"
        >
          {(probe.statement_latex || probe.prompt_md) && (
            <Card variant="glass" className="space-y-3">
              <CardHeader
                icon={<Target className="h-3.5 w-3.5" aria-hidden />}
                label={probe.node_title || t("probe", { n: probe.probe_index })}
                tone="text-indigo-300"
                className="mb-3"
              />
              <MathNotation.Provider value={!probe.notation || probe.notation === "math" || probe.notation === "chem"}>
                {probe.prompt_md && <PrimerMarkdown source={probe.prompt_md} />}
              </MathNotation.Provider>
              {probe.statement_latex && (
                <div className="overflow-x-auto">
                  <MathText latex={probe.statement_latex} display className="text-2xl text-white" />
                </div>
              )}
            </Card>
          )}
          {widget && probe.node_id && probe.item_id ? (
            <WorkspaceRenderer
              payload={{
                sessionId: "diagnostic",
                nodeId: probe.node_id,
                itemId: probe.item_id,
                scaffoldLevel: 2,
                answerMode: "selection",
                widgets: [widget],
              }}
              handlers={{ answerLocked: busy, onAction: onWidgetAction }}
            />
          ) : (
          <form onSubmit={onSubmit} className="space-y-3">
            {part?.grader === "sympy" || !part ? (
              <div className="space-y-2 text-sm text-slate-300">
                <span>{t("answer")}</span>
                <MathField value={input} onChange={setInput} placeholder={t("placeholder")} />
              </div>
            ) : (
              <label className="block space-y-2 text-sm text-slate-300">
                <span>{t("answer")}</span>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  inputMode={part.grader === "numeric" ? "decimal" : undefined}
                  maxLength={500}
                  className={inputClass}
                  autoComplete="off"
                />
              </label>
            )}
            <Button type="submit" block loading={busy} disabled={!input.trim()}>
              {busy ? t("checking") : t("submit")}
            </Button>
          </form>
          )}
        </motion.div>
      )}
      {error && (
        <p role="alert" className="mt-4 text-sm text-neuro-alert">
          {error}
        </p>
      )}
    </AppShell>
  );
}
