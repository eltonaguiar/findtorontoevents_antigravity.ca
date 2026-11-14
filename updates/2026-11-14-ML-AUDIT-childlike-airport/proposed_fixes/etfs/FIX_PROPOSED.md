# ETF Asset Class — Proposed Fixes (ML/Pick-Trading Audit)

**Class:** ETF | **Status:** PROPOSED | **Date:** 2026-11-14 | **Audit:** childlike-airport ML audit
**Source of truth:** `alpha_engine/asset_class.py` (canonical symbol→class normalization)

---

## 1. ETFs-specific findings

**Fresh feed vs stale DB (sync gap)**
- `alpha_engine/data/active_picks_etf.json` is FRESH: generated `2026-11-12T18:17:06Z` (2 days old), 16 picks, `source_system` = `etf_emitter_spike`, `category` = `etf`, `asset_class` = `ETF`.
- Strategies emitting: `etf_dual_momentum`, `etf_sector_momentum`, `etf_faber_tactical`, `etf_rsi2_pullback`, `etf_sector_dual_momentum`, `etf_cross_sectional_momentum`.
- Symbols in feed: SOXX, KWEB, XLV, XLF, XLE, SPY, QQQ, EFA, XLC (+ cross-sectional XLE, XLK, QQQ).
- These picks are NOT synced into `data/live_picks.db` — the live_picks table has no ETF footprint from `etf_scanner`/`etf_emitter_spike`.

**Mislabeled asset class (STOCKS / EQUITY / UNKNOWN)**
- `data/live_picks` schema (`live_picks` table) has **no `asset_class` column**. Asset class is derived at query/display time from `symbol` via `alpha_engine.asset_class.normalize_asset_class()` / `asset_class_from_symbol()`.
- `ETF_SYMBOLS` frozenset (`alpha_engine/asset_class.py:37-53`) is missing feed symbols **KWEB** and **VLUE**.
  - `asset_class_from_symbol("KWEB")` → `unknown` → default fallback `equity` (mislabeled as EQUITY).
  - `asset_class_from_symbol("VLUE")` → `unknown` → default fallback `equity` (mislabeled as EQUITY).
- Confirmed correct mappings (spot check): SOXX/XLV/SPY/QQQ/XLF/XLE/EFA/XLC → `etf`; TLT/IEF → `bond` (bond ETFs intentionally classed as bond, checked before ETF set).
- `live_picks` asset-class breakdown cannot be produced by `GROUP BY asset_class` because the column does not exist; ETF picks are currently buried under STOCKS/EQUITY/UNKNOWN derived rows.

**ETF strategy modules present (alpha_engine/):**
`etf_scanner.py`, `etf_strategies.py`, `etf_sector_momentum_rotation.py`, `etf_quality_filters.py`, `etf_risk_parity.py`, `etf_vix_regime_rotation.py`, `etf_country_rotation.py`, `etf_managed_futures_proxy.py`, `etf_economic_momentum.py`, `etf_rebalancer.py`, `etf_strategy_harness.py`, `etf_vix_term_structure.py`.

---

## 2. Quick wins for ETFs

- Add missing feed symbols **KWEB** and **VLUE** to `ETF_SYMBOLS` in `alpha_engine/asset_class.py:37-53` so they classify as `etf` instead of defaulting to `equity`.
- Run `etf_scanner` once with `--merge` to backfill `active_picks.json` from the fresh `active_picks_etf.json` (16 picks) so the dashboard/live panel reflects current ETF signals.
- Add a `generated_at`-freshness guard: reject `active_picks_etf.json` older than 48h before merge (stale-feed guard).
- Surface an ETF row in the per-class active-picks floor (mirror BOND/COMMODITY/FOREX panels) so ETF is no longer "not separately listed."

---

## 3. Proposed fixes for ETFs

### 3.1 Sync `active_picks_etf.json` into `live_picks.db`
- **File:** `alpha_engine/etf_scanner.py` → `_merge_into_active_picks()` (currently merges into `active_picks.json`, not SQLite).
- Add a new merge target: write each ETF pick into `data/live_picks` table `live_picks(id, symbol, strategy, system, side, entry_price, take_profit, stop_loss, current_price, unrealized_pnl_pct, entry_time, last_updated, bars_held, status, metadata)`.
- Map: `id` (existing md5 `etf-...`), `symbol`, `strategy`, `system` = `source_system` (`etf_emitter_spike` / `etf_scanner`), `side` = `direction`/`signal_type` (LONG/SHORT), `entry_price`, `take_profit`, `stop_loss`, `status` = `OPEN`→`ACTIVE`, `entry_time` = `timestamp`, `metadata` = JSON blob carrying `category`, `asset_class`, `confidence`, `risk_reward`, `extra`, `reason`, `timeframe`.
- De-dupe on `(id, system)` (existing UNIQUE constraint) — `INSERT OR REPLACE` keyed by id+system so re-runs refresh rather than duplicate.
- Because `live_picks` has no `asset_class` column, store `asset_class="ETF"` and `category="etf"` inside `metadata` and add a query-time helper that reads `metadata.asset_class` when present, falling back to `asset_class_from_symbol(symbol)`.

### 3.2 Correct asset_class labels via `alpha_engine.asset_class`
- **File:** `alpha_engine/asset_class.py` → `ETF_SYMBOLS` (line 37-53).
  - Add `KWEB`, `VLUE` (and any other feed symbols missing from the frozenset).
- Keep bond-ETF ordering: `BOND_SYMBOLS` checked before `ETF_SYMBOLS` so TLT/IEF remain `bond`, not `etf`.
- Add unit assertions in `tests/` (or a one-off validation script) that every symbol in `active_picks_etf.json` resolves to `etf` via `normalize_asset_class` / `classify_pick_asset_class_upper`.
- Audit dashboard / per-class queries should call `classify_pick_asset_class_upper(pick)` on each `live_picks` row (merging `metadata.asset_class` when present) instead of relying on a nonexistent `asset_class` column.

### 3.3 Refresh PnL for ETF picks
- Run the outcome resolver / MTM refresh against the newly-synced ETF rows so `unrealized_pnl_pct` / `current_price` are populated (currently `None` for zombies per audit).
- **File:** `audit_trail/universal_pick_resolver.py` (TP/SL/time exit resolver) — ensure ETF rows (`system='etf_scanner'`) are included in the resolution loop, not skipped.
- Backfill `pick_history` events for ETF picks so age/PnL metrics display correctly on the dashboard.

### 3.4 Populate `strategy_stats` for ETF strategies
- Aggregate per-strategy stats (n, win_rate, avg_r, PF, cum_pnl) for `etf_*` strategies from resolved ETF picks.
- Write to the strategy_stats store (mirror how other classes register strategy_stats) so the ETF class exits "no stats" state and can be scored/gated like STOCKS/CRYPTO.

---

## 4. Verification steps

1. `python3 -c "from alpha_engine.asset_class import asset_class_from_symbol; [print(s, asset_class_from_symbol(s)) for s in ['KWEB','VLUE','SOXX','XLV','TLT']]"` → KWEB/VLUE must return `etf`; TLT must return `bond`.
2. `python3 -m alpha_engine.etf_scanner --merge` → exits 0, `active_picks.json` gains ETF rows, `LAST_RUN_DIAGNOSTICS` loaded ratio >= 0.5 (no `::error::DATA FETCH FAILURE`).
3. SQLite check: `SELECT COUNT(*) FROM live_picks WHERE system='etf_scanner'` (or `metadata LIKE '%"asset_class":"ETF"%'` after sync) → should equal 16 after first sync.
4. `SELECT system, COUNT(*) FROM live_picks GROUP BY system` → ETF system present; no duplicate `(id, system)` violations on re-run.
5. Per-class query: every ETF pick resolves to uppercase `ETF` via `classify_pick_asset_class_upper`; zero ETF-pick rows resolve to `EQUITY`/`UNKNOWN`.
6. Resolver check: ETF rows get `current_price`/`unrealized_pnl_pct` populated and `pick_history` events written; strategy_stats for `etf_*` strategies non-empty.

---

## 5. Repo paths touched

- `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/etfs/FIX_PROPOSED.md` (this document)
- `alpha_engine/asset_class.py` — `ETF_SYMBOLS` frozenset (+ KWEB, VLUE)
- `alpha_engine/etf_scanner.py` — add SQLite `live_picks` merge target + freshness guard
- `alpha_engine/data/active_picks_etf.json` — source feed (read-only input to sync)
- `alpha_engine/data/active_picks.json` — existing merge target (unchanged behavior, keep)
- `data/live_picks.db` (`live_picks`, `pick_history` tables) — sync target; no `asset_class` column → store class in `metadata`
- `audit_trail/universal_pick_resolver.py` — include `etf_scanner` system in resolution loop
- `alpha_engine/data/scanner_output/active_picks_etf.json` — alternate feed path referenced by scanner `ETF_PICKS_PATH`
- Tests: new/updated assertions for ETF symbol classification + sync de-dupe

---

**File written:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/etfs/FIX_PROPOSED.md`
