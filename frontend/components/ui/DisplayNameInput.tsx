"use client";

import { inputClass } from "@/components/ui/FormField";

export function DisplayNameInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative">
      <input
        id={id}
        type="text"
        name="displayName"
        autoComplete="nickname"
        maxLength={80}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`${inputClass} min-h-14 pr-14 text-lg`}
      />
      <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 font-mono text-micro text-slate-500">
        {value.trim().length}/80
      </span>
    </div>
  );
}
