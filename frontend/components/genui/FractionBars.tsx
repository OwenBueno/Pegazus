"use client";

import { MathText } from "@/components/math/MathText";

type Bar = { parts: number; shaded: number; label?: string };

/** Bar model: each bar split into equal parts, `shaded` of them filled. Display-only. */
export function FractionBars({ bars }: { bars: Bar[] }) {
  return (
    <figure className="space-y-3 rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl sm:p-5">
      {bars.map((b, i) => (
        <div key={i} className="flex items-center gap-3">
          <div
            role="img"
            aria-label={`${b.shaded} of ${b.parts} equal parts shaded`}
            className="flex h-9 flex-1 overflow-hidden rounded-control border border-line-strong"
          >
            {Array.from({ length: b.parts }, (_, j) => (
              <div
                key={j}
                className={`flex-1 border-slate-600 ${j ? "border-l" : ""} ${
                  j < b.shaded ? "bg-neuro-teal/70" : "bg-background/40"
                }`}
              />
            ))}
          </div>
          {b.label ? (
            <MathText latex={toLatex(b.label)} className="w-14 shrink-0 text-right" />
          ) : null}
        </div>
      ))}
    </figure>
  );
}

function toLatex(label: string): string {
  const m = label.match(/^\s*(\d+)\s*\/\s*(\d+)\s*$/);
  return m ? `\\frac{${m[1]}}{${m[2]}}` : label;
}
