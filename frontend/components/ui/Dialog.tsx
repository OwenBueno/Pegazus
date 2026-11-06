"use client";

import * as RD from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** Accessible modal (focus trap, Esc, aria-modal). `dismissible={false}` blocks Esc/outside close. */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  dismissible = true,
  closeLabel,
  className,
  hideTitle,
}: {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  dismissible?: boolean;
  closeLabel?: string;
  className?: string;
  hideTitle?: boolean;
}) {
  const block = (e: Event) => {
    if (!dismissible) e.preventDefault();
  };
  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-50 bg-background/80 backdrop-blur-md data-[state=open]:animate-fade-in" />
        <RD.Content
          onEscapeKeyDown={block}
          onPointerDownOutside={block}
          onInteractOutside={block}
          className={cn(
            "fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-panel border border-line-strong bg-surface p-6 shadow-sheet data-[state=open]:animate-fade-in",
            className,
          )}
        >
          <RD.Title className={cn("font-display text-xl font-semibold text-slate-50", hideTitle && "sr-only")}>
            {title}
          </RD.Title>
          {description ? (
            <RD.Description className="mt-1 text-sm text-slate-400">{description}</RD.Description>
          ) : (
            <RD.Description className="sr-only">{title}</RD.Description>
          )}
          <div className="mt-4">{children}</div>
          {dismissible && closeLabel ? (
            <RD.Close
              className="absolute right-3 top-3 grid h-10 w-10 place-items-center rounded-full text-slate-400 hover:bg-white/5 hover:text-white"
              aria-label={closeLabel}
            >
              <X className="h-4 w-4" aria-hidden />
            </RD.Close>
          ) : null}
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
