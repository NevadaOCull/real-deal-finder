import pytest

from dealfinder.camel import amazon_observation, asin_from_url, parse_camel_page
from dealfinder.fetch import SourceError
from helpers import fake_fetch, fixture


def test_asin_from_url():
    assert asin_from_url("https://www.amazon.com/Citizen-Eco-Drive/dp/B00KCF7JL6/ref=sr_1_1?x=y") == "B00KCF7JL6"
    assert asin_from_url("https://amazon.com/gp/product/B00KCF7JL6") == "B00KCF7JL6"
    assert asin_from_url("https://www.amazon.com/dp/B00KCF7JL6") == "B00KCF7JL6"
    assert asin_from_url("https://a.co/d/abc123") is None


def test_parse_real_page():
    stats = parse_camel_page(fixture("camel_B00KCF7JL6.html"))
    assert (stats.current, stats.lowest, stats.average) == (184.63, 51.99, 214.71)
    assert "Citizen" in stats.title


def test_falls_back_to_third_party_when_amazon_out_of_stock():
    html = """<table>
    <tr><td>Amazon</td><td>$10.00</td><td>(Jan 1, 2020)</td><td>$20.00</td><td>(Jan 2, 2020)</td>
        <td>-</td><td></td><td>$15.00</td></tr>
    <tr><td>3rd Party New</td><td>$11.00</td><td>(Jan 1, 2020)</td><td>$21.00</td><td>(Jan 2, 2020)</td>
        <td>$12.50</td><td>(Oct 21, 2026)</td><td>$16.00</td></tr></table>"""
    stats = parse_camel_page(html)
    assert (stats.current, stats.lowest, stats.average) == (12.5, 11.0, 16.0)


def test_page_without_table_is_source_error():
    with pytest.raises(SourceError, match="CamelCamelCamel"):
        parse_camel_page("<html>Just a moment...</html>")


def test_amazon_observation():
    fetch = fake_fetch({"camelcamelcamel.com/product/B00KCF7JL6": fixture("camel_B00KCF7JL6.html")})
    obs = amazon_observation("B00KCF7JL6", fetch)
    assert fetch.calls == ["https://camelcamelcamel.com/product/B00KCF7JL6"]
    assert (obs.id, obs.store, obs.url, obs.price) == (
        "amazon-B00KCF7JL6", "Amazon", "https://www.amazon.com/dp/B00KCF7JL6", 184.63)
    assert (obs.outside.normal, obs.outside.lowest) == (214.71, 51.99)
