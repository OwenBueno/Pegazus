"""Expand algebra seed: primers, ~12 nodes, item floors. Run from repo via Docker."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_CANDIDATES = [
    Path("/supabase/seed/algebra_p0lite.json"),
    ROOT / "supabase" / "seed" / "algebra_p0lite.json",
]
SEED = next((p for p in _CANDIDATES if p.parent.is_dir()), _CANDIDATES[-1])

PRIMERS = {
    "math.algebra.one-step-equations": (
        "## One-step equations\n\n"
        "An equation says two expressions are equal. To solve "
        "`x + a = b` or `ax = b`, undo the single operation with its inverse "
        "on **both** sides so the equation stays balanced.\n\n"
        "**When to use:** isolate `x` in one move. "
        "**Outline:** identify the operation → apply inverse → check by substitution."
    ),
    "math.algebra.two-step-equations": (
        "## Two-step equations\n\n"
        "Forms like `ax + b = c` need a deliberate order: undo addition/subtraction "
        "first, then undo multiplication/division.\n\n"
        "**Why order matters:** clearing the constant first leaves a one-step multiply/divide."
    ),
    "math.algebra.variables-both-sides": (
        "## Variables on both sides\n\n"
        "When `x` appears on both sides, collect variable terms on one side and "
        "constants on the other, then finish as a one- or two-step equation.\n\n"
        "**Outline:** subtract (or add) a variable term → simplify → isolate `x`."
    ),
    "math.algebra.linear-inequalities": (
        "## Linear inequalities\n\n"
        "Inequalities use `<`, `>`, `≤`, `≥`. Solving steps mirror equations, "
        "**except** multiplying or dividing by a negative flips the inequality.\n\n"
        "**Check:** pick a test value from your solution set."
    ),
    "math.algebra.simple-quadratics": (
        "## Simple quadratics\n\n"
        "Equations like `x² = k` or `(x − h)² = k` are solved with square roots. "
        "Remember both positive and negative roots when they exist.\n\n"
        "**Outline:** isolate the square → take ± square root → solve for `x`."
    ),
    "math.algebra.combining-like-terms": (
        "## Combining like terms\n\n"
        "Like terms share the same variable power. Combine coefficients only; "
        "unlike terms stay separate.\n\n"
        "**Outline:** group like terms → add/subtract coefficients → rewrite cleanly."
    ),
    "math.algebra.distributing": (
        "## Distributive property\n\n"
        "`a(b + c) = ab + ac`. Expand carefully with signs, then combine like terms "
        "if needed.\n\n"
        "**Outline:** multiply each term inside → watch negatives → simplify."
    ),
    "math.algebra.clearing-fractions": (
        "## Clearing fractions\n\n"
        "Multiply every term by a common denominator to clear fractions, then solve "
        "the resulting integer equation.\n\n"
        "**Outline:** find LCD → multiply through → solve as usual."
    ),
    "math.algebra.compound-inequalities": (
        "## Compound inequalities\n\n"
        "Forms like `a < x < b` are two inequalities at once. Apply the same "
        "operation to all three parts.\n\n"
        "**Outline:** treat as a chain → isolate `x` in the middle → graph if useful."
    ),
    "math.algebra.absolute-value-eq": (
        "## Absolute value equations\n\n"
        "`|A| = k` (k ≥ 0) splits into `A = k` or `A = −k`. Solve each case "
        "and check extraneous results.\n\n"
        "**Outline:** isolate absolute value → split cases → solve → verify."
    ),
    "math.algebra.difference-of-squares": (
        "## Difference of squares\n\n"
        "`a² − b² = (a − b)(a + b)`. Factor first when solving equations set to zero.\n\n"
        "**Outline:** recognize pattern → factor → zero-product property."
    ),
    "math.algebra.graphing-linear": (
        "## Graphing linear forms\n\n"
        "`y = mx + b` is a line: slope `m`, intercept `b`. Plotting helps check "
        "solutions of related equations.\n\n"
        "**Outline:** identify slope/intercept → plot two points → connect."
    ),
}

NEW_NODES = [
    {
        "id": "11111111-1111-1111-1111-111111111106",
        "slug": "math.algebra.combining-like-terms",
        "title": "Combining like terms",
        "description": "Add and subtract like terms to simplify algebraic expressions.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "ax + bx = (a+b)x",
    },
    {
        "id": "11111111-1111-1111-1111-111111111107",
        "slug": "math.algebra.distributing",
        "title": "Distributive property",
        "description": "Expand a(b+c) and simplify resulting expressions.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "a(b+c)=ab+ac",
    },
    {
        "id": "11111111-1111-1111-1111-111111111108",
        "slug": "math.algebra.clearing-fractions",
        "title": "Clearing fractions in equations",
        "description": "Multiply through by an LCD to clear denominators before solving.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "\\frac{x}{a}+\\frac{x}{b}=c",
    },
    {
        "id": "11111111-1111-1111-1111-111111111109",
        "slug": "math.algebra.compound-inequalities",
        "title": "Compound inequalities",
        "description": "Solve chained inequalities a < x < b with consistent operations.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "a < x < b",
    },
    {
        "id": "11111111-1111-1111-1111-111111111110",
        "slug": "math.algebra.absolute-value-eq",
        "title": "Absolute value equations",
        "description": "Solve |A| = k by splitting into two linear cases.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "|x| = k",
    },
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "slug": "math.algebra.difference-of-squares",
        "title": "Difference of squares",
        "description": "Factor a^2 - b^2 and solve related equations.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "a^{2}-b^{2}=(a-b)(a+b)",
    },
    {
        "id": "11111111-1111-1111-1111-111111111112",
        "slug": "math.algebra.graphing-linear",
        "title": "Graphing linear equations",
        "description": "Interpret and plot y = mx + b on the coordinate plane.",
        "node_type": "SKILL",
        "domain": "MATHEMATICS",
        "canonical_equation_latex": "y = mx + b",
    },
]

NEW_EDGES = [
    ("11111111-1111-1111-1111-111111111101", "11111111-1111-1111-1111-111111111106"),
    ("11111111-1111-1111-1111-111111111106", "11111111-1111-1111-1111-111111111107"),
    ("11111111-1111-1111-1111-111111111107", "11111111-1111-1111-1111-111111111102"),
    ("11111111-1111-1111-1111-111111111102", "11111111-1111-1111-1111-111111111108"),
    ("11111111-1111-1111-1111-111111111104", "11111111-1111-1111-1111-111111111109"),
    ("11111111-1111-1111-1111-111111111103", "11111111-1111-1111-1111-111111111110"),
    ("11111111-1111-1111-1111-111111111105", "11111111-1111-1111-1111-111111111111"),
    ("11111111-1111-1111-1111-111111111102", "11111111-1111-1111-1111-111111111112"),
]

# Extra items for original 5 nodes (bring to 8 each) — ids 206-208, 216-218, etc.
EXTRA_CORE = [
    # node 101
    ("22222222-2222-2222-2222-222222222206", "11111111-1111-1111-1111-111111111101",
     "x + 9 = 15", 0.2,
     [("x + 9 = 15", "Eq(x + 9, 15)", "GIVEN"), ("x = 6", "Eq(x, 6)", "SUBTRACT_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222207", "11111111-1111-1111-1111-111111111101",
     "6x = 42", 0.25,
     [("6x = 42", "Eq(6*x, 42)", "GIVEN"), ("x = 7", "Eq(x, 7)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222208", "11111111-1111-1111-1111-111111111101",
     "x - 11 = 4", 0.2,
     [("x - 11 = 4", "Eq(x - 11, 4)", "GIVEN"), ("x = 15", "Eq(x, 15)", "ADD_CONSTANT")]),
    # node 102
    ("22222222-2222-2222-2222-222222222216", "11111111-1111-1111-1111-111111111102",
     "2x + 5 = 17", 0.35,
     [("2x + 5 = 17", "Eq(2*x + 5, 17)", "GIVEN"), ("2x = 12", "Eq(2*x, 12)", "SUBTRACT_CONSTANT"),
      ("x = 6", "Eq(x, 6)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222217", "11111111-1111-1111-1111-111111111102",
     "3x - 4 = 11", 0.35,
     [("3x - 4 = 11", "Eq(3*x - 4, 11)", "GIVEN"), ("3x = 15", "Eq(3*x, 15)", "ADD_CONSTANT"),
      ("x = 5", "Eq(x, 5)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222218", "11111111-1111-1111-1111-111111111102",
     "\\frac{x}{3} - 2 = 1", 0.45,
     [("\\frac{x}{3} - 2 = 1", "Eq(x/3 - 2, 1)", "GIVEN"), ("\\frac{x}{3} = 3", "Eq(x/3, 3)", "ADD_CONSTANT"),
      ("x = 9", "Eq(x, 9)", "MULTIPLY_CONSTANT")]),
    # node 103
    ("22222222-2222-2222-2222-222222222226", "11111111-1111-1111-1111-111111111103",
     "2x + 5 = x + 9", 0.5,
     [("2x + 5 = x + 9", "Eq(2*x + 5, x + 9)", "GIVEN"), ("x + 5 = 9", "Eq(x + 5, 9)", "SUBTRACT_VARIABLE_TERM"),
      ("x = 4", "Eq(x, 4)", "SUBTRACT_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222227", "11111111-1111-1111-1111-111111111103",
     "8x - 3 = 5x + 9", 0.55,
     [("8x - 3 = 5x + 9", "Eq(8*x - 3, 5*x + 9)", "GIVEN"), ("3x - 3 = 9", "Eq(3*x - 3, 9)", "SUBTRACT_VARIABLE_TERM"),
      ("3x = 12", "Eq(3*x, 12)", "ADD_CONSTANT"), ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222228", "11111111-1111-1111-1111-111111111103",
     "9x = 4x + 20", 0.45,
     [("9x = 4x + 20", "Eq(9*x, 4*x + 20)", "GIVEN"), ("5x = 20", "Eq(5*x, 20)", "SUBTRACT_VARIABLE_TERM"),
      ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    # node 104
    ("22222222-2222-2222-2222-222222222236", "11111111-1111-1111-1111-111111111104",
     "4x + 3 > 11", 0.4,
     [("4x + 3 > 11", "4*x + 3 > 11", "GIVEN"), ("4x > 8", "4*x > 8", "SUBTRACT_CONSTANT"),
      ("x > 2", "x > 2", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222237", "11111111-1111-1111-1111-111111111104",
     "-4x \\leq 12", 0.55,
     [("-4x \\leq 12", "-4*x <= 12", "GIVEN"), ("x \\geq -3", "x >= -3", "DIVIDE_NEGATIVE")]),
    ("22222222-2222-2222-2222-222222222238", "11111111-1111-1111-1111-111111111104",
     "x + 2 < 10", 0.3,
     [("x + 2 < 10", "x + 2 < 10", "GIVEN"), ("x < 8", "x < 8", "SUBTRACT_CONSTANT")]),
    # node 105
    ("22222222-2222-2222-2222-222222222246", "11111111-1111-1111-1111-111111111105",
     "x^{2} = 36", 0.5,
     [("x^{2} = 36", "Eq(x**2, 36)", "GIVEN"),
      ("x = \\pm 6", "Or(Eq(x, 6), Eq(x, -6))", "SQUARE_ROOT")]),
    ("22222222-2222-2222-2222-222222222247", "11111111-1111-1111-1111-111111111105",
     "(x - 1)^{2} = 16", 0.6,
     [("(x - 1)^{2} = 16", "Eq((x - 1)**2, 16)", "GIVEN"),
      ("x - 1 = \\pm 4", "Or(Eq(x - 1, 4), Eq(x - 1, -4))", "SQUARE_ROOT"),
      ("x = 5 \\text{ or } x = -3", "Or(Eq(x, 5), Eq(x, -3))", "ADD_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222248", "11111111-1111-1111-1111-111111111105",
     "x^{2} - 9 = 0", 0.55,
     [("x^{2} - 9 = 0", "Eq(x**2 - 9, 0)", "GIVEN"), ("x^{2} = 9", "Eq(x**2, 9)", "ADD_CONSTANT"),
      ("x = \\pm 3", "Or(Eq(x, 3), Eq(x, -3))", "SQUARE_ROOT")]),
]

NEW_ITEMS = [
    # combining like terms — grade as equations after simplify
    ("22222222-2222-2222-2222-222222222251", "11111111-1111-1111-1111-111111111106",
     "2x + 3x = 20", 0.3,
     [("2x + 3x = 20", "Eq(2*x + 3*x, 20)", "GIVEN"), ("5x = 20", "Eq(5*x, 20)", "COMBINE"),
      ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222252", "11111111-1111-1111-1111-111111111106",
     "7x - 2x = 15", 0.3,
     [("7x - 2x = 15", "Eq(7*x - 2*x, 15)", "GIVEN"), ("5x = 15", "Eq(5*x, 15)", "COMBINE"),
      ("x = 3", "Eq(x, 3)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222253", "11111111-1111-1111-1111-111111111106",
     "4x + x = 25", 0.3,
     [("4x + x = 25", "Eq(4*x + x, 25)", "GIVEN"), ("5x = 25", "Eq(5*x, 25)", "COMBINE"),
      ("x = 5", "Eq(x, 5)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222254", "11111111-1111-1111-1111-111111111106",
     "9x - 4x = 30", 0.3,
     [("9x - 4x = 30", "Eq(9*x - 4*x, 30)", "GIVEN"), ("5x = 30", "Eq(5*x, 30)", "COMBINE"),
      ("x = 6", "Eq(x, 6)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222255", "11111111-1111-1111-1111-111111111106",
     "3x + 5x = 24", 0.3,
     [("3x + 5x = 24", "Eq(3*x + 5*x, 24)", "GIVEN"), ("8x = 24", "Eq(8*x, 24)", "COMBINE"),
      ("x = 3", "Eq(x, 3)", "DIVIDE_CONSTANT")]),
    # distributing
    ("22222222-2222-2222-2222-222222222261", "11111111-1111-1111-1111-111111111107",
     "2(x + 3) = 14", 0.4,
     [("2(x + 3) = 14", "Eq(2*(x + 3), 14)", "GIVEN"), ("2x + 6 = 14", "Eq(2*x + 6, 14)", "DISTRIBUTE"),
      ("2x = 8", "Eq(2*x, 8)", "SUBTRACT_CONSTANT"), ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222262", "11111111-1111-1111-1111-111111111107",
     "3(x - 2) = 9", 0.4,
     [("3(x - 2) = 9", "Eq(3*(x - 2), 9)", "GIVEN"), ("3x - 6 = 9", "Eq(3*x - 6, 9)", "DISTRIBUTE"),
      ("3x = 15", "Eq(3*x, 15)", "ADD_CONSTANT"), ("x = 5", "Eq(x, 5)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222263", "11111111-1111-1111-1111-111111111107",
     "4(x + 1) = 20", 0.4,
     [("4(x + 1) = 20", "Eq(4*(x + 1), 20)", "GIVEN"), ("4x + 4 = 20", "Eq(4*x + 4, 20)", "DISTRIBUTE"),
      ("4x = 16", "Eq(4*x, 16)", "SUBTRACT_CONSTANT"), ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222264", "11111111-1111-1111-1111-111111111107",
     "5(x - 1) = 15", 0.4,
     [("5(x - 1) = 15", "Eq(5*(x - 1), 15)", "GIVEN"), ("5x - 5 = 15", "Eq(5*x - 5, 15)", "DISTRIBUTE"),
      ("5x = 20", "Eq(5*x, 20)", "ADD_CONSTANT"), ("x = 4", "Eq(x, 4)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222265", "11111111-1111-1111-1111-111111111107",
     "2(x + 4) = 18", 0.4,
     [("2(x + 4) = 18", "Eq(2*(x + 4), 18)", "GIVEN"), ("2x + 8 = 18", "Eq(2*x + 8, 18)", "DISTRIBUTE"),
      ("2x = 10", "Eq(2*x, 10)", "SUBTRACT_CONSTANT"), ("x = 5", "Eq(x, 5)", "DIVIDE_CONSTANT")]),
    # clearing fractions
    ("22222222-2222-2222-2222-222222222271", "11111111-1111-1111-1111-111111111108",
     "\\frac{x}{2} + \\frac{x}{4} = 6", 0.5,
     [("\\frac{x}{2} + \\frac{x}{4} = 6", "Eq(x/2 + x/4, 6)", "GIVEN"),
      ("2x + x = 24", "Eq(2*x + x, 24)", "CLEAR_FRACTIONS"),
      ("3x = 24", "Eq(3*x, 24)", "COMBINE"), ("x = 8", "Eq(x, 8)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222272", "11111111-1111-1111-1111-111111111108",
     "\\frac{x}{3} + 1 = 5", 0.4,
     [("\\frac{x}{3} + 1 = 5", "Eq(x/3 + 1, 5)", "GIVEN"), ("\\frac{x}{3} = 4", "Eq(x/3, 4)", "SUBTRACT_CONSTANT"),
      ("x = 12", "Eq(x, 12)", "MULTIPLY_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222273", "11111111-1111-1111-1111-111111111108",
     "\\frac{x}{5} - 2 = 1", 0.4,
     [("\\frac{x}{5} - 2 = 1", "Eq(x/5 - 2, 1)", "GIVEN"), ("\\frac{x}{5} = 3", "Eq(x/5, 3)", "ADD_CONSTANT"),
      ("x = 15", "Eq(x, 15)", "MULTIPLY_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222274", "11111111-1111-1111-1111-111111111108",
     "\\frac{2x}{3} = 8", 0.4,
     [("\\frac{2x}{3} = 8", "Eq(2*x/3, 8)", "GIVEN"), ("2x = 24", "Eq(2*x, 24)", "MULTIPLY_CONSTANT"),
      ("x = 12", "Eq(x, 12)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222275", "11111111-1111-1111-1111-111111111108",
     "\\frac{x}{4} + \\frac{x}{2} = 9", 0.5,
     [("\\frac{x}{4} + \\frac{x}{2} = 9", "Eq(x/4 + x/2, 9)", "GIVEN"),
      ("x + 2x = 36", "Eq(x + 2*x, 36)", "CLEAR_FRACTIONS"),
      ("3x = 36", "Eq(3*x, 36)", "COMBINE"), ("x = 12", "Eq(x, 12)", "DIVIDE_CONSTANT")]),
    # compound inequalities
    ("22222222-2222-2222-2222-222222222281", "11111111-1111-1111-1111-111111111109",
     "1 < x + 2 < 7", 0.45,
     [("1 < x + 2 < 7", "(1 < x + 2) & (x + 2 < 7)", "GIVEN"),
      ("-1 < x < 5", "(-1 < x) & (x < 5)", "SUBTRACT_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222282", "11111111-1111-1111-1111-111111111109",
     "0 \\leq 2x \\leq 10", 0.45,
     [("0 \\leq 2x \\leq 10", "(0 <= 2*x) & (2*x <= 10)", "GIVEN"),
      ("0 \\leq x \\leq 5", "(0 <= x) & (x <= 5)", "DIVIDE_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222283", "11111111-1111-1111-1111-111111111109",
     "3 < x - 1 < 8", 0.45,
     [("3 < x - 1 < 8", "(3 < x - 1) & (x - 1 < 8)", "GIVEN"),
      ("4 < x < 9", "(4 < x) & (x < 9)", "ADD_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222284", "11111111-1111-1111-1111-111111111109",
     "-2 \\leq x + 3 \\leq 4", 0.45,
     [("-2 \\leq x + 3 \\leq 4", "(-2 <= x + 3) & (x + 3 <= 4)", "GIVEN"),
      ("-5 \\leq x \\leq 1", "(-5 <= x) & (x <= 1)", "SUBTRACT_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222285", "11111111-1111-1111-1111-111111111109",
     "2 < 3x < 12", 0.5,
     [("2 < 3x < 12", "(2 < 3*x) & (3*x < 12)", "GIVEN"),
      ("\\frac{2}{3} < x < 4", "(Rational(2,3) < x) & (x < 4)", "DIVIDE_CONSTANT")]),
    # absolute value
    ("22222222-2222-2222-2222-222222222291", "11111111-1111-1111-1111-111111111110",
     "|x| = 5", 0.4,
     [("|x| = 5", "Eq(Abs(x), 5)", "GIVEN"),
      ("x = \\pm 5", "Or(Eq(x, 5), Eq(x, -5))", "SPLIT_ABS")]),
    ("22222222-2222-2222-2222-222222222292", "11111111-1111-1111-1111-111111111110",
     "|x - 2| = 3", 0.5,
     [("|x - 2| = 3", "Eq(Abs(x - 2), 3)", "GIVEN"),
      ("x - 2 = \\pm 3", "Or(Eq(x - 2, 3), Eq(x - 2, -3))", "SPLIT_ABS"),
      ("x = 5 \\text{ or } x = -1", "Or(Eq(x, 5), Eq(x, -1))", "ADD_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222293", "11111111-1111-1111-1111-111111111110",
     "|x + 1| = 4", 0.5,
     [("|x + 1| = 4", "Eq(Abs(x + 1), 4)", "GIVEN"),
      ("x + 1 = \\pm 4", "Or(Eq(x + 1, 4), Eq(x + 1, -4))", "SPLIT_ABS"),
      ("x = 3 \\text{ or } x = -5", "Or(Eq(x, 3), Eq(x, -5))", "SUBTRACT_CONSTANT")]),
    ("22222222-2222-2222-2222-222222222294", "11111111-1111-1111-1111-111111111110",
     "|x| = 0", 0.35,
     [("|x| = 0", "Eq(Abs(x), 0)", "GIVEN"), ("x = 0", "Eq(x, 0)", "SPLIT_ABS")]),
    ("22222222-2222-2222-2222-222222222295", "11111111-1111-1111-1111-111111111110",
     "|2x| = 8", 0.45,
     [("|2x| = 8", "Eq(Abs(2*x), 8)", "GIVEN"),
      ("2x = \\pm 8", "Or(Eq(2*x, 8), Eq(2*x, -8))", "SPLIT_ABS"),
      ("x = \\pm 4", "Or(Eq(x, 4), Eq(x, -4))", "DIVIDE_CONSTANT")]),
    # difference of squares
    ("22222222-2222-2222-2222-2222222222a1", "11111111-1111-1111-1111-111111111111",
     "x^{2} - 25 = 0", 0.5,
     [("x^{2} - 25 = 0", "Eq(x**2 - 25, 0)", "GIVEN"),
      ("(x - 5)(x + 5) = 0", "Eq((x - 5)*(x + 5), 0)", "FACTOR"),
      ("x = \\pm 5", "Or(Eq(x, 5), Eq(x, -5))", "ZERO_PRODUCT")]),
    ("22222222-2222-2222-2222-2222222222a2", "11111111-1111-1111-1111-111111111111",
     "x^{2} - 49 = 0", 0.5,
     [("x^{2} - 49 = 0", "Eq(x**2 - 49, 0)", "GIVEN"),
      ("(x - 7)(x + 7) = 0", "Eq((x - 7)*(x + 7), 0)", "FACTOR"),
      ("x = \\pm 7", "Or(Eq(x, 7), Eq(x, -7))", "ZERO_PRODUCT")]),
    ("22222222-2222-2222-2222-2222222222a3", "11111111-1111-1111-1111-111111111111",
     "x^{2} - 4 = 0", 0.45,
     [("x^{2} - 4 = 0", "Eq(x**2 - 4, 0)", "GIVEN"),
      ("(x - 2)(x + 2) = 0", "Eq((x - 2)*(x + 2), 0)", "FACTOR"),
      ("x = \\pm 2", "Or(Eq(x, 2), Eq(x, -2))", "ZERO_PRODUCT")]),
    ("22222222-2222-2222-2222-2222222222a4", "11111111-1111-1111-1111-111111111111",
     "x^{2} - 81 = 0", 0.5,
     [("x^{2} - 81 = 0", "Eq(x**2 - 81, 0)", "GIVEN"),
      ("(x - 9)(x + 9) = 0", "Eq((x - 9)*(x + 9), 0)", "FACTOR"),
      ("x = \\pm 9", "Or(Eq(x, 9), Eq(x, -9))", "ZERO_PRODUCT")]),
    ("22222222-2222-2222-2222-2222222222a5", "11111111-1111-1111-1111-111111111111",
     "x^{2} - 1 = 0", 0.4,
     [("x^{2} - 1 = 0", "Eq(x**2 - 1, 0)", "GIVEN"),
      ("(x - 1)(x + 1) = 0", "Eq((x - 1)*(x + 1), 0)", "FACTOR"),
      ("x = \\pm 1", "Or(Eq(x, 1), Eq(x, -1))", "ZERO_PRODUCT")]),
    # graphing linear — solve for intercepts / slope forms as equations
    ("22222222-2222-2222-2222-2222222222b1", "11111111-1111-1111-1111-111111111112",
     "y = 2x + 1", 0.35,
     [("y = 2x + 1", "Eq(y, 2*x + 1)", "GIVEN"),
      ("y = 2x + 1", "Eq(y, 2*x + 1)", "IDENTIFY_SLOPE_INTERCEPT")]),
    ("22222222-2222-2222-2222-2222222222b2", "11111111-1111-1111-1111-111111111112",
     "y = -x + 4", 0.35,
     [("y = -x + 4", "Eq(y, -x + 4)", "GIVEN"),
      ("y = -x + 4", "Eq(y, -x + 4)", "IDENTIFY_SLOPE_INTERCEPT")]),
    ("22222222-2222-2222-2222-2222222222b3", "11111111-1111-1111-1111-111111111112",
     "y = 3x - 2", 0.35,
     [("y = 3x - 2", "Eq(y, 3*x - 2)", "GIVEN"),
      ("y = 3x - 2", "Eq(y, 3*x - 2)", "IDENTIFY_SLOPE_INTERCEPT")]),
    ("22222222-2222-2222-2222-2222222222b4", "11111111-1111-1111-1111-111111111112",
     "y = \\frac{1}{2}x + 3", 0.4,
     [("y = \\frac{1}{2}x + 3", "Eq(y, x/2 + 3)", "GIVEN"),
      ("y = \\frac{1}{2}x + 3", "Eq(y, x/2 + 3)", "IDENTIFY_SLOPE_INTERCEPT")]),
    ("22222222-2222-2222-2222-2222222222b5", "11111111-1111-1111-1111-111111111112",
     "y = -2x", 0.3,
     [("y = -2x", "Eq(y, -2*x)", "GIVEN"),
      ("y = -2x", "Eq(y, -2*x)", "IDENTIFY_SLOPE_INTERCEPT")]),
]


def _item(iid, nid, stmt, diff, steps):
    return {
        "id": iid,
        "node_id": nid,
        "statement_latex": stmt,
        "difficulty_estimate": diff,
        "status": "VERIFIED",
        "source": "SEEDED",
        "steps": [{"latex": a, "sympy": b, "operation": c} for a, b, c in steps],
    }


def main() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    existing_ids = {n["id"] for n in seed["nodes"]}
    for n in seed["nodes"]:
        n["primer_md"] = PRIMERS.get(n["slug"], n.get("description", ""))
    for n in NEW_NODES:
        if n["id"] not in existing_ids:
            n = {**n, "primer_md": PRIMERS[n["slug"]]}
            seed["nodes"].append(n)
    edge_keys = {(e["parent_id"], e["child_id"], e["edge_type"]) for e in seed["edges"]}
    for p, c in NEW_EDGES:
        key = (p, c, "PREREQUISITE_OF")
        if key not in edge_keys:
            seed["edges"].append(
                {"parent_id": p, "child_id": c, "edge_type": "PREREQUISITE_OF", "weight": 1.0}
            )
            edge_keys.add(key)
    item_ids = {i["id"] for i in seed["items"]}
    for row in EXTRA_CORE + NEW_ITEMS:
        it = _item(*row)
        if it["id"] not in item_ids:
            # fix non-hex ids like 2a1 -> use valid UUID hex only
            if any(ch in it["id"] for ch in "ghijklmnopqrstuvwxyz" if ch not in "abcdef"):
                continue
            seed["items"].append(it)
            item_ids.add(it["id"])
    # Fix items with invalid hex (2a1 etc) — regenerate with valid hex
    seed["items"] = [i for i in seed["items"] if all(c in "0123456789abcdef-" for c in i["id"])]
    # Re-add difference-of-squares / graphing with valid UUIDs
    valid_extra = [
        _item(
            "22222222-2222-2222-2222-2222222222c1",
            "11111111-1111-1111-1111-111111111111",
            "x^{2} - 25 = 0",
            0.5,
            [
                ("x^{2} - 25 = 0", "Eq(x**2 - 25, 0)", "GIVEN"),
                ("(x - 5)(x + 5) = 0", "Eq((x - 5)*(x + 5), 0)", "FACTOR"),
                ("x = \\pm 5", "Or(Eq(x, 5), Eq(x, -5))", "ZERO_PRODUCT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222c2",
            "11111111-1111-1111-1111-111111111111",
            "x^{2} - 49 = 0",
            0.5,
            [
                ("x^{2} - 49 = 0", "Eq(x**2 - 49, 0)", "GIVEN"),
                ("(x - 7)(x + 7) = 0", "Eq((x - 7)*(x + 7), 0)", "FACTOR"),
                ("x = \\pm 7", "Or(Eq(x, 7), Eq(x, -7))", "ZERO_PRODUCT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222c3",
            "11111111-1111-1111-1111-111111111111",
            "x^{2} - 4 = 0",
            0.45,
            [
                ("x^{2} - 4 = 0", "Eq(x**2 - 4, 0)", "GIVEN"),
                ("(x - 2)(x + 2) = 0", "Eq((x - 2)*(x + 2), 0)", "FACTOR"),
                ("x = \\pm 2", "Or(Eq(x, 2), Eq(x, -2))", "ZERO_PRODUCT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222c4",
            "11111111-1111-1111-1111-111111111111",
            "x^{2} - 81 = 0",
            0.5,
            [
                ("x^{2} - 81 = 0", "Eq(x**2 - 81, 0)", "GIVEN"),
                ("(x - 9)(x + 9) = 0", "Eq((x - 9)*(x + 9), 0)", "FACTOR"),
                ("x = \\pm 9", "Or(Eq(x, 9), Eq(x, -9))", "ZERO_PRODUCT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222c5",
            "11111111-1111-1111-1111-111111111111",
            "x^{2} - 1 = 0",
            0.4,
            [
                ("x^{2} - 1 = 0", "Eq(x**2 - 1, 0)", "GIVEN"),
                ("(x - 1)(x + 1) = 0", "Eq((x - 1)*(x + 1), 0)", "FACTOR"),
                ("x = \\pm 1", "Or(Eq(x, 1), Eq(x, -1))", "ZERO_PRODUCT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222d1",
            "11111111-1111-1111-1111-111111111112",
            "y = 2x + 1",
            0.35,
            [
                ("y = 2x + 1", "Eq(y, 2*x + 1)", "GIVEN"),
                ("y = 2x + 1", "Eq(y, 2*x + 1)", "IDENTIFY_SLOPE_INTERCEPT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222d2",
            "11111111-1111-1111-1111-111111111112",
            "y = -x + 4",
            0.35,
            [
                ("y = -x + 4", "Eq(y, -x + 4)", "GIVEN"),
                ("y = -x + 4", "Eq(y, -x + 4)", "IDENTIFY_SLOPE_INTERCEPT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222d3",
            "11111111-1111-1111-1111-111111111112",
            "y = 3x - 2",
            0.35,
            [
                ("y = 3x - 2", "Eq(y, 3*x - 2)", "GIVEN"),
                ("y = 3x - 2", "Eq(y, 3*x - 2)", "IDENTIFY_SLOPE_INTERCEPT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222d4",
            "11111111-1111-1111-1111-111111111112",
            "y = \\frac{1}{2}x + 3",
            0.4,
            [
                ("y = \\frac{1}{2}x + 3", "Eq(y, x/2 + 3)", "GIVEN"),
                ("y = \\frac{1}{2}x + 3", "Eq(y, x/2 + 3)", "IDENTIFY_SLOPE_INTERCEPT"),
            ],
        ),
        _item(
            "22222222-2222-2222-2222-2222222222d5",
            "11111111-1111-1111-1111-111111111112",
            "y = -2x",
            0.3,
            [
                ("y = -2x", "Eq(y, -2*x)", "GIVEN"),
                ("y = -2x", "Eq(y, -2*x)", "IDENTIFY_SLOPE_INTERCEPT"),
            ],
        ),
    ]
    have = {i["id"] for i in seed["items"]}
    for it in valid_extra:
        if it["id"] not in have:
            seed["items"].append(it)

    out = Path("/app/seed/algebra_p0lite.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Also try host-mounted supabase if writable
    try:
        SEED.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"also wrote {SEED}")
    except OSError:
        print(f"supabase mount not writable; wrote {out}")
    print(f"nodes={len(seed['nodes'])} edges={len(seed['edges'])} items={len(seed['items'])}")


if __name__ == "__main__":
    main()
