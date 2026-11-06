"use client";

import { useMemo } from "react";
import {
  parseGenUI,
  type GenUIWorkspacePayload,
  type WidgetAction,
} from "@/lib/contracts/genui";
import { renderWidget, type WidgetHandlers } from "./registry";

const MAX_VISIBLE = 4;

export function WorkspaceRenderer({
  payload,
  handlers,
  errorLabel = "Could not load this exercise.",
}: {
  payload: unknown;
  handlers?: WidgetHandlers;
  errorLabel?: string;
}) {
  const parsed = useMemo(() => {
    try {
      return { ok: true as const, data: parseGenUI(payload) };
    } catch {
      // Strip nulls (server may emit justification: null) and retry once
      try {
        const cleaned = JSON.parse(
          JSON.stringify(payload, (_, v) => (v === null ? undefined : v)),
        );
        return { ok: true as const, data: parseGenUI(cleaned) };
      } catch {
        return { ok: false as const, data: null };
      }
    }
  }, [payload]);

  if (!parsed.ok || !parsed.data) {
    return (
      <p role="alert" className="text-sm text-neuro-alert">
        {errorLabel}
      </p>
    );
  }

  const data: GenUIWorkspacePayload = parsed.data;
  const visible = prioritizeWidgets(data.widgets).slice(0, MAX_VISIBLE);

  return (
    <div className="space-y-4">
      {visible.map((w) => (
        <div key={w.id}>{renderWidget(w, handlers)}</div>
      ))}
    </div>
  );
}

function prioritizeWidgets(
  widgets: GenUIWorkspacePayload["widgets"],
): GenUIWorkspacePayload["widgets"] {
  const priority = (t: string) => {
    switch (t) {
      case "ConceptCard":
        return 0;
      case "QuickCheck":
      case "NumberLine":
      case "MatchPairs":
      case "ShortAnswer":
      case "FreeResponse":
      case "Cloze":
      case "OrderSteps":
      case "Categorize":
      case "Flashcards":
      case "WorkedExample":
        return 1;
      case "FadedWorkedExample":
        return 2;
      case "SymbolicStepEditor":
        return 3;
      case "FunctionPlotter":
        return 5;
      case "SocraticDialogueBox":
        return 6;
      case "VirtualMathKeyboard":
        return 7;
      default:
        return 9;
    }
  };
  return [...widgets].sort((a, b) => priority(a.type) - priority(b.type));
}

export type { WidgetAction };
