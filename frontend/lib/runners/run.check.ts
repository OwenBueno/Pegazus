// Run: node lib/runners/run.check.ts (Node >= 23.6 strips types).
import assert from "node:assert/strict";
import { Worker } from "node:worker_threads";
import { jsPass, samePrinted, type RunResult, type Test } from "./js.worker.ts";

assert.ok(jsPass(5, "5"));
assert.ok(jsPass("hi", '"hi"'));
assert.ok(jsPass("hi", "hi"));
assert.ok(jsPass([1, 2], "[1,2]"));
assert.ok(jsPass({ a: 1 }, '{"a":1}'));
assert.ok(jsPass(true, "true"));
assert.ok(jsPass(undefined, "undefined"));
assert.ok(!jsPass(6, "5"));
assert.ok(!jsPass([1, 2], "[1, 2]"));

const tests: Test[] = [
  { call: "add(2, 3)", expect: "5" },
  { call: "add(-1, 1)", expect: "0" },
];

// Runs the real worker module in a Node worker thread; terminate() on timeout mirrors run.ts.
function runInThread(code: string, timeoutMs = 2000, cases: Test[] = tests): Promise<RunResult | "TIMEOUT"> {
  const url = new URL("./js.worker.ts", import.meta.url).href;
  const w = new Worker(
    `import(${JSON.stringify(url)}).then(async (m) => require("node:worker_threads").parentPort.postMessage(await m.runJs(...require("node:worker_threads").workerData)))`,
    { eval: true, workerData: [code, cases] },
  );
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => w.terminate().then(() => resolve("TIMEOUT")), timeoutMs);
    w.once("message", (r) => (clearTimeout(timer), w.terminate(), resolve(r)));
    w.once("error", (e) => (clearTimeout(timer), reject(e)));
  });
}

const good = await runInThread("function add(a, b) { console.log('adding'); return a + b; }");
assert.ok(good !== "TIMEOUT");
assert.equal(good.passed, 2);
assert.equal(good.stdout, "adding\nadding\n");

const wrong = await runInThread("const add = (a, b) => a - b;");
assert.ok(wrong !== "TIMEOUT");
assert.equal(wrong.passed, 0);
assert.equal(wrong.results[0].got, "-1");

const broken = await runInThread("function add(a, b) { return a + ; }");
assert.ok(broken !== "TIMEOUT" && broken.error?.startsWith("SyntaxError"));

const sandboxed = await runInThread("const add = () => typeof fetch;");
assert.ok(sandboxed !== "TIMEOUT");
assert.equal(sandboxed.results[0].got, '"undefined"');

assert.equal(await runInThread("while (true) {}", 500), "TIMEOUT");

assert.ok(samePrinted("3\n2 \n1\n", "3\n2\n1"));
assert.ok(!samePrinted("", "3"));
const printed = await runInThread("function main() { console.log(3); console.log('go'); }", 2000, [
  { call: "main()", stdout: "3\ngo" },
]);
assert.ok(printed !== "TIMEOUT" && printed.passed === 1 && printed.results[0].got === "3\ngo");
const stub = await runInThread("function main() {}", 2000, [{ call: "main()", stdout: "3\ngo" }]);
assert.ok(stub !== "TIMEOUT" && stub.passed === 0);

console.log("run.check: ok");
