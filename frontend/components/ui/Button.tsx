"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

const VARIANTS = {
  primary:
    "bg-neuro-indigo text-white shadow-[0_8px_24px_-12px_rgb(99_102_241/0.8)] hover:bg-neuro-indigo-soft active:scale-[0.98]",
  secondary:
    "border border-line-strong bg-surface-raised text-slate-100 hover:border-slate-500 hover:bg-surface-subtle",
  ghost: "text-slate-300 hover:bg-white/5 hover:text-white",
  danger: "bg-neuro-alert/90 text-white hover:bg-neuro-alert",
  success: "bg-neuro-teal/90 text-slate-950 hover:bg-neuro-teal",
} as const;

const SIZES = {
  md: "min-h-12 px-5 text-sm",
  sm: "min-h-10 px-3.5 text-sm",
  icon: "h-12 w-12 p-0",
} as const;

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
  loading?: boolean;
  block?: boolean;
};

export const buttonClass = (
  variant: keyof typeof VARIANTS = "primary",
  size: keyof typeof SIZES = "md",
  block = false,
) =>
  cn(
    "inline-flex select-none items-center justify-center gap-2 rounded-control font-medium transition-[background-color,border-color,color,transform] duration-150 disabled:pointer-events-none disabled:opacity-40",
    VARIANTS[variant],
    SIZES[size],
    block && "w-full",
  );

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, block, className, children, disabled, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonClass(variant, size, block), className)}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
});
