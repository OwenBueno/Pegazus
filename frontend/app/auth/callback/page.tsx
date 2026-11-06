import { redirect } from "next/navigation";

export default async function LegacyAuthCallback({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") qs.set(key, value);
    else if (Array.isArray(value)) value.forEach((v) => qs.append(key, v));
  }
  // Always land on locale callback (which sends users to OTP sign-in).
  const q = qs.toString();
  redirect(q ? `/en/auth/callback?${q}` : "/en/auth/callback");
}
