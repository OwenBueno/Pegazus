"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { Mic } from "lucide-react";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";
import { ListenButton, useVoice } from "./AudioClip";

// Minimal slice of the (non-standard, partly webkit-prefixed) Web Speech recognition API.
type Recognition = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  abort(): void;
};
type RecognitionCtor = new () => Recognition;

const getRecognition = (): RecognitionCtor | undefined => {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
};
const noop = () => () => {};

type Status = "idle" | "listening" | "heard" | "noSpeech" | "micDenied" | "error";

/** Emits {transcript} (server compares to phrase) or self-rating {self: 0|1}; self-rating is always offered. */
export function Pronunciation({
  phrase,
  lang,
  prompt,
  widgetId = "pronunciation",
  disabled = false,
  onAction,
}: {
  phrase: string;
  lang: string;
  prompt?: string;
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const voice = useVoice(lang);
  const canRecord = useSyncExternalStore(noop, () => !!getRecognition(), () => false);
  const [status, setStatus] = useState<Status>("idle");
  const [transcript, setTranscript] = useState("");
  const rec = useRef<Recognition | null>(null);

  useEffect(() => () => rec.current?.abort(), []);

  function record() {
    const Ctor = getRecognition();
    if (!Ctor) return;
    const r = new Ctor();
    r.lang = lang;
    r.interimResults = false;
    r.maxAlternatives = 1;
    let got = "";
    r.onresult = (e) => {
      got = e.results[0]?.[0]?.transcript.trim() ?? "";
    };
    r.onerror = (e) => {
      setStatus(e.error === "not-allowed" || e.error === "service-not-allowed" ? "micDenied" : e.error === "no-speech" ? "noSpeech" : "error");
    };
    r.onend = () => {
      rec.current = null;
      setTranscript(got);
      setStatus((s) => (s !== "listening" ? s : got ? "heard" : "noSpeech"));
    };
    rec.current = r;
    setTranscript("");
    setStatus("listening");
    try {
      r.start();
    } catch {
      rec.current = null;
      setStatus("error");
    }
  }

  const send = (payload: Record<string, unknown>) => onAction?.({ widgetId, type: "ANSWER", payload });
  const listening = status === "listening";

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("pronounceTitle")}</p>
      {prompt && <p className="text-sm text-slate-300">{prompt}</p>}
      <div className="flex items-center gap-3 rounded-control border border-line-strong bg-surface-raised p-4">
        {voice && <ListenButton text={phrase} voice={voice} />}
        <p lang={lang} className="text-[17px] leading-relaxed text-slate-50">
          {phrase}
        </p>
      </div>

      {canRecord ? (
        <>
          <button
            type="button"
            disabled={disabled || listening}
            onClick={record}
            className={buttonClass("secondary", "md", true)}
          >
            <Mic className="h-4 w-4" aria-hidden />
            {listening ? t("pronounceListening") : t("pronounceRecord")}
          </button>
          <p aria-live="polite" className="min-h-5 text-sm text-slate-300">
            {status === "heard" && (
              <>
                {t("pronounceHeard")} <span lang={lang} className="text-slate-50">{transcript}</span>
              </>
            )}
            {status === "noSpeech" && t("pronounceNoSpeech")}
            {status === "micDenied" && t("pronounceMicDenied")}
            {status === "error" && t("pronounceError")}
          </p>
          {status === "heard" && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => send({ transcript })}
              className={buttonClass("primary", "md", true)}
            >
              {t("pronounceSubmit")}
            </button>
          )}
        </>
      ) : (
        <p className="text-sm text-slate-400">{t("pronounceUnsupported")}</p>
      )}

      <div role="group" aria-label={t("pronounceSelfRate")} className="grid grid-cols-2 gap-2">
        <button type="button" disabled={disabled} onClick={() => send({ self: 0 })} className={buttonClass("secondary", "md", true)}>
          {t("pronounceSelfPractice")}
        </button>
        <button type="button" disabled={disabled} onClick={() => send({ self: 1 })} className={buttonClass("secondary", "md", true)}>
          {t("pronounceSelfGood")}
        </button>
      </div>
    </section>
  );
}
