"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { Square, Volume2 } from "lucide-react";
import { buttonClass } from "@/components/ui/Button";

const hasTts = () => typeof window !== "undefined" && "speechSynthesis" in window;

function pickVoice(lang: string) {
  const voices = window.speechSynthesis.getVoices();
  const norm = (l: string) => l.toLowerCase().replace(/_/g, "-");
  const want = norm(lang);
  const primary = want.split("-")[0];
  return (
    voices.find((v) => norm(v.lang) === want) ??
    voices.find((v) => norm(v.lang).split("-")[0] === primary) ??
    null
  );
}

function subscribe(cb: () => void) {
  if (!hasTts()) return () => {};
  window.speechSynthesis.addEventListener("voiceschanged", cb);
  return () => window.speechSynthesis.removeEventListener("voiceschanged", cb);
}

/** Best SpeechSynthesisVoice for `lang` (exact, then primary subtag), or null. Null on the server. */
export function useVoice(lang: string): SpeechSynthesisVoice | null {
  // Snapshot is the voiceURI (a stable string) since getVoices() may return fresh objects each call.
  const uri = useSyncExternalStore(
    subscribe,
    () => (hasTts() ? (pickVoice(lang)?.voiceURI ?? "") : ""),
    () => "",
  );
  return useMemo(
    () => (uri ? (window.speechSynthesis.getVoices().find((v) => v.voiceURI === uri) ?? null) : null),
    [uri],
  );
}

/** Play/stop toggle for one utterance; cancels its own speech on unmount. */
export function ListenButton({ text, voice, rate }: { text: string; voice: SpeechSynthesisVoice; rate?: number }) {
  const t = useTranslations("session");
  const [speaking, setSpeaking] = useState(false);
  const mine = useRef<SpeechSynthesisUtterance | null>(null);

  // ponytail: speechSynthesis is a global queue; we cancel() it wholesale, so starting one clip stops any other.
  useEffect(() => () => {
    if (mine.current) window.speechSynthesis.cancel();
  }, []);

  function toggle() {
    const synth = window.speechSynthesis;
    synth.cancel();
    if (speaking) {
      mine.current = null;
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    if (rate) u.rate = rate;
    u.onend = u.onerror = () => {
      if (mine.current === u) mine.current = null;
      setSpeaking(false);
    };
    mine.current = u;
    setSpeaking(true);
    synth.speak(u);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={speaking}
      aria-label={speaking ? t("audioStop") : t("audioListen", { text })}
      className={buttonClass("secondary", "icon")}
    >
      {speaking ? <Square className="h-5 w-5" aria-hidden /> : <Volume2 className="h-5 w-5" aria-hidden />}
    </button>
  );
}

/** Display-only TTS clip; renders nothing when the browser has no voice for `lang`. */
export function AudioClip({ text, lang, rate, label }: { text: string; lang: string; rate?: number; label?: string }) {
  const voice = useVoice(lang);
  if (!voice) return null;

  return (
    <div className="flex items-center gap-3 rounded-panel border border-line bg-surface-glass p-4 backdrop-blur-xl">
      <ListenButton text={text} voice={voice} rate={rate} />
      <div className="min-w-0">
        {label && <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{label}</p>}
        <p lang={lang} className="text-[17px] leading-relaxed text-slate-50">
          {text}
        </p>
      </div>
    </div>
  );
}
