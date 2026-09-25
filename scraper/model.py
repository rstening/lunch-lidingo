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
