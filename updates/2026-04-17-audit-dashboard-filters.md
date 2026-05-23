# Audit Dashboard Filter Updates — 2026-04-17

## Summary
Added two new interactive features to the Crypto and Non-Crypto performance panels in `audit_dashboard/template.html`.

## 1. "Last N Picks" Filter

**What changed:**
- The existing Last-N dropdowns (crypto panel header and conviction bar for non-crypto) were updated:
  - **Default:** changed from `All Time` to **`Last 20`**.
  - **Options:** now `Last 10`, `Last 20`, `Last 50`, `Last 100`, `All Time`.
- Both dropdowns stay in sync: changing either one updates `_PERF_LAST_N_FILTER` and re-renders **both** panels.
- Under the hood, `_applyLastNFilter(active, closed, n)` keeps the `n` most recent closed picks (by `closed_at` DESC) plus any active picks opened on or after the oldest of those `n` closed picks.
- If a filtered sample would drop below 5 picks, the full list is used as a defensive fallback (`_applyRecentN`).

**Lines modified:**
- `_PERF_LAST_N_FILTER` default value (was `null`, now `20`)
- `renderConvictionBar()` — non-crypto select options reordered and expanded
- `renderCryptoPanel()` — crypto select options reordered and expanded

## 2. "Latest Active + Latest Closed per Strategy" View

**What changed:**
- **Crypto panel:** new split mode button **`Latest/Strat`** joins the existing `Score` / `Source` / `Strategy` buttons.
- **Non-crypto panel:** new toggle button **`Category view`** / **`✓ Strategy view`** in the panel header (next to the existing kill-list toggle).
- When enabled, both panels render **one card per strategy** instead of grouping by score tier or asset class.
- Each strategy card displays:
  1. **Strategy name** (truncated if >24 chars)
  2. **Most recent ACTIVE pick** — symbol, entry price, unrealized PnL
  3. **Most recent CLOSED pick** — symbol, exit reason, realized PnL
  4. **Mini stats from the last 10 closed picks for that strategy only:**
     - Win / Loss / Flat counts
     - Win-rate badge
     - Profit Factor
     - Average PnL per trade
     - Total realized PnL

**New helper function:**
- `_buildLatestStrategyCard(strategyName, stratActive, stratClosed, borderColor, color)` — shared by both panels to keep card markup consistent with the existing `nc-card` / `nc-header` / `nc-row` CSS.

**Lines modified:**
- Added `_NC_LATEST_PER_STRATEGY = false` global toggle
- `renderNonCryptoPanel()` — strategy-view branch + toggle button + event listener
- `renderCryptoPanel()` — `latest-strategy` split mode + branch in card builder

## Backward Compatibility
- Default panel behavior when the page loads is unchanged **except** for the Last-N default (now 20 instead of All). 
- Existing split modes (`score`, `source`, `strategy`) and category views remain untouched.
- No existing function signatures were changed; only new branches and UI controls were added.
