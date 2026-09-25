import re
from datetime import date

from scraper.build import CSS, _tab_css, pick_week, render

DATA = {
    "generated_at": "2026-09-25T07:02:11Z",
    "restaurants": [
        {"id": "a", "name": "Alfa Kök", "url": "https://a.example", "address": "Gatan 1", "lunch_hours": "11-14",
         "last_success": "2026-09-25T07:02:11Z", "error": None,
         "weeks": [{"year": 2026, "week": 39, "week_known": True, "notes": "Ingår kaffe",
                    "days": {"1": [{"name": "Soppa", "price": 120, "tags": ["soppa"]}],
                             "5": [{"name": "Fisk", "price": None, "tags": ["fisk"]},
                                   {"name": "Pasta", "price": 130, "tags": []}]}}]},
        {"id": "b", "name": "Beta Bar", "url": "https://b.example", "address": "Gatan 2",
         "last_success": "2026-09-10T07:00:00Z", "error": "HTTPError: 500",
         "weeks": [{"year": 2026, "week": 38, "week_known": True, "notes": "",
                    "days": {"1": [{"name": "Gammal rätt", "price": None, "tags": []}]}}]},
        {"id": "c", "name": "Gamma Grill", "url": "https://c.example", "address": "",
         "last_success": None, "error": "ParseError: x", "weeks": []},
        {"id": "d", "name": "Delta Deli", "url": "https://d.example", "address": "Gatan 4",
         "last_success": "2026-09-25T07:02:11Z", "error": None,
         "weeks": [{"year": 2026, "week": 40, "week_known": True, "notes": "",
                    "days": {"1": [{"name": "Framtidsrätt", "price": None, "tags": []}]}}]},
    ],
}


def test_pick_week_exact_match():
    week, notice = pick_week(DATA["restaurants"][0], 2026, 39)
    assert week["week"] == 39 and notice is None


def test_pick_week_falls_back_to_latest_with_notice():
    week, notice = pick_week(DATA["restaurants"][1], 2026, 39)
    assert week["week"] == 38
    assert notice == "Visar vecka 38, inte uppdaterad än"


def test_pick_week_none_when_no_weeks():
    assert pick_week(DATA["restaurants"][2], 2026, 39) == (None, None)


def test_pick_week_none_when_only_future_weeks_exist():
    week, notice = pick_week(DATA["restaurants"][3], 2026, 39)
    assert week is None
    assert notice == "Nästa veckas meny finns på restaurangens sida"


def test_pick_week_none_when_latest_is_more_than_one_week_older():
    old = {"weeks": [{"year": 2026, "week": 30, "week_known": True, "days": {}, "notes": ""}]}
    week, notice = pick_week(old, 2026, 39)
    assert week is None
    assert notice == "Ingen aktuell meny, se restaurangens sida"


def test_render_friday():
    html = render(DATA, date(2026, 9, 25))
    assert "<!doctype html>" in html.lower()
    assert "<script" not in html.lower()
    assert 'id="dag-5" checked' in html.replace("  ", " ")
    assert "Fredag 25 september" in html
    assert "Alfa Kök" in html and "Beta Bar" in html and "Gamma Grill" in html
    assert "Delta Deli" in html
    assert "Pasta" in html and "130 kr" in html
    assert "Ingår kaffe" in html
    assert "Kunde inte hämta menyn" in html          # Beta (stale > 7 days) and Gamma
    assert "Nästa veckas meny finns på restaurangens sida" in html  # Delta (week 40 only)
    assert "Ingen meny för den här dagen" in html             # Alfa has no dishes Tue-Thu
    assert "Uppdaterad 25 september 09:02" in html
    assert html.count('class="restaurang"') == 20    # 4 restaurants x 5 days


def test_render_weekend_defaults_to_monday_next_week():
    html = render(DATA, date(2026, 9, 26))
    assert 'id="dag-1" checked' in html.replace("  ", " ")
    assert "Måndag 28 september" in html
    assert "Visar vecka 39, inte uppdaterad än" in html


def test_render_escapes_html():
    data = {"generated_at": "2026-09-25T07:02:11Z", "restaurants": [
        {"id": "x", "name": "<b>X</b>", "url": "https://x", "address": "",
         "last_success": "2026-09-25T07:02:11Z", "error": None,
         "weeks": [{"year": 2026, "week": 39, "week_known": True, "notes": "",
                    "days": {"1": [{"name": "Fisk & <chips>", "price": None, "tags": []}]}}]}]}
    html = render(data, date(2026, 9, 21))
    assert "&lt;b&gt;X&lt;/b&gt;" in html and "Fisk &amp; &lt;chips&gt;" in html


def test_all_font_sizes_are_at_least_18px():
    css = CSS + "\n" + _tab_css()
    root_px = 20  # from `html { font-size: 20px; }` in CSS
    sizes = re.findall(r"font-size:\s*([0-9.]+)(px|rem)", css)
    assert sizes, "expected at least one font-size declaration"
    for value, unit in sizes:
        px = float(value) if unit == "px" else float(value) * root_px
        assert px >= 18, f"font-size {value}{unit} computes to {px}px, below 18px minimum"


def test_dish_li_has_ratt_and_pris_spans():
    html = render(DATA, date(2026, 9, 25))
    assert '<li><span class="ratt">' in html
    assert '<span class="pris">130 kr</span>' in html


def test_render_shows_lunch_hours():
    html = render(DATA, date(2026, 9, 25))
    assert '<p class="tider">Lunch 11-14</p>' in html


def test_page_copy_has_no_long_dashes():
    html = render(DATA, date(2026, 9, 25))
    assert "–" not in html and "—" not in html


def test_page_uses_self_hosted_geist():
    html = render(DATA, date(2026, 9, 25))
    assert 'url("fonts/Geist-Variable.woff2")' in html
    assert '"Geist", -apple-system' in html
    assert "fonts.googleapis" not in html and "https://" not in html.split("<main>")[0]


def test_page_uses_only_the_two_brand_colours():
    html = render(DATA, date(2026, 9, 25))
    css = html.split("<style>")[1].split("</style>")[0]
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{3,6}\b", css)}
    assert hexes == {"#fafafa", "#121212"}, hexes
    rgbas = set(re.findall(r"rgba\([^)]*\)", css))
    assert rgbas == {"rgba(18, 18, 18, 0.068)"}, rgbas
    assert "color: #" not in css.split(":root")[1]  # everything else goes through variables
