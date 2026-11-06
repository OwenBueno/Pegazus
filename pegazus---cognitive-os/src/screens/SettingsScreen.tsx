import React from 'react';
import {
  User,
  Sliders,
  Key,
  Trash2,
  Info,
  ChevronRight,
  LogOut,
  ShieldAlert
} from 'lucide-react';
import { UserProfile, Locale } from '../types';
import { useTranslation } from '../i18n/context';

interface SettingsScreenProps {
  user: UserProfile;
  onUpdateProfile: (updates: Partial<UserProfile>) => void;
  onNavigateByo: () => void;
  onNavigateDelete: () => void;
  onSignOut: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  user,
  onUpdateProfile,
  onNavigateByo,
  onNavigateDelete,
  onSignOut
}) => {
  const { t, locale, setLocale } = useTranslation();

  return (
    <div className="w-full space-y-6">
      {/* Title */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">
          {t('settings.title')}
        </h1>
        <p className="text-xs font-mono text-slate-400">
          {t('settings.versionLabel')}
        </p>
      </div>

      {/* Minor Protection Notice if applicable */}
      {user.isMinor && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{t('settings.minorNotice')}</span>
        </div>
      )}

      {/* Section 1: Profile */}
      <div className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-400">
          <User className="w-4 h-4 text-indigo-400" />
          <span>{t('settings.profileSection')}</span>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">{t('settings.emailLabel')}</label>
            <div className="p-3 bg-[#1E293B] border border-slate-800 rounded-xl text-slate-300 text-xs font-mono">
              {user.email}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('settings.localeLabel')}</label>
              <select
                value={locale}
                onChange={(e) => setLocale(e.target.value as Locale)}
                className="w-full p-2.5 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value="en">English (US)</option>
                <option value="es">Español (LatAm)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">{t('settings.sessionDurationLabel')}</label>
              <select
                value={user.preferredSessionMinutes}
                onChange={(e) =>
                  onUpdateProfile({ preferredSessionMinutes: parseInt(e.target.value, 10) })
                }
                className="w-full p-2.5 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value={15}>15 minutes</option>
                <option value={25}>25 minutes</option>
                <option value={45}>45 minutes</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Study Engine */}
      <div className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-400">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <span>{t('settings.studySection')}</span>
        </div>

        <div className="space-y-4">
          {/* Target Retention */}
          <div>
            <div className="flex items-center justify-between text-xs text-slate-300 mb-1">
              <span>{t('settings.retentionLabel')}</span>
              <span className="font-mono text-indigo-300 font-semibold">{user.targetRetention.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.80"
              max="0.95"
              step="0.01"
              value={user.targetRetention}
              onChange={(e) =>
                onUpdateProfile({ targetRetention: parseFloat(e.target.value) })
              }
              className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-slate-500 mt-1">{t('settings.retentionHelp')}</p>
          </div>

          {/* Micro-break interval */}
          <div className="pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between text-xs text-slate-300 mb-1">
              <span>{t('settings.microBreakLabel')}</span>
              <span className="font-mono text-indigo-300 font-semibold">{user.microBreakIntervalMinutes} min</span>
            </div>
            <input
              type="range"
              min="5"
              max="7"
              step="1"
              value={user.microBreakIntervalMinutes}
              onChange={(e) =>
                onUpdateProfile({ microBreakIntervalMinutes: parseInt(e.target.value, 10) })
              }
              className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
            <p className="text-[11px] text-slate-500 mt-1">{t('settings.microBreakHelp')}</p>
          </div>

          {/* Focus priming toggle */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-xs text-slate-300 font-medium block">
                {t('settings.focusPrimingLabel')}
              </span>
              <span className="text-[11px] text-slate-500 block">
                {t('settings.focusPrimingHelp')}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={user.focusPrimingEnabled}
              onClick={() =>
                onUpdateProfile({ focusPrimingEnabled: !user.focusPrimingEnabled })
              }
              className={`w-11 h-6 rounded-full transition-colors relative ${
                user.focusPrimingEnabled ? 'bg-indigo-600' : 'bg-slate-800'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform transform ${
                  user.focusPrimingEnabled ? 'translate-x-6' : 'translate-x-1'
                } top-1 absolute`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Section 3: BYO API Key */}
      {!user.isMinor && (
        <div
          onClick={onNavigateByo}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onNavigateByo()}
          className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer flex items-center justify-between group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300 transition-colors">
                {t('settings.apiKeySection')}
              </h4>
              <p className="text-[11px] text-slate-400">
                {user.openRouterApiKey ? 'Custom key configured' : t('settings.apiKeyDesc')}
              </p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-slate-300" />
        </div>
      )}

      {/* Section 4: Privacy & Deletion */}
      <div
        onClick={onNavigateDelete}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onNavigateDelete()}
        className="p-5 rounded-2xl bg-[#0F172A] border border-slate-800 hover:border-red-500/40 transition-colors cursor-pointer flex items-center justify-between group"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red-500/10 text-[#F43F5E]">
            <Trash2 className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-200 group-hover:text-red-400 transition-colors">
              {t('settings.deleteAccountLink')}
            </h4>
            <p className="text-[11px] text-slate-500">
              Permanently delete all learning data and account records
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-slate-300" />
      </div>

      {/* Sign Out Action */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onSignOut}
          className="w-full h-11 rounded-xl bg-transparent hover:bg-slate-800/80 border border-slate-800 text-slate-400 hover:text-slate-200 text-xs font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>{t('nav.signOut')}</span>
        </button>
      </div>
    </div>
  );
};
