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
@font-face { font-family: "Geist"; src: url("fonts/Geist-Variable.woff2") format("woff2");
             font-weight: 100 900; font-style: normal; font-display: swap; }
:root { color-scheme: light; --bg: #fafafa; --text: #121212; --line: rgba(18, 18, 18, 0.068); }
* { box-sizing: border-box; }
html { font-size: 16px; }
body { margin: 0; padding: 16px; font: 16px/1.5 "Geist", -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: var(--text); background: var(--bg); }
main { max-width: 640px; margin: 0 auto; }
header h1 { font-size: 1rem; margin: 0 0 4px; }
header p { margin: 0 0 12px; }
.dagval { position: absolute; opacity: 0; pointer-events: none; }
.flikar { position: relative; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0;
          margin: 16px 0 24px; padding: 4px; border-radius: 999px;
          background: var(--line); box-shadow: inset 0 1px 2px rgba(18, 18, 18, 0.06);
          -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent; }
.flikar label { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center;
                justify-content: center; min-height: 52px; padding: 6px 2px; border-radius: 999px;
                cursor: pointer; font-weight: 500; line-height: 1.2; text-align: center; }
.flikar label small { display: block; font-weight: 400; font-size: 1rem; }
.indikator { position: absolute; z-index: 0; top: 4px; bottom: 4px; left: 4px; width: calc((100% - 8px) / 5);
             border-radius: 999px; transition: transform 280ms cubic-bezier(0.32, 0.72, 0, 1); }
.indikator::before { content: ""; position: absolute; inset: 0; border-radius: inherit;
                     background: rgba(250, 250, 250, 0.72);
                     -webkit-backdrop-filter: blur(12px) saturate(180%); backdrop-filter: blur(12px) saturate(180%);
                     border: 1px solid rgba(250, 250, 250, 0.9);
                     box-shadow: 0 1px 1px rgba(18, 18, 18, 0.04), 0 4px 14px rgba(18, 18, 18, 0.1),
                                 inset 0 1px 0 rgba(250, 250, 250, 1), inset 0 -1px 1px rgba(18, 18, 18, 0.05);
                     transition: transform 160ms ease-out; }
.flikar:has(label:active) .indikator::before { transform: scale(0.96); }
.flikar { touch-action: pan-y; }
.flikar.drar { cursor: grabbing; }
.flikar.drar .indikator { transition: transform 60ms ease-out; }
.flikar.drar .indikator::before { transform: scale(1.06); }
@media (prefers-reduced-motion: reduce) { .indikator, .indikator::before { transition: none; } }
.dag { display: none; }
.dag h2.dagrubrik { font-size: 1rem; margin: 0 0 14px; }
.lista { display: grid; grid-template-columns: 1fr; gap: 14px; }
.restaurang { background: var(--bg); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.restaurang h3 { font-size: 1rem; margin: 0 0 2px; }
.restaurang h3 a { color: var(--text); text-decoration: none; }
.restaurang h3 a:hover { text-decoration: underline; }
.adress { margin: 0; font-size: 1rem; }
.tider { margin: 0 0 8px; font-size: 1rem; font-weight: 600; }
.restaurang ul { list-style: none; margin: 0; padding: 0; }
.restaurang li { display: flex; justify-content: space-between; gap: 12px; align-items: baseline;
                 padding: 6px 0; border-top: 1px solid var(--line); }
.ratt { flex: 1 1 auto; min-width: 0; }
.tagg { display: inline-block; font-size: 1rem; text-transform: uppercase; letter-spacing: .03em;
        background: var(--line); border-radius: 4px; padding: 1px 6px; margin-right: 6px; }
.pris { white-space: nowrap; flex-shrink: 0; }
.notis { margin: 8px 0 0; font-size: 1rem; }
.info { margin: 8px 0 0; font-size: 1rem; }
.tom { margin: 4px 0 0; font-style: italic; }
footer { margin: 28px 0 8px; font-size: 1rem; }
"""


DRAG_JS = """
(function () {
  var nav = document.querySelector(".flikar");
  var pill = nav && nav.querySelector(".indikator");
  if (!nav || !pill || !window.PointerEvent) return;
  var radios = [1, 2, 3, 4, 5].map(function (n) { return document.getElementById("dag-" + n); });
  var start = null, moved = false, samples = [], pos = 0;

  function seg() { return (nav.clientWidth - 8) / 5; }
  function current() { for (var i = 0; i < 5; i++) { if (radios[i].checked) return i; } return 0; }
  function damp(d) { return d * 0.25; }

  nav.addEventListener("pointerdown", function (e) {
    if (e.button !== 0) return;
    start = { x: e.clientX, y: e.clientY, id: e.pointerId };
    moved = false;
    samples = [];
  });

  nav.addEventListener("pointermove", function (e) {
    if (!start || e.pointerId !== start.id) return;
    var dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (!moved) {
      if (Math.abs(dx) < 6 || Math.abs(dx) < Math.abs(dy)) return;
      moved = true;
      try { nav.setPointerCapture(e.pointerId); } catch (err) { /* pointer already gone */ }
      nav.classList.add("drar");
    }
    var w = seg(), max = 4 * w;
    var x = e.clientX - nav.getBoundingClientRect().left - 4 - w / 2;
    if (x < 0) x = -damp(-x);
    if (x > max) x = max + damp(x - max);
    pos = x;
    pill.style.transform = "translateX(" + x + "px)";
    var now = performance.now();
    samples.push([now, e.clientX]);
    while (samples.length > 2 && now - samples[0][0] > 100) samples.shift();
  });

  function finish(e) {
    if (!start || e.pointerId !== start.id) return;
    var wasDrag = moved;
    start = null;
    if (!wasDrag) return;
    var w = seg(), target = Math.round(pos / w);
    var fresh = samples.length > 1 && performance.now() - samples[samples.length - 1][0] < 80;
    if (fresh) {  // only a movement that is still going on at release counts as a flick
      var a = samples[0], b = samples[samples.length - 1];
      var v = (b[1] - a[1]) / Math.max(1, b[0] - a[0]);
      if (Math.abs(v) > 0.4) target = v > 0 ? Math.floor(pos / w) + 1 : Math.ceil(pos / w) - 1;
    }
    target = Math.max(0, Math.min(4, target));
    nav.classList.remove("drar");
    pill.style.transform = "";
    radios[target].checked = true;
    radios[target].dispatchEvent(new Event("change", { bubbles: true }));
  }
  nav.addEventListener("pointerup", finish);
  nav.addEventListener("pointercancel", finish);

  // A drag must not also count as a tap on the label under the finger.
  nav.addEventListener("click", function (e) {
    if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; }
  }, true);
})();
"""


def _tab_css() -> str:
    rules = []
    for n in range(1, 6):
        rules.append(f"#dag-{n}:checked ~ #d-{n} {{ display: block; }}")
        rules.append(f"#dag-{n}:checked ~ .flikar .indikator "
                     f"{{ transform: translateX({(n - 1) * 100}%); }}")
        rules.append(f'#dag-{n}:checked ~ .flikar label[for="dag-{n}"] {{ font-weight: 600; }}')
        rules.append(f"#dag-{n}:focus-visible ~ .flikar .indikator::before "
                     "{ outline: 2px solid var(--text); outline-offset: 2px; }")
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
        return latest, f"Visar vecka {latest['week']}, inte uppdaterad än"
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
    if r.get("lunch_hours"):
        out.append(f'<p class="tider">Lunch {escape(r["lunch_hours"])}</p>')
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
        out.append('<p class="tom">Ingen meny för den här dagen.</p>')
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
    parts.append('<nav class="flikar" aria-label="Välj dag">')
    parts.append('<span class="indikator" aria-hidden="true"></span>')
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
                 "sidor, så det kan bli fel ibland. Dubbelkolla gärna med restaurangen.</footer>")
    parts.append(f"</main><script>{DRAG_JS}</script></body></html>")
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
