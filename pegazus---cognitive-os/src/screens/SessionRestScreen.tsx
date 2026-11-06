import React from 'react';
import { NSDRPlayer } from '../components/modals/NSDRPlayerModal';

interface SessionRestScreenProps {
  onReturnHome: () => void;
}

export const SessionRestScreen: React.FC<SessionRestScreenProps> = ({ onReturnHome }) => {
  return (
    <div className="w-full pt-4 animate-fade-in">
      <NSDRPlayer onReturnHome={onReturnHome} defaultMinutes={7} />
    </div>
  );
};
