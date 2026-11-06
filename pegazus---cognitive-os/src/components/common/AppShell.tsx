import React from 'react';
import { Home, Compass, Play, HelpCircle, Settings, Wifi, WifiOff } from 'lucide-react';
import { AppRoute, Locale } from '../../types';
import { useTranslation } from '../../i18n/context';

interface AppShellProps {
  currentRoute: AppRoute;
  onNavigate: (route: AppRoute) => void;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  isOffline: boolean;
  onToggleOffline: () => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentRoute,
  onNavigate,
  locale,
  onLocaleChange,
  isOffline,
  onToggleOffline,
  children
}) => {
  const { t } = useTranslation();

  const navItems: { id: AppRoute; label: string; icon: React.ReactNode }[] = [
    { id: 'HOME', label: t('nav.home'), icon: <Home className="w-5 h-5" /> },
    { id: 'PATH_VIEW', label: t('nav.path'), icon: <Compass className="w-5 h-5" /> },
    { id: 'SESSION', label: t('nav.practice'), icon: <Play className="w-5 h-5" /> },
    { id: 'SOCRATIC', label: t('nav.ask'), icon: <HelpCircle className="w-5 h-5" /> }
  ];

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top bar, 56 px min */}
      <header className="sticky top-0 z-30 w-full min-h-[56px] h-14 bg-[#0F172A]/90 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-6 flex items-center justify-between">
        {/* Brand: Pegazus hero-level signal */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onNavigate('HOME')}
            className="flex items-center gap-2 group text-left focus:outline-none"
            aria-label="Pegazus Home"
          >
            <span className="font-semibold text-xl tracking-tight text-slate-100 group-hover:text-indigo-300 transition-colors">
              Pegazus
            </span>
            <span className="text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 hidden sm:inline">
              Cognitive OS
            </span>
          </button>
        </div>

        {/* Top bar actions: offline simulator toggle, locale switch, settings */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Offline indicator / toggle */}
          <button
            type="button"
            onClick={onToggleOffline}
            className={`min-w-[48px] min-h-[48px] flex items-center justify-center rounded-lg text-xs transition-colors ${
              isOffline
                ? 'text-amber-400 hover:bg-amber-500/10'
                : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
            }`}
            title={isOffline ? 'Simulating offline' : 'Simulate offline'}
            aria-label={isOffline ? 'Network offline' : 'Network online'}
          >
            {isOffline ? <WifiOff className="w-4 h-4" /> : <Wifi className="w-4 h-4" />}
          </button>

          {/* Locale switcher: en / es */}
          <div className="flex items-center bg-[#1E293B] rounded-lg p-0.5 border border-slate-700/60">
            <button
              type="button"
              onClick={() => onLocaleChange('en')}
              className={`min-h-[40px] px-2.5 rounded-md text-xs font-medium transition-colors ${
                locale === 'en'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => onLocaleChange('es')}
              className={`min-h-[40px] px-2.5 rounded-md text-xs font-medium transition-colors ${
                locale === 'es'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ES
            </button>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-1 ml-4 border-l border-slate-800 pl-4">
            {navItems.map((item) => {
              const isActive = currentRoute === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onNavigate(item.id)}
                  className={`min-h-[48px] px-3.5 flex items-center gap-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#1E293B]'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Settings / Account button */}
          <button
            type="button"
            onClick={() => onNavigate('SETTINGS')}
            className={`min-w-[48px] min-h-[48px] flex items-center justify-center rounded-lg transition-colors ${
              currentRoute === 'SETTINGS' || currentRoute === 'SETTINGS_BYO' || currentRoute === 'SETTINGS_DELETE'
                ? 'bg-indigo-500/15 text-indigo-300'
                : 'text-slate-400 hover:text-slate-200 hover:bg-[#1E293B]'
            }`}
            aria-label="Settings and profile"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Page Content: centered max-w-xl on tablet+ */}
      <main className="flex-1 w-full max-w-xl mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-12">
        {children}
      </main>

      {/* Mobile Bottom Navigation (< md): 4 destinations max */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-30 min-h-[56px] bg-[#0F172A]/95 backdrop-blur-lg border-t border-slate-800/80 px-2 py-1 flex items-center justify-around"
        role="navigation"
        aria-label="Bottom Navigation"
      >
        {navItems.map((item) => {
          const isActive = currentRoute === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`min-w-[48px] min-h-[48px] flex-1 flex flex-col items-center justify-center gap-1 rounded-lg text-xs font-medium transition-colors ${
                isActive ? 'text-indigo-400' : 'text-slate-400 hover:text-slate-200'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              {item.icon}
              <span className="text-[11px] leading-none">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
