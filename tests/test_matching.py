from dealfinder.matching import matches


def test_phrase_must_appear_together():
    assert matches("angle kit", "Steering Angle Kit for SN95 Mustang")
    assert not matches("angle kit", "Ryobi 4-1/2 in. Angle Grinder with 2.0 Ah Battery and Charger Kit")


def test_whole_words_only():
    assert not matches("angle kit", "Bosch 18V Cordless Angled Finish Nailer + FREE Kit")
    assert not matches("new edge mustang", "roborock 2026 New Qrevo Edge 3 Pro")
    assert not matches("gt", "Weighted Blanket")


def test_plurals_and_case():
    assert matches("coilover", "20% OFF COILOVERS Kits at Flashark")
    assert matches("subframe connector", "Maximum Motorsports Subframe Connectors")
    assert matches("bucket seat", "Sparco bucket seat")


def test_punctuation_in_terms():
    assert matches("eco-drive", "45mm Citizen Eco-Drive Avion Watch")
    assert matches("mustang 4.6", "Ford Mustang 4.6 cold air intake")
    assert not matches("mustang 4.6", "Ford Mustang 4.60 decal")
