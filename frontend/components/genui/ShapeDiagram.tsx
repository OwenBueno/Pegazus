"use client";

type Shape = "triangle" | "rectangle" | "circle" | "polygon";
type Pt = [number, number];

/**
 * Labeled geometry sketch (not to scale). Label keys: triangle a/b/c (side opposite
 * vertex A/B/C) + angles at A,B,C; rectangle width/height; circle r; polygon side.
 */
export function ShapeDiagram({
  shape,
  labels = {},
  angles,
  sides = 5,
}: {
  shape: Shape;
  labels?: Record<string, string>;
  angles?: number[];
  sides?: number;
}) {
  const desc = Object.entries(labels)
    .map(([k, v]) => `${k} = ${v}`)
    .join(", ");
  return (
    <figure className="rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl sm:p-5">
      <svg
        viewBox="0 0 240 200"
        role="img"
        aria-label={`${shape}${desc ? `: ${desc}` : ""}${angles ? `; angles ${angles.join(", ")} degrees` : ""}`}
        className="mx-auto h-48 w-full max-w-sm"
      >
        {render(shape, labels, angles, sides)}
      </svg>
    </figure>
  );
}

const stroke = "fill-teal-950/30 stroke-neuro-teal";
const text = "fill-slate-100 text-[13px]";

function Label({ at, children }: { at: Pt; children: string }) {
  return (
    <text x={at[0]} y={at[1]} textAnchor="middle" dominantBaseline="middle" className={text}>
      {children}
    </text>
  );
}

function mid(a: Pt, b: Pt, push: Pt = [0, 0]): Pt {
  return [(a[0] + b[0]) / 2 + push[0], (a[1] + b[1]) / 2 + push[1]];
}

function render(shape: Shape, labels: Record<string, string>, angles: number[] | undefined, sides: number) {
  if (shape === "circle") {
    return (
      <>
        <circle cx="120" cy="100" r="70" className={stroke} strokeWidth="2" />
        <line x1="120" y1="100" x2="190" y2="100" className="stroke-slate-400" strokeDasharray="4 3" />
        <circle cx="120" cy="100" r="3" className="fill-slate-300" />
        {labels.r ? <Label at={[155, 90]}>{labels.r}</Label> : null}
      </>
    );
  }
  if (shape === "rectangle") {
    return (
      <>
        <rect x="40" y="40" width="160" height="110" className={stroke} strokeWidth="2" />
        {labels.width ? <Label at={[120, 168]}>{labels.width}</Label> : null}
        {labels.height ? <Label at={[218, 95]}>{labels.height}</Label> : null}
      </>
    );
  }
  const pts: Pt[] =
    shape === "triangle"
      ? [[30, 170], [210, 170], [90, 30]]
      : Array.from({ length: sides }, (_, i) => {
          const t = (2 * Math.PI * i) / sides - Math.PI / 2;
          return [120 + 80 * Math.cos(t), 100 + 80 * Math.sin(t)] as Pt;
        });
  const names = ["A", "B", "C"];
  return (
    <>
      <polygon points={pts.map((p) => p.join(",")).join(" ")} className={stroke} strokeWidth="2" />
      {shape === "triangle" ? (
        <>
          {labels.a ? <Label at={mid(pts[1], pts[2], [14, 0])}>{labels.a}</Label> : null}
          {labels.b ? <Label at={mid(pts[0], pts[2], [-14, 0])}>{labels.b}</Label> : null}
          {labels.c ? <Label at={mid(pts[0], pts[1], [0, 16])}>{labels.c}</Label> : null}
          {pts.map((p, i) => (
            <Label key={i} at={[p[0] + (i === 0 ? -12 : i === 1 ? 12 : 0), p[1] + (i === 2 ? -12 : 10)]}>
              {names[i] + (angles?.[i] != null ? ` ${angles[i]}°` : "")}
            </Label>
          ))}
        </>
      ) : (
        <>
          {labels.side ? <Label at={mid(pts[0], pts[1], [10, -6])}>{labels.side}</Label> : null}
          {angles?.map((a, i) => (
            <Label key={i} at={[120 + (pts[i][0] - 120) * 0.72, 100 + (pts[i][1] - 100) * 0.72]}>
              {`${a}°`}
            </Label>
          ))}
        </>
      )}
    </>
  );
}
