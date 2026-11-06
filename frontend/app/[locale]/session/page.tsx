"use client";

import { FormEvent, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useRouter } from "@/i18n/navigation";
import { AppShell } from "@/components/AppShell";
import { AlertCircle, ArrowRight, CheckCircle2, Lightbulb, Loader2, PartyPopper, RotateCcw, XCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { WorkspaceRenderer } from "@/components/genui/WorkspaceRenderer";
import { renderVisual } from "@/components/genui/registry";
import { ANSWER_ACTIONS, type WidgetAction } from "@/lib/contracts/genui";
import { LessonBeatRail } from "@/components/learn/LessonBeatRail";
import { MathNotation } from "@/components/learn/PrimerMarkdown";
import { ProblemStatement } from "@/components/session/ProblemStatement";
import { SessionHeader } from "@/components/session/SessionHeader";
import { TeachBeatPanel } from "@/components/session/TeachBeatPanel";
import { SourcesList } from "@/components/learn/SourcesList";
import { TutorChat } from "@/components/session/TutorChat";
import { Button, buttonClass } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, ProgressRing, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { FocusPrimingModal } from "@/components/neuro/FocusPrimingModal";
import { RestOverlay } from "@/components/neuro/RestOverlay";
import {
  completeSession,
  evaluateStep,
  getMe,
  isProfileComplete,
  needsGuardianConsent,
  prepareLessonAndStart,
  requestHint as apiRequestHint,
  startSession,
  syncOfflineAttempts,
  type EvaluateStepResult,
  type LessonBeat,
  type PartAnswer,
  type SessionItem,
  type SessionNode,
  type SessionStart,
} from "@/lib/api";
import { buildSessionGenUI, gapPrefillFromGenui } from "@/lib/sessionGenUI";
import type { GenUIWorkspacePayload } from "@/lib/contracts/genui";
import { enqueueAttempt, listQueued, removeQueued } from "@/lib/offlineQueue";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";
import { PathBuildingStage } from "@/components/path/PathBuildingStage";
import { Link } from "@/i18n/navigation";

const REST_AFTER_ACTIVE_S = 360;

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <AppShell width="wide">
          <SessionSkeleton label="…" />
        </AppShell>
      }
    >
      <SessionBody />
    </Suspense>
  );
}

function SessionBody() {
  const t = useTranslations("session");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathFromQuery = searchParams.get("path");
  const nodeFromQuery = searchParams.get("node");
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pathId, setPathId] = useState<string | null>(pathFromQuery);
  const [item, setItem] = useState<SessionItem | null>(null);
  const [node, setNode] = useState<SessionNode | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [beatIndex, setBeatIndex] = useState(0);
  const [input, setInput] = useState("");
  const [hintLevel, setHintLevel] = useState(0);
  const [hintText, setHintText] = useState<string | null>(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [verdict, setVerdict] = useState<EvaluateStepResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [preparing, setPreparing] = useState(false);
  const [prepareStatus, setPrepareStatus] = useState<string | null>(null);
  /** Teach beats are showing while problems are still being built in the background. */
  const [practicePending, setPracticePending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRest, setShowRest] = useState(false);
  const [restDone, setRestDone] = useState(false);
  const [breaksTriggered, setBreaksTriggered] = useState(0);
  const [breaksSkipped, setBreaksSkipped] = useState(0);
  const [correct, setCorrect] = useState(0);
  const [incorrect, setIncorrect] = useState(0);
  const [offline, setOffline] = useState(false);
  const [scaffoldLevel, setScaffoldLevel] = useState<1 | 2 | 3>(1);
  const [serverGenui, setServerGenui] = useState<unknown | null>(null);
  const [showPriming, setShowPriming] = useState(true);
  const stepStartedAt = useRef(Date.now());
  const activeAccum = useRef(0);
  const lastTick = useRef(Date.now());

  const dismissPriming = useCallback(() => setShowPriming(false), []);

  const beats: LessonBeat[] = useMemo(
    () => (node?.lesson_beats?.length ? node.lesson_beats : []),
    [node],
  );
  const currentBeat = beats[beatIndex] ?? null;
  const isTeachBeat =
    currentBeat != null && currentBeat.type !== "problem";
  const hasLesson = beats.length > 0;

  const stageLabel = useCallback(
    (name: string, data: unknown): string | null => {
      const d = (data ?? {}) as { count?: number; target?: number };
      switch (name) {
        case "research_ready":
          return t("stageResearch");
        case "design_ready":
          return t("stageDesign");
        case "teach_ready":
          return t("stageTeach");
        case "item_verified":
          return t("stageItems", { count: d.count ?? 0, target: d.target ?? 5 });
        case "review_ready":
          return t("stageReview");
        case "beats_ready":
        case "node_ready":
          return t("prepareReady");
        default:
          return null;
      }
    },
    [t],
  );

  const applyStarted = useCallback((started: SessionStart) => {
    setSessionId(started.session_id);
    setAiEnabled(Boolean(started.ai_enabled));
    if (started.path_id) setPathId(started.path_id);
    if (!started.item || !started.node) {
      setItem(null);
      setNode(null);
      return;
    }
    setItem(started.item);
    setNode(started.node);
    // Binding can drop unfilled problem beats; keep the learner's place in range.
    const n = started.node.lesson_beats?.length ?? 0;
    if (n) setBeatIndex((i) => Math.min(i, n - 1));
    const sc = started.scaffold_level;
    setScaffoldLevel(sc === 1 || sc === 3 ? sc : sc === 2 ? 2 : 1);
    setServerGenui(started.genui ?? null);
    const idx = started.step_index ?? 0;
    setStepIndex(idx);
    setInput(
      gapPrefillFromGenui(
        started.genui as GenUIWorkspacePayload | null | undefined,
        started.item,
        idx,
      ),
    );
    setHintLevel(0);
    setHintText(null);
    setVerdict(null);
    stepStartedAt.current = Date.now();
    setError(null);
  }, []);

  const loadItem = useCallback(
    async (
      tok: string,
      sid?: string | null,
      pid?: string | null,
      opts?: { nodeId?: string | null; itemId?: string | null },
    ) => {
      const started = await startSession(tok, sid, pid, opts);
      setSessionId(started.session_id);
      setAiEnabled(Boolean(started.ai_enabled));
      if (started.path_id) setPathId(started.path_id);

      if (started.needs_materialize && started.path_id) {
        const nid =
          (started.materialize_node_id as string | null | undefined) ||
          opts?.nodeId ||
          nodeFromQuery;
        if (!nid) {
          setItem(null);
          setNode(null);
          router.replace(`/path/${started.path_id}`);
          return started;
        }
        // Ensure URL carries the lesson id (load happens on this page)
        if (nodeFromQuery !== nid || pathFromQuery !== started.path_id) {
          router.replace(`/session?path=${started.path_id}&node=${nid}`);
          return started;
        }
        // Teach-first: render designed beats now; problems bind when node_ready lands.
        const teachNode = started.node?.lesson_beats?.length ? started.node : null;
        const pid = started.path_id;
        const sid = started.session_id;
        let teachShown = teachNode != null;
        setItem(null);
        setNode(teachNode);
        setPreparing(!teachNode);
        setPracticePending(true);
        setPrepareStatus(t("preparing"));
        if (!teachNode) setShowPriming(false);
        setError(null);
        void prepareLessonAndStart(tok, pid, nid, sid, (name, data) => {
          const label = stageLabel(name, data);
          if (label) setPrepareStatus(label);
          if (name === "materialize_failed") {
            const d = data as { error?: string; reason?: string };
            setError(String(d?.error || d?.reason || t("prepareFailed")));
          }
          if (name === "teach_ready" && !teachShown) {
            teachShown = true;
            void startSession(tok, sid, pid, { nodeId: nid })
              .then((s) => {
                if (!s.node?.lesson_beats?.length) return;
                setNode(s.node);
                setBeatIndex(0);
                setPreparing(false);
              })
              .catch(() => {
                /* keep waiting for node_ready */
              });
          }
        })
          .then((again) => {
            setPrepareStatus(t("prepareReady"));
            applyStarted(again);
          })
          .catch((e) => {
            setError(e instanceof Error ? e.message : t("prepareFailed"));
          })
          .finally(() => {
            setPreparing(false);
            setPracticePending(false);
          });
        return started;
      }

      if (started.done || !started.item || !started.node) {
        setItem(null);
        setNode(null);
        return started;
      }
      applyStarted(started);
      return started;
    },
    [router, nodeFromQuery, pathFromQuery, t, applyStarted, stageLabel],
  );

  // Load the item for the current problem beat (on navigation and once practice binds).
  const requestedItem = useRef<string | null>(null);
  useEffect(() => {
    const want = currentBeat?.type === "problem" ? currentBeat.item_id : undefined;
    if (!token || !sessionId || !want) return;
    if (item?.id === want || requestedItem.current === want) return;
    requestedItem.current = want;
    // No full-page loading flash: showProblem stays false until the beat's item arrives.
    loadItem(token, sessionId, pathId, { nodeId: node?.id, itemId: want }).catch((e) =>
      setError(e instanceof Error ? e.message : t("error")),
    );
  }, [token, sessionId, pathId, node?.id, currentBeat, item?.id, loadItem, t]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
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
        if (needsGuardianConsent(me)) {
          router.replace("/consent");
          return;
        }
        if (!cancelled) {
          setToken(tok);
          const started = await loadItem(tok, null, pathFromQuery, {
            nodeId: nodeFromQuery,
          });
          if (cancelled) return;
          if (started.node?.lesson_beats?.length) setBeatIndex(0);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("error"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadItem, router, t, pathFromQuery, nodeFromQuery]);

  useEffect(() => {
    if (showRest) return;
    const id = setInterval(() => {
      const now = Date.now();
      activeAccum.current += (now - lastTick.current) / 1000;
      lastTick.current = now;
      if (!restDone && activeAccum.current >= REST_AFTER_ACTIVE_S) {
        setShowRest(true);
        setBreaksTriggered((n) => n + 1);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [showRest, restDone]);

  useEffect(() => {
    const syncOnline = () => setOffline(!navigator.onLine);
    syncOnline();
    window.addEventListener("online", syncOnline);
    window.addEventListener("offline", syncOnline);
    return () => {
      window.removeEventListener("online", syncOnline);
      window.removeEventListener("offline", syncOnline);
    };
  }, []);

  useEffect(() => {
    if (!token || offline) return;
    (async () => {
      const queued = await listQueued();
      if (!queued.length) return;
      const bySession = new Map<string, typeof queued>();
      for (const q of queued) {
        const list = bySession.get(q.session_id) ?? [];
        list.push(q);
        bySession.set(q.session_id, list);
      }
      for (const [sid, attempts] of bySession) {
        try {
          const synced = await syncOfflineAttempts(
            token,
            sid,
            attempts.map((a) => ({
              client_attempt_id: a.client_attempt_id,
              item_id: a.item_id,
              part_index: a.part_index,
              answer: a.answer,
              latency_ms: a.latency_ms,
              hint_level: a.hint_level,
            })),
          );
          const accepted = (synced.results || [])
            .filter((r) => r.status === "accepted")
            .map((r) => r.client_attempt_id);
          if (accepted.length) {
            await removeQueued(accepted);
          }
        } catch {
          /* keep queue */
        }
      }
    })();
  }, [token, offline]);

  function goToBeat(i: number) {
    setBeatIndex(Math.max(0, Math.min(i, beats.length - 1)));
    setVerdict(null);
  }

  async function advanceBeat() {
    if (!token || !sessionId) return;
    if (beatIndex + 1 >= beats.length) {
      await finishSession();
      return;
    }
    goToBeat(beatIndex + 1);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await submitStep(input);
  }

  // ponytail: "Show step" grades the model line at max hint level, so FSRS sees heavy help
  // without blocking the learner; upgrade path is a dedicated "revealed" verdict.
  async function submitStep(raw: string, hint = hintLevel) {
    const latex = raw.trim();
    if (latex) await submitAnswer(stepIndex, { latex }, hint);
  }

  async function submitAnswer(partIndex: number, answer: PartAnswer, hint = hintLevel) {
    if (!token || !sessionId || !item || busy) return;
    setBusy(true);
    setError(null);
    const latency = Date.now() - stepStartedAt.current;
    try {
      if (!navigator.onLine) {
        const id = crypto.randomUUID();
        await enqueueAttempt({
          client_attempt_id: id,
          session_id: sessionId,
          item_id: item.id,
          part_index: partIndex,
          answer,
          latency_ms: latency,
          hint_level: hint,
          created_at: Date.now(),
        });
        setOffline(true);
        setError(t("queued"));
        return;
      }
      const result = await evaluateStep(token, {
        item_id: item.id,
        part_index: partIndex,
        answer,
        session_id: sessionId,
        hint_level: hint,
        scaffold_level: scaffoldLevel,
        latency_ms: latency,
      });
      setVerdict(result);
      if (result.genui) setServerGenui(result.genui);
      if (
        result.scaffold_level === 1 ||
        result.scaffold_level === 2 ||
        result.scaffold_level === 3
      ) {
        setScaffoldLevel(result.scaffold_level);
      }
      if (result.is_success) {
        setCorrect((c) => c + 1);
        if (result.is_final_step) {
          // Server may have jumped ahead (final answer typed early); its genui shows every step.
          setStepIndex(Math.max(0, item.steps.length - 1));
          setInput("");
          setHintLevel(0);
          setHintText(null);
        } else {
          const nextIdx = stepIndex + 1;
          setStepIndex(nextIdx);
          setInput(
            gapPrefillFromGenui(
              (result.genui as GenUIWorkspacePayload | null | undefined) ?? null,
              item,
              nextIdx,
            ),
          );
          setHintLevel(0);
          setHintText(null);
          setVerdict(null);
          stepStartedAt.current = Date.now();
        }
      } else {
        setIncorrect((c) => c + 1);
      }
    } catch (err) {
      if (!navigator.onLine) {
        const id = crypto.randomUUID();
        await enqueueAttempt({
          client_attempt_id: id,
          session_id: sessionId,
          item_id: item.id,
          part_index: partIndex,
          answer,
          latency_ms: latency,
          hint_level: hint,
          created_at: Date.now(),
        });
        setOffline(true);
        setError(t("queued"));
      } else {
        setError(err instanceof Error ? err.message : t("error"));
      }
    } finally {
      setBusy(false);
    }
  }

  async function finishSession() {
    if (!token || !sessionId) return;
    const secs = Math.max(1, Math.round(activeAccum.current));
    try {
      const summary = await completeSession(token, sessionId, {
        active_seconds: secs,
        micro_breaks_triggered: breaksTriggered,
        micro_breaks_skipped: breaksSkipped,
        post_session_rest_completed: false,
      });
      if (pathId) {
        router.push(`/path/${pathId}`);
        return;
      }
      const q = new URLSearchParams({
        correct: String(summary.correct_count || correct),
        incorrect: String(summary.incorrect_count || incorrect),
        seconds: String(summary.active_seconds),
      });
      router.push(`/session/summary?${q.toString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    }
  }

  async function nextProblem() {
    if (!token || !sessionId) return;
    if (hasLesson) {
      await advanceBeat();
      return;
    }
    setLoading(true);
    try {
      const started = await loadItem(token, sessionId, pathId);
      if (started.done) {
        await finishSession();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setLoading(false);
    }
  }

  async function requestHint() {
    if (!token || !sessionId || !item || hintLevel >= 3) return;
    const next = Math.min(3, hintLevel + 1);
    setHintLevel(next);
    try {
      const res = await apiRequestHint(token, {
        session_id: sessionId,
        item_id: item.id,
        step_index: stepIndex,
        hint_level: next,
        locale: locale === "es" ? "es" : "en",
        submitted_latex: input.trim() || undefined,
        verdict: verdict?.verdict,
      });
      setAiEnabled(res.ai_enabled);
      setHintText(res.socratic_prompt);
    } catch {
      setHintText(null);
    }
  }

  const genuiPayload = useMemo(() => {
    if (serverGenui && hintLevel === 0) return serverGenui;
    if (!item || !sessionId || !node) return null;
    const fallback =
      hintLevel > 0
        ? (hintText ?? t(`hint${hintLevel}` as "hint1" | "hint2" | "hint3"))
        : null;
    return buildSessionGenUI({
      sessionId,
      nodeId: node.id,
      item,
      stepIndex,
      scaffoldLevel,
      hintTier: hintLevel >= 1 && hintLevel <= 3 ? (hintLevel as 1 | 2 | 3) : null,
      hintPrompt: fallback,
    });
  }, [
    serverGenui,
    item,
    sessionId,
    node,
    stepIndex,
    scaffoldLevel,
    hintLevel,
    hintText,
    t,
  ]);

  const selectionPrimary = useMemo(
    () => isSelectionPrimaryAnswer(genuiPayload),
    [genuiPayload],
  );

  if (loading || preparing) {
    return (
      <AppShell width="wide">
        {preparing ? (
          <div className="mx-auto max-w-lg">
            <PathBuildingStage
              goal={prepareStatus ?? t("preparing")}
              nodes={
                node?.title
                  ? [{ title: node.title }]
                  : [{ title: t("preparingLesson") }]
              }
              finishing={prepareStatus === t("prepareReady")}
            />
            <p className="mt-4 text-center text-xs text-slate-500">
              {t("prepareWait")}
            </p>
            {pathId && (
              <p className="mt-4 text-center">
                <Link href={`/path/${pathId}`} className={buttonClass("ghost", "sm")}>
                  {t("backToOutline")}
                </Link>
              </p>
            )}
            {error && (
              <p className="mt-4 text-center text-sm text-neuro-alert">{error}</p>
            )}
          </div>
        ) : (
          <SessionSkeleton label={t("loading")} />
        )}
      </AppShell>
    );
  }

  const problemPending =
    currentBeat?.type === "problem" && !currentBeat.item_id && practicePending;
  const showProblem =
    !hasLesson ||
    (currentBeat?.type === "problem" &&
      (currentBeat.item_id ? item?.id === currentBeat.item_id : !practicePending));
  // Answer bar dispatch: sympy parts use the step editor (MathField); every other grader's
  // widget owns its input and submit (ShortAnswer/FreeResponse text, Cloze blanks, …).
  const isSympy = !item?.parts?.length || item.parts[0].grader === "sympy";
  const activePart = isSympy ? undefined : item?.parts?.[Math.min(stepIndex, (item?.parts?.length ?? 1) - 1)];

  const onWorkspaceAction = (a: WidgetAction) => {
    if (a.type === "SUBMIT_STEP") {
      const latex =
        typeof a.payload === "object" && a.payload && "latex" in a.payload
          ? String((a.payload as { latex?: string }).latex || "")
          : "";
      if (latex.trim()) {
        setInput(latex);
        void submitStep(latex);
      }
      return;
    }
    if (a.type === "REVEAL_STEP") {
      const model = item?.steps[stepIndex]?.latex ?? "";
      setInput(model);
      void submitStep(model, 3);
      return;
    }
    if (ANSWER_ACTIONS.has(a.type) && typeof a.payload === "object" && a.payload) {
      // The widget sends what the learner did; the server holds the key and grades.
      void submitAnswer(isSympy ? 0 : stepIndex, a.payload as PartAnswer);
    }
  };
  const partStem = String(activePart?.props.question ?? activePart?.props.prompt ?? "").trim();
  const score = verdict?.score ?? 0;

  return (
    <AppShell width="wide">
      <FocusPrimingModal
        open={showPriming && !preparing && Boolean(item || hasLesson)}
        onComplete={dismissPriming}
        onSkip={dismissPriming}
      />
      {showRest && (
        <RestOverlay
          onComplete={() => {
            setShowRest(false);
            setRestDone(true);
            lastTick.current = Date.now();
          }}
          onSkipLogged={() => setBreaksSkipped((n) => n + 1)}
        />
      )}

      <MathNotation.Provider value={!node?.notation || node.notation === "math" || node.notation === "chem"}>
      <div className="flex gap-10">
        <div className="mx-auto w-full min-w-0 max-w-2xl flex-1">
          <SessionHeader
            title={node?.title || t("title")}
            pathId={pathId}
            beats={beats}
            beatIndex={beatIndex}
            onPrev={() => goToBeat(beatIndex - 1)}
            offline={offline}
            aiEnabled={aiEnabled}
          />

          {!item && !hasLesson ? (
            <EmptyState
              icon={error ? <AlertCircle className="h-5 w-5" aria-hidden /> : <PartyPopper className="h-5 w-5" aria-hidden />}
              title={error ? t("prepareFailed") : t("done")}
              body={error ? <span role="alert">{error}</span> : undefined}
              action={
                <div className="flex flex-wrap justify-center gap-3">
                  {error && token && pathId && nodeFromQuery && (
                    <Button
                      variant="success"
                      onClick={() => {
                        setError(null);
                        setLoading(true);
                        void loadItem(token, sessionId, pathId, { nodeId: nodeFromQuery }).finally(() =>
                          setLoading(false),
                        );
                      }}
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden />
                      {t("prepareRetry")}
                    </Button>
                  )}
                  <Button onClick={finishSession}>{t("finish")}</Button>
                </div>
              }
            />
          ) : (
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={beatIndex}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-5"
              >
                {problemPending && (
                  <Card variant="glass" role="status" className="space-y-4">
                    <CardHeader
                      icon={<Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
                      label={t("beatProblem")}
                      tone="text-neuro-teal"
                      className="mb-0"
                    />
                    <p className="text-sm text-slate-300">{t("practicePreparing")}</p>
                    {prepareStatus && <p className="text-xs text-slate-500">{prepareStatus}</p>}
                    <Skeleton className="h-24" />
                  </Card>
                )}

                {currentBeat?.type === "problem" && currentBeat.item_id && item?.id !== currentBeat.item_id && (
                  <div role="status" className="space-y-3">
                    <span className="sr-only">{t("loading")}</span>
                    <Skeleton className="h-28 rounded-panel" />
                    <Skeleton className="h-40 rounded-panel" />
                  </div>
                )}

                {isTeachBeat && currentBeat && (
                  <>
                    <TeachBeatPanel
                      beat={currentBeat}
                      onContinue={() => void advanceBeat()}
                      continueLabel={t("continue")}
                      revealLabel={t("revealStep")}
                      readyLabel={t("exampleReady")}
                    />
                    <SourcesList sources={node?.sources} />
                  </>
                )}

                {showProblem && item && (
                  <>
                    {/* Generic widgets usually repeat the prompt as their own question; show it once. */}
                    {(isSympy || (item.prompt_md || "").trim() !== partStem) && (
                      <ProblemStatement
                        prompt={item.prompt}
                        promptMd={item.prompt_md}
                        statementLatex={item.statement_latex}
                        label={t("statement")}
                      />
                    )}
                    {currentBeat?.type === "problem" && renderVisual(currentBeat.visual, `beat-${beatIndex}-visual`)}

                    {genuiPayload && (
                      <WorkspaceRenderer
                        payload={genuiPayload}
                        handlers={{
                          stepValue: input,
                          onStepChange: setInput,
                          onAction: onWorkspaceAction,
                          answerLocked: busy || Boolean(verdict?.is_success && verdict.is_final_step),
                        }}
                        errorLabel={t("genuiError")}
                      />
                    )}

                    <AnimatePresence>
                      {verdict && (
                        <motion.div
                          key={`${verdict.is_success}-${verdict.verdict}`}
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0 }}
                          role="status"
                          className={cn(
                            "flex items-center gap-3 rounded-control border px-4 py-3 text-sm font-medium",
                            verdict.is_success
                              ? "border-teal-500/30 bg-teal-500/10 text-teal-200"
                              : "border-rose-500/30 bg-rose-500/10 text-rose-200",
                          )}
                        >
                          {score > 0 && score < 1 ? (
                            <ProgressRing value={score} size={40} label={t("scoreLabel", { pct: Math.round(score * 100) })}>
                              <span className="text-micro font-semibold">{Math.round(score * 100)}%</span>
                            </ProgressRing>
                          ) : verdict.is_success ? (
                            <CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden />
                          ) : (
                            <XCircle className="h-5 w-5 shrink-0" aria-hidden />
                          )}
                          <span>
                            {verdict.is_success
                              ? verdict.is_final_step && isSympy
                                ? t("verdictSolved")
                                : t("verdictOk")
                              : verdict.verdict === "SIGN_ERROR"
                                ? t("verdictSign")
                                : verdict.verdict === "PARTIAL"
                                  ? t("verdictPartial")
                                  : verdict.verdict === "SYNTAX_ERROR" && !isSympy
                                    ? t("verdictUnreadable")
                                    : t("verdictBad")}
                            {verdict.feedback ? <span className="mt-0.5 block font-normal opacity-90">{verdict.feedback}</span> : null}
                          </span>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div className="flex flex-wrap items-center gap-3 border-t border-line pt-5">
                      {verdict?.is_success && verdict.is_final_step ? (
                        <>
                          <Button variant="success" onClick={nextProblem}>
                            {hasLesson ? t("continue") : t("nextItem")}
                            <ArrowRight className="h-4 w-4" aria-hidden />
                          </Button>
                          {!hasLesson && (
                            <Button variant="secondary" onClick={finishSession}>
                              {t("finish")}
                            </Button>
                          )}
                        </>
                      ) : !selectionPrimary ? (
                        <form onSubmit={onSubmit} className="contents">
                          <Button type="submit" loading={busy} disabled={!input.trim()}>
                            {busy ? t("checking") : t("submit")}
                          </Button>
                          <Button variant="secondary" onClick={requestHint} disabled={hintLevel >= 3}>
                            <Lightbulb className="h-4 w-4" aria-hidden />
                            {t("hint")}
                          </Button>
                        </form>
                      ) : (
                        !isSympy && (
                          <Button variant="secondary" onClick={requestHint} disabled={hintLevel >= 3}>
                            <Lightbulb className="h-4 w-4" aria-hidden />
                            {t("hint")}
                          </Button>
                        )
                      )}
                      {token && sessionId && (
                        <div className="sm:ml-auto">
                          <TutorChat key={item.id} token={token} sessionId={sessionId} itemId={item.id} locale={locale} offline={offline} />
                        </div>
                      )}
                    </div>
                  </>
                )}
              </motion.div>
            </AnimatePresence>
          )}

          {error && (item || hasLesson) && (
            <p role="alert" className="mt-4 text-sm text-neuro-alert">
              {error}
            </p>
          )}
        </div>

        {hasLesson && <LessonBeatRail beats={beats} currentIndex={beatIndex} onSelect={goToBeat} />}
      </div>
      </MathNotation.Provider>
    </AppShell>
  );
}

function SessionSkeleton({ label }: { label: string }) {
  return (
    <div role="status" className="mx-auto max-w-2xl space-y-5">
      <span className="sr-only">{label}</span>
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-8 w-2/3" />
      <Skeleton className="h-1.5 w-full" />
      <Skeleton className="h-48 rounded-panel" />
      <Skeleton className="h-12 w-40" />
    </div>
  );
}

function isSelectionPrimaryAnswer(payload: unknown): boolean {
  if (!payload || typeof payload !== "object") return false;
  const p = payload as {
    answerMode?: string;
    widgets?: { type?: string }[];
  };
  if (p.answerMode === "selection") return true;
  if (p.answerMode === "symbolic") return false;
  const types = (p.widgets || []).map((w) => w.type || "");
  const sel = types.some(
    (t) => t === "QuickCheck" || t === "NumberLine" || t === "MatchPairs",
  );
  const sym = types.includes("SymbolicStepEditor");
  return sel && !sym;
}
