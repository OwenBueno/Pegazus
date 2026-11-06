import type { RunResult, Test } from "./js.worker";

export type { RunResult, Test, TestResult } from "./js.worker";
export const TIMEOUT = "TIMEOUT";

let pyWorker: Worker | null = null;
let pyQueue: Promise<unknown> = Promise.resolve();
let pyLoaded = false;

/** True once Pyodide (~10 MB) has loaded in this tab, so the UI can show a first-load hint. */
export const pythonLoaded = () => pyLoaded;

function exec(worker: Worker, code: string, tests: Test[], timeoutMs: number, onEnd: (ok: boolean) => void) {
  return new Promise<RunResult>((resolve) => {
    const finish = (r: RunResult, ok: boolean) => {
      clearTimeout(timer);
      worker.onmessage = worker.onerror = null;
      onEnd(ok);
      resolve(r);
    };
    const fail = (error: string) =>
      finish({ passed: 0, total: tests.length, results: tests.map(() => ({ ok: false })), error }, false);
    // Terminating the worker is the only way to stop an infinite loop.
    const timer = setTimeout(() => fail(TIMEOUT), timeoutMs);
    worker.onmessage = (e: MessageEvent<RunResult>) => finish(e.data, true);
    worker.onerror = (e) => fail(e.message || "Worker error");
    worker.postMessage({ code, tests });
  });
}

export function runTests(
  language: "python" | "javascript",
  code: string,
  tests: Test[],
  // The first Python run also downloads Pyodide (~10 MB), so it gets a longer window.
  timeoutMs = language === "python" ? (pyLoaded ? 10_000 : 60_000) : 5_000,
): Promise<RunResult> {
  if (language === "javascript") {
    const w = new Worker(new URL("./js.worker.ts", import.meta.url), { type: "module", name: "js-runner" });
    return exec(w, code, tests, timeoutMs, () => w.terminate());
  }
  // Python worker stays alive between runs (Pyodide load is slow); runs are serialized, and a
  // timeout/crash terminates it so the next run starts fresh.
  const run = pyQueue.then(() => {
    const w = (pyWorker ??= new Worker(new URL("./pyodide.worker.ts", import.meta.url), { type: "module" }));
    return exec(w, code, tests, timeoutMs, (ok) => {
      if (ok) pyLoaded = true;
      else {
        w.terminate();
        pyWorker = null;
      }
    });
  });
  pyQueue = run.catch(() => {});
  return run;
}
