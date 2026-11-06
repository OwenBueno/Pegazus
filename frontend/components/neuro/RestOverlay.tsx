"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";

export const FULLSCREEN =
  "left-0 top-0 h-dvh max-h-none w-full max-w-none translate-x-0 translate-y-0 rounded-none border-0 bg-background/95 p-6 shadow-none backdrop-blur-md";

interface RestOverlayProps {
  durationSeconds?: number;
  allowSkip?: boolean;
  breathCycleSeconds?: number;
  onComplete: () => void;
  onSkipLogged: () => void;
}

export function RestOverlay({
  durationSeconds = 15,
  allowSkip = true,
  breathCycleSeconds = 10,
  onComplete,
  onSkipLogged,
}: RestOverlayProps) {
  const t = useTranslations("rest");
  const [secondsRemaining, setSecondsRemaining] = useState(durationSeconds);
  const [confirmingSkip, setConfirmingSkip] = useState(false);
  const done = useRef(false);
  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const finish = () => {
    if (done.current) return;
    done.current = true;
    onCompleteRef.current();
  };

  useEffect(() => {
    const deadline = Date.now() + durationSeconds * 1000;
    const timer = setInterval(() => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setSecondsRemaining(left);
      if (left === 0) {
        clearInterval(timer);
        finish();
      }
    }, 250);
    return () => clearInterval(timer);
  }, [durationSeconds]);

  return (
    <Dialog open dismissible={false} title={t("title")} hideTitle className={FULLSCREEN}>
      <div className="flex min-h-[80dvh] select-none flex-col items-center justify-center">
        <div
          className="mb-8 flex h-40 w-40 items-center justify-center rounded-full border border-neuro-indigo/30 bg-gradient-to-tr from-neuro-indigo/20 to-neuro-teal/20 shadow-glow motion-safe:animate-pulse"
          style={{ animationDuration: `${breathCycleSeconds}s` }}
        >
          <span className="font-mono text-4xl font-semibold tabular-nums text-slate-50" aria-live="off">
            {secondsRemaining}s
          </span>
        </div>

        <p className="mb-2 text-center font-display text-xl font-semibold text-slate-100">{t("title")}</p>
        <p className="mb-10 max-w-xs text-center text-sm leading-relaxed text-slate-400">{t("body")}</p>

        {allowSkip && (
          <Button variant="ghost" size="sm" onClick={() => setConfirmingSkip(true)} className="font-mono uppercase tracking-wider">
            {t("skip")}
          </Button>
        )}
      </div>

      <Dialog open={confirmingSkip} onOpenChange={setConfirmingSkip} title={t("skipTitle")} description={t("skipBody")}>
        <div className="flex gap-3">
          <Button block onClick={() => setConfirmingSkip(false)}>
            {t("keepResting")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              onSkipLogged();
              finish();
            }}
          >
            {t("skipConfirm")}
          </Button>
        </div>
      </Dialog>
    </Dialog>
  );
}
