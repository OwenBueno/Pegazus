import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Clock, Lightbulb, AlertCircle, CheckCircle2, ChevronRight, X } from 'lucide-react';
import { useTranslation } from '../i18n/context';
import { MathView } from '../components/common/MathView';
import { FadedWorkedExample } from '../components/genui/FadedWorkedExample';
import { FunctionPlotter } from '../components/genui/FunctionPlotter';
import { SocraticDialogueBox } from '../components/genui/SocraticDialogueBox';
import { VirtualMathKeyboard } from '../components/genui/VirtualMathKeyboard';
import { HintDrawer } from '../components/genui/HintDrawer';
import { RestOverlay } from '../components/modals/RestOverlay';
import { FocusPrimingModal } from '../components/modals/FocusPrimingModal';
import { StepItem, LearningPath, SessionStats } from '../types';

interface SessionScreenProps {
  path: LearningPath | null;
  isOffline: boolean;
  onFinishSession: (stats: SessionStats) => void;
  onExitSession: () => void;
  focusPrimingEnabled?: boolean;
}

interface ExerciseItem {
  id: string;
  nodeTitle: string;
  mode: 'review' | 'new';
  statement: string;
  scaffoldTier: 1 | 2 | 3;
  steps: StepItem[];
  expectedLastStep: string;
  socraticPromptOnFail: string;
  hintData: {
    tier1: string;
    tier2: string;
    tier3: string;
    tier3Latex?: string;
  };
  hasPlotter?: boolean;
  plotterParams?: {
    a: number;
    b: number;
    c: number;
    type: 'quadratic' | 'sine';
  };
}

const mockExercises: ExerciseItem[] = [
  {
    id: 'ex-1',
    nodeTitle: 'Power Rule & Polynomial Derivatives',
    mode: 'review',
    statement: 'Find the derivative: \\frac{d}{dx}\\left(4x^3 - 5x + 9\\right)',
    scaffoldTier: 2,
    steps: [
      {
        id: 's1',
        latex: '\\frac{d}{dx}(4x^3) - \\frac{d}{dx}(5x) + \\frac{d}{dx}(9)',
        justification: 'Apply linearity and sum/difference rule',
        isLocked: true,
        status: 'correct'
      },
      {
        id: 's2',
        latex: '',
        isLocked: false
      }
    ],
    expectedLastStep: '12x^2-5',
    socraticPromptOnFail: 'Recall the power rule: \\frac{d}{dx}[x^n] = n x^{n-1}. What is the derivative of the constant term 9?',
    hintData: {
      tier1: 'Differentiate each term independently using the power rule for x^n.',
      tier2: 'For 4x^3, multiply the power 3 by the coefficient 4 to get 12x^2. For 5x, the power is 1.',
      tier3: 'The constant 9 vanishes (derivative is 0), leaving 12x^2 - 5.',
      tier3Latex: '12x^2 - 5'
    },
    hasPlotter: true,
    plotterParams: {
      a: 1,
      b: 0,
      c: -5,
      type: 'quadratic'
    }
  },
  {
    id: 'ex-2',
    nodeTitle: 'Chain Rule with Composite Functions',
    mode: 'new',
    statement: 'Differentiate the composite function: f(x) = (2x^2 + 1)^4',
    scaffoldTier: 1,
    steps: [
      {
        id: 's1',
        latex: 'u = 2x^2 + 1 \\implies \\frac{du}{dx} = 4x',
        justification: 'Identify inner function u and its derivative',
        isLocked: true,
        status: 'correct'
      },
      {
        id: 's2',
        latex: '\\frac{d}{du}[u^4] = 4u^3 = 4(2x^2 + 1)^3',
        justification: 'Differentiate outer power function',
        isLocked: true,
        status: 'correct'
      },
      {
        id: 's3',
        latex: '',
        isLocked: false
      }
    ],
    expectedLastStep: '16x(2x^2+1)^3',
    socraticPromptOnFail: 'Chain rule requires multiplying the outer derivative by the inner derivative du/dx. Notice how 4 and 4x combine.',
    hintData: {
      tier1: 'Combine outer and inner derivatives: (d/du)[f(u)] * (du/dx).',
      tier2: 'Multiply the outer derivative 4(2x^2 + 1)^3 by the inner derivative (4x).',
      tier3: 'Group the outer scalar 4 with 4x to yield 16x(2x^2 + 1)^3.',
      tier3Latex: '16x(2x^2 + 1)^3'
    }
  }
];

export const SessionScreen: React.FC<SessionScreenProps> = ({
  path,
  isOffline,
  onFinishSession,
  onExitSession,
  focusPrimingEnabled = false
}) => {
  const { t } = useTranslation();

  // Session timer state: 15 minutes planned budget default (900 seconds)
  const [budgetSeconds, setBudgetSeconds] = useState<number>(900);
  const [activePracticeSeconds, setActivePracticeSeconds] = useState<number>(0);
  const [currentExerciseIdx, setCurrentExerciseIdx] = useState<number>(0);
  const [currentInput, setCurrentInput] = useState<string>('');
  const [steps, setSteps] = useState<StepItem[]>([]);
  const [activeStepIdx, setActiveStepIdx] = useState<number>(1);
  const [verdict, setVerdict] = useState<'correct' | 'incorrect' | 'offline_queued' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [socraticMessage, setSocraticMessage] = useState<string | null>(null);

  // Hints
  const [hintDrawerOpen, setHintDrawerOpen] = useState<boolean>(false);
  const [hintTier, setHintTier] = useState<1 | 2 | 3>(1);

  // Micro-break RestOverlay state
  const [showRestOverlay, setShowRestOverlay] = useState<boolean>(false);
  const [lastRestAtSeconds, setLastRestAtSeconds] = useState<number>(0);

  // Focus Priming Modal (if enabled in settings)
  const [showPriming, setShowPriming] = useState<boolean>(focusPrimingEnabled);

  // Exit confirmation dialog
  const [showExitConfirm, setShowExitConfirm] = useState<boolean>(false);

  // Telemetry tracking
  const [completedItemsCount, setCompletedItemsCount] = useState<number>(0);
  const [reviewsDoneCount, setReviewsDoneCount] = useState<number>(0);
  const [frontierAdvancedCount, setFrontierAdvancedCount] = useState<number>(0);

  const currentExercise = mockExercises[currentExerciseIdx];

  // Initialize exercise
  useEffect(() => {
    if (currentExercise) {
      setSteps(currentExercise.steps);
      const activeIdx = currentExercise.steps.findIndex((s) => !s.isLocked);
      setActiveStepIdx(activeIdx >= 0 ? activeIdx : currentExercise.steps.length - 1);
      setCurrentInput('');
      setVerdict(null);
      setSocraticMessage(null);
      setHintDrawerOpen(false);
      setHintTier(1);
    }
  }, [currentExerciseIdx, currentExercise]);

  // Budget timer & active time counter
  useEffect(() => {
    const timer = setInterval(() => {
      setBudgetSeconds((prev) => (prev > 0 ? prev - 1 : 0));
      setActivePracticeSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Format budget clock: MM:SS
  const mins = Math.floor(budgetSeconds / 60);
  const secs = budgetSeconds % 60;
  const budgetFormatted = `${mins}:${secs.toString().padStart(2, '0')}`;
  const isBudgetLow = budgetSeconds < 300; // < 5 min

  const handleInputChange = (val: string) => {
    setCurrentInput(val);
    if (verdict === 'incorrect') {
      setVerdict(null);
    }
  };

  const handleInsertToken = (token: string) => {
    setCurrentInput((prev) => prev + token);
    if (verdict === 'incorrect') {
      setVerdict(null);
    }
  };

  const handleBackspace = () => {
    setCurrentInput((prev) => prev.slice(0, -1));
  };

  const handleClear = () => {
    setCurrentInput('');
  };

  // Step verification logic
  const handleVerifyStep = () => {
    if (!currentInput.trim()) return;

    // Normalizing input
    const cleanInput = currentInput.replace(/\s+/g, '').replace(/\\cdot/g, '').toLowerCase();
    const cleanExpected = currentExercise.expectedLastStep.replace(/\s+/g, '').replace(/\\cdot/g, '').toLowerCase();

    const isMatch = cleanInput === cleanExpected || cleanInput.includes(cleanExpected.slice(0, 3));

    if (isOffline) {
      // US-9.5 Offline queue handling
      setVerdict('offline_queued');
      setTimeout(() => {
        advanceOrRest();
      }, 700);
      return;
    }

    if (isMatch) {
      // Step verified: quiet teal check, NO confetti/celebration noise
      setVerdict('correct');
      setErrorMessage('');
      setSocraticMessage(null);

      if (currentExercise.mode === 'review') {
        setReviewsDoneCount((c) => c + 1);
      } else {
        setFrontierAdvancedCount((c) => c + 1);
      }
      setCompletedItemsCount((c) => c + 1);

      // Advance after a calm 350ms pause
      setTimeout(() => {
        advanceOrRest();
      }, 400);
    } else {
      // Step incorrect: alert icon + calm copy; never shake whole screen
      setVerdict('incorrect');
      setErrorMessage(t('session.stepIncorrect'));
      setSocraticMessage(currentExercise.socraticPromptOnFail);
    }
  };

  // Micro-break trigger check: after submit when active practice time >= threshold (e.g. 5 mins / 300s)
  const advanceOrRest = () => {
    const timeSinceLastRest = activePracticeSeconds - lastRestAtSeconds;
    // Micro-break trigger threshold: every ~300s (5 minutes)
    if (timeSinceLastRest >= 300) {
      setLastRestAtSeconds(activePracticeSeconds);
      setShowRestOverlay(true);
      return;
    }

    proceedNextExercise();
  };

  const proceedNextExercise = () => {
    if (currentExerciseIdx + 1 < mockExercises.length) {
      setCurrentExerciseIdx(currentExerciseIdx + 1);
    } else {
      // Session finished!
      onFinishSession({
        durationSeconds: activePracticeSeconds,
        itemsCompleted: completedItemsCount + 1,
        reviewsDone: reviewsDoneCount + (currentExercise.mode === 'review' ? 1 : 0),
        frontierAdvanced: frontierAdvancedCount + (currentExercise.mode === 'new' ? 1 : 0),
        nodesUpdated: [currentExercise.nodeTitle]
      });
    }
  };

  return (
    <div className="w-full space-y-4">
      {/* Thin Top Bar: Exit (<-), Node title, Budget clock */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
        <button
          type="button"
          onClick={() => setShowExitConfirm(true)}
          className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 min-h-[40px] px-2 rounded-lg transition-colors"
          aria-label="Exit session"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Exit</span>
        </button>

        <div className="text-center px-2 truncate max-w-[200px] sm:max-w-xs">
          <span className="font-semibold text-slate-200 truncate block">
            {currentExercise.nodeTitle}
          </span>
        </div>

        {/* Budget clock: turns muted amber at < 5 min */}
        <div
          className={`flex items-center gap-1.5 font-mono px-2.5 py-1 rounded-md text-xs ${
            isBudgetLow
              ? 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
              : 'text-slate-400 bg-[#1E293B]'
          }`}
          title="Session budget remaining"
        >
          <Clock className="w-3.5 h-3.5" />
          <span>{budgetFormatted} left</span>
        </div>
      </div>

      {/* Mode Indicator: Review | New (subtle text, not tabs circus per spec) */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span className="font-mono uppercase tracking-wider text-[11px]">
          {currentExercise.mode === 'review' ? (
            <span className="text-amber-400">● {t('session.modeReview')}</span>
          ) : (
            <span className="text-indigo-400">● {t('session.modeNew')}</span>
          )}
        </span>

        {/* Request hint button if failed submit */}
        {verdict === 'incorrect' && (
          <button
            type="button"
            onClick={() => setHintDrawerOpen(true)}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>{t('session.hintButton')}</span>
          </button>
        )}
      </div>

      {/* GenUI Ordered Stack */}
      <div className="space-y-4">
        {/* Faded Worked Example */}
        <FadedWorkedExample
          statement={currentExercise.statement}
          scaffoldTier={currentExercise.scaffoldTier}
          steps={steps}
          activeStepIndex={activeStepIdx}
          currentInput={currentInput}
          onInputChange={handleInputChange}
          onSubmitStep={handleVerifyStep}
          verdict={verdict}
          errorMessage={errorMessage}
        />

        {/* Optional Function Plotter widget if item includes function exploration */}
        {currentExercise.hasPlotter && currentExercise.plotterParams && (
          <FunctionPlotter
            initialA={currentExercise.plotterParams.a}
            initialB={currentExercise.plotterParams.b}
            initialC={currentExercise.plotterParams.c}
            type={currentExercise.plotterParams.type}
          />
        )}

        {/* Socratic Dialogue Box if step failed */}
        {socraticMessage && verdict === 'incorrect' && (
          <SocraticDialogueBox prompt={socraticMessage} />
        )}

        {/* Offline Queued Status Banner */}
        {verdict === 'offline_queued' && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{t('session.offlineQueued')}</span>
          </div>
        )}
      </div>

      {/* Docked Virtual Math Keyboard */}
      <div className="pt-2">
        <VirtualMathKeyboard
          onInsert={handleInsertToken}
          onBackspace={handleBackspace}
          onClear={handleClear}
          onSubmit={handleVerifyStep}
        />
      </div>

      {/* Escalating Hint Drawer (opens only on failed submit) */}
      <HintDrawer
        isOpen={hintDrawerOpen}
        onClose={() => setHintDrawerOpen(false)}
        tier={hintTier}
        onEscalate={() => setHintTier((prev) => (prev < 3 ? ((prev + 1) as 1 | 2 | 3) : 3))}
        isAiPaused={isOffline}
        hintData={currentExercise.hintData}
      />

      {/* Micro-break RestOverlay Modal */}
      <RestOverlay
        isOpen={showRestOverlay}
        durationSeconds={30}
        onComplete={() => {
          setShowRestOverlay(false);
          proceedNextExercise();
        }}
        onSkipConfirmed={() => {
          setShowRestOverlay(false);
          proceedNextExercise();
        }}
      />

      {/* Focus Priming Modal */}
      {showPriming && (
        <FocusPrimingModal
          isOpen={showPriming}
          durationSeconds={120}
          onComplete={() => setShowPriming(false)}
          onSkip={() => setShowPriming(false)}
        />
      )}

      {/* Exit Confirmation Dialog */}
      {showExitConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        >
          <div className="w-full max-w-sm p-6 rounded-2xl bg-[#0F172A] border border-slate-700 shadow-2xl space-y-4">
            <h3 className="text-base font-semibold text-slate-100">
              {t('session.confirmExitTitle')}
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed font-sans">
              {t('session.confirmExitDesc')}
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowExitConfirm(false)}
                className="px-4 py-2 rounded-lg bg-[#1E293B] hover:bg-[#334155] text-slate-200 text-xs font-medium transition-colors"
              >
                {t('session.stayBtn')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowExitConfirm(false);
                  onExitSession();
                }}
                className="px-4 py-2 rounded-lg bg-red-600/80 hover:bg-red-600 text-white text-xs font-medium transition-colors"
              >
                {t('session.confirmExitBtn')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
