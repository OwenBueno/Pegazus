"use client";

import { Sigma } from "lucide-react";
import { MathText } from "@/components/math/MathText";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import { Card, CardHeader } from "@/components/ui/Card";

/** True when latex string is really English prose jammed into math mode. */
export function statementLooksLikeProse(latex: string): boolean {
  const s = latex.trim();
  if (!s) return false;
  const letters = (s.match(/[A-Za-z]/g) || []).length;
  const hasMathOp = /[=<>+\-*/^\\]|\\frac|\\times|\\div|\\cdot/.test(s);
  return letters > 20 && !hasMathOp;
}

/**
 * Readable problem statement: prose as text, math via KaTeX.
 * Never send long English through KaTeX alone (spaces collapse).
 * `promptMd` (§6.2 items) renders as Markdown; `$…$` is KaTeX only under MathNotation.
 */
export function ProblemStatement({
  prompt,
  promptMd,
  statementLatex,
  label,
}: {
  prompt?: string | null;
  promptMd?: string | null;
  statementLatex: string;
  label?: string;
}) {
  const latex = (statementLatex || "").trim();
  const md = (promptMd || "").trim();
  if (!latex && md) {
    return (
      <Card variant="glass" className="relative overflow-hidden">
        {label ? <CardHeader icon={<Sigma className="h-3.5 w-3.5" aria-hidden />} label={label} tone="text-indigo-300" className="mb-3" /> : null}
        <div className="text-[17px] [&_p]:text-[17px] [&_p]:text-slate-100">
          <PrimerMarkdown source={md} />
        </div>
      </Card>
    );
  }
  const prose = (prompt || "").trim();
  const fallbackProse = !prose && latex && statementLooksLikeProse(latex);
  const showProse = prose || (fallbackProse ? latex : "");
  const showMath = latex && !fallbackProse;

  return (
    <Card variant="glass" className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/50 to-transparent"
      />
      {label ? <CardHeader icon={<Sigma className="h-3.5 w-3.5" aria-hidden />} label={label} tone="text-indigo-300" className="mb-3" /> : null}
      {showProse ? (
        <p className={`text-[17px] leading-relaxed text-slate-100 ${showMath ? "mb-4" : ""}`}>{showProse}</p>
      ) : null}
      {showMath ? (
        <div className="overflow-x-auto py-1">
          <MathText latex={latex} display className="text-2xl text-white" />
        </div>
      ) : null}
    </Card>
  );
}
