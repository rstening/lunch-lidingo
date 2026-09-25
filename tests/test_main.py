"""Tests for the run_all / main empty-page guard in scraper.__main__."""
import json
import sys
import types
from datetime import date

import yaml

import scraper.__main__ as main_mod
from scraper.model import Dish, WeekMenu


def _fake_module(name, read_fn):
    mod = types.ModuleType(name)
    mod.read = read_fn
    return mod


def _ok_read(get, url, today):
    return [WeekMenu(year=2026, week=39, week_known=True,
                     days={"1": [Dish("Toast", 79, [])]}, notes="")]


def _fail_read(get, url, today):
    raise RuntimeError("kunde inte hämta")


def _empty_read(get, url, today):
    return []


def _write_restaurants(tmp_path, entries):
    path = tmp_path / "restaurants.yaml"
    path.write_text(yaml.safe_dump(entries), encoding="utf-8")
    return path


def test_all_readers_failing_returns_1_and_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "scraper.readers.fake_fail",
                        _fake_module("scraper.readers.fake_fail", _fail_read))
    data_path = tmp_path / "menus.json"
    monkeypatch.setattr(main_mod, "DATA_PATH", data_path)
    restaurants = [
        {"id": "a", "name": "A", "url": "https://a", "address": "", "reader": "fake_fail"},
        {"id": "b", "name": "B", "url": "https://b", "address": "", "reader": "fake_fail"},
    ]
    yaml_path = _write_restaurants(tmp_path, restaurants)

    rc = main_mod.main(["--restaurants", str(yaml_path), "--date", "2026-09-25"])

    assert rc == 1
    assert not data_path.exists()


def test_one_failing_one_succeeding_returns_0_and_writes_both(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "scraper.readers.fake_ok",
                        _fake_module("scraper.readers.fake_ok", _ok_read))
    monkeypatch.setitem(sys.modules, "scraper.readers.fake_fail",
                        _fake_module("scraper.readers.fake_fail", _fail_read))
    data_path = tmp_path / "menus.json"
    monkeypatch.setattr(main_mod, "DATA_PATH", data_path)
    restaurants = [
        {"id": "a", "name": "A", "url": "https://a", "address": "", "reader": "fake_ok"},
        {"id": "b", "name": "B", "url": "https://b", "address": "", "reader": "fake_fail"},
    ]
    yaml_path = _write_restaurants(tmp_path, restaurants)

    rc = main_mod.main(["--restaurants", str(yaml_path), "--date", "2026-09-25"])

    assert rc == 0
    data = json.loads(data_path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in data["restaurants"]}
    assert by_id["a"]["error"] is None
    assert by_id["a"]["weeks"][0]["days"]["1"][0]["name"] == "Toast"
    assert by_id["b"]["error"] is not None and "RuntimeError" in by_id["b"]["error"]
    assert by_id["b"]["weeks"] == []


def test_reader_returning_empty_list_is_recorded_as_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "scraper.readers.fake_empty",
                        _fake_module("scraper.readers.fake_empty", _empty_read))
    restaurants = [{"id": "a", "name": "A", "url": "https://a", "address": "", "reader": "fake_empty"}]

    results = main_mod.run_all(restaurants, date(2026, 9, 25))

    assert not isinstance(results["a"], list)
    assert isinstance(results["a"], Exception)
