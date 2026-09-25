import scraper.fetch as fetch


class FakeResponse:
    def __init__(self, content=b"ok", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_get_uses_timeout_and_user_agent(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return FakeResponse(b"hello")

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    assert fetch.get("https://example.com/x", headers={"apikey": "k"}) == b"hello"
    assert calls["url"] == "https://example.com/x"
    assert calls["timeout"] == 20
    assert calls["headers"]["apikey"] == "k"
    assert "lunch-lidingo" in calls["headers"]["User-Agent"]


def test_restaurants_yaml_lists_seven_readers():
    import importlib
    import yaml
    entries = yaml.safe_load(open("restaurants.yaml", encoding="utf-8"))
    assert [e["id"] for e in entries] == [
        "firren", "ronneberga", "golf", "pocket", "saluhallen", "bibliothek", "jernet"]
    for e in entries:
        for key in ("id", "name", "address", "lunch_hours", "url", "reader"):
            assert key in e, f"{e.get('id')} saknar {key}"
        module = importlib.import_module(f"scraper.readers.{e['reader']}")
        assert hasattr(module, "read"), f"{e['reader']} saknar read()"
