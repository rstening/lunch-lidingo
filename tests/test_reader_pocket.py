from datetime import date
from pathlib import Path

from scraper.readers import pocket

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_pocket_fixture_two_weeks():
    weeks = pocket.parse((FIX / "pocket.html").read_text(encoding="utf-8"), TODAY)
    assert [(w.year, w.week, w.week_known) for w in weeks] == [(2026, 39, True), (2026, 40, True)]
    w39 = weeks[0]
    assert sorted(w39.days) == ["1", "2", "3", "4", "5"]
    mon = w39.days["1"]
    assert len(mon) == 3
    assert mon[0].name == "Vegetarisk lasagne, sojafärs, grönsaker, parmesankräk, ruccola (Gluten, Laktos, Ägg)"
    assert mon[0].tags == ["veg"]
    assert mon[0].price == 135
    assert mon[2].name.startswith("Thaifisk curry") and mon[2].tags == ["fisk"]
    tue = w39.days["2"]
    treat = [d for d in tue if d.name.lower().startswith("idag bjuder")]
    assert treat and treat[0].price is None
    assert "salladsbuffé" in w39.notes


def test_parse_pocket_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        pocket.parse("<html><body></body></html>", TODAY)


def test_pocket_pensioner_price_is_an_extra():
    weeks = pocket.parse((FIX / "pocket.html").read_text(encoding="utf-8"), TODAY)
    assert all(w.extras == ["Pensionärspris 120 kr."] for w in weeks)
