import pytest

from dealfinder.fetch import SourceError
from dealfinder.pricepage import page_observation, parse_product_page
from helpers import fake_fetch, fixture


def test_bigcommerce_synergy():
    info = parse_product_page(fixture("bigcommerce_synergy.html"))
    assert info.price == 7.5
    assert info.title == "2005-2014 Mustang S197 Spindle Bushings"
    assert info.image.startswith("https://cdn11.bigcommerce.com/")


def test_bigcommerce_drift_american():
    info = parse_product_page(fixture("bigcommerce_driftamerican.html"))
    assert info.price == 135
    assert info.title == "1979-2004 Mustang Extended Length Steel Braided Front Brake Lines"


def test_json_ld_offer_list_with_comma_price():
    html = """<html><head><title>Big Drill | Shop</title>
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
    "name":"Big Drill","offers":[{"@type":"Offer","price":"1,299.99","priceCurrency":"USD"}]}</script>
    </head></html>"""
    info = parse_product_page(html)
    assert (info.title, info.price) == ("Big Drill | Shop", 1299.99)


def test_json_ld_graph_and_low_price():
    html = """<script type="application/ld+json">{"@graph":[{"@type":"WebPage"},
    {"@type":"Product","offers":{"@type":"AggregateOffer","lowPrice":49.5}}]}</script>"""
    assert parse_product_page(html).price == 49.5


def test_broken_json_ld_is_skipped():
    html = '<script type="application/ld+json">{oops</script><meta itemprop="price" content="12.00">'
    assert parse_product_page(html).price == 12.0


def test_bot_check_page_has_no_price():
    html = "<html><head><title>Robot or human?</title></head><body>Press and hold</body></html>"
    assert parse_product_page(html).price is None


def test_page_observation():
    url = "https://synergyracedevelopment.com/2005-2014-mustang-s197-spindle-bushings/"
    obs = page_observation(url, fake_fetch({"synergyracedevelopment.com": fixture("bigcommerce_synergy.html")}))
    assert obs.id.startswith("page-")
    assert (obs.store, obs.price, obs.url, obs.source) == ("Synergy Race Development", 7.5, url, "page")


def test_page_without_price_is_source_error():
    fetch = fake_fetch({"walmart.com": "<title>Robot or human?</title>"})
    with pytest.raises(SourceError, match="no price found on Walmart page"):
        page_observation("https://www.walmart.com/ip/1", fetch)
