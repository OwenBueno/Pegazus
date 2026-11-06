"use client";

import type { ReactNode } from "react";

export const inputClass =
  "min-h-12 w-full rounded-control border border-line-strong bg-background/60 px-3.5 text-slate-100 outline-none transition-[border-color,box-shadow] placeholder:text-slate-500 focus:border-neuro-indigo focus:ring-4 focus:ring-neuro-indigo/15";

export function FormField({
  label,
  hint,
  htmlFor,
  children,
  error,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
  error?: string | null;
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <label htmlFor={htmlFor} className="font-display text-[15px] font-semibold text-slate-100">
          {label}
        </label>
        {hint && <span className="text-xs text-slate-500">{hint}</span>}
      </div>
      {children}
      {error && (
        <p role="alert" className="text-sm text-neuro-alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function FieldPanel({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl sm:p-5">{children}</div>
  );
}
