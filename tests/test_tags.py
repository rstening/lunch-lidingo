import pytest

from scraper.tags import guess_tags


@pytest.mark.parametrize("name, expected", [
    # Fish and shellfish
    ("Krämig fiskgryta på lax och kolja med saffransmajo", ["fisk"]),
    ("Färserad röding med gräslöksvitvinssås", ["fisk"]),
    ("Stekt sejfilé med kräftröra, citron & färskpotatis", ["fisk"]),
    ("Gösfilé meunière med kapris och brynt smör", ["fisk"]),
    ("Rödtunga med vitvinssås, sparris, räkor", ["fisk"]),
    ("Pockets Bouillabaisse, räkor, crabfish, citron", ["fisk"]),
    ("Firrens queneller med räksås och potatismos", ["fisk"]),
    ("Fisk- & skaldjursgryta med smak av tomat & saffran", ["fisk"]),
    # Meat
    ("Kalops på kalvkött med rödbetor och kokt potatis", ["kött"]),
    ("Färskostfylld kyckling med cidersås", ["kött"]),
    ("Rostad kycklingklubba, ratatouille, örtkräm", ["kött"]),
    ("Fläskkotlett, rotfruktsgratäng, rödvinssås", ["kött"]),
    ("Korvstroganoff, ris, smetana, saltgurka", ["kött"]),
    ("Biffstroganoff med ris, smetana samt saltgurka", ["kött"]),
    ("Isterband med stuvad potatis, senap & rödbetor", ["kött"]),
    ("Örtrostad porchetta med chilibakad spetskål", ["kött"]),
    ("Flankstek med chimichurri, smashad gurka", ["kött"]),
    ("Pulled Pork burgare, picklad rödlök, tryffelmajonnäs", ["kött"]),
    ("Steak minute pommes frites och bearnaisesås", ["kött"]),
    ("Nötschnitzel med rostad potatis serveras med svampsås", ["kött"]),
    ("Grillbuffé - med olika sortes kött & goda tillbehör", ["kött"]),
    ("Coq au vin med krossad potatis, dijonaise och örter", ["kött"]),
    ("Bakad fläsksida från Nibble gård kokt gourmetpotatis", ["kött"]),
    # Vegetarian
    ("Vegetarisk moussaka", ["veg"]),
    ("Vegansk chili sin carne", ["veg"]),
    ("Wok med tofu", ["veg"]),
    ("Pannoumi paneer", ["veg"]),
    ("Linsbolognese med pasta", ["veg"]),
    ("Halloumiburgare med klyftpotatis", ["veg"]),
    ("Falafel med hummus och pitabröd", ["veg"]),
    # Soup
    ("Dagens soppa", ["soppa"]),
    ("Ärtsoppa med pannkakor, sylt & grädde", ["soppa"]),
    ("Fisksoppa med aioli", ["soppa"]),
    # Not sure: no tag
    ("Pannkakor", []),
    ("Broccoli-& ädelostpaj med sallad & örtcrème", []),
    ("Pad kra pao med stekt ägg, basilika & ris", []),
    ("Krämig gnocchi, blandsvamp, soltorkad tomat", []),
    ("Idag bjuder vi på Pockets äppelpaj & vaniljsås", []),
    ("", []),
])
def test_guess_tags(name, expected):
    assert guess_tags(name) == expected


def test_first_mentioned_main_ingredient_wins():
    assert guess_tags("Långafilé med bechamelsås, ärtor, bacon & kokt potatis") == ["fisk"]
    assert guess_tags("Fläskschnitzel med anjovis- & kaprissmör") == ["kött"]
    assert guess_tags("Kyckling i röd curry med fisksås") == ["kött"]
    assert guess_tags("Kyckling med linser och spenat") == ["kött"]
    assert guess_tags("Havets wallenbergare, potatismos, brynt smör") == ["fisk"]
    assert guess_tags("Pockets Wallenbergare, brynt smör, potatismos") == ["kött"]


def test_explicit_vegetarian_beats_other_words():
    assert guess_tags("Vegetarisk broccolibiffar, rostad sötpotatis") == ["veg"]
    assert guess_tags("Vegetarisk raggmunk, tångkaviar, cremefraiche") == ["veg"]
    assert guess_tags("Vegokorv med potatismos") == ["veg"]


def test_stems_do_not_match_inside_other_words():
    assert guess_tags("Rostad blomkål med nötter och fetaost") == []
    assert guess_tags("Grönsaksbiffar med tzatziki") == []
    assert guess_tags("Stekt potatis med persilja och apelsin") == []
    assert guess_tags("Köttfri gryta") == []
