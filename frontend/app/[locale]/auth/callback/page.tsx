"use client";

import { useEffect } from "react";
import { useLocale } from "next-intl";

/**
 * Magic-link / PKCE callback is disabled for local Docker.
 * Auth is email OTP only — paste the code from Mailpit on the sign-in page.
 */
export default function AuthCallbackPage() {
  const locale = useLocale();

  useEffect(() => {
    const msg = encodeURIComponent(
      "Use the sign-in code from the email (Mailpit). Magic links are disabled locally.",
    );
    window.location.replace(`/${locale}/signin?error=${msg}`);
  }, [locale]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center justify-center px-4 text-slate-300">
      <p>Redirecting to sign-in…</p>
    </main>
  );
}
