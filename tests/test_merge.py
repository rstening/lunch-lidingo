from datetime import datetime, timezone

from scraper.merge import merge
from scraper.model import Dish, WeekMenu

NOW = datetime(2026, 9, 25, 7, 2, 11, tzinfo=timezone.utc)
RESTAURANTS = [
    {"id": "a", "name": "A", "address": "Gatan 1", "lunch_hours": "11–14", "url": "https://a", "reader": "a"},
    {"id": "b", "name": "B", "address": "Gatan 2", "url": "https://b", "reader": "b"},
]
MENU = [WeekMenu(2026, 39, True, {"1": [Dish("Soppa", 120, ["soppa"])]}, "obs")]


def test_merge_success_serialises_weeks():
    out = merge({}, RESTAURANTS, {"a": MENU, "b": MENU}, NOW)
    assert out["generated_at"] == "2026-09-25T07:02:11Z"
    a = out["restaurants"][0]
    assert a["id"] == "a" and a["name"] == "A" and a["address"] == "Gatan 1"
    assert a["lunch_hours"] == "11–14"
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


def test_merge_keeps_old_week_alongside_new_week():
    # A restaurant that had week 39 published now also has week 40 (some
    # restaurants publish next week's menu before this week is over). Both
    # must survive: losing week 39 would show next week's dishes as today's.
    previous = merge({}, RESTAURANTS, {"a": MENU, "b": MENU}, NOW)
    week40 = [WeekMenu(2026, 40, True, {"1": [Dish("Ny rätt", None, [])]}, "")]
    out = merge(previous, RESTAURANTS, {"a": week40, "b": MENU}, NOW)
    a = out["restaurants"][0]
    assert [(w["year"], w["week"]) for w in a["weeks"]] == [(2026, 39), (2026, 40)]


def test_merge_replaces_same_week_with_new_data():
    previous = merge({}, RESTAURANTS, {"a": MENU, "b": MENU}, NOW)
    updated = [WeekMenu(2026, 39, True, {"1": [Dish("Uppdaterad rätt", 99, [])]}, "ny notis")]
    out = merge(previous, RESTAURANTS, {"a": updated, "b": MENU}, NOW)
    a = out["restaurants"][0]
    assert len(a["weeks"]) == 1
    assert a["weeks"][0]["days"]["1"][0]["name"] == "Uppdaterad rätt"
    assert a["weeks"][0]["notes"] == "ny notis"


def test_merge_drops_weeks_older_than_last_week():
    # NOW is 2026-09-25 (ISO week 39); anything older than week 38 is dropped.
    old_weeks = [
        {"year": 2026, "week": 36, "week_known": True, "days": {}, "notes": ""},
        {"year": 2026, "week": 38, "week_known": True, "days": {}, "notes": ""},
    ]
    previous = {"restaurants": [{"id": "a", "name": "A", "url": "https://a",
                                 "address": "Gatan 1", "last_success": None,
                                 "error": "x", "weeks": old_weeks}]}
    out = merge(previous, RESTAURANTS, {"a": MENU, "b": MENU}, NOW)
    a = out["restaurants"][0]
    assert [(w["year"], w["week"]) for w in a["weeks"]] == [(2026, 38), (2026, 39)]
