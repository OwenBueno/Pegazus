"use client";

type P = { x: number; y: number; label?: string };

const SIZE = 220;
const PAD = 10;

/** Square grid over [lo, hi] on both axes with labeled points and segments. Display-only. */
export function CoordinateGrid({
  range,
  points,
  segments = [],
}: {
  range: [number, number];
  points: P[];
  segments?: [number, number][];
}) {
  const [lo, hi] = range;
  const span = hi - lo;
  const sx = (x: number) => PAD + ((x - lo) / span) * (SIZE - 2 * PAD);
  const sy = (y: number) => SIZE - PAD - ((y - lo) / span) * (SIZE - 2 * PAD);
  // ponytail: one gridline per unit; ranges are capped at 40 units server-side.
  const ticks = Array.from({ length: Math.floor(span) + 1 }, (_, i) => Math.ceil(lo) + i).filter((t) => t <= hi);
  const desc = points.map((p) => `${p.label ?? ""}(${p.x}, ${p.y})`).join(", ");

  return (
    <figure className="rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl sm:p-5">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={`Points ${desc}`} className="mx-auto h-56 w-full max-w-xs">
        {ticks.map((t) => (
          <g key={t} className={t === 0 ? "stroke-slate-400" : "stroke-slate-800"}>
            <line x1={sx(t)} y1={PAD} x2={sx(t)} y2={SIZE - PAD} />
            <line x1={PAD} y1={sy(t)} x2={SIZE - PAD} y2={sy(t)} />
          </g>
        ))}
        {segments.map(([a, b], i) =>
          points[a] && points[b] ? (
            <line
              key={i}
              x1={sx(points[a].x)}
              y1={sy(points[a].y)}
              x2={sx(points[b].x)}
              y2={sy(points[b].y)}
              className="stroke-neuro-teal"
              strokeWidth="2"
            />
          ) : null,
        )}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={sx(p.x)} cy={sy(p.y)} r="4" className="fill-neuro-teal" />
            <text x={sx(p.x) + 6} y={sy(p.y) - 6} className="fill-slate-100 text-[11px]">
              {p.label ? `${p.label}(${p.x}, ${p.y})` : `(${p.x}, ${p.y})`}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}
