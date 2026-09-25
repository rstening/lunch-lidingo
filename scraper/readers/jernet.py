"""Brasserie Jernet: React app; the weekly lunch lives in a public Supabase table."""
import json
import re
from datetime import date, datetime
from typing import Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import iso_week

BUNDLE_RE = re.compile(r'<script[^>]+src="([^"]*/assets/index-[^"]+\.js)"', re.I)
SUPABASE_URL_RE = re.compile(r"https://[a-z0-9]+\.supabase\.co")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
TZ = ZoneInfo("Europe/Stockholm")
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


def _row_week(row: dict, fallback: Tuple[int, int]) -> Tuple[int, int]:
    """The ISO week a row belongs to: the week it was last edited, in Swedish time.

    Jernet fills in each weekday's row on that same day, so a row last edited
    before this week's Monday still holds last week's dish.
    """
    stamp = row.get("updated_at")
    if not stamp:
        return fallback
    try:
        edited = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if edited.tzinfo is None:
        return fallback
    year, week, _ = edited.astimezone(TZ).isocalendar()
    return min((year, week), fallback)  # a clock ahead of ours never means next week


def parse_rows(rows: list, today: date) -> List[WeekMenu]:
    this_week = iso_week(today)
    by_week: Dict[Tuple[int, int], Dict[str, List[Dish]]] = {}
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
            by_week.setdefault(_row_week(row, this_week), {})[str(idx)] = dishes
    if not by_week:
        raise ParseError("Jernet: inga rätter i API-svaret")
    return [WeekMenu(year=y, week=w, week_known=True, days=days)
            for (y, w), days in sorted(by_week.items())]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    html = get(url).decode("utf-8", errors="replace")
    bundle = get(find_bundle_url(html, url)).decode("utf-8", errors="replace")
    base, key = find_supabase(bundle)
    api = f"{base}/rest/v1/lunch_menu?select=*&order=day_of_week.asc"
    raw = get(api, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    return parse_rows(json.loads(raw.decode("utf-8")), today)
