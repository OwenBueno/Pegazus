"""Humanities visuals (Doc 11 MS-4.1): dates incl. BCE, map regions, cited-only URLs."""

from app.services.component_catalog import sanitize_visual


def _v(name, **props):
    return sanitize_visual({"type": name, "props": props})


def test_timeline_dates_parse_and_sort():
    events = [
        {"date": "1789-07-14", "label": "Bastille"},
        {"date": "490 BCE", "label": "Marathon"},
        {"date": 1799, "label": "Coup of 18 Brumaire"},
    ]
    out = _v("Timeline", events=events)["props"]["events"]
    assert [(e["date"], e["year"]) for e in out] == [("-490", -490), ("1789-07-14", 1789), ("1799", 1799)]
    assert _v("Timeline", events=[{"date": "1789-13-01", "label": "x"}, {"date": "1790", "label": "y"}]) is None
    assert _v("Timeline", events=[{"date": "July 1789", "label": "x"}, {"date": "1790", "label": "y"}]) is None
    assert _v("Timeline", events=events[:1]) is None  # 2-12 events


def test_map_pins_region_and_ranges():
    paris = {"lat": 48.85, "lon": 2.35, "label": "Paris"}
    assert _v("MapPins", region="europe", pins=[paris])["props"]["pins"] == [paris]
    assert _v("MapPins", region="asia", pins=[paris]) is None  # off the region's map
    assert _v("MapPins", region="atlantis", pins=[paris]) is None
    assert _v("MapPins", region="world", pins=[{"lat": 95, "lon": 0, "label": "x"}]) is None
    assert _v("MapPins", region="world", pins=[paris] * 13) is None


def test_source_excerpt_url_only_when_cited():
    props = {"quote": "Men are born and remain free.", "source": "Declaration", "year": 1789, "url": "https://ex.org/d"}
    assert "url" not in _v("SourceExcerpt", **props)["props"]
    cited = sanitize_visual({"type": "SourceExcerpt", "props": props}, {"https://ex.org/d"})["props"]
    assert cited["url"] == "https://ex.org/d" and cited["year"] == 1789
    js = sanitize_visual({"type": "SourceExcerpt", "props": {**props, "url": "javascript:alert(1)"}}, {"javascript:alert(1)"})
    assert "url" not in js["props"]
    assert _v("SourceExcerpt", quote="x" * 601) is None


def test_cause_effect_links():
    assert _v("CauseEffect", links=[{"cause": "Debt", "effect": "Estates-General"}])
    assert _v("CauseEffect", links=[{"cause": "Debt"}]) is None
    assert _v("CauseEffect", links=[{"cause": "a", "effect": "b"}] * 7) is None
