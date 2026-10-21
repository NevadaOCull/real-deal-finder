from pathlib import Path

import pytest

from dealfinder.settings import SettingsError, load_settings

ROOT = Path(__file__).parent.parent


def write(tmp_path, text):
    path = tmp_path / "settings.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_full_settings(tmp_path):
    s = load_settings(write(tmp_path, """
real_deal_threshold_percent: 20
site_url: https://example.github.io/real-deal-finder/
interests:
  Drift parts: [coilovers, bucket seat]
shop_sections:
  - https://drifthq.com/collections/garage-sale
watchlist:
  - url: https://www.amazon.com/dp/B00KCF7JL6
    target_price: 150
    name: Citizen watch
  - https://drifthq.com/products/some-part
"""))
    assert s.real_deal_threshold_percent == 20
    assert s.site_url == "https://example.github.io/real-deal-finder/"
    assert s.interests == {"Drift parts": ["coilovers", "bucket seat"]}
    assert s.shop_sections == ["https://drifthq.com/collections/garage-sale"]
    assert s.watchlist[0].url == "https://www.amazon.com/dp/B00KCF7JL6"
    assert s.watchlist[0].target_price == 150
    assert s.watchlist[0].name == "Citizen watch"
    assert s.watchlist[1].url == "https://drifthq.com/products/some-part"
    assert s.watchlist[1].target_price is None


def test_empty_file_uses_defaults(tmp_path):
    s = load_settings(write(tmp_path, ""))
    assert s.real_deal_threshold_percent == 15
    assert s.interests == {}
    assert s.shop_sections == []
    assert s.watchlist == []


def test_interest_with_no_words_is_empty_list(tmp_path):
    s = load_settings(write(tmp_path, "interests:\n  Tools:\n"))
    assert s.interests == {"Tools": []}


def test_single_word_interest_is_allowed(tmp_path):
    s = load_settings(write(tmp_path, "interests:\n  Tools: drill\n"))
    assert s.interests == {"Tools": ["drill"]}


def test_bad_yaml_gives_plain_message(tmp_path):
    with pytest.raises(SettingsError, match="formatting mistake"):
        load_settings(write(tmp_path, "interests: [unclosed"))


def test_watch_item_without_url(tmp_path):
    with pytest.raises(SettingsError, match="watchlist item #1 needs a 'url'"):
        load_settings(write(tmp_path, "watchlist:\n  - target_price: 10\n"))


def test_target_price_not_a_number(tmp_path):
    with pytest.raises(SettingsError, match="target_price"):
        load_settings(write(tmp_path, "watchlist:\n  - url: https://x.com/p\n    target_price: cheap\n"))


def test_threshold_not_a_number(tmp_path):
    with pytest.raises(SettingsError, match="real_deal_threshold_percent"):
        load_settings(write(tmp_path, "real_deal_threshold_percent: lots\n"))


def test_real_settings_file_loads():
    s = load_settings(ROOT / "config" / "settings.yml")
    assert s.real_deal_threshold_percent == 15
    assert "Drift parts" in s.interests
