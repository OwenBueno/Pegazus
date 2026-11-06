import React from 'react';
import { Delete, CornerDownLeft, RotateCcw } from 'lucide-react';

interface VirtualMathKeyboardProps {
  onInsert: (token: string) => void;
  onBackspace: () => void;
  onClear: () => void;
  onSubmit: () => void;
  className?: string;
}

export const VirtualMathKeyboard: React.FC<VirtualMathKeyboardProps> = ({
  onInsert,
  onBackspace,
  onClear,
  onSubmit,
  className = ''
}) => {
  const handleKeyClick = (token: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(10);
      }
    } catch {
      // ignore haptic failures per spec
    }
    onInsert(token);
  };

  const keyBase =
    'flex items-center justify-center min-w-[42px] sm:min-w-[48px] h-12 rounded-lg font-mono text-sm sm:text-base font-medium transition-colors select-none active:scale-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/50';
  const opKey = `${keyBase} bg-[#1E293B] text-slate-200 hover:bg-[#334155] border border-slate-700/60`;
  const numKey = `${keyBase} bg-[#0F172A] text-slate-100 hover:bg-[#1E293B] border border-slate-800`;
  const actionKey = `${keyBase} bg-[#1E293B] text-slate-300 hover:bg-[#334155] border border-slate-700/80`;
  const submitKey = `${keyBase} bg-[#6366F1] text-white hover:bg-[#4F46E5] font-semibold col-span-2 shadow-sm`;

  return (
    <div
      className={`w-full max-w-xl mx-auto bg-[#0F172A] border-t border-slate-800 p-2 sm:p-3 select-none ${className}`}
      role="group"
      aria-label="Math input keyboard"
    >
      {/* Function and algebra toolbar */}
      <div className="grid grid-cols-7 gap-1 sm:gap-1.5 mb-1.5">
        <button type="button" onClick={() => handleKeyClick('x')} className={opKey} aria-label="variable x">x</button>
        <button type="button" onClick={() => handleKeyClick('y')} className={opKey} aria-label="variable y">y</button>
        <button type="button" onClick={() => handleKeyClick('^2')} className={opKey} aria-label="squared">x²</button>
        <button type="button" onClick={() => handleKeyClick('^')} className={opKey} aria-label="power">xⁿ</button>
        <button type="button" onClick={() => handleKeyClick('\\sqrt{')} className={opKey} aria-label="square root">√x</button>
        <button type="button" onClick={() => handleKeyClick('\\frac{')} className={opKey} aria-label="fraction">a/b</button>
        <button type="button" onClick={() => handleKeyClick('\\pi')} className={opKey} aria-label="pi">π</button>
      </div>

      <div className="grid grid-cols-7 gap-1 sm:gap-1.5 mb-1.5">
        <button type="button" onClick={() => handleKeyClick('\\sin(')} className={opKey} aria-label="sine">sin</button>
        <button type="button" onClick={() => handleKeyClick('\\cos(')} className={opKey} aria-label="cosine">cos</button>
        <button type="button" onClick={() => handleKeyClick('\\tan(')} className={opKey} aria-label="tangent">tan</button>
        <button type="button" onClick={() => handleKeyClick('\\ln(')} className={opKey} aria-label="natural log">ln</button>
        <button type="button" onClick={() => handleKeyClick('(')} className={opKey} aria-label="open parenthesis">(</button>
        <button type="button" onClick={() => handleKeyClick(')')} className={opKey} aria-label="close parenthesis">)</button>
        <button type="button" onClick={() => handleKeyClick('\\theta')} className={opKey} aria-label="theta">θ</button>
      </div>

      {/* Main numpad & operators */}
      <div className="grid grid-cols-6 gap-1 sm:gap-1.5">
        <button type="button" onClick={() => handleKeyClick('7')} className={numKey}>7</button>
        <button type="button" onClick={() => handleKeyClick('8')} className={numKey}>8</button>
        <button type="button" onClick={() => handleKeyClick('9')} className={numKey}>9</button>
        <button type="button" onClick={() => handleKeyClick('+')} className={opKey} aria-label="plus">+</button>
        <button type="button" onClick={() => handleKeyClick('-')} className={opKey} aria-label="minus">−</button>
        <button type="button" onClick={onClear} className={actionKey} aria-label="Clear all">
          <RotateCcw className="w-4 h-4" />
        </button>

        <button type="button" onClick={() => handleKeyClick('4')} className={numKey}>4</button>
        <button type="button" onClick={() => handleKeyClick('5')} className={numKey}>5</button>
        <button type="button" onClick={() => handleKeyClick('6')} className={numKey}>6</button>
        <button type="button" onClick={() => handleKeyClick('\\cdot ')} className={opKey} aria-label="multiply">×</button>
        <button type="button" onClick={() => handleKeyClick('/')} className={opKey} aria-label="divide">÷</button>
        <button type="button" onClick={onBackspace} className={actionKey} aria-label="Backspace">
          <Delete className="w-4 h-4" />
        </button>

        <button type="button" onClick={() => handleKeyClick('1')} className={numKey}>1</button>
        <button type="button" onClick={() => handleKeyClick('2')} className={numKey}>2</button>
        <button type="button" onClick={() => handleKeyClick('3')} className={numKey}>3</button>
        <button type="button" onClick={() => handleKeyClick('0')} className={numKey}>0</button>
        <button type="button" onClick={() => handleKeyClick('.')} className={numKey}>.</button>
        <button type="button" onClick={() => handleKeyClick('=')} className={opKey} aria-label="equals">=</button>
      </div>

      <div className="mt-1.5">
        <button
          type="button"
          onClick={onSubmit}
          className={`${submitKey} w-full h-12 flex items-center justify-center gap-2`}
          aria-label="Verify derivation step"
        >
          <span>Verify Step</span>
          <CornerDownLeft className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
