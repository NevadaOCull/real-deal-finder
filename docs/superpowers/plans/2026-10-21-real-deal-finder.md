# Real Deal Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily price checker that finds deals genuinely below an item's normal price, publishes them to a phone-friendly web page, and emails the owner when something is worth buying.

**Architecture:** A Python package (`dealfinder/`) run once a day by GitHub Actions. Source modules (Slickdeals RSS, CamelCamelCamel, Shopify JSON, generic product pages) turn web data into `Observation`s; `history.py` stores one price per item per day as JSON files in the repo; `rating.py` labels each price; `run.py` writes `site/deals.json`, which a static HTML/JS page in `site/` renders. GitHub Pages serves `site/`.

**Tech Stack:** Python 3.12 (3.13 locally), `requests`, `PyYAML`, `pytest`; stdlib `xml.etree`, `smtplib`; vanilla HTML/CSS/JS; GitHub Actions + GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-21-real-deal-finder-design.md`

## Global Constraints

- $0 running cost — no paid APIs, no paid services.
- Never record or show a guessed price: a failed check records `null` for that day and shows "Couldn't check today".
- One source failing must never stop the others; failures are shown on the page.
- Amazon is never fetched directly — Amazon data comes from CamelCamelCamel and Slickdeals.
- Owner-facing text (page, email, settings comments, README) is plain English for a non-programmer. Never use the words "engineer" or "engineering".
- Everything shown on the page comes from other websites: insert it with `textContent`, never `innerHTML`; only link `http(s)` URLs.
- Rating constants (from spec): default threshold 15%; normal price = median of last 90 days; 14 days minimum history; new low needs 30 days; "was" price is fake if it held on fewer than 30% of days.
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Run all commands from the repo root: `C:\Users\nevad\OneDrive\Email attachments\Documents\real-deal-finder`. Python is `python` (3.13).

**Decisions made while planning (differences from the spec, all small):**
- Slickdeals has no working per-category feed; its keyword search feed works (verified). So "categories" become **interests**, each a list of search words. Search results are kept only if the title contains every word of the term, the title has a price, and the post is ≤14 days old (search feeds return years-old posts).
- CamelCamelCamel has no per-product RSS anymore; its product page has a price table (lowest ever / highest ever / current / average) which we read. For Amazon, "normal price" = CamelCamelCamel's average, "lowest" = its lowest ever.
- Added a fifth label, **"No deal"**, for an item at its normal price with no sale claim (calling that "Fake sale" would be wrong for watchlist items). Added **"Couldn't check today"** for failed checks.
- Alert email goes to the `GMAIL_ADDRESS` secret, not a settings-file field, so the email address never sits in a possibly-public file.
- Daily run is at 11:00 UTC (6 AM Central daylight time). Changeable in the workflow file.

## Review Focus

1. **Price text in odd formats** — `$1,299.99`, ranges like `$173.59–$369.99`, `$2499.99`, no price at all ("Sweepstakes") must parse to 1299.99 / 173.59 / 2499.99 / None, never a wrong number. (Task 4 `test_parse_price_formats`.)
2. **Same item seen twice in one day** (in two searches, or in both deals and watchlist) must leave exactly one history point for that day, the lower price, and a later failed check must not erase an earlier good price. (Task 2 `test_same_day_*`.)
3. **A store page that answers "200 OK" but is really a bot-check page** must be "Couldn't check today", not a price of $0 or a crash. (Task 4 `test_bot_check_page_has_no_price`, Task 8 `test_blocked_item_is_reported_not_guessed`.)
4. **Owner typos in `settings.yml`** (broken YAML, a watch item with no url, `target_price: cheap`, a single word instead of a list) must give a plain-English message naming the problem, not a Python traceback. (Task 1 tests.)
5. **Every source failing on the same day** (internet trouble on GitHub's side) must still produce a page listing what failed, send no email, and keep all existing price history. (Task 10 `test_everything_failing_still_builds_page_and_keeps_history`.)

---

## File Structure

```
real-deal-finder/
├── .github/workflows/daily.yml   # Task 12: daily run + publish page
├── .gitignore                    # Task 1
├── README.md                     # Task 12: owner setup + how to change settings
├── pyproject.toml                # Task 1: pytest config
├── requirements.txt              # Task 1
├── config/settings.yml           # Task 1: owner's settings
├── data/history/                 # created at runtime: one JSON file per item
├── dealfinder/
│   ├── __init__.py               # Task 1
│   ├── models.py                 # Task 1: Observation, OutsideStats
│   ├── settings.py               # Task 1: load + validate settings.yml
│   ├── history.py                # Task 2: per-item daily price history
│   ├── rating.py                 # Task 3: the real-deal test
│   ├── fetch.py                  # Task 4: HTTP + SourceError
│   ├── prices.py                 # Task 4: parse "$1,299.99" etc.
│   ├── stores.py                 # Task 4: store names, item ids
│   ├── pricepage.py              # Task 4: price from any product page
│   ├── slickdeals.py             # Task 5
│   ├── camel.py                  # Task 6: CamelCamelCamel (Amazon history)
│   ├── shopify.py                # Task 7: DriftHQ, FDF Raceshop
│   ├── watchlist.py              # Task 8: route a watched URL to the right reader
│   ├── emailer.py                # Task 9
│   └── run.py                    # Task 10: daily orchestration (python -m dealfinder.run)
├── site/                         # Task 11: index.html, app.js, style.css (+ generated deals.json)
└── tests/
    ├── fixtures/                 # already committed: real responses captured 2026-10-21
    ├── helpers.py                # Task 4: fixture() + fake_fetch()
    └── test_*.py
```

Fixtures already in `tests/fixtures/` (captured live 2026-10-21):
`slickdeals_frontpage.xml` (25 items; item 1 = Citizen watch, `$184.65`, store slug `amazon`, ASIN `B00KCF7JL6`, posted 2026-10-21), `slickdeals_coilovers.xml` (5 items, newest posted 2026-05-28: "20% OFF Coilovers Kits at Flashark + $173.59–$369.99 Shipped"), `camel_B00KCF7JL6.html` (Amazon row: lowest $51.99, highest $308.48, current $184.63, average $214.71), `shopify_drifthq_garage.json` (5 products), `shopify_fdf_product.json` (hoodie, $47.27, no compare price), `bigcommerce_synergy.html` ($7.50), `bigcommerce_driftamerican.html` ($135).

---

### Task 1: Project skeleton, models, settings

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `requirements.txt`, `dealfinder/__init__.py`, `dealfinder/models.py`, `dealfinder/settings.py`, `config/settings.yml`
- Test: `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `dealfinder.models.OutsideStats(normal: float, lowest: float)`
  - `dealfinder.models.Observation(id: str, title: str, store: str, url: str, price: float | None, source: str, was_price: float | None = None, outside: OutsideStats | None = None, image: str | None = None, interest: str | None = None, target_price: float | None = None, error: str | None = None)` — mutable dataclass
  - `dealfinder.settings.SettingsError(Exception)`
  - `dealfinder.settings.WatchItem(url: str, target_price: float | None = None, name: str | None = None)`
  - `dealfinder.settings.Settings(real_deal_threshold_percent: float = 15, site_url: str = "", interests: dict[str, list[str]], shop_sections: list[str], watchlist: list[WatchItem])`
  - `dealfinder.settings.load_settings(path: Path) -> Settings`

- [ ] **Step 1: Create project files**

`.gitignore`:
```
__pycache__/
.pytest_cache/
*.pyc
site/deals.json
```

`requirements.txt`:
```
requests==2.32.3
PyYAML==6.0.2
pytest==8.3.3
```

`pyproject.toml`:
```toml
[project]
name = "real-deal-finder"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`dealfinder/__init__.py`:
```python
"""Real Deal Finder: finds prices that are actually below an item's normal price."""
```

`dealfinder/models.py`:
```python
from dataclasses import dataclass


@dataclass
class OutsideStats:
    """Price history from another site (CamelCamelCamel), so we don't have to wait weeks."""
    normal: float
    lowest: float


@dataclass
class Observation:
    """One price seen today for one item."""
    id: str
    title: str
    store: str
    url: str
    price: float | None
    source: str
    was_price: float | None = None
    outside: OutsideStats | None = None
    image: str | None = None
    interest: str | None = None
    target_price: float | None = None
    error: str | None = None
```

Run: `pip install -r requirements.txt`
Expected: installs (or "Requirement already satisfied").

- [ ] **Step 2: Write the failing tests**

`tests/test_settings.py`:
```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.settings'`

- [ ] **Step 4: Implement settings and the owner's settings file**

`dealfinder/settings.py`:
```python
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
```

`config/settings.yml`:
```yaml
# Real Deal Finder settings
# Lines starting with # are notes and are ignored.
# After you change this file, the next daily check uses the new settings.

# How far below its normal price something must be to count as a "Real deal".
real_deal_threshold_percent: 15

# The web address of your deals page (filled in once the page is turned on).
site_url: ""

# What you're interested in. Each name has a list of search words.
# A deal shows up when its title contains every word of one of the searches.
# These are starter words - change them to match your car and your tools.
interests:
  Drift parts:
    - coilovers
    - bucket seat
    - angle kit
    - hydraulic handbrake
    - mustang
  Tools:
    - milwaukee
    - dewalt
    - impact driver
    - socket set

# Store sale sections to watch (Shopify stores like DriftHQ and FDF Raceshop).
shop_sections:
  - https://drifthq.com/collections/garage-sale

# Specific items to watch. Paste the product link.
# target_price is optional: you get an email when the price drops to it or below.
# Example:
#   - url: https://www.amazon.com/dp/B00KCF7JL6
#     target_price: 150
watchlist: []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_settings.py -v`
Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add .gitignore pyproject.toml requirements.txt dealfinder config tests/test_settings.py tests/fixtures
git commit -m "Add project skeleton, models and settings loader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Price history

**Files:**
- Create: `dealfinder/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `Observation` (Task 1)
- Produces:
  - `dealfinder.history.PricePoint(date: str, price: float | None)` — `date` is `YYYY-MM-DD`
  - `dealfinder.history.History(folder: Path)` with `.load(item_id: str) -> list[PricePoint]` and `.record(obs: Observation, today: date) -> list[PricePoint]` (returns all points, oldest first, including today's)
  - File format `data/history/<safe id>.json`: `{"id", "title", "store", "url", "points": [{"date", "price"}]}`

- [ ] **Step 1: Write the failing tests**

`tests/test_history.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.history'`

- [ ] **Step 3: Implement**

`dealfinder/history.py`:
```python
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .models import Observation


@dataclass
class PricePoint:
    date: str  # YYYY-MM-DD
    price: float | None  # None = couldn't check that day


class History:
    """One JSON file per item holding one price per day."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def _path(self, item_id: str) -> Path:
        return self.folder / (re.sub(r"[^A-Za-z0-9_.-]", "_", item_id) + ".json")

    def load(self, item_id: str) -> list[PricePoint]:
        path = self._path(item_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [PricePoint(p["date"], p["price"]) for p in data.get("points", [])]

    def record(self, obs: Observation, today: date) -> list[PricePoint]:
        points = self.load(obs.id)
        day = today.isoformat()
        if points and points[-1].date == day:
            old = points[-1].price
            if obs.price is not None and (old is None or obs.price < old):
                points[-1] = PricePoint(day, obs.price)
        else:
            points.append(PricePoint(day, obs.price))
        self.folder.mkdir(parents=True, exist_ok=True)
        self._path(obs.id).write_text(json.dumps({
            "id": obs.id,
            "title": obs.title,
            "store": obs.store,
            "url": obs.url,
            "points": [{"date": p.date, "price": p.price} for p in points],
        }, indent=1), encoding="utf-8")
        return points
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_history.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/history.py tests/test_history.py
git commit -m "Add per-item daily price history

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The real-deal test

**Files:**
- Create: `dealfinder/rating.py`
- Test: `tests/test_rating.py`

**Interfaces:**
- Consumes: `PricePoint` (Task 2), `OutsideStats` (Task 1)
- Produces:
  - Label constants: `REAL = "real-deal"`, `MEH = "meh"`, `FAKE = "fake-sale"`, `NO_DEAL = "no-deal"`, `NOT_ENOUGH = "not-enough-history"`, `UNAVAILABLE = "unavailable"`
  - `dealfinder.rating.Rating(label: str, normal: float | None, lowest: float | None, percent_below: float | None, history_days: int, hit_target: bool = False)`
  - `dealfinder.rating.rate(price: float | None, points: list[PricePoint], today: date, threshold_percent: float, was_price: float | None = None, outside: OutsideStats | None = None, target_price: float | None = None) -> Rating` — ignores any point dated `today` or later.

Rules (in order): no price → UNAVAILABLE. Normal = `outside.normal` if given, else median of prices in the 90 days before today if there are ≥14 of them, else NOT_ENOUGH. `percent_below` = (normal − price) / normal × 100, rounded to 1 place. Lowest before today = min of all earlier prices (and `outside.lowest`). REAL if percent_below ≥ threshold, or price < lowest-before and (outside given or ≥30 earlier price days). FAKE if a `was_price` above the price is claimed, ≥14 days history, and prices ≥ 98% of `was_price` occurred on < 30% of the 90-day days. MEH if percent_below ≥ 1. FAKE if a higher `was_price` is claimed. Otherwise NO_DEAL.

- [ ] **Step 1: Write the failing tests**

`tests/test_rating.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rating.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.rating'`

- [ ] **Step 3: Implement**

`dealfinder/rating.py`:
```python
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
    new_low = long_enough and lowest_before is not None and price < lowest_before
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rating.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/rating.py tests/test_rating.py
git commit -m "Add the real-deal rating test

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Fetching, price parsing, store names, product pages

**Files:**
- Create: `dealfinder/fetch.py`, `dealfinder/prices.py`, `dealfinder/stores.py`, `dealfinder/pricepage.py`, `tests/helpers.py`
- Test: `tests/test_fetch.py`, `tests/test_prices.py`, `tests/test_stores.py`, `tests/test_pricepage.py`

**Interfaces:**
- Consumes: `Observation` (Task 1)
- Produces:
  - `dealfinder.fetch.SourceError(Exception)` — message is owner-readable
  - `dealfinder.fetch.fetch(url: str, timeout: float = 20) -> str` — raises `SourceError` on network error or non-200
  - `dealfinder.prices.parse_price(text: str | None) -> float | None` — first `$` amount in text
  - `dealfinder.prices.to_number(value) -> float | None` — number or numeric string, positive only
  - `dealfinder.stores.host_of(url) -> str` (lowercase, no `www.`), `store_name(url) -> str`, `store_from_slug(slug: str | None) -> str`, `page_id(url) -> str` (`"page-" + 12 hex`)
  - `dealfinder.pricepage.PageInfo(title: str | None, price: float | None, image: str | None)`
  - `dealfinder.pricepage.parse_product_page(html: str) -> PageInfo`
  - `dealfinder.pricepage.page_observation(url: str, fetch) -> Observation` — raises `SourceError` if no price
  - `tests/helpers.py`: `fixture(name) -> str`, `fake_fetch(pages: dict[str, str | Exception])` — returns a callable matching the first key that is a substring of the URL, recording calls in `.calls`
- Every source module takes `fetch` as a parameter (a `Callable[[str], str]`) so tests pass `fake_fetch`.

- [ ] **Step 1: Write the test helpers and failing tests**

`tests/helpers.py`:
```python
from pathlib import Path

from dealfinder.fetch import SourceError

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def fake_fetch(pages):
    """A stand-in for dealfinder.fetch.fetch. Keys are URL substrings; values are bodies or exceptions."""
    calls = []

    def fetch(url):
        calls.append(url)
        for key, body in pages.items():
            if key in url:
                if isinstance(body, Exception):
                    raise body
                return body
        raise SourceError(f"no fake page for {url}")

    fetch.calls = calls
    return fetch
```

`tests/test_prices.py`:
```python
from dealfinder.prices import parse_price, to_number


def test_parse_price_formats():
    assert parse_price("Citizen Watch $184.65 + Free S&H") == 184.65
    assert parse_price("MacBook $1,299.99") == 1299.99
    assert parse_price("Kits + $173.59–$369.99 Shipped") == 173.59
    assert parse_price("Massimo Mini 125 - $2499.99") == 2499.99
    assert parse_price("Jacket $31 + Free S&H") == 31.0
    assert parse_price("AutoZone Sweepstakes 6-27-22") is None
    assert parse_price(None) is None


def test_to_number():
    assert to_number("8.99") == 8.99
    assert to_number("1,299.00") == 1299.0
    assert to_number(7.5) == 7.5
    assert to_number(135) == 135.0
    assert to_number("") is None
    assert to_number(None) is None
    assert to_number("0.00") is None
    assert to_number(True) is None
```

`tests/test_stores.py`:
```python
from dealfinder.stores import host_of, page_id, store_from_slug, store_name


def test_store_names():
    assert store_name("https://www.homedepot.com/p/x/123") == "Home Depot"
    assert store_name("https://drifthq.com/products/x") == "DriftHQ"
    assert store_name("https://driftamerican.com/x/") == "Drift American"
    assert store_name("https://shop.example.com/x") == "shop.example.com"


def test_host_of():
    assert host_of("https://WWW.Walmart.com:443/ip/1") == "walmart.com"


def test_store_from_slug():
    assert store_from_slug("home-depot") == "Home Depot"
    assert store_from_slug("amazon") == "Amazon"
    assert store_from_slug("tractor-supply-co") == "Tractor Supply Co"
    assert store_from_slug(None) == "Unknown store"


def test_page_id_is_stable_and_ignores_query_and_slash():
    a = page_id("https://driftamerican.com/brake-lines/?utm=1")
    assert a == page_id("https://www.driftamerican.com/brake-lines")
    assert a.startswith("page-") and len(a) == 17
```

`tests/test_fetch.py`:
```python
import pytest
import requests

from dealfinder import fetch as fetch_module
from dealfinder.fetch import SourceError, fetch


class FakeResponse:
    def __init__(self, status, text="ok"):
        self.status_code = status
        self.text = text


def test_returns_text_on_200(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(200, "hello"))
    assert fetch("https://drifthq.com/x") == "hello"


def test_blocked_status_is_source_error(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(403))
    with pytest.raises(SourceError, match="homedepot.com blocked the check"):
        fetch("https://www.homedepot.com/p/1")


def test_other_status_is_source_error(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(404))
    with pytest.raises(SourceError, match="error 404"):
        fetch("https://drifthq.com/x")


def test_network_problem_is_source_error(monkeypatch):
    def boom(url, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(fetch_module.requests, "get", boom)
    with pytest.raises(SourceError, match="couldn't reach drifthq.com"):
        fetch("https://drifthq.com/x")
```

`tests/test_pricepage.py`:
```python
import pytest

from dealfinder.fetch import SourceError
from dealfinder.pricepage import page_observation, parse_product_page
from helpers import fake_fetch, fixture


def test_bigcommerce_synergy():
    info = parse_product_page(fixture("bigcommerce_synergy.html"))
    assert info.price == 7.5
    assert info.title == "2005-2014 Mustang S197 Spindle Bushings"
    assert info.image.startswith("https://cdn11.bigcommerce.com/")


def test_bigcommerce_drift_american():
    info = parse_product_page(fixture("bigcommerce_driftamerican.html"))
    assert info.price == 135
    assert info.title == "1979-2004 Mustang Extended Length Steel Braided Front Brake Lines"


def test_json_ld_offer_list_with_comma_price():
    html = """<html><head><title>Big Drill | Shop</title>
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Product",
    "name":"Big Drill","offers":[{"@type":"Offer","price":"1,299.99","priceCurrency":"USD"}]}</script>
    </head></html>"""
    info = parse_product_page(html)
    assert (info.title, info.price) == ("Big Drill | Shop", 1299.99)


def test_json_ld_graph_and_low_price():
    html = """<script type="application/ld+json">{"@graph":[{"@type":"WebPage"},
    {"@type":"Product","offers":{"@type":"AggregateOffer","lowPrice":49.5}}]}</script>"""
    assert parse_product_page(html).price == 49.5


def test_broken_json_ld_is_skipped():
    html = '<script type="application/ld+json">{oops</script><meta itemprop="price" content="12.00">'
    assert parse_product_page(html).price == 12.0


def test_bot_check_page_has_no_price():
    html = "<html><head><title>Robot or human?</title></head><body>Press and hold</body></html>"
    assert parse_product_page(html).price is None


def test_page_observation():
    url = "https://synergyracedevelopment.com/2005-2014-mustang-s197-spindle-bushings/"
    obs = page_observation(url, fake_fetch({"synergyracedevelopment.com": fixture("bigcommerce_synergy.html")}))
    assert obs.id.startswith("page-")
    assert (obs.store, obs.price, obs.url, obs.source) == ("Synergy Race Development", 7.5, url, "page")


def test_page_without_price_is_source_error():
    fetch = fake_fetch({"walmart.com": "<title>Robot or human?</title>"})
    with pytest.raises(SourceError, match="no price found on Walmart page"):
        page_observation("https://www.walmart.com/ip/1", fetch)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prices.py tests/test_stores.py tests/test_fetch.py tests/test_pricepage.py -v`
Expected: FAIL — `ModuleNotFoundError` for `dealfinder.fetch` / `dealfinder.prices` / etc.

- [ ] **Step 3: Implement**

`dealfinder/fetch.py`:
```python
from urllib.parse import urlparse

import requests

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


class SourceError(Exception):
    """A store or site couldn't be read. The message is shown to the owner."""


def fetch(url: str, timeout: float = 20) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        })
    except requests.RequestException as e:
        raise SourceError(f"couldn't reach {host} ({e.__class__.__name__})") from None
    if response.status_code in (403, 429, 503):
        raise SourceError(f"{host} blocked the check (error {response.status_code})")
    if response.status_code != 200:
        raise SourceError(f"{host} answered with error {response.status_code}")
    return response.text
```

`dealfinder/prices.py`:
```python
import re

MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def parse_price(text: str | None) -> float | None:
    """The first dollar amount in a piece of text, e.g. a deal title."""
    match = MONEY.search(text or "")
    return float(match.group(1).replace(",", "")) if match else None


def to_number(value) -> float | None:
    """A positive number from a number or numeric string; anything else is None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and (match := NUMBER.search(value)):
        number = float(match.group(0).replace(",", ""))
    else:
        return None
    return number if number > 0 else None
```

`dealfinder/stores.py`:
```python
import hashlib
from urllib.parse import urlparse

STORE_NAMES = {
    "amazon.com": "Amazon",
    "walmart.com": "Walmart",
    "homedepot.com": "Home Depot",
    "drifthq.com": "DriftHQ",
    "fdfraceshop.com": "FDF Raceshop",
    "synergyracedevelopment.com": "Synergy Race Development",
    "driftamerican.com": "Drift American",
    "enjukuracing.com": "Enjuku Racing",
}

# Slickdeals' names for stores, where title-casing the slug isn't right.
SLUG_NAMES = {
    "amazon": "Amazon",
    "walmart": "Walmart",
    "home-depot": "Home Depot",
    "best-buy": "Best Buy",
    "lowes": "Lowe's",
}


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def store_name(url: str) -> str:
    host = host_of(url)
    return STORE_NAMES.get(host, host)


def store_from_slug(slug: str | None) -> str:
    if not slug:
        return "Unknown store"
    return SLUG_NAMES.get(slug, slug.replace("-", " ").title())


def page_id(url: str) -> str:
    key = host_of(url) + urlparse(url).path.rstrip("/")
    return "page-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
```

`dealfinder/pricepage.py`:
```python
import json
import re
from dataclasses import dataclass
from html import unescape

from .fetch import SourceError
from .models import Observation
from .prices import to_number
from .stores import page_id, store_name

META_TAG = re.compile(r"<meta\b[^>]*>", re.I)
ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
PRICE_META_KEYS = ("product:price:amount", "og:price:amount", "price")


@dataclass
class PageInfo:
    title: str | None
    price: float | None
    image: str | None


def _meta(html):
    found = {}
    for tag in META_TAG.findall(html):
        attrs = {key.lower(): value for key, value in ATTR.findall(tag)}
        key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
        if key and "content" in attrs:
            found.setdefault(key.lower(), unescape(attrs["content"]).strip())
    return found


def _offer_price(node):
    if isinstance(node, list):
        for child in node:
            price = _offer_price(child)
            if price is not None:
                return price
    elif isinstance(node, dict):
        for key in ("price", "lowPrice"):
            price = to_number(node.get(key))
            if price is not None:
                return price
        return _offer_price(node.get("priceSpecification"))
    return None


def _ld_price(node):
    if isinstance(node, list):
        for child in node:
            price = _ld_price(child)
            if price is not None:
                return price
    elif isinstance(node, dict):
        if "offers" in node:
            price = _offer_price(node["offers"])
            if price is not None:
                return price
        for value in node.values():
            if isinstance(value, (dict, list)):
                price = _ld_price(value)
                if price is not None:
                    return price
    return None


def parse_product_page(html: str) -> PageInfo:
    meta = _meta(html)
    price = next((p for p in (to_number(meta.get(k)) for k in PRICE_META_KEYS) if p is not None), None)
    if price is None:
        for block in LD_JSON.findall(html):
            try:
                data = json.loads(block, strict=False)
            except ValueError:
                continue
            price = _ld_price(data)
            if price is not None:
                break
    title = meta.get("og:title")
    if not title and (match := TITLE.search(html)):
        title = unescape(match.group(1)).strip()
    return PageInfo(title=title or None, price=price, image=meta.get("og:image"))


def page_observation(url: str, fetch) -> Observation:
    info = parse_product_page(fetch(url))
    if info.price is None:
        raise SourceError(f"no price found on {store_name(url)} page (it may have blocked the check)")
    return Observation(id=page_id(url), title=info.title or url, store=store_name(url), url=url,
                       price=info.price, source="page", image=info.image)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_prices.py tests/test_stores.py tests/test_fetch.py tests/test_pricepage.py -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/fetch.py dealfinder/prices.py dealfinder/stores.py dealfinder/pricepage.py tests/helpers.py tests/test_prices.py tests/test_stores.py tests/test_fetch.py tests/test_pricepage.py
git commit -m "Add fetching, price parsing, store names and product-page reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Slickdeals search feeds

**Files:**
- Create: `dealfinder/slickdeals.py`
- Test: `tests/test_slickdeals.py`

**Interfaces:**
- Consumes: `SourceError`, `parse_price`, `store_from_slug`, `Observation`
- Produces:
  - `dealfinder.slickdeals.SlickDeal(thread_id: str, title: str, link: str, price: float | None, store_slug: str | None, asin: str | None, image: str | None, posted: datetime | None)`
  - `parse_feed(xml_text: str) -> list[SlickDeal]` — raises `SourceError` on unreadable XML
  - `search(term: str, fetch, now: datetime) -> list[SlickDeal]` — `now` is timezone-aware; keeps deals whose title contains every word of `term` (case-insensitive), has a price, and was posted within 14 days
  - `deal_observation(deal: SlickDeal) -> Observation` — id `amazon-<ASIN>` if ASIN else `sd-<thread_id>`; `source="slickdeals"`

- [ ] **Step 1: Write the failing tests**

`tests/test_slickdeals.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_slickdeals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.slickdeals'`

- [ ] **Step 3: Implement**

`dealfinder/slickdeals.py`:
```python
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from .fetch import SourceError
from .models import Observation
from .prices import parse_price
from .stores import store_from_slug

SEARCH_URL = "https://slickdeals.net/newsearch.php?q={q}&searcharea=deals&searchin=first&rss=1"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
MAX_AGE = timedelta(days=14)


@dataclass
class SlickDeal:
    thread_id: str
    title: str
    link: str
    price: float | None
    store_slug: str | None
    asin: str | None
    image: str | None
    posted: datetime | None


def _first(pattern, text):
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _posted(text):
    try:
        return parsedate_to_datetime(text) if text else None
    except (TypeError, ValueError):
        return None


def parse_feed(xml_text: str) -> list[SlickDeal]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise SourceError(f"Slickdeals sent a feed that couldn't be read ({e})") from None
    deals = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        content = item.findtext(CONTENT) or ""
        deals.append(SlickDeal(
            thread_id=_first(r"/f/(\d+)", link) or link,
            title=title,
            link=link.split("?")[0],
            price=parse_price(title),
            store_slug=_first(r'data-store-slug="([^"]+)"', content),
            asin=_first(r'data-aps-asin="([A-Z0-9]{10})"', content),
            image=_first(r'<img[^>]+src="([^"]+)"', content),
            posted=_posted(item.findtext("pubDate")),
        ))
    return deals


def _matches(term, title):
    title = title.lower()
    return all(word in title for word in term.lower().split())


def search(term: str, fetch, now: datetime) -> list[SlickDeal]:
    deals = parse_feed(fetch(SEARCH_URL.format(q=quote_plus(term))))
    return [d for d in deals
            if d.price is not None and _matches(term, d.title)
            and d.posted is not None and now - d.posted <= MAX_AGE]


def deal_observation(deal: SlickDeal) -> Observation:
    item_id = f"amazon-{deal.asin}" if deal.asin else f"sd-{deal.thread_id}"
    return Observation(id=item_id, title=deal.title, store=store_from_slug(deal.store_slug),
                       url=deal.link, price=deal.price, source="slickdeals", image=deal.image)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_slickdeals.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/slickdeals.py tests/test_slickdeals.py
git commit -m "Add Slickdeals search feed reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: CamelCamelCamel (Amazon price history)

**Files:**
- Create: `dealfinder/camel.py`
- Test: `tests/test_camel.py`

**Interfaces:**
- Consumes: `SourceError`, `Observation`, `OutsideStats`, `parse_product_page`, `to_number`
- Produces:
  - `dealfinder.camel.CamelStats(title: str | None, current: float, lowest: float, average: float)`
  - `asin_from_url(url: str) -> str | None`
  - `parse_camel_page(html: str) -> CamelStats` — uses the "Amazon" row, falls back to "3rd Party New"; raises `SourceError` if neither row is readable
  - `amazon_observation(asin: str, fetch) -> Observation` — id `amazon-<ASIN>`, url `https://www.amazon.com/dp/<ASIN>`, store `Amazon`, price = current, `outside=OutsideStats(normal=average, lowest=lowest)`, `source="camelcamelcamel"`

- [ ] **Step 1: Write the failing tests**

`tests/test_camel.py`:
```python
import pytest

from dealfinder.camel import amazon_observation, asin_from_url, parse_camel_page
from dealfinder.fetch import SourceError
from helpers import fake_fetch, fixture


def test_asin_from_url():
    assert asin_from_url("https://www.amazon.com/Citizen-Eco-Drive/dp/B00KCF7JL6/ref=sr_1_1?x=y") == "B00KCF7JL6"
    assert asin_from_url("https://amazon.com/gp/product/B00KCF7JL6") == "B00KCF7JL6"
    assert asin_from_url("https://www.amazon.com/dp/B00KCF7JL6") == "B00KCF7JL6"
    assert asin_from_url("https://a.co/d/abc123") is None


def test_parse_real_page():
    stats = parse_camel_page(fixture("camel_B00KCF7JL6.html"))
    assert (stats.current, stats.lowest, stats.average) == (184.63, 51.99, 214.71)
    assert "Citizen" in stats.title


def test_falls_back_to_third_party_when_amazon_out_of_stock():
    html = """<table>
    <tr><td>Amazon</td><td>$10.00</td><td>(Jan 1, 2020)</td><td>$20.00</td><td>(Jan 2, 2020)</td>
        <td>-</td><td></td><td>$15.00</td></tr>
    <tr><td>3rd Party New</td><td>$11.00</td><td>(Jan 1, 2020)</td><td>$21.00</td><td>(Jan 2, 2020)</td>
        <td>$12.50</td><td>(Oct 21, 2026)</td><td>$16.00</td></tr></table>"""
    stats = parse_camel_page(html)
    assert (stats.current, stats.lowest, stats.average) == (12.5, 11.0, 16.0)


def test_page_without_table_is_source_error():
    with pytest.raises(SourceError, match="CamelCamelCamel"):
        parse_camel_page("<html>Just a moment...</html>")


def test_amazon_observation():
    fetch = fake_fetch({"camelcamelcamel.com/product/B00KCF7JL6": fixture("camel_B00KCF7JL6.html")})
    obs = amazon_observation("B00KCF7JL6", fetch)
    assert fetch.calls == ["https://camelcamelcamel.com/product/B00KCF7JL6"]
    assert (obs.id, obs.store, obs.url, obs.price) == (
        "amazon-B00KCF7JL6", "Amazon", "https://www.amazon.com/dp/B00KCF7JL6", 184.63)
    assert (obs.outside.normal, obs.outside.lowest) == (214.71, 51.99)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_camel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.camel'`

- [ ] **Step 3: Implement**

`dealfinder/camel.py`:
```python
import re
from dataclasses import dataclass
from html import unescape

from .fetch import SourceError
from .models import Observation, OutsideStats
from .pricepage import parse_product_page
from .prices import to_number

CAMEL_URL = "https://camelcamelcamel.com/product/{asin}"
ASIN = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)")
MONEY = r"\$([\d,]+(?:\.\d{1,2})?)"
DATE = r"\([^)]*\)"


@dataclass
class CamelStats:
    title: str | None
    current: float
    lowest: float
    average: float


def asin_from_url(url: str) -> str | None:
    match = ASIN.search(url)
    return match.group(1) if match else None


def _table_text(html):
    """Page text with every tag turned into a single ' | ' cell separator."""
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]+>", "|", text)).replace("\xa0", " ")
    return re.sub(r"\s*(?:\|\s*)+", " | ", text)


def _row_pattern(label):
    # Columns: Lowest Ever (date), Highest Ever (date), Current (date), Average
    cell = rf"{MONEY} \| {DATE}"
    return rf"\| {re.escape(label)} \| {cell} \| {cell} \| {cell} \| {MONEY}"


def parse_camel_page(html: str) -> CamelStats:
    text = _table_text(html)
    for label in ("Amazon", "3rd Party New"):
        match = re.search(_row_pattern(label), text)
        if match:
            lowest, _highest, current, average = (to_number(g) for g in match.groups())
            return CamelStats(title=parse_product_page(html).title, current=current,
                              lowest=lowest, average=average)
    raise SourceError("couldn't read the CamelCamelCamel price table")


def amazon_observation(asin: str, fetch) -> Observation:
    stats = parse_camel_page(fetch(CAMEL_URL.format(asin=asin)))
    return Observation(id=f"amazon-{asin}", title=stats.title or f"Amazon item {asin}", store="Amazon",
                       url=f"https://www.amazon.com/dp/{asin}", price=stats.current, source="camelcamelcamel",
                       outside=OutsideStats(normal=stats.average, lowest=stats.lowest))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_camel.py -v`
Expected: 5 passed. If `test_parse_real_page` fails, print `_table_text(fixture(...))` around the word "Lowest Ever" and adjust `_table_text`/`_row_pattern` to the real cell layout — do not change the expected numbers (they were read off the live page).

- [ ] **Step 5: Commit**

```bash
git add dealfinder/camel.py tests/test_camel.py
git commit -m "Add CamelCamelCamel reader for Amazon price history

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Shopify shops (DriftHQ, FDF Raceshop)

**Files:**
- Create: `dealfinder/shopify.py`
- Test: `tests/test_shopify.py`

**Interfaces:**
- Consumes: `SourceError`, `Observation`, `to_number`, `host_of`, `store_name`
- Produces:
  - `dealfinder.shopify.product_from_json(product: dict, url: str) -> Observation | None` — price = cheapest available variant (cheapest of all if none available); `was_price` = that variant's `compare_at_price` only if higher; id `shopify-<host>-<product id>`; `source="shop"`
  - `section_observations(section_url: str, fetch) -> list[Observation]` — fetches `<section_url>/products.json?limit=250`
  - `product_observation(product_url: str, fetch) -> Observation` — fetches `<product_url without query>.json`; raises `SourceError` if not Shopify JSON or no price

- [ ] **Step 1: Write the failing tests**

`tests/test_shopify.py`:
```python
import pytest

from dealfinder.fetch import SourceError
from dealfinder.shopify import product_from_json, product_observation, section_observations
from helpers import fake_fetch, fixture

GARAGE = "https://drifthq.com/collections/garage-sale"


def test_section_observations():
    fetch = fake_fetch({"drifthq.com": fixture("shopify_drifthq_garage.json")})
    found = section_observations(GARAGE + "/", fetch)
    assert fetch.calls == [GARAGE + "/products.json?limit=250"]
    assert len(found) == 5
    shirt = found[0]
    assert shirt.id == "shopify-drifthq.com-7816453619899"
    assert (shirt.price, shirt.was_price, shirt.store) == (10.0, 30.0, "DriftHQ")
    assert shirt.url == "https://drifthq.com/products/lzmfg-x-dhq-shirt"
    assert shirt.image.startswith("https://")


def test_no_compare_price_means_no_was_price():
    found = section_observations(GARAGE, fake_fetch({"drifthq.com": fixture("shopify_drifthq_garage.json")}))
    leo = next(o for o in found if "Leo Grande" in o.title)
    assert (leo.price, leo.was_price) == (100.0, None)


def test_product_observation():
    fetch = fake_fetch({"fdfraceshop.com": fixture("shopify_fdf_product.json")})
    obs = product_observation("https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie?variant=1", fetch)
    assert fetch.calls == ["https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie.json"]
    assert (obs.price, obs.was_price, obs.store) == (47.27, None, "FDF Raceshop")
    assert obs.id == "shopify-fdfraceshop.com-7345075060789"


def test_sold_out_everywhere_still_has_price():
    product = {"id": 1, "handle": "x", "title": "X", "variants": [
        {"price": "50.00", "compare_at_price": "80.00", "available": False},
        {"price": "40.00", "compare_at_price": None, "available": False}]}
    assert product_from_json(product, "https://drifthq.com/").price == 40.0


def test_cheapest_available_variant_wins():
    product = {"id": 1, "handle": "x", "title": "X", "variants": [
        {"price": "30.00", "compare_at_price": "45.00", "available": False},
        {"price": "40.00", "compare_at_price": "60.00", "available": True}]}
    obs = product_from_json(product, "https://drifthq.com/")
    assert (obs.price, obs.was_price) == (40.0, 60.0)


def test_product_without_prices_is_none():
    assert product_from_json({"id": 1, "handle": "x", "variants": []}, "https://drifthq.com/") is None


def test_non_shopify_answer_is_source_error():
    fetch = fake_fetch({"synergyracedevelopment.com": "<!DOCTYPE html><html>Not Found</html>"})
    with pytest.raises(SourceError, match="Synergy Race Development"):
        product_observation("https://synergyracedevelopment.com/products/x", fetch)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_shopify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.shopify'`

- [ ] **Step 3: Implement**

`dealfinder/shopify.py`:
```python
import json
from urllib.parse import urlparse

from .fetch import SourceError
from .models import Observation
from .prices import to_number
from .stores import host_of, store_name


def _base(url):
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def _load_json(text, url):
    try:
        data = json.loads(text)
    except ValueError:
        raise SourceError(f"{store_name(url)} didn't send product data") from None
    if not isinstance(data, dict):
        raise SourceError(f"{store_name(url)} didn't send product data")
    return data


def product_from_json(product: dict, url: str) -> Observation | None:
    priced = [(to_number(v.get("price")), v) for v in product.get("variants") or []]
    priced = [(price, v) for price, v in priced if price is not None]
    if not priced:
        return None
    pool = [pv for pv in priced if pv[1].get("available", True)] or priced
    price, variant = min(pool, key=lambda pv: pv[0])
    was = to_number(variant.get("compare_at_price"))
    images = product.get("images") or []
    return Observation(
        id=f"shopify-{host_of(url)}-{product.get('id')}",
        title=product.get("title") or "",
        store=store_name(url),
        url=f"{_base(url)}/products/{product.get('handle')}",
        price=price,
        source="shop",
        was_price=was if was and was > price else None,
        image=images[0].get("src") if images else None,
    )


def section_observations(section_url: str, fetch) -> list[Observation]:
    data = _load_json(fetch(section_url.split("?")[0].rstrip("/") + "/products.json?limit=250"), section_url)
    products = data.get("products")
    if not isinstance(products, list):
        raise SourceError(f"{store_name(section_url)} didn't send product data")
    return [obs for obs in (product_from_json(p, section_url) for p in products) if obs is not None]


def product_observation(product_url: str, fetch) -> Observation:
    data = _load_json(fetch(product_url.split("?")[0].rstrip("/") + ".json"), product_url)
    product = data.get("product")
    obs = product_from_json(product, product_url) if isinstance(product, dict) else None
    if obs is None:
        raise SourceError(f"no price found for {product_url}")
    return obs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_shopify.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/shopify.py tests/test_shopify.py
git commit -m "Add Shopify shop reader for DriftHQ and FDF Raceshop

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Watchlist routing

**Files:**
- Create: `dealfinder/watchlist.py`
- Test: `tests/test_watchlist.py`

**Interfaces:**
- Consumes: `amazon_observation`, `asin_from_url` (Task 6), `product_observation` (Task 7), `page_observation` (Task 4), `WatchItem` (Task 1), `SourceError`, `host_of`, `page_id`, `store_name`
- Produces: `dealfinder.watchlist.watch_observation(item: WatchItem, fetch) -> Observation` — never raises `SourceError`; on failure returns `price=None`, `error=<message>`, `source="watchlist"`. Always sets `target_price` from the item and overrides `title` with `item.name` if given. Routing: Amazon host with ASIN → CamelCamelCamel; `/products/` in path → Shopify JSON, falling back to page reading; anything else → page reading.

- [ ] **Step 1: Write the failing tests**

`tests/test_watchlist.py`:
```python
from dealfinder.fetch import SourceError
from dealfinder.settings import WatchItem
from dealfinder.stores import page_id
from dealfinder.watchlist import watch_observation
from helpers import fake_fetch, fixture

SYNERGY = "https://synergyracedevelopment.com/2005-2014-mustang-s197-spindle-bushings/"


def test_amazon_link_uses_camelcamelcamel():
    fetch = fake_fetch({"camelcamelcamel.com": fixture("camel_B00KCF7JL6.html")})
    obs = watch_observation(WatchItem("https://www.amazon.com/Citizen/dp/B00KCF7JL6?th=1", 150, "My watch"), fetch)
    assert (obs.id, obs.price, obs.target_price, obs.title) == ("amazon-B00KCF7JL6", 184.63, 150, "My watch")
    assert obs.outside is not None


def test_shopify_product_link():
    fetch = fake_fetch({"fdfraceshop.com": fixture("shopify_fdf_product.json")})
    obs = watch_observation(WatchItem("https://fdfraceshop.com/products/fdf-raceshop-classic-hoodie"), fetch)
    assert (obs.price, obs.source, obs.target_price) == (47.27, "shop", None)


def test_other_store_reads_the_page():
    fetch = fake_fetch({"synergyracedevelopment.com": fixture("bigcommerce_synergy.html")})
    obs = watch_observation(WatchItem(SYNERGY), fetch)
    assert (obs.price, obs.source) == (7.5, "page")


def test_products_path_that_isnt_shopify_falls_back_to_page():
    url = "https://driftamerican.com/products/brake-lines"
    fetch = fake_fetch({".json": SourceError("not shopify"),
                        "driftamerican.com": fixture("bigcommerce_driftamerican.html")})
    obs = watch_observation(WatchItem(url), fetch)
    assert (obs.price, obs.source) == (135, "page")


def test_blocked_item_is_reported_not_guessed():
    url = "https://www.homedepot.com/p/Milwaukee-Drill/306224456"
    fetch = fake_fetch({"homedepot.com": SourceError("homedepot.com blocked the check (error 403)")})
    obs = watch_observation(WatchItem(url, 99, "Milwaukee drill"), fetch)
    assert obs.price is None
    assert obs.error == "homedepot.com blocked the check (error 403)"
    assert (obs.id, obs.title, obs.store, obs.target_price) == (page_id(url), "Milwaukee drill", "Home Depot", 99)


def test_blocked_amazon_item_keeps_amazon_id():
    fetch = fake_fetch({"camelcamelcamel.com": SourceError("down")})
    obs = watch_observation(WatchItem("https://www.amazon.com/dp/B00KCF7JL6"), fetch)
    assert (obs.id, obs.price) == ("amazon-B00KCF7JL6", None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_watchlist.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.watchlist'`

- [ ] **Step 3: Implement**

`dealfinder/watchlist.py`:
```python
from urllib.parse import urlparse

from .camel import amazon_observation, asin_from_url
from .fetch import SourceError
from .models import Observation
from .pricepage import page_observation
from .settings import WatchItem
from .shopify import product_observation
from .stores import host_of, page_id, store_name


def _amazon_asin(url):
    return asin_from_url(url) if "amazon." in host_of(url) else None


def _read(url, fetch):
    if asin := _amazon_asin(url):
        return amazon_observation(asin, fetch)
    if "/products/" in urlparse(url).path:
        try:
            return product_observation(url, fetch)
        except SourceError:
            pass  # not a Shopify store after all; read the page instead
    return page_observation(url, fetch)


def watch_observation(item: WatchItem, fetch) -> Observation:
    try:
        obs = _read(item.url, fetch)
    except SourceError as e:
        asin = _amazon_asin(item.url)
        obs = Observation(id=f"amazon-{asin}" if asin else page_id(item.url), title=item.url,
                          store=store_name(item.url), url=item.url, price=None,
                          source="watchlist", error=str(e))
    if item.name:
        obs.title = item.name
    obs.target_price = item.target_price
    return obs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_watchlist.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/watchlist.py tests/test_watchlist.py
git commit -m "Add watchlist routing to the right price reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Alert email

**Files:**
- Create: `dealfinder/emailer.py`
- Test: `tests/test_emailer.py`

**Interfaces:**
- Consumes: report entry dicts as produced by Task 10 (`title`, `store`, `url`, `price`, `target_price`, `rating: {label, normal, percent_below, hit_target}`)
- Produces:
  - `dealfinder.emailer.compose(alerts: list[dict], site_url: str, address: str) -> EmailMessage` — subject `"1 deal alert today"` / `"N deal alerts today"`; From and To = `address`
  - `dealfinder.emailer.send(msg: EmailMessage, address: str, app_password: str, smtp_factory=smtplib.SMTP_SSL) -> None` — Gmail SMTP on port 465

- [ ] **Step 1: Write the failing tests**

`tests/test_emailer.py`:
```python
from dealfinder.emailer import compose, send


def entry(title, price, normal=None, percent=None, label="real-deal", target=None, hit=False):
    return {"title": title, "store": "DriftHQ", "url": "https://drifthq.com/products/x", "price": price,
            "target_price": target,
            "rating": {"label": label, "normal": normal, "percent_below": percent, "hit_target": hit}}


def test_compose():
    msg = compose([entry("Coilovers", 800, 1000, 20.0),
                   entry("Bucket seat", 1250.5, label="meh", target=1300, hit=True)],
                  "https://nevadaocull.github.io/real-deal-finder/", "me@gmail.com")
    body = msg.get_content()
    assert msg["Subject"] == "2 deal alerts today"
    assert msg["To"] == msg["From"] == "me@gmail.com"
    assert "Coilovers - $800.00 at DriftHQ, 20% below its normal $1,000.00" in body
    assert "Bucket seat - $1,250.50 at DriftHQ, hit your target of $1,300.00" in body
    assert "https://drifthq.com/products/x" in body
    assert "See everything: https://nevadaocull.github.io/real-deal-finder/" in body


def test_compose_single():
    assert compose([entry("Coilovers", 800, 1000, 20.0)], "", "me@gmail.com")["Subject"] == "1 deal alert today"


def test_send_logs_in_and_sends():
    events = []

    class FakeSMTP:
        def __init__(self, host, port):
            events.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            events.append(("close",))

        def login(self, user, password):
            events.append(("login", user, password))

        def send_message(self, msg):
            events.append(("send", msg["Subject"]))

    msg = compose([entry("Coilovers", 800, 1000, 20.0)], "", "me@gmail.com")
    send(msg, "me@gmail.com", "app-pass", smtp_factory=FakeSMTP)
    assert events == [("connect", "smtp.gmail.com", 465), ("login", "me@gmail.com", "app-pass"),
                      ("send", "1 deal alert today"), ("close",)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_emailer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.emailer'`

- [ ] **Step 3: Implement**

`dealfinder/emailer.py`:
```python
import smtplib
from email.message import EmailMessage


def _money(amount):
    return f"${amount:,.2f}"


def _line(item):
    rating = item["rating"]
    parts = [f"{item['title']} - {_money(item['price'])} at {item['store']}"]
    if rating["label"] == "real-deal" and rating.get("normal") is not None:
        parts.append(f"{rating['percent_below']:g}% below its normal {_money(rating['normal'])}")
    if rating.get("hit_target") and item.get("target_price") is not None:
        parts.append(f"hit your target of {_money(item['target_price'])}")
    return ", ".join(parts) + f"\n  {item['url']}"


def compose(alerts: list[dict], site_url: str, address: str) -> EmailMessage:
    count = len(alerts)
    msg = EmailMessage()
    msg["Subject"] = f"{count} deal alert{'' if count == 1 else 's'} today"
    msg["From"] = address
    msg["To"] = address
    body = "\n\n".join(_line(item) for item in alerts)
    if site_url:
        body += f"\n\nSee everything: {site_url}"
    msg.set_content(body + "\n")
    return msg


def send(msg: EmailMessage, address: str, app_password: str, smtp_factory=smtplib.SMTP_SSL) -> None:
    with smtp_factory("smtp.gmail.com", 465) as smtp:
        smtp.login(address, app_password)
        smtp.send_message(msg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_emailer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add dealfinder/emailer.py tests/test_emailer.py
git commit -m "Add daily alert email

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: The daily run

**Files:**
- Create: `dealfinder/run.py`
- Test: `tests/test_run.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `dealfinder.run.SourceStatus(name: str, ok: bool, message: str = "")`
  - `collect(settings: Settings, fetch, now: datetime, pause=time.sleep) -> tuple[list[Observation], list[Observation], list[SourceStatus]]` — (deals, watched, statuses). Deals are deduped by id (first interest wins). Amazon deals get `outside` stats from CamelCamelCamel (max 40 lookups per run, `pause(2)` before each); a failed lookup leaves `outside=None`. Any exception inside one source is caught and recorded in its `SourceStatus`.
  - `build_report(deals, watched, statuses, history: History, today: date, settings: Settings, generated: datetime) -> dict` — records every observation in history, rates it, returns:
    ```
    {"generated": "2026-10-21T11:00+00:00",
     "settings": {"threshold": 15.0, "interests": {...}, "shop_sections": [...], "watch_count": 0},
     "sources": [{"name", "ok", "message"}],
     "deals": [entry...],      # priced deals only; sorted real, meh, not-enough, no-deal, fake; then % below, biggest first
     "watchlist": [entry...]}
    entry = {"id","title","store","url","image","interest","price","was_price","target_price","error",
             "rating": {"label","normal","lowest","percent_below","history_days","hit_target"},
             "history": [["YYYY-MM-DD", price_or_null], ...]}   # last 90 days
    ```
  - `pick_alerts(report: dict) -> list[dict]` — real-deal deals + watchlist entries that are real deals or hit their target; no duplicates by id
  - `main(root=Path("."), fetch=fetch, pause=time.sleep, env=os.environ) -> int` — writes `site/deals.json`, emails if alerts and `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` are set; returns 1 with a plain message on `SettingsError`
  - Run as `python -m dealfinder.run`

- [ ] **Step 1: Write the failing tests**

`tests/test_run.py`:
```python
import json
from datetime import date, datetime, timezone

from dealfinder import run as run_module
from dealfinder.fetch import SourceError
from dealfinder.history import History, PricePoint
from dealfinder.models import Observation, OutsideStats
from dealfinder.rating import MEH, NOT_ENOUGH, REAL, UNAVAILABLE
from dealfinder.settings import Settings, WatchItem
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
    settings = Settings(shop_sections=["https://drifthq.com/collections/garage-sale"])
    deals, _, statuses = run_module.collect(settings, fake_fetch(pages()), NOW, no_pause)
    assert len(deals) == 5 and all(d.interest == "Shop sales" for d in deals)
    assert ("DriftHQ sale section", True) in [(s.name, s.ok) for s in statuses]


def test_one_source_crashing_does_not_stop_others(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("parser bug")
    monkeypatch.setattr(run_module.slickdeals, "search", broken)
    settings = Settings(interests={"Watches": ["eco-drive"]},
                        shop_sections=["https://drifthq.com/collections/garage-sale"])
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
                        shop_sections=["https://drifthq.com/collections/garage-sale"],
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dealfinder.run'`

- [ ] **Step 3: Implement**

`dealfinder/run.py`:
```python
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
        emailer.send(emailer.compose(alerts, settings.site_url, address), address, password)
        print("alert email sent")
    elif alerts:
        print("alerts found, but email isn't set up (GMAIL_ADDRESS / GMAIL_APP_PASSWORD)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_run.py -v`
Expected: 10 passed

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -q`
Expected: 89 passed

- [ ] **Step 6: Live smoke run against the real sites**

Run: `python -m dealfinder.run`
Expected: a summary line like `N deals checked, ...`, possibly with `problem - ...` lines for blocked stores. `site/deals.json` exists. Open it and confirm entries have sane prices. Then delete the test history so the real history starts clean: `git status` should show `data/history/` as untracked — run `rm -rf data/history` (it will be rebuilt by the first real daily run).

- [ ] **Step 7: Commit**

```bash
git add dealfinder/run.py tests/test_run.py
git commit -m "Add daily run: collect, record history, rate, write page data, email

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: The deals page

**Files:**
- Create: `site/index.html`, `site/style.css`, `site/app.js`

**Interfaces:**
- Consumes: `site/deals.json` in the shape produced by `build_report` (Task 10)
- Produces: a static page with three tabs (Deals, Watchlist, Settings)

- [ ] **Step 1: Write the page**

`site/index.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Real Deal Finder</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>Real Deal Finder</h1>
    <p id="updated" class="muted">Loading…</p>
    <nav>
      <button type="button" data-tab="deals" class="active">Deals</button>
      <button type="button" data-tab="watchlist">Watchlist</button>
      <button type="button" data-tab="settings">Settings</button>
    </nav>
  </header>
  <main>
    <section id="deals">
      <div class="filters">
        <select id="f-store" aria-label="Store"><option value="">All stores</option></select>
        <select id="f-interest" aria-label="Interest"><option value="">All interests</option></select>
        <label><input type="checkbox" id="f-real"> Real deals only</label>
      </div>
      <div id="problems"></div>
      <div id="deal-list" class="cards"></div>
    </section>
    <section id="watchlist" hidden>
      <div id="watch-list" class="cards"></div>
    </section>
    <section id="settings" hidden>
      <div id="settings-body"></div>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

`site/style.css`:
```css
:root {
  --bg: #f6f5f2; --surface: #ffffff; --text: #1c1c1a; --muted: #6b6a66; --line: #e3e1db;
  --accent: #1f5f8b;
  --real: #1d7a46; --real-bg: #e3f3e9;
  --meh: #8a6a10; --meh-bg: #f7efd6;
  --fake: #a1322b; --fake-bg: #f8e2df;
  --neutral: #55544f; --neutral-bg: #ecebe6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161615; --surface: #20201e; --text: #ecebe6; --muted: #a09f99; --line: #34332f;
    --accent: #7db6dd;
    --real: #6fd39a; --real-bg: #193826;
    --meh: #e5c568; --meh-bg: #3a3117;
    --fake: #f08a80; --fake-bg: #3f201d;
    --neutral: #c4c3bd; --neutral-bg: #2d2c29;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
header, main { max-width: 960px; margin: 0 auto; padding: 0 16px; }
header { padding-top: 20px; }
h1 { font-size: 1.5rem; margin: 0; }
.muted { color: var(--muted); margin: 4px 0 12px; font-size: .9rem; }
nav { display: flex; gap: 4px; border-bottom: 1px solid var(--line); }
nav button { background: none; border: 0; border-bottom: 3px solid transparent; color: var(--muted);
  font: inherit; padding: 10px 12px; cursor: pointer; }
nav button.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin: 16px 0; }
select { font: inherit; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--surface); color: var(--text); max-width: 100%; }
.problems { background: var(--meh-bg); color: var(--meh); border-radius: 8px; padding: 10px 12px;
  margin-bottom: 16px; font-size: .9rem; }
.problems ul { margin: 4px 0 0; padding-left: 20px; }
.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  margin-bottom: 32px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  display: flex; gap: 12px; padding: 12px; }
.card img, .card .noimg { width: 72px; height: 72px; object-fit: contain; flex: none; border-radius: 6px;
  background: var(--neutral-bg); }
.card .body { min-width: 0; flex: 1; }
.card h3 { font-size: .95rem; margin: 6px 0 2px; line-height: 1.3; overflow-wrap: anywhere; }
.card h3 a { color: var(--text); text-decoration: none; }
.card h3 a:hover { text-decoration: underline; }
.meta, .note { color: var(--muted); font-size: .8rem; margin: 0; }
.note { margin-top: 6px; }
.top { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.badge { font-size: .75rem; font-weight: 600; padding: 2px 8px; border-radius: 999px;
  background: var(--neutral-bg); color: var(--neutral); }
.badge.real-deal { background: var(--real-bg); color: var(--real); }
.badge.meh { background: var(--meh-bg); color: var(--meh); }
.badge.fake-sale { background: var(--fake-bg); color: var(--fake); }
.pct { font-size: .8rem; font-weight: 600; color: var(--real); }
.row { display: flex; justify-content: space-between; align-items: end; gap: 8px; margin-top: 8px; }
.stats { display: grid; grid-template-columns: auto auto; gap: 0 10px; margin: 0; font-size: .8rem; }
.stats dt { color: var(--muted); }
.stats dd { margin: 0; font-variant-numeric: tabular-nums; }
.stats dd.now { font-weight: 700; font-size: .95rem; }
.spark { width: 96px; height: 32px; flex: none; }
.spark path { fill: none; stroke: var(--accent); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.empty { color: var(--muted); padding: 24px 0; }
#settings-body { max-width: 640px; padding: 16px 0 32px; }
#settings-body h2 { font-size: 1.05rem; margin: 20px 0 6px; }
#settings-body ul { margin: 0; padding-left: 20px; }
code { background: var(--neutral-bg); padding: 1px 5px; border-radius: 4px; }
```

`site/app.js`:
```js
"use strict";

const LABELS = {
  "real-deal": "Real deal",
  "meh": "Meh",
  "fake-sale": "Fake sale",
  "no-deal": "No deal",
  "not-enough-history": "Not enough history yet",
  "unavailable": "Couldn't check today",
};

let report = null;

function money(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : null;
}

// Builds elements with textContent only: every title and URL comes from other websites.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null) continue;
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) if (child) node.append(child);
  return node;
}

function sparkline(history) {
  const points = history.filter((p) => p[1] != null);
  if (points.length < 2) return null;
  const w = 96, h = 32;
  const prices = points.map((p) => p[1]);
  const lo = Math.min(...prices), hi = Math.max(...prices), span = hi - lo || 1;
  const d = points.map((p, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - 3 - ((p[1] - lo) / span) * (h - 6);
    return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Price over ${points.length} days: low ${money(lo)}, high ${money(hi)}`);
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  svg.append(path);
  return svg;
}

function card(item) {
  const r = item.rating;
  const url = safeUrl(item.url);
  const title = url
    ? el("a", { href: url, target: "_blank", rel: "noopener", text: item.title })
    : el("span", { text: item.title });
  const pct = r.percent_below > 0 ? el("span", { class: "pct", text: `${r.percent_below}% below normal` }) : null;
  const notes = [];
  if (item.was_price) notes.push(`Store says it was ${money(item.was_price)}`);
  if (item.target_price != null) notes.push(`Your target ${money(item.target_price)}${r.hit_target ? " — hit!" : ""}`);
  if (r.label === "not-enough-history") notes.push(`Tracked ${r.history_days} of 14 days needed`);
  if (item.error) notes.push(item.error);
  const image = safeUrl(item.image) ? el("img", { src: item.image, alt: "", loading: "lazy" }) : el("div", { class: "noimg" });
  return el("article", { class: "card" }, [
    image,
    el("div", { class: "body" }, [
      el("div", { class: "top" }, [el("span", { class: `badge ${r.label}`, text: LABELS[r.label] || r.label }), pct]),
      el("h3", {}, title),
      el("p", { class: "meta", text: [item.store, item.interest].filter(Boolean).join(" · ") }),
      el("div", { class: "row" }, [
        el("dl", { class: "stats" }, [
          el("dt", { text: "Now" }), el("dd", { class: "now", text: money(item.price) }),
          el("dt", { text: "Normal" }), el("dd", { text: money(r.normal) }),
          el("dt", { text: "Lowest seen" }), el("dd", { text: money(r.lowest) }),
        ]),
        sparkline(item.history),
      ]),
      notes.length ? el("p", { class: "note", text: notes.join(" · ") }) : null,
    ]),
  ]);
}

function fillSelect(select, values) {
  for (const value of [...new Set(values.filter(Boolean))].sort()) {
    select.append(el("option", { value, text: value }));
  }
}

function renderDeals() {
  const store = document.getElementById("f-store").value;
  const interest = document.getElementById("f-interest").value;
  const realOnly = document.getElementById("f-real").checked;
  const shown = report.deals.filter((d) =>
    (!store || d.store === store) &&
    (!interest || d.interest === interest) &&
    (!realOnly || d.rating.label === "real-deal"));
  const list = document.getElementById("deal-list");
  list.replaceChildren(...shown.map(card));
  if (!shown.length) list.append(el("p", { class: "empty", text: "No deals match right now. Check back tomorrow." }));
}

function renderProblems() {
  const failed = report.sources.filter((s) => !s.ok);
  const box = document.getElementById("problems");
  box.replaceChildren();
  if (!failed.length) return;
  box.className = "problems";
  box.append(el("strong", { text: "Some checks didn't work today:" }),
    el("ul", {}, failed.map((s) => el("li", { text: `${s.name}: ${s.message}` }))));
}

function renderWatchlist() {
  const list = document.getElementById("watch-list");
  list.replaceChildren(...report.watchlist.map(card));
  if (!report.watchlist.length) {
    list.append(el("p", { class: "empty", text: "Nothing on your watchlist yet. Add product links in the settings file (see the Settings tab)." }));
  }
}

function renderSettings() {
  const s = report.settings;
  const body = document.getElementById("settings-body");
  const interests = Object.entries(s.interests).map(([name, words]) =>
    el("li", { text: `${name}: ${words.join(", ") || "(no search words yet)"}` }));
  body.replaceChildren(
    el("h2", { text: "Real deal means" }),
    el("p", { text: `At least ${s.threshold}% below the item's normal price (its typical price over the last 90 days), or a new lowest price.` }),
    el("h2", { text: "Your interests" }),
    interests.length ? el("ul", {}, interests) : el("p", { text: "None yet." }),
    el("h2", { text: "Shop sale sections watched" }),
    s.shop_sections.length ? el("ul", {}, s.shop_sections.map((u) => el("li", { text: u }))) : el("p", { text: "None." }),
    el("h2", { text: "Watchlist" }),
    el("p", { text: `${s.watch_count} item(s).` }),
    el("h2", { text: "Changing these" }),
    el("p", {}, ["Edit ", el("code", { text: "config/settings.yml" }),
      " in your GitHub repository (or ask Claude to). The next daily check uses the new settings."]),
  );
}

function showTab(name) {
  for (const button of document.querySelectorAll("nav button")) {
    button.classList.toggle("active", button.dataset.tab === name);
  }
  for (const id of ["deals", "watchlist", "settings"]) {
    document.getElementById(id).hidden = id !== name;
  }
}

async function load() {
  const updated = document.getElementById("updated");
  try {
    const response = await fetch("deals.json", { cache: "no-store" });
    if (!response.ok) throw new Error(response.status);
    report = await response.json();
  } catch (e) {
    updated.textContent = "Couldn't load today's deals. The daily check may not have run yet.";
    return;
  }
  const when = new Date(report.generated);
  updated.textContent = `Checked ${when.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} · ` +
    `${report.deals.filter((d) => d.rating.label === "real-deal").length} real deals`;
  fillSelect(document.getElementById("f-store"), report.deals.map((d) => d.store));
  fillSelect(document.getElementById("f-interest"), report.deals.map((d) => d.interest));
  renderProblems();
  renderDeals();
  renderWatchlist();
  renderSettings();
}

for (const button of document.querySelectorAll("nav button")) {
  button.addEventListener("click", () => showTab(button.dataset.tab));
}
for (const id of ["f-store", "f-interest", "f-real"]) {
  document.getElementById(id).addEventListener("change", renderDeals);
}
load();
```

- [ ] **Step 2: Preview with real data**

Run: `python -m dealfinder.run` (creates `site/deals.json`), then `python -m http.server 8765 --directory site` in the background.
Open `http://localhost:8765/` in Chrome (claude-in-chrome). Check, at desktop width and at 390px wide:
- Deals tab shows cards with badge, prices, store; filters change the list; "Real deals only" works.
- Watchlist tab shows the empty message (or items if the settings file has any).
- Settings tab lists the interests from `config/settings.yml`.
- No horizontal scrolling at 390px; dark mode readable (toggle OS/browser dark mode).
- Browser console has no errors.
Then stop the server and `rm -rf data/history` (test history).

- [ ] **Step 3: Commit**

```bash
git add site/index.html site/style.css site/app.js
git commit -m "Add the deals page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Daily GitHub job and owner guide

**Files:**
- Create: `.github/workflows/daily.yml`, `README.md`

**Interfaces:**
- Consumes: `python -m dealfinder.run`, `requirements.txt`, `site/`
- Produces: a workflow that runs daily at 11:00 UTC and on demand, runs tests, runs the check, commits `data/history`, and publishes `site/` to GitHub Pages. Secrets used: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`.

- [ ] **Step 1: Write the workflow**

`.github/workflows/daily.yml`:
```yaml
name: Daily deal check

on:
  schedule:
    - cron: "0 11 * * *"   # 11:00 UTC = 6 AM Central (daylight time)
  workflow_dispatch:       # lets you run it by hand from the Actions tab

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: daily-deal-check
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - run: pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest -q

      - name: Check prices
        run: python -m dealfinder.run
        env:
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}

      - name: Save price history
        run: |
          git config user.name "deal-finder-bot"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/history
          git diff --cached --quiet || git commit -m "Price history $(date -u +%F)"
          git push

      - uses: actions/configure-pages@v5

      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Write the owner guide**

`README.md`:
````markdown
# Real Deal Finder

Finds deals that are actually below an item's normal price — not just things a store
calls "on sale." Every morning it checks prices, keeps a price history, rates each deal,
updates your deals page, and emails you if something is worth buying.

## What the ratings mean

| Rating | Meaning |
|---|---|
| **Real deal** | At least 15% below its normal price (typical price over the last 90 days), or the lowest price seen |
| **Meh** | A little below normal |
| **Fake sale** | The store's "was" price wasn't really the normal price, or it isn't actually cheaper |
| **No deal** | Normal price |
| **Not enough history yet** | Tracked fewer than 14 days — check back |
| **Couldn't check today** | The store blocked the check or was down; no price is guessed |

Amazon items use CamelCamelCamel's price history, so they're rated from day one.
Other stores get smarter as the app records prices each day.

## Changing what it looks for

Everything is in **`config/settings.yml`**. On GitHub: open the file, click the pencil
(Edit), change it, and click **Commit changes**. Or just ask Claude to change it.

- **interests** — names with search words. A deal shows up when its title has every word of a search.
- **shop_sections** — sale pages of Shopify stores (DriftHQ, FDF Raceshop) to watch.
- **watchlist** — product links to track, with an optional `target_price`.
- **real_deal_threshold_percent** — how big a discount counts as a real deal.

## Running it by hand

On GitHub: **Actions → Daily deal check → Run workflow**.

## One-time setup (already done if your page is working)

1. **Gmail app password:** Google Account → Security → 2-Step Verification (must be on) →
   App passwords → create one named "Real Deal Finder". Copy the 16-letter password.
2. **Secrets:** repository **Settings → Secrets and variables → Actions → New repository secret**:
   - `GMAIL_ADDRESS` — your Gmail address
   - `GMAIL_APP_PASSWORD` — the app password from step 1
3. **Page:** repository **Settings → Pages → Source: GitHub Actions**.
4. Run the workflow once by hand (above). Your page appears at the address shown in Settings → Pages.

## Stores and how reliable they are

| Store | How it's checked | Reliability |
|---|---|---|
| Slickdeals (all stores incl. Walmart, Home Depot, Enjuku) | Keyword search feed | Good |
| Amazon | CamelCamelCamel price history | Good |
| DriftHQ, FDF Raceshop | Store's product data | Very good |
| Synergy Race Development, Drift American | Product page | Good |
| Walmart, Home Depot (watchlist) | Product page | Often blocked |
| Enjuku Racing (watchlist) | Product page | Usually blocked |
````

- [ ] **Step 3: Check the workflow file is valid YAML**

Run: `python -c "import yaml; d = yaml.safe_load(open('.github/workflows/daily.yml')); print(list(d['jobs']['check']['steps'][i].get('name', d['jobs']['check']['steps'][i].get('uses')) for i in range(9)))"`
Expected: prints the 9 step names/actions without error.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/daily.yml README.md
git commit -m "Add daily GitHub job and owner guide

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Go live (needs the owner)

**Files:** none (configuration on GitHub)

This task needs the owner's decisions and hands; stop and ask at each **Ask** point.

- [ ] **Step 1: Ask: public or private repository?**
Free GitHub Pages requires a public repository. Explain to the owner: price history, settings (interests, watchlist links) and code become visible; email address and Gmail password stay secret. Options: make public (free page) / keep private (page needs GitHub Pro, $4/month — conflicts with $0 constraint). If public: `gh repo edit NevadaOCull/real-deal-finder --visibility public --accept-visibility-change-consequences`

- [ ] **Step 2: Push**
Run: `git push origin main`
Expected: pushes all commits.

- [ ] **Step 3: Turn on Pages (workflow source)**
Run: `gh api -X POST repos/NevadaOCull/real-deal-finder/pages -f build_type=workflow`
Expected: JSON with `"html_url": "https://nevadaocull.github.io/real-deal-finder/"`. (If it says it already exists, run the same with `-X PUT`.)

- [ ] **Step 4: Ask: Gmail app password**
Walk the owner through README setup step 1. Then have them run, in this session, so the password never appears in chat:
`! gh secret set GMAIL_APP_PASSWORD -R NevadaOCull/real-deal-finder` (prompts for the value)
and run `gh secret set GMAIL_ADDRESS -R NevadaOCull/real-deal-finder --body "<your Gmail address>"` after confirming that's the address they want alerts at.

- [ ] **Step 5: Fill in site_url**
Set `site_url:` in `config/settings.yml` to the Pages address from Step 3; commit ("Set deals page address" + Co-Authored-By line); push.

- [ ] **Step 6: First run**
Run: `gh workflow run daily.yml -R NevadaOCull/real-deal-finder`, then `gh run watch -R NevadaOCull/real-deal-finder` (pick the newest run).
Expected: all steps green. If "Run tests" or "Check prices" fails, use superpowers:systematic-debugging — do not skip tests in the workflow.

- [ ] **Step 7: Verify for real**
Open the Pages address in Chrome at phone width; confirm deals render and the "problems" box lists only expected blocked stores. Confirm `data/history/` got a commit from `deal-finder-bot`. Report to the owner: page address, number of deals found, which sources worked, which were blocked, and whether an alert email was sent.
