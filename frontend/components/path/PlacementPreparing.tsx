"use client";

/** Calm wait state while placement questions are generated or graded. */
export function PlacementPreparing({ label }: { label: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy
      className="rounded-panel border border-line bg-surface-glass px-5 py-12 text-center backdrop-blur-xl"
    >
      <div className="mx-auto mb-5 h-1 w-32 overflow-hidden rounded-full bg-white/5">
        <div className="h-full w-2/5 rounded-full bg-neuro-teal/80 motion-safe:animate-placement-scan" />
      </div>
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  );
}
