from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from .history import PricePoint
from .models import OutsideStats

REAL = "real-deal"
MEH = "meh"
FAKE = "fake-sale"
NO_DEAL = "no-deal"
NOT_ENOUGH = "not-enough-history"
UNAVAILABLE = "unavailable"

WINDOW_DAYS = 90       # "normal price" looks back this far
MIN_DAYS = 14          # history needed before we judge
NEW_LOW_DAYS = 30      # history needed before a new low counts
WAS_PRICE_SHARE = 0.30  # a real "was" price held on at least this share of days


@dataclass
class Rating:
    label: str
    normal: float | None
    lowest: float | None
    percent_below: float | None
    history_days: int
    hit_target: bool = False


def rate(price: float | None, points: list[PricePoint], today: date, threshold_percent: float,
         was_price: float | None = None, outside: OutsideStats | None = None,
         target_price: float | None = None) -> Rating:
    start = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    day = today.isoformat()
    earlier = [p.price for p in points if p.price is not None and p.date < day]
    recent = [p.price for p in points if p.price is not None and start <= p.date < day]
    days = len(recent)

    if price is None:
        return Rating(UNAVAILABLE, None, min(earlier) if earlier else None, None, days)

    hit_target = target_price is not None and price <= target_price
    lowest_candidates = earlier + ([outside.lowest] if outside else [])
    lowest_before = min(lowest_candidates) if lowest_candidates else None

    if outside:
        normal = outside.normal
    elif days >= MIN_DAYS:
        normal = median(recent)
    else:
        return Rating(NOT_ENOUGH, None, lowest_before, None, days, hit_target)

    percent_below = round((normal - price) / normal * 100, 1)
    lowest = min(price, lowest_before) if lowest_before is not None else price
    long_enough = outside is not None or len(earlier) >= NEW_LOW_DAYS
    # A new low only counts when it beats an earlier sale, not a dip below a flat price.
    new_low = long_enough and lowest_before is not None and lowest_before < normal and price < lowest_before
    claims_sale = was_price is not None and was_price > price

    if percent_below >= threshold_percent or new_low:
        label = REAL
    elif claims_sale and days >= MIN_DAYS and \
            sum(1 for p in recent if p >= was_price * 0.98) / days < WAS_PRICE_SHARE:
        label = FAKE
    elif percent_below >= 1:
        label = MEH
    elif claims_sale:
        label = FAKE
    else:
        label = NO_DEAL
    return Rating(label, normal, lowest, percent_below, days, hit_target)
