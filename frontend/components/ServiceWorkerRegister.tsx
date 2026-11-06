"use client";

import { useEffect } from "react";

/** Registers /sw.js once on the client. */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* ignore */
    });
  }, []);
  return null;
}
