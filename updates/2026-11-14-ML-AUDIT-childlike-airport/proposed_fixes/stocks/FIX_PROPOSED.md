# FIX_PROPOSED.md — STOCKS (EQUITY) Asset Class

**Date:** 2026-11-14  
**Asset class:** STOCKS / EQUITY  
**Source audit:** ML-AUDIT childlike-airport session (2026-11-14)

## 1. Stocks-specific findings

- `live_picks.db`: only 5 active stock picks observed (AMZN, AAPL, QQQ among them), all STALE ~172 days (opened 2026-05-25), still marked ACTIVE with no resolution.
- `dashboard/live_picks.json`: asset_class present (CRYPTO/BOND/STOCKS/FOREX, no UNK) — stocks among the classified picks; asset class never backfilled at ingest time for some rows.
- `stocksunify2_active_picks.json`: 14 equity picks, STALE ~79 days (2026-08-26), all 'STRONG BUY'/BUY, scores 60-100, no `current_price` refresh, no PnL updates.
- Closed picks: STOCKS has only 1 closed pick vs 6,400 CRYPTO — the stocks pipeline produces almost no resolved outcomes (no TP/SL/time exits).
- `alpha_engine/asset_class.py:55` `EQUITY_SYMBOLS` frozenset (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, etc.) exists as the canonical normalization source but is not used to backfill `asset_class` on existing picks.
- ML: `ml_ranker_fixed.py` is sound; `ml_gatekeeper ASSET_CLASS_MAP` EQUITY:2 is correct — no ML-layer changes needed for stocks.

## 2. Quick wins for stocks (low effort, high impact)

- Backfill `asset_class` = 'EQUITY' for all UNK stock picks in `live_picks.db`, `dashboard/live_picks.json`, and `stocksunify2_active_picks.json` using `alpha_engine.asset_class.EQUITY_SYMBOLS` as the canonical source.
- Refresh `current_price` and recompute `unrealized_pnl` for the 5 stale active stock picks via `audit_trail/fetch_stock_prices.py` (server-side stock price fetcher).
- Add a staleness guard so picks older than a configurable max age (e.g. 30d) are auto-flagged for exit instead of staying ACTIVE indefinitely.
- Register `alpha_engine/equity_breakout_scanner.py`, `equity_bb_zscore_mr.py`, `equity_rsi_divergence_mr.py`, `equity_pead_strategy.py`, `equity_factor_model.py`, `equity_insider_buying.py`, `equity_sector_rotation*.py` in the production scanner registry if not already wired.

## 3. Proposed fixes for stocks

### 3.1 Refresh current_price/unrealized_pnl for the 5 stale stock picks

- Targets: AMZN, AAPL, QQQ + the other 2 stale active stock picks in `live_picks.db`.
- Tool: `audit_trail/fetch_stock_prices.py` (fetches live stock prices server-side).
- Action: fetch current price for each symbol, update `current_price`, recompute `unrealized_pnl = (current_price - entry_price) / entry_price`, set `last_updated` timestamp (top-level column; `last_checked`/`pnl_pct` live in `metadata` JSON).
- Files touched: `live_picks.db` (SQLite), potentially `dashboard/live_picks.json` if regenerated from DB.

### 3.2 Backfill asset_class via alpha_engine.asset_class

- Source of truth: `alpha_engine/asset_class.py:55` `EQUITY_SYMBOLS` frozenset.
- Normalization: map each stock symbol to uppercase, strip `-USD`/suffixes if present, look up in `EQUITY_SYMBOLS`.
- Apply to: `live_picks.db` (all rows with `asset_class IS NULL OR 'UNK'`), `dashboard/live_picks.json`, `stocksunify2_active_picks.json`.
- Add an assert/test that every stock symbol in the active-picks set resolves to EQUITY (no UNK remains).

### 3.3 Emit CLOSED/EXIT events for aged-out picks

- Rule: any active stock pick older than max_age_days (default 30) without a TP/SL hit is force-closed at last known price with exit_reason='TIME_EXIT' or 'STALE_AGEOUT'.
- Records `closed_at`, `exit_price`, `realized_pnl`, `exit_reason`; flips status ACTIVE -> CLOSED.
- Reuse the existing resolver path: `audit_trail/universal_pick_resolver.py` (active pick TP/SL/time exit resolver).
- Targets: the 5 stale active stock picks (~172 days old) plus the 14 stale equity picks in `stocksunify2_active_picks.json` (~79 days old).
- Expected outcome: the 5 stale active stock picks plus the 14 stale equity picks in `stocksunify2_active_picks.json` (~79 days old) age out to CLOSED/EXPIRED, giving the pipeline resolved STOCKS/EQUITY outcomes where previously only 1 closed pick existed.

### 3.4 Re-run equity scanners to replenish the stocks pipeline

- Run the equity strategy set: `equity_breakout_scanner.py`, `equity_bb_zscore_mr.py`, `equity_rsi_divergence_mr.py`, `equity_pead_strategy.py`, `equity_factor_model.py`, `equity_insider_buying.py`, `equity_sector_rotation.py`, `equity_sector_rotation_momentum.py`.
- Orchestrator: `alpha_engine/production_scanner.py` (production scan orchestrator).
- Gate new picks through `ml_ranker_fixed.py` (sound) then `ml_gatekeeper` (ASSET_CLASS_MAP EQUITY:2).
- Write new picks to `live_picks.db` with `asset_class='EQUITY'` and a fresh `opened_at` timestamp.

## 4. Verification steps

- Query `live_picks.db`: since `asset_class` lives in `metadata` JSON (not a top-level column), backfill reads `metadata` via Python `asset_class_from_symbol()`; after backfill, 0 UNK rows; all stocks show EQUITY.
- Confirm `current_price` and `unrealized_pnl` are non-null and refreshed (`last_updated` top-level / `last_checked` in `metadata` within last 24h) for the 5 formerly-stale stock picks.
- Confirm closed-pick count for STOCKS/EQUITY increased from 1 to ~19+ with `exit_reason` populated.
- Run `python3 alpha_engine/production_scanner.py --asset-class EQUITY` and confirm new active EQUITY picks are emitted with `asset_class='EQUITY'`.
- Run ML gatekeeper on new equity picks: `ASSET_CLASS_MAP` EQUITY:2 accepts; no rejects.
- Add a regression test asserting no `asset_class='UNK'` remains for symbols present in `EQUITY_SYMBOLS`.

## 5. Repo paths touched

- `data/live_picks.db` — stale stock pick rows, price/pnl refresh, age-out closes
- `dashboard/live_picks.json` — asset_class backfill, price/pnl refresh
- `stocksunify2_active_picks.json` — asset_class backfill, age-out closes
- `alpha_engine/asset_class.py` — EQUITY_SYMBOLS canonical source (read-only reference)
- `audit_trail/fetch_stock_prices.py` — current_price refresh tool
- `audit_trail/universal_pick_resolver.py` — CLOSED/EXIT event emission
- `alpha_engine/production_scanner.py` — re-run equity scanners
- `ml_ranker_fixed.py` — ML ranking (no change, sound)
- `ml_gatekeeper/gatekeeper.py` — ASSET_CLASS_MAP EQUITY:2 (no change)
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_breakout_scanner.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_bb_zscore_mr.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_rsi_divergence_mr.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_pead_strategy.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_factor_model.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_insider_buying.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_sector_rotation.py` — re-run
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/equity_sector_rotation_momentum.py` — re-run
