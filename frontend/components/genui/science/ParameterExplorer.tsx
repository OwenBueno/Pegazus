"use client";

import { useId, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { compile } from "@/lib/safeExpr";

type Param = { name: string; min: number; max: number; value: number };

const W = 320;
const H = 200;
const PAD = 24;
const SAMPLES = 200;

const fmt = (v: number) => String(Number(v.toPrecision(3)));

/** y = expr(x) with live parameter sliders. Expression compiled by lib/safeExpr (no eval). */
export function ParameterExplorer({
  expr,
  x,
  domain,
  params,
  textAlt,
}: {
  expr: string;
  x: string;
  domain: [number, number];
  params: Param[];
  textAlt: string;
}) {
  const t = useTranslations("session");
  const id = useId();
  const [vals, setVals] = useState<Record<string, number>>(() => Object.fromEntries(params.map((p) => [p.name, p.value])));

  const names = params.map((p) => p.name).join("\u0000");
  const fn = useMemo(() => compile(expr, [x, ...names.split("\u0000")]), [expr, x, names]);
  const [x0, x1] = domain;
  const plottable = fn !== null && Number.isFinite(x0) && Number.isFinite(x1) && x0 < x1;

  const segments = useMemo(() => {
    const segs: { x: number; y: number }[][] = [];
    if (!fn || !plottable) return segs;
    let cur: { x: number; y: number }[] = [];
    for (let i = 0; i <= SAMPLES; i++) {
      const xv = x0 + ((x1 - x0) * i) / SAMPLES;
      const y = fn({ ...vals, [x]: xv });
      if (Number.isFinite(y)) cur.push({ x: xv, y });
      else if (cur.length) {
        segs.push(cur);
        cur = [];
      }
    }
    if (cur.length) segs.push(cur);
    return segs;
  }, [plottable, fn, vals, x, x0, x1]);

  // ponytail: y-range is plain min/max, so asymptotes (tan, 1/x) flatten the rest; upgrade = percentile clipping.
  const ys = segments.flat().map((p) => p.y);
  const lo = ys.length ? Math.min(...ys) : -1;
  const hi = ys.length ? Math.max(...ys) : 1;
  const yPad = (hi - lo) * 0.1 || 1;
  const [y0, y1] = [lo - yPad, hi + yPad];
  const sx = (v: number) => PAD + ((v - x0) / (x1 - x0)) * (W - 2 * PAD);
  const sy = (v: number) => H - PAD - ((v - y0) / (y1 - y0)) * (H - 2 * PAD);
  const axisY = sy(Math.min(Math.max(0, y0), y1));
  const axisX = sx(Math.min(Math.max(0, x0), x1));

  const current = params.map((p) => `${p.name} = ${fmt(vals[p.name] ?? p.value)}`).join(", ");

  return (
    <figure className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("explorer")}</p>
      <p className="font-mono text-sm text-slate-200">y = {expr}</p>
      {plottable ? (
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={textAlt}
          aria-describedby={`${id}-d`}
          className="mx-auto block h-auto w-full max-w-md"
        >
          <line x1={PAD} y1={axisY} x2={W - PAD} y2={axisY} stroke="#475569" strokeWidth={1} />
          <line x1={axisX} y1={PAD} x2={axisX} y2={H - PAD} stroke="#475569" strokeWidth={1} />
          <text x={PAD} y={H - 6} fill="#94a3b8" fontSize={10}>
            {fmt(x0)}
          </text>
          <text x={W - PAD} y={H - 6} fill="#94a3b8" fontSize={10} textAnchor="end">
            {fmt(x1)}
          </text>
          <text x={4} y={PAD} fill="#94a3b8" fontSize={10}>
            {fmt(y1)}
          </text>
          <text x={4} y={H - PAD} fill="#94a3b8" fontSize={10}>
            {fmt(y0)}
          </text>
          {segments.map((seg, i) =>
            seg.length < 2 ? null : (
              <path
                key={i}
                d={seg.map((p, j) => `${j ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ")}
                fill="none"
                stroke="#818cf8"
                strokeWidth={2}
              />
            ),
          )}
        </svg>
      ) : (
        <p className="text-sm text-slate-400">{t("explorerInvalid")}</p>
      )}
      <figcaption id={`${id}-d`} className="space-y-1 text-sm leading-relaxed text-slate-300">
        <span className="block">{textAlt}</span>
        <span className="block text-xs text-slate-400">{t("explorerCurrent", { values: current })}</span>
      </figcaption>
      {params.map((p) => {
        const v = vals[p.name] ?? p.value;
        return (
          <div key={p.name} className="space-y-1">
            <label htmlFor={`${id}-${p.name}`} className="flex justify-between font-mono text-xs text-slate-300">
              <span>{p.name}</span>
              <span aria-hidden>{fmt(v)}</span>
            </label>
            <input
              id={`${id}-${p.name}`}
              type="range"
              min={p.min}
              max={p.max}
              step={(p.max - p.min) / 100 || 1}
              value={v}
              aria-valuetext={`${p.name} = ${fmt(v)}`}
              onChange={(e) => setVals((s) => ({ ...s, [p.name]: Number(e.target.value) }))}
              className="w-full accent-indigo-400"
            />
          </div>
        );
      })}
    </figure>
  );
}
