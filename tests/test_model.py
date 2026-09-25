from scraper.model import Dish, WeekMenu, clean


def test_clean_collapses_whitespace_and_nbsp():
    assert clean("  Scampi\xa0Indiana \n med   ris ") == "Scampi Indiana med ris"


def test_dish_defaults():
    d = Dish("Köttbullar")
    assert d.price is None
    assert d.tags == []


def test_weekmenu_holds_days():
    w = WeekMenu(year=2026, week=40, week_known=True, days={"1": [Dish("Soppa")]})
    assert w.days["1"][0].name == "Soppa"
    assert w.notes == ""
