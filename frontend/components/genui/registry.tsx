"use client";

import dynamic from "next/dynamic";
import { AnyWidgetSchema, type AnyWidgetConfig, type WidgetAction } from "@/lib/contracts/genui";
import { BalanceScale } from "./BalanceScale";
import { Callout } from "./Callout";
import { ConceptCard } from "./ConceptCard";
import { CoordinateGrid } from "./CoordinateGrid";
import { Categorize } from "./core/Categorize";
import { Cloze } from "./core/Cloze";
import { Comparison } from "./core/Comparison";
import { DataTable } from "./core/DataTable";
import { Flashcards } from "./core/Flashcards";
import { FreeResponse } from "./core/FreeResponse";
import { KeyTerms } from "./core/KeyTerms";
import { OrderSteps } from "./core/OrderSteps";
import { ProcessSteps } from "./core/ProcessSteps";
import { ShortAnswer } from "./core/ShortAnswer";
import { WorkedExample } from "./core/WorkedExample";
import { FadedWorkedExample } from "./FadedWorkedExample";
import { FractionBars } from "./FractionBars";
import { ShapeDiagram } from "./ShapeDiagram";
import { FunctionPlotter } from "./FunctionPlotter";
import { MatchPairs } from "./MatchPairs";
import { NumberLine } from "./NumberLine";
import { QuickCheck } from "./QuickCheck";
import { SocraticDialogueBox } from "./SocraticDialogueBox";
import { SymbolicStepEditor } from "./SymbolicStepEditor";
import { VirtualMathKeyboard } from "./VirtualMathKeyboard";

const loading = () => <div aria-hidden className="min-h-32 animate-pulse rounded-panel border border-line bg-surface-glass" />;
const Diagram = dynamic(() => import("./core/Diagram").then((m) => m.Diagram), { ssr: false, loading });
// Family packs (Doc 11 Phase 4): lazy so the core session route bundle does not grow.
const Timeline = dynamic(() => import("./humanities/Timeline").then((m) => m.Timeline), { ssr: false, loading });
const MapPins = dynamic(() => import("./humanities/MapPins").then((m) => m.MapPins), { ssr: false, loading });
const SourceExcerpt = dynamic(() => import("./humanities/SourceExcerpt").then((m) => m.SourceExcerpt), { ssr: false, loading });
const CauseEffect = dynamic(() => import("./humanities/CauseEffect").then((m) => m.CauseEffect), { ssr: false, loading });
const AudioClip = dynamic(() => import("./language/AudioClip").then((m) => m.AudioClip), { ssr: false });
const Pronunciation = dynamic(() => import("./language/Pronunciation").then((m) => m.Pronunciation), { ssr: false, loading });
const TranslationAnswer = dynamic(() => import("./language/TranslationAnswer").then((m) => m.TranslationAnswer), { ssr: false, loading });
const ChemFormula = dynamic(() => import("./science/ChemFormula").then((m) => m.ChemFormula), { ssr: false, loading });
const QuantityAnswer = dynamic(() => import("./science/QuantityAnswer").then((m) => m.QuantityAnswer), { ssr: false, loading });
const ParameterExplorer = dynamic(() => import("./science/ParameterExplorer").then((m) => m.ParameterExplorer), { ssr: false, loading });
const LabeledDiagram = dynamic(() => import("./science/LabeledDiagram").then((m) => m.LabeledDiagram), { ssr: false, loading });
const CodeBlock = dynamic(() => import("./code/CodeBlock").then((m) => m.CodeBlock), { ssr: false, loading });
const PredictOutput = dynamic(() => import("./code/PredictOutput").then((m) => m.PredictOutput), { ssr: false, loading });
const CodeExercise = dynamic(() => import("./code/CodeExercise").then((m) => m.CodeExercise), { ssr: false, loading });

export type WidgetHandlers = {
  stepValue?: string;
  onStepChange?: (latex: string) => void;
  onAction?: (a: WidgetAction) => void;
  /** Locks selection widgets while grading or once the item is solved. */
  answerLocked?: boolean;
};

/** Beat-level picture chosen by the lesson designer; invalid props render nothing. */
export function renderVisual(
  visual: { type: string; props: Record<string, unknown> } | undefined,
  id: string,
) {
  if (!visual) return null;
  const parsed = AnyWidgetSchema.safeParse({ id, type: visual.type, visible: true, props: visual.props });
  return parsed.success ? renderWidget(parsed.data) : null;
}

export function renderWidget(
  widget: AnyWidgetConfig,
  handlers: WidgetHandlers = {},
) {
  if (!widget.visible) return null;
  switch (widget.type) {
    case "SymbolicStepEditor":
      return (
        <SymbolicStepEditor
          {...widget.props}
          widgetId={widget.id}
          value={handlers.stepValue}
          onChange={handlers.onStepChange}
          onAction={handlers.onAction}
        />
      );
    case "SocraticDialogueBox":
      return <SocraticDialogueBox {...widget.props} />;
    case "VirtualMathKeyboard":
      return <VirtualMathKeyboard {...widget.props} />;
    case "FadedWorkedExample":
      return (
        <FadedWorkedExample
          {...widget.props}
          gapValue={handlers.stepValue}
          onGapChange={handlers.onStepChange}
        />
      );
    case "FunctionPlotter":
      return <FunctionPlotter {...widget.props} />;
    case "QuickCheck":
      return (
        <QuickCheck
          {...widget.props}
          widgetId={widget.id}
          disabled={handlers.answerLocked}
          onAction={handlers.onAction}
        />
      );
    case "ConceptCard":
      return (
        <ConceptCard
          {...widget.props}
          widgetId={widget.id}
          onAction={handlers.onAction}
        />
      );
    case "NumberLine":
      return (
        <NumberLine
          {...widget.props}
          widgetId={widget.id}
          disabled={handlers.answerLocked}
          onAction={handlers.onAction}
        />
      );
    case "MatchPairs":
      return (
        <MatchPairs
          {...widget.props}
          widgetId={widget.id}
          disabled={handlers.answerLocked}
          onAction={handlers.onAction}
        />
      );
    case "FractionBars":
      return <FractionBars {...widget.props} />;
    case "BalanceScale":
      return <BalanceScale {...widget.props} />;
    case "DataTable":
    case "ValueTable":
      return <DataTable {...widget.props} />;
    case "ShortAnswer":
      return (
        <ShortAnswer {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "FreeResponse":
      return (
        <FreeResponse {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "Cloze":
      return <Cloze {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />;
    case "OrderSteps":
      return (
        <OrderSteps {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "Categorize":
      return (
        <Categorize {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "Flashcards":
      return (
        <Flashcards {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "WorkedExample":
      return (
        <WorkedExample {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "Comparison":
      return <Comparison {...widget.props} />;
    case "ProcessSteps":
      return <ProcessSteps {...widget.props} />;
    case "KeyTerms":
      return <KeyTerms {...widget.props} />;
    case "Diagram":
      return <Diagram {...widget.props} />;
    case "Timeline":
      return <Timeline {...widget.props} />;
    case "MapPins":
      return <MapPins {...widget.props} />;
    case "SourceExcerpt":
      return <SourceExcerpt {...widget.props} />;
    case "CauseEffect":
      return <CauseEffect {...widget.props} />;
    case "AudioClip":
      return <AudioClip {...widget.props} />;
    case "ChemFormula":
      return <ChemFormula {...widget.props} />;
    case "ParameterExplorer":
      return <ParameterExplorer {...widget.props} />;
    case "LabeledDiagram":
      return <LabeledDiagram {...widget.props} />;
    case "CodeBlock":
      return <CodeBlock {...widget.props} />;
    case "Pronunciation":
      return (
        <Pronunciation {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "TranslationAnswer":
      return (
        <TranslationAnswer {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "QuantityAnswer":
      return (
        <QuantityAnswer {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "PredictOutput":
      return (
        <PredictOutput {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "CodeExercise":
      return (
        <CodeExercise {...widget.props} widgetId={widget.id} disabled={handlers.answerLocked} onAction={handlers.onAction} />
      );
    case "Callout":
      return <Callout {...widget.props} />;
    case "ShapeDiagram":
      return <ShapeDiagram {...widget.props} />;
    case "CoordinateGrid":
      return <CoordinateGrid {...widget.props} />;
    default:
      return null;
  }
}
