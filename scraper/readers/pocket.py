"""Pocket (Nordrest): Castit weekly menu widget, possibly several weeks."""
import re
from datetime import date
from typing import Callable, List, Optional

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, year_for_week


def _price(soup: BeautifulSoup) -> Optional[int]:
    meta = soup.select_one(".castit-lunch-meta")
    if not meta:
        return None
    m = re.search(r"Dagens rätt\s*:\s*(\d+)", clean(meta.get_text(" ")))
    return int(m.group(1)) if m else None


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    price = _price(soup)
    intro = soup.select_one(".castit-menu-text--intro")
    notes = clean(intro.get_text(" ")) if intro else ""
    weeks = []
    for panel in soup.select(".castit-weekpanel[data-week]"):
        try:
            week = int(panel["data-week"])
        except (KeyError, ValueError):
            continue
        days = {}
        for section in panel.select(".castit-day"):
            title = section.select_one(".castit-day__title")
            idx = day_index(clean(title.get_text())) if title else None
            if not idx:
                continue
            dishes = []
            for wrap in section.select(".castit-dish-wrap"):
                t = wrap.select_one(".castit-dish__title")
                if not t:
                    continue
                name = clean(t.get_text(" "))
                if not name:
                    continue
                d = wrap.select_one(".castit-dish__desc")
                a = wrap.select_one(".castit-dish__allergens")
                header = wrap.select_one(".castit-dish-header")
                if d and clean(d.get_text(" ")):
                    name = f"{name}, {clean(d.get_text(' '))}"
                if a and a.get("title"):
                    name = f"{name} ({clean(a['title'])})"
                tags = []
                if header and "fisk" in header.get_text().lower():
                    tags = ["fisk"]
                elif name.lower().startswith(("vegetarisk", "vegansk", "falafel")):
                    tags = ["veg"]
                dish_price = None if name.lower().startswith("idag bjuder") else price
                dishes.append(Dish(name=name, price=dish_price, tags=tags))
            if dishes:
                days[str(idx)] = dishes
        if days:
            weeks.append(WeekMenu(year=year_for_week(week, today), week=week,
                                  week_known=True, days=days, notes=notes))
    if not weeks:
        raise ParseError("Pocket: hittade inga veckor med rätter")
    weeks.sort(key=lambda w: (w.year, w.week))
    return weeks


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
