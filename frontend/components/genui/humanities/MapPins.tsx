"use client";

import { useTranslations } from "next-intl";
import type { MAP_REGIONS } from "@/lib/contracts/genui";

type Region = (typeof MAP_REGIONS)[number];

/** [lonMin, lonMax, latMin, latMax] + i18n name key. */
const REGION_BOX: Record<Region, { box: [number, number, number, number]; key: string }> = {
  world: { box: [-180, 180, -60, 80], key: "mapRegionWorld" },
  europe: { box: [-25, 45, 34, 72], key: "mapRegionEurope" },
  africa: { box: [-20, 55, -37, 38], key: "mapRegionAfrica" },
  asia: { box: [25, 150, -12, 60], key: "mapRegionAsia" },
  middle_east: { box: [25, 65, 10, 43], key: "mapRegionMiddleEast" },
  north_america: { box: [-170, -50, 5, 75], key: "mapRegionNorthAmerica" },
  south_america: { box: [-85, -30, -57, 14], key: "mapRegionSouthAmerica" },
  oceania: { box: [105, 180, -50, 5], key: "mapRegionOceania" },
};

// ponytail: coarse hand-drawn [lon, lat] outlines (no inland seas, few islands) — fine for context, wrong for
// precise geography. Upgrade path: Natural Earth 110m TopoJSON loaded lazily and projected the same way.
const LAND: [number, number][][] = [
  // North America
  [[-168, 66], [-162, 70], [-140, 70], [-120, 72], [-95, 72], [-80, 73], [-62, 66], [-55, 52], [-66, 45], [-70, 41],
   [-76, 35], [-81, 31], [-80, 25], [-82, 28], [-84, 30], [-90, 29], [-97, 27], [-97, 22], [-92, 19], [-87, 21],
   [-88, 16], [-83, 10], [-77, 8], [-80, 7], [-86, 12], [-92, 14], [-105, 20], [-110, 24], [-112, 31], [-117, 32],
   [-124, 40], [-124, 48], [-132, 55], [-140, 60], [-152, 58], [-165, 54], [-158, 58], [-166, 62]],
  // Greenland
  [[-73, 78], [-60, 82], [-30, 83], [-20, 75], [-22, 70], [-42, 60], [-52, 64], [-58, 75]],
  // South America
  [[-77, 8], [-72, 12], [-62, 10], [-52, 5], [-50, 0], [-35, -5], [-38, -13], [-40, -22], [-48, -26], [-53, -34],
   [-58, -38], [-62, -41], [-65, -45], [-68, -50], [-69, -55], [-74, -52], [-73, -42], [-71, -30], [-70, -18],
   [-76, -14], [-81, -6], [-80, -1], [-77, 4]],
  // Africa
  [[-17, 21], [-16, 28], [-10, 30], [-6, 36], [10, 37], [11, 33], [20, 31], [32, 31], [34, 28], [39, 21], [43, 12],
   [51, 12], [48, 4], [40, -3], [40, -15], [35, -24], [32, -29], [27, -34], [20, -35], [18, -32], [12, -17],
   [13, -6], [9, -1], [9, 4], [4, 6], [-5, 5], [-12, 7], [-17, 14]],
  // Madagascar
  [[44, -25], [47, -25], [50, -15], [49, -12], [44, -17]],
  // Eurasia
  [[-6, 36], [-9, 37], [-9, 43], [-2, 44], [-5, 48], [2, 51], [8, 54], [10, 57], [5, 59], [5, 62], [14, 67], [25, 71],
   [40, 68], [45, 68], [60, 69], [70, 73], [80, 73], [100, 77], [115, 74], [130, 71], [140, 72], [160, 70], [180, 69],
   [180, 65], [170, 60], [163, 58], [156, 51], [143, 59], [135, 54], [140, 48], [132, 43], [127, 39], [126, 35],
   [122, 40], [121, 32], [119, 25], [110, 21], [106, 17], [109, 12], [105, 9], [100, 13], [101, 3], [104, 1], [98, 8],
   [98, 16], [92, 22], [87, 22], [80, 15], [77, 8], [73, 18], [69, 22], [62, 25], [57, 25], [56, 27], [52, 28],
   [48, 30], [50, 26], [56, 24], [59, 22], [52, 16], [44, 13], [42, 16], [35, 28], [34, 31], [36, 36], [30, 36],
   [27, 38], [26, 41], [23, 40], [24, 37], [21, 38], [19, 42], [13, 45], [16, 41], [18, 40], [15, 38], [12, 42],
   [8, 44], [3, 43], [-1, 37]],
  // Great Britain
  [[-5, 50], [1, 51], [2, 53], [-2, 56], [-2, 58], [-5, 58], [-6, 56], [-3, 54], [-5, 52]],
  // Japan
  [[130, 31], [135, 34], [140, 35], [142, 40], [141, 45], [144, 43], [140, 41], [136, 37], [131, 34]],
  // Australia
  [[114, -22], [122, -18], [130, -12], [137, -12], [136, -15], [141, -11], [146, -19], [153, -25], [150, -37],
   [141, -38], [135, -35], [129, -32], [115, -34], [113, -26]],
  // New Zealand
  [[172, -34], [178, -38], [174, -41], [168, -46], [166, -46], [172, -41]],
];

const W = 600;

/** Static equirectangular map with numbered pins + a visible text list. Display-only. */
export function MapPins({
  region,
  pins,
  caption,
}: {
  region: Region;
  pins: { lat: number; lon: number; label: string }[];
  caption?: string;
}) {
  const t = useTranslations("session");
  const { box, key } = REGION_BOX[region] ?? REGION_BOX.world;
  const [lonMin, lonMax, latMin, latMax] = box;
  const s = W / (lonMax - lonMin);
  const H = Math.round((latMax - latMin) * s);
  const x = (lon: number) => (lon - lonMin) * s;
  const y = (lat: number) => (latMax - lat) * s;
  const step = lonMax - lonMin > 100 ? 30 : 10;
  const grid = (min: number, max: number) =>
    Array.from({ length: Math.floor(max / step) - Math.ceil(min / step) + 1 }, (_, i) => (Math.ceil(min / step) + i) * step);
  const regionName = t(key);
  const fmt = (p: { lat: number; lon: number }) =>
    t("mapCoords", {
      lat: Math.abs(p.lat).toFixed(1),
      latDir: p.lat >= 0 ? "n" : "s",
      lon: Math.abs(p.lon).toFixed(1),
      lonDir: p.lon >= 0 ? "e" : "w",
    });

  return (
    <figure className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">
        {t("mapTitle", { region: regionName })}
      </p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={caption ? `${caption} — ${t("mapAria", { region: regionName, count: pins.length })}` : t("mapAria", { region: regionName, count: pins.length })}
        className="h-auto w-full overflow-hidden rounded-control border border-line bg-slate-950/40"
      >
        <g className="stroke-slate-500/20" strokeWidth={1}>
          {grid(lonMin, lonMax).map((lon) => (
            <line key={`x${lon}`} x1={x(lon)} x2={x(lon)} y1={0} y2={H} />
          ))}
          {grid(latMin, latMax).map((lat) => (
            <line key={`y${lat}`} x1={0} x2={W} y1={y(lat)} y2={y(lat)} />
          ))}
        </g>
        <g className="fill-slate-400/15 stroke-slate-400/30" strokeWidth={1} strokeLinejoin="round">
          {LAND.map((poly, i) => (
            <polygon key={i} points={poly.map(([lon, lat]) => `${x(lon).toFixed(1)},${y(lat).toFixed(1)}`).join(" ")} />
          ))}
        </g>
        {pins.map((p, i) => {
          const px = Math.min(W - 10, Math.max(10, x(p.lon)));
          const py = Math.min(H - 10, Math.max(10, y(p.lat)));
          // ponytail: naive fit check (avg glyph width), no overlap avoidance; upgrade = label collision pass.
          const showLabel = px + 16 + p.label.length * 6.5 < W;
          return (
            <g key={i}>
              <circle cx={px} cy={py} r={9} className="fill-teal-500 stroke-slate-950" strokeWidth={1.5} />
              <text x={px} y={py + 3.5} textAnchor="middle" className="fill-slate-950 font-mono text-[10px] font-bold">
                {i + 1}
              </text>
              {showLabel && (
                <text x={px + 14} y={py + 4} className="fill-slate-100 text-[12px]" paintOrder="stroke" stroke="#020617" strokeWidth={3}>
                  {p.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {caption ? <figcaption className="text-sm text-slate-300">{caption}</figcaption> : null}
      <ol className="space-y-1 text-sm" aria-label={t("mapPinList")}>
        {pins.map((p, i) => (
          <li key={i} className="flex gap-2">
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-teal-500 font-mono text-[10px] font-bold text-slate-950">
              {i + 1}
            </span>
            <span className="text-slate-100">{p.label}</span>
            <span className="font-mono text-xs leading-5 text-slate-400">{fmt(p)}</span>
          </li>
        ))}
      </ol>
    </figure>
  );
}
