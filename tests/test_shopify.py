import pytest

from dealfinder.fetch import SourceError
from dealfinder.shopify import product_from_json, product_observation, section_observations
from helpers import fake_fetch, fixture

GARAGE = "https://drifthq.com/collections/garage-sale"


def test_section_observations():
    fetch = fake_fetch({"drifthq.com": fixture("shopify_drifthq_garage.json")})
    found = section_observations(GARAGE + "/", fetch)
    assert fetch.calls == [GARAGE + "/products.json?limit=250"]
    assert len(found) == 5
    shirt = found[0]
    assert shirt.id == "shopify-drifthq.com-7816453619899"
    assert (shirt.price, shirt.was_price, shirt.store) == (10.0, 30.0, "DriftHQ")
    assert shirt.url == "https://drifthq.com/products/lzmfg-x-dhq-shirt"
    assert shirt.image.startswith("https://")


def test_no_compare_price_means_no_was_price():
    found = section_observations(GARAGE, fake_fetch({"drifthq.com": fixture("shopify_drifthq_garage.json")}))
    leo = next(o for o in found if "Leo Grande" in o.title)
    assert (leo.price, leo.was_price) == (100.0, None)


def test_product_observation():
    fetch = fake_fetch({"fdfraceshop.com": fixture("shopify_fdf_product.json")})
    obs = product_observation("https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie?variant=1", fetch)
    assert fetch.calls == ["https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie.json"]
    assert (obs.price, obs.was_price, obs.store) == (47.27, None, "FDF Raceshop")
    assert obs.id == "shopify-fdfraceshop.com-7345075060789"


def test_sold_out_everywhere_still_has_price():
    product = {"id": 1, "handle": "x", "title": "X", "variants": [
        {"price": "50.00", "compare_at_price": "80.00", "available": False},
        {"price": "40.00", "compare_at_price": None, "available": False}]}
    assert product_from_json(product, "https://drifthq.com/").price == 40.0


def test_cheapest_available_variant_wins():
    product = {"id": 1, "handle": "x", "title": "X", "variants": [
        {"price": "30.00", "compare_at_price": "45.00", "available": False},
        {"price": "40.00", "compare_at_price": "60.00", "available": True}]}
    obs = product_from_json(product, "https://drifthq.com/")
    assert (obs.price, obs.was_price) == (40.0, 60.0)


def test_product_without_prices_is_none():
    assert product_from_json({"id": 1, "handle": "x", "variants": []}, "https://drifthq.com/") is None


def test_non_shopify_answer_is_source_error():
    fetch = fake_fetch({"synergyracedevelopment.com": "<!DOCTYPE html><html>Not Found</html>"})
    with pytest.raises(SourceError, match="Synergy Race Development"):
        product_observation("https://synergyracedevelopment.com/products/x", fetch)
