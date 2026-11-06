import React from 'react';
import { Lightbulb, ChevronRight, X, Sparkles, ShieldAlert } from 'lucide-react';
import { MathView } from '../common/MathView';

interface HintDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tier: 1 | 2 | 3;
  onEscalate: () => void;
  isAiPaused?: boolean;
  hintData: {
    tier1: string;
    tier2: string;
    tier3: string;
    tier3Latex?: string;
  };
}

export const HintDrawer: React.FC<HintDrawerProps> = ({
  isOpen,
  onClose,
  tier,
  onEscalate,
  isAiPaused = false,
  hintData
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="hint-drawer-title"
      className="fixed inset-x-0 bottom-0 z-40 p-4 sm:p-6 bg-[#0F172A] border-t border-slate-800 shadow-2xl rounded-t-2xl max-w-xl mx-auto transition-all duration-200 transform translate-y-0"
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Lightbulb className="w-4 h-4" />
          </div>
          <div>
            <h3 id="hint-drawer-title" className="text-sm font-semibold text-slate-100">
              Scaffold Hint · Level {tier} of 3
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              {tier === 1 ? 'Conceptual Direction' : tier === 2 ? 'Algebraic Structure' : 'Concrete Derivation'}
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-[#1E293B] transition-colors"
          aria-label="Close hints"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* AI Paused Banner if offline or LLM down */}
      {isAiPaused && (
        <div className="my-2.5 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>Smart hints paused · Operating with local rule engine</span>
        </div>
      )}

      {/* Hint content based on current tier */}
      <div className="py-4 space-y-3">
        <div className="p-3.5 rounded-xl bg-[#1E293B] border border-slate-700/60 text-slate-200 text-sm sm:text-base leading-relaxed">
          {tier === 1 && <p>{hintData.tier1}</p>}
          {tier === 2 && <p>{hintData.tier2}</p>}
          {tier === 3 && (
            <div className="space-y-2">
              <p>{hintData.tier3}</p>
              {hintData.tier3Latex && (
                <div className="p-2 rounded bg-[#090D16] border border-slate-800 text-center">
                  <MathView math={hintData.tier3Latex} display />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Escalation Control */}
      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-slate-400">
          {tier < 3 ? 'Need deeper guidance?' : 'Maximum scaffold reached'}
        </span>

        {tier < 3 ? (
          <button
            type="button"
            onClick={onEscalate}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#1E293B] hover:bg-[#334155] text-indigo-300 text-xs font-medium border border-indigo-500/30 transition-colors"
          >
            <span>Escalate to Tier {tier + 1}</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
          >
            Apply hint to step
          </button>
        )}
      </div>
    </div>
  );
};
