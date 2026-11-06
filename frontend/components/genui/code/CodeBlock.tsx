"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/primitives";

export type CodeLanguage = "python" | "javascript";

export const LANGUAGE_NAME: Record<CodeLanguage, string> = { python: "Python", javascript: "JavaScript" };

const KEYWORDS: Record<CodeLanguage, Set<string>> = {
  python: new Set(
    "and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield print len range".split(" "),
  ),
  javascript: new Set(
    "async await break case catch class const continue default delete do else export extends false finally for function if import in instanceof let new null of return switch this throw true try typeof undefined var void while yield console".split(" "),
  ),
};

const COMMENT = { python: String.raw`#.*`, javascript: String.raw`\/\/.*|\/\*[\s\S]*?\*\/` };
const STRING = {
  python: String.raw`"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'`,
  javascript: String.raw`\x60(?:\\[\s\S]|[^\x60\\])*\x60|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'`,
};
const TOKEN_CLASS = ["italic text-slate-400", "text-emerald-300", "text-amber-300"];

/**
 * ponytail: naive regex tokenizer (comments, strings, numbers, keywords); no regex literals, f-string
 * interpolation or nesting. Upgrade = shiki/CodeMirror if learners ask.
 */
export function highlight(code: string, language: CodeLanguage): ReactNode[] {
  const re = new RegExp(
    `(${COMMENT[language]})|(${STRING[language]})|(\\b\\d+(?:\\.\\d+)?\\b)|([A-Za-z_$][\\w$]*)`,
    "g",
  );
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of code.matchAll(re)) {
    const i = m.index;
    if (i > last) out.push(code.slice(last, i));
    const kind = m[1] ? 0 : m[2] ? 1 : m[3] ? 2 : KEYWORDS[language].has(m[0]) ? 3 : -1;
    out.push(
      kind < 0 ? m[0] : (
        <span key={i} className={TOKEN_CLASS[kind] ?? "text-indigo-300"}>
          {m[0]}
        </span>
      ),
    );
    last = i + m[0].length;
  }
  if (last < code.length) out.push(code.slice(last));
  return out;
}

export function CodeBlock({ language, code, caption }: { language: CodeLanguage; code: string; caption?: string }) {
  const t = useTranslations("session");
  return (
    <figure className="space-y-2">
      <Badge tone="indigo">{LANGUAGE_NAME[language]}</Badge>
      <pre
        role="region"
        tabIndex={0}
        aria-label={t("codeRegionLabel", { language: LANGUAGE_NAME[language] })}
        className="overflow-x-auto rounded-control border border-line bg-slate-950/70 p-4 font-mono text-sm leading-relaxed text-slate-200 focus-visible:outline-2 focus-visible:outline-indigo-400"
      >
        <code>{highlight(code, language)}</code>
      </pre>
      {caption ? <figcaption className="text-sm text-slate-400">{caption}</figcaption> : null}
    </figure>
  );
}
