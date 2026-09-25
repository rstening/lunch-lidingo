"""Week and weekday helpers. All dates are ISO: week starts Monday, weekday 1..7."""
from datetime import date, timedelta
from typing import List, Optional, Tuple

DAY_NAMES = ["måndag", "tisdag", "onsdag", "torsdag", "fredag"]
DAY_SHORT = ["Mån", "Tis", "Ons", "Tor", "Fre"]
MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]


def iso_week(d: date) -> Tuple[int, int]:
    year, week, _ = d.isocalendar()
    return year, week


def day_index(text: str) -> Optional[int]:
    """Return 1..5 if text starts with a Swedish weekday name Mon..Fri, else None."""
    t = text.strip().lower().rstrip(":").strip()
    for i, name in enumerate(DAY_NAMES, start=1):
        if t == name or t.startswith(name + " "):
            return i
    return None


def year_for_week(week: int, today: date) -> int:
    """Guess which ISO year a bare week number refers to, relative to today."""
    year, this_week = iso_week(today)
    if week < this_week - 26:
        return year + 1
    if week > this_week + 26:
        return year - 1
    return year


def display_date(today: date) -> date:
    """The date whose lunch we show: today on weekdays, next Monday on weekends."""
    wd = today.isoweekday()
    if wd > 5:
        return today + timedelta(days=8 - wd)
    return today


def week_dates(year: int, week: int) -> List[date]:
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(5)]


def format_date(d: date) -> str:
    """'25 september' style."""
    return f"{d.day} {MONTHS[d.month - 1]}"
