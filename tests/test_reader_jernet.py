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
    assert (w.year, w.week, w.week_known) == (2026, 39, True)
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


def _row(day, updated, name):
    return {"day_of_week": day, "updated_at": updated, "meat_name": name, "meat_price": 139}


def test_rows_not_updated_this_week_belong_to_last_week():
    # Tuesday of week 40: Jernet has filled in Monday and Tuesday; Wednesday to
    # Friday still hold last week's dishes.
    rows = [_row(1, "2026-09-28T08:10:00+00:00", "Mån v40"),
            _row(2, "2026-09-29T08:10:00+00:00", "Tis v40"),
            _row(3, "2026-09-23T08:16:11+00:00", "Ons v39"),
            _row(4, "2026-09-24T07:20:39+00:00", "Tor v39"),
            _row(5, "2026-09-25T10:10:18+00:00", "Fre v39")]
    weeks = {w.week: w for w in jernet.parse_rows(rows, date(2026, 9, 29))}
    assert sorted(weeks) == [39, 40]
    assert sorted(weeks[40].days) == ["1", "2"]
    assert weeks[40].days["1"][0].name == "Mån v40"
    assert sorted(weeks[39].days) == ["3", "4", "5"]
    assert all(w.week_known for w in weeks.values())


def test_monday_morning_before_any_update_is_all_last_week():
    rows = [_row(d, f"2026-09-2{d}T08:00:00+00:00", f"Dag {d}") for d in range(1, 6)]
    weeks = jernet.parse_rows(rows, date(2026, 9, 28))
    assert [(w.year, w.week) for w in weeks] == [(2026, 39)]


def test_update_time_uses_swedish_time():
    # 23:30 UTC on Sunday is already Monday 01:30 in Stockholm (week 40).
    rows = [_row(1, "2026-09-27T23:30:00+00:00", "Tidig måndag")]
    weeks = jernet.parse_rows(rows, date(2026, 9, 28))
    assert [(w.week, sorted(w.days)) for w in weeks] == [(40, ["1"])]


def test_rows_without_update_time_count_as_this_week():
    rows = [{"day_of_week": 2, "meat_name": "Utan tid", "meat_price": 139}]
    weeks = jernet.parse_rows(rows, date(2026, 9, 29))
    assert [(w.week, sorted(w.days)) for w in weeks] == [(40, ["2"])]
