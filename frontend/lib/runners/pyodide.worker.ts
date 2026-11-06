import { blockNetwork, STDOUT_CAP, type RunResult, type Test } from "./js.worker";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs";

type PyProxy = { toJs: () => unknown; destroy: () => void } & ((...args: unknown[]) => PyProxy);
type Pyodide = {
  globals: { get: (k: string) => () => PyProxy };
  runPython: (code: string) => PyProxy;
  runPythonAsync: (code: string, opts: { globals: PyProxy }) => Promise<unknown>;
  setStdout: (o: { batched: (s: string) => void }) => void;
  setStderr: (o: { batched: (s: string) => void }) => void;
};

let ready: Promise<{ py: Pyodide; check: PyProxy }> | null = null;

async function load() {
  const { loadPyodide } = await import(/* webpackIgnore: true */ /* turbopackIgnore: true */ PYODIDE_URL);
  const py: Pyodide = await loadPyodide({ indexURL: PYODIDE_URL.slice(0, PYODIDE_URL.lastIndexOf("/") + 1) });
  blockNetwork();
  // `expect` / `want` are "" when the test doesn't check them; printed text is echoed to the output panel.
  const check = py.runPython(`
import contextlib, io
def _pgz_norm(s):
    return "\\n".join(l.rstrip() for l in s.strip().splitlines())
def _pgz_check(ns, call, expect, want):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = eval(call, ns)
    out = buf.getvalue()
    print(out, end="")
    ok = (not expect or repr(r) == expect or str(r) == expect) and (not want or _pgz_norm(out) == _pgz_norm(want))
    return [ok, out.rstrip() if want else repr(r)]
_pgz_check`);
  return { py, check };
}

const lastLine = (e: unknown) => (e instanceof Error ? e.message : String(e)).trim().split("\n").pop() ?? "Error";

async function run(code: string, tests: Test[]): Promise<RunResult> {
  const { py, check } = await (ready ??= load());
  let stdout = "";
  const write = (s: string) => {
    if (stdout.length < STDOUT_CAP) stdout = (stdout + s + "\n").slice(0, STDOUT_CAP);
  };
  py.setStdout({ batched: write });
  py.setStderr({ batched: write });

  const ns = py.globals.get("dict")();
  try {
    try {
      await py.runPythonAsync(code, { globals: ns });
    } catch (e) {
      return {
        passed: 0,
        total: tests.length,
        results: tests.map(() => ({ ok: false })),
        stdout: stdout || undefined,
        error: lastLine(e),
      };
    }
    const results = tests.map(({ call, expect, stdout: want }) => {
      try {
        const r = check(ns, call, expect ?? "", want ?? "");
        const [ok, got] = r.toJs() as [boolean, string];
        r.destroy();
        return { ok, got };
      } catch (e) {
        return { ok: false, error: lastLine(e) };
      }
    });
    return { passed: results.filter((r) => r.ok).length, total: tests.length, results, stdout: stdout || undefined };
  } finally {
    ns.destroy();
  }
}

const scope = globalThis as unknown as {
  onmessage: ((e: MessageEvent<{ code: string; tests: Test[] }>) => void) | null;
  postMessage: (m: RunResult) => void;
};
scope.onmessage = async (e) => {
  try {
    scope.postMessage(await run(e.data.code, e.data.tests));
  } catch (err) {
    ready = null;
    const tests = e.data.tests;
    scope.postMessage({ passed: 0, total: tests.length, results: tests.map(() => ({ ok: false })), error: lastLine(err) });
  }
};
