# Real Deal Finder

Finds deals that are actually below an item's normal price — not just things a store
calls "on sale." Every morning it checks prices, keeps a price history, rates each deal,
updates your deals page, and emails you if something is worth buying.

## What the ratings mean

| Rating | Meaning |
|---|---|
| **Real deal** | At least 15% below its normal price (typical price over the last 90 days), or cheaper than its best earlier sale |
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

- **interests** — names with searches. A deal shows up when its title contains a search as a phrase (whole words; plurals count).
- **shop_sections** — sale pages of Shopify stores (DriftHQ, FDF Raceshop) to watch. Add `only:` words to show just the items whose titles contain one of them.
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
