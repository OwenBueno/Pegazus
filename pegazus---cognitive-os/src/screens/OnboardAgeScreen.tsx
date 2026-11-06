import React, { useState } from 'react';
import { Calendar, ArrowRight } from 'lucide-react';
import { useTranslation } from '../i18n/context';

interface OnboardAgeScreenProps {
  onYearSelected: (year: number, isMinor: boolean) => void;
}

export const OnboardAgeScreen: React.FC<OnboardAgeScreenProps> = ({ onYearSelected }) => {
  const { t } = useTranslation();
  const [year, setYear] = useState<number | ''>('');
  const [error, setError] = useState('');

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 90 }, (_, i) => currentYear - 6 - i);

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    if (!year || typeof year !== 'number' || year < 1920 || year > currentYear - 4) {
      setError(t('age.error'));
      return;
    }

    // Mexico market consent age: 18 years
    const age = currentYear - year;
    const isMinor = age < 18;

    onYearSelected(year, isMinor);
  };

  return (
    <div className="min-h-screen w-full bg-[#090D16] flex flex-col justify-between p-6 sm:p-10 text-slate-100">
      <div className="w-full max-w-[420px] mx-auto my-auto space-y-8">
        <div className="text-center space-y-2">
          <span className="font-mono text-xs text-indigo-400 uppercase tracking-widest">
            Pegazus Onboarding
          </span>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-100">
            {t('age.title')}
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-sans max-w-sm mx-auto">
            {t('age.help')}
          </p>
        </div>

        <form onSubmit={handleContinue} className="p-6 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-5 shadow-xl">
          <div>
            <label htmlFor="birth-year" className="block text-xs font-medium text-slate-300 mb-2">
              Birth Year
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Calendar className="w-4 h-4" />
              </div>
              <select
                id="birth-year"
                value={year}
                onChange={(e) => {
                  setYear(e.target.value ? parseInt(e.target.value, 10) : '');
                  setError('');
                }}
                className="w-full pl-10 pr-4 py-3 bg-[#1E293B] border border-slate-700/80 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 appearance-none transition-colors cursor-pointer"
              >
                <option value="">{t('age.yearPlaceholder')}</option>
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            {error && <p className="mt-2 text-xs text-[#F43F5E]">{error}</p>}
          </div>

          <button
            type="submit"
            disabled={!year}
            className="w-full h-12 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-40"
          >
            <span>{t('age.continue')}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </div>

      <div />
    </div>
  );
};
