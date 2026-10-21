import json
from datetime import date, datetime, timezone

from dealfinder import run as run_module
from dealfinder.fetch import SourceError
from dealfinder.history import History, PricePoint
from dealfinder.models import Observation, OutsideStats
from dealfinder.rating import MEH, NOT_ENOUGH, REAL, UNAVAILABLE
from dealfinder.settings import Settings, ShopSection, WatchItem
from dealfinder.stores import page_id
from helpers import fake_fetch, fixture

NOW = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)
TODAY = NOW.date()


def no_pause(seconds):
    pass


def pages():
    return {
        "slickdeals.net": fixture("slickdeals_frontpage.xml"),
        "camelcamelcamel.com/product/B00KCF7JL6": fixture("camel_B00KCF7JL6.html"),
        "drifthq.com": fixture("shopify_drifthq_garage.json"),
    }


def test_collect_amazon_deal_gets_outside_history():
    settings = Settings(interests={"Watches": ["eco-drive"]})
    deals, watched, statuses = run_module.collect(settings, fake_fetch(pages()), NOW, no_pause)
    assert len(deals) == 1
    deal = deals[0]
    assert (deal.id, deal.price, deal.interest) == ("amazon-B00KCF7JL6", 184.65, "Watches")
    assert (deal.outside.normal, deal.outside.lowest) == (214.71, 51.99)
    assert watched == []
    assert statuses[0].name == "Slickdeals" and statuses[0].ok


def test_collect_dedupes_across_searches_and_looks_up_once():
    settings = Settings(interests={"Watches": ["eco-drive"], "Gifts": ["citizen"]})
    fetch = fake_fetch(pages())
    deals, _, _ = run_module.collect(settings, fetch, NOW, no_pause)
    assert [d.interest for d in deals] == ["Watches"]
    assert sum("camelcamelcamel" in url for url in fetch.calls) == 1


def test_camel_failure_still_keeps_deal():
    p = pages()
    p["camelcamelcamel.com/product/B00KCF7JL6"] = SourceError("blocked")
    deals, _, _ = run_module.collect(Settings(interests={"Watches": ["eco-drive"]}), fake_fetch(p), NOW, no_pause)
    assert deals[0].outside is None and deals[0].price == 184.65


def test_shop_sections_collected():
    settings = Settings(shop_sections=[ShopSection("https://drifthq.com/collections/garage-sale")])
    deals, _, statuses = run_module.collect(settings, fake_fetch(pages()), NOW, no_pause)
    assert len(deals) == 5 and all(d.interest == "Shop sales" for d in deals)
    assert ("DriftHQ sale section", True) in [(s.name, s.ok) for s in statuses]


def test_shop_section_only_words_filter_items():
    settings = Settings(shop_sections=[ShopSection("https://drifthq.com/collections/garage-sale", ["turbosmart", "leo grande"])])
    deals, _, _ = run_module.collect(settings, fake_fetch(pages()), NOW, no_pause)
    assert sorted(d.title.split(" - ")[1] for d in deals) == ["Leo Grande Racing", "Turbosmart Gen4 CompGate40 14psi"]


def test_one_source_crashing_does_not_stop_others(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("parser bug")
    monkeypatch.setattr(run_module.slickdeals, "search", broken)
    settings = Settings(interests={"Watches": ["eco-drive"]},
                        shop_sections=[ShopSection("https://drifthq.com/collections/garage-sale")])
    deals, _, statuses = run_module.collect(settings, fake_fetch(pages()), NOW, no_pause)
    assert len(deals) == 5
    slick = statuses[0]
    assert slick.name == "Slickdeals" and not slick.ok and "parser bug" in slick.message


def test_everything_failing_still_builds_page_and_keeps_history(tmp_path):
    url = "https://www.homedepot.com/p/drill/1"
    history = History(tmp_path)
    history.record(Observation(id=page_id(url), title="Drill", store="Home Depot", url=url,
                               price=99.0, source="page"), date(2026, 10, 20))
    settings = Settings(interests={"Drift parts": ["coilovers"]},
                        shop_sections=[ShopSection("https://drifthq.com/collections/garage-sale")],
                        watchlist=[WatchItem(url, 90)])
    deals, watched, statuses = run_module.collect(settings, fake_fetch({}), NOW, no_pause)
    report = run_module.build_report(deals, watched, statuses, history, TODAY, settings, NOW)
    assert report["deals"] == []
    assert [s["ok"] for s in report["sources"]] == [False, False, False]
    assert report["watchlist"][0]["rating"]["label"] == UNAVAILABLE
    assert run_module.pick_alerts(report) == []
    assert history.load(page_id(url)) == [PricePoint("2026-10-20", 99.0), PricePoint("2026-10-21", None)]


def obs(item_id, price, normal=None):
    return Observation(id=item_id, title=item_id, store="Amazon", url=f"https://x.com/{item_id}", price=price,
                       source="test", outside=OutsideStats(normal, normal / 2) if normal else None)


def test_build_report_sorts_and_picks_alerts(tmp_path):
    deals = [obs("a", 80, 100), obs("b", 70, 100), obs("c", 99, 100), obs("d", 50), obs("e", None)]
    watched = [Observation(id="w", title="Seat", store="DriftHQ", url="https://drifthq.com/products/s",
                           price=95.0, source="shop", target_price=96, outside=OutsideStats(100, 90))]
    report = run_module.build_report(deals, watched, [], History(tmp_path), TODAY, Settings(), NOW)
    assert [d["id"] for d in report["deals"]] == ["b", "a", "c", "d"]
    assert [d["rating"]["label"] for d in report["deals"]] == [REAL, REAL, MEH, NOT_ENOUGH]
    assert report["deals"][0]["history"] == [["2026-10-21", 70]]
    assert report["generated"] == "2026-10-21T20:00+00:00"
    assert [a["id"] for a in run_module.pick_alerts(report)] == ["b", "a", "w"]


def write_settings(root, threshold):
    (root / "config").mkdir()
    (root / "config" / "settings.yml").write_text(
        f"real_deal_threshold_percent: {threshold}\ninterests:\n  Watches: [eco-drive]\n", encoding="utf-8")


def test_main_writes_page_data_without_email(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_module, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: NOW)}))
    write_settings(tmp_path, 15)
    assert run_module.main(tmp_path, fake_fetch(pages()), no_pause, env={}) == 0
    report = json.loads((tmp_path / "site" / "deals.json").read_text(encoding="utf-8"))
    assert [d["rating"]["label"] for d in report["deals"]] == [MEH]  # 14.0% below normal, threshold 15
    assert (tmp_path / "data" / "history" / "amazon-B00KCF7JL6.json").exists()
    assert "1 deals checked" in capsys.readouterr().out


def test_main_emails_real_deals(tmp_path, monkeypatch):
    monkeypatch.setattr(run_module, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: NOW)}))
    sent = []
    monkeypatch.setattr(run_module.emailer, "send", lambda msg, address, password: sent.append(msg["Subject"]))
    write_settings(tmp_path, 10)
    env = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "pw"}
    assert run_module.main(tmp_path, fake_fetch(pages()), no_pause, env=env) == 0
    assert sent == ["1 deal alert today"]


def test_main_settings_mistake_returns_1(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yml").write_text("interests: [unclosed", encoding="utf-8")
    assert run_module.main(tmp_path, fake_fetch({}), no_pause, env={}) == 1
    assert "formatting mistake" in capsys.readouterr().out


def test_email_failure_does_not_fail_the_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_module, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: NOW)}))

    def broken_send(msg, address, password):
        raise OSError("535 Username and Password not accepted")
    monkeypatch.setattr(run_module.emailer, "send", broken_send)
    write_settings(tmp_path, 10)
    env = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "old"}
    assert run_module.main(tmp_path, fake_fetch(pages()), no_pause, env=env) == 0
    assert "couldn't send the alert email" in capsys.readouterr().out
    assert (tmp_path / "data" / "history" / "amazon-B00KCF7JL6.json").exists()


def test_main_only_emails_new_deals(tmp_path, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(run_module.emailer, "send", lambda msg, address, password: sent.append(msg["Subject"]))
    write_settings(tmp_path, 10)
    env = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "pw"}

    def run_on(day):
        when = datetime(2026, 10, day, 11, 0, tzinfo=timezone.utc)
        monkeypatch.setattr(run_module, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: when)}))
        assert run_module.main(tmp_path, fake_fetch(pages()), no_pause, env=env) == 0

    run_on(21)
    run_on(22)  # same deal, same price: no second email
    assert sent == ["1 deal alert today"]
    assert "1 alerts (0 new)" in capsys.readouterr().out
    assert json.loads((tmp_path / "data" / "alerted.json").read_text(encoding="utf-8"))["amazon-B00KCF7JL6"] == {
        "price": 184.65, "date": "2026-10-21"}


def test_failed_email_is_retried_next_day(tmp_path, monkeypatch):
    attempts = []

    def flaky_send(msg, address, password):
        attempts.append(msg["Subject"])
        if len(attempts) == 1:
            raise OSError("network down")
    monkeypatch.setattr(run_module.emailer, "send", flaky_send)
    write_settings(tmp_path, 10)
    env = {"GMAIL_ADDRESS": "me@gmail.com", "GMAIL_APP_PASSWORD": "pw"}
    for day in (21, 22):
        when = datetime(2026, 10, day, 11, 0, tzinfo=timezone.utc)
        monkeypatch.setattr(run_module, "datetime", type("D", (), {"now": staticmethod(lambda tz=None: when)}))
        run_module.main(tmp_path, fake_fetch(pages()), no_pause, env=env)
    assert attempts == ["1 deal alert today", "1 deal alert today"]
