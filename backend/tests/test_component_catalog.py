"""Component catalog: frontend registry sync, visual validation, design normalization."""

import re
from pathlib import Path

import pytest

from app.graders import GRADERS
from app.services.component_catalog import CATEGORIES, COMPONENTS, catalog_prompt, sanitize_visual
from app.services.lesson_beats import normalize_design

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
REGISTRY = FRONTEND / "components" / "genui" / "registry.tsx"
CONTRACT = FRONTEND / "lib" / "contracts" / "genui.ts"
# The api container mounts only backend/; run these from a checkout (or copy the two files in).
needs_frontend = pytest.mark.skipif(not CONTRACT.exists(), reason="frontend/ not mounted")


@needs_frontend
def test_every_catalog_component_is_rendered_by_frontend():
    cases = set(re.findall(r'case "(\w+)"', REGISTRY.read_text(encoding="utf-8")))
    assert set(COMPONENTS) <= cases, set(COMPONENTS) - cases


@needs_frontend
def test_catalog_contract_has_every_component():
    schemas = {a or b for a, b in re.findall(r'z\.literal\("(\w+)"\)|(?:visual|answer)\("(\w+)"', CONTRACT.read_text(encoding="utf-8"))}
    assert set(COMPONENTS) <= schemas, set(COMPONENTS) - schemas


def test_catalog_two_axes_and_graders():
    for name, c in COMPONENTS.items():
        assert c["category"] in CATEGORIES, name
        assert (c["role"] == "answer") == ("grader" in c), name
        assert c["role"] != "answer" or c["grader"] in GRADERS, name


def test_catalog_prompt_filters_by_category():
    assert catalog_prompt("problem") == catalog_prompt("problem", CATEGORIES)
    core = catalog_prompt("problem", ["core"])
    assert "QuickCheck" in core and "MatchPairs" in core
    assert not any(n in core for n, c in COMPONENTS.items() if c["category"] == "math")


def _bars(parts, shaded, label):
    return {"type": "FractionBars", "props": {"bars": [{"parts": parts, "shaded": shaded, "label": label}]}}


def test_sanitize_visual_checks_the_math():
    assert sanitize_visual(_bars(4, 3, "3/4"))
    assert sanitize_visual(_bars(4, 2, r"\frac{1}{2}"))  # equivalent label is fine
    assert sanitize_visual(_bars(4, 5, "5/4")) is None  # more shaded than parts
    assert sanitize_visual(_bars(4, 3, "2/3")) is None  # label lies about the picture
    assert sanitize_visual({"type": "BalanceScale", "props": {"left": "2x+3", "right": "11"}})
    assert sanitize_visual({"type": "BalanceScale", "props": {"left": "2x+(", "right": "11"}}) is None
    tri = {"type": "ShapeDiagram", "props": {"shape": "triangle", "angles": [90, 60, 20]}}
    assert sanitize_visual(tri) is None  # angles must sum to 180
    assert sanitize_visual({"type": "Nope", "props": {}}) is None


def test_normalize_design_keeps_valid_visual_and_layout():
    good = _bars(4, 3, "3/4")
    ai = {
        "beats": [
            {"kind": "teach", "type": "intro", "title": "A", "body_md": "Parts.", "layout": "split", "visual": good},
            {"kind": "problem", "spec_index": 0},
            {"kind": "teach", "type": "concept", "title": "B", "body_md": "More.", "layout": "split",
             "visual": _bars(4, 3, "2/3")},
            {"kind": "teach", "type": "fun_fact", "title": "C", "body_md": "Fact.", "visual": {"type": "PieChart"}},
            {"kind": "problem", "spec_index": 1},
        ],
        "problem_specs": [
            {"facet": "a", "widget": "QuickCheck"},
            {"facet": "b", "widget": "FunctionPlotter"},
            {"facet": "c", "widget": "QuickCheck", "visual": good},  # full object, not a name
        ],
    }
    d = normalize_design(ai, brief=None)
    assert d["beats"][0]["visual"]["type"] == "FractionBars" and d["beats"][0]["layout"] == "split"
    assert "visual" not in d["beats"][2] and "layout" not in d["beats"][2]  # stack is the default
    assert d["visuals_dropped"] == ["FractionBars"]
    assert d["missing_widgets"] == ["PieChart"]
    assert d["specs"][1] == {**d["specs"][1], "widget": "SymbolicStepEditor", "visual": "FunctionPlotter"}
    assert d["specs"][2]["visual"] == "FractionBars"
