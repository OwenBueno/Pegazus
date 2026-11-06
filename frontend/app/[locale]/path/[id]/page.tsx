"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useParams } from "next/navigation";
import { Link, useRouter } from "@/i18n/navigation";
import {
  AlertCircle,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Lock,
  Play,
  RefreshCw,
  Target,
  Trash2,
  Wand2,
} from "lucide-react";
import { motion } from "motion/react";
import { AppShell } from "@/components/AppShell";
import { Button, buttonClass } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Sheet } from "@/components/ui/Sheet";
import { Badge, EmptyState, PageHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import {
  PathBuildingStage,
  type PathBuildNode,
} from "@/components/path/PathBuildingStage";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import { SourcesList } from "@/components/learn/SourcesList";
import {
  deletePath,
  getMe,
  getPath,
  improvePath,
  isProfileComplete,
  materializeNode,
  rebuildPath,
  streamPathUntilComplete,
  type PathDetail,
} from "@/lib/api";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";

export default function PathDetailPage() {
  const t = useTranslations("pathDetail");
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const pathId = typeof params.id === "string" ? params.id : params.id?.[0];
  const [path, setPath] = useState<PathDetail | null>(null);
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [streamDone, setStreamDone] = useState(false);
  const [streamNodes, setStreamNodes] = useState<PathBuildNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"delete" | "improve" | "rebuild" | null>(
    null,
  );
  const [improveOpen, setImproveOpen] = useState(false);
  const [confirm, setConfirm] = useState<"delete" | "rebuild" | null>(null);
  const [improvePrompt, setImprovePrompt] = useState("");
  const [retryingNode, setRetryingNode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAfterRebuild = useCallback(
    async (tok: string, id: string) => {
      setStreamDone(false);
      setStreamNodes([]);
      setLoading(true);
      setError(null);
      try {
        const detail = await getPath(tok, id);
        setPath(detail);
        if (detail.nodes?.length) {
          setStreamNodes(
            detail.nodes.map((n) => ({ title: n.title, slug: n.slug })),
          );
          setStreamDone(detail.status !== "DRAFTING");
          if (detail.status !== "DRAFTING") {
            setLoading(false);
            setBusy(null);
            return;
          }
        }
        await streamPathUntilComplete(tok, id, (name, data) => {
          if (name !== "node_validated" && name !== "node_planned") return;
          const d = data as { title?: string; slug?: string };
          if (!d?.title) return;
          setStreamNodes((prev) => {
            if (d.slug && prev.some((p) => p.slug === d.slug)) return prev;
            return [...prev, { title: d.title!, slug: d.slug }];
          });
        });
        setStreamDone(true);
        setPath(await getPath(tok, id));
      } catch (e) {
        setError(e instanceof Error ? e.message : t("error"));
      } finally {
        setLoading(false);
        setBusy(null);
      }
    },
    [t],
  );

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
        if (cancelled) return;
        setToken(tok);
        await refreshAfterRebuild(tok, pathId);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("error"));
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pathId, router, t, refreshAfterRebuild]);

  const labelKey = (label: string) => {
    if (label === "mastered") return t("mastered");
    if (label === "frontier") return t("frontier");
    if (label === "locked") return t("locked");
    return t("unknown");
  };

  const refining = !streamDone && !error;
  const outlineFailed = Boolean(error) && !streamDone && path?.status === "DRAFTING";

  async function onRetryNode(nodeId: string) {
    if (!token || !pathId || retryingNode) return;
    setRetryingNode(nodeId);
    setError(null);
    try {
      await materializeNode(token, pathId, nodeId);
      setPath(await getPath(token, pathId));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("prepareFailed"));
    } finally {
      setRetryingNode(null);
    }
  }

  async function onDelete() {
    if (!token || !pathId) return;
    setBusy("delete");
    try {
      await deletePath(token, pathId);
      router.replace("/path");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("deleteError"));
      setBusy(null);
    }
  }

  async function onRebuild() {
    if (!token || !pathId) return;
    setBusy("rebuild");
    try {
      await rebuildPath(token, pathId);
      setImproveOpen(false);
      await refreshAfterRebuild(token, pathId);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("rebuildError"));
      setBusy(null);
    }
  }

  async function onImprove(e: FormEvent) {
    e.preventDefault();
    if (!token || !pathId || improvePrompt.trim().length < 3) return;
    setBusy("improve");
    try {
      await improvePath(token, pathId, improvePrompt.trim());
      setImprovePrompt("");
      setImproveOpen(false);
      await refreshAfterRebuild(token, pathId);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("improveError"));
      setBusy(null);
    }
  }

  const firstNodeId = path?.nodes[0]?.node_id;

  return (
    <AppShell>
      <Link
        href="/path"
        className="-ml-2 mb-4 inline-flex min-h-11 items-center gap-1 rounded-control px-2 text-sm text-slate-400 hover:text-slate-100"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden />
        {t("back")}
      </Link>
      <PageHeader
        eyebrow={streamDone ? t("ready") : undefined}
        title={path?.title ?? t("title")}
        description={path ? <span className="whitespace-pre-wrap">{path.target_goal}</span> : undefined}
      />

      {(loading || refining) && (
        <div className="mb-8">
          <PathBuildingStage goal={path?.target_goal} nodes={streamNodes} finishing={streamDone} />
        </div>
      )}

      {outlineFailed && (
        <EmptyState
          className="mb-8"
          icon={<AlertCircle className="h-5 w-5" aria-hidden />}
          title={t("outlineFailed")}
          body={<span role="alert">{error}</span>}
          action={
            <Button loading={busy === "rebuild"} disabled={busy !== null} onClick={() => void onRebuild()}>
              {busy === "rebuild" ? null : <RefreshCw className="h-4 w-4" aria-hidden />}
              {t("retry")}
            </Button>
          }
        />
      )}

      {path && streamDone && (
        <>
          <div className="mb-8 flex flex-wrap items-center gap-2">
            {firstNodeId && (
              <Link href={`/session?path=${path.path_id}&node=${firstNodeId}`} className={buttonClass("primary")}>
                <Play className="h-4 w-4" aria-hidden />
                {t("continueLesson")}
              </Link>
            )}
            <Link href={`/path/${path.path_id}/diagnostic`} className={buttonClass("secondary")}>
              <Target className="h-4 w-4" aria-hidden />
              {t("diagnostic")}
            </Link>
            <Button variant="ghost" disabled={busy !== null} onClick={() => setImproveOpen(true)}>
              <Wand2 className="h-4 w-4" aria-hidden />
              {t("improve")}
            </Button>
            <div className="ml-auto flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                loading={busy === "rebuild"}
                disabled={busy !== null}
                onClick={() => setConfirm("rebuild")}
                aria-label={busy === "rebuild" ? t("rebuilding") : t("rebuild")}
                title={t("rebuild")}
              >
                {busy === "rebuild" ? null : <RefreshCw className="h-4 w-4" aria-hidden />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                loading={busy === "delete"}
                disabled={busy !== null}
                onClick={() => setConfirm("delete")}
                aria-label={busy === "delete" ? t("deleting") : t("delete")}
                title={t("delete")}
                className="hover:text-neuro-alert"
              >
                {busy === "delete" ? null : <Trash2 className="h-4 w-4" aria-hidden />}
              </Button>
            </div>
          </div>

          <p className="mb-4 text-sm text-slate-400">{t("outlineHint")}</p>

          <ol className="relative space-y-3 pl-10">
            <span aria-hidden className="absolute bottom-6 left-[15px] top-6 w-px bg-gradient-to-b from-line-strong via-line to-transparent" />
            {path.nodes.map((n, i) => {
              const ready = Boolean(n.content_ready);
              return (
                <motion.li
                  key={n.node_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i, 10) * 0.035 }}
                  className="relative"
                >
                  <NodeDot label={n.label} />
                  <Card variant="glass" className="space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1.5">
                        <p className="font-display text-base font-semibold text-slate-50">{n.title}</p>
                        <div className="flex flex-wrap gap-1.5">
                          <Badge tone={LABEL_TONE[n.label] ?? "neutral"}>{labelKey(n.label)}</Badge>
                          <Badge tone={ready ? "teal" : "amber"}>{ready ? t("contentReady") : t("draft")}</Badge>
                        </div>
                      </div>
                      <Link
                        href={`/session?path=${path.path_id}&node=${n.node_id}`}
                        className={buttonClass(ready ? "primary" : "secondary", "sm")}
                      >
                        {ready ? t("openLesson") : t("prepare")}
                        <ArrowRight className="h-4 w-4" aria-hidden />
                      </Link>
                    </div>
                    {n.build_status === "FAILED" && (
                      <EmptyState
                        className="gap-2 px-4 py-5"
                        title={t("nodeFailed")}
                        body={n.build_error || undefined}
                        action={
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={retryingNode === n.node_id}
                            disabled={retryingNode !== null}
                            onClick={() => void onRetryNode(n.node_id)}
                            aria-label={t("retryNode", { title: n.title })}
                          >
                            {retryingNode === n.node_id ? null : <RefreshCw className="h-4 w-4" aria-hidden />}
                            {t("retry")}
                          </Button>
                        }
                      />
                    )}
                    {n.primer_md && (
                      <details className="group border-t border-line pt-3">
                        <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1.5 font-mono text-micro uppercase tracking-[0.14em] text-slate-500 hover:text-slate-300">
                          <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden />
                          {t("primer")}
                        </summary>
                        <div className="pt-2">
                          <PrimerMarkdown source={n.primer_md} />
                        </div>
                      </details>
                    )}
                    <SourcesList sources={n.sources} />
                    {n.source_attribution && n.source_attribution !== "Pegazus seed" && (
                      <p className="text-xs text-slate-500">
                        {n.source_attribution}
                        {n.source_license ? ` · ${n.source_license}` : ""}
                      </p>
                    )}
                  </Card>
                </motion.li>
              );
            })}
          </ol>
        </>
      )}
      {error && !outlineFailed && (
        <p role="alert" className="mt-4 text-sm text-neuro-alert">
          {error}
        </p>
      )}

      <Sheet open={improveOpen} onOpenChange={setImproveOpen} title={t("improve")} closeLabel={t("cancel")}>
        <form onSubmit={onImprove} className="space-y-4">
          <label className="block space-y-2 text-sm text-slate-300">
            <span>{t("improveLabel")}</span>
            <textarea
              value={improvePrompt}
              onChange={(ev) => setImprovePrompt(ev.target.value)}
              rows={4}
              placeholder={t("improvePlaceholder")}
              className="w-full rounded-control border border-line-strong bg-background/60 px-3.5 py-3 text-slate-100 outline-none placeholder:text-slate-500 focus:border-neuro-indigo"
            />
          </label>
          <p className="text-xs text-slate-500">{t("improveHint")}</p>
          <Button
            type="submit"
            block
            loading={busy === "improve"}
            disabled={busy !== null || improvePrompt.trim().length < 3}
          >
            {busy === "improve" ? t("improving") : t("improveSubmit")}
          </Button>
        </form>
      </Sheet>

      <Dialog
        open={confirm !== null}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm === "delete" ? t("delete") : t("rebuild")}
        description={confirm === "delete" ? t("deleteConfirm") : t("rebuildConfirm")}
        closeLabel={t("cancel")}
      >
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirm(null)}>
            {t("cancel")}
          </Button>
          <Button
            variant={confirm === "delete" ? "danger" : "primary"}
            onClick={() => {
              const action = confirm;
              setConfirm(null);
              void (action === "delete" ? onDelete() : onRebuild());
            }}
          >
            {confirm === "delete" ? t("delete") : t("rebuild")}
          </Button>
        </div>
      </Dialog>
    </AppShell>
  );
}

const LABEL_TONE: Record<string, "teal" | "indigo" | "neutral"> = {
  mastered: "teal",
  frontier: "indigo",
};

function NodeDot({ label }: { label: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "absolute -left-10 top-5 grid h-8 w-8 place-items-center rounded-full border bg-surface",
        label === "mastered"
          ? "border-teal-500/40 text-neuro-teal"
          : label === "frontier"
            ? "border-indigo-400/50 text-indigo-200 shadow-glow"
            : "border-line-strong text-slate-500",
      )}
    >
      {label === "mastered" ? (
        <Check className="h-4 w-4" />
      ) : label === "locked" ? (
        <Lock className="h-3.5 w-3.5" />
      ) : (
        <span className="h-2 w-2 rounded-full bg-current" />
      )}
    </span>
  );
}
