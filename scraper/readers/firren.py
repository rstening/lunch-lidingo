"""Firren bistro: one dish per weekday in Bootstrap cards."""
import re
from collections import Counter
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    days = {}
    dates = []
    for card in soup.select(".store-item"):
        title = card.select_one(".card-title")
        if not title:
            continue
        idx = day_index(clean(title.get_text()))
        if not idx:
            continue
        dishes = []
        for h6 in card.select("h6"):
            name = clean(h6.get_text(" "))
            if not name:
                continue
            desc_el = h6.find_next_sibling("p")
            desc = clean(desc_el.get_text(" ")) if desc_el else ""
            dishes.append(Dish(name=clean(f"{name} {desc}")))
        m = re.search(r"\d{4}-\d{2}-\d{2}", card.get_text())
        if m:
            try:
                dates.append(date.fromisoformat(m.group(0)))
            except ValueError:
                pass
        if dishes:
            days[str(idx)] = dishes
    if not days:
        raise ParseError("Firren: hittade inga rätter")
    if dates:
        (year, week), _ = Counter(iso_week(d) for d in dates).most_common(1)[0]
        known = True
    else:
        year, week = iso_week(today)
        known = False
    return [WeekMenu(year=year, week=week, week_known=known, days=days)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
