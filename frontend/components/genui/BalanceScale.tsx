"use client";

import { MathText } from "@/components/math/MathText";

/** Equation as a level balance: same value on both pans. Display-only. */
export function BalanceScale({
  left,
  right,
  note,
}: {
  left: string;
  right: string;
  note?: string;
}) {
  return (
    <figure
      className="space-y-2 rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl sm:p-5"
      aria-label={`Balance: ${left} on the left equals ${right} on the right`}
    >
      <div className="grid grid-cols-2 gap-6">
        {[left, right].map((side, i) => (
          <div
            key={i}
            className="flex min-h-14 items-center justify-center rounded-control border border-teal-500/25 bg-teal-500/[0.05] px-3 py-2"
          >
            <MathText latex={side} display />
          </div>
        ))}
      </div>
      <svg viewBox="0 0 200 60" className="mx-auto h-14 w-full max-w-xs" aria-hidden>
        <line x1="20" y1="10" x2="180" y2="10" className="stroke-slate-400" strokeWidth="3" />
        <line x1="100" y1="10" x2="100" y2="50" className="stroke-slate-500" strokeWidth="3" />
        <polygon points="85,58 115,58 100,44" className="fill-slate-500" />
        <circle cx="100" cy="10" r="4" className="fill-neuro-teal" />
      </svg>
      {note ? <figcaption className="text-center text-sm text-slate-300">{note}</figcaption> : null}
    </figure>
  );
}
