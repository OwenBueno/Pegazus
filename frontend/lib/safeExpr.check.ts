// Run: node lib/safeExpr.check.ts
import assert from "node:assert/strict";
import { compile } from "./safeExpr.ts";

const run = (expr: string, env: Record<string, number> = {}, vars = Object.keys(env)) => compile(expr, vars)?.(env);
const close = (a: number | undefined, b: number) => assert.ok(a !== undefined && Math.abs(a - b) < 1e-9, `${a} ≈ ${b}`);

assert.equal(run("1 + 2 * 3"), 7);
assert.equal(run("(1 + 2) * 3"), 9);
assert.equal(run("8 / 4 / 2"), 1);
assert.equal(run("2 ^ 3 ^ 2"), 512);
assert.equal(run("2 ** 3 ** 2"), 512);
assert.equal(run("-x^2", { x: 3 }), -9);
assert.equal(run("2^-1"), 0.5);
assert.equal(run("1.5e-3 * 2e3"), 3);
assert.equal(run(".5 + 1."), 1.5);
close(run("sin(pi / 2) + ln(e) + Abs(-2) + sqrt(16)"), 8);
close(run("a * x + b", { a: 2, b: 1, x: 3 }), 7);
assert.equal(run("e", { e: 5 }), 5);
assert.ok(Number.isNaN(run("sqrt(-1)") as number));

for (const bad of ["y + 1", "foo(1)", "constructor", "__proto__", "toString", "2x", "2(3)", "1 +", "(1", "1)", "1 $ 2", "sin 1", "sin", "x.y", "max(1, 2)", "", "a".repeat(201), "(".repeat(60) + "1" + ")".repeat(60)]) {
  assert.equal(compile(bad, ["x"]), null, `expected null for ${JSON.stringify(bad.slice(0, 40))}`);
}

console.log("safeExpr ok");
