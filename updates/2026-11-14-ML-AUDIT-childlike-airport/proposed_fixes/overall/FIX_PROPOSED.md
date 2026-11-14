# ML / Pick-Trading Audit — Proposed Fixes (Overall / Cross-Cutting)

**Repo root:** /home/eaguiar2015/findtorontoevents_antigravity.ca  
**Worktree:** childlike-airport  
**Audit source:** `updates/2026-11-14-ML-AUDIT-childlike-airport.md` (read-only audit, 2026-11-14T16:04:48Z)  
**Status:** Proposed — no code changes made yet.

This document covers cross-cutting infrastructure fixes that affect every asset class (stocks, bonds, ETFs, mutual funds, forex, crypto, futures, commodities). Asset-class-specific logic belongs in the per-asset-class docs under `proposed_fixes/<class>/`.

---

## 1. Executive Summary

The ML/pick-trading system is not money-ready because the cross-cutting pick-infrastructure layer is broken in ways that corrupt every downstream consumer (dashboard, gatekeeper, consensus, resolver, backtest sync).

The root findings (read-only audit):

- `data/live_picks.db` has 129 active picks; **129/129 are ~172 days stale** (all `last_updated` = 2026-05-25T20:50:25.xxx, a single day) yet all marked ACTIVE/OPEN and never refreshed. `entry_time` ranges 2026-03-19 → 2026-05-25.
- PnL is unreliable: 8 picks have `unrealized_pnl_pct` with the sign flipped vs `pnl_pct`; 15 picks mismatch the canonical formula `(current_price - entry_price) / entry_price`.
- `asset_class` is missing for 6 DB rows; `dashboard/live_picks.json` (17 active picks) is NOT all-UNK — spot check shows CRYPTO (11), BOND (4), STOCKS (3), FOREX (1), no UNK; 6 picks are STALE (`ml_strategy_reviver`, `entry_time` 2026-07-11, ~126d).
- `pick_history` has 136 rows, all `event='REGISTERED'` — no CLOSED/EXIT/TP/SL events, so picks never resolve and can never age out.
- `data/audit_trail.db` consensus/feature/strategy-stats tables are all 0 rows (only `bt_backtest_runs`=20, `meta`=1).
- `consensus_active_picks.json` is fresh (1d) but EMPTY (0 picks) — the consensus merger produces nothing.
- ML algorithms themselves are sound: `ml_ranker_fixed.py` (chronological 80/20, ROC-AUC, isotonic calibration, leakage guards) and `ml_gatekeeper/gatekeeper.py` (trained on 3,500+ real closed picks, documents target-leakage features `forward_wr`/`strat_fwd_wr`/`eb_forward_wr`/`age_hours` with `ML_GATE_DROP_LEAKAGE` mask). `alpha_engine/asset_class.py` is the canonical single source of truth for normalization (FOREX_CODES, BOND_SYMBOLS, ETF_SYMBOLS, EQUITY_SYMBOLS, COMMODITY_SYMBOLS frozensets at lines 22–62).
- `dbpasses`: no `dbpasses.txt`; only the public keyless Pollinations info file — no secrets, nothing to fix.

Net effect: the models are fine, but the data they consume and write is stale, mislabeled, miscalculated, and unresolved. Fixing the infra layer is the gating prerequisite for any per-asset-class improvement.

---

## 2. Quick Wins (Low Effort, High Impact, Doable Now)

These require no new schema and no per-asset-class logic:

- Recompute `unrealized_pnl_pct` for all 129 active picks using the canonical signed formula (long: `(current_price - entry_price) / entry_price`; short: invert sign), and make `pnl_pct` a single source of truth so sign contradictions cannot recur.
- Refresh `current_price` + `last_checked` for all active picks via the existing price-enrichment path (`mercury2/scanner.py:127-128` already writes `round(pnl_pct, 4)` and `last_checked = now.isoformat()`).
- Backfill the 6 missing `asset_class` values in `live_picks.db` and the 17 `UNK` entries in `dashboard/live_picks.json` using `alpha_engine.asset_class.asset_class_from_symbol` (line 130) / `normalize_asset_class` (line 191) / `classify_pick_asset_class_upper` (line 263).
- Mask the silent `ab_router` import failure in `ml_gatekeeper/gatekeeper.py:25-32` so the A/B disable is logged explicitly instead of silently skipped (line 30 already prints; make it a structured warning and gate downstream dual-write on `AB_ENABLED`).
- Add a staleness guard: any active pick older than 30–60 days with no `pick_history` resolution event is flagged STALE and excluded from the active panel until refreshed or closed.

---

## 3. Proposed Fixes (Detailed, Per-Category)

### 3.1 PnL Calculation (all asset classes)

**Problem:** `unrealized_pnl_pct` sign contradicts `pnl_pct` for 8 picks; 15 picks mismatch `(current_price - entry_price) / entry_price`. `forward_trade_executor.py:100-102` already encodes the correct long/short formula pattern; `copy_trader_intel/outcome_resolver.py:252` encodes `round((current - entry) / entry, 4)`.

**Fix:**
- Single canonical function (one place) computing signed unrealized PnPct: long = `(current - entry) / entry`, short = `(entry - current) / entry`, multiplied by 100 for percent, rounded to 4 dp.
- Both `unrealized_pnl_pct` and `pnl_pct` derive from this function; `pnl_pct` is the stored source of truth and `unrealized_pnl_pct` is a recomputed view, never independently set.
- Audit every row in `live_picks.db`; correct the 8 sign contradictions and 15 mismatches.
- Apply at write path: `mercury2/scanner.py:481-485` (long/short branches) and `dashboard/generate_dashboard.py:15,24` (consumer) must read the same canonical value.

**Locations:** `data/live_picks.db` (live_picks), `mercury2/scanner.py:481-485`, `copy_trader_intel/outcome_resolver.py:252`, `forward_trade_executor.py:100-102`, `dashboard/generate_dashboard.py:15,24`.

### 3.2 Staleness Refresh (all asset classes)

**Problem:** 129/129 active picks are ~172 days stale (entry_time/last_checked = 2026-05-24/25) yet marked ACTIVE/OPEN. Bond/ETF feeds are fresh (2d) but `live_picks.db` and `stocksunify2_active_picks.json` (79d) are stale.

**Fix:**
- Re-run price enrichment (`current_price`, `unrealized_pnl_pct`, `last_checked`) for all 129 active picks on every refresh cycle.
- Retire/close picks older than 30–60 days with no activity and no resolution event; do not leave them ACTIVE/OPEN indefinitely.
- Align refresh schedules: bond (active_picks_bond.json, 2d), ETF (active_picks_etf.json, 2d), consensus (1d), and live_picks.db must all refresh on the same cadence.
- Wire into `tools/db_freshness_check.py` (DB freshness guardian) so staleness is a CI gate, not a post-hoc audit finding.

**Locations:** `data/live_picks.db`, `dashboard/live_picks.json`, `active_picks_bond.json`, `active_picks_etf.json`, `stocksunify2_active_picks.json`, `tools/db_freshness_check.py`, `mercury2/scanner.py:127-128`.

### 3.3 asset_class Backfill (all asset classes)

**Problem:** 6 DB rows lack `asset_class`; `dashboard/live_picks.json` has 17 picks — spot check shows CRYPTO (11), BOND (4), STOCKS (3), FOREX (1), **no UNK**; Active picks are dominated by UNK (108/273 deduped) and crypto; closed picks dominated by CRYPTO with 6,953 UNK. Mutual funds are absent entirely (zero active, zero closed).

**Fix:**
- Use `alpha_engine/asset_class.py` as the single source of truth: `asset_class_from_symbol` (line 130), `normalize_asset_class` (line 191), `classify_pick_asset_class_upper` (line 263), `is_crypto` (line 269). FOREX_CODES/BOND_SYMBOLS/ETF_SYMBOLS/EQUITY_SYMBOLS/COMMODITY_SYMBOLS frozensets at lines 22–62.
- Backfill the 6 missing DB rows and 17 dashboard UNK rows.
- Add a `MUTUAL_FUND` class + symbol set to `asset_class.py` so mutual funds can be tracked (currently absent from all DBs and `alpha_engine/`); extend DB schema and picker to include it. No mutual fund strategies exist yet — that is a per-asset-class task, not here.
- Normalize case/duplicates: active vs closed cross-reference shows mixed-case duplicates (crypto 66 vs CRYPTO 6,400 vs crypto 1,348).

**Locations:** `alpha_engine/asset_class.py:22-62,125,130,191,263,269`, `data/live_picks.db` (metadata JSON), `dashboard/live_picks.json`.

### 3.4 Pick Lifecycle / Resolution (all asset classes)

**Problem:** `pick_history` has 136 rows, all `event='REGISTERED'`; no CLOSED/EXIT/TP/SL events. Picks are registered but never resolved, so active picks can never age out and the resolver has nothing to act on.

**Fix:**
- Emit CLOSED/EXIT/TP/SL events into `pick_history` when a pick hits TP/SL/time-exit or is manually closed.
- `audit_trail/universal_pick_resolver.py` (Active pick TP/SL/time exit resolver) is the write path for resolution events; ensure it writes `pick_history` rows with event type, exit price, realized PnPct, and timestamp.
- Active picks older than 30–60 days with no resolution event transition to STALE/EXPIRED rather than staying ACTIVE/OPEN.
- Store realized `pnl_pct` on close so closed-pick PnL (currently 16,176/16,771 closed picks have a pnl field) stays consistent.

**Locations:** `data/live_picks.db` (pick_history), `audit_trail/universal_pick_resolver.py`, `copy_trader_intel/outcome_resolver.py:252`.

### 3.5 audit_trail.db Population (all asset classes)

**Problem:** All consensus/feature/strategy-stats tables are 0 rows: consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events, filter_log, bt_backtest_trades. Only `bt_backtest_runs` (20) and `meta` (1) have data. No audit evidence is being recorded.

**Fix:**
- Populate `consensus_picks`, `feature_edge_snapshots`, `symbol_strategy_stats`, `strategy_stats`, `raw_picks`, `audit_events`, `filter_log`, `bt_backtest_trades` from the existing scan/gatekeeper/resolver outputs.
- `alpha_engine/audit_sync.py` (portfolio data MySQL sync) is the sync path; ensure it writes to `data/audit_trail.db` tables, not just `bt_backtest_runs`.
- Every consensus run, feature computation, and strategy stat must leave an audit row so the dashboard summary cards and per-class stats have a source.

**Locations:** `data/audit_trail.db`, `alpha_engine/audit_sync.py`, `audit_trail/dashboard_generator.py`, `ml_gatekeeper/gatekeeper.py`.

### 3.6 Consensus Merger (all asset classes)

**Problem:** `consensus_active_picks.json` is fresh (1d) but EMPTY (0 picks). The consensus merger produces nothing, so the consensus dashboard page and cross-system agreement signals are absent.

**Fix:**
- Investigate why the consensus merger yields 0 picks: check input feeds (per-class active picks), the merger filter thresholds, and asset_class normalization (UNK picks may be dropped by the merger).
- Ensure the merger consumes normalized, non-UNK, non-stale picks and writes `consensus_active_picks.json` with a non-empty result when qualifying picks exist.
- Tie the empty-result case to an audit event in `audit_trail.db` so silence is detectable.

**Locations:** `copy_trader_intel/data/consensus_active_picks.json`, `copy_trader_intel/non_crypto_consensus.py`, `alpha_engine/prediction_market_consensus.py`, `alpha_engine/contrarian_consensus.py`, `data/audit_trail.db` (audit_events).

### 3.7 dbpasses / Secrets

**Problem:** No `dbpasses.txt`; only `dbpasses_ASK_MISSINGpollinations2026-11-03.txt` (public keyless Pollinations info, no secrets).

**Fix:** Nothing to fix. No credential exposure. Do not create a `dbpasses.txt` unless the user explicitly requests secret storage.

**Locations:** none.

### 3.8 Bugs Found in Recently Modified Files (during peer review)

**sync_all_picks_to_mysql.py** (`sync_all_picks_to_mysql.py`) — two actual bugs:

- **Bug A:** `process_sqlite_source` inserts into `bt_backtest_trades` for **every** row, including rows that fail the `if entry and entry > 0` guard — producing backtest trade rows with null/zero `entry_price` for invalid picks (lines 873-884).
- **Bug B:** The `pnl *= 100` heuristic (lines 660-661, 858-859) can corrupt a legitimately small percent value (e.g. `0.5` meaning 0.5% → becomes `50`).
- **Fix:** Guard the `bt_backtest_trades` insert behind the same `entry > 0` check; replace the blind `pnl *= 100` with an explicit percent/decimal detection (only scale if value is clearly a decimal fraction, e.g. `abs(pnl) < 1` AND source metadata indicates decimal-not-percent).
- **Impact:** corrupts backtest PnL data piped into `audit_trail.db` `bt_backtest_trades`.

**price_realism_check.py** (`price_realism_check.py`):

- **Bug:** hardcoded `expected_2026_prices` dict (e.g. AAPL 150–300, NVDA 400–1200). Prices outside these ranges are labeled "UNREALISTIC/SYNTHETIC" — a baked-in stale-data assumption that misclassifies real data after splits, reverse splits, or normal price appreciation.
- **Fix:** Replace hardcoded ranges with a dynamic lookback window (e.g. price within 50–200% of the symbol's trailing 26-week range from market data) plus an optional user-override config file.
- **Impact:** false "synthetic data" flags on legitimately high-priced equities/crypto.

### 3.9 Out of Scope for This Document (per-asset-class docs)

- Mutual fund strategy implementation (none exist in `alpha_engine/`).
- Per-asset-class scanner thresholds, gatekeeper class weights, and promotion gates.
- `ml_ranker_fixed.py` and `ml_gatekeeper/gatekeeper.py` core logic (both reviewed sound); only the `ab_router` masking and leakage-feature handling are touched here as cross-cutting.

---

## 4. Implementation Order (Priority)

1. **P0 — PnL calc + staleness refresh** (blocks everything downstream): recompute signed `unrealized_pnl_pct`/`pnl_pct` for all 129 active picks; refresh `current_price`/`last_checked`; flag >30–60 day stale picks.
2. **P0 — asset_class backfill**: backfill 6 DB rows + 17 dashboard UNK rows via `alpha_engine/asset_class.py`; add MUTUAL_FUND class/symbol set + schema.
3. **P0 — pick lifecycle**: emit CLOSED/EXIT/TP/SL into `pick_history`; close/expire stale picks via `audit_trail/universal_pick_resolver.py`.
4. **P1 — audit_trail population**: write consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events, filter_log, bt_backtest_trades via `alpha_engine/audit_sync.py`.
5. **P1 — consensus merger**: fix zero-pick output in `consensus_active_picks.json`; gate on normalized non-stale inputs.
6. **P2 — dbpasses**: nothing (no secrets).
7. **P2 — gatekeeper hygiene**: explicit A/B disable warning at `ml_gatekeeper/gatekeeper.py:25-32`; `ML_GATE_DROP_LEAKAGE` mask already documented.
8. **P2 — sync_all_picks_to_mysql.py**: guard `bt_backtest_trades` insert behind `entry > 0` check; replace blind `pnl *= 100` with decimal/percent detection.
9. **P2 — price_realism_check.py**: replace hardcoded `expected_2026_prices` dict with dynamic trailing 26-week range lookback.

Do not start per-asset-class work until P0 is complete; stale/mislabeled data invalidates per-class results.

---

## 5. Verification Steps

For each fix, confirm:

**PnL calc:**
- Recompute `unrealized_pnl_pct` for all 129 rows in `live_picks.db` using `(current_price - entry_price) / entry_price` (long) / inverted (short); 0 sign contradictions vs `pnl_pct`, 0 mismatches.
- `dashboard/generate_dashboard.py:15,24` displays the canonical value.

**Staleness:**
- `MAX(last_updated)` across `live_picks.db` within 24h of refresh (`last_updated` is top-level; `last_checked` lives in `metadata` JSON); no ACTIVE/OPEN pick older than 30–60 days without a `pick_history` resolution row.
- `tools/db_freshness_check.py` passes (freshness CI gate).
- `sync_all_picks_to_mysql.py`: 0 `bt_backtest_trades` rows with null/zero `entry_price`; `pnl` values not spuriously scaled by 100x (spot check vs source picks).
- `price_realism_check.py`: no hardcoded `expected_2026_prices`; price realism uses dynamic trailing range instead.

**asset_class:**
- 0 rows in `live_picks.db` missing `asset_class`; `dashboard/live_picks.json` has 0 `asset_class='UNK'` active picks.
- `alpha_engine.asset_class.asset_class_from_symbol` (line 130) returns a non-UNK class for each sample symbol across all classes; MUTUAL_FUND class present in `asset_class.py`.

**Pick lifecycle:**
- `pick_history` contains CLOSED/EXIT/TP/SL rows after a resolution run; count > 0 and events have exit price + realized PnPct + timestamp.
- Active picks older than 30–60 days with no history row are STALE/EXPIRED, not ACTIVE/OPEN.

**audit_trail:**
- `SELECT COUNT(*)` from each of consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events, filter_log, bt_backtest_trades > 0 after a sync run.
- `bt_backtest_runs` (20) + `meta` (1) still intact (no regression).

**Consensus:**
- `consensus_active_picks.json` contains > 0 picks when qualifying normalized active picks exist; empty result writes an audit event to `audit_trail.db`.

**ML (no regression):**
- `ml_ranker_fixed.py` harness still passes (chronological 80/20, ROC-AUC, isotonic calibration, train-test gap guard).
- `ml_gatekeeper/gatekeeper.py` `ML_GATE_DROP_LEAKAGE` mask still drops `forward_wr`/`strat_fwd_wr`/`eb_forward_wr`/`age_hours`; `ab_router` import failure logged explicitly (line 30).

**dbpasses:**
- Confirm no `dbpasses.txt` created; no secrets introduced.

Verification command pattern: `python3 -c "import py_compile; py_compile.compile('<file>', doraise=True)"` for any edited `.py`; then run the relevant DB/JSON queries above.

---

## 6. Files Touched

- `data/live_picks.db` — live_picks (PnL, current_price, last_checked, asset_class metadata), pick_history (resolution events)
- `data/audit_trail.db` — consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events, filter_log, bt_backtest_trades (population)
- `dashboard/live_picks.json` — asset_class present (CRYPTO/BOND/STOCKS/FOREX, no UNK); 6 stale ml_strategy_reviver picks to refresh
- `alpha_engine/asset_class.py:22-62,125,130,191,263,269` — symbol sets + normalization (single source of truth); add MUTUAL_FUND class/symbol set
- `alpha_engine/audit_sync.py` — portfolio/MySQL sync path writing audit_trail tables
- `audit_trail/universal_pick_resolver.py` — TP/SL/time-exit resolution write path into pick_history
- `audit_trail/dashboard_generator.py` — dashboard payload consumer of audit_trail data
- `mercury2/scanner.py:127-128,481-485` — price enrichment + long/short PnL calc pattern
- `copy_trader_intel/outcome_resolver.py:252` — resolved PnPct formula `round((current - entry) / entry, 4)`
- `copy_trader_intel/data/consensus_active_picks.json` — consensus output (fix zero-pick)
- `copy_trader_intel/non_crypto_consensus.py`, `alpha_engine/prediction_market_consensus.py`, `alpha_engine/contrarian_consensus.py` — merger inputs/filters
- `ml_gatekeeper/gatekeeper.py:25-32` — ab_router import masking; `ML_GATE_DROP_LEAKAGE` leakage-feature mask
- `dashboard/generate_dashboard.py:15,24` — PnL display consumer
- `tools/db_freshness_check.py` — freshness CI gate (staleness)
- `forward_trade_executor.py:100-102` — canonical long/short PnPct formula reference
- `sync_all_picks_to_mysql.py` — Bug A (bt_backtest_trades null entry_price insert) + Bug B (pnl *= 100 corruption)
- `price_realism_check.py` — hardcoded expected_2026_prices dict → dynamic range lookback

File written: `/home/eaguiar2015/findtorontoevents_antigravity.ca/updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/overall/FIX_PROPOSED.md`
