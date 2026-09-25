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
    assert html.count("<script>") == 1  # only the drag enhancement, inline
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


def test_all_text_is_16px_except_footer_and_badges():
    css = CSS + "\n" + _tab_css()
    root_px = 16  # from `html { font-size: 16px; }` in CSS
    assert "html { font-size: 16px; }" in css
    assert "font: 16px/1.5" in css
    sizes = re.findall(r"font-size:\s*([0-9.]+)(px|rem)", css)
    assert sizes, "expected at least one font-size declaration"
    footer = re.search(r"footer \{([^}]*)\}", css).group(1)
    badge = re.search(r"\.tagg \{([^}]*)\}", css).group(1)
    assert "font-size: 14px" in footer  # deliberate exceptions: footer and badges
    assert "font-size: 14px" in badge
    body_css = css.replace(footer, "").replace(badge, "")
    for value, unit in re.findall(r"font-size:\s*([0-9.]+)(px|rem)", body_css):
        px = float(value) if unit == "px" else float(value) * root_px
        assert px == 16, f"font-size {value}{unit} computes to {px}px, expected 16px"


def test_dish_li_has_ratt_and_pris_spans():
    html = render(DATA, date(2026, 9, 25))
    assert '<li><span class="ratt">Pasta</span>' in html
    assert '<span class="pris">130 kr</span>' in html


def test_render_shows_lunch_hours():
    html = render(DATA, date(2026, 9, 25))
    assert '<span class="tider">Lunch 11-14</span>' in html


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
    rgbas = set(re.findall(r"rgba\(([^)]*)\)", css))
    for value in rgbas:  # translucent versions of the two colours only
        r, g, b, _alpha = [x.strip() for x in value.split(",")]
        assert (r, g, b) in {("18", "18", "18"), ("250", "250", "250")}, value
    assert "color: #" not in css.split(":root")[1]  # everything else goes through variables


def test_restaurants_are_grouped_by_space_not_boxes():
    css = render(DATA, date(2026, 9, 25)).split("<style>")[1].split("</style>")[0]
    assert not re.search(r"\.restaurang \{", css)  # no card box at all
    assert "border-top" not in css                  # no separator lines between dishes
    assert ".lista { display: grid; grid-template-columns: 1fr; gap: 48px; }" in css
    for cls in ("tider", "pris", "tagg"):
        rule = re.search(r"\." + cls + r" \{([^}]*)\}", css).group(1)
        assert "color: var(--text-2)" in rule, cls


def test_weekday_tabs_share_one_row():
    css = render(DATA, date(2026, 9, 25)).split("<style>")[1].split("</style>")[0]
    tabs = re.search(r"\.flikar \{([^}]*)\}", css).group(1)
    assert "grid-template-columns: repeat(5, minmax(0, 1fr))" in tabs


def test_single_narrow_column_at_every_width():
    css = CSS + "\n" + _tab_css()
    assert "1fr 1fr" not in css
    assert "main { max-width: 640px;" in css


def test_day_picker_has_sliding_glass_indicator():
    html = render(DATA, date(2026, 9, 25))
    assert '<span class="indikator" aria-hidden="true"></span>' in html
    css = html.split("<style>")[1].split("</style>")[0]
    for n in range(1, 6):
        assert f"#dag-{n}:checked ~ .flikar .indikator {{ transform: translateX({(n - 1) * 100}%); }}" in css
    assert "backdrop-filter: blur(12px)" in css
    assert "prefers-reduced-motion: reduce" in css


def test_day_picker_works_without_script_and_adds_drag_with_it():
    html = render(DATA, date(2026, 9, 25))
    before_script = html.split("<script>")[0]
    # Without JavaScript: radios, labels and sections are all in the HTML.
    for n in range(1, 6):
        assert f'id="dag-{n}"' in before_script and f'for="dag-{n}"' in before_script
        assert f'id="d-{n}"' in before_script
    script = html.split("<script>")[1].split("</script>")[0]
    for needle in ("pointerdown", "pointermove", "pointerup", "pointercancel",
                   "setPointerCapture", "drar"):
        assert needle in script
    css = html.split("<style>")[1].split("</style>")[0]
    assert ".flikar { touch-action: pan-y; }" in css


def test_day_picker_spans_the_full_column():
    css = CSS + "\n" + _tab_css()
    tabs = re.search(r"\.flikar \{ position: relative;([^}]*)\}", css).group(1)
    assert "max-width" not in tabs


def test_footer_uses_secondary_colour_and_new_copy():
    html = render(DATA, date(2026, 9, 25))
    assert "--text-2: rgba(18, 18, 18, 0.595)" in html
    assert "footer { margin: 96px 0 0; font-size: 14px; color: var(--text-2); }" in html
    assert "<footer><p>Uppdaterad 25 september 09:02.</p>" in html
    assert "Dubbelkolla gärna på restaurangens hemsida." in html


def test_cards_show_hours_but_not_address():
    html = render(DATA, date(2026, 9, 25))
    assert 'class="adress"' not in html and "Gatan 1" not in html
    assert '<span class="tider">Lunch 11-14</span>' in html
    css = html.split("<style>")[1].split("</style>")[0]
    tider = re.search(r"\.tider \{([^}]*)\}", css).group(1)
    assert "font-weight" not in tider


def test_tags_are_round_calm_badges():
    css = render(DATA, date(2026, 9, 25)).split("<style>")[1].split("</style>")[0]
    badge = re.search(r"\.tagg \{([^}]*)\}", css).group(1)
    for rule in ("border-radius: 999px", "background: var(--line)", "color: var(--text-2)"):
        assert rule in badge
    assert "border:" not in badge and "box-shadow" not in badge


def test_tag_badge_sits_in_its_own_element_before_the_dish():
    html = render(DATA, date(2026, 9, 21))
    assert '<li><span class="taggar"><span class="tagg">soppa</span></span><span class="ratt">Soppa</span>' in html


def test_badge_sits_between_dish_and_price():
    html = render(DATA, date(2026, 9, 25))
    css = html.split("<style>")[1].split("</style>")[0]
    row = re.search(r"\.restaurang li \{([^}]*)\}", css).group(1)
    assert 'grid-template-areas: "ratt taggar pris"' in row
    assert "tl-" not in html and "devval" not in html
