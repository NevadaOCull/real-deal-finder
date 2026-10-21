import json
import re
from dataclasses import dataclass
from html import unescape

from .fetch import SourceError
from .models import Observation
from .prices import to_number
from .stores import page_id, store_name

META_TAG = re.compile(r"<meta\b[^>]*>", re.I)
ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
PRICE_META_KEYS = ("product:price:amount", "og:price:amount", "price")


@dataclass
class PageInfo:
    title: str | None
    price: float | None
    image: str | None


def _meta(html):
    found = {}
    for tag in META_TAG.findall(html):
        attrs = {key.lower(): value for key, value in ATTR.findall(tag)}
        key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
        if key and "content" in attrs:
            found.setdefault(key.lower(), unescape(attrs["content"]).strip())
    return found


def _offer_price(node):
    if isinstance(node, list):
        for child in node:
            price = _offer_price(child)
            if price is not None:
                return price
    elif isinstance(node, dict):
        for key in ("price", "lowPrice"):
            price = to_number(node.get(key))
            if price is not None:
                return price
        return _offer_price(node.get("priceSpecification"))
    return None


def _ld_price(node):
    if isinstance(node, list):
        for child in node:
            price = _ld_price(child)
            if price is not None:
                return price
    elif isinstance(node, dict):
        if "offers" in node:
            price = _offer_price(node["offers"])
            if price is not None:
                return price
        for value in node.values():
            if isinstance(value, (dict, list)):
                price = _ld_price(value)
                if price is not None:
                    return price
    return None


def parse_product_page(html: str) -> PageInfo:
    meta = _meta(html)
    price = next((p for p in (to_number(meta.get(k)) for k in PRICE_META_KEYS) if p is not None), None)
    if price is None:
        for block in LD_JSON.findall(html):
            try:
                data = json.loads(block, strict=False)
            except ValueError:
                continue
            price = _ld_price(data)
            if price is not None:
                break
    title = meta.get("og:title")
    if not title and (match := TITLE.search(html)):
        title = unescape(match.group(1)).strip()
    return PageInfo(title=title or None, price=price, image=meta.get("og:image"))


def page_observation(url: str, fetch) -> Observation:
    info = parse_product_page(fetch(url))
    if info.price is None:
        raise SourceError(f"no price found on {store_name(url)} page (it may have blocked the check)")
    return Observation(id=page_id(url), title=info.title or url, store=store_name(url), url=url,
                       price=info.price, source="page", image=info.image)
