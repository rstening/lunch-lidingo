from datetime import date

from scraper.weeks import (day_index, display_date, iso_week, week_dates,
                           year_for_week)


def test_iso_week():
    assert iso_week(date(2026, 9, 25)) == (2026, 39)


def test_day_index_swedish_names_case_insensitive():
    assert day_index("Måndag ") == 1
    assert day_index("tisdag") == 2
    assert day_index("ONSDAG") == 3
    assert day_index("Torsdag:") == 4
    assert day_index("fredag") == 5


def test_day_index_rejects_english_and_weekend():
    assert day_index("monday") is None
    assert day_index("Lördag:") is None
    assert day_index("Vecka 39") is None


def test_year_for_week_handles_new_year():
    assert year_for_week(40, date(2026, 9, 25)) == 2026
    assert year_for_week(1, date(2026, 12, 30)) == 2027
    assert year_for_week(52, date(2027, 1, 2)) == 2026


def test_display_date_weekday_is_same_day():
    assert display_date(date(2026, 9, 23)) == date(2026, 9, 23)


def test_display_date_weekend_is_next_monday():
    assert display_date(date(2026, 9, 26)) == date(2026, 9, 28)
    assert display_date(date(2026, 9, 27)) == date(2026, 9, 28)


def test_week_dates():
    ds = week_dates(2026, 40)
    assert ds[0] == date(2026, 9, 28)
    assert ds[4] == date(2026, 10, 2)
