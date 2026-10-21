from datetime import datetime, timezone

import pytest

from dealfinder.fetch import SourceError
from dealfinder.slickdeals import deal_observation, parse_feed, search
from helpers import fake_fetch, fixture

OCT_21 = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)
JUN_1 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_parse_frontpage():
    deals = parse_feed(fixture("slickdeals_frontpage.xml"))
    assert len(deals) == 25
    first = deals[0]
    assert first.thread_id == "20184453"
    assert first.price == 184.65
    assert first.store_slug == "amazon"
    assert first.asin == "B00KCF7JL6"
    assert first.image.startswith("https://static.slickdealscdn.com/")
    assert first.link.startswith("https://slickdeals.net/f/20184453-") and "utm_" not in first.link
    assert first.posted.date().isoformat() == "2026-10-21"


def test_search_drops_old_posts():
    fetch = fake_fetch({"slickdeals.net": fixture("slickdeals_coilovers.xml")})
    assert search("coilovers", fetch, OCT_21) == []


def test_search_keeps_recent_matching_priced_posts():
    fetch = fake_fetch({"slickdeals.net": fixture("slickdeals_coilovers.xml")})
    found = search("coilovers", fetch, JUN_1)
    assert [d.price for d in found] == [173.59]
    assert found[0].store_slug == "flasharkracing"


def test_search_requires_every_word_in_title():
    fetch = fake_fetch({"slickdeals.net": fixture("slickdeals_frontpage.xml")})
    assert [d.thread_id for d in search("citizen watch", fetch, OCT_21)] == ["20184453"]
    assert search("citizen toaster", fetch, OCT_21) == []


def test_search_url_encodes_term():
    fetch = fake_fetch({"slickdeals.net": fixture("slickdeals_frontpage.xml")})
    search("bucket seat", fetch, OCT_21)
    assert "q=bucket+seat" in fetch.calls[0] and "rss=1" in fetch.calls[0]


def test_unreadable_feed_is_source_error():
    with pytest.raises(SourceError, match="Slickdeals"):
        parse_feed("<html>not a feed")


def test_observations():
    deals = parse_feed(fixture("slickdeals_frontpage.xml"))
    amazon = deal_observation(deals[0])
    assert (amazon.id, amazon.store, amazon.price, amazon.source) == ("amazon-B00KCF7JL6", "Amazon", 184.65, "slickdeals")
    dicks = next(d for d in deals if d.store_slug == "dicks-sporting-goods")
    obs = deal_observation(dicks)
    assert obs.id == f"sd-{dicks.thread_id}"
    assert obs.store == "Dicks Sporting Goods"
