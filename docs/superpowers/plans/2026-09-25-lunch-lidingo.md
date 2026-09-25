# Lunch Lidingö Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static web page listing today's lunch at seven Lidingö restaurants, rebuilt every morning by a Python scraper in GitHub Actions and served by GitHub Pages.

**Architecture:** `python -m scraper` runs one reader per restaurant (each reader turns HTML/PDF/JSON into `WeekMenu` objects), merges results with the previous `data/menus.json` so failures keep the last good menu, then `python -m scraper.build` renders `docs/index.html` (pure HTML+CSS, no JavaScript). Readers are pure functions over bytes/strings so they are tested against saved fixtures in `tests/fixtures/`.

**Tech Stack:** Python 3.9+ (must run on the local 3.9.6 and on Actions 3.12), requests, beautifulsoup4, pdfplumber, PyYAML, pytest. GitHub Actions + GitHub Pages (branch `main`, folder `/docs`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-25-lunch-lidingo-design.md`. Read it first.
- Python syntax must work on 3.9: use `Optional[X]` / `List[X]` from `typing` in annotations that are evaluated, no `X | None`, no `match`. Built-in generics `list[str]` are fine inside dataclass annotations (PEP 585 works on 3.9) but to keep it simple use `typing` everywhere.
- Local interpreter: `.venv/bin/python` (already created with all dependencies). Run tests with `.venv/bin/python -m pytest`.
- Working directory for all commands: `/Users/richardstening/Desktop/Lunch LO` (the git repo root).
- Git identity is already set locally (Richard Stening / rstening@users.noreply.github.com). Never push in this plan; never touch the `rillesten` account. Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Readers signature: `read(get, url, today) -> List[WeekMenu]` where `get(url, headers=None) -> bytes`. A reader that finds zero dishes must raise `ParseError`.
- `days` keys are strings `"1"`..`"5"` (ISO weekday). Tags come from `{"veg","fisk","kött","soppa","buffé","lätt"}`.
- All user-facing text in the HTML is Swedish. No JavaScript, no external fonts/scripts/stylesheets in `docs/index.html`.
- Fixtures already exist in `tests/fixtures/` (saved 2026-09-25): `firren.html`, `ronneberga.html`, `golf.html`, `pocket.html`, `saluhallen.html`, `bibliothek.html`, `bibliothek-v40-2026.pdf`, `jernet.html`, `jernet-lunch_menu.json`. Do not modify them.

---

## File structure

| File | Responsibility |
|---|---|
| `requirements.txt` | Runtime + test dependencies |
| `restaurants.yaml` | Ordered list of restaurants: id, name, address, url, reader |
| `scraper/__init__.py` | Empty package marker |
| `scraper/model.py` | `Dish`, `WeekMenu`, `ParseError`, `clean()` text helper |
| `scraper/weeks.py` | ISO week helpers, Swedish day names, `day_index`, `year_for_week`, `display_date` |
| `scraper/fetch.py` | `get(url, headers=None) -> bytes` with timeout and user-agent |
| `scraper/readers/__init__.py` | Empty |
| `scraper/readers/firren.py` … `jernet.py` | One reader per restaurant |
| `scraper/merge.py` | `merge(previous, restaurants, results, now) -> dict` |
| `scraper/__main__.py` | CLI: load yaml, run readers, merge, write `data/menus.json` |
| `scraper/build.py` | `render(data, today) -> str` and CLI writing `docs/index.html` |
| `tests/test_weeks.py`, `tests/test_model.py`, `tests/test_readers_*.py`, `tests/test_merge.py`, `tests/test_build.py` | Tests |
| `.github/workflows/test.yml` | pytest on push |
| `.github/workflows/daily.yml` | Scheduled scrape + build + commit |
| `README.md` | Short Swedish description and the manual setup steps |

---

### Task 1: Project skeleton, model and week helpers

**Files:**
- Create: `requirements.txt`, `scraper/__init__.py`, `scraper/readers/__init__.py`, `scraper/model.py`, `scraper/weeks.py`, `tests/__init__.py`
- Test: `tests/test_model.py`, `tests/test_weeks.py`

**Interfaces:**
- Produces: `Dish(name: str, price: Optional[int]=None, tags: List[str]=[])`, `WeekMenu(year: int, week: int, week_known: bool, days: Dict[str, List[Dish]], notes: str="")`, `ParseError(Exception)`, `clean(text: str) -> str`.
- Produces: `iso_week(d: date) -> Tuple[int,int]`, `day_index(text: str) -> Optional[int]`, `year_for_week(week: int, today: date) -> int`, `display_date(today: date) -> date`, `week_dates(year: int, week: int) -> List[date]`, `DAY_NAMES`, `DAY_SHORT`.

- [ ] **Step 1: Write requirements and package markers**

`requirements.txt`:
```
requests>=2.31
beautifulsoup4>=4.12
pdfplumber>=0.11
PyYAML>=6.0
pytest>=8.0
```

Create empty files `scraper/__init__.py`, `scraper/readers/__init__.py`, `tests/__init__.py`.

- [ ] **Step 2: Write failing tests for model and weeks**

`tests/test_model.py`:
```python
from scraper.model import Dish, WeekMenu, clean


def test_clean_collapses_whitespace_and_nbsp():
    assert clean("  Scampi\xa0Indiana \n med   ris ") == "Scampi Indiana med ris"


def test_dish_defaults():
    d = Dish("Köttbullar")
    assert d.price is None
    assert d.tags == []


def test_weekmenu_holds_days():
    w = WeekMenu(year=2026, week=40, week_known=True, days={"1": [Dish("Soppa")]})
    assert w.days["1"][0].name == "Soppa"
    assert w.notes == ""
```

`tests/test_weeks.py`:
```python
from datetime import date

from scraper.weeks import (day_index, display_date, iso_week, week_dates,
                           year_for_week)


def test_iso_week():
    assert iso_week(date(2026, 9, 25)) == (2026, 39)


def test_day_index_swedish_names_case_insensitive():
    assert day_index("Måndag ") == 1
    assert day_index("tisdag") == 2
    assert day_index("ONSDAG") == 3
    assert day_index("Torsdag:") == 4
    assert day_index("fredag") == 5


def test_day_index_rejects_english_and_weekend():
    assert day_index("monday") is None
    assert day_index("Lördag:") is None
    assert day_index("Vecka 39") is None


def test_year_for_week_handles_new_year():
    assert year_for_week(40, date(2026, 9, 25)) == 2026
    assert year_for_week(1, date(2026, 12, 30)) == 2027
    assert year_for_week(52, date(2027, 1, 2)) == 2026


def test_display_date_weekday_is_same_day():
    assert display_date(date(2026, 9, 23)) == date(2026, 9, 23)


def test_display_date_weekend_is_next_monday():
    assert display_date(date(2026, 9, 26)) == date(2026, 9, 28)
    assert display_date(date(2026, 9, 27)) == date(2026, 9, 28)


def test_week_dates():
    ds = week_dates(2026, 40)
    assert ds[0] == date(2026, 9, 28)
    assert ds[4] == date(2026, 10, 2)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_model.py tests/test_weeks.py -q`
Expected: errors with `ModuleNotFoundError: No module named 'scraper.model'`.

- [ ] **Step 4: Implement model.py and weeks.py**

`scraper/model.py`:
```python
"""Shared data types for all readers."""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ParseError(Exception):
    """Raised when a source was fetched but no menu could be read from it."""


def clean(text: str) -> str:
    """Collapse whitespace (including non-breaking spaces) and strip."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


@dataclass
class Dish:
    name: str
    price: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class WeekMenu:
    year: int
    week: int
    week_known: bool
    days: Dict[str, List[Dish]]
    notes: str = ""
```

`scraper/weeks.py`:
```python
"""Week and weekday helpers. All dates are ISO: week starts Monday, weekday 1..7."""
from datetime import date, timedelta
from typing import List, Optional, Tuple

DAY_NAMES = ["måndag", "tisdag", "onsdag", "torsdag", "fredag"]
DAY_SHORT = ["Mån", "Tis", "Ons", "Tor", "Fre"]
MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]


def iso_week(d: date) -> Tuple[int, int]:
    year, week, _ = d.isocalendar()
    return year, week


def day_index(text: str) -> Optional[int]:
    """Return 1..5 if text starts with a Swedish weekday name Mon..Fri, else None."""
    t = text.strip().lower().rstrip(":").strip()
    for i, name in enumerate(DAY_NAMES, start=1):
        if t == name or t.startswith(name + " "):
            return i
    return None


def year_for_week(week: int, today: date) -> int:
    """Guess which ISO year a bare week number refers to, relative to today."""
    year, this_week = iso_week(today)
    if week < this_week - 26:
        return year + 1
    if week > this_week + 26:
        return year - 1
    return year


def display_date(today: date) -> date:
    """The date whose lunch we show: today on weekdays, next Monday on weekends."""
    wd = today.isoweekday()
    if wd > 5:
        return today + timedelta(days=8 - wd)
    return today


def week_dates(year: int, week: int) -> List[date]:
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(5)]


def format_date(d: date) -> str:
    """'25 september' style."""
    return f"{d.day} {MONTHS[d.month - 1]}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_model.py tests/test_weeks.py -q`
Expected: `11 passed`.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scraper tests/__init__.py tests/test_model.py tests/test_weeks.py
git commit -m "Add model and week helpers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: HTTP fetch helper and restaurants.yaml

**Files:**
- Create: `scraper/fetch.py`, `restaurants.yaml`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Produces: `get(url: str, headers: Optional[dict]=None) -> bytes` (raises `requests.HTTPError` on non-2xx), `USER_AGENT`.
- Produces: `restaurants.yaml` entries with keys `id`, `name`, `address`, `url`, `reader`.

- [ ] **Step 1: Write failing test**

`tests/test_fetch.py`:
```python
import scraper.fetch as fetch


class FakeResponse:
    def __init__(self, content=b"ok", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_get_uses_timeout_and_user_agent(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return FakeResponse(b"hello")

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    assert fetch.get("https://example.com/x", headers={"apikey": "k"}) == b"hello"
    assert calls["url"] == "https://example.com/x"
    assert calls["timeout"] == 20
    assert calls["headers"]["apikey"] == "k"
    assert "lunch-lidingo" in calls["headers"]["User-Agent"]


def test_restaurants_yaml_lists_seven_readers():
    import importlib
    import yaml
    entries = yaml.safe_load(open("restaurants.yaml", encoding="utf-8"))
    assert [e["id"] for e in entries] == [
        "firren", "ronneberga", "golf", "pocket", "saluhallen", "bibliothek", "jernet"]
    for e in entries:
        for key in ("id", "name", "address", "url", "reader"):
            assert key in e, f"{e.get('id')} saknar {key}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_fetch.py -q`
Expected: `ModuleNotFoundError: No module named 'scraper.fetch'`.

- [ ] **Step 3: Implement fetch.py and restaurants.yaml**

`scraper/fetch.py`:
```python
"""Single place for network access so readers stay testable."""
from typing import Optional

import requests

USER_AGENT = ("lunch-lidingo/1.0 (+https://github.com/rstening/lunch-lidingo) "
              "Mozilla/5.0")
TIMEOUT = 20


def get(url: str, headers: Optional[dict] = None) -> bytes:
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    resp = requests.get(url, headers=merged, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content
```

`restaurants.yaml`:
```yaml
# Ordningen här är ordningen på sidan. Lägg till en rad för en ny restaurang
# och en läsare i scraper/readers/<reader>.py.
- id: firren
  name: Firren
  address: Friggavägen 18
  url: https://firren.org/bistro/
  reader: firren
- id: ronneberga
  name: Rönneberga
  address: Rönnebergavägen 1
  url: https://ronneberga.se/restaurang/lunchmeny/
  reader: ronneberga
- id: golf
  name: Lidingö Golfrestaurang
  address: Trolldalsvägen 2
  url: https://www.lidingogolfrestaurang.com/
  reader: golf
- id: pocket
  name: Pocket
  address: Lidingö stadshus, Stockholmsvägen 50
  url: https://www.nordrest.se/restaurang/pocket-lidingo/
  reader: pocket
- id: saluhallen
  name: Lidingö Saluhall
  address: Pyrolavägen 7
  url: https://www.lidingosaluhall.com/
  reader: saluhallen
- id: bibliothek
  name: Bibliothek
  address: Lejonstigen 5
  url: https://bibliothek.nu/menyer
  reader: bibliothek
- id: jernet
  name: Brasserie Jernet
  address: Stockholmsvägen 56
  url: https://brasseriejernet.se/
  reader: jernet
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_fetch.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/fetch.py restaurants.yaml tests/test_fetch.py
git commit -m "Add fetch helper and restaurant list

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Firren reader

**Files:**
- Create: `scraper/readers/firren.py`
- Test: `tests/test_reader_firren.py`

**Interfaces:**
- Consumes: `Dish`, `WeekMenu`, `ParseError`, `clean` from `scraper.model`; `day_index`, `iso_week` from `scraper.weeks`.
- Produces: `parse(html: str, today: date) -> List[WeekMenu]`, `read(get, url, today) -> List[WeekMenu]`.

Source structure (fixture `tests/fixtures/firren.html`): each day is a `div.store-item` with `h5.card-title` = day name, one or more `h6` dish names each followed by a `p.text-muted` description, and a `small.text-muted` with the date `YYYY-MM-DD`. Empty `h6` elements exist and must be skipped. One card has a wrong date (2026-09-17), so the week is the majority week of all card dates.

- [ ] **Step 1: Write failing test**

`tests/test_reader_firren.py`:
```python
from datetime import date
from pathlib import Path

from scraper.readers import firren

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_firren_fixture():
    weeks = firren.parse((FIX / "firren.html").read_text(encoding="utf-8"), TODAY)
    assert len(weeks) == 1
    w = weeks[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    assert w.days["1"][0].name == "Scampi Indiana med grönsaksris"
    assert w.days["2"][0].name.startswith("Mandelbakad torsk med vitvinssås")
    assert all(len(v) == 1 for v in w.days.values())


def test_parse_firren_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        firren.parse("<html><body>nothing</body></html>", TODAY)


def test_read_uses_get():
    html = (FIX / "firren.html").read_text(encoding="utf-8")
    weeks = firren.read(lambda url, headers=None: html.encode("utf-8"),
                        "https://firren.org/bistro/", TODAY)
    assert weeks[0].week == 39
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_firren.py -q`
Expected: `ImportError: cannot import name 'firren'`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/firren.py`:
```python
"""Firren bistro: one dish per weekday in Bootstrap cards."""
import re
from collections import Counter
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    days = {}
    dates = []
    for card in soup.select(".store-item"):
        title = card.select_one(".card-title")
        if not title:
            continue
        idx = day_index(clean(title.get_text()))
        if not idx:
            continue
        dishes = []
        for h6 in card.select("h6"):
            name = clean(h6.get_text(" "))
            if not name:
                continue
            desc_el = h6.find_next_sibling("p")
            desc = clean(desc_el.get_text(" ")) if desc_el else ""
            dishes.append(Dish(name=clean(f"{name} {desc}")))
        m = re.search(r"\d{4}-\d{2}-\d{2}", card.get_text())
        if m:
            try:
                dates.append(date.fromisoformat(m.group(0)))
            except ValueError:
                pass
        if dishes:
            days[str(idx)] = dishes
    if not days:
        raise ParseError("Firren: hittade inga rätter")
    if dates:
        (year, week), _ = Counter(iso_week(d) for d in dates).most_common(1)[0]
        known = True
    else:
        year, week = iso_week(today)
        known = False
    return [WeekMenu(year=year, week=week, week_known=known, days=days)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_firren.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/firren.py tests/test_reader_firren.py
git commit -m "Add Firren reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Rönneberga reader

**Files:**
- Create: `scraper/readers/ronneberga.py`
- Test: `tests/test_reader_ronneberga.py`

**Interfaces:** same shape as Task 3: `parse(html, today)`, `read(get, url, today)`.

Source structure (fixture `ronneberga.html`): inside a `div.rich-text`, an `h2` "lunchmeny v. 40", then repeated `h3` day headings in lowercase Swedish (`måndag`) with `p` dishes, followed by an English `h3` (`monday`) whose `p` lines are wrapped in `<em>`. Days are separated by an `h2` containing a bullet. A large HTML comment with Word styles sits between the header and the first day; `html.parser` handles it.

- [ ] **Step 1: Write failing test**

`tests/test_reader_ronneberga.py`:
```python
from datetime import date
from pathlib import Path

from scraper.readers import ronneberga

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_ronneberga_fixture():
    weeks = ronneberga.parse((FIX / "ronneberga.html").read_text(encoding="utf-8"), TODAY)
    w = weeks[0]
    assert (w.year, w.week, w.week_known) == (2026, 40, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    assert [d.name for d in w.days["1"]] == [
        "Isterband med stuvad potatis, senap & rödbetor",
        "Linsbolognese med pasta",
        "Dagens soppa",
    ]
    assert [d.name for d in w.days["4"]][-1] == "Pannkakor"
    all_names = [d.name for v in w.days.values() for d in v]
    assert not any("Soup of the day" in n for n in all_names)
    assert "11:30-13:00" in w.notes


def test_parse_ronneberga_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        ronneberga.parse("<html><body><h2>lunchmeny v. 1</h2></body></html>", TODAY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_ronneberga.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/ronneberga.py`:
```python
"""Rönneberga: Swedish and English day blocks interleaved; we keep Swedish only."""
import re
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find(["h1", "h2", "h3"], string=re.compile(r"lunchmeny", re.I))
    if not header:
        raise ParseError("Rönneberga: hittade ingen lunchmeny-rubrik")
    m = re.search(r"v\.?\s*(\d{1,2})", header.get_text())
    if m:
        week = int(m.group(1))
        year = year_for_week(week, today)
        known = True
    else:
        year, week = iso_week(today)
        known = False

    container = header.parent
    days = {}
    notes = []
    current = None
    for el in container.find_all(["h2", "h3", "p"]):
        text = clean(el.get_text(" "))
        if el.name == "h3":
            current = day_index(text)
            continue
        if el.name == "h2":
            current = None
            continue
        if not text:
            continue
        if current is None:
            if "öppettider" in text.lower():
                notes.append(text)
            continue
        if el.find("em"):
            continue  # English translation lines
        days.setdefault(str(current), []).append(Dish(name=text))
    if not days:
        raise ParseError("Rönneberga: hittade inga rätter")
    return [WeekMenu(year=year, week=week, week_known=known, days=days,
                     notes=" ".join(notes))]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_ronneberga.py -q`
Expected: `2 passed`. If the `h2` lookup fails because the heading text contains `&nbsp;`, the `re.compile` on `string=` still matches since `html.parser` unescapes entities; if it does not, replace the `find` with a loop over `soup.find_all(["h1","h2","h3"])` checking `"lunchmeny" in clean(el.get_text()).lower()`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/ronneberga.py tests/test_reader_ronneberga.py
git commit -m "Add Rönneberga reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Lidingö Golfrestaurang reader

**Files:**
- Create: `scraper/readers/golf.py`
- Test: `tests/test_reader_golf.py`

**Interfaces:** `parse(html, today)`, `read(get, url, today)`.

Source structure (fixture `golf.html`): one `div.elementor-widget-container` holds `<p>` elements: `<p><strong>Vecka 39 Lidingö Golfrestaurang</strong></p>`, a bold intro containing `kostar 165`, then per day `<p><strong>Måndag</strong></p>` followed by: a plain `<p>` (dagens rätt), `<p><strong>Buffé:</strong> …</p>`, `<p><strong>Vegetarisk:</strong> …</p>`, `<p><strong>Veckans lätta: </strong>…</p>`. Also `Lördag:`/`Söndag:` blocks (skip) and a legend at the end. Strong labels sometimes have leading spaces/nbsp.

- [ ] **Step 1: Write failing test**

`tests/test_reader_golf.py`:
```python
from datetime import date
from pathlib import Path

from scraper.readers import golf

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_golf_fixture():
    w = golf.parse((FIX / "golf.html").read_text(encoding="utf-8"), TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert len(mon) == 4
    assert mon[0].name.startswith("Pocherad flundrafilé med skaldjurssås")
    assert mon[0].tags == []
    assert mon[1].name.startswith("Gulaschgryta") and mon[1].tags == ["buffé"]
    assert mon[2].name.startswith("Friterade risbollar") and mon[2].tags == ["veg"]
    assert mon[3].name.startswith("Sallad med varmrökt lax") and mon[3].tags == ["lätt"]
    assert all(d.price == 165 for d in mon)
    assert "salladsbuffé" in w.notes


def test_parse_golf_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        golf.parse("<html><body><p><strong>Vecka 3</strong></p></body></html>", TODAY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_golf.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/golf.py`:
```python
"""Lidingö Golfrestaurang: Elementor text widget with bold day headings."""
import re
from datetime import date
from typing import Callable, List, Optional

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_golf.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/golf.py tests/test_reader_golf.py
git commit -m "Add Golfrestaurangen reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Pocket (Nordrest) reader

**Files:**
- Create: `scraper/readers/pocket.py`
- Test: `tests/test_reader_pocket.py`

**Interfaces:** `parse(html, today)`, `read(get, url, today)`.

Source structure (fixture `pocket.html`): `div.castit-weekpanel[data-week="39"]` and one for `40`. Each panel has `section.castit-day` with `h3.castit-day__title` (Swedish name inside a span with `data-sv`), and `div.castit-dish-wrap` items with optional `div.castit-dish-header` ("Veckans fisk"), `div.castit-dish__title`, `div.castit-dish__desc`, `div.castit-dish__allergens`. Price appears in `.castit-lunch-meta` as `Dagens rätt : 135 SEK`. Intro text sits in `.castit-menu-text--intro`.

- [ ] **Step 1: Write failing test**

`tests/test_reader_pocket.py`:
```python
from datetime import date
from pathlib import Path

from scraper.readers import pocket

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_pocket_fixture_two_weeks():
    weeks = pocket.parse((FIX / "pocket.html").read_text(encoding="utf-8"), TODAY)
    assert [(w.year, w.week, w.week_known) for w in weeks] == [(2026, 39, True), (2026, 40, True)]
    w39 = weeks[0]
    assert sorted(w39.days) == ["1", "2", "3", "4", "5"]
    mon = w39.days["1"]
    assert len(mon) == 3
    assert mon[0].name == "Vegetarisk lasagne, sojafärs, grönsaker, parmesankräk, ruccola (Gluten, Laktos, Ägg)"
    assert mon[0].tags == ["veg"]
    assert mon[0].price == 135
    assert mon[2].name.startswith("Thaifisk curry") and mon[2].tags == ["fisk"]
    tue = w39.days["2"]
    treat = [d for d in tue if d.name.lower().startswith("idag bjuder")]
    assert treat and treat[0].price is None
    assert "salladsbuffé" in w39.notes


def test_parse_pocket_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        pocket.parse("<html><body></body></html>", TODAY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_pocket.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/pocket.py`:
```python
"""Pocket (Nordrest): Castit weekly menu widget, possibly several weeks."""
import re
from datetime import date
from typing import Callable, List, Optional

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, year_for_week


def _price(soup: BeautifulSoup) -> Optional[int]:
    meta = soup.select_one(".castit-lunch-meta")
    if not meta:
        return None
    m = re.search(r"Dagens rätt\s*:\s*(\d+)", clean(meta.get_text(" ")))
    return int(m.group(1)) if m else None


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    price = _price(soup)
    intro = soup.select_one(".castit-menu-text--intro")
    notes = clean(intro.get_text(" ")) if intro else ""
    weeks = []
    for panel in soup.select(".castit-weekpanel[data-week]"):
        try:
            week = int(panel["data-week"])
        except (KeyError, ValueError):
            continue
        days = {}
        for section in panel.select(".castit-day"):
            title = section.select_one(".castit-day__title")
            idx = day_index(clean(title.get_text())) if title else None
            if not idx:
                continue
            dishes = []
            for wrap in section.select(".castit-dish-wrap"):
                t = wrap.select_one(".castit-dish__title")
                if not t:
                    continue
                name = clean(t.get_text(" "))
                if not name:
                    continue
                d = wrap.select_one(".castit-dish__desc")
                a = wrap.select_one(".castit-dish__allergens")
                header = wrap.select_one(".castit-dish-header")
                if d and clean(d.get_text(" ")):
                    name = f"{name}, {clean(d.get_text(' '))}"
                if a and a.get("title"):
                    name = f"{name} ({clean(a['title'])})"
                tags = []
                if header and "fisk" in header.get_text().lower():
                    tags = ["fisk"]
                elif name.lower().startswith(("vegetarisk", "vegansk", "falafel")):
                    tags = ["veg"]
                dish_price = None if name.lower().startswith("idag bjuder") else price
                dishes.append(Dish(name=name, price=dish_price, tags=tags))
            if dishes:
                days[str(idx)] = dishes
        if days:
            weeks.append(WeekMenu(year=year_for_week(week, today), week=week,
                                  week_known=True, days=days, notes=notes))
    if not weeks:
        raise ParseError("Pocket: hittade inga veckor med rätter")
    weeks.sort(key=lambda w: (w.year, w.week))
    return weeks


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_pocket.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/pocket.py tests/test_reader_pocket.py
git commit -m "Add Pocket reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Lidingö Saluhall reader

**Files:**
- Create: `scraper/readers/saluhallen.py`
- Test: `tests/test_reader_saluhallen.py`

**Interfaces:** `parse(html, today)`, `read(get, url, today)`.

Source structure (fixture `saluhallen.html`): Squarespace section `#lunchmeny-section` with an `h1` "Lunchmeny vecka 40", an `<em>` intro paragraph, then `<p><strong>MÅNDAG</strong></p>` followed by plain `<p>` dishes, blank bold `<p>`s between days, then `<p><strong>VECKANS VEGETARISKA</strong></p>` with one dish, then `SALLADER` etc. which we ignore.

- [ ] **Step 1: Write failing test**

`tests/test_reader_saluhallen.py`:
```python
from datetime import date
from pathlib import Path

from scraper.readers import saluhallen

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)


def test_parse_saluhallen_fixture():
    w = saluhallen.parse((FIX / "saluhallen.html").read_text(encoding="utf-8"), TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 40, True)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert len(mon) == 3
    assert mon[0].name.startswith("Fläsknoisette med senapssås")
    assert mon[2].name.startswith("Broccoli-& ädelostpaj") and mon[2].tags == ["veg"]
    assert len(w.days["4"]) == 4
    names = [d.name for v in w.days.values() for d in v]
    assert not any("Räksallad" in n for n in names)
    assert "salladsbuffé" in w.notes


def test_parse_saluhallen_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        saluhallen.parse('<html><body><section id="lunchmeny-section"></section></body></html>', TODAY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_saluhallen.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/saluhallen.py`:
```python
"""Lidingö Saluhall: lunch section on the Squarespace front page."""
import re
from datetime import date
from typing import Callable, List

from bs4 import BeautifulSoup

from scraper.model import Dish, ParseError, WeekMenu, clean
from scraper.weeks import day_index, iso_week, year_for_week


def parse(html: str, today: date) -> List[WeekMenu]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#lunchmeny-section")
    if section is None:
        raise ParseError("Saluhallen: hittade ingen lunchsektion")
    year, week = iso_week(today)
    known = False
    for h in section.find_all(["h1", "h2", "h3"]):
        m = re.search(r"vecka\s+(\d{1,2})", clean(h.get_text()), re.I)
        if m:
            week = int(m.group(1))
            year = year_for_week(week, today)
            known = True
            break

    days = {}
    veg = []
    notes = ""
    mode = None  # ("day", idx) | ("veg", None) | None
    for p in section.find_all("p"):
        text = clean(p.get_text(" "))
        if not text:
            continue
        if p.find("em") and not notes and "ingår" in text.lower():
            notes = text
            continue
        strong = p.find("strong")
        if strong and clean(strong.get_text()) == text:
            idx = day_index(text)
            if idx:
                mode = ("day", idx)
            elif text.upper().startswith("VECKANS VEGETARISKA"):
                mode = ("veg", None)
            else:
                mode = None
            continue
        if mode is None:
            continue
        if mode[0] == "day":
            days.setdefault(str(mode[1]), []).append(Dish(name=text))
        else:
            veg.append(Dish(name=text, tags=["veg"]))
    if not days:
        raise ParseError("Saluhallen: hittade inga rätter")
    for key in days:
        days[key].extend(Dish(name=v.name, price=v.price, tags=list(v.tags)) for v in veg)
    return [WeekMenu(year=year, week=week, week_known=known, days=days, notes=notes)]


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    return parse(get(url).decode("utf-8", errors="replace"), today)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_saluhallen.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/saluhallen.py tests/test_reader_saluhallen.py
git commit -m "Add Saluhallen reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Bibliothek reader (PDF)

**Files:**
- Create: `scraper/readers/bibliothek.py`
- Test: `tests/test_reader_bibliothek.py`

**Interfaces:**
- Produces: `find_pdf_links(html: str, base_url: str) -> List[Tuple[int, int, str]]` (year, week, absolute url), `parse_pdf(pdf: bytes) -> Tuple[List[Dish], str]` (dishes, notes), `friday_special(pdf_words_text: str)` folded into `parse_pdf`, `read(get, url, today)`.

Source structure: `bibliothek.html` links to `https://static.thatsup.website/.../Lunch-v40-2026.pdf?v=...` (three weeks). The PDF is one A4 page. Words above `AFFÄRSLUNCH` and below the `INK SALLAD…` line form four blocks in two columns: left-top kött, right-top fisk, left-bottom veg, right-bottom soppa. Category labels are rotated 90°, so pdfplumber returns them reversed (`ttök`, `ksif`, `gev`, `appos`); they sit at the left edge of their block, within about 30pt vertically. Prices look like `185kr`. A line `FREDAGAR: STEAK MINUTE pommes frites och bearnaisesås 245kr` below the blocks is a Friday extra.

- [ ] **Step 1: Write failing test**

`tests/test_reader_bibliothek.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_bibliothek.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/bibliothek.py`:
```python
"""Bibliothek: one PDF per week, same four dishes every weekday."""
import html as htmlmod
import io
import re
from datetime import date
from typing import Callable, List, Optional, Tuple
from urllib.parse import urljoin

import pdfplumber

from scraper.model import Dish, ParseError, WeekMenu

LABELS = {"kött", "fisk", "veg", "soppa"}
PDF_RE = re.compile(r'href="([^"]*Lunch-v(\d{1,2})-(\d{4})\.pdf[^"]*)"', re.I)


def find_pdf_links(html: str, base_url: str) -> List[Tuple[int, int, str]]:
    found = {}
    for m in PDF_RE.finditer(html):
        url = urljoin(base_url, htmlmod.unescape(m.group(1)))
        week, year = int(m.group(2)), int(m.group(3))
        found[(year, week)] = url
    return [(y, w, found[(y, w)]) for (y, w) in sorted(found)]


def _label_of(word) -> Optional[str]:
    t = word["text"].lower()
    if t in LABELS:
        return t
    if t[::-1] in LABELS:
        return t[::-1]
    return None


def parse_pdf(pdf: bytes) -> Tuple[List[Dish], str]:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        page = doc.pages[0]
        width, height = page.width, page.height
        words = page.extract_words()
    if not words:
        raise ParseError("Bibliothek: PDF utan text")

    stop = min([w["top"] for w in words if w["text"].upper().startswith("AFFÄRSLUNCH")]
               + [height])
    ink = [w for w in words if w["text"].upper() == "INK"]
    start = (ink[0]["top"] + 5) if ink else 0
    notes = ""
    if ink:
        line = [w["text"] for w in words if abs(w["top"] - ink[0]["top"]) < 3]
        notes = " ".join(line).capitalize()

    body = [w for w in words if start < w["top"] < stop]
    labels = [(_label_of(w), w) for w in body if _label_of(w)]
    body = [w for w in body if not _label_of(w)]

    blocks = []
    for col in (0, 1):
        col_words = sorted((w for w in body if (w["x0"] >= width / 2) == bool(col)),
                           key=lambda w: (round(w["top"]), w["x0"]))
        lines = []
        for w in col_words:
            if lines and abs(lines[-1][0] - w["top"]) < 4:
                lines[-1][1].append(w)
            else:
                lines.append([w["top"], [w]])
        current = None
        for top, ws in lines:
            if current and top - current["bottom"] > 20:
                blocks.append(current)
                current = None
            if current is None:
                current = {"col": col, "top": top, "bottom": top, "lines": []}
            current["lines"].append(" ".join(x["text"] for x in ws))
            current["bottom"] = top
        if current:
            blocks.append(current)

    dishes = []
    for b in blocks:
        text = " ".join(b["lines"])
        pm = re.search(r"(\d+)\s*kr", text)
        price = int(pm.group(1)) if pm else None
        name = re.sub(r"\s*\d+\s*kr\b", "", text).strip()
        tag = next((lab for lab, w in labels
                    if (w["x0"] >= width / 2) == bool(b["col"])
                    and b["top"] - 30 <= w["top"] <= b["bottom"] + 30), None)
        if name:
            dishes.append(Dish(name=name, price=price, tags=[tag] if tag else []))
    if not dishes:
        raise ParseError("Bibliothek: hittade inga rätter i PDF")
    return dishes, notes


def _friday_special(pdf: bytes) -> Optional[Dish]:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = doc.pages[0].extract_text() or ""
    m = re.search(r"FREDAGAR:\s*(.+?)\s*(\d+)\s*kr", text, re.I | re.S)
    if not m:
        return None
    name = re.sub(r"\s+", " ", m.group(1)).strip()
    name = name[:1].upper() + name[1:].lower()
    return Dish(name=name, price=int(m.group(2)))


def read(get: Callable, url: str, today: date) -> List[WeekMenu]:
    links = find_pdf_links(get(url).decode("utf-8", errors="replace"), url)
    if not links:
        raise ParseError("Bibliothek: hittade inga lunch-PDF:er")
    weeks = []
    for year, week, pdf_url in links:
        pdf = get(pdf_url)
        dishes, notes = parse_pdf(pdf)
        days = {str(d): [Dish(x.name, x.price, list(x.tags)) for x in dishes] for d in range(1, 6)}
        special = _friday_special(pdf)
        if special:
            days["5"].append(special)
        weeks.append(WeekMenu(year=year, week=week, week_known=True, days=days, notes=notes))
    return weeks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_bibliothek.py -q`
Expected: `4 passed`. If `test_parse_pdf_four_blocks` fails on the soppa tag, widen the `30` tolerance to `40` (the rotated label sits about 20pt above its block).

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/bibliothek.py tests/test_reader_bibliothek.py
git commit -m "Add Bibliothek PDF reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Brasserie Jernet reader (Supabase API)

**Files:**
- Create: `scraper/readers/jernet.py`
- Test: `tests/test_reader_jernet.py`

**Interfaces:**
- Produces: `find_bundle_url(html: str, base_url: str) -> str`, `find_supabase(js: str) -> Tuple[str, str]` (project url, anon key), `parse_rows(rows: list, today: date) -> List[WeekMenu]`, `read(get, url, today)`.

Source: `jernet.html` has `<script type="module" crossorigin src="/assets/index-xZPF3w39.js">`. The bundle contains `https://<id>.supabase.co` and a JWT anon key (`eyJ…`). Rows in `jernet-lunch_menu.json` have `day_of_week` 1–5 and `meat_name/meat_price`, `fish_name/fish_price`, `vegetarian_name/vegetarian_price`.

- [ ] **Step 1: Write failing test**

`tests/test_reader_jernet.py`:
```python
import json
from datetime import date
from pathlib import Path

from scraper.readers import jernet

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 9, 25)
JS = ('var a="https://abcdefghij.supabase.co",b="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
      'eyJpc3MiOiJzdXBhYmFzZSJ9.abc_DEF-123";')


def test_find_bundle_url():
    html = (FIX / "jernet.html").read_text(encoding="utf-8")
    assert jernet.find_bundle_url(html, "https://brasseriejernet.se/") == \
        "https://brasseriejernet.se/assets/index-xZPF3w39.js"


def test_find_supabase():
    url, key = jernet.find_supabase(JS)
    assert url == "https://abcdefghij.supabase.co"
    assert key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.")


def test_parse_rows():
    rows = json.loads((FIX / "jernet-lunch_menu.json").read_text(encoding="utf-8"))
    w = jernet.parse_rows(rows, TODAY)[0]
    assert (w.year, w.week, w.week_known) == (2026, 39, False)
    assert sorted(w.days) == ["1", "2", "3", "4", "5"]
    mon = w.days["1"]
    assert [d.tags for d in mon] == [["kött"], ["fisk"], ["veg"]]
    assert mon[0].name == "Kalvfärsbiffar serveras med ugnsrostad potatis och gräddsås"
    assert mon[0].price == 139
    assert mon[1].price == 149


def test_read_end_to_end_with_fake_get():
    html = (FIX / "jernet.html").read_bytes()
    rows = (FIX / "jernet-lunch_menu.json").read_bytes()
    seen = {}

    def fake_get(url, headers=None):
        if url.endswith(".js"):
            return JS.encode()
        if "lunch_menu" in url:
            seen["headers"] = headers
            return rows
        return html

    weeks = jernet.read(fake_get, "https://brasseriejernet.se/", TODAY)
    assert weeks[0].days["5"][0].name.startswith("Schnitzel")
    assert seen["headers"]["apikey"].startswith("eyJ")


def test_parse_rows_empty_raises():
    import pytest
    from scraper.model import ParseError
    with pytest.raises(ParseError):
        jernet.parse_rows([], TODAY)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_reader_jernet.py -q`
Expected: `ImportError`.

- [ ] **Step 3: Implement the reader**

`scraper/readers/jernet.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_reader_jernet.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add scraper/readers/jernet.py tests/test_reader_jernet.py
git commit -m "Add Jernet API reader

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: Merge logic and the scraper CLI

**Files:**
- Create: `scraper/merge.py`, `scraper/__main__.py`
- Test: `tests/test_merge.py`

**Interfaces:**
- Produces: `merge(previous: dict, restaurants: List[dict], results: Dict[str, Union[List[WeekMenu], Exception]], now: datetime) -> dict` matching the JSON shape in the spec; `load_restaurants(path="restaurants.yaml") -> List[dict]`; `run_all(restaurants, today, get) -> Dict[str, Union[List[WeekMenu], Exception]]`; `main(argv=None) -> int`.
- Consumes: readers via `importlib.import_module(f"scraper.readers.{entry['reader']}").read(get, url, today)`.

- [ ] **Step 1: Write failing test**

`tests/test_merge.py`:
```python
from datetime import datetime, timezone

from scraper.merge import merge
from scraper.model import Dish, WeekMenu

NOW = datetime(2026, 9, 25, 7, 2, 11, tzinfo=timezone.utc)
RESTAURANTS = [
    {"id": "a", "name": "A", "address": "Gatan 1", "url": "https://a", "reader": "a"},
    {"id": "b", "name": "B", "address": "Gatan 2", "url": "https://b", "reader": "b"},
]
MENU = [WeekMenu(2026, 39, True, {"1": [Dish("Soppa", 120, ["soppa"])]}, "obs")]


def test_merge_success_serialises_weeks():
    out = merge({}, RESTAURANTS, {"a": MENU, "b": MENU}, NOW)
    assert out["generated_at"] == "2026-09-25T07:02:11Z"
    a = out["restaurants"][0]
    assert a["id"] == "a" and a["name"] == "A" and a["address"] == "Gatan 1"
    assert a["last_success"] == "2026-09-25T07:02:11Z"
    assert a["error"] is None
    assert a["weeks"][0]["days"]["1"][0] == {"name": "Soppa", "price": 120, "tags": ["soppa"]}
    assert a["weeks"][0]["notes"] == "obs"


def test_merge_failure_keeps_previous_menu():
    previous = merge({}, RESTAURANTS, {"a": MENU, "b": MENU},
                     datetime(2026, 9, 24, 7, 0, tzinfo=timezone.utc))
    out = merge(previous, RESTAURANTS, {"a": MENU, "b": RuntimeError("timeout")}, NOW)
    b = out["restaurants"][1]
    assert b["error"] == "RuntimeError: timeout"
    assert b["last_success"] == "2026-09-24T07:00:00Z"
    assert b["weeks"] == previous["restaurants"][1]["weeks"]


def test_merge_failure_without_previous_gives_empty_weeks():
    out = merge({}, RESTAURANTS, {"a": MENU, "b": RuntimeError("x")}, NOW)
    b = out["restaurants"][1]
    assert b["weeks"] == [] and b["last_success"] is None


def test_merge_missing_result_keeps_previous_entry_unchanged():
    previous = merge({}, RESTAURANTS, {"a": MENU, "b": MENU},
                     datetime(2026, 9, 24, 7, 0, tzinfo=timezone.utc))
    out = merge(previous, RESTAURANTS, {"a": MENU}, NOW)
    assert out["restaurants"][1] == previous["restaurants"][1]


def test_merge_missing_result_without_previous_is_error():
    out = merge({}, RESTAURANTS, {"a": MENU}, NOW)
    b = out["restaurants"][1]
    assert b["error"] == "Inget resultat" and b["weeks"] == []


def test_merge_keeps_yaml_order():
    out = merge({}, RESTAURANTS, {"b": MENU, "a": MENU}, NOW)
    assert [r["id"] for r in out["restaurants"]] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_merge.py -q`
Expected: `ModuleNotFoundError: No module named 'scraper.merge'`.

- [ ] **Step 3: Implement merge.py**

`scraper/merge.py`:
```python
"""Combine this run's reader results with the previous data file."""
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Union

from scraper.model import WeekMenu

Result = Union[List[WeekMenu], BaseException]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def merge(previous: dict, restaurants: List[dict],
          results: Dict[str, Result], now: datetime) -> dict:
    prev_by_id = {r.get("id"): r for r in previous.get("restaurants", [])}
    out = []
    for entry in restaurants:
        rid = entry["id"]
        base = {"id": rid, "name": entry["name"], "url": entry["url"],
                "address": entry.get("address", "")}
        old = prev_by_id.get(rid)
        if rid not in results and old is not None:
            out.append({**old, **base})  # not run this time (--only): keep as is
            continue
        result = results.get(rid)
        if isinstance(result, list) and result:
            out.append({**base, "last_success": _iso(now), "error": None,
                        "weeks": [asdict(w) for w in result]})
            continue
        if result is None:
            error = "Inget resultat"
        elif isinstance(result, BaseException):
            error = f"{type(result).__name__}: {result}"
        else:
            error = "Tom meny"
        old = old or {}
        out.append({**base, "last_success": old.get("last_success"), "error": error,
                    "weeks": old.get("weeks", [])})
    return {"generated_at": _iso(now), "restaurants": out}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_merge.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Implement the CLI**

`scraper/__main__.py`:
```python
"""Run every reader, merge with data/menus.json, write it back.

Usage: python -m scraper [--only firren,jernet] [--date 2026-09-25]
Exit code 1 if every reader failed (so the daily job does not publish).
"""
import argparse
import importlib
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List
from zoneinfo import ZoneInfo

import yaml

from scraper import fetch
from scraper.merge import Result, merge
from scraper.model import ParseError

DATA_PATH = Path("data/menus.json")
TZ = ZoneInfo("Europe/Stockholm")
log = logging.getLogger("scraper")


def load_restaurants(path: str = "restaurants.yaml") -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_all(restaurants: List[dict], today: date,
            get: Callable = fetch.get) -> Dict[str, Result]:
    results: Dict[str, Result] = {}
    for entry in restaurants:
        rid = entry["id"]
        try:
            module = importlib.import_module(f"scraper.readers.{entry['reader']}")
            weeks = module.read(get, entry["url"], today)
            if not weeks or not any(w.days for w in weeks):
                raise ParseError("Tom meny")
            results[rid] = weeks
            log.info("%s: ok, veckor %s", rid, [w.week for w in weeks])
        except Exception as exc:  # noqa: BLE001 - one bad source must not stop the rest
            log.warning("%s: misslyckades: %s: %s", rid, type(exc).__name__, exc)
            results[rid] = exc
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="kommaseparerade restaurang-id")
    parser.add_argument("--date", help="YYYY-MM-DD, standard är idag")
    parser.add_argument("--restaurants", default="restaurants.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    now = datetime.now(TZ)
    today = date.fromisoformat(args.date) if args.date else now.date()
    restaurants = load_restaurants(args.restaurants)
    if args.only:
        wanted = set(args.only.split(","))
        restaurants = [r for r in restaurants if r["id"] in wanted]

    results = run_all(restaurants, today)
    if not any(isinstance(v, list) for v in results.values()):
        log.error("Alla läsare misslyckades, skriver ingen fil")
        return 1

    previous = {}
    if DATA_PATH.exists():
        previous = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    # merge() keeps restaurants missing from `results` (the --only case) unchanged.
    data = merge(previous, load_restaurants(args.restaurants), results,
                 now.astimezone(ZoneInfo("UTC")))
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.info("Skrev %s", DATA_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`zoneinfo` needs tz data. On macOS it is available. On GitHub's Ubuntu runner it is available. If `ZoneInfo("Europe/Stockholm")` raises locally, add `tzdata>=2024.1` to `requirements.txt` and reinstall.

- [ ] **Step 6: Smoke-test against the real sites**

Run: `.venv/bin/python -m scraper`
Expected: seven `INFO <id>: ok, veckor [...]` lines (or a WARNING for a site that is down), then `INFO Skrev data/menus.json`, exit code 0. Inspect: `head -40 data/menus.json` shows `"generated_at"` and the first restaurant with dishes.

- [ ] **Step 7: Commit**

```bash
git add scraper/merge.py scraper/__main__.py tests/test_merge.py data/menus.json
git commit -m "Add merge logic and scraper CLI

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: HTML builder

**Files:**
- Create: `scraper/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `data/menus.json` shape from Task 10; `display_date`, `iso_week`, `week_dates`, `DAY_SHORT`, `DAY_NAMES`, `format_date` from `scraper.weeks`.
- Produces: `pick_week(restaurant: dict, year: int, week: int) -> Tuple[Optional[dict], Optional[str]]` (chosen week dict and a Swedish notice or None), `render(data: dict, today: date) -> str`, `main(argv=None) -> int` writing `docs/index.html`.

Page mechanics (no JavaScript): five `<input type="radio" name="dag" id="dag-N">` at the top of `<main>`, the one for the display day has `checked`; a `<nav class="flikar">` with `<label for="dag-N">`; five `<section class="dag" id="d-N">`. CSS: `.dag{display:none}` and `#dag-1:checked ~ #d-1{display:block}` for each N; `#dag-1:checked ~ .flikar label[for="dag-1"]` gets the active style. Inputs, nav and sections must be direct siblings inside `<main>`.

Per restaurant card: `<h2><a href=url>name</a></h2>`, `<p class="adress">address</p>`, `<ul>` of dishes with `<span class="tagg">veg</span>` and `<span class="pris">165 kr</span>` where present, `<p class="notis">` for week/stale notices, `<p class="info">` for notes. No dishes for that day: `<p class="tom">Ingen lunch angiven.</p>`. Error older than 7 days or no weeks at all: `<p class="tom">Kunde inte hämta menyn, se restaurangens sida.</p>`.

- [ ] **Step 1: Write failing test**

`tests/test_build.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_build.py -q`
Expected: `ModuleNotFoundError: No module named 'scraper.build'`.

- [ ] **Step 3: Implement build.py**

`scraper/build.py`:
```python
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
body { margin: 0; padding: 16px; font: 19px/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #1a1a1a; background: #f6f4ef; }
main { max-width: 1100px; margin: 0 auto; }
header h1 { font-size: 1.9rem; margin: 0 0 4px; }
header p { margin: 0 0 12px; color: #444; }
.dagval { position: absolute; opacity: 0; pointer-events: none; }
.flikar { display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 20px; }
.flikar label { display: block; padding: 10px 14px; border: 2px solid #1a1a1a; border-radius: 8px;
                background: #fff; cursor: pointer; font-weight: 600; }
.flikar label small { display: block; font-weight: 400; font-size: 0.8rem; color: #444; }
.dag { display: none; }
.dag h2.dagrubrik { font-size: 1.5rem; margin: 0 0 14px; }
.lista { display: grid; grid-template-columns: 1fr; gap: 14px; }
@media (min-width: 800px) { .lista { grid-template-columns: 1fr 1fr; } }
.restaurang { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 14px 16px; }
.restaurang h2 { font-size: 1.3rem; margin: 0 0 2px; }
.restaurang h2 a { color: #0b4f9c; text-decoration: none; }
.restaurang h2 a:hover { text-decoration: underline; }
.adress { margin: 0 0 8px; color: #555; font-size: 0.95rem; }
.restaurang ul { list-style: none; margin: 0; padding: 0; }
.restaurang li { padding: 6px 0; border-top: 1px solid #eee; }
.tagg { display: inline-block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .03em;
        background: #e9efe4; color: #2f4f2f; border-radius: 4px; padding: 1px 6px; margin-right: 6px; }
.pris { float: right; color: #444; white-space: nowrap; margin-left: 8px; }
.notis { margin: 8px 0 0; color: #8a4b00; font-size: 0.95rem; }
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
    return "\n".join(rules)


def pick_week(restaurant: dict, year: int, week: int) -> Tuple[Optional[dict], Optional[str]]:
    weeks = restaurant.get("weeks") or []
    if not weeks:
        return None, None
    for w in weeks:
        if (w.get("year"), w.get("week")) == (year, week):
            return w, None
    latest = max(weeks, key=lambda w: (w.get("year", 0), w.get("week", 0)))
    if (latest["year"], latest["week"]) < (year, week):
        return latest, f"Visar vecka {latest['week']}, ej uppdaterad än"
    return latest, f"Visar vecka {latest['week']}"


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
    parts = ["<li>"]
    for t in d.get("tags") or []:
        parts.append(f'<span class="tagg">{escape(t)}</span>')
    parts.append(escape(d.get("name", "")))
    if d.get("price") is not None:
        parts.append(f'<span class="pris">{int(d["price"])} kr</span>')
    parts.append("</li>")
    return "".join(parts)


def _card_html(r: dict, week: Optional[dict], notice: Optional[str],
               day: int, now: datetime) -> str:
    out = ['<article class="restaurang">']
    out.append(f'<h2><a href="{escape(r["url"], quote=True)}">{escape(r["name"])}</a></h2>')
    if r.get("address"):
        out.append(f'<p class="adress">{escape(r["address"])}</p>')
    if week is None or _is_stale(r, now):
        out.append('<p class="tom">Kunde inte hämta menyn, se restaurangens sida.</p>')
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
        for r in restaurants:
            w, notice = pick_week(r, year, week)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_build.py -q`
Expected: `6 passed`. The `test_render_friday` "Kunde inte hämta menyn" assertion relies on Beta's `last_success` (Sep 10) being more than 7 days before `generated_at` (Sep 25).

- [ ] **Step 5: Build the real page and look at it**

Run: `.venv/bin/python -m scraper.build && open docs/index.html` (or open it in the in-app browser via a `file://` URL). Check: today's tab is highlighted, seven cards, dishes readable, tabs switch without JavaScript, layout is one column when the window is narrow.

- [ ] **Step 6: Commit**

```bash
git add scraper/build.py tests/test_build.py docs/index.html
git commit -m "Add static page builder

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: GitHub Actions workflows and README

**Files:**
- Create: `.github/workflows/test.yml`, `.github/workflows/daily.yml`, `README.md`, `docs/.nojekyll`

**Interfaces:**
- Consumes: `python -m scraper` (exit 1 when all readers fail), `python -m scraper.build`.

- [ ] **Step 1: Write the test workflow**

`.github/workflows/test.yml`:
```yaml
name: Tester
on:
  push:
  pull_request:
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
```

- [ ] **Step 2: Write the daily workflow**

`.github/workflows/daily.yml`:
```yaml
name: Hämta menyer
on:
  schedule:
    - cron: "0 7 * * *"   # 09:00 svensk sommartid
    - cron: "0 8 * * *"   # 09:00 svensk vintertid
  workflow_dispatch:
permissions:
  contents: write
concurrency:
  group: daily
  cancel-in-progress: false
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - name: Hämta menyer
        run: python -m scraper
      - name: Bygg sidan
        run: python -m scraper.build
      - name: Committa om något ändrats
        run: |
          git config user.name "lunch-bot"
          git config user.email "lunch-bot@users.noreply.github.com"
          git add data/menus.json docs/index.html
          if git diff --cached --quiet; then
            echo "Inga ändringar"
          else
            git commit -m "Uppdatera menyer $(TZ=Europe/Stockholm date '+%Y-%m-%d %H:%M')"
            git push
          fi
```

- [ ] **Step 3: Write README and .nojekyll**

Create empty `docs/.nojekyll` (so GitHub Pages serves files as-is).

`README.md`:
```markdown
# Lunch Lidingö

En sida som samlar dagens lunch från restauranger på Lidingö. Menyerna hämtas
automatiskt varje morgon kl 09 av GitHub Actions och publiceras som en statisk
sida via GitHub Pages från mappen `docs/`.

## Så funkar det

1. `python -m scraper` läser `restaurants.yaml`, hämtar varje restaurangs meny
   och skriver `data/menus.json`. En restaurang som inte går att läsa behåller
   sin senaste meny.
2. `python -m scraper.build` gör om JSON-filen till `docs/index.html`.
3. Actions committar och pushar filerna om de ändrats.

## Köra lokalt

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m scraper
.venv/bin/python -m scraper.build
open docs/index.html
```

## Lägga till en restaurang

Lägg till en rad i `restaurants.yaml` och en läsare i `scraper/readers/`
med funktionen `read(get, url, today)`. Spara en kopia av källan i
`tests/fixtures/` och skriv ett test.

## Engångsinställningar i GitHub

1. Settings → Pages → Build and deployment → Source: "Deploy from a branch",
   Branch: `main`, mapp `/docs`.
2. Settings → Actions → General → Workflow permissions: "Read and write permissions".
3. Actions → "Hämta menyer" → "Run workflow" för att köra första gången.
```

- [ ] **Step 4: Run the whole test suite once more**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass (around 40).

- [ ] **Step 5: Commit**

```bash
git add .github README.md docs/.nojekyll
git commit -m "Add GitHub Actions workflows and README

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: Hand-off to GitHub (requires Richard)

**Files:** none new.

This task is done together with Richard, not by a subagent. Steps:

- [ ] **Step 1: Log in with the private account**

Richard runs, in a terminal:
```bash
gh auth login --hostname github.com --web
```
and chooses the `rstening` account in the browser. Then switch: `gh auth switch --user rstening`. Verify with `gh auth status` that the active account is `rstening`.

- [ ] **Step 2: Add the remote and push**

```bash
git remote add origin https://github.com/rstening/lunch-lidingo.git
git branch -M main
git push -u origin main
```

If the repo already has commits (e.g. a README created on GitHub), run `git pull --rebase origin main` first and resolve the README conflict by keeping ours.

- [ ] **Step 3: Enable Pages and Actions permissions**

Richard does the three items under "Engångsinställningar i GitHub" in `README.md`, then runs the "Hämta menyer" workflow manually and opens `https://rstening.github.io/lunch-lidingo/`.

- [ ] **Step 4: Verify**

Check that the Actions run is green, that a "Uppdatera menyer …" commit appeared, and that the page shows today's tab with seven cards.

---

## Self-review notes

- Spec coverage: readers (Tasks 3–9), merge and failure handling (10), page with tabs, notices, stale handling (11), schedule with DST and commit-if-changed (12), tests per reader and for merge/build (3–11), manual steps (13). Per-restaurant email notifications are explicitly out of scope in the spec.
- Types: `read(get, url, today)` is used identically in every reader and in `run_all`. `merge` consumes `List[WeekMenu]` or exceptions and produces the JSON shape that `build.pick_week`/`render` consume. `Dish`/`WeekMenu` field names match `asdict` output used in build tests.
- Known judgement calls: Pocket "Idag bjuder vi på…" rows are kept with no price; Saluhallen salads are dropped; Golf weekend buffés are dropped; Jernet is always tagged as current week (`week_known=False`).
