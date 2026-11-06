import React from 'react';
import { CheckCircle2, Clock, Award, ArrowRight, X } from 'lucide-react';
import { useTranslation } from '../i18n/context';
import { SessionStats } from '../types';

interface SessionSummaryScreenProps {
  stats: SessionStats;
  onContinueToRest: () => void;
  onSkipRest: () => void;
}

export const SessionSummaryScreen: React.FC<SessionSummaryScreenProps> = ({
  stats,
  onContinueToRest,
  onSkipRest
}) => {
  const { t } = useTranslation();

  const minutes = Math.floor(stats.durationSeconds / 60);
  const seconds = stats.durationSeconds % 60;
  const durationText = `${minutes}m ${seconds}s`;

  return (
    <div className="w-full space-y-6 animate-fade-in">
      {/* Calm Header (no confetti, no fake points) */}
      <div className="space-y-1 text-center pt-4">
        <span className="text-xs font-mono uppercase tracking-widest text-teal-400 font-medium">
          Deliberate Practice Complete
        </span>
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-100">
          {t('summary.title')}
        </h1>
        <p className="text-sm text-slate-400 font-sans max-w-sm mx-auto leading-relaxed">
          {t('summary.subtitle')}
        </p>
      </div>

      {/* Metrics Grid (Plain numbers) */}
      <div className="grid grid-cols-2 gap-3 p-2">
        <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-1">
          <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
            {t('summary.duration')}
          </div>
          <div className="text-2xl font-mono font-semibold text-slate-100">
            {durationText}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-1">
          <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
            {t('summary.itemsCompleted')}
          </div>
          <div className="text-2xl font-mono font-semibold text-teal-400">
            {stats.itemsCompleted}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-1">
          <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
            {t('summary.reviewsDone')}
          </div>
          <div className="text-2xl font-mono font-semibold text-indigo-300">
            {stats.reviewsDone}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-1">
          <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
            {t('summary.frontierAdvanced')}
          </div>
          <div className="text-2xl font-mono font-semibold text-slate-100">
            {stats.frontierAdvanced}
          </div>
        </div>
      </div>

      {/* Nodes whose due dates moved */}
      {stats.nodesUpdated.length > 0 && (
        <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-2">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
            {t('summary.nodesUpdated')}
          </span>
          <div className="space-y-1.5">
            {stats.nodesUpdated.map((nodeName, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-[#1E293B] border border-slate-700/60 text-xs text-slate-300 flex items-center justify-between"
              >
                <span>{nodeName}</span>
                <span className="font-mono text-[11px] text-teal-400">+3 days interval</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTA Group: Continue to rest (primary), Skip rest (secondary) */}
      <div className="space-y-2.5 pt-2">
        <button
          type="button"
          onClick={onContinueToRest}
          className="w-full h-14 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-colors"
        >
          <span>{t('summary.continueToRest')}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={onSkipRest}
          className="w-full h-11 rounded-xl bg-transparent hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 text-xs font-medium transition-colors"
        >
          {t('summary.skipRest')}
        </button>
      </div>
    </div>
  );
};
