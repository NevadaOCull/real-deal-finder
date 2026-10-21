from datetime import date, timedelta

from dealfinder.history import PricePoint
from dealfinder.models import OutsideStats
from dealfinder.rating import FAKE, MEH, NO_DEAL, NOT_ENOUGH, REAL, UNAVAILABLE, rate

TODAY = date(2026, 10, 21)


def history(prices):
    """One point per day, ending yesterday."""
    n = len(prices)
    return [PricePoint((TODAY - timedelta(days=n - i)).isoformat(), p) for i, p in enumerate(prices)]


def test_real_deal_when_well_below_normal():
    r = rate(80, history([100] * 30), TODAY, 15)
    assert (r.label, r.normal, r.percent_below, r.lowest, r.history_days) == (REAL, 100, 20.0, 80, 30)


def test_meh_small_discount():
    r = rate(95, history([100] * 30), TODAY, 15)
    assert (r.label, r.percent_below) == (MEH, 5.0)


def test_no_deal_at_normal_price():
    assert rate(100, history([100] * 30), TODAY, 15).label == NO_DEAL


def test_fake_sale_when_was_price_was_inflated_just_before():
    r = rate(95, history([100] * 28 + [150] * 2), TODAY, 15, was_price=150)
    assert r.label == FAKE


def test_honest_was_price_is_meh_not_fake():
    assert rate(95, history([100] * 30), TODAY, 15, was_price=100).label == MEH


def test_sale_claim_at_normal_price_is_fake():
    assert rate(100, history([100] * 30), TODAY, 15, was_price=130).label == FAKE


def test_big_real_drop_wins_even_if_was_price_exaggerated():
    assert rate(70, history([100] * 30), TODAY, 15, was_price=200).label == REAL


def test_not_enough_history():
    r = rate(50, history([100] * 5), TODAY, 15)
    assert (r.label, r.normal, r.lowest, r.history_days) == (NOT_ENOUGH, None, 100, 5)


def test_new_low_counts_as_real_even_if_small_discount():
    r = rate(89, history([100] * 29 + [90]), TODAY, 15)
    assert (r.label, r.percent_below, r.lowest) == (REAL, 11.0, 89)


def test_new_low_needs_30_days():
    assert rate(89, history([100] * 20), TODAY, 15).label == MEH


def test_outside_stats_skip_the_wait():
    r = rate(150, [], TODAY, 15, outside=OutsideStats(normal=200, lowest=140))
    assert (r.label, r.normal, r.lowest, r.percent_below) == (REAL, 200, 140, 25.0)


def test_outside_new_low():
    r = rate(139, [], TODAY, 15, outside=OutsideStats(normal=150, lowest=140))
    assert (r.label, r.percent_below) == (REAL, 7.3)


def test_points_older_than_90_days_ignored_for_normal():
    old = [PricePoint((TODAY - timedelta(days=120 + i)).isoformat(), 500) for i in range(30)]
    assert rate(100, old + history([100] * 20), TODAY, 15).normal == 100


def test_todays_point_is_not_its_own_history():
    points = history([100] * 30) + [PricePoint(TODAY.isoformat(), 80)]
    r = rate(80, points, TODAY, 15)
    assert (r.label, r.history_days) == (REAL, 30)


def test_target_price_hit():
    assert rate(95, history([100] * 30), TODAY, 15, target_price=96).hit_target is True
    assert rate(97, history([100] * 30), TODAY, 15, target_price=96).hit_target is False


def test_unavailable_when_no_price():
    assert rate(None, history([100] * 30), TODAY, 15).label == UNAVAILABLE


def test_failed_days_are_skipped():
    r = rate(80, history([100] * 20 + [None] * 10), TODAY, 15)
    assert (r.label, r.normal, r.history_days) == (REAL, 100, 20)
