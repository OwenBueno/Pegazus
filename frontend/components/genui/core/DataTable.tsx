"use client";

import { useContext } from "react";
import { MathNotation } from "@/components/learn/PrimerMarkdown";
import { MathText } from "@/components/math/MathText";

/** Small data table; cells are KaTeX only under math notation, plain text otherwise. Display-only. */
export function DataTable({
  headers,
  rows,
  highlight_col,
}: {
  headers: string[];
  rows: string[][];
  highlight_col?: number;
}) {
  const math = useContext(MathNotation);
  const cell = (s: string) => (math ? <MathText latex={s} /> : s);
  const tone = (j: number) => (j === highlight_col ? "bg-teal-950/40 text-neuro-teal" : "");
  return (
    <div className="overflow-x-auto rounded-panel border border-line bg-surface-glass p-2 backdrop-blur-xl">
      <table className="w-full text-center text-sm text-slate-200">
        <thead>
          <tr>
            {headers.map((h, j) => (
              <th key={j} scope="col" className={`border-b border-line-strong px-3 py-2 ${tone(j)}`}>
                {cell(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j} className={`border-b border-line px-3 py-2 ${tone(j)}`}>
                  {cell(c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
