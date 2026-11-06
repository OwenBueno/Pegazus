"use client";

import { useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { MathText } from "@/components/math/MathText";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { WidgetAction } from "@/lib/contracts/genui";

export function ConceptCard({
  title,
  body_md,
  latex,
  gateLabel,
  widgetId = "concept",
  onAction,
  eyebrow,
  hideGate,
}: {
  title: string;
  body_md: string;
  latex?: string;
  gateLabel?: string;
  widgetId?: string;
  onAction?: (a: WidgetAction) => void;
  /** Beat-type label row (icon + type) shown above the title. */
  eyebrow?: ReactNode;
  /** Parent renders its own Continue; skip the duplicate gate button. */
  hideGate?: boolean;
}) {
  const t = useTranslations("session");
  // Ack is tied to this content, so a new beat never starts with Continue stuck disabled.
  const contentKey = `${title}\u0000${body_md}\u0000${latex ?? ""}`;
  const [ackedFor, setAckedFor] = useState<string | null>(null);
  const acked = ackedFor === contentKey;

  return (
    <Card variant="glass" className="space-y-4">
      <div className="space-y-2">
        {eyebrow}
        <h2 className="font-display text-xl font-semibold leading-snug text-slate-50 sm:text-2xl">{title}</h2>
      </div>
      <div className="text-[15px] leading-7 [&_p]:text-slate-300">
        <PrimerMarkdown source={body_md} />
      </div>
      {latex ? (
        <div className="rounded-control border border-line bg-background/50 px-4 py-3">
          <MathText latex={latex} display className="text-slate-100" />
        </div>
      ) : null}
      {hideGate ? null : (
        <Button
          variant={acked ? "secondary" : "primary"}
          disabled={acked}
          onClick={() => {
            setAckedFor(contentKey);
            onAction?.({ widgetId, type: "CONCEPT_ACK", payload: {} });
          }}
        >
          {acked ? t("conceptGotIt") : gateLabel || t("conceptGotIt")}
        </Button>
      )}
    </Card>
  );
}
