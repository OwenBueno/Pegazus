from app.graders import grade

G = {"value": 9.8, "unit": "m/s^2", "tolerance": 0.05}


def test_numeric_units_and_tolerance() -> None:
    assert grade("numeric", G, {"value": 9.81, "unit": "m/s^2"}).is_success
    assert grade("numeric", G, {"value": 981, "unit": "cm/s^2"}).is_success
    assert grade("numeric", G, {"value": "9.81"}).is_success  # bare number read in the spec unit
    assert not grade("numeric", G, {"value": 11, "unit": "m/s^2"}).is_success
    assert not grade("numeric", G, {"value": 9.8, "unit": "km"}).is_success  # wrong dimension
    assert grade("numeric", {**G, "tolerance": 5}, {"value": 11.7}).is_success  # clamped to 20 %
    assert not grade("numeric", {**G, "tolerance": 5}, {"value": 12}).is_success


def test_number_line_absolute_tolerance() -> None:
    spec = {"value": 7.0, "abs_tolerance": 0.5}
    assert grade("numeric", spec, {"value": 7.5}).is_success
    assert not grade("numeric", spec, {"value": 8}).is_success


def test_numeric_garbage() -> None:
    for answer in ({"value": float("nan")}, {"value": "inf"}, {"value": True}, {"value": 9.8, "unit": "furlong"}):
        assert grade("numeric", G, answer).verdict == "SYNTAX_ERROR"
