from datetime import date
from pathlib import Path

from scraper.readers import saluhallen

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_saluhallen_fixture():
    w = saluhallen.parse((FIX / "saluhallen.html").read_text(encoding="utf-8"), TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 40, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert len(mon) == 3
    assert mon[0].name.startswith("Fläsknoisette med senapssås")
    assert mon[2].name.startswith("Broccoli-& ädelostpaj") and mon[2].tags == ["veg"]
    assert len(w.days["4"]) == 4
    names = [d.name for v in w.days.values() for d in v]
    assert not any("Räksallad" in n for n in names)
    assert "salladsbuffé" in w.notes


def test_parse_saluhallen_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        saluhallen.parse('<html><body><section id="lunchmeny-section"></section></body></html>', TODAY)
