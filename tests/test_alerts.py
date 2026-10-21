import json
from datetime import date

from dealfinder.alerts import load_sent, new_alerts, remember, save_sent

TODAY = date(2026, 10, 21)


def alert(item_id, price):
    return {"id": item_id, "price": price}


def test_never_sent_is_new():
    assert new_alerts([alert("a", 10.0)], {}, TODAY) == [alert("a", 10.0)]


def test_same_or_higher_price_is_not_new():
    sent = {"a": {"price": 10.0, "date": "2026-10-20"}}
    assert new_alerts([alert("a", 10.0), alert("a", 12.0)], sent, TODAY) == []


def test_lower_price_is_new_again():
    sent = {"a": {"price": 10.0, "date": "2026-10-20"}}
    assert new_alerts([alert("a", 9.5)], sent, TODAY) == [alert("a", 9.5)]


def test_sent_over_30_days_ago_is_new_again():
    sent = {"a": {"price": 10.0, "date": "2026-09-20"}, "b": {"price": 10.0, "date": "2026-09-21"}}
    assert new_alerts([alert("a", 10.0), alert("b", 10.0)], sent, TODAY) == [alert("a", 10.0)]


def test_remember_records_and_drops_old_entries():
    sent = {"old": {"price": 5.0, "date": "2026-07-01"}, "kept": {"price": 7.0, "date": "2026-10-01"}}
    updated = remember([alert("a", 9.5)], sent, TODAY)
    assert updated == {"kept": {"price": 7.0, "date": "2026-10-01"},
                       "a": {"price": 9.5, "date": "2026-10-21"}}


def test_load_and_save(tmp_path):
    path = tmp_path / "data" / "alerted.json"
    assert load_sent(path) == {}
    save_sent(path, {"a": {"price": 9.5, "date": "2026-10-21"}})
    assert load_sent(path) == {"a": {"price": 9.5, "date": "2026-10-21"}}
    path.write_text("not json", encoding="utf-8")
    assert load_sent(path) == {}
