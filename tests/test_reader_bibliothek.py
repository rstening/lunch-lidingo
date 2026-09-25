from datetime import date
from pathlib import Path

from scraper.readers import bibliothek

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_find_pdf_links():
    links = bibliothek.find_pdf_links((FIX / "bibliothek.html").read_text(encoding="utf-8"),
                                      "https://bibliothek.nu/menyer")
    assert [(y, w) for y, w, _ in links] == [(2026, 39), (2026, 40), (2026, 41)]
    assert all(u.startswith("https://static.thatsup.website/") for _, _, u in links)
    assert "&amp;" not in links[0][2]


def test_parse_pdf_four_blocks():
    dishes, notes = bibliothek.parse_pdf((FIX / "bibliothek-v40-2026.pdf").read_bytes())
    by_tag = {d.tags[0]: d for d in dishes if d.tags}
    assert set(by_tag) == {"kött", "fisk", "veg", "soppa"}
    assert by_tag["kött"].name == "Bakad kycklinglårfilé dragongräddsås, rostad spetskål och gourmetpotatis"
    assert by_tag["kött"].price == 185
    assert by_tag["fisk"].name.startswith("Gravad lax")
    assert by_tag["veg"].price == 175
    assert by_tag["soppa"].name.startswith("Rotselleri & misosoppa")
    assert "sallad" in notes.lower()


def test_read_builds_week_menus():
    html = (FIX / "bibliothek.html").read_bytes()
    pdf = (FIX / "bibliothek-v40-2026.pdf").read_bytes()

    def fake_get(url, headers=None):
        return pdf if url.endswith(".pdf") or ".pdf?" in url else html

    weeks = bibliothek.read(fake_get, "https://bibliothek.nu/menyer", TODAY)
    assert [(w.year, w.week) for w in weeks] == [(2026, 39), (2026, 40), (2026, 41)]
    w = weeks[1]
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    assert len(w.days["1"]) == 4
    assert len(w.days["5"]) == 5
    assert w.days["5"][-1].name.startswith("Steak minute") and w.days["5"][-1].price == 245


def test_read_without_pdfs_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        bibliothek.read(lambda url, headers=None: b"<html></html>", "https://bibliothek.nu/menyer", TODAY)
