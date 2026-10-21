from dealfinder.fetch import SourceError
from dealfinder.settings import WatchItem
from dealfinder.stores import page_id
from dealfinder.watchlist import watch_observation
from helpers import fake_fetch, fixture

SYNERGY = "https://synergyracedevelopment.com/2005-2014-mustang-s197-spindle-bushings/"


def test_amazon_link_uses_camelcamelcamel():
    fetch = fake_fetch({"camelcamelcamel.com": fixture("camel_B00KCF7JL6.html")})
    obs = watch_observation(WatchItem("https://www.amazon.com/Citizen/dp/B00KCF7JL6?th=1", 150, "My watch"), fetch)
    assert (obs.id, obs.price, obs.target_price, obs.title) == ("amazon-B00KCF7JL6", 184.63, 150, "My watch")
    assert obs.outside is not None


def test_shopify_product_link():
    fetch = fake_fetch({"fdfraceshop.com": fixture("shopify_fdf_product.json")})
    obs = watch_observation(WatchItem("https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie"), fetch)
    assert (obs.price, obs.source, obs.target_price) == (47.27, "shop", None)


def test_other_store_reads_the_page():
    fetch = fake_fetch({"synergyracedevelopment.com": fixture("bigcommerce_synergy.html")})
    obs = watch_observation(WatchItem(SYNERGY), fetch)
    assert (obs.price, obs.source) == (7.5, "page")


def test_products_path_that_isnt_shopify_falls_back_to_page():
    url = "https://driftamerican.com/products/brake-lines"
    fetch = fake_fetch({".json": SourceError("not shopify"),
                        "driftamerican.com": fixture("bigcommerce_driftamerican.html")})
    obs = watch_observation(WatchItem(url), fetch)
    assert (obs.price, obs.source) == (135, "page")


def test_blocked_item_is_reported_not_guessed():
    url = "https://www.homedepot.com/p/Milwaukee-Drill/306224456"
    fetch = fake_fetch({"homedepot.com": SourceError("homedepot.com blocked the check (error 403)")})
    obs = watch_observation(WatchItem(url, 99, "Milwaukee drill"), fetch)
    assert obs.price is None
    assert obs.error == "homedepot.com blocked the check (error 403)"
    assert (obs.id, obs.title, obs.store, obs.target_price) == (page_id(url), "Milwaukee drill", "Home Depot", 99)


def test_blocked_amazon_item_keeps_amazon_id():
    fetch = fake_fetch({"camelcamelcamel.com": SourceError("down")})
    obs = watch_observation(WatchItem("https://www.amazon.com/dp/B00KCF7JL6"), fetch)
    assert (obs.id, obs.price) == ("amazon-B00KCF7JL6", None)
