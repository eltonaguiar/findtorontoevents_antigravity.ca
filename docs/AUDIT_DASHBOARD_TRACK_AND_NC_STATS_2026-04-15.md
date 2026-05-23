# Audit dashboard: Track column, non-crypto stats, and related fixes (2026-04-15)

## Summary

This note documents fixes for **empty Track** cells, **Track matching FWD WR** (expected in some cases), and **non-crypto performance cards** under-counting or mis-aligning with feeder data when `asset_class` was missing or micro-futures were split out.

## 1. Track column empty while FWD WR showed a value

### Cause

- The **FWD WR** cell uses `strat_fwd_wr` with a fallback to `pick.forward_wr` and normalizes 0–1 fractions to percent.
- The **Track** (`_ic_track`) cell only used `strat_fwd_wr` and **hid the cell** when `track_level === 'none'`, even if `forward_wr` was populated.
- **Symbol-bold** Track also required `track_level === 'symbol'`, which could disagree with `sym_track_total` / `sym_track_wr` from the symbol track map.

### Fix

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html`

- **Bold (symbol-specific):** `sym_track_total >= 3` and `sym_track_wr` present (no dependency on `track_level` for display).
- **Italic (strategy-wide):** `strat_fwd_wr`, else `forward_wr`, with the same **fraction → percent** normalization as FWD WR (`> 0 && <= 1.5` → multiply by 100).
- **Removed** the rule that blanked Track whenever `track_level === 'none'`.
- **Regime / IC tooltip** (`_ic_regime`): `track_wr` line now uses the same effective strategy WR and trade count (`strat_fwd_trades` or `forward_trades`) so the tooltip matches the Track column.

**File:** `audit_trail/dashboard_generator.py`

- **Fallback** from universal forward stats into `strat_fwd_wr` / `strat_fwd_trades` / `track_level = strategy` when the leaderboard row is sparse: threshold lowered from **5+** to **3+** closed trades so Track aligns with the same forward ledger the dashboard already uses for smaller samples.

## 2. Track sometimes equals FWD WR (e.g. EURJPY=X)

### Explanation (not a bug)

- **Track** shows **symbol-specific** WR only when there are **at least three** resolved closes for that **strategy + symbol** pair.
- For many **forex** pairs, that symbol-specific sample stays thin; the UI then shows **strategy-wide** WR (italic), which is the **same statistic** as **FWD WR** when both are sourced from the strategy forward ledger.
- Lack of “proper history” for that **exact symbol** is exactly why the two columns match.

Copy in **colTips** / column metadata was updated to state this explicitly.

## 3. Non-crypto stats (Futures, ETF, Commodities, Bonds) looked “wrong”

### Causes

1. **`compute_non_crypto_performance`** (`nc_asset_category_for_pick`) returned `None` when `asset_class` / `category` were empty and the symbol was not caught by `=X`, `XAU`/`XAG`, or `=F` heuristics — e.g. plain **ETF tickers**, **equities**, **bonds** without a Yahoo-style suffix.
2. **`MICRO_FUTURES`** was not mapped into the **Futures** bucket, so micro contracts could be excluded from the Futures card while client drilldowns expected them under futures.

### Fix

**File:** `audit_trail/dashboard_generator.py` — `nc_asset_category_for_pick`

- Map **`MICRO_FUTURES` → `FUTURES`** (same as treating micros as futures for the non-crypto summary).
- After existing heuristics, **fallback** to `audit_trail.asset_classification.classify_asset(symbol)` for non-crypto buckets; skip `CRYPTO`, `MEME`, `UNKNOWN`.

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html` — `matchCategory`

- Futures matching now includes **`ac === 'MICRO_FUTURES'`** so client-side category filtering matches server buckets.

### Note on “384 closed commodities, 0 active”

- **Closed** counts come from resolved history; **active** counts come from the current active feed. It is valid for a class to have many closed trades and **no** open picks if scanners are not emitting new actives for that class. The fixes above do not invent actives; they correct **classification** so actives that exist are counted in the right card.

## 4. Related earlier session (RSI / Vol)

- **USDC** spot pairs were added alongside **USDT** for Binance lazy-fill and bulk RSI enrichment (see deploy / template / `dashboard_generator` RSI block). Not repeated in detail here.

## Files touched

| File | Change |
|------|--------|
| `audit_trail/dashboard_generator.py` | `nc_asset_category_for_pick` classify fallback + `MICRO_FUTURES` → FUTURES; forward fallback threshold 3+ |
| `audit_dashboard/template.html` | `_ic_track`, `_ic_regime`, `matchCategory`, colTips |
| `audit_dashboard/index.html` | Same as template |
| `docs/AUDIT_DASHBOARD_TRACK_AND_NC_STATS_2026-04-15.md` | This document |

## Deploy

After merge, run the usual audit deploy (e.g. `deploy_audit_only` or full FTP deploy) so live `/audit/` picks up `template.html` / `index.html` and the next generated `dashboard_data.json` reflects the Python bucket changes.
