import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

const BADGE = {
  neutral: "border-line-strong bg-white/5 text-slate-300",
  indigo: "border-indigo-400/30 bg-indigo-500/10 text-indigo-200",
  teal: "border-teal-400/30 bg-teal-500/10 text-teal-200",
  amber: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  alert: "border-rose-400/30 bg-rose-500/10 text-rose-200",
} as const;

export function Badge({
  tone = "neutral",
  className,
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof BADGE }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        BADGE[tone],
        className,
      )}
      {...rest}
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        "animate-shimmer rounded-control bg-[linear-gradient(90deg,rgb(30_41_59/0.6)_0%,rgb(51_65_85/0.6)_50%,rgb(30_41_59/0.6)_100%)] bg-[length:200%_100%]",
        className,
      )}
    />
  );
}

export function ProgressBar({
  value,
  label,
  className,
  tone = "indigo",
}: {
  value: number;
  label: string;
  className?: string;
  tone?: "indigo" | "teal";
}) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-white/5", className)}
    >
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-500 ease-out",
          tone === "teal"
            ? "bg-neuro-teal"
            : "bg-[linear-gradient(90deg,var(--color-neuro-indigo),var(--color-neuro-indigo-soft))]",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function ProgressRing({
  value,
  label,
  size = 96,
  children,
}: {
  value: number;
  label: string;
  size?: number;
  children?: ReactNode;
}) {
  const v = Math.min(1, Math.max(0, value));
  const r = 42;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90" role="img" aria-label={label}>
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="8" className="stroke-white/5" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className="stroke-neuro-teal transition-[stroke-dashoffset] duration-700 ease-out"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - v)}
        />
      </svg>
      <div className="relative text-center">{children}</div>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-panel border border-dashed border-line-strong px-6 py-10 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/5 text-slate-300">{icon}</div>
      ) : null}
      <p className="font-display text-base font-semibold text-slate-100">{title}</p>
      {body ? <div className="max-w-sm text-sm text-slate-400">{body}</div> : null}
      {action}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("mb-6 flex flex-wrap items-end justify-between gap-4 sm:mb-8", className)}>
      <div className="min-w-0 space-y-2">
        {eyebrow ? (
          <p className="font-mono text-micro uppercase tracking-[0.16em] text-neuro-teal">{eyebrow}</p>
        ) : null}
        <h1 className="font-display text-title font-semibold tracking-tight text-slate-50 sm:text-[1.75rem]">
          {title}
        </h1>
        {description ? <p className="max-w-[60ch] text-[15px] leading-relaxed text-slate-400">{description}</p> : null}
      </div>
      {action}
    </header>
  );
}
