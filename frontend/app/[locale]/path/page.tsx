"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { Play, Plus, Route, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import { AppShell } from "@/components/AppShell";
import { Button, buttonClass } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Badge, EmptyState, PageHeader, Skeleton } from "@/components/ui/primitives";
import {
  deletePath,
  getMe,
  isProfileComplete,
  listPaths,
  type PathSummary,
} from "@/lib/api";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";

export default function PathPage() {
  const t = useTranslations("path");
  const router = useRouter();
  const [paths, setPaths] = useState<PathSummary[]>([]);
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  useEffect(() => {
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
        const list = await listPaths(tok);
        if (!cancelled) {
          setToken(tok);
          setPaths(list);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onDelete(pathId: string) {
    if (!token) return;
    setConfirmId(null);
    setBusyId(pathId);
    setError(null);
    try {
      await deletePath(token, pathId);
      setPaths((prev) => prev.filter((p) => p.path_id !== pathId));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("deleteError"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title={t("title")}
        description={t("subtitle")}
        action={
          <Link href="/path/new" className={buttonClass("primary")}>
            <Plus className="h-4 w-4" aria-hidden />
            {t("createPath")}
          </Link>
        }
      />
      {loading && (
        <div role="status" className="space-y-3">
          <span className="sr-only">{t("loading")}</span>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28 rounded-panel" />
          ))}
        </div>
      )}
      {error && (
        <p role="alert" className="mb-4 text-neuro-alert">
          {error}
        </p>
      )}
      {!loading && paths.length === 0 && (
        <EmptyState
          icon={<Route className="h-5 w-5" aria-hidden />}
          title={t("empty")}
          action={
            <Link href="/path/new" className={buttonClass("primary")}>
              <Plus className="h-4 w-4" aria-hidden />
              {t("createPath")}
            </Link>
          }
        />
      )}
      <ul className="space-y-3">
        {paths.map((p, i) => (
          <motion.li
            key={p.path_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i, 8) * 0.04 }}
          >
            <Card variant="glass" interactive className="relative flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Link
                  href={`/path/${p.path_id}`}
                  className="font-display text-lg font-semibold text-slate-50 after:absolute after:inset-0 after:rounded-panel hover:text-white"
                >
                  {p.title}
                </Link>
                <p className="line-clamp-2 text-sm text-slate-400">{p.target_goal}</p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Badge tone={p.status === "active" ? "teal" : "neutral"} className="font-mono uppercase">
                    {p.status}
                  </Badge>
                  <Badge>{t("nodes", { count: p.node_count })}</Badge>
                </div>
              </div>
              <div className="relative z-10 flex gap-2">
                <Link href={`/path/${p.path_id}`} className={buttonClass("success", "sm")}>
                  <Play className="h-4 w-4" aria-hidden />
                  {t("practice")}
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  loading={busyId === p.path_id}
                  onClick={() => setConfirmId(p.path_id)}
                  aria-label={busyId === p.path_id ? t("deleting") : `${t("delete")}: ${p.title}`}
                  className="text-slate-400 hover:text-neuro-alert"
                >
                  {busyId === p.path_id ? null : <Trash2 className="h-4 w-4" aria-hidden />}
                </Button>
              </div>
            </Card>
          </motion.li>
        ))}
      </ul>

      <Dialog
        open={confirmId !== null}
        onOpenChange={(o) => !o && setConfirmId(null)}
        title={t("delete")}
        description={t("deleteConfirm")}
        closeLabel={t("cancel")}
      >
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirmId(null)}>
            {t("cancel")}
          </Button>
          <Button variant="danger" onClick={() => confirmId && void onDelete(confirmId)}>
            <Trash2 className="h-4 w-4" aria-hidden />
            {t("delete")}
          </Button>
        </div>
      </Dialog>
    </AppShell>
  );
}
