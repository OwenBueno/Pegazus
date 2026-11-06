import React, { useState } from 'react';
import { HelpCircle, Send, ArrowRight, ShieldCheck, AlertCircle, RotateCcw } from 'lucide-react';
import { useTranslation } from '../i18n/context';
import { MathView } from '../components/common/MathView';
import { SocraticDialogueBox } from '../components/genui/SocraticDialogueBox';
import { SocraticExchange } from '../types';

interface SocraticScreenProps {
  onReturnHome: () => void;
}

export const SocraticScreen: React.FC<SocraticScreenProps> = ({ onReturnHome }) => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [useLatexMode, setUseLatexMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [exchanges, setExchanges] = useState<SocraticExchange[]>([]);
  const [followUpInput, setFollowUpInput] = useState('');
  const [isOffTopic, setIsOffTopic] = useState(false);

  // Maximum 3 follow-up exchanges allowed per spec
  const maxExchanges = 3;
  const remainingExchanges = maxExchanges - exchanges.filter((e) => e.role === 'learner').length;

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Check for off-topic non-academic queries
    const lower = query.toLowerCase();
    if (lower.includes('weather') || lower.includes('recipe') || lower.includes('joke') || lower.includes('movie')) {
      setIsOffTopic(true);
      return;
    }

    setIsOffTopic(false);
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      setExchanges([
        { role: 'learner', text: query },
        {
          role: 'socratic',
          text: 'Consider the rate of change behavior: What happens to the denominator as x approaches the boundary point? Can factoring reveal common terms before taking the limit?'
        }
      ]);
    }, 500);
  };

  const handleSendFollowUp = (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUpInput.trim() || remainingExchanges <= 0) return;

    const currentText = followUpInput;
    setFollowUpInput('');

    setExchanges((prev) => [
      ...prev,
      { role: 'learner', text: currentText },
      {
        role: 'socratic',
        text: 'Notice that canceling (x - 2) removes the removable singularity at x = 2. You are then left with a continuous polynomial line.'
      }
    ]);
  };

  const handleReset = () => {
    setQuery('');
    setExchanges([]);
    setIsOffTopic(false);
  };

  return (
    <div className="w-full space-y-6">
      {/* Title */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-indigo-400" />
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            {t('socratic.title')}
          </h1>
        </div>
        <p className="text-sm text-slate-400 font-sans">
          {t('socratic.subtitle')}
        </p>
      </div>

      {/* Banner: "This won't change your learning path." */}
      <div className="p-3 rounded-xl bg-[#1E293B] border border-slate-700/60 text-xs text-slate-400 flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
        <span>{t('socratic.bannerNoChange')}</span>
      </div>

      {/* Query Input Section (if no exchanges yet) */}
      {exchanges.length === 0 ? (
        <form onSubmit={handleAsk} className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <label htmlFor="socratic-query" className="text-xs font-medium text-slate-300">
              Inquiry / Mathematical question
            </label>
            <button
              type="button"
              onClick={() => setUseLatexMode(!useLatexMode)}
              className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
                useLatexMode
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200 bg-[#1E293B]'
              }`}
            >
              LaTeX Mode
            </button>
          </div>

          <textarea
            id="socratic-query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              useLatexMode
                ? 'e.g. \\lim_{x \\to 0} \\frac{\\sin(x)}{x}'
                : t('socratic.inputPlaceholder')
            }
            className="w-full p-3.5 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 resize-none transition-colors"
          />

          {/* Real-time Math Preview if in LaTeX mode */}
          {useLatexMode && query.trim() && (
            <div className="p-2.5 rounded-lg bg-[#090D16] border border-slate-800 text-center">
              <MathView math={query} display />
            </div>
          )}

          {/* Off-Topic Polite Refusal */}
          {isOffTopic && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-1">
              <div className="flex items-center gap-1.5 font-semibold">
                <AlertCircle className="w-4 h-4 text-amber-400" />
                <span>{t('socratic.offTopicTitle')}</span>
              </div>
              <p>{t('socratic.offTopicDesc')}</p>
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <div className="text-xs text-slate-500 hidden sm:block">
              Max 3 exchanges per inquiry
            </div>
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="min-h-[48px] px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold flex items-center gap-2 transition-colors ml-auto"
            >
              <span>{t('socratic.askCta')}</span>
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      ) : (
        /* Conversation Canvas (GenUI ordered payload) */
        <div className="space-y-4">
          <div className="space-y-3">
            {exchanges.map((ex, idx) => (
              <div key={idx}>
                {ex.role === 'learner' ? (
                  <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800 text-slate-100 text-sm font-mono flex items-start gap-2">
                    <span className="text-xs text-indigo-400 uppercase font-sans font-semibold">Learner:</span>
                    <div>
                      {ex.text.includes('\\') ? <MathView math={ex.text} /> : ex.text}
                    </div>
                  </div>
                ) : (
                  <SocraticDialogueBox prompt={ex.text} />
                )}
              </div>
            ))}
          </div>

          {/* Follow-up composer (if exchanges remaining) */}
          {remainingExchanges > 0 ? (
            <form onSubmit={handleSendFollowUp} className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{t('socratic.exchangesLeft', { count: remainingExchanges })}</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={followUpInput}
                  onChange={(e) => setFollowUpInput(e.target.value)}
                  placeholder={t('socratic.followUpPlaceholder')}
                  className="flex-1 px-3.5 py-2.5 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="submit"
                  disabled={!followUpInput.trim()}
                  className="min-h-[44px] px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <span>{t('socratic.followUpCta')}</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          ) : (
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-center text-xs text-slate-400">
              Exchange limit reached. Pegazus Socratic dialogues are bounded to prevent cognitive overload.
            </div>
          )}

          {/* Controls: Reset or Return Home */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 py-2 px-3 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Ask another inquiry</span>
            </button>

            <button
              type="button"
              onClick={onReturnHome}
              className="px-5 py-2.5 rounded-xl bg-[#1E293B] hover:bg-[#334155] border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
            >
              {t('socratic.doneCta')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
