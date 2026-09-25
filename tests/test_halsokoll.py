import importlib.util
from datetime import datetime, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "halsokoll", Path(__file__).resolve().parent.parent / "tools" / "halsokoll.py")
halsokoll = importlib.util.module_from_spec(spec)
spec.loader.exec_module(halsokoll)

NOW = datetime(2026, 9, 30, 9, 0, tzinfo=timezone.utc)


def restaurant(rid, error=None, last_success="2026-09-30T07:00:00Z"):
    return {"id": rid, "name": rid.capitalize(), "url": f"https://{rid}.example",
            "error": error, "last_success": last_success, "weeks": []}


DATA = {"restaurants": [
    restaurant("ok"),
    restaurant("idag", error="HTTPError: 500", last_success="2026-09-29T07:00:00Z"),   # 26 h: not yet
    restaurant("tva", error="HTTPError: 403", last_success="2026-09-28T07:00:00Z"),    # 50 h: failing
    restaurant("aldrig", error="ParseError: x", last_success=None),                    # never worked
]}


def test_only_restaurants_failing_about_two_days_count():
    ids = [r["id"] for r in halsokoll.failing_restaurants(DATA, NOW)]
    assert ids == ["tva", "aldrig"]


def test_plan_opens_new_issues_and_skips_existing_ones():
    existing = [{"number": 7, "body": halsokoll.MARKER.format(id="tva") + "\ntext"}]
    to_open, to_close = halsokoll.plan(DATA, existing, NOW)
    assert [r["id"] for r in to_open] == ["aldrig"]
    assert to_close == []


def test_plan_closes_issue_when_restaurant_works_again():
    existing = [{"number": 9, "body": halsokoll.MARKER.format(id="ok")}]
    _, to_close = halsokoll.plan(DATA, existing, NOW)
    assert [(r["id"], i["number"]) for r, i in to_close] == [("ok", 9)]


def test_a_single_failed_run_keeps_an_open_issue_open():
    # "idag" failed only once, but if an issue already exists it must not be closed.
    existing = [{"number": 3, "body": halsokoll.MARKER.format(id="idag")}]
    to_open, to_close = halsokoll.plan(DATA, existing, NOW)
    assert to_close == [] and "idag" not in [r["id"] for r in to_open]


def test_issue_body_is_swedish_and_has_marker():
    body = halsokoll.issue_body(DATA["restaurants"][2], "https://run")
    assert body.startswith(halsokoll.MARKER.format(id="tva"))
    assert "har misslyckats i ungefär två dagar" in body and "HTTPError: 403" in body
