import React, { useState } from 'react';
import {
  Compass,
  Lock,
  Play,
  CheckCircle2,
  Clock,
  Sparkles,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
  ExternalLink,
  BookOpen
} from 'lucide-react';
import { LearningPath, PathNode } from '../types';
import { useTranslation } from '../i18n/context';
import { MathView } from '../components/common/MathView';

interface PathViewScreenProps {
  path: LearningPath | null;
  onStartPractice: () => void;
  onStartDiagnostic: () => void;
  onCreateNewPath: () => void;
}

export const PathViewScreen: React.FC<PathViewScreenProps> = ({
  path,
  onStartPractice,
  onStartDiagnostic,
  onCreateNewPath
}) => {
  const { t } = useTranslation();
  const [selectedNode, setSelectedNode] = useState<PathNode | null>(null);
  const [showAttributions, setShowAttributions] = useState<boolean>(false);

  if (!path) {
    return (
      <div className="w-full py-16 text-center space-y-4">
        <Compass className="w-12 h-12 text-slate-600 mx-auto" />
        <h2 className="text-xl font-semibold text-slate-100">{t('path.emptyPath')}</h2>
        <button
          onClick={onCreateNewPath}
          className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
        >
          {t('home.ctaCreatePath')}
        </button>
      </div>
    );
  }

  const hoursTotal = (path.criticalPathMinutes / 60).toFixed(1);

  const getStatusBadge = (status: PathNode['status']) => {
    switch (status) {
      case 'mastered':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-[#14B8A6]/10 text-[#14B8A6] border border-[#14B8A6]/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>{t('path.statusMastered')}</span>
          </span>
        );
      case 'frontier':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
            <Play className="w-3 h-3 fill-current" />
            <span>{t('path.statusFrontier')}</span>
          </span>
        );
      case 'due_review':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <Clock className="w-3 h-3" />
            <span>{t('path.statusDue')}</span>
          </span>
        );
      case 'drafting':
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            <Sparkles className="w-3 h-3" />
            <span>{t('path.statusDrafting')}</span>
          </span>
        );
      case 'locked':
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-500 border border-slate-800">
            <Lock className="w-3 h-3" />
            <span>{t('path.statusLocked')}</span>
          </span>
        );
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Header Region */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
            {t('path.viewTitle')}
          </span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            {path.status}
          </span>
        </div>

        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
          {path.title}
        </h1>
        <p className="text-sm text-slate-400 font-sans">
          {path.subject}
        </p>
      </div>

      {/* Refining Banner (Phase 2 simulated) */}
      {path.status === 'REFINING' && (
        <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center gap-3 text-xs text-indigo-200">
          <div className="w-4 h-4 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin shrink-0" />
          <span>{t('path.refiningBanner')}</span>
        </div>
      )}

      {/* Fit-to-deadline warning if plan no longer fits */}
      {path.fitWarning?.isOverloaded && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-1.5 text-xs text-amber-200">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>{t('path.fitWarning', { required: path.fitWarning.requiredDailyMinutes })}</span>
          </div>
          <p className="text-slate-300 pl-6">
            {t('path.fitSuggestion')}
          </p>
        </div>
      )}

      {/* Critical Path Metric and Primary CTA */}
      <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-mono text-slate-400">
            {t('path.criticalPath', { hours: hoursTotal })}
          </span>
          <div className="text-xs text-slate-500 mt-0.5">
            {path.dailyBudgetMinutes} min/day target budget
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onStartDiagnostic}
            className="px-3.5 py-2.5 rounded-xl bg-[#1E293B] hover:bg-[#334155] border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            {t('path.startDiagnostic')}
          </button>
          <button
            type="button"
            onClick={onStartPractice}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-colors shadow-sm"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{t('path.startPractice')}</span>
          </button>
        </div>
      </div>

      {/* DAG Graph Canvas (Vertical timeline DAG) */}
      <section className="space-y-2" aria-label="Learning dependency graph">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2">
          Knowledge Dependency Nodes (DAG)
        </div>

        <div className="relative pl-6 space-y-3 before:content-[''] before:absolute before:left-2.5 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-800">
          {path.nodes.map((node, index) => {
            const isFrontier = node.status === 'frontier';
            const isMastered = node.status === 'mastered';
            const isDue = node.status === 'due_review';

            return (
              <div
                key={node.id}
                onClick={() => setSelectedNode(node)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedNode(node)}
                className={`relative p-4 rounded-xl border transition-all cursor-pointer select-none ${
                  isFrontier
                    ? 'bg-[#0F172A] border-indigo-500/60 ring-2 ring-indigo-500/20 shadow-md'
                    : isDue
                    ? 'bg-[#0F172A] border-amber-500/40'
                    : isMastered
                    ? 'bg-[#0F172A] border-slate-800 hover:border-slate-700'
                    : 'bg-[#090D16]/70 border-slate-800/60 opacity-60'
                }`}
              >
                {/* Node timeline node circle */}
                <div
                  className={`absolute -left-[27px] top-5 w-4 h-4 rounded-full border-2 ${
                    isFrontier
                      ? 'bg-indigo-600 border-[#090D16] ring-2 ring-indigo-500/40'
                      : isDue
                      ? 'bg-amber-500 border-[#090D16]'
                      : isMastered
                      ? 'bg-[#14B8A6] border-[#090D16]'
                      : 'bg-slate-700 border-[#090D16]'
                  }`}
                />

                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-500">#{index + 1}</span>
                    <h3 className="text-sm sm:text-base font-semibold text-slate-100">
                      {node.mathTitle ? (
                        <MathView math={node.mathTitle} />
                      ) : (
                        node.title
                      )}
                    </h3>
                  </div>
                  {getStatusBadge(node.status)}
                </div>

                <p className="text-xs text-slate-400 font-sans line-clamp-2 mb-2">
                  {node.description}
                </p>

                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-800/60">
                  <span>~{node.estimatedMinutes} min practice</span>
                  <span>Mastery: {node.masteryPercent}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Bottom Sheet Node Detail Modal */}
      {selectedNode && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
        >
          <div className="w-full max-w-lg bg-[#0F172A] border border-slate-700 rounded-t-2xl sm:rounded-2xl p-6 space-y-4 shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                <h3 className="text-base font-semibold text-slate-100">
                  {t('path.nodeDetails')}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200"
                aria-label="Close details"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="text-lg font-semibold text-slate-100">
                {selectedNode.mathTitle ? (
                  <MathView math={selectedNode.mathTitle} />
                ) : (
                  selectedNode.title
                )}
              </div>

              <p className="text-sm text-slate-300 leading-relaxed font-sans">
                {selectedNode.description}
              </p>

              <div className="grid grid-cols-3 gap-2 py-2 text-center font-mono">
                <div className="p-2.5 rounded-xl bg-[#1E293B] border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase">{t('path.masteryLabel')}</div>
                  <div className="text-sm font-semibold text-teal-400">{selectedNode.masteryPercent}%</div>
                </div>
                <div className="p-2.5 rounded-xl bg-[#1E293B] border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase">{t('path.estMinutesLabel')}</div>
                  <div className="text-sm font-semibold text-slate-200">{selectedNode.estimatedMinutes}m</div>
                </div>
                <div className="p-2.5 rounded-xl bg-[#1E293B] border border-slate-800">
                  <div className="text-[10px] text-slate-400 uppercase">{t('path.dueDateLabel')}</div>
                  <div className="text-sm font-semibold text-indigo-300">{selectedNode.dueDate || 'Today'}</div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#1E293B]/70 border border-slate-800 text-xs text-slate-400 space-y-1">
                <span className="font-mono text-[10px] uppercase text-slate-500 block">
                  {t('path.attributionLabel')}
                </span>
                <p className="text-slate-300">{selectedNode.sourceAttribution}</p>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => {
                  setSelectedNode(null);
                  onStartPractice();
                }}
                className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Practice this node</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Attribution Footer (Collapsible) */}
      <div className="border-t border-slate-800/80 pt-4">
        <button
          type="button"
          onClick={() => setShowAttributions(!showAttributions)}
          className="w-full flex items-center justify-between text-xs text-slate-500 hover:text-slate-400 py-1"
        >
          <span>{t('path.collapseAttributions')}</span>
          {showAttributions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showAttributions && (
          <div className="mt-3 p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-2 text-xs text-slate-400">
            <p>
              Mathematical derivations and dependency DAG grounded on OpenStax Calculus, MIT OpenCourseWare 18.01, and Creative Commons CC-BY-SA academic corpora.
            </p>
            <p className="font-mono text-[11px] text-slate-500">
              License compliance verified per Project Pegazus Cognitive Engine specifications.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
