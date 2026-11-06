"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Reorder } from "motion/react";
import { ChevronDown, ChevronUp, GripVertical } from "lucide-react";
import { buttonClass } from "@/components/ui/Button";
import type { WidgetAction } from "@/lib/contracts/genui";

/** Graded server-side: emits {order} = displayed indices in the learner's order. */
export function OrderSteps({
  prompt,
  items,
  widgetId = "order",
  disabled = false,
  onAction,
}: {
  prompt?: string;
  items: string[];
  widgetId?: string;
  disabled?: boolean;
  onAction?: (a: WidgetAction) => void;
}) {
  const t = useTranslations("session");
  const [order, setOrder] = useState(() => items.map((_, i) => i));
  const [announce, setAnnounce] = useState("");

  function move(pos: number, delta: number) {
    const next = [...order];
    [next[pos], next[pos + delta]] = [next[pos + delta], next[pos]];
    setOrder(next);
    setAnnounce(t("movedTo", { item: items[order[pos]], pos: pos + delta + 1 }));
  }

  const iconBtn =
    "grid h-9 w-9 place-items-center rounded-control text-slate-300 hover:bg-surface-subtle hover:text-slate-100 disabled:opacity-30";

  return (
    <section className="space-y-3 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl">
      <p className="font-mono text-micro uppercase tracking-[0.14em] text-indigo-300">{t("orderSteps")}</p>
      {prompt ? <p className="text-sm text-slate-200">{prompt}</p> : null}
      <p className="text-xs text-slate-400">{t("orderHint")}</p>
      <Reorder.Group axis="y" values={order} onReorder={disabled ? () => {} : setOrder} className="space-y-2">
        {order.map((idx, pos) => (
          <Reorder.Item
            key={idx}
            value={idx}
            drag={disabled ? false : "y"}
            className="flex min-h-12 items-center gap-2 rounded-control border border-line-strong bg-surface-raised px-2 py-1.5 text-sm text-slate-200"
          >
            <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-slate-500" aria-hidden />
            <span className="w-5 shrink-0 font-mono text-xs text-slate-500">{pos + 1}.</span>
            <span className="min-w-0 flex-1">{items[idx]}</span>
            <button
              type="button"
              aria-label={t("moveUp", { item: items[idx] })}
              disabled={disabled || pos === 0}
              onClick={() => move(pos, -1)}
              className={iconBtn}
            >
              <ChevronUp className="h-4 w-4" aria-hidden />
            </button>
            <button
              type="button"
              aria-label={t("moveDown", { item: items[idx] })}
              disabled={disabled || pos === order.length - 1}
              onClick={() => move(pos, 1)}
              className={iconBtn}
            >
              <ChevronDown className="h-4 w-4" aria-hidden />
            </button>
          </Reorder.Item>
        ))}
      </Reorder.Group>
      <p aria-live="polite" className="sr-only">
        {announce}
      </p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction?.({ widgetId, type: "ANSWER", payload: { order } })}
        className={buttonClass("primary", "md", true)}
      >
        {t("checkOrder")}
      </button>
    </section>
  );
}
