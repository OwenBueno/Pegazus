"""Core component sanitizers (Doc 10 §4.2): bounded props, keys split into answer_spec."""

from app.graders import grade
from app.services.component_catalog import sanitize_part, sanitize_visual


def _part(component, **props):
    return sanitize_part({"component": component, "props": props}, seed="s")


def test_short_answer_keys_stay_in_spec():
    p = _part("ShortAnswer", question="Capital of France?", accepted=["Paris", "paris city"])
    assert p["props"] == {"question": "Capital of France?"} and p["grader"] == "exact"
    assert grade("exact", p["answer_spec"], {"text": " PARIS. "}).is_success
    assert isinstance(_part("ShortAnswer", question="q", accepted=[f"a{i}" for i in range(11)]), str)  # ≤ 10


def test_cloze_and_worked_example_blanks():
    c = _part("Cloze", text="Water boils at [[100]] °C at [[sea level]].", aliases={"0": ["100°C"]})
    assert c["props"]["segments"] == ["Water boils at ", " °C at ", "."]
    assert grade("cloze", c["answer_spec"], {"blanks": ["100°C", "Sea level"]}).is_success
    assert isinstance(_part("Cloze", text="no blanks here"), str)
    w = _part("WorkedExample", steps=[{"text": "Light hits [[chlorophyll]]."}, {"text": "Water splits."}])
    assert w["grader"] == "cloze" and w["props"]["steps"][1] == {"segments": ["Water splits."]}
    assert grade("cloze", w["answer_spec"], {"blanks": ["Chlorophyll"]}).is_success


def test_order_is_shuffled_and_graded():
    items = ["light absorbed", "water split", "ATP made", "sugar built"]
    o = _part("OrderSteps", items=items)
    shown = o["props"]["items"]
    assert shown != items and sorted(shown) == sorted(items)
    canonical = [shown.index(x) for x in items]
    assert o["answer_spec"]["order"] == canonical
    assert grade("order", o["answer_spec"], {"order": canonical}).is_success
    assert isinstance(_part("OrderSteps", items=["a", "b"]), str)  # 3-7 items


def test_categorize_and_flashcards():
    items = [{"label": x, "bucket": b} for x, b in (("Fe", 0), ("O", 1), ("Cu", 0), ("N", 1))]
    c = _part("Categorize", buckets=["Metal", "Non-metal"], items=items)
    assert c["props"] == {"buckets": ["Metal", "Non-metal"], "items": ["Fe", "O", "Cu", "N"]}
    assert grade("categorize", c["answer_spec"], {"assign": {"0": 0, "1": 1, "2": 0, "3": 1}}).is_success
    assert isinstance(_part("Categorize", buckets=["A", "B"], items=items[:3]), str)  # 4-10 items
    cards = [{"front": f"f{i}", "back": f"b{i}"} for i in range(3)]
    f = _part("Flashcards", cards=cards)
    r = grade("flashcards", f["answer_spec"], {"self": [1, 0, 1]})
    assert r.verdict == "PARTIAL" and r.decided_by == "CLIENT"
    assert grade("flashcards", f["answer_spec"], {"self": [1, 2, 1]}).verdict == "SYNTAX_ERROR"
    assert isinstance(_part("Flashcards", cards=cards[:2]), str)  # 3-12 cards


def test_free_response_spec_never_public():
    p = _part("FreeResponse", question="Why are leaves green?", rubric=[{"criterion": "chlorophyll", "points": 1}],
              exemplar="Chlorophyll reflects green light.", key_terms=["chlorophyll"], max_words=999)
    assert p["props"] == {"question": "Why are leaves green?", "max_words": 300}
    assert p["answer_spec"]["exemplar"] and isinstance(_part("FreeResponse", question="q"), str)


def test_core_visuals():
    assert sanitize_visual({"type": "KeyTerms", "props": {"terms": [{"term": "ATP", "def": "energy carrier"}]}})
    assert sanitize_visual({"type": "KeyTerms", "props": {"terms": [{"term": "ATP"}]}}) is None
    steps = [{"title": "Evaporation"}, {"title": "Condensation", "body": "clouds"}]
    assert sanitize_visual({"type": "ProcessSteps", "props": {"steps": steps, "cyclic": True}})["props"]["cyclic"]
    assert sanitize_visual({"type": "ProcessSteps", "props": {"steps": steps[:1]}}) is None
    side = {"title": "Mitosis", "points": ["2 cells"]}
    assert sanitize_visual({"type": "Comparison", "props": {"left": side, "right": side}})
    assert sanitize_visual({"type": "Comparison", "props": {"left": side}}) is None
    table = {"headers": ["a"], "rows": [["1"]]}
    assert sanitize_visual({"type": "DataTable", "props": table}) == sanitize_visual({"type": "ValueTable", "props": table}) | {"type": "DataTable"}


def test_diagram_rejects_scripts_and_directives():
    ok = {"kind": "mermaid", "source": "flowchart LR; A[Light]-->B[Leaf]", "alt": "light reaches the leaf"}
    assert sanitize_visual({"type": "Diagram", "props": ok})
    for bad in (
        {**ok, "alt": ""},
        {**ok, "source": "x" * 2001},
        {**ok, "source": "%%{init: {'securityLevel': 'loose'}}%%\nflowchart LR; A-->B"},
        {**ok, "source": "flowchart LR; A-->B\nclick A callback"},
        {"kind": "svg", "source": "<svg><script>alert(1)</script></svg>", "alt": "x"},
        {"kind": "svg", "source": '<svg><rect onclick="alert(1)"/></svg>', "alt": "x"},
        {"kind": "svg", "source": '<svg><a href="javascript:alert(1)"/></svg>', "alt": "x"},
        {**ok, "kind": "png"},
    ):
        assert sanitize_visual({"type": "Diagram", "props": bad}) is None, bad
