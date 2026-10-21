from urllib.parse import urlparse

from .camel import amazon_observation, asin_from_url
from .fetch import SourceError
from .models import Observation
from .pricepage import page_observation
from .settings import WatchItem
from .shopify import product_observation
from .stores import host_of, page_id, store_name


def _amazon_asin(url):
    return asin_from_url(url) if "amazon." in host_of(url) else None


def _read(url, fetch):
    if asin := _amazon_asin(url):
        return amazon_observation(asin, fetch)
    if "/products/" in urlparse(url).path:
        try:
            return product_observation(url, fetch)
        except SourceError:
            pass  # not a Shopify store after all; read the page instead
    return page_observation(url, fetch)


def watch_observation(item: WatchItem, fetch) -> Observation:
    try:
        obs = _read(item.url, fetch)
    except SourceError as e:
        asin = _amazon_asin(item.url)
        obs = Observation(id=f"amazon-{asin}" if asin else page_id(item.url), title=item.url,
                          store=store_name(item.url), url=item.url, price=None,
                          source="watchlist", error=str(e))
    if item.name:
        obs.title = item.name
    obs.target_price = item.target_price
    return obs
