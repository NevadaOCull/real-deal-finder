import json
from datetime import date

from dealfinder.history import History, PricePoint
from dealfinder.models import Observation

DAY1 = date(2026, 10, 20)
DAY2 = date(2026, 10, 21)


def obs(price, item_id="shop-1"):
    return Observation(id=item_id, title="Coilovers", store="DriftHQ",
                       url="https://drifthq.com/products/x", price=price, source="shop")


def test_load_missing_is_empty(tmp_path):
    assert History(tmp_path).load("nothing") == []


def test_first_record_creates_file(tmp_path):
    points = History(tmp_path).record(obs(100.0), DAY1)
    assert points == [PricePoint("2026-10-20", 100.0)]
    saved = json.loads((tmp_path / "shop-1.json").read_text(encoding="utf-8"))
    assert saved["title"] == "Coilovers"
    assert saved["points"] == [{"date": "2026-10-20", "price": 100.0}]


def test_records_accumulate_across_days(tmp_path):
    h = History(tmp_path)
    h.record(obs(100.0), DAY1)
    assert h.record(obs(90.0), DAY2) == [PricePoint("2026-10-20", 100.0), PricePoint("2026-10-21", 90.0)]


def test_same_day_keeps_lower_price(tmp_path):
    h = History(tmp_path)
    h.record(obs(100.0), DAY2)
    assert h.record(obs(95.0), DAY2) == [PricePoint("2026-10-21", 95.0)]
    assert h.record(obs(99.0), DAY2) == [PricePoint("2026-10-21", 95.0)]


def test_same_day_failed_check_does_not_erase_price(tmp_path):
    h = History(tmp_path)
    h.record(obs(100.0), DAY2)
    assert h.record(obs(None), DAY2) == [PricePoint("2026-10-21", 100.0)]


def test_failed_check_records_no_data(tmp_path):
    assert History(tmp_path).record(obs(None), DAY2) == [PricePoint("2026-10-21", None)]


def test_odd_ids_stay_inside_folder(tmp_path):
    h = History(tmp_path / "hist")
    h.record(obs(5.0, item_id="shopify-drifthq.com-1/../../x"), DAY1)
    assert len(list((tmp_path / "hist").iterdir())) == 1
    assert h.load("shopify-drifthq.com-1/../../x") == [PricePoint("2026-10-20", 5.0)]
