"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { ConceptCard } from "@/components/genui/ConceptCard";
import { renderVisual } from "@/components/genui/registry";
import { RevealSteps } from "@/components/learn/RevealSteps";
import { BeatEyebrow, TeachBeatCard } from "@/components/learn/TeachBeatCard";
import { MathText } from "@/components/math/MathText";
import { Button } from "@/components/ui/Button";
import type { LessonBeat } from "@/lib/api";

const REVEAL_TYPES = new Set(["worked_example", "try_it", "important", "important_fact"]);

export function TeachBeatPanel({
  beat,
  onContinue,
  continueLabel,
  revealLabel,
  readyLabel,
}: {
  beat: LessonBeat;
  onContinue: () => void;
  continueLabel: string;
  revealLabel: string;
  readyLabel: string;
}) {
  const demo = beat.demo_steps ?? [];
  const needsReveal = demo.length > 0 && REVEAL_TYPES.has(beat.type);
  // Parent keys this panel per beat, so unlock state starts fresh on each beat.
  const [unlocked, setUnlocked] = useState(!needsReveal);

  const visual = renderVisual(beat.visual, `teach-visual-${beat.type}`);
  const layout = visual ? (beat.layout ?? "stack") : "stack";
  const card = beat.body_md ? (
    <ConceptCard
      title={beat.title || beat.type.replace(/_/g, " ")}
      body_md={beat.body_md}
      eyebrow={<BeatEyebrow type={beat.type} />}
      gateLabel={readyLabel}
      hideGate={!needsReveal}
      onAction={() => setUnlocked(true)}
    />
  ) : (
    <TeachBeatCard type={beat.type} title={beat.title}>
      <p className="text-sm text-slate-400">{continueLabel}</p>
    </TeachBeatCard>
  );

  return (
    <div className="space-y-5">
      {layout === "split" ? (
        <div className="grid gap-5 md:grid-cols-2 md:items-start">
          {card}
          {visual}
        </div>
      ) : layout === "focus" ? (
        <>
          {visual}
          {card}
        </>
      ) : (
        <>
          {card}
          {visual}
        </>
      )}
      {needsReveal && (
        <RevealSteps steps={demo} revealLabel={revealLabel} doneLabel={readyLabel} onComplete={() => setUnlocked(true)} />
      )}
      {!needsReveal && demo.length > 0 && (
        <ol className="space-y-2">
          {demo.map((s, i) => (
            <li key={`${i}-${s.latex}`} className="overflow-x-auto rounded-control border border-line bg-surface-raised px-4 py-3">
              <MathText latex={s.latex} display className="text-slate-100" />
            </li>
          ))}
        </ol>
      )}
      {/* Always visible; disabled only while reveal still required */}
      <div className="flex justify-end">
        <Button disabled={needsReveal && !unlocked} onClick={onContinue} className="w-full sm:w-auto">
          {continueLabel}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
