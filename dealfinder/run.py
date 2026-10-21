"""Daily check: collect prices, update history, rate everything, write the page data, email alerts."""
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import camel, emailer, shopify, slickdeals
from .fetch import fetch as real_fetch
from .history import History
from .models import Observation
from .rating import FAKE, MEH, NO_DEAL, NOT_ENOUGH, REAL, rate
from .settings import Settings, SettingsError, load_settings
from .stores import page_id, store_name
from .watchlist import watch_observation

CAMEL_LOOKUPS_PER_RUN = 40
PAUSE_SECONDS = 2
CHART_DAYS = 90
LABEL_ORDER = {REAL: 0, MEH: 1, NOT_ENOUGH: 2, NO_DEAL: 3, FAKE: 4}


@dataclass
class SourceStatus:
    name: str
    ok: bool
    message: str = ""


def _slickdeals(settings, fetch, now, pause, deals):
    searches = [(interest, term) for interest, terms in settings.interests.items() for term in terms]
    failures = []
    camel_left = CAMEL_LOOKUPS_PER_RUN
    for interest, term in searches:
        try:
            found = slickdeals.search(term, fetch, now)
        except Exception as e:
            failures.append(f"'{term}': {e}")
            continue
        for deal in found:
            obs = slickdeals.deal_observation(deal)
            if obs.id in deals:
                continue
            if deal.asin and camel_left > 0:
                camel_left -= 1
                pause(PAUSE_SECONDS)
                try:
                    obs.outside = camel.amazon_observation(deal.asin, fetch).outside
                except Exception:
                    pass  # rated on Slickdeals' price alone; history builds up over time
            obs.interest = interest
            deals[obs.id] = obs
    return SourceStatus("Slickdeals", not failures, "; ".join(failures))


def _shop_sections(settings, fetch, deals):
    statuses = []
    for url in settings.shop_sections:
        name = f"{store_name(url)} sale section"
        try:
            found = shopify.section_observations(url, fetch)
        except Exception as e:
            statuses.append(SourceStatus(name, False, str(e)))
            continue
        for obs in found:
            obs.interest = "Shop sales"
            deals.setdefault(obs.id, obs)
        statuses.append(SourceStatus(name, True))
    return statuses


def _watchlist(settings, fetch, pause):
    watched = []
    for item in settings.watchlist:
        if watched:
            pause(PAUSE_SECONDS)
        try:
            watched.append(watch_observation(item, fetch))
        except Exception as e:
            watched.append(Observation(id=page_id(item.url), title=item.name or item.url,
                                       store=store_name(item.url), url=item.url, price=None,
                                       source="watchlist", target_price=item.target_price,
                                       error=f"unexpected problem: {e}"))
    failed = sum(1 for obs in watched if obs.error)
    message = f"{failed} of {len(watched)} items couldn't be checked" if failed else ""
    return watched, SourceStatus("Watchlist", not failed, message)


def collect(settings: Settings, fetch, now: datetime, pause=time.sleep):
    deals: dict[str, Observation] = {}
    statuses = [_slickdeals(settings, fetch, now, pause, deals)]
    statuses += _shop_sections(settings, fetch, deals)
    watched, watch_status = _watchlist(settings, fetch, pause)
    statuses.append(watch_status)
    return list(deals.values()), watched, statuses


def _entry(obs, history, today, threshold):
    points = history.record(obs, today)
    rating = rate(obs.price, points, today, threshold, was_price=obs.was_price,
                  outside=obs.outside, target_price=obs.target_price)
    since = (today - timedelta(days=CHART_DAYS)).isoformat()
    return {
        "id": obs.id, "title": obs.title, "store": obs.store, "url": obs.url, "image": obs.image,
        "interest": obs.interest, "price": obs.price, "was_price": obs.was_price,
        "target_price": obs.target_price, "error": obs.error,
        "rating": asdict(rating),
        "history": [[p.date, p.price] for p in points if p.date >= since],
    }


def build_report(deals, watched, statuses, history: History, today: date, settings: Settings,
                 generated: datetime) -> dict:
    threshold = settings.real_deal_threshold_percent
    deal_entries = [_entry(obs, history, today, threshold) for obs in deals if obs.price is not None]
    deal_entries.sort(key=lambda d: (LABEL_ORDER.get(d["rating"]["label"], 9),
                                     -(d["rating"]["percent_below"] or 0)))
    return {
        "generated": generated.isoformat(timespec="minutes"),
        "settings": {
            "threshold": threshold,
            "interests": settings.interests,
            "shop_sections": settings.shop_sections,
            "watch_count": len(settings.watchlist),
        },
        "sources": [asdict(s) for s in statuses],
        "deals": deal_entries,
        "watchlist": [_entry(obs, history, today, threshold) for obs in watched],
    }


def pick_alerts(report: dict) -> list[dict]:
    picked = [d for d in report["deals"] if d["rating"]["label"] == REAL]
    picked += [w for w in report["watchlist"] if w["rating"]["label"] == REAL or w["rating"]["hit_target"]]
    seen, alerts = set(), []
    for item in picked:
        if item["id"] not in seen:
            seen.add(item["id"])
            alerts.append(item)
    return alerts


def main(root=Path("."), fetch=real_fetch, pause=time.sleep, env=os.environ) -> int:
    root = Path(root)
    try:
        settings = load_settings(root / "config" / "settings.yml")
    except SettingsError as e:
        print(f"Can't run: {e}")
        return 1
    now = datetime.now(timezone.utc)
    deals, watched, statuses = collect(settings, fetch, now, pause)
    report = build_report(deals, watched, statuses, History(root / "data" / "history"),
                          now.date(), settings, now)
    site = root / "site"
    site.mkdir(exist_ok=True)
    (site / "deals.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    alerts = pick_alerts(report)
    real = sum(1 for d in report["deals"] if d["rating"]["label"] == REAL)
    print(f"{len(report['deals'])} deals checked, {real} real deals, "
          f"{len(report['watchlist'])} watched items, {len(alerts)} alerts")
    for status in statuses:
        if not status.ok:
            print(f"  problem - {status.name}: {status.message}")

    address, password = env.get("GMAIL_ADDRESS"), env.get("GMAIL_APP_PASSWORD")
    if alerts and address and password:
        try:
            emailer.send(emailer.compose(alerts, settings.site_url, address), address, password)
            print("alert email sent")
        except Exception as e:
            print(f"couldn't send the alert email ({e}). Check the Gmail app password secret.")
    elif alerts:
        print("alerts found, but email isn't set up (GMAIL_ADDRESS / GMAIL_APP_PASSWORD)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
