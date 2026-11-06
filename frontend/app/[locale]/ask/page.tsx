"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { MessageCircleQuestion, RotateCcw } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge, PageHeader, ProgressBar, Skeleton } from "@/components/ui/primitives";
import { WorkspaceRenderer } from "@/components/genui/WorkspaceRenderer";
import { MathField } from "@/components/math/MathField";
import {
  getMe,
  isProfileComplete,
  needsGuardianConsent,
  socraticAsk,
  type SocraticAskResult,
} from "@/lib/api";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";

const MAX_EXCHANGES = 3;

export default function AskPage() {
  const t = useTranslations("socratic");
  const locale = useLocale();
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [query, setQuery] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [exchange, setExchange] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [prior, setPrior] = useState<string[]>([]);
  const [result, setResult] = useState<SocraticAskResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
        if (needsGuardianConsent(me)) {
          router.replace("/consent");
          return;
        }
        if (!cancelled) setToken(tok);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("error"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router, t]);

  const done = exchange >= MAX_EXCHANGES || Boolean(result?.refused);

  async function runAsk(text: string) {
    if (!token || !text.trim() || done) return;
    const nextIndex = exchange + 1;
    setBusy(true);
    setError(null);
    try {
      const res = await socraticAsk(token, {
        query: text.trim(),
        locale: locale === "es" ? "es" : "en",
        exchange_index: nextIndex,
        prior_prompts: prior,
        session_id: sessionId,
      });
      setResult(res);
      setSessionId(res.session_id);
      setExchange(res.exchange_index);
      setPrior((p) => [...p, res.socratic_prompt].slice(-3));
      setFollowUp("");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setBusy(false);
    }
  }

  function onFirstSubmit(e: FormEvent) {
    e.preventDefault();
    void runAsk(query);
  }

  function onFollowUp(e: FormEvent) {
    e.preventDefault();
    void runAsk(followUp || query);
  }

  const genuiPayload = useMemo(() => result?.genui ?? null, [result]);

  if (loading) {
    return (
      <AppShell width="narrow">
        <div role="status" className="space-y-4">
          <span className="sr-only">{t("loading")}</span>
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-40 rounded-panel" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell width="narrow">
      <PageHeader title={t("title")} description={t("subtitle")} />

      {!result && (
        <Card as="div" variant="glass">
        <form onSubmit={onFirstSubmit} className="space-y-4">
          <label className="block space-y-2 font-display text-[15px] font-semibold text-slate-100">
            <span className="flex items-center gap-2">
              <MessageCircleQuestion className="h-4 w-4 text-neuro-teal" aria-hidden />
              {t("query")}
            </span>
            <div className="font-sans font-normal">
              <MathField
                value={query}
                onChange={setQuery}
                virtualKeyboardMode="onfocus"
              />
            </div>
          </label>
          <Button type="submit" block loading={busy} disabled={query.trim().length < 2}>
            {busy ? t("asking") : t("ask")}
          </Button>
        </form>
        </Card>
      )}

      {result && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <ProgressBar value={exchange / MAX_EXCHANGES} label={t("exchange", { n: exchange, max: MAX_EXCHANGES })} tone="teal" className="max-w-[8rem]" />
            <span className="font-mono text-xs text-slate-500">{t("exchange", { n: exchange, max: MAX_EXCHANGES })}</span>
            {result.refused && <Badge tone="amber">{t("refused")}</Badge>}
          </div>

          {genuiPayload && (
            <WorkspaceRenderer
              payload={genuiPayload}
              errorLabel={t("genuiError")}
            />
          )}

          {!done && (
            <form onSubmit={onFollowUp} className="space-y-3">
              <label className="block space-y-2 text-sm font-medium text-slate-200">
                <span>{t("followUp")}</span>
                <div className="font-normal">
                  <MathField
                    value={followUp}
                    onChange={setFollowUp}
                    virtualKeyboardMode="onfocus"
                  />
                </div>
              </label>
              <Button type="submit" loading={busy}>
                {busy ? t("asking") : t("continue")}
              </Button>
            </form>
          )}

          {done && !result.refused && (
            <p role="status" className="rounded-control border border-line bg-surface-raised px-4 py-3 text-sm text-slate-400">{t("limit")}</p>
          )}

          <Button
            variant="ghost"
            onClick={() => {
              setResult(null);
              setExchange(0);
              setPrior([]);
              setSessionId(null);
              setQuery("");
              setFollowUp("");
            }}
          >
            <RotateCcw className="h-4 w-4" aria-hidden />
            {t("newQuestion")}
          </Button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-4 text-sm text-neuro-alert">
          {error}
        </p>
      )}
    </AppShell>
  );
}
