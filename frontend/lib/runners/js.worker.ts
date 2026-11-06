/** `expect`: return value (repr / JSON); `stdout`: exact printed text of the call. At least one is set. */
export type Test = { call: string; expect?: string; stdout?: string };
export type TestResult = { ok: boolean; got?: string; error?: string };
export type RunResult = { passed: number; total: number; results: TestResult[]; stdout?: string; error?: string };

export const STDOUT_CAP = 2048;
const BLOCKED = [
  "fetch",
  "XMLHttpRequest",
  "WebSocket",
  "EventSource",
  "importScripts",
  "indexedDB",
  "caches",
  "BroadcastChannel",
  "Worker",
  "SharedWorker",
];

export function jsPass(result: unknown, expect: string): boolean {
  let json: string | undefined;
  try {
    json = JSON.stringify(result);
  } catch {}
  return json === expect || String(result) === expect;
}

/** Printed output vs expected, ignoring trailing whitespace per line and at the ends. */
export const samePrinted = (got: string, want: string) => {
  const norm = (s: string) => s.trim().split(/\r?\n/).map((l) => l.trimEnd()).join("\n");
  return norm(got) === norm(want);
};

export function show(v: unknown): string {
  if (typeof v === "string") return JSON.stringify(v);
  try {
    return JSON.stringify(v) ?? String(v);
  } catch {
    return String(v);
  }
}

/** Also used by the Python worker once Pyodide is loaded (its `js` module can reach worker globals). */
export function blockNetwork() {
  for (const k of BLOCKED) {
    try {
      Object.defineProperty(globalThis, k, { value: undefined, writable: false, configurable: false });
    } catch {}
  }
}

const errText = (e: unknown) => (e instanceof Error ? `${e.name}: ${e.message}` : String(e));

/**
 * ponytail: best-effort sandbox. Runs only inside a dedicated, terminable Worker (no DOM, no cookies) with
 * network/storage globals removed; `import()` inside learner code can't be blocked here.
 * Upgrade = server-side sandbox (Doc 10 R2).
 */
export async function runJs(code: string, tests: Test[]): Promise<RunResult> {
  blockNetwork();
  let stdout = "";
  let callOut = "";
  const log = (...args: unknown[]) => {
    const line = args.map((a) => (typeof a === "string" ? a : show(a))).join(" ") + "\n";
    if (stdout.length < STDOUT_CAP) stdout = (stdout + line).slice(0, STDOUT_CAP);
    if (callOut.length < STDOUT_CAP) callOut += line;
  };
  Object.assign(console, { log, info: log, warn: log, error: log, debug: log });

  const fail = (error: string): RunResult => ({
    passed: 0,
    total: tests.length,
    results: tests.map(() => ({ ok: false })),
    stdout: stdout || undefined,
    error,
  });

  let evaluate: (expr: string) => unknown;
  try {
    // `new Function` + direct eval is acceptable ONLY because this runs in the isolated worker above.
    // The returned closure evaluates each test call in the same scope as the learner's declarations.
    evaluate = new Function(`${code}\n;return (__pgz_expr) => eval(__pgz_expr);`)();
  } catch (e) {
    return fail(errText(e));
  }

  const results: TestResult[] = [];
  for (const { call, expect, stdout: want } of tests) {
    try {
      callOut = "";
      const got = await evaluate(call);
      const ok = (!expect || jsPass(got, expect)) && (!want || samePrinted(callOut, want));
      results.push({ ok, got: want ? callOut.trimEnd() : show(got) });
    } catch (e) {
      results.push({ ok: false, error: errText(e) });
    }
  }
  return { passed: results.filter((r) => r.ok).length, total: tests.length, results, stdout: stdout || undefined };
}

const scope = globalThis as unknown as {
  name?: string;
  onmessage: ((e: MessageEvent<{ code: string; tests: Test[] }>) => void) | null;
  postMessage: (m: RunResult) => void;
};
if (scope.name === "js-runner") {
  scope.onmessage = async (e) => scope.postMessage(await runJs(e.data.code, e.data.tests));
}
