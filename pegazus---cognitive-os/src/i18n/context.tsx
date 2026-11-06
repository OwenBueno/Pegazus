import React, { createContext, useContext } from 'react';
import { Locale } from '../types';
import { en } from './messages/en';
import { es } from './messages/es';

type Messages = typeof en;

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (path: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

const catalogs: Record<Locale, Messages> = {
  en,
  es: es as Messages
};

function getNestedValue(obj: Record<string, unknown>, path: string): string {
  const parts = path.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return path;
    }
  }
  return typeof current === 'string' ? current : path;
}

export const I18nProvider: React.FC<{
  locale: Locale;
  setLocale: (locale: Locale) => void;
  children: React.ReactNode;
}> = ({ locale, setLocale, children }) => {
  const t = (path: string, params?: Record<string, string | number>): string => {
    const raw = getNestedValue(catalogs[locale] as unknown as Record<string, unknown>, path);
    if (!params) return raw;
    let result = raw;
    for (const [key, val] of Object.entries(params)) {
      result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val));
    }
    return result;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useTranslation = (): I18nContextType => {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useTranslation must be used within an I18nProvider');
  }
  return ctx;
};
