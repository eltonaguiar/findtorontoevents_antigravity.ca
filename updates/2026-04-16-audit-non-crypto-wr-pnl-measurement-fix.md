# Fix: Non-crypto aggregate WR / PnL skew (empty `asset_class` + outcome threshold)

## Problem

With **“Ex-killed”** (`_NC_EXCLUDE_KILLED`) the dashboard recomputes non-crypto stats client-side. Two issues biased the **aggregate** line and per-category **W/L/F** vs the server and vs the category cards:

1. **Aggregate header** only included closed picks where `asset_class` / `category` was non-empty and not CRYPTO/SPORTS. Picks like **`EURUSD=X`** with **missing `asset_class`** were **excluded** from the aggregate even though **FOREX cards** included them via `matchCategory` (`=X` heuristic). That diluted or skewed aggregate WR and PnL vs what users see on the cards and vs `compute_non_crypto_performance()` (which uses `nc_asset_category_for_pick` symbol heuristics).

2. **Win / loss / flat** used strict `pnl > 0` / `< 0`. Server and the rest of the dashboard use **`FLAT_PNL_THRESHOLD` (0.01%)** / `_MIN_REALIZED_PNL_PCT` so tiny noise rounds to **flat**, matching `getResolvedTradePnl` / `net_pnl_pct` usage.

## Change

In **`audit_dashboard/template.html`** and **`index.html`** (`renderNonCryptoPanel`):

- Added **`isNonCryptoPickUnified(p)`** — true if the pick matches any non-crypto **category** via existing **`matchCategory`** (same rules as cards + server heuristics for `=X`, XAU/XAG, `=F`, etc.).
- Aggregate closed loop and **active** count use **`isNonCryptoPickUnified`**, not “non-empty `asset_class` only”.
- Recompute paths use **`getResolvedTradePnl(p)`** and **`FLAT_PNL_THRESHOLD`** for W/L/F.

## Expected result

Aggregate **WR / PnL / closed count** align with the union of non-crypto category cards (for the same filtered pick set). WR may **rise or fall** vs the old bug depending on which trades were wrongly excluded; the number reflects the **full** non-crypto book under the same rules as the server.

## Verification

- `python audit_dashboard/check_template_sync.py`
- `npx playwright test tests/audit_verified_edge_active_picks.spec.ts tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"`

**Playwright:** `audit_remote_tabs_no_errors` ignores benign **“user aborted a request”** page errors from navigation on heavy `/audit/`.

## Note

This fixes **measurement and consistency**, not underlying strategy edge. If true realized WR is still below 50% after the fix, that is a **pipeline / gate** issue, not a display bug.
