"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { FULLSCREEN } from "@/components/neuro/RestOverlay";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";

const DEFAULT_SECONDS = 90;

type PrimingProps = {
  onComplete: () => void;
  onSkip: () => void;
  durationSeconds?: number;
};

/** Mounted only while open, so the countdown restarts on every open. */
export function FocusPrimingModal({ open, ...props }: PrimingProps & { open: boolean }) {
  return open ? <FocusPriming {...props} /> : null;
}

function FocusPriming({ onComplete, onSkip, durationSeconds = DEFAULT_SECONDS }: PrimingProps) {
  const t = useTranslations("priming");
  const [remaining, setRemaining] = useState(durationSeconds);
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    const id = setInterval(() => {
      setRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Fire parent close outside the setState updater (avoids setState-during-render).
  useEffect(() => {
    if (remaining > 0 || completedRef.current) return;
    completedRef.current = true;
    onCompleteRef.current();
  }, [remaining]);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const timeFormatted = `${minutes}:${seconds.toString().padStart(2, "0")}`;
  const progress = durationSeconds > 0 ? remaining / durationSeconds : 0;

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onSkip()}
      title={t("title")}
      hideTitle
      className={`${FULLSCREEN} bg-[#070b14] sm:p-10`}
    >
    <div className="flex min-h-[calc(100dvh-5rem)] flex-col items-center justify-between text-slate-100">
      <div
        className="pointer-events-none absolute inset-0 opacity-80"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 50% 45%, rgba(45, 110, 120, 0.18), transparent 65%), radial-gradient(ellipse 50% 40% at 50% 80%, rgba(67, 56, 140, 0.12), transparent 60%)",
        }}
      />

      <div className="relative z-10 flex w-full max-w-xl items-center justify-between">
        <p className="font-mono text-xs uppercase tracking-wider text-slate-400">
          {t("title")}
        </p>
        <Button variant="secondary" size="sm" onClick={onSkip}>
          {t("skip")}
        </Button>
      </div>

      <div className="relative z-10 my-auto flex flex-col items-center space-y-8">
        <div className="relative flex h-28 w-28 items-center justify-center">
          <div
            className="absolute inset-0 rounded-full border border-teal-500/25"
            style={{ animation: "focus-breathe 4s ease-in-out infinite" }}
          />
          <div
            className="absolute inset-3 rounded-full border border-indigo-400/20"
            style={{ animation: "focus-breathe 4s ease-in-out infinite 0.4s" }}
          />
          <div
            className="h-3 w-3 rounded-full bg-teal-400/90"
            style={{
              boxShadow: "0 0 24px 4px rgba(45, 212, 191, 0.35)",
              animation: "focus-dot 4s ease-in-out infinite",
            }}
          />
          <svg
            className="absolute inset-0 -rotate-90"
            viewBox="0 0 112 112"
            aria-hidden
          >
            <circle
              cx="56"
              cy="56"
              r="52"
              fill="none"
              stroke="rgba(148,163,184,0.15)"
              strokeWidth="2"
            />
            <circle
              cx="56"
              cy="56"
              r="52"
              fill="none"
              stroke="rgba(45,212,191,0.45)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 52}
              strokeDashoffset={(1 - progress) * 2 * Math.PI * 52}
              className="transition-[stroke-dashoffset] duration-1000 linear"
            />
          </svg>
        </div>
        <p className="max-w-xs text-center text-sm leading-relaxed text-slate-400">
          {t("subtitle")}
        </p>
      </div>

      <p
        className="relative z-10 pb-6 font-mono text-lg tabular-nums text-slate-400"
        aria-live="polite"
      >
        {timeFormatted}
      </p>
    </div>
    </Dialog>
  );
}
