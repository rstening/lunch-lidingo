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
    price_to: Optional[int] = None  # set when the price is a range, e.g. 145-160 kr


@dataclass
class WeekMenu:
    year: int
    week: int
    week_known: bool
    days: Dict[str, List[Dish]]
    notes: str = ""
    # Short extra facts in our own words, shown after what the lunch includes,
    # e.g. "Pensionärspris 120 kr." Each is a full sentence ending with a period.
    extras: List[str] = field(default_factory=list)
