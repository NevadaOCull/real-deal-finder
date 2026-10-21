import hashlib
from urllib.parse import urlparse

STORE_NAMES = {
    "amazon.com": "Amazon",
    "walmart.com": "Walmart",
    "homedepot.com": "Home Depot",
    "drifthq.com": "DriftHQ",
    "fdfraceshop.com": "FDF Raceshop",
    "synergyracedevelopment.com": "Synergy Race Development",
    "driftamerican.com": "Drift American",
    "enjukuracing.com": "Enjuku Racing",
}

# Slickdeals' names for stores, where title-casing the slug isn't right.
SLUG_NAMES = {
    "amazon": "Amazon",
    "walmart": "Walmart",
    "home-depot": "Home Depot",
    "the-home-depot": "Home Depot",
    "best-buy": "Best Buy",
    "lowes": "Lowe's",
}


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def store_name(url: str) -> str:
    host = host_of(url)
    return STORE_NAMES.get(host, host)


def store_from_slug(slug: str | None) -> str:
    if not slug:
        return "Unknown store"
    return SLUG_NAMES.get(slug, slug.replace("-", " ").title())


def page_id(url: str) -> str:
    key = host_of(url) + urlparse(url).path.rstrip("/")
    return "page-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
