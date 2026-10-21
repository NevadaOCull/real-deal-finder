import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from .fetch import SourceError
from .models import Observation
from .prices import parse_price
from .stores import store_from_slug

SEARCH_URL = "https://slickdeals.net/newsearch.php?q={q}&searcharea=deals&searchin=first&rss=1"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
MAX_AGE = timedelta(days=14)


@dataclass
class SlickDeal:
    thread_id: str
    title: str
    link: str
    price: float | None
    store_slug: str | None
    asin: str | None
    image: str | None
    posted: datetime | None


def _first(pattern, text):
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _posted(text):
    try:
        return parsedate_to_datetime(text) if text else None
    except (TypeError, ValueError):
        return None


def parse_feed(xml_text: str) -> list[SlickDeal]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise SourceError(f"Slickdeals sent a feed that couldn't be read ({e})") from None
    deals = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        content = item.findtext(CONTENT) or ""
        deals.append(SlickDeal(
            thread_id=_first(r"/f/(\d+)", link) or link,
            title=title,
            link=link.split("?")[0],
            price=parse_price(title),
            store_slug=_first(r'data-store-slug="([^"]+)"', content),
            asin=_first(r'data-aps-asin="([A-Z0-9]{10})"', content),
            image=_first(r'<img[^>]+src="([^"]+)"', content),
            posted=_posted(item.findtext("pubDate")),
        ))
    return deals


def _matches(term, title):
    title = title.lower()
    return all(word in title for word in term.lower().split())


def search(term: str, fetch, now: datetime) -> list[SlickDeal]:
    deals = parse_feed(fetch(SEARCH_URL.format(q=quote_plus(term))))
    return [d for d in deals
            if d.price is not None and _matches(term, d.title)
            and d.posted is not None and now - d.posted <= MAX_AGE]


def deal_observation(deal: SlickDeal) -> Observation:
    item_id = f"amazon-{deal.asin}" if deal.asin else f"sd-{deal.thread_id}"
    return Observation(id=item_id, title=deal.title, store=store_from_slug(deal.store_slug),
                       url=deal.link, price=deal.price, source="slickdeals", image=deal.image)
