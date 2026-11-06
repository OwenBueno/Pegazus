import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = HTMLAttributes<HTMLElement> & {
  as?: "section" | "div" | "article" | "aside" | "figure";
  variant?: "solid" | "glass" | "raised";
  interactive?: boolean;
  padded?: boolean;
};

const VARIANT = {
  solid: "bg-surface/85 border-line",
  glass: "bg-surface-glass border-line backdrop-blur-xl",
  raised: "bg-surface-raised border-line-strong",
} as const;

export function Card({
  as: Tag = "section",
  variant = "solid",
  interactive,
  padded = true,
  className,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cn(
        "rounded-panel border",
        VARIANT[variant],
        padded && "p-5 sm:p-6",
        interactive &&
          "transition-[border-color,transform,background-color] duration-150 hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-subtle/60",
        className,
      )}
      {...rest}
    />
  );
}

/** Micro-label eyebrow + optional title/action row used at the top of cards and widgets. */
export function CardHeader({
  icon,
  label,
  title,
  action,
  tone = "text-slate-400",
  className,
}: {
  icon?: ReactNode;
  label?: string;
  title?: ReactNode;
  action?: ReactNode;
  tone?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-start justify-between gap-3", className)}>
      <div className="min-w-0 space-y-1">
        {label ? (
          <p className={cn("flex items-center gap-1.5 font-mono text-micro uppercase tracking-[0.14em]", tone)}>
            {icon}
            {label}
          </p>
        ) : null}
        {title ? <h2 className="font-display text-lg font-semibold text-slate-50">{title}</h2> : null}
      </div>
      {action}
    </div>
  );
}
