"use client";

import { useEffect, useRef, type RefObject } from "react";
import "mathlive";

type MathFieldElement = HTMLElement & {
  value: string;
};

export function MathField({
  value,
  onChange,
  onSubmit,
  className = "",
  readOnly = false,
  placeholder,
  virtualKeyboardMode = "manual",
}: {
  value: string;
  onChange?: (latex: string) => void;
  onSubmit?: (latex: string) => void;
  className?: string;
  readOnly?: boolean;
  placeholder?: string;
  virtualKeyboardMode?: "manual" | "onfocus" | "off";
}) {
  const ref = useRef<MathFieldElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (el.value !== value) {
      el.value = value;
    }
  }, [value]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !onChange) return;
    const handler = () => onChange(el.value ?? "");
    el.addEventListener("input", handler);
    return () => el.removeEventListener("input", handler);
  }, [onChange]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !onSubmit) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onSubmit(el.value ?? "");
      }
    };
    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, [onSubmit]);

  return (
    <math-field
      ref={ref as RefObject<HTMLElement>}
      aria-label="Math input"
      className={className}
      read-only={readOnly ? true : undefined}
      placeholder={placeholder}
      virtual-keyboard-mode={virtualKeyboardMode}
      style={{
        display: "block",
        minHeight: "48px",
        width: "100%",
        fontSize: "1.125rem",
        padding: "0.5rem 0.75rem",
        borderRadius: "0.5rem",
        border: "1px solid #334155",
        background: "#0b1220",
        color: "#f1f5f9",
      }}
    />
  );
}
