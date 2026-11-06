"use client";

import { useMemo, useState } from "react";

type Slider = {
  name: string;
  min: number;
  max: number;
  step: number;
  value: number;
};

/** Lightweight latex → y(x) for y=/f(x)=/linear/quadratic forms. No eval(). */
function latexToFn(
  latex: string,
  sliders: Record<string, number>,
): ((x: number) => number | null) | null {
  let s = latex
    .replace(/\\left|\\right/g, "")
    .replace(/\\,/g, "")
    .replace(/\s+/g, "")
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, "($1)/($2)")
    .replace(/\\cdot/g, "*")
    .replace(/\^{([^}]+)}/g, "**$1")
    .replace(/\^(\d+)/g, "**$1")
    .replace(/\{|\}/g, "");

  for (const [name, val] of Object.entries(sliders)) {
    s = s.replace(new RegExp(`\\b${name}\\b`, "g"), String(val));
  }

  const assign = s.match(/^(?:y|f\(x\))\s*=\s*(.+)$/i);
  if (assign) s = assign[1];

  // Equation a = b → plot lhs - rhs as y
  if (s.includes("=") && !assign) {
    const [lhs, rhs] = s.split("=");
    if (lhs && rhs) s = `(${lhs})-(${rhs})`;
  }

  // Only allow digits, x, operators, parens, and **
  const safe = s.replace(/\*\*/g, "");
  if (!/^[0-9xX+\-*/().]+$/.test(safe)) return null;

  try {
    // ponytail: Function only on sanitized arithmetic alphabet; ceiling = no general latex
    const fn = new Function("x", `return (${s.replace(/X/g, "x")});`) as (
      x: number,
    ) => number;
    return (x: number) => {
      try {
        const y = fn(x);
        return Number.isFinite(y) ? y : null;
      } catch {
        return null;
      }
    };
  } catch {
    return null;
  }
}

const W = 320;
const H = 200;
const PAD = 24;
const SAMPLES = 200;

export function FunctionPlotter({
  expressions,
  domain,
  sliders: sliderDefs = [],
  textAlt,
}: {
  expressions: string[];
  domain: [number, number];
  sliders?: Slider[];
  textAlt?: string;
}) {
  const [sliderVals, setSliderVals] = useState(() =>
    Object.fromEntries(sliderDefs.map((s) => [s.name, s.value])),
  );

  const series = useMemo(() => {
    const [x0, x1] = domain;
    return expressions.map((expr, ei) => {
      const f = latexToFn(expr, sliderVals);
      const pts: { x: number; y: number }[] = [];
      if (!f) return { expr, pts, color: COLORS[ei % COLORS.length] };
      for (let i = 0; i <= SAMPLES; i++) {
        const x = x0 + ((x1 - x0) * i) / SAMPLES;
        const y = f(x);
        if (y != null) pts.push({ x, y });
      }
      return { expr, pts, color: COLORS[ei % COLORS.length] };
    });
  }, [expressions, domain, sliderVals]);

  const yExtent = useMemo(() => {
    const ys = series.flatMap((s) => s.pts.map((p) => p.y));
    if (!ys.length) return [-5, 5] as const;
    const lo = Math.min(...ys);
    const hi = Math.max(...ys);
    const pad = (hi - lo) * 0.1 || 1;
    return [lo - pad, hi + pad] as const;
  }, [series]);

  const [x0, x1] = domain;
  const [y0, y1] = yExtent;
  const sx = (x: number) => PAD + ((x - x0) / (x1 - x0)) * (W - 2 * PAD);
  const sy = (y: number) => H - PAD - ((y - y0) / (y1 - y0)) * (H - 2 * PAD);

  const summary = series
    .map((s) => `${s.expr}: ${s.pts.length ? `${s.pts.length} samples` : "unplottable"}`)
    .join("; ");

  return (
    <figure className="space-y-2 rounded-panel border border-line bg-surface-glass p-3 backdrop-blur-xl sm:p-4">
      <figcaption className="font-mono text-xs uppercase tracking-wider text-slate-500">
        Graph
      </figcaption>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={textAlt || summary}
        className="mx-auto block max-w-full"
      >
        <line
          x1={PAD}
          y1={sy(0)}
          x2={W - PAD}
          y2={sy(0)}
          stroke="#475569"
          strokeWidth={1}
        />
        <line
          x1={sx(0)}
          y1={PAD}
          x2={sx(0)}
          y2={H - PAD}
          stroke="#475569"
          strokeWidth={1}
        />
        {series.map((s) => {
          if (s.pts.length < 2) return null;
          const d = s.pts
            .map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`)
            .join(" ");
          return (
            <path
              key={s.expr}
              d={d}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
            />
          );
        })}
      </svg>
      <p className="sr-only">{textAlt || summary}</p>
      <ul className="flex flex-wrap gap-3 font-mono text-xs text-slate-400" aria-hidden={Boolean(textAlt)}>
        {series.map((s) => (
          <li key={s.expr} style={{ color: s.color }}>
            {s.expr}
          </li>
        ))}
      </ul>
      {textAlt ? (
        <p className="text-xs leading-relaxed text-slate-400">{textAlt}</p>
      ) : null}
      {sliderDefs.map((sl) => (
        <label key={sl.name} className="block text-xs text-slate-400">
          {sl.name} = {sliderVals[sl.name]?.toFixed(2)}
          <input
            type="range"
            min={sl.min}
            max={sl.max}
            step={sl.step}
            value={sliderVals[sl.name] ?? sl.value}
            onChange={(e) =>
              setSliderVals((v) => ({
                ...v,
                [sl.name]: Number(e.target.value),
              }))
            }
            className="mt-1 w-full"
            aria-label={`Slider ${sl.name}`}
          />
        </label>
      ))}
    </figure>
  );
}

const COLORS = ["#818cf8", "#2dd4bf", "#f472b6", "#fbbf24"];
