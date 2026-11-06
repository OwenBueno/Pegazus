import React, { useState } from 'react';
import { ShieldAlert, Mail, LogOut, CheckCircle2 } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface ConsentWaitScreenProps {
  onBypassConsent: () => void;
  onSignOut: () => void;
}

export const ConsentWaitScreen: React.FC<ConsentWaitScreenProps> = ({
  onBypassConsent,
  onSignOut
}) => {
  const { t } = useTranslation();
  const [emailSent, setEmailSent] = useState(false);

  return (
    <div className="min-h-screen w-full bg-[#090D16] flex flex-col justify-between p-6 sm:p-10 text-slate-100">
      <div className="w-full max-w-[440px] mx-auto my-auto space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 mx-auto flex items-center justify-center mb-3">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
            {t('consent.title')}
          </h1>
          <p className="text-xs font-mono text-amber-400/90 uppercase tracking-wider">
            {t('consent.status')}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4 shadow-xl">
          <p className="text-sm text-slate-300 leading-relaxed font-sans">
            {t('consent.desc')}
          </p>

          <div className="p-3.5 rounded-xl bg-[#1E293B] border border-slate-700/60 text-xs text-slate-400 leading-relaxed">
            {t('consent.blockedFeatures')}
          </div>

          <div className="pt-2 space-y-2.5">
            {!emailSent ? (
              <button
                type="button"
                onClick={() => setEmailSent(true)}
                className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                <Mail className="w-4 h-4" />
                <span>{t('consent.ctaSent')}</span>
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{t('consent.sentNotice')}</span>
                </div>
                <button
                  type="button"
                  onClick={onBypassConsent}
                  className="w-full h-10 rounded-xl bg-[#1E293B] hover:bg-[#334155] text-indigo-300 text-xs font-medium transition-colors"
                >
                  Verify guardian consent (Simulate approval)
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={onSignOut}
              className="w-full h-11 rounded-xl bg-transparent hover:bg-slate-800 text-slate-400 hover:text-slate-200 text-xs font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>{t('consent.ctaSignOut')}</span>
            </button>
          </div>
        </div>
      </div>

      <div />
    </div>
  );
};
