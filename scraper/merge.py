"""Combine this run's reader results with the previous data file."""
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, List, Union

from scraper.model import WeekMenu

Result = Union[List[WeekMenu], BaseException]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _combine_weeks(old_weeks: List[dict], new_weeks: List[WeekMenu], now: datetime) -> List[dict]:
    """Merge previous weeks with newly read ones, keyed by (year, week).

    New data overrides old data for the same week. Weeks older than
    (this week - 1) are dropped so a stale week never lingers forever, but a
    reader that has already moved on to next week does not erase this week's
    menu (the bug this exists to fix).
    """
    cutoff = (now.date() - timedelta(weeks=1)).isocalendar()[:2]
    by_key = {(w.get("year"), w.get("week")): w for w in old_weeks}
    for w in new_weeks:
        by_key[(w.year, w.week)] = asdict(w)
    kept = [w for key, w in by_key.items() if key >= cutoff]
    kept.sort(key=lambda w: (w["year"], w["week"]))
    return kept


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
            weeks = _combine_weeks((old or {}).get("weeks", []), result, now)
            out.append({**base, "last_success": _iso(now), "error": None,
                        "weeks": weeks})
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
