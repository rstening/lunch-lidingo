from datetime import date
from pathlib import Path

from scraper.readers import firren

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_firren_fixture():
    weeks = firren.parse((FIX / "firren.html").read_text(encoding="utf-8"), TODAY)
    assert len(weeks) == 1
    w = weeks[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    assert w.days["1"][0].name == "Scampi Indiana med grönsaksris"
    assert w.days["2"][0].name.startswith("Mandelbakad torsk med vitvinssås")
    assert all(len(v) == 1 for v in w.days.values())


def test_parse_firren_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        firren.parse("<html><body>nothing</body></html>", TODAY)


def test_read_uses_get():
    html = (FIX / "firren.html").read_text(encoding="utf-8")
    weeks = firren.read(lambda url, headers=None: html.encode("utf-8"),
                        "https://firren.org/bistro/", TODAY)
    assert weeks[0].week == 39
