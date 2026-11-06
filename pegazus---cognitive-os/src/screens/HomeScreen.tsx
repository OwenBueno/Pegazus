import React from 'react';
import { ArrowRight, Play, PlusCircle, HelpCircle, CheckCircle2, Clock } from 'lucide-react';
import { LearningPath } from '../types';
import { useTranslation } from '../i18n/context';
import { MathView } from '../components/common/MathView';

interface HomeScreenProps {
  activePath: LearningPath | null;
  dueReviewsCount: number;
  budgetMinutesRemaining: number;
  onStartSession: () => void;
  onCreatePath: () => void;
  onAskQuick: () => void;
  onViewPath: () => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  activePath,
  dueReviewsCount,
  budgetMinutesRemaining,
  onStartSession,
  onCreatePath,
  onAskQuick,
  onViewPath
}) => {
  const { t } = useTranslation();

  // Find next frontier node
  const nextFrontierNode = activePath?.nodes.find((n) => n.status === 'frontier');
  const masteredCount = activePath?.nodes.filter((n) => n.status === 'mastered').length || 0;
  const totalNodes = activePath?.nodes.length || 1;
  const progressPercent = Math.round((masteredCount / totalNodes) * 100);

  return (
    <div className="w-full space-y-8 animate-fade-in">
      {/* First viewport (Hero Budget): Brand + 1 Headline + 1 Supporting Sentence + 1 CTA Group */}
      <section className="space-y-4 pt-2">
        <div className="space-y-1.5">
          <span className="text-xs font-mono uppercase tracking-widest text-indigo-400 font-medium">
            Pegazus
          </span>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-100">
            {t('home.greeting')}
          </h1>
          <p className="text-sm sm:text-base text-slate-400 leading-relaxed font-sans">
            {activePath
              ? dueReviewsCount > 0
                ? t('home.subtitleDue', { count: dueReviewsCount, minutes: budgetMinutesRemaining })
                : t('home.subtitleCatchup')
              : t('home.subtitleEmpty')}
          </p>
        </div>

        {/* Hero CTA Group */}
        <div className="pt-2">
          {activePath ? (
            <button
              type="button"
              onClick={onStartSession}
              className="w-full h-14 rounded-2xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-base flex items-center justify-between px-6 shadow-lg shadow-indigo-600/20 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <div className="flex items-center gap-3">
                <Play className="w-5 h-5 fill-current" />
                <span>{t('home.ctaStart')}</span>
              </div>
              <ArrowRight className="w-5 h-5 text-indigo-200" />
            </button>
          ) : (
            <div className="space-y-3">
              <button
                type="button"
                onClick={onCreatePath}
                className="w-full h-14 rounded-2xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-base flex items-center justify-between px-6 shadow-lg shadow-indigo-600/20 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <div className="flex items-center gap-3">
                  <PlusCircle className="w-5 h-5" />
                  <span>{t('home.ctaCreatePath')}</span>
                </div>
                <ArrowRight className="w-5 h-5 text-indigo-200" />
              </button>

              <button
                type="button"
                onClick={onAskQuick}
                className="w-full h-12 rounded-xl bg-[#0F172A] hover:bg-[#1E293B] border border-slate-800 text-slate-300 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <HelpCircle className="w-4 h-4 text-indigo-400" />
                <span>{t('home.ctaAskQuick')}</span>
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Below fold: Active path summary & frontier details */}
      {activePath ? (
        <section className="space-y-4 pt-4 border-t border-slate-800/80">
          {/* Active Path & Progress Bar */}
          <div
            onClick={onViewPath}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onViewPath()}
            className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer space-y-3 group"
          >
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                  {t('home.progressLabel')}
                </span>
                <h3 className="text-base font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                  {activePath.title}
                </h3>
              </div>
              <div className="text-right">
                <span className="text-sm font-mono font-semibold text-indigo-400">
                  {progressPercent}%
                </span>
              </div>
            </div>

            {/* Simple progress bar */}
            <div className="w-full h-2 bg-[#1E293B] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-teal-400 rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {activePath.targetDate && (
              <div className="text-xs text-slate-400 flex items-center gap-1.5 pt-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>{t('home.targetDeadline', { date: activePath.targetDate })}</span>
              </div>
            )}
          </div>

          {/* Next Frontier Node with KaTeX */}
          {nextFrontierNode && (
            <div className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-indigo-400">
                  {t('home.frontierNext')}
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  ~{nextFrontierNode.estimatedMinutes} min
                </span>
              </div>

              <div className="text-base sm:text-lg font-medium text-slate-100">
                {nextFrontierNode.mathTitle ? (
                  <MathView math={nextFrontierNode.mathTitle} />
                ) : (
                  nextFrontierNode.title
                )}
              </div>

              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                {nextFrontierNode.description}
              </p>
            </div>
          )}

          {/* Last session one-liner */}
          <div className="text-xs text-slate-500 font-mono py-1 px-2 text-center">
            {t('home.yesterdaySummary', { minutes: 32, nodes: 4 })}
          </div>
        </section>
      ) : (
        <section className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 text-center space-y-2">
          <p className="text-sm text-slate-400">
            {t('home.noPathDesc')}
          </p>
        </section>
      )}
    </div>
  );
};
