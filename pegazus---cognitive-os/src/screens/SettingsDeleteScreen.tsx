import React, { useState } from 'react';
import { ArrowLeft, Trash2, AlertTriangle } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface SettingsDeleteScreenProps {
  onBack: () => void;
  onConfirmDelete: () => void;
}

export const SettingsDeleteScreen: React.FC<SettingsDeleteScreenProps> = ({
  onBack,
  onConfirmDelete
}) => {
  const { t, locale } = useTranslation();
  const [confirmInput, setConfirmInput] = useState('');

  const requiredWord = locale === 'es' ? 'ELIMINAR' : 'DELETE';
  const isMatch = confirmInput.trim() === requiredWord;

  return (
    <div className="w-full space-y-6 animate-fade-in">
      {/* Top Back Link */}
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Settings</span>
      </button>

      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100 flex items-center gap-2">
          <Trash2 className="w-5 h-5 text-[#F43F5E]" />
          <span>{t('deleteAccount.title')}</span>
        </h1>
      </div>

      <div className="p-6 rounded-2xl bg-[#0F172A] border border-red-500/30 space-y-5 shadow-xl">
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-[#F43F5E] shrink-0 mt-0.5" />
          <p className="leading-relaxed font-sans">{t('deleteAccount.warning')}</p>
        </div>

        <div className="space-y-2">
          <label htmlFor="confirm-delete-input" className="block text-xs font-medium text-slate-300">
            {t('deleteAccount.typePrompt', { confirmText: requiredWord })}
          </label>
          <input
            id="confirm-delete-input"
            type="text"
            value={confirmInput}
            onChange={(e) => setConfirmInput(e.target.value)}
            placeholder={requiredWord}
            className="w-full px-4 py-3 bg-[#1E293B] border border-slate-700 rounded-xl text-slate-100 font-mono text-sm placeholder-slate-600 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/30 transition-colors"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onBack}
            className="px-4 py-2.5 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-medium transition-colors"
          >
            {t('deleteAccount.cancel')}
          </button>
          <button
            type="button"
            disabled={!isMatch}
            onClick={onConfirmDelete}
            className="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-30 text-white text-xs font-semibold flex items-center gap-2 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span>{t('deleteAccount.deleteCta')}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
