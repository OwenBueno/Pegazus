"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/Button";
import { PageHeader, Skeleton } from "@/components/ui/primitives";
import { BirthYearPicker } from "@/components/ui/BirthYearPicker";
import { CountrySelect } from "@/components/ui/CountrySelect";
import { DisplayNameInput } from "@/components/ui/DisplayNameInput";
import { FieldPanel, FormField } from "@/components/ui/FormField";
import { LocaleToggle } from "@/components/ui/LocaleToggle";
import { getMe, isProfileComplete, patchMe } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function AgePage() {
  const t = useTranslations("onboarding");
  const locale = useLocale() as "en" | "es";
  const router = useRouter();

  const [displayName, setDisplayName] = useState("");
  const [birthYear, setBirthYear] = useState<number | null>(null);
  const [country, setCountry] = useState<string | null>("MX");
  const [appLocale, setAppLocale] = useState<"en" | "es">(locale);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.replace("/signin");
        return;
      }
      try {
        const me = await getMe(data.session.access_token);
        if (isProfileComplete(me)) {
          router.replace("/");
          return;
        }
        if (me.display_name) setDisplayName(me.display_name);
        if (me.birth_year) setBirthYear(me.birth_year);
        if (me.country_code) setCountry(me.country_code);
        if (me.locale === "en" || me.locale === "es") setAppLocale(me.locale);
      } catch {
        /* first-time profile may still work on submit */
      } finally {
        setReady(true);
      }
    })();
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const name = displayName.trim();
    if (!name) {
      setError(t("errorName"));
      return;
    }
    if (birthYear == null) {
      setError(t("errorYear"));
      return;
    }
    if (!country) {
      setError(t("errorCountry"));
      return;
    }

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
      await patchMe(token, {
        display_name: name,
        birth_year: birthYear,
        country_code: country,
        locale: appLocale,
      });
      if (appLocale !== locale) {
        router.replace("/", { locale: appLocale });
      } else {
        router.replace("/");
      }
    } catch {
      setError(t("error"));
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <AppShell width="narrow">
        <div role="status" className="space-y-4">
          <span className="sr-only">{t("loading")}</span>
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-28 rounded-panel" />
          <Skeleton className="h-56 rounded-panel" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell width="narrow">
      <PageHeader eyebrow={t("step")} title={t("title")} description={t("subtitle")} />

      <form onSubmit={onSubmit} className="space-y-4">
        <FieldPanel>
          <FormField label={t("displayName")} hint={t("displayNameHint")} htmlFor="displayName">
            <DisplayNameInput
              id="displayName"
              value={displayName}
              onChange={setDisplayName}
              placeholder={t("displayNamePlaceholder")}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={t("birthYear")} hint={t("birthYearHint")}>
            <BirthYearPicker
              value={birthYear}
              onChange={setBirthYear}
              selectedLabel={t("selectedYear")}
              decadeLabel={(d) => t("decade", { decade: d })}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={t("country")} hint={t("countryHint")}>
            <CountrySelect
              value={country}
              onChange={setCountry}
              locale={appLocale}
              searchPlaceholder={t("countrySearch")}
              featuredLabel={t("countryFeatured")}
            />
          </FormField>
        </FieldPanel>

        <FieldPanel>
          <FormField label={t("locale")} hint={t("localeHint")}>
            <LocaleToggle
              value={appLocale}
              onChange={setAppLocale}
              labelEn={t("localeEn")}
              labelEs={t("localeEs")}
            />
          </FormField>
        </FieldPanel>

        {error && (
          <p role="alert" className="text-sm text-neuro-alert">
            {error}
          </p>
        )}

        <Button type="submit" block loading={busy} className="text-base">
          {busy ? t("saving") : t("continue")}
        </Button>
      </form>
    </AppShell>
  );
}
