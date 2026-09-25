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
