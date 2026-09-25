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
