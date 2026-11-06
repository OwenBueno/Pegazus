"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { getMe, isProfileComplete, postGuardianConsent } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function ConsentWaitPage() {
  const t = useTranslations("consent");
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const tok = data.session?.access_token;
      if (!tok) {
        router.replace("/signin");
        return;
      }
      const me = await getMe(tok);
      if (!isProfileComplete(me)) {
        router.replace("/age");
        return;
      }
      if (!me.is_minor || me.guardian_consent_at) {
        router.replace("/");
      }
    })();
  }, [router]);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const tok = data.session?.access_token;
      if (!tok) {
        router.replace("/signin");
        return;
      }
      await postGuardianConsent(tok);
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell width="narrow">
      <Card variant="glass" className="space-y-5 text-center sm:p-8">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-neuro-indigo/15 text-indigo-200">
          <ShieldCheck className="h-7 w-7" aria-hidden />
        </span>
        <h1 className="font-display text-title font-semibold tracking-tight text-slate-50">{t("title")}</h1>
        <p className="text-[15px] leading-relaxed text-slate-400">{t("body")}</p>
        <p className="rounded-control border border-line bg-background/50 px-4 py-3 text-sm text-slate-500">{t("devNote")}</p>
        <Button block loading={busy} onClick={confirm}>
          {busy ? t("saving") : t("confirm")}
        </Button>
        {error && (
          <p role="alert" className="text-sm text-neuro-alert">
            {error}
          </p>
        )}
      </Card>
    </AppShell>
  );
}
