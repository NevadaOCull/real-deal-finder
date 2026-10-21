from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

import yaml

from .prices import to_number

KNOWN_SETTINGS = ["real_deal_threshold_percent", "site_url", "interests", "shop_sections", "watchlist"]


class SettingsError(Exception):
    """settings.yml has a mistake. The message is written for the owner."""


@dataclass
class WatchItem:
    url: str
    target_price: float | None = None
    name: str | None = None


@dataclass
class Settings:
    real_deal_threshold_percent: float = 15
    site_url: str = ""
    interests: dict[str, list[str]] = field(default_factory=dict)
    shop_sections: list[str] = field(default_factory=list)
    watchlist: list[WatchItem] = field(default_factory=list)


def _number(value, label):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise SettingsError(f"{label} should be a number, but it says '{value}'") from None


def _words(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(word) for word in value]


def _price(value, label):
    price = to_number(value)
    if price is None:
        raise SettingsError(f"{label} should be a price like 150, but it says '{value}'")
    return price


def _list(value, label):
    """A list setting; a single entry written without a dash is accepted too."""
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    if not isinstance(value, list):
        raise SettingsError(f"'{label}' should be a list, with each entry on its own line starting with '- '")
    return value


def _check_names(raw):
    for key in raw:
        if key not in KNOWN_SETTINGS:
            close = get_close_matches(str(key), KNOWN_SETTINGS, n=1)
            hint = f" Did you mean '{close[0]}'?" if close else ""
            raise SettingsError(f"settings.yml has a setting called '{key}' that isn't used.{hint}")


def load_settings(path: Path) -> Settings:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except OSError:
        raise SettingsError(f"can't find the settings file at {path}") from None
    except yaml.YAMLError as e:
        raise SettingsError(f"settings.yml has a formatting mistake: {e}") from None
    if not isinstance(raw, dict):
        raise SettingsError("settings.yml should be a list of 'name: value' settings")
    _check_names(raw)

    interests = raw.get("interests") or {}
    if not isinstance(interests, dict):
        raise SettingsError("'interests' should be names, each with a list of search words under it")

    watchlist = []
    for number, item in enumerate(_list(raw.get("watchlist"), "watchlist"), start=1):
        if isinstance(item, str):
            item = {"url": item}
        if not isinstance(item, dict) or not item.get("url"):
            raise SettingsError(f"watchlist item #{number} needs a 'url'")
        target = item.get("target_price")
        watchlist.append(WatchItem(
            url=str(item["url"]).strip(),
            target_price=_price(target, f"watchlist item #{number} target_price") if target is not None else None,
            name=item.get("name"),
        ))

    threshold = _number(raw.get("real_deal_threshold_percent", 15), "real_deal_threshold_percent")
    if not 1 <= threshold <= 90:
        raise SettingsError(f"real_deal_threshold_percent should be between 1 and 90, but it says {threshold:g}")

    return Settings(
        real_deal_threshold_percent=threshold,
        site_url=str(raw.get("site_url") or ""),
        interests={str(name): _words(words) for name, words in interests.items()},
        shop_sections=[str(url).strip() for url in _list(raw.get("shop_sections"), "shop_sections")],
        watchlist=watchlist,
    )
