import json
from urllib.parse import urlparse

from .fetch import SourceError
from .models import Observation
from .prices import to_number
from .stores import host_of, store_name


def _base(url):
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def _load_json(text, url):
    try:
        data = json.loads(text)
    except ValueError:
        raise SourceError(f"{store_name(url)} didn't send product data") from None
    if not isinstance(data, dict):
        raise SourceError(f"{store_name(url)} didn't send product data")
    return data


def product_from_json(product: dict, url: str) -> Observation | None:
    priced = [(to_number(v.get("price")), v) for v in product.get("variants") or []]
    priced = [(price, v) for price, v in priced if price is not None]
    if not priced:
        return None
    pool = [pv for pv in priced if pv[1].get("available", True)] or priced
    price, variant = min(pool, key=lambda pv: pv[0])
    was = to_number(variant.get("compare_at_price"))
    images = product.get("images") or []
    return Observation(
        id=f"shopify-{host_of(url)}-{product.get('id')}",
        title=product.get("title") or "",
        store=store_name(url),
        url=f"{_base(url)}/products/{product.get('handle')}",
        price=price,
        source="shop",
        was_price=was if was and was > price else None,
        image=images[0].get("src") if images else None,
    )


def section_observations(section_url: str, fetch) -> list[Observation]:
    data = _load_json(fetch(section_url.split("?")[0].rstrip("/") + "/products.json?limit=250"), section_url)
    products = data.get("products")
    if not isinstance(products, list):
        raise SourceError(f"{store_name(section_url)} didn't send product data")
    return [obs for obs in (product_from_json(p, section_url) for p in products) if obs is not None]


def product_observation(product_url: str, fetch) -> Observation:
    data = _load_json(fetch(product_url.split("?")[0].rstrip("/") + ".json"), product_url)
    product = data.get("product")
    obs = product_from_json(product, product_url) if isinstance(product, dict) else None
    if obs is None:
        raise SourceError(f"no price found for {product_url}")
    return obs
