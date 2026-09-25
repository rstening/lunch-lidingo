"""Run every reader, merge with data/menus.json, write it back.

Usage: python -m scraper [--only firren,jernet] [--date 2026-09-25]
Exit code 1 if every reader failed (so the daily job does not publish).
"""
import argparse
import importlib
import json
import logging
import sys
from datetime import date, datetime, time
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

    if args.date:
        today = date.fromisoformat(args.date)
        now = datetime.combine(today, time(9, 0), tzinfo=TZ)
    else:
        now = datetime.now(TZ)
        today = now.date()
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
