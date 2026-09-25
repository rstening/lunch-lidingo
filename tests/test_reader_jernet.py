import json
from datetime import date
from pathlib import Path

from scraper.readers import jernet

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)
JS = ('var a="https://abcdefghij.supabase.co",b="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
      'eyJpc3MiOiJzdXBhYmFzZSJ9.abc_DEF-123";')


def test_find_bundle_url():
    html = (FIX / "jernet.html").read_text(encoding="utf-8")
    assert jernet.find_bundle_url(html, "https://brasseriejernet.se/") == \
        "https://brasseriejernet.se/assets/index-xZPF3w39.js"


def test_find_supabase():
    url, key = jernet.find_supabase(JS)
    assert url == "https://abcdefghij.supabase.co"
    assert key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.")


def test_parse_rows():
    rows = json.loads((FIX / "jernet-lunch_menu.json").read_text(encoding="utf-8"))
    w = jernet.parse_rows(rows, TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, False)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert [d.tags for d in mon] == [["kött"], ["fisk"], ["veg"]]
    assert mon[0].name == "Kalvfärsbiffar serveras med ugnsrostad potatis och gräddsås"
    assert mon[0].price == 139
    assert mon[1].price == 149


def test_read_end_to_end_with_fake_get():
    html = (FIX / "jernet.html").read_bytes()
    rows = (FIX / "jernet-lunch_menu.json").read_bytes()
    seen = {}

    def fake_get(url, headers=None):
        if url.endswith(".js"):
            return JS.encode()
        if "lunch_menu" in url:
            seen["headers"] = headers
            return rows
        return html

    weeks = jernet.read(fake_get, "https://brasseriejernet.se/", TODAY)
    assert weeks[0].days["5"][0].name.startswith("Schnitzel")
    assert seen["headers"]["apikey"].startswith("eyJ")


def test_parse_rows_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        jernet.parse_rows([], TODAY)
