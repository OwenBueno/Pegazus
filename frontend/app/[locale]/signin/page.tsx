"use client";

import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { ArrowRight, ChevronLeft, Mail } from "lucide-react";
import { Wordmark } from "@/components/AppShell";
import { Button, buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import { createClient } from "@/lib/supabase/client";

function SignInForm() {
  const t = useTranslations("auth");
  const tBrand = useTranslations();
  const tHome = useTranslations("home");
  const tNav = useTranslations("nav");
  const router = useRouter();
  const searchParams = useSearchParams();
  const linkError = searchParams.get("error");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendCode(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const supabase = createClient();
    // No emailRedirectTo — OTP only; avoids PKCE magic-link flow.
    const { error: err } = await supabase.auth.signInWithOtp({ email });
    setBusy(false);
    if (err) {
      setError(err.message);
      return;
    }
    setSent(true);
  }

  async function verifyCode(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const token = code.trim();
    const supabase = createClient();

    const attempts = ["email", "magiclink"] as const;
    let lastError: string | null = null;
    for (const type of attempts) {
      const { error: err } = await supabase.auth.verifyOtp({
        email,
        token,
        type,
      });
      if (!err) {
        setBusy(false);
        router.replace("/");
        router.refresh();
        return;
      }
      lastError = err.message;
    }
    setBusy(false);
    setError(lastError ?? t("error"));
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden border-r border-line lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div aria-hidden className="absolute -left-32 top-1/4 h-[28rem] w-[28rem] rounded-full bg-indigo-500/15 blur-3xl" />
        <div aria-hidden className="absolute -bottom-24 right-0 h-80 w-80 rounded-full bg-teal-500/10 blur-3xl" />
        <Wordmark />
        <div className="relative space-y-4">
          <p className="font-display text-display font-semibold leading-[1.05] tracking-tight text-slate-50">{tBrand("brand")}</p>
          <p className="max-w-sm text-lg leading-relaxed text-slate-400">{tHome("subtitle")}</p>
        </div>
        <p className="relative font-mono text-micro uppercase tracking-[0.16em] text-slate-600">© Pegazus</p>
      </aside>

      <main className="flex flex-col justify-center px-4 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-sm animate-fade-in">
      <div className="mb-8 lg:hidden">
        <Wordmark />
      </div>
      <h1 className="mb-2 font-display text-title font-semibold tracking-tight text-slate-50">{t("title")}</h1>
      <p className="mb-6 text-sm leading-relaxed text-slate-400">{t("subtitle")}</p>

      {!sent ? (
        <form onSubmit={sendCode} className="space-y-4">
          <label className="block space-y-2 text-sm font-medium text-slate-200">
            <span>{t("email")}</span>
            <span className="relative block">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden />
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`${inputClass} pl-10 font-normal`}
              />
            </span>
          </label>
          <Button type="submit" block loading={busy}>
            {t("sendLink")}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
        </form>
      ) : (
        <form onSubmit={verifyCode} className="space-y-4">
          <p role="status" className="rounded-control border border-teal-500/25 bg-teal-500/5 px-4 py-3 text-sm text-teal-200">{t("sent")}</p>
          <label className="block space-y-2 text-sm font-medium text-slate-200">
            <span>{t("code")}</span>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className={`${inputClass} min-h-14 text-center font-mono text-2xl font-normal tracking-[0.4em]`}
            />
          </label>
          <Button type="submit" block loading={busy}>
            {t("verifyCode")}
          </Button>
          <Button
            variant="ghost"
            block
            onClick={() => {
              setSent(false);
              setCode("");
              setError(null);
            }}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
            {t("email")}
          </Button>
        </form>
      )}

      {(error || linkError) && (
        <p role="alert" className="mt-4 text-sm text-neuro-alert">
          {error || decodeURIComponent(linkError!)}
        </p>
      )}
      <p className="mt-4 text-xs leading-relaxed text-slate-500">{t("pkceHint")}</p>

      <p className="mt-8 text-center text-sm">
        <Link href="/" className={buttonClass("ghost", "sm")}>
          {tNav("home")}
        </Link>
      </p>
      </div>
      </main>
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={<p className="p-8 text-slate-500">…</p>}>
      <SignInForm />
    </Suspense>
  );
}
