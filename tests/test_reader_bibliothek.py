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


def test_read_skips_one_failing_pdf_and_keeps_the_rest():
    html = (FIX / "bibliothek.html").read_bytes()
    pdf = (FIX / "bibliothek-v40-2026.pdf").read_bytes()

    def fake_get(url, headers=None):
        if "Lunch-v40-2026.pdf" in url:
            raise RuntimeError("boom")
        return pdf if url.endswith(".pdf") or ".pdf?" in url else html

    weeks = bibliothek.read(fake_get, "https://bibliothek.nu/menyer", TODAY)
    assert [(w.year, w.week) for w in weeks] == [(2026, 39), (2026, 41)]


def test_read_raises_when_every_pdf_fails():
    import pytest
    from scraper.model import ParseError
    html = (FIX / "bibliothek.html").read_bytes()

    def fake_get(url, headers=None):
        if url.endswith(".pdf") or ".pdf?" in url:
            raise RuntimeError("boom")
        return html

    with pytest.raises(ParseError):
        bibliothek.read(fake_get, "https://bibliothek.nu/menyer", TODAY)


def test_parse_pdf_raises_when_layout_is_not_recognised(monkeypatch):
    import pytest
    from scraper.model import ParseError

    class FakeWord(dict):
        pass

    class FakePage:
        width = 595
        height = 842

        def extract_words(self):
            # Plain text with none of the kött/fisk/veg/soppa category labels:
            # a layout change that leaves nothing to tag dishes with.
            return [
                {"text": "Något", "top": 100, "x0": 10, "bottom": 110},
                {"text": "helt", "top": 100, "x0": 60, "bottom": 110},
                {"text": "annat", "top": 100, "x0": 100, "bottom": 110},
                {"text": "220kr", "top": 100, "x0": 150, "bottom": 110},
            ]

    class FakeDoc:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(bibliothek.pdfplumber, "open", lambda *a, **k: FakeDoc())
    with pytest.raises(ParseError):
        bibliothek.parse_pdf(b"not really a pdf")
