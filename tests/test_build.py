from datetime import date

from scraper.build import pick_week, render

DATA = {
    "generated_at": "2026-09-25T07:02:11Z",
    "restaurants": [
        {"id": "a", "name": "Alfa Kök", "url": "https://a.example", "address": "Gatan 1",
         "last_success": "2026-09-25T07:02:11Z", "error": None,
         "weeks": [{"year": 2026, "week": 39, "week_known": True, "notes": "Ingår kaffe",
                    "days": {"1": [{"name": "Soppa", "price": 120, "tags": ["soppa"]}],
                             "5": [{"name": "Fisk", "price": None, "tags": ["fisk"]},
                                   {"name": "Pasta", "price": 130, "tags": []}]}}]},
        {"id": "b", "name": "Beta Bar", "url": "https://b.example", "address": "Gatan 2",
         "last_success": "2026-09-10T07:00:00Z", "error": "HTTPError: 500",
         "weeks": [{"year": 2026, "week": 37, "week_known": True, "notes": "",
                    "days": {"1": [{"name": "Gammal rätt", "price": None, "tags": []}]}}]},
        {"id": "c", "name": "Gamma Grill", "url": "https://c.example", "address": "",
         "last_success": None, "error": "ParseError: x", "weeks": []},
    ],
}


def test_pick_week_exact_match():
    week, notice = pick_week(DATA["restaurants"][0], 2026, 39)
    assert week["week"] == 39 and notice is None


def test_pick_week_falls_back_to_latest_with_notice():
    week, notice = pick_week(DATA["restaurants"][1], 2026, 39)
    assert week["week"] == 37
    assert notice == "Visar vecka 37, ej uppdaterad än"


def test_pick_week_none_when_no_weeks():
    assert pick_week(DATA["restaurants"][2], 2026, 39) == (None, None)


def test_render_friday():
    html = render(DATA, date(2026, 9, 25))
    assert "<!doctype html>" in html.lower()
    assert "<script" not in html.lower()
    assert 'id="dag-5" checked' in html.replace("  ", " ")
    assert "Fredag 25 september" in html
    assert "Alfa Kök" in html and "Beta Bar" in html and "Gamma Grill" in html
    assert "Pasta" in html and "130 kr" in html
    assert "Ingår kaffe" in html
    assert "Kunde inte hämta menyn" in html          # Beta (stale > 7 days) and Gamma
    assert "Ingen lunch angiven" in html             # Alfa has no dishes Tue-Thu
    assert "Uppdaterad 25 september 09:02" in html
    assert html.count('class="restaurang"') == 15    # 3 restaurants x 5 days


def test_render_weekend_defaults_to_monday_next_week():
    html = render(DATA, date(2026, 9, 26))
    assert 'id="dag-1" checked' in html.replace("  ", " ")
    assert "Måndag 28 september" in html
    assert "Visar vecka 39, ej uppdaterad än" in html


def test_render_escapes_html():
    data = {"generated_at": "2026-09-25T07:02:11Z", "restaurants": [
        {"id": "x", "name": "<b>X</b>", "url": "https://x", "address": "",
         "last_success": "2026-09-25T07:02:11Z", "error": None,
         "weeks": [{"year": 2026, "week": 39, "week_known": True, "notes": "",
                    "days": {"1": [{"name": "Fisk & <chips>", "price": None, "tags": []}]}}]}]}
    html = render(data, date(2026, 9, 21))
    assert "&lt;b&gt;X&lt;/b&gt;" in html and "Fisk &amp; &lt;chips&gt;" in html
