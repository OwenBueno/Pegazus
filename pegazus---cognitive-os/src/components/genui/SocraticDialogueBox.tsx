import React from 'react';
import { HelpCircle } from 'lucide-react';

interface SocraticDialogueBoxProps {
  prompt: string;
  highlightId?: string;
  className?: string;
}

export const SocraticDialogueBox: React.FC<SocraticDialogueBoxProps> = ({
  prompt,
  highlightId,
  className = ''
}) => {
  // Truncate to maximum 240 chars per spec
  const formattedPrompt = prompt.length > 240 ? `${prompt.slice(0, 237)}...` : prompt;

  return (
    <div
      role="region"
      aria-live="polite"
      className={`p-3.5 sm:p-4 rounded-xl bg-[#1E293B]/80 border border-indigo-500/30 text-slate-200 flex items-start gap-3 shadow-sm ${className}`}
      data-highlight-target={highlightId}
    >
      <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0 mt-0.5">
        <HelpCircle className="w-4 h-4" />
      </div>

      <div className="space-y-1 text-sm sm:text-base leading-relaxed">
        <div className="text-[11px] font-mono uppercase tracking-wider text-indigo-300/80">
          Socratic Prompt
        </div>
        <p className="text-slate-200 font-sans">{formattedPrompt}</p>
      </div>
    </div>
  );
};
