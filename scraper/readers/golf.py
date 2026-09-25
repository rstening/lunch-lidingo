"""Lidingö Golfrestaurang: Elementor text widget with bold day headings."""
import re
from datetime import date
from typing import Callable, List, Optional

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, year_for_week

LABEL_TAGS = {"buffé": "buffé", "buffe": "buffé", "vegetarisk": "veg",
              "veckans lätta": "lätt", "veckans vegetariska": "veg"}


def _find_container(soup: BeautifulSoup):
    for strong in soup.find_all("strong"):
        if re.match(r"vecka\s+\d+", clean(strong.get_text()), re.I):
            return strong.find_parent("div"), clean(strong.get_text())
    return None, ""


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    container, header = _find_container(soup)
    if container is None:
        raise ParseError("Golfrestaurangen: hittade ingen veckorubrik")
    m = re.search(r"vecka\s+(\d{1,2})", header, re.I)
    week = int(m.group(1))
    year = year_for_week(week, today)

    price: Optional[int] = None
    notes = ""
    days = {}
    current = None
    for p in container.find_all("p"):
        text = clean(p.get_text(" "))
        if not text:
            continue
        strong = p.find("strong")
        label = clean(strong.get_text()) if strong else ""
        if label and label == text:
            # A fully bold line is either a weekday heading or something to skip
            # (Vecka 39, Lördag:, the intro with the price, the allergen legend).
            idx = day_index(text)
            if idx:
                current = idx
                continue
            if "kostar" in text.lower():
                notes = text
                pm = re.search(r"kostar\s*(\d+)", text)
                if pm:
                    price = int(pm.group(1))
            current = None
            continue
        if current is None:
            continue
        if label:
            key = label.rstrip(":").strip().lower()
            tag = LABEL_TAGS.get(key)
            if not tag:
                continue
            rest = clean(text[len(label):].lstrip(": ") if text.startswith(label) else text.replace(label, "", 1))
            rest = rest.lstrip(": ").strip()
            if rest:
                days.setdefault(str(current), []).append(Dish(name=rest, price=price, tags=[tag]))
        else:
            days.setdefault(str(current), []).append(Dish(name=text, price=price))
    if not days:
        raise ParseError("Golfrestaurangen: hittade inga rätter")
    return [WeekMenu(year=year, week=week, week_known=True, days=days, notes=notes)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
