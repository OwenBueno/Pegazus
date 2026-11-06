import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // CommonJS config files (next.config.js) legitimately use require().
    files: ["*.config.js"],
    rules: { "@typescript-eslint/no-require-imports": "off" },
  },
  globalIgnores([".next/**", "node_modules/**", "out/**", "next-env.d.ts"]),
]);
