"use client";

import { Suspense, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CheckCircle2, Clock, Compass, Home, RotateCcw, XCircle } from "lucide-react";
import { motion } from "motion/react";
import { Link } from "@/i18n/navigation";
import { AppShell } from "@/components/AppShell";
import { RestOverlay } from "@/components/neuro/RestOverlay";
import { buttonClass } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressRing, Skeleton } from "@/components/ui/primitives";

function SummaryBody() {
  const t = useTranslations("summary");
  const params = useSearchParams();
  const correct = Number(params.get("correct") || 0);
  const incorrect = Number(params.get("incorrect") || 0);
  const seconds = Number(params.get("seconds") || 0);
  const [showRest, setShowRest] = useState(true);
  const total = correct + incorrect;
  const ratio = total ? correct / total : 0;

  return (
    <>
      {showRest && (
        <RestOverlay
          durationSeconds={10}
          onComplete={() => setShowRest(false)}
          onSkipLogged={() => setShowRest(false)}
        />
      )}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="space-y-6"
      >
        <Card variant="glass" className="flex flex-col items-center gap-5 py-10 text-center">
          <ProgressRing value={ratio} label={t("correct", { count: correct })} size={128}>
            <span className="font-display text-3xl font-semibold tabular-nums text-slate-50">{Math.round(ratio * 100)}%</span>
          </ProgressRing>
          <div className="space-y-2">
            <h1 className="font-display text-title font-semibold tracking-tight text-slate-50">{t("title")}</h1>
            <p className="text-slate-400">{t("subtitle")}</p>
          </div>
        </Card>

        <div className="grid grid-cols-3 gap-3">
          <Stat icon={<CheckCircle2 className="h-4 w-4 text-neuro-teal" aria-hidden />} text={t("correct", { count: correct })} />
          <Stat icon={<XCircle className="h-4 w-4 text-slate-400" aria-hidden />} text={t("incorrect", { count: incorrect })} />
          <Stat icon={<Clock className="h-4 w-4 text-indigo-300" aria-hidden />} text={t("active", { seconds })} />
        </div>

        <p className="text-center text-sm text-slate-500">{t("restNote")}</p>

        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/" className={buttonClass("primary")}>
            <Home className="h-4 w-4" aria-hidden />
            {t("home")}
          </Link>
          <Link href="/path" className={buttonClass("secondary")}>
            <Compass className="h-4 w-4" aria-hidden />
            {t("path")}
          </Link>
          <Link href="/session" className={buttonClass("ghost")}>
            <RotateCcw className="h-4 w-4" aria-hidden />
            {t("practiceAgain")}
          </Link>
        </div>
      </motion.div>
    </>
  );
}

function Stat({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <Card padded={false} className="flex flex-col items-center gap-2 px-3 py-4 text-center text-sm text-slate-300">
      {icon}
      {text}
    </Card>
  );
}

export default function SessionSummaryPage() {
  return (
    <AppShell width="narrow">
      <Suspense fallback={<Skeleton className="h-72 rounded-panel" />}>
        <SummaryBody />
      </Suspense>
    </AppShell>
  );
}
