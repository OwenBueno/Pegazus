/**
 * Tiny safe math expression compiler: recursive descent → closures. Never eval / new Function.
 *
 * expr    := term (("+" | "-") term)*
 * term    := unary (("*" | "/") unary)*
 * unary   := ("-" | "+") unary | power
 * power   := primary (("^" | "**") unary)?        right-assoc; -x^2 = -(x^2); 2^-1 ok
 * primary := number | ident | func "(" expr ")" | "(" expr ")"
 * number  := digits ["." digits] [exponent] | "." digits [exponent]
 * ident   := one of `vars` (shadows constants), else pi | E | e
 * No implicit multiplication, no commas / multi-arg calls.
 */

type Fn = (env: Record<string, number>) => number;

const CONSTANTS = new Map<string, number>([
  ["pi", Math.PI],
  ["E", Math.E],
  ["e", Math.E],
]);

const FUNCS = new Map<string, (v: number) => number>([
  ["sin", Math.sin],
  ["cos", Math.cos],
  ["tan", Math.tan],
  ["asin", Math.asin],
  ["acos", Math.acos],
  ["atan", Math.atan],
  ["sinh", Math.sinh],
  ["cosh", Math.cosh],
  ["tanh", Math.tanh],
  ["sqrt", Math.sqrt],
  ["abs", Math.abs],
  ["Abs", Math.abs],
  ["exp", Math.exp],
  ["log", Math.log],
  ["ln", Math.log],
]);

const MAX_LEN = 200;
const MAX_DEPTH = 50;
const TOKEN = /\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|[-+*/^()]))/y;

export function compile(expr: string, vars: string[]): Fn | null {
  if (typeof expr !== "string" || expr.length > MAX_LEN) return null;

  const tokens: { num?: number; id?: string; op?: string }[] = [];
  TOKEN.lastIndex = 0;
  while (TOKEN.lastIndex < expr.length) {
    if (/^\s*$/.test(expr.slice(TOKEN.lastIndex))) break;
    const m = TOKEN.exec(expr);
    if (!m) return null;
    tokens.push(m[1] !== undefined ? { num: Number(m[1]) } : m[2] !== undefined ? { id: m[2] } : { op: m[3] });
  }

  let pos = 0;
  let depth = 0;
  const fail = (): never => {
    throw new Error("parse");
  };
  const isOp = (op: string) => tokens[pos]?.op === op;
  const eat = (op: string) => (isOp(op) ? (pos++, true) : false);

  const parseExpr = (): Fn => {
    let left = parseTerm();
    while (isOp("+") || isOp("-")) {
      const op = tokens[pos++].op;
      const a = left;
      const b = parseTerm();
      left = op === "+" ? (env) => a(env) + b(env) : (env) => a(env) - b(env);
    }
    return left;
  };

  const parseTerm = (): Fn => {
    let left = parseUnary();
    while (isOp("*") || isOp("/")) {
      const op = tokens[pos++].op;
      const a = left;
      const b = parseUnary();
      left = op === "*" ? (env) => a(env) * b(env) : (env) => a(env) / b(env);
    }
    return left;
  };

  const parseUnary = (): Fn => {
    if (++depth > MAX_DEPTH) fail();
    let out: Fn;
    if (eat("-")) {
      const a = parseUnary();
      out = (env) => -a(env);
    } else if (eat("+")) {
      out = parseUnary();
    } else {
      out = parsePower();
    }
    depth--;
    return out;
  };

  const parsePower = (): Fn => {
    const base = parsePrimary();
    if (eat("^") || eat("**")) {
      const exp = parseUnary();
      return (env) => Math.pow(base(env), exp(env));
    }
    return base;
  };

  const parsePrimary = (): Fn => {
    const tok = tokens[pos++];
    if (!tok) return fail();
    if (tok.num !== undefined) {
      const n = tok.num;
      return () => n;
    }
    if (tok.id !== undefined) {
      const name = tok.id;
      const fn = FUNCS.get(name);
      if (fn && isOp("(")) {
        pos++;
        const arg = parseInner();
        return (env) => fn(arg(env));
      }
      if (vars.includes(name)) return (env) => (Object.hasOwn(env, name) ? env[name] : NaN);
      const c = CONSTANTS.get(name);
      if (c !== undefined) return () => c;
      return fail();
    }
    if (tok.op === "(") return parseInner();
    return fail();
  };

  const parseInner = (): Fn => {
    if (++depth > MAX_DEPTH) fail();
    const inner = parseExpr();
    if (!eat(")")) fail();
    depth--;
    return inner;
  };

  try {
    const root = parseExpr();
    return pos === tokens.length ? root : null;
  } catch {
    return null;
  }
}
