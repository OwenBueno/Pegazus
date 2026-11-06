import React from 'react';
import { MathView } from '../common/MathView';
import { SymbolicStepEditor } from './SymbolicStepEditor';
import { StepItem } from '../../types';

interface FadedWorkedExampleProps {
  statement: string;
  scaffoldTier: 1 | 2 | 3;
  steps: StepItem[];
  activeStepIndex: number;
  currentInput: string;
  onInputChange: (val: string) => void;
  onSubmitStep: () => void;
  verdict?: 'correct' | 'incorrect' | 'offline_queued' | null;
  errorMessage?: string;
}

export const FadedWorkedExample: React.FC<FadedWorkedExampleProps> = ({
  statement,
  scaffoldTier,
  steps,
  activeStepIndex,
  currentInput,
  onInputChange,
  onSubmitStep,
  verdict,
  errorMessage
}) => {
  return (
    <div className="w-full space-y-4">
      {/* Problem Statement Card */}
      <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
            Problem Statement
          </span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            Tier {scaffoldTier}: {scaffoldTier === 1 ? 'Guided Gap' : scaffoldTier === 2 ? 'Partial Scaffold' : 'Independent Derivation'}
          </span>
        </div>

        <div className="text-lg sm:text-xl text-slate-100 font-sans leading-relaxed">
          <MathView math={statement} display={false} />
        </div>
      </div>

      {/* Steps according to scaffold tier */}
      <SymbolicStepEditor
        steps={steps}
        activeStepIndex={activeStepIndex}
        currentInput={currentInput}
        onInputChange={onInputChange}
        onSubmitStep={onSubmitStep}
        verdict={verdict}
        errorMessage={errorMessage}
      />
    </div>
  );
};
