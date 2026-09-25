"""Lidingö Saluhall: lunch section on the Squarespace front page."""
import re
from datetime import date
from typing import Callable, List, Tuple

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week


# "145 :- mellan 10.00-11:00" -> price, start and end time
_TIME_PRICE = re.compile(r"(\d{2,3})\s*:\s*-\s*mellan\s*(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})")


def time_prices(notes: str) -> List[Tuple[int, str]]:
    """Prices by time of day from the intro, e.g. [(145, "10:00-11:00"), (160, "11:00-14:00")]."""
    return [(int(p), f"{int(h1):02d}:{m1}-{int(h2):02d}:{m2}")
            for p, h1, m1, h2, m2 in _TIME_PRICE.findall(notes)]


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#lunchmeny-section")
    if section is None:
        raise ParseError("Saluhallen: hittade ingen lunchsektion")
    year, week = iso_week(today)
    known = False
    for h in section.find_all(["h1", "h2", "h3"]):
        m = re.search(r"vecka\s+(\d{1,2})", clean(h.get_text()), re.I)
        if m:
            week = int(m.group(1))
            year = year_for_week(week, today)
            known = True
            break

    days = {}
    veg = []
    notes = ""
    mode = None  # ("day", idx) | ("veg", None) | None
    seen_day_heading = False
    for p in section.find_all("p"):
        text = clean(p.get_text(" "))
        if not text:
            continue
        if not seen_day_heading and not notes and p.find("em"):
            notes = text
            continue
        strongs = p.find_all("strong")
        if strongs and clean(" ".join(s.get_text(" ") for s in strongs)) == text:
            idx = day_index(text)
            if idx:
                mode = ("day", idx)
                seen_day_heading = True
            elif text.upper().startswith("VECKANS VEGETARISKA"):
                mode = ("veg", None)
            else:
                mode = None
            continue
        if mode is None:
            continue
        if mode[0] == "day":
            days.setdefault(str(mode[1]), []).append(Dish(name=text))
        else:
            veg.append(Dish(name=text, tags=["veg"]))
    if not days:
        raise ParseError("Saluhallen: hittade inga rätter")
    for key in days:
        days[key].extend(Dish(name=v.name, price=v.price, tags=list(v.tags)) for v in veg)
    prices = time_prices(notes)
    extras = []
    if prices:
        low, high = min(p for p, _ in prices), max(p for p, _ in prices)
        for dishes in days.values():
            for d in dishes:
                d.price = low
                d.price_to = high if high != low else None
        extras.append(", ".join(f"{p} kr {span}" for p, span in prices) + ".")
    return [WeekMenu(year=year, week=week, week_known=known, days=days, notes=notes, extras=extras)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
