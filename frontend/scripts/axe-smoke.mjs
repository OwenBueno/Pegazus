/**
 * Axe smoke against a static fixture mirroring session/ask landmarks.
 * Live Next SSR pages are not JSDOM-safe (client bundles). Auth /session waived.
 * Run: npm run axe:smoke
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { JSDOM } from "jsdom";

const require = createRequire(import.meta.url);
const axeSource = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fixture = fs.readFileSync(path.join(__dirname, "axe-fixture.html"), "utf8");

const dom = new JSDOM(fixture, {
  url: "http://localhost:3000/en/axe-fixture",
  pretendToBeVisual: true,
  runScripts: "outside-only",
});
dom.window.eval(axeSource);
if (!dom.window.axe?.run) {
  console.error("FAIL: axe failed to load in JSDOM");
  process.exit(1);
}

const results = await dom.window.axe.run(dom.window.document, {
  runOnly: { type: "tag", values: ["wcag2a", "wcag2aa"] },
});
const serious = results.violations.filter(
  (v) => v.impact === "critical" || v.impact === "serious",
);
console.log(
  `fixture violations=${results.violations.length} serious/critical=${serious.length}`,
);
for (const v of serious) {
  console.log(`  - [${v.impact}] ${v.id}: ${v.help}`);
}
if (serious.length) {
  process.exit(1);
}
console.log("axe smoke OK");
