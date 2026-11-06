"use client";

import * as RD from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useSyncExternalStore, type ReactNode } from "react";
import { Drawer } from "vaul";

const QUERY = "(min-width: 768px)";

function useDesktop(): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(QUERY);
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia(QUERY).matches,
    () => true,
  );
}

/** Bottom drawer on mobile, right side panel on desktop. Same props either way. */
export function Sheet({
  open,
  onOpenChange,
  title,
  closeLabel,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  closeLabel: string;
  children: ReactNode;
}) {
  const desktop = useDesktop();

  if (!desktop) {
    return (
      <Drawer.Root open={open} onOpenChange={onOpenChange}>
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-50 bg-background/70 backdrop-blur-sm" />
          <Drawer.Content className="pb-safe fixed inset-x-0 bottom-0 z-50 flex max-h-[88dvh] flex-col rounded-t-[1.5rem] border-t border-line-strong bg-surface shadow-sheet outline-none">
            <div className="mx-auto mt-3 h-1.5 w-10 shrink-0 rounded-full bg-slate-600" aria-hidden />
            <Drawer.Title className="px-5 pt-3 font-display text-base font-semibold text-slate-50">
              {title}
            </Drawer.Title>
            <Drawer.Description className="sr-only">{title}</Drawer.Description>
            <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-3">{children}</div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    );
  }

  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-50 bg-background/50 backdrop-blur-[2px] data-[state=open]:animate-fade-in" />
        <RD.Content className="fixed inset-y-3 right-3 z-50 flex w-[min(28rem,calc(100vw-1.5rem))] flex-col rounded-panel border border-line-strong bg-surface shadow-sheet outline-none data-[state=open]:animate-fade-in">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <RD.Title className="font-display text-base font-semibold text-slate-50">{title}</RD.Title>
            <RD.Close
              aria-label={closeLabel}
              className="grid h-10 w-10 place-items-center rounded-full text-slate-400 hover:bg-white/5 hover:text-white"
            >
              <X className="h-4 w-4" aria-hidden />
            </RD.Close>
          </div>
          <RD.Description className="sr-only">{title}</RD.Description>
          <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
