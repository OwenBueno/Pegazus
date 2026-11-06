"use client";

export function LocaleToggle({
  value,
  onChange,
  labelEn,
  labelEs,
}: {
  value: "en" | "es";
  onChange: (locale: "en" | "es") => void;
  labelEn: string;
  labelEs: string;
}) {
  return (
    <div
      role="group"
      className="grid grid-cols-2 gap-1 rounded-control border border-line bg-background/50 p-1"
    >
      {(
        [
          ["en", labelEn],
          ["es", labelEs],
        ] as const
      ).map(([code, label]) => {
        const active = value === code;
        return (
          <button
            key={code}
            type="button"
            onClick={() => onChange(code)}
            aria-pressed={active}
            className={`min-h-11 rounded-[calc(var(--radius-control)-4px)] text-sm font-medium transition ${
              active
                ? "bg-neuro-indigo text-white shadow-[0_6px_20px_-10px_rgb(99_102_241/0.9)]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
