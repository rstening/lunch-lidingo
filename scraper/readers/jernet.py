"""Brasserie Jernet: React app; the weekly lunch lives in a public Supabase table."""
import json
import re
from datetime import date
from typing import Callable, List, Optional, Tuple
from urllib.parse import urljoin

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import iso_week

BUNDLE_RE = re.compile(r'<script[^>]+src="([^"]*/assets/index-[^"]+\.js)"', re.I)
SUPABASE_URL_RE = re.compile(r"https://[a-z0-9]+\.supabase\.co")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
FIELDS = [("meat_name", "meat_price", "kött"),
          ("fish_name", "fish_price", "fisk"),
          ("vegetarian_name", "vegetarian_price", "veg")]


def find_bundle_url(html: str, base_url: str) -> str:
    m = BUNDLE_RE.search(html)
    if not m:
        raise ParseError("Jernet: hittade ingen JS-bundle")
    return urljoin(base_url, m.group(1))


def find_supabase(js: str) -> Tuple[str, str]:
    u = SUPABASE_URL_RE.search(js)
    k = JWT_RE.search(js)
    if not u or not k:
        raise ParseError("Jernet: hittade inte Supabase-adress eller nyckel")
    return u.group(0), k.group(0)


def _price(value) -> Optional[int]:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def parse_rows(rows: list, today: date) -> List[WeekMenu]:
    days = {}
    for row in rows:
        try:
            idx = int(row.get("day_of_week"))
        except (TypeError, ValueError):
            continue
        if not 1 <= idx <= 5:
            continue
        dishes = []
        for name_key, price_key, tag in FIELDS:
            name = clean(str(row.get(name_key) or ""))
            if name:
                dishes.append(Dish(name=name, price=_price(row.get(price_key)), tags=[tag]))
        if dishes:
            days[str(idx)] = dishes
    if not days:
        raise ParseError("Jernet: inga rätter i API-svaret")
    year, week = iso_week(today)
    return [WeekMenu(year=year, week=week, week_known=False, days=days)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    html = get(url).decode("utf-8", errors="replace")
    bundle = get(find_bundle_url(html, url)).decode("utf-8", errors="replace")
    base, key = find_supabase(bundle)
    api = f"{base}/rest/v1/lunch_menu?select=*&order=day_of_week.asc"
    raw = get(api, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    return parse_rows(json.loads(raw.decode("utf-8")), today)
