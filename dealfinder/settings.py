from dataclasses import dataclass, field
from pathlib import Path

import yaml


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


def load_settings(path: Path) -> Settings:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise SettingsError(f"settings.yml has a formatting mistake: {e}") from None
    if not isinstance(raw, dict):
        raise SettingsError("settings.yml should be a list of 'name: value' settings")

    interests = raw.get("interests") or {}
    if not isinstance(interests, dict):
        raise SettingsError("'interests' should be names, each with a list of search words under it")

    watchlist = []
    for number, item in enumerate(raw.get("watchlist") or [], start=1):
        if isinstance(item, str):
            item = {"url": item}
        if not isinstance(item, dict) or not item.get("url"):
            raise SettingsError(f"watchlist item #{number} needs a 'url'")
        target = item.get("target_price")
        watchlist.append(WatchItem(
            url=str(item["url"]).strip(),
            target_price=_number(target, f"watchlist item #{number} target_price") if target is not None else None,
            name=item.get("name"),
        ))

    return Settings(
        real_deal_threshold_percent=_number(raw.get("real_deal_threshold_percent", 15), "real_deal_threshold_percent"),
        site_url=str(raw.get("site_url") or ""),
        interests={str(name): _words(words) for name, words in interests.items()},
        shop_sections=[str(url).strip() for url in raw.get("shop_sections") or []],
        watchlist=watchlist,
    )
