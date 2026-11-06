"use client";

import { useEffect } from "react";
import { MotionConfig } from "motion/react";
import { Toaster } from "sonner";
import * as Tooltip from "@radix-ui/react-tooltip";

export function Providers({ locale, children }: { locale: string; children: React.ReactNode }) {
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
      <Tooltip.Provider delayDuration={300}>{children}</Tooltip.Provider>
      <Toaster
        theme="dark"
        position="top-center"
        toastOptions={{
          className: "!bg-surface !border !border-white/10 !text-slate-100 !rounded-xl",
        }}
      />
    </MotionConfig>
  );
}
