"use client";

import { useEffect, useRef } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/** Strip \\( \\) / $ wrappers LLMs often add — KaTeX wants the body only. */
export function sanitizeLatex(raw: string): string {
  let s = (raw || "").trim();
  if (!s) return s;
  for (const pat of [
    /^\$\$([\s\S]+?)\$\$/,
    /^\\\[([\s\S]+?)\\\]/,
    /^\\\(([\s\S]+?)\\\)/,
    /^\$([^$]+)\$$/,
  ]) {
    const m = s.match(pat);
    if (m) {
      s = m[1].trim();
      break;
    }
  }
  // Inline delimiters anywhere
  s = s
    .replace(/\\\(([\s\S]*?)\\\)/g, "$1")
    .replace(/\\\[([\s\S]*?)\\\]/g, "$1")
    .replace(/\$\$([\s\S]*?)\$\$/g, "$1")
    .replace(/\$([^$]+)\$/g, "$1");
  return s.trim();
}

export function MathText({
  latex,
  display = false,
  className = "",
}: {
  latex: string;
  display?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const cleaned = sanitizeLatex(latex);
    try {
      katex.render(cleaned, ref.current, {
        throwOnError: false,
        trust: false,
        displayMode: display,
        output: "htmlAndMathml",
        errorColor: "#94a3b8", // slate-400 — never KaTeX default red
      });
    } catch {
      ref.current.textContent = cleaned || latex;
    }
  }, [latex, display]);

  return <span ref={ref} className={`text-slate-100 ${className}`.trim()} />;
}
