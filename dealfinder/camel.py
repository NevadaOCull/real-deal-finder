import re
from dataclasses import dataclass
from html import unescape

from .fetch import SourceError
from .models import Observation, OutsideStats
from .pricepage import parse_product_page
from .prices import to_number

CAMEL_URL = "https://camelcamelcamel.com/product/{asin}"
ASIN = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)")
MONEY = r"\$([\d,]+(?:\.\d{1,2})?)"
DATE = r"\([^)]*\)"


@dataclass
class CamelStats:
    title: str | None
    current: float
    lowest: float
    average: float


def asin_from_url(url: str) -> str | None:
    match = ASIN.search(url)
    return match.group(1) if match else None


def _table_text(html):
    """Page text with every tag turned into a single ' | ' cell separator."""
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]+>", "|", text)).replace("\xa0", " ")
    return re.sub(r"\s*(?:\|\s*)+", " | ", text)


def _row_pattern(label):
    # Columns: Lowest Ever (date), Highest Ever (date), Current (date), Average
    cell = rf"{MONEY} \| {DATE}"
    return rf"\| {re.escape(label)} \| {cell} \| {cell} \| {cell} \| {MONEY}"


def parse_camel_page(html: str) -> CamelStats:
    text = _table_text(html)
    for label in ("Amazon", "3rd Party New"):
        match = re.search(_row_pattern(label), text)
        values = [to_number(g) for g in match.groups()] if match else [None]
        if None not in values:
            lowest, _highest, current, average = values
            return CamelStats(title=parse_product_page(html).title, current=current,
                              lowest=lowest, average=average)
    raise SourceError("couldn't read the CamelCamelCamel price table")


def amazon_observation(asin: str, fetch) -> Observation:
    stats = parse_camel_page(fetch(CAMEL_URL.format(asin=asin)))
    return Observation(id=f"amazon-{asin}", title=stats.title or f"Amazon item {asin}", store="Amazon",
                       url=f"https://www.amazon.com/dp/{asin}", price=stats.current, source="camelcamelcamel",
                       outside=OutsideStats(normal=stats.average, lowest=stats.lowest))
