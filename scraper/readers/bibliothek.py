"""Bibliothek: one PDF per week, same four dishes every weekday."""
import html as htmlmod
import io
import logging
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
    tagged = sum(1 for d in dishes if d.tags)
    if tagged < 3:
        raise ParseError("Bibliothek: PDF-layouten känns inte igen")
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
    last_error = None
    for year, week, pdf_url in links:
        try:
            pdf = get(pdf_url)
            dishes, notes = parse_pdf(pdf)
            days = {str(d): [Dish(x.name, x.price, list(x.tags)) for x in dishes]
                    for d in range(1, 6)}
            special = _friday_special(pdf)
            if special:
                days["5"].append(special)
            weeks.append(WeekMenu(year=year, week=week, week_known=True, days=days, notes=notes))
        except Exception as exc:
            # One bad week's PDF (fetch failure or a layout that can't be
            # read) must not take down the other weeks.
            logging.getLogger("scraper").warning(
                "Bibliothek: hoppar över %s: %s: %s", pdf_url, type(exc).__name__, exc)
            last_error = f"{type(exc).__name__}: {exc}"
            continue
    if not weeks:
        if last_error:
            raise ParseError(f"Bibliothek: ingen vecka kunde läsas: {last_error}")
        raise ParseError("Bibliothek: ingen vecka kunde läsas")
    return weeks
