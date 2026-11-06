"use client";

import { useMemo, useState } from "react";

const CURRENT_YEAR = new Date().getFullYear();
const MIN_YEAR = 1940;
const MAX_YEAR = CURRENT_YEAR - 5; // soft: learners typically school-age+

function decades(): number[] {
  const start = Math.floor(MIN_YEAR / 10) * 10;
  const end = Math.floor(MAX_YEAR / 10) * 10;
  const list: number[] = [];
  for (let d = end; d >= start; d -= 10) list.push(d);
  return list;
}

function yearsInDecade(decade: number): number[] {
  const years: number[] = [];
  for (let y = decade; y < decade + 10; y++) {
    if (y >= MIN_YEAR && y <= MAX_YEAR) years.push(y);
  }
  return years;
}

export function BirthYearPicker({
  value,
  onChange,
  decadeLabel,
  selectedLabel,
}: {
  value: number | null;
  onChange: (year: number) => void;
  decadeLabel: (decade: number) => string;
  selectedLabel: string;
}) {
  const decadeOptions = useMemo(() => decades(), []);
  const initialDecade =
    value != null ? Math.floor(value / 10) * 10 : decadeOptions[2] ?? decadeOptions[0];
  const [decade, setDecade] = useState(initialDecade);
  const years = yearsInDecade(decade);

  return (
    <div className="space-y-4">
      <div
        className="flex items-end justify-between rounded-control border border-line-strong bg-background/60 px-4 py-3"
        aria-live="polite"
      >
        <span className="text-xs font-mono uppercase tracking-wider text-slate-500">
          {selectedLabel}
        </span>
        <span className="font-mono text-3xl font-semibold tabular-nums text-slate-100">
          {value ?? "————"}
        </span>
      </div>

      <div
        className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        role="listbox"
        aria-label="Decade"
      >
        {decadeOptions.map((d) => {
          const active = d === decade;
          return (
            <button
              key={d}
              type="button"
              role="option"
              aria-selected={active}
              onClick={() => setDecade(d)}
              className={`min-h-12 shrink-0 rounded-full px-4 text-sm font-medium transition ${
                active
                  ? "bg-neuro-indigo text-white"
                  : "border border-line-strong bg-surface-raised text-slate-300 hover:border-slate-500"
              }`}
            >
              {decadeLabel(d)}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-5 gap-2 sm:grid-cols-5">
        {years.map((y) => {
          const selected = value === y;
          return (
            <button
              key={y}
              type="button"
              onClick={() => onChange(y)}
              aria-pressed={selected}
              className={`min-h-12 rounded-control font-mono text-sm tabular-nums transition ${
                selected
                  ? "bg-teal-500/15 text-teal-200 ring-2 ring-teal-400/60"
                  : "border border-line bg-surface-raised text-slate-200 hover:border-line-strong hover:bg-surface-subtle"
              }`}
            >
              {y}
            </button>
          );
        })}
      </div>
    </div>
  );
}
