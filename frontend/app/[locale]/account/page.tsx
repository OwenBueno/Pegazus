"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { AppShell } from "@/components/AppShell";
import { BirthYearPicker } from "@/components/ui/BirthYearPicker";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { DisplayNameInput } from "@/components/ui/DisplayNameInput";
import { AlertTriangle, CheckCircle2, KeyRound, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { FieldPanel, FormField, inputClass } from "@/components/ui/FormField";
import { Badge, PageHeader, Skeleton } from "@/components/ui/primitives";
import { LocaleToggle } from "@/components/ui/LocaleToggle";
import { deleteMe, deleteOpenRouterKey, getMe, patchMe, putOpenRouterKey, type UserProfile } from "@/lib/api";
import { countryLabel } from "@/lib/countries";
import { createClient } from "@/lib/supabase/client";

export default function AccountPage() {
  const t = useTranslations("account");
  const tOn = useTranslations("onboarding");
  const locale = useLocale() as "en" | "es";
  const router = useRouter();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [birthYear, setBirthYear] = useState<number | null>(null);
  const [country, setCountry] = useState<string | null>(null);
  const [appLocale, setAppLocale] = useState<"en" | "es">(locale);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [byoKey, setByoKey] = useState("");
  const [hasByo, setHasByo] = useState(false);
  const [byoMsg, setByoMsg] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.replace("/signin");
        return;
      }
      try {
        const me = await getMe(token);
        setProfile(me);
        setDisplayName(me.display_name ?? "");
        setBirthYear(me.birth_year);
        setCountry(me.country_code);
        setHasByo(Boolean(me.has_openrouter_key));
        if (me.locale === "en" || me.locale === "es") setAppLocale(me.locale);
      } catch (e) {
        setError(e instanceof Error ? e.message : "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    const name = displayName.trim();
    if (!name || birthYear == null || !country) {
      setError(t("saveError"));
      return;
    }
    setBusy(true);
    setError(null);
    setSaved(false);
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.replace("/signin");
      return;
    }
    try {
      const updated = await patchMe(token, {
        display_name: name,
        birth_year: birthYear,
        country_code: country,
        locale: appLocale,
      });
      setProfile(updated);
      setSaved(true);
      toast.success(t("saved"));
      if (appLocale !== locale) {
        router.replace("/account", { locale: appLocale });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveError"));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    setBusy(true);
    setError(null);
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.replace("/signin");
      return;
    }
    try {
      await deleteMe(token);
      await supabase.auth.signOut();
      router.replace("/signin");
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <AppShell width="narrow">
        <div role="status" className="space-y-4">
          <span className="sr-only">{t("loading")}</span>
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-20 rounded-panel" />
          <Skeleton className="h-56 rounded-panel" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell width="narrow">
      <PageHeader title={t("title")} description={t("subtitle")} />

      {profile && (
        <Card variant="raised" className="mb-6 flex items-center gap-4 text-sm text-slate-400">
          <span aria-hidden className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[linear-gradient(135deg,var(--color-neuro-indigo),var(--color-neuro-teal))] font-display text-lg font-semibold text-white">
            {(profile.display_name || profile.email || "?").slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0">
          <div className="font-mono text-micro uppercase tracking-wider text-slate-500">
            {t("signedInAs")}
          </div>
          <div className="mt-0.5 truncate text-slate-100">{profile.email}</div>
          {profile.country_code && (
            <div className="mt-1 text-xs text-slate-500">
              {countryLabel(profile.country_code, appLocale)}
              {profile.birth_year != null ? ` · ${profile.birth_year}` : ""}
            </div>
          )}
          </div>
        </Card>
      )}

      <form onSubmit={onSave} className="space-y-4">
        <FieldPanel>
          <FormField label={tOn("displayName")} hint={tOn("displayNameHint")} htmlFor="settingsName">
            <DisplayNameInput
              id="settingsName"
              value={displayName}
              onChange={setDisplayName}
              placeholder={tOn("displayNamePlaceholder")}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={tOn("birthYear")} hint={tOn("birthYearHint")}>
            <BirthYearPicker
              value={birthYear}
              onChange={setBirthYear}
              selectedLabel={tOn("selectedYear")}
              decadeLabel={(d) => tOn("decade", { decade: d })}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={tOn("country")} hint={tOn("countryHint")}>
            <CountrySelect
              value={country}
              onChange={setCountry}
              locale={appLocale}
              searchPlaceholder={tOn("countrySearch")}
              featuredLabel={tOn("countryFeatured")}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={tOn("locale")} hint={tOn("localeHint")}>
            <LocaleToggle
              value={appLocale}
              onChange={setAppLocale}
              labelEn={tOn("localeEn")}
              labelEs={tOn("localeEs")}
            />
          </FormField>
        </FieldPanel>

        {error && (
          <p role="alert" className="text-sm text-neuro-alert">
            {error}
          </p>
        )}
        {saved && (
          <p role="status" className="flex items-center gap-1.5 text-sm text-neuro-teal">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {t("saved")}
          </p>
        )}

        <Button type="submit" block loading={busy}>
          {busy ? t("saving") : t("save")}
        </Button>
      </form>

      {profile && !profile.is_minor && (
        <Card as="section" variant="glass" className="mt-10 space-y-3">
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-slate-100">
            <KeyRound className="h-4 w-4 text-indigo-300" aria-hidden />
            {t("byoTitle")}
          </h2>
          <p className="text-sm text-slate-500">{t("byoHelp")}</p>
          <Badge tone={hasByo ? "teal" : "neutral"}>{hasByo ? t("byoHasKey") : t("byoNoKey")}</Badge>
          <input
            type="password"
            value={byoKey}
            onChange={(e) => setByoKey(e.target.value)}
            placeholder={t("byoPlaceholder")}
            aria-label={t("byoPlaceholder")}
            className={`${inputClass} font-mono text-sm`}
            autoComplete="off"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={busy || !byoKey.trim()}
              onClick={async () => {
                const supabase = createClient();
                const { data } = await supabase.auth.getSession();
                const token = data.session?.access_token;
                if (!token) return;
                setBusy(true);
                setByoMsg(null);
                try {
                  await putOpenRouterKey(token, byoKey.trim());
                  setHasByo(true);
                  setByoKey("");
                  setByoMsg(t("byoSaved"));
                } catch (e) {
                  setError(e instanceof Error ? e.message : "error");
                } finally {
                  setBusy(false);
                }
              }}
            >
              {t("byoSave")}
            </Button>
            {hasByo && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={async () => {
                  const supabase = createClient();
                  const { data } = await supabase.auth.getSession();
                  const token = data.session?.access_token;
                  if (!token) return;
                  setBusy(true);
                  try {
                    await deleteOpenRouterKey(token);
                    setHasByo(false);
                    setByoMsg(t("byoCleared"));
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "error");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {t("byoClear")}
              </Button>
            )}
          </div>
          {byoMsg && (
            <p role="status" className="text-sm text-neuro-teal">
              {byoMsg}
            </p>
          )}
        </Card>
      )}

      <section className="mt-10 rounded-panel border border-rose-500/20 bg-rose-500/[0.04] p-5 sm:p-6">
        <h2 className="mb-2 flex items-center gap-2 font-display text-lg font-semibold text-slate-100">
          <AlertTriangle className="h-4 w-4 text-neuro-alert" aria-hidden />
          {t("dangerTitle")}
        </h2>
        <p className="mb-4 text-sm text-slate-400">{t("dangerHelp")}</p>
        <Button variant="danger" onClick={() => setConfirming(true)}>
          <Trash2 className="h-4 w-4" aria-hidden />
          {t("delete")}
        </Button>
      </section>

      <Dialog open={confirming} onOpenChange={setConfirming} title={t("delete")} description={t("deleteConfirm")} closeLabel={t("cancel")}>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirming(false)}>
            {t("cancel")}
          </Button>
          <Button variant="danger" loading={busy} onClick={onDelete}>
            {t("delete")}
          </Button>
        </div>
      </Dialog>
    </AppShell>
  );
}
