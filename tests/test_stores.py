from dealfinder.stores import host_of, page_id, store_from_slug, store_name


def test_store_names():
    assert store_name("https://www.homedepot.com/p/x/123") == "Home Depot"
    assert store_name("https://drifthq.com/products/x") == "DriftHQ"
    assert store_name("https://driftamerican.com/x/") == "Drift American"
    assert store_name("https://shop.example.com/x") == "shop.example.com"


def test_host_of():
    assert host_of("https://WWW.Walmart.com:443/ip/1") == "walmart.com"


def test_store_from_slug():
    assert store_from_slug("home-depot") == "Home Depot"
    assert store_from_slug("amazon") == "Amazon"
    assert store_from_slug("tractor-supply-co") == "Tractor Supply Co"
    assert store_from_slug(None) == "Unknown store"


def test_page_id_is_stable_and_ignores_query_and_slash():
    a = page_id("https://driftamerican.com/brake-lines/?utm=1")
    assert a == page_id("https://www.driftamerican.com/brake-lines")
    assert a.startswith("page-") and len(a) == 17
