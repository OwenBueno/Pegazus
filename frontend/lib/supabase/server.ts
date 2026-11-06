import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { AUTH_COOKIE } from "@/lib/supabase/constants";

/** Same hostname as the browser client so cookie keys match (set in compose). */
export function supabaseUrl() {
  return (
    process.env.INTERNAL_SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL!
  );
}

export function appOrigin() {
  return process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
}

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    supabaseUrl(),
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: { name: AUTH_COOKIE },
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            /* Server Component — middleware will refresh */
          }
        },
      },
    },
  );
}
