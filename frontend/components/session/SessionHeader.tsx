"use client";

import { ChevronLeft, CloudOff, PauseCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { BeatIcon, beatLabel } from "@/components/learn/LessonBeatRail";
import { Button } from "@/components/ui/Button";
import { Badge, ProgressBar } from "@/components/ui/primitives";
import type { LessonBeat } from "@/lib/api";

export function SessionHeader({
  title,
  pathId,
  beats,
  beatIndex,
  onPrev,
  offline,
  aiEnabled,
}: {
  title: string;
  pathId: string | null;
  beats: LessonBeat[];
  beatIndex: number;
  onPrev: () => void;
  offline: boolean;
  aiEnabled: boolean;
}) {
  const t = useTranslations("session");
  const beat = beats[beatIndex];
  return (
    <header className="mb-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        {pathId ? (
          <Link
            href={`/path/${pathId}`}
            className="-ml-2 inline-flex min-h-11 items-center gap-1 rounded-control px-2 text-sm text-slate-400 hover:text-slate-100"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
            {t("backToOutline")}
          </Link>
        ) : (
          <span />
        )}
        <div className="flex flex-wrap justify-end gap-2">
          {offline && (
            <Badge tone="amber">
              <CloudOff className="h-3 w-3" aria-hidden />
              {t("offline")}
            </Badge>
          )}
          {!aiEnabled && (
            <Badge>
              <PauseCircle className="h-3 w-3" aria-hidden />
              {t("aiPaused")}
            </Badge>
          )}
        </div>
      </div>

      <div className="space-y-1">
        {pathId && <p className="font-mono text-micro uppercase tracking-[0.16em] text-neuro-teal">{t("onPath")}</p>}
        <h1 className="font-display text-title font-semibold tracking-tight text-slate-50">{title}</h1>
      </div>

      {beats.length > 0 && (
        <nav aria-label={t("beatRail")} className="space-y-3">
          <ProgressBar value={(beatIndex + 1) / beats.length} label={t("beatRail")} />
          <div className="flex items-center justify-between gap-2">
            <Button variant="ghost" size="sm" onClick={onPrev} disabled={beatIndex === 0} className="-ml-2">
              <ChevronLeft className="h-4 w-4" aria-hidden />
              {t("prevBeat")}
            </Button>
            <div className="flex min-w-0 items-center gap-2">
              {beat && (
                <span className="inline-flex min-w-0 items-center gap-1.5 rounded-full border border-line bg-surface-glass px-3 py-1 text-xs text-slate-300 lg:hidden">
                  <BeatIcon type={beat.type} className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate capitalize">{beatLabel(beat, t("beatProblem"))}</span>
                </span>
              )}
              <span aria-live="polite" className="shrink-0 font-mono text-xs text-slate-500">
                {t("beatCounter", { current: beatIndex + 1, total: beats.length })}
              </span>
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}
