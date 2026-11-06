import React from 'react';
import { WifiOff } from 'lucide-react';
import { useTranslation } from '../../i18n/context';

interface OfflineBannerProps {
  isOffline: boolean;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({ isOffline }) => {
  const { t } = useTranslation();

  if (!isOffline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="w-full bg-amber-500/15 border-b border-amber-500/30 text-amber-200 px-4 py-2 text-xs flex items-center justify-center gap-2 font-medium"
    >
      <WifiOff className="w-4 h-4 shrink-0 text-amber-400" />
      <span>{t('offline.banner')}</span>
    </div>
  );
};
