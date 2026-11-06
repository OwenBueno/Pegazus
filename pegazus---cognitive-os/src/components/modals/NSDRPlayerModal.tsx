import React, { useState, useEffect, useRef } from 'react';
import { Volume2, VolumeX, FileText, X } from 'lucide-react';
import { useTranslation } from '../../i18n/context';

interface NSDRPlayerProps {
  onReturnHome: () => void;
  defaultMinutes?: number;
}

export const NSDRPlayer: React.FC<NSDRPlayerProps> = ({
  onReturnHome,
  defaultMinutes = 7
}) => {
  const { t } = useTranslation();
  const [secondsRemaining, setSecondsRemaining] = useState<number>(defaultMinutes * 60);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [showTranscript, setShowTranscript] = useState<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);

  // Timer countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Ambient sound synthesis using Web Audio API (so no external audio asset required and ZERO autoplay)
  const toggleAudio = () => {
    if (isPlaying) {
      // stop
      if (gainNodeRef.current && audioContextRef.current) {
        gainNodeRef.current.gain.setTargetAtTime(0, audioContextRef.current.currentTime, 0.2);
        setTimeout(() => {
          oscillatorRef.current?.stop();
          oscillatorRef.current?.disconnect();
          oscillatorRef.current = null;
        }, 200);
      }
      setIsPlaying(false);
    } else {
      // start calm 136.1 Hz om/earth tone or low delta frequency
      try {
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        // 108 Hz warm grounded tone
        osc.type = 'sine';
        osc.frequency.setValueAtTime(108, ctx.currentTime);

        // Gentle volume ramp
        gain.gain.setValueAtTime(0.001, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.04, ctx.currentTime + 1.5);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();

        oscillatorRef.current = osc;
        gainNodeRef.current = gain;
        setIsPlaying(true);
      } catch {
        setIsPlaying(false);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  const mins = Math.floor(secondsRemaining / 60);
  const secs = secondsRemaining % 60;
  const timeFormatted = `${mins}:${secs.toString().padStart(2, '0')}`;

  return (
    <div className="w-full max-w-xl mx-auto p-6 sm:p-8 rounded-2xl bg-[#0F172A] border border-slate-800 text-center space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl sm:text-2xl font-semibold text-slate-100">
          {t('wakefulRest.title')}
        </h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
          {t('wakefulRest.instruction')}
        </p>
      </div>

      {/* Timer Display */}
      <div className="py-4">
        <span className="font-mono text-4xl sm:text-5xl font-light tracking-wider text-slate-100">
          {timeFormatted}
        </span>
        <div className="text-xs font-mono text-slate-500 uppercase tracking-wider mt-1">
          {t('wakefulRest.timerLabel')}
        </div>
      </div>

      {/* NSDR Ambient Player */}
      <div className="p-4 rounded-xl bg-[#1E293B]/70 border border-slate-700/60 text-left space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              {t('wakefulRest.nsdrTitle')}
            </h4>
            <p className="text-xs text-slate-400">
              {t('wakefulRest.nsdrHelp')}
            </p>
          </div>
          <button
            type="button"
            onClick={toggleAudio}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors ${
              isPlaying
                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
            }`}
            aria-label={isPlaying ? 'Pause acoustic guidance' : 'Play acoustic guidance'}
          >
            {isPlaying ? <Volume2 className="w-4 h-4 text-teal-400" /> : <VolumeX className="w-4 h-4" />}
            <span>{isPlaying ? t('wakefulRest.pauseAudio') : t('wakefulRest.playAudio')}</span>
          </button>
        </div>

        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowTranscript(true)}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{t('wakefulRest.viewTranscript')}</span>
          </button>
        </div>
      </div>

      {/* Return Home CTA */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onReturnHome}
          className="w-full h-12 rounded-xl bg-[#1E293B] hover:bg-[#334155] border border-slate-700 text-slate-200 text-sm font-medium transition-colors"
        >
          {secondsRemaining === 0 ? t('wakefulRest.completedReturn') : t('wakefulRest.doneEarly')}
        </button>
      </div>

      {/* Transcript Modal */}
      {showTranscript && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm text-left"
        >
          <div className="w-full max-w-lg p-6 rounded-2xl bg-[#0F172A] border border-slate-700 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-base font-semibold text-slate-100">
                {t('wakefulRest.transcriptTitle')}
              </h3>
              <button
                type="button"
                onClick={() => setShowTranscript(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200"
                aria-label="Close transcript"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="text-sm text-slate-300 leading-relaxed max-h-80 overflow-y-auto space-y-3 font-sans pr-1">
              <p>
                <strong>0:00 - 1:30:</strong> Allow your eyes to close gently or soften your gaze downwards. Breathe in deeply through the nose, pause for a second, and release a long, slow exhale through the mouth. Repeat twice.
              </p>
              <p>
                <strong>1:30 - 4:00:</strong> Release any effort to solve problems or analyze mathematical steps. Allow the mind to wander naturally. During this wakeful resting state, neural circuits in the hippocampus replay and stabilize recent memory traces.
              </p>
              <p>
                <strong>4:00 - 7:00:</strong> Notice the sensation of weight in your hands and feet. Maintain stillness. When the timer concludes, you will return feeling renewed mental clarity.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
