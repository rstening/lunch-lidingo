"""Lidingö Saluhall: lunch section on the Squarespace front page."""
import re
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week


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
    return [WeekMenu(year=year, week=week, week_known=known, days=days, notes=notes)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
