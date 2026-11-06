import React, { useState, useEffect } from 'react';
import { Target, X } from 'lucide-react';
import { useTranslation } from '../../i18n/context';

interface FocusPrimingModalProps {
  isOpen: boolean;
  onComplete: () => void;
  onSkip: () => void;
  durationSeconds?: number;
}

export const FocusPrimingModal: React.FC<FocusPrimingModalProps> = ({
  isOpen,
  onComplete,
  onSkip,
  durationSeconds = 120
}) => {
  const { t } = useTranslation();
  const [remaining, setRemaining] = useState<number>(durationSeconds);

  useEffect(() => {
    if (!isOpen) {
      setRemaining(durationSeconds);
      return;
    }

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onComplete();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, durationSeconds, onComplete]);

  if (!isOpen) return null;

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const timeFormatted = `${minutes}:${seconds.toString().padStart(2, '0')}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Focus priming"
      className="fixed inset-0 z-50 flex flex-col items-center justify-between p-6 sm:p-10 bg-[#090D16] text-slate-100"
    >
      <div className="w-full flex items-center justify-between max-w-xl">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Target className="w-4 h-4 text-indigo-400" />
          <span>{t('priming.title')}</span>
        </div>
        <button
          type="button"
          onClick={onSkip}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg bg-[#1E293B] border border-slate-800 transition-colors"
        >
          <span>{t('priming.skip')}</span>
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Center fixation point */}
      <div className="flex flex-col items-center justify-center my-auto space-y-6">
        <div className="relative flex items-center justify-center">
          <div className="w-20 h-20 rounded-full border border-indigo-500/20 flex items-center justify-center">
            <div className="w-3.5 h-3.5 rounded-full bg-indigo-500 shadow-[0_0_16px_rgba(99,102,241,0.8)]" />
          </div>
        </div>
        <p className="text-sm text-slate-400 max-w-xs text-center font-sans">
          {t('priming.subtitle')}
        </p>
      </div>

      <div className="pb-6">
        <span className="font-mono text-lg text-slate-400">
          {timeFormatted}
        </span>
      </div>
    </div>
  );
};
