"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, Compass, MessageCircleQuestion, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { Link, useRouter } from "@/i18n/navigation";
import { AppShell } from "@/components/AppShell";
import { PageHeader, Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { getMe, isProfileComplete, type UserProfile } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export default function HomePage() {
  const t = useTranslations("home");
  const router = useRouter();
  const [me, setMe] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.replace("/signin");
        return;
      }
      try {
        const profile = await getMe(token);
        if (!isProfileComplete(profile)) {
          router.replace("/age");
          return;
        }
        if (!cancelled) setMe(profile);
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

  return (
    <AppShell>
      <PageHeader
        eyebrow={me?.display_name ? t("greeting", { name: me.display_name }) : undefined}
        title={<span className="text-display">{t("title")}</span>}
        description={t("subtitle")}
      />
      {loading && (
        <div role="status" className="grid gap-4 sm:grid-cols-2">
          <span className="sr-only">{t("loading")}</span>
          <Skeleton className="h-44 rounded-panel sm:col-span-2" />
          <Skeleton className="h-32 rounded-panel" />
          <Skeleton className="h-32 rounded-panel" />
        </div>
      )}
      {error && (
        <p role="alert" className="text-neuro-alert">
          {error}
        </p>
      )}
      {!loading && !error && (
        <motion.div
          initial="hidden"
          animate="show"
          variants={{ show: { transition: { staggerChildren: 0.06 } } }}
          className="grid gap-4 sm:grid-cols-2"
        >
          <Tile href="/path" className="sm:col-span-2" hero>
            <div className="flex items-end justify-between gap-6">
              <div className="space-y-3">
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-neuro-indigo/20 text-indigo-200">
                  <Sparkles className="h-5 w-5" aria-hidden />
                </span>
                <p className="font-display text-2xl font-semibold text-slate-50">{t("practiceCta")}</p>
              </div>
              <ArrowRight className="h-6 w-6 shrink-0 text-indigo-200 transition-transform group-hover:translate-x-1" aria-hidden />
            </div>
          </Tile>
          <Tile href="/ask">
            <MessageCircleQuestion className="h-5 w-5 text-neuro-teal" aria-hidden />
            <p className="font-display text-lg font-semibold text-slate-100">{t("askCta")}</p>
          </Tile>
          <Tile href="/path">
            <Compass className="h-5 w-5 text-indigo-300" aria-hidden />
            <p className="font-display text-lg font-semibold text-slate-100">{t("pathCta")}</p>
          </Tile>
        </motion.div>
      )}
    </AppShell>
  );
}

function Tile({
  href,
  hero,
  className,
  children,
}: {
  href: string;
  hero?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
      className={className}
    >
      <Link
        href={href}
        className={cn(
          "group flex h-full flex-col gap-3 rounded-panel border p-6 transition-[border-color,transform,background-color] duration-150 hover:-translate-y-0.5",
          hero
            ? "border-indigo-400/25 bg-[radial-gradient(120%_120%_at_0%_0%,rgb(99_102_241/0.22),transparent_60%),var(--color-surface)] shadow-glow hover:border-indigo-400/50"
            : "border-line bg-surface-glass backdrop-blur-xl hover:border-line-strong",
        )}
      >
        {children}
      </Link>
    </motion.div>
  );
}
