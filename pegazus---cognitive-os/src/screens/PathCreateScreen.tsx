import React, { useState } from 'react';
import { ArrowRight, Upload, Calendar, Clock, AlertCircle } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface PathCreateScreenProps {
  isMinor: boolean;
  onCreatePath: (pathData: {
    subject: string;
    targetDate?: string;
    dailyBudgetMinutes: number;
    syllabusFileName?: string;
  }) => void;
  onCancel: () => void;
}

export const PathCreateScreen: React.FC<PathCreateScreenProps> = ({
  isMinor,
  onCreatePath,
  onCancel
}) => {
  const { t } = useTranslation();
  const [subject, setSubject] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [dailyBudget, setDailyBudget] = useState<number>(30);
  const [useDate, setUseDate] = useState<boolean>(true);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [errorGoal, setErrorGoal] = useState('');
  const [errorConstraint, setErrorConstraint] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let hasError = false;

    if (!subject.trim()) {
      setErrorGoal(t('path.errorGoal'));
      hasError = true;
    } else {
      setErrorGoal('');
    }

    if (!targetDate && (!dailyBudget || dailyBudget < 15)) {
      setErrorConstraint(t('path.errorConstraint'));
      hasError = true;
    } else {
      setErrorConstraint('');
    }

    if (hasError) return;

    onCreatePath({
      subject,
      targetDate: targetDate || undefined,
      dailyBudgetMinutes: dailyBudget,
      syllabusFileName: uploadedFile || undefined
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isMinor) return;
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        alert('File size exceeds 10 MB limit.');
        return;
      }
      setUploadedFile(file.name);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Title */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
          {t('path.newTitle')}
        </h1>
        <p className="text-sm text-slate-400 font-sans">
          {t('path.newSubtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-6 shadow-xl">
        {/* Goal / Subject input */}
        <div className="space-y-2">
          <label htmlFor="subject-input" className="block text-xs font-medium text-slate-300">
            {t('path.goalLabel')} <span className="text-[#F43F5E]">*</span>
          </label>
          <textarea
            id="subject-input"
            rows={3}
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value);
              if (errorGoal) setErrorGoal('');
            }}
            placeholder={t('path.goalPlaceholder')}
            className="w-full p-3.5 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 resize-none transition-colors"
          />
          {errorGoal && <p className="text-xs text-[#F43F5E]">{errorGoal}</p>}
        </div>

        {/* Constraint group: Target date OR Daily budget */}
        <div className="space-y-3 pt-1">
          <span className="block text-xs font-medium text-slate-300">
            {t('path.constraintLabel')} <span className="text-[#F43F5E]">*</span>
          </span>

          <div className="space-y-3">
            {/* Target date field */}
            <div className="p-3.5 rounded-xl bg-[#1E293B] border border-slate-700/60 space-y-2">
              <label htmlFor="target-date" className="flex items-center gap-2 text-xs text-slate-300">
                <Calendar className="w-4 h-4 text-indigo-400" />
                <span>{t('path.targetDateLabel')}</span>
              </label>
              <input
                id="target-date"
                type="date"
                value={targetDate}
                onChange={(e) => {
                  setTargetDate(e.target.value);
                  if (errorConstraint) setErrorConstraint('');
                }}
                className="w-full px-3 py-2 bg-[#0F172A] border border-slate-700 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {/* Daily study budget stepper */}
            <div className="p-3.5 rounded-xl bg-[#1E293B] border border-slate-700/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" />
                  <span>{t('path.dailyBudgetLabel')}</span>
                </span>
                <span className="font-mono text-sm text-indigo-300 font-semibold">
                  {dailyBudget} {t('path.minutesUnit')}
                </span>
              </div>
              <input
                type="range"
                min="15"
                max="120"
                step="5"
                value={dailyBudget}
                onChange={(e) => {
                  setDailyBudget(parseInt(e.target.value, 10));
                  if (errorConstraint) setErrorConstraint('');
                }}
                className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>
          </div>
          {errorConstraint && (
            <p className="text-xs text-[#F43F5E] flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errorConstraint}</span>
            </p>
          )}
        </div>

        {/* Syllabus upload (quiet secondary control, disabled for minors) */}
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <label className="block text-xs font-medium text-slate-300">
            {t('path.uploadLabel')}
          </label>
          <div className="text-[11px] text-slate-500">
            {t('path.uploadHelp')}
          </div>

          <div className="flex items-center gap-3 pt-1">
            <label
              className={`min-h-[48px] px-4 py-2.5 rounded-xl border border-dashed flex items-center gap-2 text-xs font-medium cursor-pointer transition-colors ${
                isMinor
                  ? 'border-slate-800 text-slate-600 cursor-not-allowed opacity-50'
                  : 'border-slate-700 hover:border-indigo-500/50 bg-[#1E293B] text-slate-300 hover:text-slate-100'
              }`}
            >
              <Upload className="w-4 h-4 text-slate-400" />
              <span>{uploadedFile || t('path.uploadButton')}</span>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                disabled={isMinor}
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
            {uploadedFile && (
              <button
                type="button"
                onClick={() => setUploadedFile(null)}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={onCancel}
            className="min-h-[48px] px-5 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="min-h-[48px] px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 transition-colors"
          >
            <span>{t('path.createCta')}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
