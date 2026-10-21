# Real Deal Finder — Design

Date: 2026-10-21
Status: Draft, awaiting owner review

## Purpose

Find deals that are genuinely below an item's normal price, not just items a store
labels "on sale." Covers Amazon, Walmart, Home Depot, deal posts in categories the
owner picks, and drift-car parts from specialty shops.

**Success looks like:** the owner opens one page (phone or computer) and sees today's
deals ranked by how far below their *real* normal price they are, with fake sales
clearly flagged, and gets one email a day when something worth buying shows up.

## Constraints

- **$0 running cost.** Free data sources only; no paid APIs.
- **Works on phone and computer.** Nothing has to run on the owner's PC.
- **Owner is not a programmer.** Setup steps must be walked through; settings must
  live in one plain, commented file.

## Architecture

```
GitHub repo (free)
├── config/settings.yml        ← owner edits: categories, keywords, watchlist, threshold, email
├── data/history/*.json        ← price history, one file per tracked item
├── src/                       ← Python daily checker
│   ├── sources/               ← one module per source (see below)
│   ├── rating.py              ← the real-deal test
│   ├── history.py             ← read/append price history
│   ├── build_site.py          ← writes site/ (deals.json + static page)
│   └── emailer.py             ← daily alert email
├── site/                      ← static web page, published by GitHub Pages
└── .github/workflows/daily.yml← runs the checker every day ~6 AM local time
```

Daily run: load settings → each source collects candidate deals / watched prices →
append prices to history → rate everything → write `site/deals.json` → commit →
GitHub Pages republishes → send email if anything qualifies.

Each source is isolated: if one fails, the others still run, and the page shows
"couldn't check today" for the failed source.

## Sources

| Source | Used for | Method | Expected reliability |
|---|---|---|---|
| Slickdeals | Category + keyword deals from all stores (incl. Walmart, Home Depot, Amazon, Enjuku) | Public RSS feeds (frontpage/popular + per-category; fallback: category page) | Good — category feed URLs to be verified first |
| CamelCamelCamel | Amazon price history from day one | Per-product price-history RSS | Good |
| Shopify shops: **DriftHQ**, **FDF Raceshop** | Watched parts + sale sections (e.g. DriftHQ Garage Sale) | `/products.json` and `/collections/<name>/products.json` | Very good (verified 2026-10-21) |
| Product-page shops: **Synergy Race Development**, **Drift American** | Watched parts | Read price from product page (structured data / meta tags) | Probably good — test each |
| **Walmart**, **Home Depot** | Watched items | Read price from product page | Fair — sometimes blocked |
| **Enjuku Racing** | Watched items | Read product page | Poor — Cloudflare blocks; deals still arrive via Slickdeals |

Amazon is never read directly (it blocks automated checks); Amazon prices come from
CamelCamelCamel and deal posts.

## The real-deal test (`rating.py`)

Inputs: current price, the item's price history, and (if given) the store's
claimed "was" price.

- **Normal price** = median price over the last 90 days of history.
- **Real deal** — current price is ≥ threshold (default 15%) below normal price,
  **or** is a new all-time low with at least 30 days of history.
- **Meh** — 1% up to threshold below normal.
- **Fake sale** — store claims a "was" price, but that price was the actual price
  on fewer than 30% of days in the last 90 (i.e. inflated before the "sale"), or the
  current price is at/above normal.
- **Not enough history** — fewer than 14 days of history and no outside history.

Target prices on watchlist items trigger an alert independently of the rating.

## The page (`site/`)

Static HTML/JS reading `deals.json`; no login, no server. Three tabs:

1. **Deals** — cards sorted by % below normal price. Each card: item, store, price
   now, normal price, lowest seen, rating badge, small price-history chart, link.
   Filters: store, category/keyword, "Real deals only."
2. **Watchlist** — every watched item with history chart, rating, target price.
3. **Settings** — read-only view of current settings plus plain instructions for
   changing them.

Phone-first layout.

## Alerts (`emailer.py`)

One email per day after the run, only if something qualifies: real deals in the
owner's categories/keywords, and watched items that hit their target price or a new
low. Sent via Gmail SMTP using a Gmail app password stored as a GitHub secret.

## Settings (`config/settings.yml`)

```yaml
real_deal_threshold_percent: 15
email: you@example.com
categories: [tools, automotive, electronics]
keywords: [coilovers, bucket seat, angle kit, hydro e-brake, wheels]
watch_sale_sections:
  - https://drifthq.com/collections/garage-sale
watchlist:
  - url: https://www.amazon.com/dp/XXXXXXXX
    target_price: 150
```

## Error handling

- Each source wrapped so a failure is logged and shown on the page, never fatal.
- Blocked/failed price check records "no data" for that day — never a guessed price.
- If the whole run fails, GitHub emails the owner (built-in workflow failure notice).

## Testing

- Unit tests for `rating.py` against hand-built histories: honest sale, inflated
  "was" price, new low, too little history, target hit.
- Unit tests for each source's parser against saved sample responses.
- Live check of every source before handover, with results reported to the owner.

## Out of scope (v1)

- Adding items from the page itself (needs login/backend) — edit settings file instead.
- Browser extension for rating prices while shopping — possible v2.
- Paid data sources (Keepa etc.).

## Setup the owner will do (walked through step by step)

1. Create a free GitHub account.
2. Create a Gmail app password.
3. Paste two secrets into GitHub; turn on GitHub Pages.
