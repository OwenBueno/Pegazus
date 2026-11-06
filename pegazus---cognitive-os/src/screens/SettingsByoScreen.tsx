import React, { useState } from 'react';
import { ArrowLeft, Key, CheckCircle2, AlertCircle, Eye, EyeOff, Trash2 } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface SettingsByoScreenProps {
  currentKey?: string;
  onSaveKey: (key: string) => void;
  onRemoveKey: () => void;
  onBack: () => void;
  isMinor: boolean;
}

export const SettingsByoScreen: React.FC<SettingsByoScreenProps> = ({
  currentKey,
  onSaveKey,
  onRemoveKey,
  onBack,
  isMinor
}) => {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState(currentKey || '');
  const [showKey, setShowKey] = useState(false);
  const [status, setStatus] = useState<'idle' | 'testing' | 'valid' | 'invalid'>('idle');

  const handleTestAndSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;

    if (isMinor) {
      setStatus('invalid');
      return;
    }

    setStatus('testing');
    setTimeout(() => {
      // Simulate validation
      if (apiKey.startsWith('sk-') && apiKey.length > 10) {
        setStatus('valid');
        onSaveKey(apiKey);
      } else {
        setStatus('invalid');
      }
    }, 700);
  };

  const handleRemove = () => {
    setApiKey('');
    setStatus('idle');
    onRemoveKey();
  };

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
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
          {t('byo.title')}
        </h1>
        <p className="text-sm text-slate-400 font-sans leading-relaxed">
          {t('byo.desc')}
        </p>
      </div>

      <form onSubmit={handleTestAndSave} className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-5 shadow-xl">
        <div>
          <label htmlFor="api-key-input" className="block text-xs font-medium text-slate-300 mb-2">
            OpenRouter API Key
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Key className="w-4 h-4" />
            </div>
            <input
              id="api-key-input"
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                if (status !== 'idle') setStatus('idle');
              }}
              placeholder={t('byo.keyPlaceholder')}
              disabled={status === 'testing'}
              className="w-full pl-10 pr-12 py-3 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 placeholder-slate-500 font-mono text-xs focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 transition-colors"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200"
              aria-label={showKey ? t('byo.hide') : t('byo.show')}
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Validation statuses */}
        {status === 'valid' && (
          <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{t('byo.keyValid')}</span>
          </div>
        )}

        {status === 'invalid' && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{t('byo.keyInvalid')}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          {currentKey ? (
            <button
              type="button"
              onClick={handleRemove}
              className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>{t('byo.removeKey')}</span>
            </button>
          ) : (
            <div />
          )}

          <button
            type="submit"
            disabled={status === 'testing' || !apiKey.trim()}
            className="min-h-[44px] px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold transition-colors"
          >
            {status === 'testing' ? t('byo.testing') : t('byo.saveAndTest')}
          </button>
        </div>
      </form>
    </div>
  );
};
