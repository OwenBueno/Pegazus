import React, { useRef, useEffect } from 'react';
import { Check, AlertCircle } from 'lucide-react';
import { StepItem } from '../../types';
import { MathView } from '../common/MathView';

interface SymbolicStepEditorProps {
  steps: StepItem[];
  activeStepIndex: number;
  currentInput: string;
  onInputChange: (val: string) => void;
  onSubmitStep: () => void;
  verdict?: 'correct' | 'incorrect' | 'offline_queued' | null;
  errorMessage?: string;
  disabled?: boolean;
}

export const SymbolicStepEditor: React.FC<SymbolicStepEditorProps> = ({
  steps,
  activeStepIndex,
  currentInput,
  onInputChange,
  onSubmitStep,
  verdict,
  errorMessage,
  disabled = false
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the active step input on mount or step change
    if (!disabled) {
      inputRef.current?.focus();
    }
  }, [activeStepIndex, disabled]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmitStep();
    }
  };

  return (
    <div className="w-full space-y-3" role="region" aria-label="Derivation steps">
      <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">
        Symbolic Derivation
      </div>

      <div className="space-y-2.5">
        {steps.map((step, idx) => {
          const isCurrent = idx === activeStepIndex;
          const isCompleted = idx < activeStepIndex;

          if (isCompleted) {
            return (
              <div
                key={step.id || idx}
                className="flex items-center justify-between p-3.5 rounded-xl bg-[#0F172A] border border-slate-800 transition-opacity duration-150"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-slate-500 w-5">{idx + 1}.</span>
                  <div className="text-lg text-slate-100 font-mono">
                    <MathView math={step.latex} />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {step.justification && (
                    <span className="text-xs text-slate-400 font-sans hidden sm:inline">
                      {step.justification}
                    </span>
                  )}
                  <span
                    className="flex items-center justify-center w-6 h-6 rounded-full bg-[#14B8A6]/10 text-[#14B8A6] border border-[#14B8A6]/30"
                    aria-label="Correct step"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          }

          if (isCurrent) {
            return (
              <div
                key={step.id || idx}
                className={`p-3.5 rounded-xl bg-[#0F172A] border transition-all duration-150 ${
                  verdict === 'incorrect'
                    ? 'border-[#F43F5E] shadow-[0_0_12px_rgba(244,63,94,0.15)]'
                    : verdict === 'correct'
                    ? 'border-[#14B8A6] shadow-[0_0_12px_rgba(20,184,166,0.15)]'
                    : 'border-indigo-500/60 ring-2 ring-indigo-500/20'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-xs text-indigo-400 font-semibold w-5">
                    {idx + 1}.
                  </span>
                  <span className="text-xs text-slate-400">Active Derivation Step</span>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    ref={inputRef}
                    type="text"
                    value={currentInput}
                    onChange={(e) => onInputChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    placeholder="e.g. 2x + 4 = 10"
                    aria-label={`Step ${idx + 1} mathematical expression`}
                    className="w-full bg-[#1E293B] border border-slate-700/80 rounded-lg px-3.5 py-2.5 font-mono text-base text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 transition-colors"
                  />
                  {verdict === 'correct' && (
                    <span
                      className="flex items-center justify-center w-8 h-8 rounded-full bg-[#14B8A6]/10 text-[#14B8A6] border border-[#14B8A6]/30 shrink-0"
                      aria-label="Verified step"
                    >
                      <Check className="w-4 h-4" />
                    </span>
                  )}
                  {verdict === 'incorrect' && (
                    <span
                      className="flex items-center justify-center w-8 h-8 rounded-full bg-[#F43F5E]/10 text-[#F43F5E] border border-[#F43F5E]/30 shrink-0"
                      aria-label="Incorrect step"
                    >
                      <AlertCircle className="w-4 h-4" />
                    </span>
                  )}
                </div>

                {/* Real-time Math Preview */}
                {currentInput.trim() && (
                  <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[11px] font-mono text-slate-500">Preview:</span>
                    <div className="text-base text-slate-200">
                      <MathView math={currentInput} />
                    </div>
                  </div>
                )}

                {/* Calm error message on incorrect submission */}
                {verdict === 'incorrect' && errorMessage && (
                  <div className="mt-2 text-xs text-[#F43F5E] flex items-center gap-1.5" role="alert">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}
              </div>
            );
          }

          // Future / locked step
          return (
            <div
              key={step.id || idx}
              className="flex items-center gap-3 p-3 rounded-xl bg-[#090D16]/50 border border-slate-800/50 opacity-40"
            >
              <span className="font-mono text-xs text-slate-600 w-5">{idx + 1}.</span>
              <span className="text-sm text-slate-600 font-mono italic">Subsequent step</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
