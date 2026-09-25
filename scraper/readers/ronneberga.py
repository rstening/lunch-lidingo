"""Rönneberga: Swedish and English day blocks interleaved; we keep Swedish only."""
import re
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find(["h1", "h2", "h3"], string=re.compile(r"lunchmeny", re.I))
    if not header:
        raise ParseError("Rönneberga: hittade ingen lunchmeny-rubrik")
    m = re.search(r"v\.?\s*(\d{1,2})", header.get_text())
    if m:
        week = int(m.group(1))
        year = year_for_week(week, today)
        known = True
    else:
        year, week = iso_week(today)
        known = False

    container = header.parent
    days = {}
    notes = []
    current = None
    for el in container.find_all(["h2", "h3", "p"]):
        text = clean(el.get_text(" "))
        if el.name == "h3":
            current = day_index(text)
            continue
        if el.name == "h2":
            current = None
            continue
        if not text:
            continue
        if current is None:
            if "öppettider" in text.lower():
                notes.append(text)
            continue
        if el.find("em"):
            continue  # English translation lines
        days.setdefault(str(current), []).append(Dish(name=text))
    if not days:
        raise ParseError("Rönneberga: hittade inga rätter")
    return [WeekMenu(year=year, week=week, week_known=known, days=days,
                     notes=" ".join(notes))]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
