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


def test_parse_saluhallen_heading_split_across_strong_tags_not_absorbed_as_dish():
    html = """
    <html><body><section id="lunchmeny-section">
      <h1>Lunchmeny vecka 40</h1>
      <p><em>Valkommen till oss denna vecka.</em></p>
      <p><strong>MÅNDAG</strong></p>
      <p>Fläsknoisette med senapssås</p>
      <p><strong>VECKANS</strong> <strong>KÖTT</strong></p>
      <p>Detta ska inte bli en rätt under måndag</p>
    </section></body></html>
    """
    w = saluhallen.parse(html, TODAY)[0]
    mon = w.days["1"]
    assert len(mon) == 1
    assert mon[0].name == "Fläsknoisette med senapssås"
    names = [d.name for d in mon]
    assert "VECKANS KÖTT" not in names
    assert "Detta ska inte bli en rätt under måndag" not in names


def test_parse_saluhallen_intro_em_without_ingar_becomes_notes():
    html = """
    <html><body><section id="lunchmeny-section">
      <h1>Lunchmeny vecka 40</h1>
      <p><em>Varmt valkomna till oss denna vecka!</em></p>
      <p><strong>MÅNDAG</strong></p>
      <p>Fläsknoisette med senapssås</p>
    </section></body></html>
    """
    w = saluhallen.parse(html, TODAY)[0]
    assert w.notes == "Varmt valkomna till oss denna vecka!"


def test_saluhallen_price_range_and_time_prices():
    w = saluhallen.parse((FIX / "saluhallen.html").read_text(encoding="utf-8"), TODAY)[0]
    dishes = [d for v in w.days.values() for d in v]
    assert all((d.price, d.price_to) == (160, None) for d in dishes)  # 11-14 is most of the day
    assert w.extras == ["145 kr 10:00-11:00, 160 kr 11:00-14:00."]


def test_saluhallen_without_price_sentence_has_no_price():
    html = ('<section id="lunchmeny-section"><h1>Lunchmeny vecka 40</h1>'
            '<p><em>I lunchen ingår kaffe.</em></p><p><strong>MÅNDAG</strong></p><p>Soppa</p></section>')
    w = saluhallen.parse(html, TODAY)[0]
    assert w.days["1"][0].price is None and w.days["1"][0].price_to is None
    assert w.extras == []


def test_saluhallen_uses_the_price_that_lasts_longest():
    html = ('<section id="lunchmeny-section"><h1>Lunchmeny vecka 40</h1>'
            '<p><em>I lunchen ingår kaffe. Dagens lunch kostar 150 :- mellan 10.00-13:00, '
            '170: - mellan 13.00-14.00.</em></p><p><strong>MÅNDAG</strong></p><p>Soppa</p></section>')
    w = saluhallen.parse(html, TODAY)[0]
    assert w.days["1"][0].price == 150
    assert w.extras == ["150 kr 10:00-13:00, 170 kr 13:00-14:00."]
