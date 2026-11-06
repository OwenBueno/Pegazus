/** GenUI flat widget contract — interactive catalog. */
import { z } from "zod";

export const DerivationStepSchema = z.object({
  stepNumber: z.number().int().positive(),
  latexExpression: z.string(),
  isLocked: z.boolean(),
  status: z.enum(["VALID", "INVALID", "PENDING"]).nullish(),
  justification: z.string().nullish(),
});

export const SymbolicStepEditorSchema = z.object({
  id: z.string(),
  type: z.literal("SymbolicStepEditor"),
  visible: z.boolean(),
  props: z.object({
    targetVariable: z.string(),
    inlineValidation: z.boolean(),
    activeStepIndex: z.number().int().nonnegative(),
    initialSteps: z.array(DerivationStepSchema),
  }),
});

export const VirtualMathKeyboardSchema = z.object({
  id: z.string(),
  type: z.literal("VirtualMathKeyboard"),
  visible: z.boolean(),
  props: z.object({
    layout: z.enum(["algebra", "calculus"]),
    targetWidgetId: z.string(),
  }),
});

export const SocraticDialogueBoxSchema = z.object({
  id: z.string(),
  type: z.literal("SocraticDialogueBox"),
  visible: z.boolean(),
  props: z.object({
    hintTier: z.union([z.literal(1), z.literal(2), z.literal(3)]),
    prompt: z.string().max(240),
    highlightElementId: z.string().optional(),
  }),
});

export const FadedWorkedExampleSchema = z.object({
  id: z.string(),
  type: z.literal("FadedWorkedExample"),
  visible: z.boolean(),
  props: z.object({
    problemStatement: z.string(),
    steps: z.array(DerivationStepSchema),
    activeStepIndex: z.number().int().nonnegative(),
    scaffoldLevel: z.union([z.literal(1), z.literal(2), z.literal(3)]).optional(),
    gapLatex: z.string().optional(),
  }),
});

export const FunctionPlotterSchema = z.object({
  id: z.string(),
  type: z.literal("FunctionPlotter"),
  visible: z.boolean(),
  props: z.object({
    expressions: z.array(z.string()).min(1),
    domain: z.tuple([z.number(), z.number()]),
    sliders: z
      .array(
        z.object({
          name: z.string(),
          min: z.number(),
          max: z.number(),
          step: z.number(),
          value: z.number(),
        }),
      )
      .optional(),
    textAlt: z.string().optional(),
  }),
});

export const QuickCheckSchema = z.object({
  id: z.string(),
  type: z.literal("QuickCheck"),
  visible: z.boolean(),
  props: z.object({
    prompt: z.string().max(400),
    choices: z.array(z.object({ id: z.string(), label: z.string().max(200) })).min(2).max(6),
    labelsAreLatex: z.boolean().optional(),
  }),
});

export const ConceptCardSchema = z.object({
  id: z.string(),
  type: z.literal("ConceptCard"),
  visible: z.boolean(),
  props: z.object({
    title: z.string().max(120),
    body_md: z.string().max(2500),
    latex: z.string().optional(),
    gateLabel: z.string().max(80).optional(),
  }),
});

export const NumberLineSchema = z.object({
  id: z.string(),
  type: z.literal("NumberLine"),
  visible: z.boolean(),
  props: z.object({
    min: z.number(),
    max: z.number(),
    step: z.number().positive().optional(),
    prompt: z.string().max(240).optional(),
  }),
});

export const MatchPairsSchema = z.object({
  id: z.string(),
  type: z.literal("MatchPairs"),
  visible: z.boolean(),
  props: z.object({
    prompt: z.string().max(240).optional(),
    lefts: z.array(z.string().max(200)).min(2).max(6),
    rights: z.array(z.string().max(200)).min(2).max(6),
  }),
});

/* Display-only visuals (catalog: backend/app/services/component_catalog.py). */
const visual = <T extends string, P extends z.ZodRawShape>(type: T, props: P) =>
  z.object({ id: z.string(), type: z.literal(type), visible: z.boolean(), props: z.object(props) });

export const FractionBarsSchema = visual("FractionBars", {
  bars: z
    .array(
      z.object({
        parts: z.number().int().min(1).max(12),
        shaded: z.number().int().min(0),
        label: z.string().max(20).optional(),
      }),
    )
    .min(1)
    .max(4),
});

export const BalanceScaleSchema = visual("BalanceScale", {
  left: z.string().max(80),
  right: z.string().max(80),
  note: z.string().max(160).optional(),
});

export const ValueTableSchema = visual("ValueTable", {
  headers: z.array(z.string().max(30)).min(1).max(6),
  rows: z.array(z.array(z.string().max(40))).min(1).max(12),
  highlight_col: z.number().int().nonnegative().optional(),
});

export const CalloutSchema = visual("Callout", {
  tone: z.enum(["tip", "warning", "fact"]),
  title: z.string().max(80).optional(),
  body_md: z.string().min(1).max(600),
});

export const ShapeDiagramSchema = visual("ShapeDiagram", {
  shape: z.enum(["triangle", "rectangle", "circle", "polygon"]),
  labels: z.record(z.string(), z.string().max(20)).optional(),
  angles: z.array(z.number()).max(10).optional(),
  sides: z.number().int().min(3).max(10).optional(),
});

export const CoordinateGridSchema = visual("CoordinateGrid", {
  range: z.tuple([z.number(), z.number()]),
  points: z
    .array(z.object({ x: z.number(), y: z.number(), label: z.string().max(8).optional() }))
    .min(1)
    .max(12),
  segments: z.array(z.tuple([z.number().int(), z.number().int()])).max(12).optional(),
});

/* Core generic components (Doc 10 §4.2). Answer props are key-free; widgets emit
 * {type: "ANSWER", payload: <grader answer>} and the server grades from answer_spec. */
const answer = <T extends string, P extends z.ZodRawShape>(type: T, props: P) =>
  z.object({ id: z.string(), type: z.literal(type), visible: z.boolean(), props: z.object(props) });

const str = (n: number) => z.string().max(n);
const segments = z.array(str(300)).min(2).max(5); // blanks sit between segments

export const ShortAnswerSchema = answer("ShortAnswer", { question: str(400) });

export const FreeResponseSchema = answer("FreeResponse", {
  question: str(600),
  max_words: z.number().int().min(10).max(300),
});

export const ClozeSchema = answer("Cloze", { prompt: str(240).optional(), segments });

export const OrderStepsSchema = answer("OrderSteps", {
  prompt: str(240).optional(),
  items: z.array(str(160)).min(3).max(7),
});

export const CategorizeSchema = answer("Categorize", {
  prompt: str(240).optional(),
  buckets: z.array(str(60)).min(2).max(4),
  items: z.array(str(120)).min(4).max(10),
});

export const FlashcardsSchema = answer("Flashcards", {
  cards: z.array(z.object({ front: str(160), back: str(160) })).min(3).max(12),
});

export const WorkedExampleSchema = answer("WorkedExample", {
  title: str(120).optional(),
  steps: z.array(z.object({ segments: z.array(str(300)).min(1).max(3) })).min(2).max(8),
});

export const DataTableSchema = visual("DataTable", {
  headers: z.array(z.string().max(30)).min(1).max(6),
  rows: z.array(z.array(z.string().max(40))).min(1).max(12),
  highlight_col: z.number().int().nonnegative().optional(),
});

const side = z.object({ title: str(60), points: z.array(str(160)).min(1).max(6) });
export const ComparisonSchema = visual("Comparison", { left: side, right: side });

export const ProcessStepsSchema = visual("ProcessSteps", {
  steps: z.array(z.object({ title: str(80), body: str(300).optional() })).min(2).max(8),
  cyclic: z.boolean().optional(),
});

export const KeyTermsSchema = visual("KeyTerms", {
  terms: z.array(z.object({ term: str(60), def: str(300) })).min(1).max(8),
});

export const DiagramSchema = visual("Diagram", {
  kind: z.enum(["mermaid", "svg"]),
  source: z.string().min(1).max(2000),
  alt: z.string().min(1).max(300),
});

/* Family packs (Doc 10 §4.2, Doc 11 Phase 4); each pack is lazy-loaded in registry.tsx. */
const lang = z.string().regex(/^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,3}$/);
export const MAP_REGIONS = [
  "world", "europe", "africa", "asia", "middle_east", "north_america", "south_america", "oceania",
] as const;
const codeLanguage = z.enum(["python", "javascript"]);

export const TimelineSchema = visual("Timeline", {
  title: str(120).optional(),
  events: z
    .array(z.object({ date: str(20), year: z.number().int(), label: str(120), detail: str(240).optional() }))
    .min(2)
    .max(12),
});

export const MapPinsSchema = visual("MapPins", {
  region: z.enum(MAP_REGIONS),
  pins: z
    .array(z.object({ lat: z.number().min(-90).max(90), lon: z.number().min(-180).max(180), label: str(60) }))
    .min(1)
    .max(12),
  caption: str(200).optional(),
});

export const SourceExcerptSchema = visual("SourceExcerpt", {
  quote: z.string().min(1).max(600),
  author: str(120).optional(),
  source: str(160).optional(),
  year: z.number().int().optional(),
  url: z.url({ protocol: /^https?$/ }).max(500).optional(),
});

export const CauseEffectSchema = visual("CauseEffect", {
  title: str(120).optional(),
  links: z.array(z.object({ cause: str(200), effect: str(200) })).min(1).max(6),
});

export const AudioClipSchema = visual("AudioClip", {
  text: z.string().min(1).max(200),
  lang,
  rate: z.number().min(0.5).max(1.5).optional(),
  label: str(120).optional(),
});

export const PronunciationSchema = answer("Pronunciation", {
  phrase: z.string().min(1).max(160),
  lang,
  prompt: str(240).optional(),
});

export const TranslationAnswerSchema = answer("TranslationAnswer", {
  source: z.string().min(1).max(300),
  lang,
  prompt: str(240).optional(),
});

export const ChemFormulaSchema = visual("ChemFormula", {
  latex: z.string().min(1).max(300),
  caption: str(200).optional(),
});

export const QuantityAnswerSchema = answer("QuantityAnswer", {
  question: str(400),
  unit: str(12),
  units: z.array(str(12)).min(1).max(12),
});

export const ParameterExplorerSchema = visual("ParameterExplorer", {
  expr: z.string().min(1).max(160),
  x: str(8),
  domain: z.tuple([z.number(), z.number()]),
  params: z
    .array(z.object({ name: str(8), min: z.number(), max: z.number(), value: z.number() }))
    .min(1)
    .max(3),
  textAlt: z.string().min(1).max(400),
});

export const LabeledDiagramSchema = visual("LabeledDiagram", {
  source: z.string().max(3000).optional(),
  labels: z
    .array(z.object({ x: z.number().min(0).max(1), y: z.number().min(0).max(1), text: str(60) }))
    .min(1)
    .max(12),
  alt: z.string().min(1).max(300),
});

export const CodeBlockSchema = visual("CodeBlock", {
  language: codeLanguage,
  code: z.string().min(1).max(3000),
  caption: str(200).optional(),
});

export const PredictOutputSchema = answer("PredictOutput", {
  language: codeLanguage,
  code: z.string().min(1).max(3000),
  prompt: str(240).optional(),
});

export const CodeExerciseSchema = answer("CodeExercise", {
  language: codeLanguage,
  starter: z.string().max(3000),
  tests: z.array(z.object({ call: str(200), expect: str(200).optional(), stdout: str(500).optional() })).min(1).max(8),
  prompt: str(400).optional(),
  beta: z.boolean().optional(),
});

export const AnyWidgetSchema = z.discriminatedUnion("type", [
  TimelineSchema,
  MapPinsSchema,
  SourceExcerptSchema,
  CauseEffectSchema,
  AudioClipSchema,
  PronunciationSchema,
  TranslationAnswerSchema,
  ChemFormulaSchema,
  QuantityAnswerSchema,
  ParameterExplorerSchema,
  LabeledDiagramSchema,
  CodeBlockSchema,
  PredictOutputSchema,
  CodeExerciseSchema,
  ShortAnswerSchema,
  FreeResponseSchema,
  ClozeSchema,
  OrderStepsSchema,
  CategorizeSchema,
  FlashcardsSchema,
  WorkedExampleSchema,
  DataTableSchema,
  ComparisonSchema,
  ProcessStepsSchema,
  KeyTermsSchema,
  DiagramSchema,
  FractionBarsSchema,
  BalanceScaleSchema,
  ValueTableSchema,
  CalloutSchema,
  ShapeDiagramSchema,
  CoordinateGridSchema,
  SymbolicStepEditorSchema,
  VirtualMathKeyboardSchema,
  SocraticDialogueBoxSchema,
  FadedWorkedExampleSchema,
  FunctionPlotterSchema,
  QuickCheckSchema,
  ConceptCardSchema,
  NumberLineSchema,
  MatchPairsSchema,
]);

export const GenUIWorkspacePayloadSchema = z.object({
  sessionId: z.string(),
  nodeId: z.string(),
  itemId: z.string(),
  scaffoldLevel: z.union([z.literal(1), z.literal(2), z.literal(3)]),
  answerMode: z.enum(["selection", "symbolic"]).optional(),
  widgets: z.array(AnyWidgetSchema).max(6),
});

export type GenUIWorkspacePayload = z.infer<typeof GenUIWorkspacePayloadSchema>;
export type AnyWidgetConfig = z.infer<typeof AnyWidgetSchema>;
export type DerivationStep = z.infer<typeof DerivationStepSchema>;
/** Widget action types that carry a grader answer for part 0 (graded server-side). */
export const ANSWER_ACTIONS = new Set(["ANSWER", "QUICK_CHECK", "NUMBER_LINE", "MATCH_PAIRS"]);
export type WidgetAction = {
  widgetId: string;
  type: string;
  payload: unknown;
};

export function parseGenUI(raw: unknown): GenUIWorkspacePayload {
  return GenUIWorkspacePayloadSchema.parse(raw);
}
