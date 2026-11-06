"use client";

import { BookOpen, Compass, Home, Languages, LogOut, MessageCircleQuestion, Settings } from "lucide-react";
import { motion } from "motion/react";
import { useLocale, useTranslations } from "next-intl";
import { useId } from "react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/cn";
import { createClient } from "@/lib/supabase/client";

const NAV = [
  { href: "/", key: "home", icon: Home },
  { href: "/path", key: "path", icon: Compass },
  { href: "/session", key: "practice", icon: BookOpen },
  { href: "/ask", key: "ask", icon: MessageCircleQuestion },
] as const;

const WIDTH = { narrow: "max-w-xl", default: "max-w-3xl", wide: "max-w-6xl" } as const;

export function Wordmark({ className }: { className?: string }) {
  // Unique per instance: a gradient defined inside a display:none copy breaks every other url(#id) reference.
  const grad = `pg-mark-${useId().replace(/:/g, "")}`;
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <defs>
          <linearGradient id={grad} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#818cf8" />
            <stop offset="1" stopColor="#14b8a6" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="9" fill={`url(#${grad})`} opacity="0.18" />
        <path
          d="M9 23V9h7.5a4.5 4.5 0 0 1 0 9H9m7.5 0 6.5 5"
          fill="none"
          stroke={`url(#${grad})`}
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="font-display text-xl font-semibold tracking-tight text-slate-50">Pegazus</span>
    </span>
  );
}

export function AppShell({
  children,
  width = "default",
}: {
  children: React.ReactNode;
  width?: keyof typeof WIDTH;
}) {
  const t = useTranslations();
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const active = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/signin");
    router.refresh();
  }

  const iconBtn =
    "grid h-11 w-11 place-items-center rounded-full text-slate-400 transition-colors hover:bg-white/5 hover:text-white";

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b border-line bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-3 px-4">
          <Link href="/" aria-label={t("brand")} className="rounded-lg">
            <Wordmark />
          </Link>
          <nav aria-label={t("nav.main")} className="hidden items-center gap-1 md:flex">
            {NAV.map(({ href, key, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                aria-current={active(href) ? "page" : undefined}
                className={cn(
                  "relative inline-flex h-10 items-center gap-2 rounded-full px-4 text-sm transition-colors",
                  active(href) ? "text-white" : "text-slate-400 hover:text-slate-100",
                )}
              >
                {active(href) ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-full border border-line-strong bg-white/[0.06]"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                ) : null}
                <Icon className="relative h-4 w-4" aria-hidden />
                <span className="relative">{t(`nav.${key}`)}</span>
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className={cn(iconBtn, "w-auto gap-1.5 px-3 text-xs font-medium")}
              aria-label={`${t("nav.language")}: ${locale === "en" ? "Español" : "English"}`}
              onClick={() => router.replace(pathname, { locale: locale === "en" ? "es" : "en" })}
            >
              <Languages className="h-4 w-4" aria-hidden />
              {locale === "en" ? "ES" : "EN"}
            </button>
            <Link
              href="/account"
              aria-label={t("nav.account")}
              aria-current={active("/account") ? "page" : undefined}
              className={cn(iconBtn, active("/account") && "bg-white/5 text-white")}
            >
              <Settings className="h-4 w-4" aria-hidden />
            </Link>
            <button type="button" onClick={signOut} aria-label={t("nav.signOut")} className={iconBtn}>
              <LogOut className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>
      </header>

      <main className={cn("mx-auto w-full flex-1 px-4 pb-28 pt-6 sm:pt-10 md:pb-12", WIDTH[width])}>
        {children}
      </main>

      <nav
        aria-label={t("nav.main")}
        className="pb-safe fixed inset-x-0 bottom-0 z-40 border-t border-line bg-background/85 backdrop-blur-xl md:hidden"
      >
        <ul className="mx-auto grid max-w-md grid-cols-4">
          {NAV.map(({ href, key, icon: Icon }) => (
            <li key={href}>
              <Link
                href={href}
                aria-current={active(href) ? "page" : undefined}
                className={cn(
                  "relative flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors",
                  active(href) ? "text-white" : "text-slate-500",
                )}
              >
                {active(href) ? (
                  <motion.span
                    layoutId="tab-dot"
                    className="absolute top-0 h-0.5 w-8 rounded-full bg-neuro-indigo"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                ) : null}
                <Icon className={cn("h-5 w-5", active(href) && "text-neuro-indigo-soft")} aria-hidden />
                {t(`nav.${key}`)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
