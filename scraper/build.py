"""Render data/menus.json into docs/index.html (static, no JavaScript)."""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from scraper.weeks import (DAY_NAMES, DAY_SHORT, display_date, format_date,
                           iso_week, week_dates)

DATA_PATH = Path("data/menus.json")
OUT_PATH = Path("docs/index.html")
TZ = ZoneInfo("Europe/Stockholm")
STALE_AFTER = timedelta(days=7)

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
html { font-size: 20px; }
body { margin: 0; padding: 16px; font: 20px/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1a1a1a; background: #f6f4ef; }
main { max-width: 1100px; margin: 0 auto; }
header h1 { font-size: 1.9rem; margin: 0 0 4px; }
header p { margin: 0 0 12px; color: #444; }
.dagval { position: absolute; opacity: 0; pointer-events: none; }
.flikar { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 20px; }
.flikar label { display: block; padding: 10px 14px; border: 2px solid #1a1a1a; border-radius: 8px;
                background: #fff; cursor: pointer; font-weight: 600; }
.flikar label small { display: block; font-weight: 400; font-size: 0.9rem; color: #444; }
.dag { display: none; }
.dag h2.dagrubrik { font-size: 1.5rem; margin: 0 0 14px; }
.lista { display: grid; grid-template-columns: 1fr; gap: 14px; }
@media (min-width: 800px) { .lista { grid-template-columns: 1fr 1fr; } }
.restaurang { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 14px 16px; }
.restaurang h3 { font-size: 1.3rem; margin: 0 0 2px; }
.restaurang h3 a { color: #0b4f9c; text-decoration: none; }
.restaurang h3 a:hover { text-decoration: underline; }
.adress { margin: 0 0 8px; color: #555; font-size: 0.9rem; }
.restaurang ul { list-style: none; margin: 0; padding: 0; }
.restaurang li { display: flex; justify-content: space-between; gap: 12px; align-items: baseline;
                 padding: 6px 0; border-top: 1px solid #eee; }
.ratt { flex: 1 1 auto; min-width: 0; }
.tagg { display: inline-block; font-size: 0.9rem; text-transform: uppercase; letter-spacing: .03em;
        background: #e9efe4; color: #2f4f2f; border-radius: 4px; padding: 1px 6px; margin-right: 6px; }
.pris { color: #444; white-space: nowrap; flex-shrink: 0; }
.notis { margin: 8px 0 0; color: #8a4b00; font-size: 0.9rem; }
.info { margin: 8px 0 0; color: #555; font-size: 0.9rem; }
.tom { margin: 4px 0 0; color: #666; font-style: italic; }
footer { margin: 28px 0 8px; color: #666; font-size: 0.9rem; }
"""


def _tab_css() -> str:
    rules = []
    for n in range(1, 6):
        rules.append(f"#dag-{n}:checked ~ #d-{n} {{ display: block; }}")
        rules.append(f'#dag-{n}:checked ~ .flikar label[for="dag-{n}"] '
                     "{ background: #1a1a1a; color: #fff; }")
        rules.append(f'#dag-{n}:checked ~ .flikar label[for="dag-{n}"] small {{ color: #ddd; }}')
        rules.append(f'#dag-{n}:focus-visible ~ .flikar label[for="dag-{n}"] '
                     "{ outline: 3px solid #0b4f9c; outline-offset: 2px; }")
    return "\n".join(rules)


def pick_week(restaurant: dict, year: int, week: int) -> Tuple[Optional[dict], Optional[str]]:
    weeks = restaurant.get("weeks") or []
    if not weeks:
        return None, None
    for w in weeks:
        if (w.get("year"), w.get("week")) == (year, week):
            return w, None
    latest = max(weeks, key=lambda w: (w.get("year", 0), w.get("week", 0)))
    latest_key = (latest["year"], latest["week"])
    this_key = (year, week)
    if latest_key > this_key:
        # Only weeks newer than today's exist: never show a future week as
        # today's lunch.
        return None, "Nästa veckas meny finns på restaurangens sida"
    monday = date.fromisocalendar(year, week, 1)
    one_week_older = (monday - timedelta(weeks=1)).isocalendar()[:2]
    if latest_key == one_week_older:
        return latest, f"Visar vecka {latest['week']}, ej uppdaterad än"
    return None, "Ingen aktuell meny, se restaurangens sida"


def _is_stale(restaurant: dict, now: datetime) -> bool:
    if not restaurant.get("error"):
        return False
    last = restaurant.get("last_success")
    if not last:
        return True
    dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return now - dt > STALE_AFTER


def _last_success_text(restaurant: dict) -> Optional[str]:
    last = restaurant.get("last_success")
    if not restaurant.get("error") or not last:
        return None
    dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(TZ)
    return f"Senast hämtad {format_date(dt.date())}"


def _dish_html(d: dict) -> str:
    ratt = []
    for t in d.get("tags") or []:
        ratt.append(f'<span class="tagg">{escape(t)}</span>')
    ratt.append(escape(d.get("name", "")))
    parts = ["<li>", f'<span class="ratt">{"".join(ratt)}</span>']
    if d.get("price") is not None:
        parts.append(f'<span class="pris">{int(d["price"])} kr</span>')
    parts.append("</li>")
    return "".join(parts)


def _card_html(r: dict, week: Optional[dict], notice: Optional[str],
               day: int, now: datetime) -> str:
    out = ['<article class="restaurang">']
    out.append(f'<h3><a href="{escape(r["url"], quote=True)}">{escape(r["name"])}</a></h3>')
    if r.get("address"):
        out.append(f'<p class="adress">{escape(r["address"])}</p>')
    if _is_stale(r, now):
        out.append('<p class="tom">Kunde inte hämta menyn, se restaurangens sida.</p>')
        out.append("</article>")
        return "\n".join(out)
    if week is None:
        text = notice or "Kunde inte hämta menyn, se restaurangens sida."
        out.append(f'<p class="tom">{escape(text)}</p>')
        out.append("</article>")
        return "\n".join(out)
    dishes = (week.get("days") or {}).get(str(day)) or []
    if dishes:
        out.append("<ul>" + "".join(_dish_html(d) for d in dishes) + "</ul>")
    else:
        out.append('<p class="tom">Ingen lunch angiven.</p>')
    notices = [n for n in (notice, _last_success_text(r)) if n]
    if notices:
        out.append(f'<p class="notis">{escape(". ".join(notices))}</p>')
    if week.get("notes"):
        out.append(f'<p class="info">{escape(week["notes"])}</p>')
    out.append("</article>")
    return "\n".join(out)


def render(data: dict, today: date) -> str:
    shown = display_date(today)
    year, week = iso_week(shown)
    dates = week_dates(year, week)
    now = datetime.strptime(data["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    updated = now.astimezone(TZ)
    restaurants = data.get("restaurants", [])
    restaurant_weeks = [(r,) + pick_week(r, year, week) for r in restaurants]

    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="sv"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append("<title>Dagens lunch på Lidingö</title>")
    parts.append(f"<style>{CSS}\n{_tab_css()}</style></head><body><main>")
    for n in range(1, 6):
        checked = " checked" if n == shown.isoweekday() else ""
        parts.append(f'<input type="radio" name="dag" class="dagval" id="dag-{n}"{checked}>')
    parts.append("<header><h1>Dagens lunch på Lidingö</h1>")
    parts.append(f"<p>{DAY_NAMES[shown.isoweekday() - 1].capitalize()} {format_date(shown)}, "
                 f"vecka {week}. Uppdaterad {format_date(updated.date())} {updated:%H:%M}.</p></header>")
    parts.append('<nav class="flikar">')
    for n in range(1, 6):
        d = dates[n - 1]
        parts.append(f'<label for="dag-{n}">{DAY_SHORT[n - 1]}<small>{d.day}/{d.month}</small></label>')
    parts.append("</nav>")
    for n in range(1, 6):
        parts.append(f'<section class="dag" id="d-{n}">')
        parts.append(f'<h2 class="dagrubrik">{DAY_NAMES[n - 1].capitalize()} {format_date(dates[n - 1])}</h2>')
        parts.append('<div class="lista">')
        for r, w, notice in restaurant_weeks:
            parts.append(_card_html(r, w, notice, n, now))
        parts.append("</div></section>")
    parts.append("<footer>Menyerna hämtas automatiskt varje morgon från restaurangernas egna "
                 "sidor. Fel kan förekomma, kontrollera gärna med restaurangen.</footer>")
    parts.append("</main></body></html>")
    return "\n".join(parts) + "\n"


def main(argv=None) -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    today = datetime.now(TZ).date()
    if argv and len(argv) > 0:
        today = date.fromisoformat(argv[0])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(data, today), encoding="utf-8")
    print(f"Skrev {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
