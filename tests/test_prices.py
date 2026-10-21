from dealfinder.prices import parse_price, to_number


def test_parse_price_formats():
    assert parse_price("Citizen Watch $184.65 + Free S&H") == 184.65
    assert parse_price("MacBook $1,299.99") == 1299.99
    assert parse_price("Kits + $173.59–$369.99 Shipped") == 173.59
    assert parse_price("Massimo Mini 125 - $2499.99") == 2499.99
    assert parse_price("Jacket $31 + Free S&H") == 31.0
    assert parse_price("AutoZone Sweepstakes 6-27-22") is None
    assert parse_price(None) is None


def test_to_number():
    assert to_number("8.99") == 8.99
    assert to_number("1,299.00") == 1299.0
    assert to_number(7.5) == 7.5
    assert to_number(135) == 135.0
    assert to_number("") is None
    assert to_number(None) is None
    assert to_number("0.00") is None
    assert to_number(True) is None
