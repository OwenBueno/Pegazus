"use client";

import { useEffect } from "react";
import { Keyboard } from "lucide-react";

/** Configures MathLive's native virtual keyboard for the focused math-field. */
export function VirtualMathKeyboard({
  layout,
}: {
  layout: "algebra" | "calculus";
  targetWidgetId: string;
}) {
  useEffect(() => {
    // MathLive types already declare window.mathVirtualKeyboard
    const kb = (
      window as unknown as {
        mathVirtualKeyboard?: { layouts?: unknown };
      }
    ).mathVirtualKeyboard;
    if (!kb) return;
    try {
      kb.layouts =
        layout === "calculus" ? ["numeric", "symbols"] : ["numeric", "symbols"];
    } catch {
      /* MathLive version variance */
    }
  }, [layout]);

  return (
    <p className="flex items-center gap-1.5 font-mono text-micro uppercase tracking-wider text-slate-600" aria-hidden="true">
      <Keyboard className="h-3.5 w-3.5" />
      {layout}
    </p>
  );
}
