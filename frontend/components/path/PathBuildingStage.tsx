"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, Sparkles } from "lucide-react";

export type PathBuildNode = {
  title: string;
  slug?: string;
};

type Props = {
  goal?: string | null;
  paceLine?: string | null;
  nodes?: PathBuildNode[];
  /** When true, show “almost ready” phase copy */
  finishing?: boolean;
};

const PHASE_COUNT = 4;

/**
 * Full-bleed-ish building stage while path ingest / SSE runs.
 * Uses goal + live node titles when available so the wait feels informative.
 */
export function PathBuildingStage({
  goal,
  paceLine,
  nodes = [],
  finishing = false,
}: Props) {
  const t = useTranslations("pathBuilding");
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    if (finishing) return; // phaseKey shows "ready" directly
    const id = window.setInterval(() => {
      setPhase((p) => (p + 1) % (PHASE_COUNT - 1));
    }, 2200);
    return () => window.clearInterval(id);
  }, [finishing]);

  const placeholders = useMemo(
    () => [t("slot1"), t("slot2"), t("slot3"), t("slot4"), t("slot5")],
    [t],
  );

  const displayNodes: PathBuildNode[] =
    nodes.length > 0
      ? nodes
      : placeholders.map((title) => ({ title }));

  const phaseKey = finishing
    ? "phaseReady"
    : (["phaseRead", "phaseMatch", "phaseLink", "phaseReady"] as const)[phase];

  return (
    <div
      className="relative overflow-hidden rounded-panel border border-line bg-surface-glass px-5 py-10 backdrop-blur-xl sm:px-8"
      role="status"
      aria-live="polite"
      aria-busy={!finishing}
    >
      {/* Soft atmosphere */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 -top-20 h-56 w-56 rounded-full bg-teal-500/10 blur-3xl motion-safe:path-build-pulse"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-24 -right-10 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl motion-safe:path-build-pulse"
        style={{ animationDelay: "0.7s" }}
      />

      <div className="relative mx-auto flex max-w-md flex-col items-center text-center">
        {/* Orbit mark */}
        <div className="relative mb-6 flex h-20 w-20 items-center justify-center">
          <svg
            className="absolute inset-0 h-full w-full motion-safe:path-build-orbit text-slate-600"
            viewBox="0 0 80 80"
            aria-hidden
          >
            <circle
              cx="40"
              cy="40"
              r="34"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              strokeDasharray="4 10"
              opacity="0.5"
            />
            <circle cx="40" cy="6" r="3" className="fill-neuro-teal" />
          </svg>
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-neuro-teal/40 bg-teal-950/40 text-neuro-teal motion-safe:path-build-pulse">
            {finishing ? <Check className="h-5 w-5" aria-hidden /> : <Sparkles className="h-5 w-5" aria-hidden />}
          </div>
        </div>

        <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
          Pegazus
        </p>
        <h2 className="mb-2 font-display text-xl font-semibold tracking-tight text-slate-50">
          {t("title")}
        </h2>
        <p className="mb-6 min-h-[1.25rem] text-sm text-slate-400 transition-opacity">
          {t(phaseKey)}
        </p>

        {(goal || paceLine) && (
          <div className="mb-8 w-full space-y-2 rounded-control border border-line bg-background/50 px-4 py-3 text-left">
            {goal && (
              <p className="text-sm leading-snug text-slate-200">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {t("goalLabel")}
                </span>
                <br />
                {goal}
              </p>
            )}
            {paceLine && (
              <p className="text-xs text-slate-500">{paceLine}</p>
            )}
          </div>
        )}

        {/* Growing path spine */}
        <ol className="w-full space-y-0">
          {displayNodes.slice(0, 6).map((n, i) => {
            const live = nodes.length > 0 && i < nodes.length;
            const visible = live || nodes.length === 0;
            return (
              <li
                key={`${n.slug ?? n.title}-${i}`}
                className={`relative flex gap-3 pb-5 last:pb-0 ${
                  visible ? "motion-safe:path-build-rise" : "opacity-30"
                }`}
                style={{ animationDelay: `${i * 90}ms` }}
              >
                <div className="flex w-6 flex-col items-center">
                  <span
                    className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
                      live
                        ? "bg-neuro-teal shadow-[0_0_12px_rgba(20,184,166,0.45)]"
                        : "bg-slate-600 motion-safe:path-build-pulse"
                    }`}
                    style={
                      !live ? { animationDelay: `${i * 0.25}s` } : undefined
                    }
                  />
                  {i < displayNodes.slice(0, 6).length - 1 && (
                    <svg
                      className="mt-1 h-8 w-3 overflow-visible text-slate-600"
                      aria-hidden
                    >
                      <line
                        x1="6"
                        y1="0"
                        x2="6"
                        y2="32"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className={
                          live ? "motion-safe:path-build-draw text-neuro-teal/50" : ""
                        }
                      />
                    </svg>
                  )}
                </div>
                <div className="min-w-0 flex-1 pt-0.5 text-left">
                  <p
                    className={`truncate text-sm ${
                      live ? "text-slate-100" : "text-slate-500"
                    }`}
                  >
                    {n.title}
                  </p>
                  {n.slug && (
                    <p className="truncate font-mono text-[10px] text-slate-600">
                      {n.slug}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
