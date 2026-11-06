import React, { useState } from 'react';
import { Mail, ArrowRight, CheckCircle2, Shield } from 'lucide-react';
import { Locale } from '../types';
import { useTranslation } from '../i18n/context';

interface AuthSignInScreenProps {
  onSignInSuccess: (email: string) => void;
  locale: Locale;
  onLocaleChange: (loc: Locale) => void;
}

export const AuthSignInScreen: React.FC<AuthSignInScreenProps> = ({
  onSignInSuccess,
  locale,
  onLocaleChange
}) => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [resendCooldown, setResendCooldown] = useState(60);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@') || !email.includes('.')) {
      setStatus('error');
      setErrorMessage(t('auth.invalidEmail'));
      return;
    }

    setStatus('sending');
    setTimeout(() => {
      setStatus('sent');
      // Cooldown timer
      let count = 60;
      const timer = setInterval(() => {
        count -= 1;
        setResendCooldown(count);
        if (count <= 0) {
          clearInterval(timer);
        }
      }, 1000);
    }, 600);
  };

  const handleSimulateClickLink = () => {
    onSignInSuccess(email || 'alex@pegazus.edu');
  };

  return (
    <div className="min-h-screen w-full bg-[#090D16] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/30 via-[#090D16] to-[#090D16] flex flex-col justify-between p-6 sm:p-10 text-slate-100">
      {/* Top Bar with Locale Switcher */}
      <div className="w-full max-w-md mx-auto flex items-center justify-between">
        <div />
        <div className="flex items-center bg-[#1E293B] rounded-lg p-0.5 border border-slate-700/60">
          <button
            type="button"
            onClick={() => onLocaleChange('en')}
            className={`min-h-[40px] px-3 rounded-md text-xs font-medium transition-colors ${
              locale === 'en' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => onLocaleChange('es')}
            className={`min-h-[40px] px-3 rounded-md text-xs font-medium transition-colors ${
              locale === 'es' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ES
          </button>
        </div>
      </div>

      {/* Main Form: max-width ~420 px centered */}
      <div className="w-full max-w-[420px] mx-auto my-auto space-y-8">
        {/* Pegazus Wordmark Hero */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-100">
            Pegazus
          </h1>
          <p className="text-sm sm:text-base text-slate-400 font-sans">
            {t('auth.subtitle')}
          </p>
        </div>

        {status !== 'sent' ? (
          <div className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-5 shadow-xl">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-xs font-medium text-slate-300 mb-1.5">
                  Email address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (status === 'error') setStatus('idle');
                    }}
                    placeholder={t('auth.emailPlaceholder')}
                    disabled={status === 'sending'}
                    className="w-full pl-10 pr-4 py-3 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 transition-colors"
                  />
                </div>
                {status === 'error' && (
                  <p className="mt-1.5 text-xs text-[#F43F5E]">{errorMessage}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={status === 'sending'}
                className="w-full h-12 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                <span>{status === 'sending' ? t('auth.sending') : t('auth.sendLink')}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            <div className="relative flex items-center justify-center">
              <div className="border-t border-slate-800 w-full" />
              <span className="bg-[#0F172A] px-2 text-[11px] font-mono text-slate-500 uppercase tracking-wider absolute">
                {t('auth.orContinue')}
              </span>
            </div>

            {/* SSO buttons */}
            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={() => onSignInSuccess('owen.alexlol321@gmail.com')}
                className="w-full h-11 rounded-xl bg-[#1E293B] hover:bg-[#334155] border border-slate-700/60 text-slate-200 text-xs font-medium flex items-center justify-center gap-2.5 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#EA4335" d="M12 5c1.7 0 3 .6 4 1.5l3-3C17.2 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z" />
                  <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z" />
                  <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.8 0 12s.7 3.3 1.9 5.7l3.7-2.9z" />
                  <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z" />
                </svg>
                <span>{t('auth.google')}</span>
              </button>
            </div>
          </div>
        ) : (
          /* Sent State */
          <div className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-5 text-center shadow-xl">
            <div className="w-12 h-12 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h2 className="text-base font-semibold text-slate-100">
                {t('auth.checkEmail')}
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                {t('auth.checkEmailSub', { email })}
              </p>
            </div>

            {/* Simulator action to proceed into session */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleSimulateClickLink}
                className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
              >
                Simulate clicking magic link in email
              </button>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <button
                type="button"
                disabled={resendCooldown > 0}
                onClick={() => setResendCooldown(60)}
                className="text-xs text-slate-400 hover:text-slate-200 disabled:opacity-40"
              >
                {resendCooldown > 0
                  ? t('auth.resendIn', { seconds: resendCooldown })
                  : t('auth.resend')}
              </button>
            </div>
          </div>
        )}

        {/* Footer Privacy Note */}
        <p className="text-[11px] text-slate-500 text-center leading-relaxed">
          {t('auth.privacyNote')}
        </p>
      </div>

      <div />
    </div>
  );
};
