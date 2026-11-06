"""Science pack (Doc 11 MS-4.3): ChemFormula, QuantityAnswer, ParameterExplorer, LabeledDiagram."""

from app.graders import grade
from app.services.component_catalog import expr_ok, sanitize_part, sanitize_visual


def _v(name, **props):
    return sanitize_visual({"type": name, "props": props})


def test_chem_formula():
    assert _v("ChemFormula", latex=r"\ce{2H2 + O2 -> 2H2O}")
    assert _v("ChemFormula", latex="H_2O") is None  # not mhchem
    assert _v("ChemFormula", latex=r"\ce{H2O} \href{javascript:x}{y}") is None
    assert _v("ChemFormula", latex=r"\ce{H2O") is None


def test_quantity_answer_accepts_equivalent_units():
    p = sanitize_part({"component": "QuantityAnswer", "props": {"question": "Moles in 36 g of water?"},
                       "answer_spec": {"value": 2, "unit": "mol"}})
    assert p["grader"] == "numeric" and "value" not in p["props"]
    assert set(p["props"]["units"]) == {"mol", "mmol"}
    assert grade("numeric", p["answer_spec"], {"value": 2000, "unit": "mmol"}).is_success
    assert not grade("numeric", p["answer_spec"], {"value": 2, "unit": "g"}).is_success
    assert isinstance(sanitize_part({"component": "QuantityAnswer", "props": {"question": "q", "value": 1, "unit": "furlong"}}), str)


def test_parameter_explorer_expr_whitelist():
    assert expr_ok("v0*t - 4.9*t^2 + sin(t)", {"v0", "t"})
    for bad in ("2t", "__import__('os')", "t.real", "v0(t)", "[t]", "lambda: t", "t if t else 1", "sin(t, t)", "u*t"):
        assert not expr_ok(bad, {"v0", "t"}), bad
    props = {"expr": "a*x^2", "x": "x", "domain": [-3, 3], "params": [{"name": "a", "min": -2, "max": 2}], "textAlt": "parabola"}
    assert _v("ParameterExplorer", **props)["props"]["params"][0]["value"] == 0
    assert _v("ParameterExplorer", **{**props, "params": [{"name": "sin", "min": 0, "max": 1}]}) is None
    assert _v("ParameterExplorer", **{**props, "params": [{"name": f"p{i}", "min": 0, "max": 1} for i in range(4)]}) is None


def test_labeled_diagram():
    labels = [{"x": 0.4, "y": 0.2, "text": "Nucleus"}]
    assert _v("LabeledDiagram", labels=labels, alt="cell", source='<svg viewBox="0 0 4 3"></svg>')
    assert _v("LabeledDiagram", labels=[{"x": 1.2, "y": 0, "text": "x"}], alt="cell") is None
    assert _v("LabeledDiagram", labels=labels, alt="cell", source='<svg onload="x()"></svg>') is None
