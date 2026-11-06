"use client";

import { useEffect, type Dispatch, type SetStateAction } from "react";
import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { AUTH_COOKIE } from "@/lib/supabase/constants";

let browserClient: SupabaseClient | null = null;

/** Browser client — PKCE verifier stored in cookies (same name as server/middleware). */
export function createClient() {
  if (browserClient) return browserClient;
  browserClient = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: { name: AUTH_COOKIE },
      auth: {
        flowType: "pkce",
        detectSessionInUrl: false,
        persistSession: true,
        autoRefreshToken: true,
      },
    },
  );
  return browserClient;
}

/**
 * Keeps a page's stored access token current: Supabase rotates it about hourly (TOKEN_REFRESHED),
 * so a long session would otherwise submit with an expired token. Only replaces a token the page
 * already accepted, so its sign-in / profile gating still decides when the first one lands.
 */
export function useTokenRefresh(setToken: Dispatch<SetStateAction<string | null>>) {
  useEffect(() => {
    const { data } = createClient().auth.onAuthStateChange((_event, session) => {
      const next = session?.access_token;
      if (next) setToken((cur) => (cur && cur !== next ? next : cur));
    });
    return () => data.subscription.unsubscribe();
  }, [setToken]);
}
