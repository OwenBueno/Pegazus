import type { GenUIWorkspacePayload } from "@/lib/contracts/genui";
import type { SessionItem } from "@/lib/api";

/** Derive plot expressions from statement latex when shape is recognizable. */
export function plotExpressionsFromLatex(latex: string): string[] | null {
  const s = latex.trim();
  if (/^(?:y|f\s*\(\s*x\s*\))\s*=/i.test(s)) return [s];
  if (/x\s*\^\s*\{?\s*2\s*\}?/i.test(s) || /x\^\{2\}/.test(s)) return [s];
  // Drop \times etc. so "x" inside times is not treated as a variable
  const plain = s
    .replace(/\\(?:times|div|cdot|left|right)\b/gi, "")
    .replace(/\\/g, "");
  if (
    plain.includes("=") &&
    !/[<>]/.test(plain) &&
    /(?<![a-z])x(?![a-z])/i.test(plain)
  ) {
    return [s];
  }
  return null;
}

const MAX_WIDGETS = 4;

/** Client-side GenUI fallback when server payload absent. */
export function buildSessionGenUI(opts: {
  sessionId: string;
  nodeId: string;
  item: SessionItem;
  stepIndex: number;
  scaffoldLevel: 1 | 2 | 3;
  hintTier: 1 | 2 | 3 | null;
  hintPrompt: string | null;
}): GenUIWorkspacePayload {
  const {
    sessionId,
    nodeId,
    item,
    stepIndex,
    scaffoldLevel,
    hintTier,
    hintPrompt,
  } = opts;

  const parts = item.parts ?? [];
  if (parts.length && parts[0].grader !== "sympy") {
    const part = parts[Math.min(stepIndex, parts.length - 1)];
    // Shape is validated by WorkspaceRenderer's parse; props are answer-key free.
    const widgets = [
      { id: "answer", type: part.component, visible: true, props: part.props },
    ] as GenUIWorkspacePayload["widgets"];
    if (hintTier && hintPrompt) {
      widgets.push({ id: "socratic", type: "SocraticDialogueBox", visible: true, props: { hintTier, prompt: hintPrompt.slice(0, 240) } });
    }
    return { sessionId, nodeId, itemId: item.id, scaffoldLevel, answerMode: "selection", widgets };
  }

  const steps = item.steps.slice(0, stepIndex + 1).map((s, i) => ({
    stepNumber: i + 1,
    latexExpression: i < stepIndex ? s.latex : "",
    isLocked: i < stepIndex,
    status: (i < stepIndex ? "VALID" : "PENDING") as "VALID" | "PENDING",
    justification: s.justification ?? undefined,
  }));
  if (steps.length === 0) {
    steps.push({
      stepNumber: 1,
      latexExpression: "",
      isLocked: false,
      status: "PENDING",
      justification: undefined,
    });
  }

  const fadedSteps = item.steps.slice(0, stepIndex + 1).map((s, i) => ({
    stepNumber: i + 1,
    latexExpression: i < stepIndex ? s.latex : "",
    isLocked: i < stepIndex,
    status: (i < stepIndex ? "VALID" : "PENDING") as "VALID" | "PENDING",
    justification: s.justification ?? undefined,
  }));

  const gapLatex =
    scaffoldLevel === 1
      ? (item.steps[stepIndex]?.gap_latex ?? "").trim()
      : "";

  const widgets: GenUIWorkspacePayload["widgets"] = [];

  if (scaffoldLevel <= 2) {
    widgets.push({
      id: "faded",
      type: "FadedWorkedExample",
      visible: true,
      props: {
        problemStatement: item.statement_latex,
        steps: fadedSteps.length
          ? fadedSteps
          : [
              {
                stepNumber: 1,
                latexExpression: "",
                isLocked: false,
                status: "PENDING",
              },
            ],
        activeStepIndex: Math.min(stepIndex, Math.max(0, fadedSteps.length - 1)),
        scaffoldLevel,
        ...(gapLatex ? { gapLatex } : {}),
      },
    });
  }

  if (scaffoldLevel >= 3) {
    widgets.push({
      id: "steps",
      type: "SymbolicStepEditor",
      visible: true,
      props: {
        targetVariable: "x",
        inlineValidation: true,
        activeStepIndex: Math.min(stepIndex, steps.length - 1),
        initialSteps: steps,
      },
    });
  }

  widgets.push({
    id: "kbd",
    type: "VirtualMathKeyboard",
    visible: true,
    props: {
      layout: "algebra",
      targetWidgetId: scaffoldLevel <= 2 ? "faded" : "steps",
    },
  });

  const plotExprs = plotExpressionsFromLatex(item.statement_latex);
  if (plotExprs && widgets.length < MAX_WIDGETS) {
    widgets.push({
      id: "plot",
      type: "FunctionPlotter",
      visible: true,
      props: {
        expressions: plotExprs,
        domain: [-10, 10],
      },
    });
  }

  if (hintTier && hintPrompt && widgets.length < MAX_WIDGETS) {
    widgets.push({
      id: "socratic",
      type: "SocraticDialogueBox",
      visible: true,
      props: {
        hintTier,
        prompt: hintPrompt.slice(0, 240),
      },
    });
  }

  return {
    sessionId,
    nodeId,
    itemId: item.id,
    scaffoldLevel,
    answerMode: "symbolic",
    widgets: widgets.slice(0, MAX_WIDGETS),
  };
}

/** Prefill latex from GenUI faded gap or item step gap_latex. */
export function gapPrefillFromGenui(
  genui: GenUIWorkspacePayload | null | undefined,
  item: SessionItem | null | undefined,
  stepIndex: number,
): string {
  if (genui?.widgets) {
    for (const w of genui.widgets) {
      if (w.type === "FadedWorkedExample" && w.props.gapLatex) {
        return w.props.gapLatex;
      }
    }
  }
  return (item?.steps[stepIndex]?.gap_latex ?? "").trim();
}
