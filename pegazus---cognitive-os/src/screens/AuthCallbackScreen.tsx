import React, { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface AuthCallbackScreenProps {
  onComplete: () => void;
}

export const AuthCallbackScreen: React.FC<AuthCallbackScreenProps> = ({ onComplete }) => {
  const { t } = useTranslation();

  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 900);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="min-h-screen w-full bg-[#090D16] flex flex-col items-center justify-center p-6 text-slate-100 text-center space-y-4">
      <h1 className="text-3xl font-semibold tracking-tight text-slate-100">
        Pegazus
      </h1>
      <div className="flex items-center gap-2 text-indigo-400 text-sm font-medium">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>{t('auth.callbackTitle')}</span>
      </div>
      <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
        {t('auth.callbackSub')}
      </p>
    </div>
  );
};
