"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AnimatePresence, motion } from "motion/react";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Self-rated: emits {self: (0|1)[]}, one rating per card in order. */
export function Flashcards({
  cards,
  widgetId = "flashcards",
  disabled = false,
  onAction,
}: {
  cards: { front: string; back: string }[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [self, setSelf] = useState<(0 | 1)[]>([]);
  const done = self.length === cards.length;
  const card = cards[Math.min(i, cards.length - 1)];

  function rate(v: 0 | 1) {
    setSelf((s) => [...s.slice(0, i), v]);
    setFlipped(false);
    setI((n) => n + 1);
  }

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("flashcards")}</p>
        <p className="text-xs text-slate-400">
          {t("cardOf", { i: Math.min(i + 1, cards.length), n: cards.length })}
        </p>
      </div>
      {!done && (
        <>
          <div
            aria-live="polite"
            className="grid min-h-32 place-items-center rounded-control border border-line-strong bg-surface-raised p-5 text-center"
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.p
                key={`${i}-${flipped}`}
                initial={{ opacity: 0, rotateX: -90 }}
                animate={{ opacity: 1, rotateX: 0 }}
                exit={{ opacity: 0, rotateX: 90 }}
                transition={{ duration: 0.18 }}
                className={`text-[17px] leading-relaxed ${flipped ? "text-teal-100" : "text-slate-50"}`}
              >
                {flipped ? card.back : card.front}
              </motion.p>
            </AnimatePresence>
          </div>
          <button
            type="button"
            aria-pressed={flipped}
            disabled={disabled}
            onClick={() => setFlipped((f) => !f)}
            className={buttonClass("secondary", "md", true)}
          >
            {t("flipCard")}
          </button>
          {flipped && (
            <div className="grid grid-cols-2 gap-2">
              <button type="button" disabled={disabled} onClick={() => rate(0)} className={buttonClass("secondary", "md", true)}>
                {t("again")}
              </button>
              <button type="button" disabled={disabled} onClick={() => rate(1)} className={buttonClass("secondary", "md", true)}>
                {t("gotIt")}
              </button>
            </div>
          )}
        </>
      )}
      {done && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAction?.({ widgetId, type: "ANSWER", payload: { self } })}
          className={buttonClass("primary", "md", true)}
        >
          {t("submitRatings")}
        </button>
      )}
    </section>
  );
}
