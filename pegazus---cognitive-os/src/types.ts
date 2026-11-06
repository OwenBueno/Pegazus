/**
 * Project Cognitive OS (Pegazus) - Type Definitions
 * Source: UI/UX Spec Doc 09 & Doc 06
 */

export type Locale = 'en' | 'es';

export type AppRoute =
  | 'HOME'
  | 'AUTH_SIGNIN'
  | 'AUTH_CALLBACK'
  | 'ONBOARD_AGE'
  | 'CONSENT_WAIT'
  | 'SETTINGS'
  | 'SETTINGS_BYO'
  | 'SETTINGS_DELETE'
  | 'PATH_CREATE'
  | 'PATH_VIEW'
  | 'DIAGNOSTIC'
  | 'SESSION'
  | 'SESSION_SUMMARY'
  | 'SESSION_REST'
  | 'SOCRATIC';

export type NodeStatus = 'locked' | 'frontier' | 'mastered' | 'due_review' | 'drafting';

export interface PathNode {
  id: string;
  title: string;
  mathTitle?: string;
  description: string;
  status: NodeStatus;
  masteryPercent: number; // 0 - 100
  dueDate?: string;
  estimatedMinutes: number;
  prerequisites: string[];
  sourceAttribution: string;
  scaffoldTier: 1 | 2 | 3;
}

export interface LearningPath {
  id: string;
  title: string;
  subject: string;
  targetDate?: string;
  dailyBudgetMinutes: number;
  status: 'DRAFTING' | 'REFINING' | 'ACTIVE' | 'COMPLETED';
  criticalPathMinutes: number;
  nodes: PathNode[];
  fitWarning?: {
    isOverloaded: boolean;
    requiredDailyMinutes: number;
  };
}

export interface StepItem {
  id: string;
  latex: string;
  justification?: string;
  isLocked: boolean;
  status?: 'correct' | 'incorrect' | 'pending';
  feedback?: string;
}

export interface FadedExampleData {
  problemStatement: string;
  scaffoldLevel: 1 | 2 | 3;
  steps: StepItem[];
  missingPartIndex?: number;
  expectedInput?: string;
}

export interface FunctionPlotData {
  type: 'quadratic' | 'sine';
  title: string;
  a: number;
  b: number;
  c: number;
  xRange: [number, number];
  yRange: [number, number];
}

export interface SocraticExchange {
  role: 'learner' | 'socratic';
  text: string;
  highlightId?: string;
}

export interface UserProfile {
  email: string;
  locale: Locale;
  birthYear: number | null;
  isMinor: boolean;
  guardianConsentGiven: boolean;
  preferredSessionMinutes: number;
  targetRetention: number; // e.g. 0.90
  microBreakIntervalMinutes: number; // 5-7 mins
  focusPrimingEnabled: boolean;
  openRouterApiKey?: string;
  isOffline: boolean;
}

export interface SessionStats {
  durationSeconds: number;
  itemsCompleted: number;
  reviewsDone: number;
  frontierAdvanced: number;
  nodesUpdated: string[];
}
