"use client";

/** Minimal Markdown → React for primers (headings, paragraphs, line breaks, ``` fences, bold, KaTeX). */
import { createContext, useContext, type ReactNode } from "react";
import { MathText } from "@/components/math/MathText";

/** False for non-math/chem lessons: `$…$` stays literal text (e.g. "$5 a ticket"). */
export const MathNotation = createContext(true);

export function PrimerMarkdown({ source }: { source: string }) {
  const math = useContext(MathNotation);
  const blocks = source.trim().split(FENCE).filter((b) => b?.trim());
  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-300">
      {blocks.map((block, i) => {
        if (block.startsWith("```")) {
          return (
            <pre
              key={i}
              className="whitespace-pre-wrap break-words rounded-control bg-slate-950/70 p-3 font-mono text-sm text-slate-200"
            >
              {block.replace(/^```[^\n]*\n?|\n?```$/g, "")}
            </pre>
          );
        }
        const line = block.trim();
        if (line.startsWith("## ")) {
          return (
            <h3 key={i} className="text-base font-semibold text-slate-100">
              {inline(line.slice(3), math)}
            </h3>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h2 key={i} className="text-lg font-semibold text-slate-100">
              {inline(line.slice(2), math)}
            </h2>
          );
        }
        // Display math block $$...$$
        if (math && line.startsWith("$$") && line.endsWith("$$") && line.length > 4) {
          return (
            <MathText
              key={i}
              latex={line.slice(2, -2).trim()}
              display
              className="block text-slate-100"
            />
          );
        }
        return (
          <p key={i} className="whitespace-pre-line">
            {inline(line, math)}
          </p>
        );
      })}
    </div>
  );
}

/** Splits on blank lines, keeping each ``` fence (which may contain blank lines) as one block. */
const FENCE = /(```[^\n]*\n[\s\S]*?```)|\n\n+/;

/** Drops ``` fences, for widgets that render the code themselves. */
export const stripFences = (md: string) => md.replace(/```[^\n]*\n[\s\S]*?```/g, "").trim();

const WITH_MATH = /(\$\S[^$]*\$|\$\$[\s\S]+?\$\$|\*\*[^*]+\*\*|`[^`]+`)/g;
const TEXT_ONLY = /(\*\*[^*]+\*\*|`[^`]+`)/g;

function inline(text: string, math: boolean): ReactNode {
  const parts = text.split(math ? WITH_MATH : TEXT_ONLY);
  return parts.map((p, i) => {
    if (!p) return null;
    if (math && p.startsWith("$$") && p.endsWith("$$")) {
      return (
        <MathText
          key={i}
          latex={p.slice(2, -2).trim()}
          display
          className="my-1 block text-slate-100"
        />
      );
    }
    if (math && p.startsWith("$") && p.endsWith("$") && p.length > 2) {
      return (
        <MathText
          key={i}
          latex={p.slice(1, -1)}
          className="mx-0.5 text-slate-100"
        />
      );
    }
    if (p.startsWith("**") && p.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-slate-100">
          {p.slice(2, -2)}
        </strong>
      );
    }
    if (p.startsWith("`") && p.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-slate-800 px-1 font-mono text-xs text-neuro-teal"
        >
          {p.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{p}</span>;
  });
}
