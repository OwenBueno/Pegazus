import React, { useState, useEffect, useRef } from 'react';
import { Eye, CheckCircle2, AlertCircle } from 'lucide-react';
import { useTranslation } from '../../i18n/context';

interface RestOverlayProps {
  isOpen: boolean;
  durationSeconds?: number;
  onComplete: () => void;
  onSkipConfirmed: () => void;
}

export const RestOverlay: React.FC<RestOverlayProps> = ({
  isOpen,
  durationSeconds = 30,
  onComplete,
  onSkipConfirmed
}) => {
  const { t } = useTranslation();
  const [remaining, setRemaining] = useState<number>(durationSeconds);
  const [showSkipConfirm, setShowSkipConfirm] = useState<boolean>(false);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!isOpen) {
      setRemaining(durationSeconds);
      setShowSkipConfirm(false);
      completedRef.current = false;
      return;
    }

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          if (!completedRef.current) {
            completedRef.current = true;
            onComplete();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, durationSeconds, onComplete]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('rest.overlayTitle')}
      className="fixed inset-0 z-50 flex flex-col items-center justify-between p-6 sm:p-10 bg-[#090D16]/95 backdrop-blur-md text-slate-100"
    >
      {/* Top instruction */}
      <div className="text-center max-w-md pt-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-300 font-mono mb-4">
          <Eye className="w-3.5 h-3.5 text-indigo-400" />
          <span>{t('rest.overlayTitle')}</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-100 mb-2">
          {t('rest.overlaySub')}
        </h2>
      </div>

      {/* Center 10s breathe circle animation */}
      <div className="relative flex flex-col items-center justify-center my-auto">
        <div className="relative flex items-center justify-center">
          {/* Outer glow ring */}
          <div className="w-64 h-64 sm:w-72 sm:h-72 rounded-full border border-indigo-500/20 animate-breathe flex items-center justify-center">
            {/* Middle pulsating circle */}
            <div className="w-48 h-48 sm:w-56 sm:h-56 rounded-full bg-gradient-to-tr from-indigo-600/20 to-teal-500/10 border border-indigo-500/30 flex items-center justify-center">
              {/* Inner core */}
              <div className="w-28 h-28 rounded-full bg-[#0F172A] border border-indigo-500/50 flex flex-col items-center justify-center shadow-lg">
                <span className="font-mono text-2xl font-semibold text-slate-100">
                  {remaining}s
                </span>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                  Resting
                </span>
              </div>
            </div>
          </div>
        </div>

        <p className="mt-8 text-sm font-medium text-slate-400 text-center tracking-wide">
          {t('rest.breatheIn')}
        </p>
      </div>

      {/* Bottom controls */}
      <div className="w-full max-w-xs pb-4 text-center">
        <button
          type="button"
          onClick={() => setShowSkipConfirm(true)}
          className="text-xs text-slate-400 hover:text-slate-200 py-2.5 px-4 rounded-lg hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-800"
        >
          {t('rest.skipRest')}
        </button>
      </div>

      {/* Honest Skip Confirmation Dialog */}
      {showSkipConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        >
          <div className="w-full max-w-md p-6 rounded-2xl bg-[#0F172A] border border-slate-700 shadow-2xl text-left space-y-4">
            <div className="flex items-center gap-3 text-slate-100">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <AlertCircle className="w-5 h-5" />
              </div>
              <h3 className="text-base font-semibold">
                {t('rest.skipConfirmTitle')}
              </h3>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">
              {t('rest.skipConfirmDesc')}
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowSkipConfirm(false)}
                className="px-4 py-2 rounded-lg bg-[#1E293B] hover:bg-[#334155] text-slate-200 text-xs font-medium transition-colors"
              >
                {t('rest.stayRest')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSkipConfirm(false);
                  onSkipConfirmed();
                }}
                className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-100 text-xs font-medium transition-colors"
              >
                {t('rest.confirmSkip')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
