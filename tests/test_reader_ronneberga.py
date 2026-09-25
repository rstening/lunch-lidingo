from datetime import date
from pathlib import Path

from scraper.readers import ronneberga

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_ronneberga_fixture():
    weeks = ronneberga.parse((FIX / "ronneberga.html").read_text(encoding="utf-8"), TODAY)
    w = weeks[0]
    assert (w.year, w.week, w.week_known) == (2026, 40, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    assert [d.name for d in w.days["1"]] == [
        "Isterband med stuvad potatis, senap & rödbetor",
        "Linsbolognese med pasta",
        "Dagens soppa",
    ]
    assert [d.name for d in w.days["4"]][-1] == "Pannkakor"
    all_names = [d.name for v in w.days.values() for d in v]
    assert not any("Soup of the day" in n for n in all_names)
    assert "11:30-13:00" in w.notes


def test_parse_ronneberga_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        ronneberga.parse("<html><body><h2>lunchmeny v. 1</h2></body></html>", TODAY)
