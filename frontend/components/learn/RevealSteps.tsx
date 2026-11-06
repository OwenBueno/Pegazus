"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ChevronDown } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { MathText } from "@/components/math/MathText";
import { Button } from "@/components/ui/Button";

/** Cognitive worked-example: reveal one step at a time before practice. */
export function RevealSteps({
  steps,
  revealLabel,
  doneLabel,
  onComplete,
}: {
  steps: { latex: string }[];
  revealLabel: string;
  doneLabel: string;
  onComplete?: () => void;
}) {
  // Progress is tied to this steps array; new steps start again at one.
  const [progress, setProgress] = useState({ steps, shown: 1 });
  const shown = progress.steps === steps ? progress.shown : 1;
  const doneFor = useRef<typeof steps | null>(null);
  const allShown = steps.length === 0 || shown >= steps.length;

  useEffect(() => {
    if (!allShown || doneFor.current === steps) return;
    doneFor.current = steps;
    onComplete?.();
  }, [allShown, onComplete, steps]);

  if (!steps.length) return null;

  return (
    <div className="space-y-3">
      <ol className="relative space-y-2 pl-9">
        <span aria-hidden className="absolute bottom-3 left-[13px] top-3 w-px bg-line-strong" />
        <AnimatePresence initial={false}>
          {steps.slice(0, shown).map((s, i) => (
            <motion.li
              key={`${i}-${s.latex}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative rounded-control border border-line bg-surface-raised px-4 py-3"
            >
              <span className="absolute -left-9 top-3 grid h-7 w-7 place-items-center rounded-full border border-line-strong bg-surface font-mono text-[11px] text-slate-300">
                {i + 1}
              </span>
              <div className="overflow-x-auto">
                <MathText latex={s.latex} display className="text-slate-50" />
              </div>
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>
      <div aria-live="polite">
        {!allShown ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setProgress({ steps, shown: Math.min(shown + 1, steps.length) })}
          >
            <ChevronDown className="h-4 w-4" aria-hidden />
            {revealLabel}
          </Button>
        ) : (
          <p className="flex items-center gap-1.5 text-sm text-neuro-teal">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            {doneLabel}
          </p>
        )}
      </div>
    </div>
  );
}
