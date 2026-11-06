"use client";

import { useMemo, useState } from "react";
import { inputClass } from "@/components/ui/FormField";
import { COUNTRIES, countryLabel } from "@/lib/countries";

export function CountrySelect({
  value,
  onChange,
  locale,
  searchPlaceholder,
  featuredLabel,
}: {
  value: string | null;
  onChange: (code: string) => void;
  locale: string;
  searchPlaceholder: string;
  featuredLabel: string;
}) {
  const [query, setQuery] = useState("");
  const featured = COUNTRIES.find((c) => c.code === "MX")!;
  const others = useMemo(() => {
    const q = query.trim().toLowerCase();
    return COUNTRIES.filter((c) => c.code !== "MX").filter((c) => {
      if (!q) return true;
      const label = locale.startsWith("es") ? c.nameEs : c.nameEn;
      return label.toLowerCase().includes(q) || c.code.toLowerCase().includes(q);
    });
  }, [query, locale]);

  function chip(code: string, label: string, featuredChip = false) {
    const selected = value === code;
    return (
      <button
        key={code}
        type="button"
        onClick={() => onChange(code)}
        aria-pressed={selected}
        className={`min-h-12 rounded-control px-3 py-1.5 text-left text-sm transition ${
          selected
            ? "bg-neuro-indigo/20 text-slate-50 ring-2 ring-indigo-400/60"
            : featuredChip
              ? "border border-teal-400/30 bg-teal-500/10 text-slate-100 hover:border-teal-400/60"
              : "border border-line bg-surface-raised text-slate-200 hover:border-line-strong"
        }`}
      >
        <span className="block font-medium">{label}</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
          {code === "XX" ? "—" : code}
        </span>
      </button>
    );
  }

  return (
    <div className="space-y-3">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={searchPlaceholder}
        aria-label={searchPlaceholder}
        className={inputClass}
        autoComplete="off"
      />

      {!query && (
        <div>
          <p className="mb-2 text-xs font-mono uppercase tracking-wider text-slate-500">
            {featuredLabel}
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {chip(featured.code, countryLabel(featured.code, locale), true)}
          </div>
        </div>
      )}

      <div className="grid max-h-56 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
        {others.map((c) => chip(c.code, countryLabel(c.code, locale)))}
      </div>
    </div>
  );
}
