from datetime import date
from pathlib import Path

from scraper.readers import golf

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_golf_fixture():
    w = golf.parse((FIX / "golf.html").read_text(encoding="utf-8"), TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert len(mon) == 4
    assert mon[0].name.startswith("Pocherad flundrafilé med skaldjurssås")
    assert mon[0].tags == []
    assert mon[1].name.startswith("Gulaschgryta") and mon[1].tags == ["buffé"]
    assert mon[2].name.startswith("Friterade risbollar") and mon[2].tags == ["veg"]
    assert mon[3].name.startswith("Sallad med varmrökt lax") and mon[3].tags == ["lätt"]
    assert all(d.price == 165 for d in mon)
    assert "salladsbuffé" in w.notes


def test_parse_golf_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        golf.parse("<html><body><p><strong>Vecka 3</strong></p></body></html>", TODAY)
