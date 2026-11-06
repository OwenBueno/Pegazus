"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { MessagesSquare, SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Sheet } from "@/components/ui/Sheet";
import { tutorChat, type TutorChatMessage } from "@/lib/api";
import { cn } from "@/lib/cn";

const MAX_TURNS = 8;

export function TutorChat({
  token,
  sessionId,
  itemId,
  locale,
  offline,
}: {
  token: string;
  sessionId: string;
  itemId: string;
  locale: string;
  offline?: boolean;
}) {
  const t = useTranslations("session");
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<TutorChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [capped, setCapped] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, open]);

  const userTurns = messages.filter((m) => m.role === "user").length;
  const atCap = capped || userTurns >= MAX_TURNS;

  async function onSend(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy || atCap || offline) return;
    setBusy(true);
    setError(null);
    const history = [...messages];
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setDraft("");
    try {
      const res = await tutorChat(token, {
        session_id: sessionId,
        item_id: itemId,
        message: text,
        locale: locale === "es" ? "es" : "en",
        history,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply },
      ]);
      if (res.capped) setCapped(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
      // Roll back optimistic user bubble on hard failure
      setMessages(history);
      setDraft(text);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)} aria-haspopup="dialog">
        <MessagesSquare className="h-4 w-4" aria-hidden />
        {t("tutorAsk")}
      </Button>

      <Sheet open={open} onOpenChange={setOpen} title={t("tutorLabel")} closeLabel={t("tutorHide")}>
        <div className="flex h-full flex-col gap-4">
          <div className="min-h-[12rem] flex-1 space-y-3" aria-live="polite">
            {messages.length === 0 && <ChatBubble role="assistant" label={t("tutorLabel")} text={t("tutorEmpty")} />}
            {messages.map((m, i) => (
              <ChatBubble
                key={`${i}-${m.role}`}
                role={m.role}
                label={m.role === "user" ? t("tutorYou") : t("tutorLabel")}
                text={m.content}
              />
            ))}
            {busy && <p className="animate-pulse text-xs text-slate-500">{t("tutorSending")}</p>}
            <div ref={bottomRef} />
          </div>

          {atCap ? (
            <p className="text-sm text-amber-200/90" role="status">
              {t("tutorCapped")}
            </p>
          ) : (
            <form onSubmit={onSend} className="flex gap-2">
              <input
                type="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={busy || offline}
                placeholder={t("tutorPlaceholder")}
                aria-label={t("tutorPlaceholder")}
                maxLength={500}
                className="min-h-12 min-w-0 flex-1 rounded-control border border-line-strong bg-background/60 px-3.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-neuro-indigo disabled:opacity-50"
              />
              <Button type="submit" size="icon" disabled={busy || offline || !draft.trim()} aria-label={t("tutorSend")}>
                <SendHorizontal className="h-4 w-4" aria-hidden />
              </Button>
            </form>
          )}

          {offline && <p className="text-xs text-slate-500">{t("tutorOffline")}</p>}
          {error && (
            <p className="text-sm text-neuro-alert" role="alert">
              {error}
            </p>
          )}
        </div>
      </Sheet>
    </>
  );
}

export function ChatBubble({ role, label, text }: { role: string; label: string; text: string }) {
  const mine = role === "user";
  return (
    <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed animate-fade-in",
          mine
            ? "rounded-br-md bg-neuro-indigo/25 text-slate-50"
            : "rounded-bl-md border border-line bg-surface-raised text-slate-200",
        )}
      >
        <p className="mb-0.5 font-mono text-micro uppercase tracking-wider text-slate-500">{label}</p>
        {text}
      </div>
    </div>
  );
}
