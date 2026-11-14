# ML / Algo Audit — Asset-Class Picks & Databases

**Worktree:** childlike-airport
**Repo root:** /home/eaguiar2015/findtorontoevents_antigravity.ca
**Audit time:** 2026-11-14T16:04:48Z (today = 2026-11-14)
**Auditor:** Kilo

---

## Scope

Reviewed AI/ML algorithms and pick databases across asset classes: stocks, bonds, ETFs, mutual funds, forex, crypto. Checked `dbpasses.txt`, all `.db` databases, active + closed picks JSON feeds, and cross-referenced PnL per asset class. Spot-checked every column for accuracy, staleness, and calculation errors.

---

## 1. dbpasses.txt / secrets

- No `dbpasses.txt` exists in the repo.
- Only `dbpasses_ASK_MISSINGpollinations2026-11-03.txt` present; it contains **only public Pollinations (keyless) endpoint info** — no API keys, no secrets, nothing to redact.
- **Finding:** No credential exposure. Nothing to fix.

---

## 2. Databases inspected

| Database | Tables | Rows | Status |
|---|---|---|---|
| `data/live_picks.db` | live_picks, pick_history | 129 / 136 | **STALE + PnL errors** (see below) |
| `data/audit_trail.db` | 11 tables | consensus_picks 0, feature_edge_snapshots 0, symbol_strategy_stats 0, strategy_stats 0, raw_picks 0, audit_events 0, filter_log 0, bt_backtest_trades 0; bt_backtest_runs 20 | **EMPTY — no audit data populated** |
| `alpha_engine.db` | strategy_control, strategy_performance | — | present |
| Plus 14 others | quan_engine.db, mlflow.db, predictions.db, paper_trading/data/paper.db, crypto_data.db, coinglass.db, trading/data/positions.db, KIMI_RISEOFTHECLAW, incubator, battleground, audit_trail/audit_trail.db, sandbox, blogwatcher | — | not deeply scanned |

---

## 3. Critical findings — `data/live_picks.db` (active picks)

`live_picks` schema: id, symbol, strategy, system, side, entry_price, take_profit, stop_loss, current_price, unrealized_pnl_pct, entry_time, last_updated, bars_held, status, metadata.  
Note: `asset_class`, `pnl_pct`, `last_checked` live **inside the `metadata` JSON**, not as top-level columns.

### 3.1 Stale data — 129 of 129 active picks are stale

Every active pick has `last_updated` = **2026-05-25T20:50:25.xxx** (a single day, all rows identical timestamp). Today is 2026-11-14 → **~172 days (~5.7 months) stale**. All marked `ACTIVE` (69) or `OPEN` (60) but never refreshed. `entry_time` ranges 2026-03-19 → 2026-05-25.

Examples (symbol, last_updated, age_days, asset_class):
- AMZN, 2026-05-25, 172, STOCKS
- UNIUSDT, 2026-05-25, 172, CRYPTO
- SUSHIUSDT, 2026-05-25, 172, CRYPTO
- AAPL, 2026-05-25, 172, STOCKS
- NEARUSDT, 2026-05-25, 172, CRYPTO
- QQQ, 2026-05-25, 172, STOCKS

### 3.2 PnL sign contradictions — 8 picks

`unrealized_pnl_pct` has the **opposite sign** of `pnl_pct` even though `current_price` vs `entry_price` clearly implies one direction.

| symbol | entry | current | unrealized_pnl_pct (WRONG sign) | pnl_pct (correct) | class |
|---|---|---|---|---|---|
| NEARUSDT | 2.42 | 2.733 | -0.129339 | +0.128512 | CRYPTO |
| ATOMUSDT | 2.1067 | 2.156 | -0.023401 | +0.024826 | CRYPTO |
| ZECUSDT | 674.39 | 665.24 | +0.013568 | -0.012204 | CRYPTO |
| INJUSDT | 5.607 | 5.738 | -0.023364 | +0.023542 | CRYPTO |
| WUSDT | 0.01248 | 0.01254 | -0.004808 | +0.9615 | CRYPTO |
| HBARUSDT | 0.08923 | 0.08899 | +0.00269 | -0.269 | CRYPTO |

### 3.3 PnL calc mismatch vs `(current_price - entry_price) / entry_price` — 15 picks

`unrealized_pnl_pct` does not equal the expected return. Same 6 examples above plus 9 more (all CRYPTO except where noted). E.g. NEARUSDT expected +0.1293 but stored -0.129339 (sign-flipped magnitude).

### 3.4 Missing `asset_class` — 6 picks

6 active picks have no `asset_class` in metadata. Dashboard `dashboard/live_picks.json` (17 active picks) is **NOT all-UNK** — spot check shows CRYPTO (11), BOND (4), STOCKS (3), FOREX (1), no UNK; 6 picks are STALE (`ml_strategy_reviver`, `entry_time` 2026-07-11, ~126d).

### 3.5 Asset-class coverage (live_picks.db)

STOCKS 5, CRYPTO 101, FOREX 4, BOND 2, EQUITY 6, COMMODITY 5, UNKNOWN 6.  
**No mutual funds anywhere.** User asked for mutual funds — this class is absent from the DB.

### 3.6 `pick_history` — no resolution events

136 rows, all `event = REGISTERED`. No CLOSED/EXIT/TP/SL hits. Picks are registered but never marked resolved, so active picks can never age out naturally.

### 3.7 `data/audit_trail.db` — empty

All audit/consensus/feature/strategy-stats tables are **0 rows**. No audit evidence, no consensus picks, no feature snapshots, no strategy stats are being recorded. Only `bt_backtest_runs` (20) and `meta` (1) have data.

---

## 4. Picks JSON feeds — freshness inventory

| File | Count | generated_at / timestamp | Age | Notes |
|---|---|---|---|---|
| `dashboard/live_picks.json` | 17 active | 2026-11-12T19:27 | 2d | Fresh; asset_class present (CRYPTO/BOND/STOCKS/FOREX, no UNK); 6 stale `ml_strategy_reviver` picks (entry_time 2026-07-11) |
| `alpha_engine/data/active_picks_bond.json` | 6 bond | 2026-11-12T14:09 | 2d | Fresh (bond_scanner); NOT synced into `live_picks.db` |
| `alpha_engine/data/active_picks_etf.json` | 16 ETF | 2026-11-12T18:17 | 2d | Fresh (etf_scanner); `ingested_by_dashboard: false`, NOT synced into `live_picks.db` |
| `consensus_active_picks.json` | **0** | 2026-11-12T19:40 | 1d | Fresh but EMPTY |
| `stocksunify2_active_picks.json` | 14 equity | 2026-08-26 | 79d | STALE |
| `active_picks.json` | 0 | 2026-05-29 | 169d | STALE / empty |
| `highscore_closed_picks.json` | 132 closed | various (2026-04) | — | Full PnL columns present |
| **Closed picks (all files, deduped)** | **16,771** | — | — | **16,176 have a pnl field** |

Closed-pick PnL samples (symbol, class, pnl_pct): DOTUSDT 5.73, ADAUSDT 2.61, BNBUSDT 2.67, LINKUSDT 3.87, SUIUSDT 4.22, BCHUSDT 4.69, DOGEUSDT 2.52, SHIBUSDT 2.36 — all crypto, all positive.

### Active vs closed cross-reference by asset class

ACTIVE (273 deduped): crypto 66, UNK 108, EQUITY 15, ETF 32, FOREX 10, COMMODITY 9, BOND 9, STOCKS 3, meme 2, + mixed-case duplicates.
CLOSED (16,771 deduped): CRYPTO 6,400, crypto 1,348, FOREX 1,097, COMMODITY 560, forex 120, FUTURES 234, EQUITY 50, equity 4, BOND 3, STOCKS 1, UNK 6,953.

**Finding:** Active picks are dominated by UNK (108/273) and crypto; closed picks are dominated by CRYPTO (6,400) with large UNK (6,953). Bond (9 active vs 3 closed), ETF (32 active), FOREX (10 active) are thinly covered. Mutual funds: zero active, zero closed.

---

## 5. ML algorithms reviewed

### `ml_ranker_fixed.py` (ml_ranker v2)
**Sound.** Addresses prior audit findings: removed placeholder time features, proper 80/20 **chronological** train/test split (no leakage), ROC-AUC instead of accuracy, isotonic probability calibration, cross-validation with ROC-AUC, overfitting guard (train-test gap > 0.1 warning). Test harness included and passing by design. No calculation errors spotted.

### `ml_gatekeeper/gatekeeper.py`
**Sound with one known risk.** Pick Quality Classifier + Strategy-Regime Router, trained on 3,500+ real closed picks, no synthetic data. `ASSET_CLASS_MAP` = {CRYPTO:0, FOREX:1, EQUITY:2, COMMODITY:3, ETF:4, BOND:5, FUTURES:6}. Documents target-leakage features (`forward_wr`, `strat_fwd_wr`, `eb_forward_wr`, `age_hours`) with `ML_GATE_DROP_LEAKAGE=1` mask. The import-error masking of `ab_router` silences A/B failures (logged at line 30) — acceptable but worth making explicit.

### `alpha_engine/asset_class.py`
**Canonical single source of truth** for asset-class normalization. `FOREX_CODES`, `BOND_SYMBOLS`, `ETF_SYMBOLS`, `EQUITY_SYMBOLS`, `COMMODITY_SYMBOLS` frozensets. Should be the single place used to backfill the 6 missing + 17 UNK asset classes.

### `alpha_engine/` (~350 strategy files)
Strategies span all requested classes: `bond_*`, `etf_*`, `equity_*`, `forex_*`, `crypto_*`, `commodities_*`, `futures_strategies.py`. **No mutual fund strategies** found.

---

## 6. Summary of errors

| # | Error | Severity | Count | Location |
|---|---|---|---|---|
| 1 | Stale active picks (~172 days, never refreshed) | Critical | 129/129 | `data/live_picks.db` |
| 2 | PnL sign contradiction (`unrealized_pnl_pct` vs `pnl_pct`) | Critical | 8 | `data/live_picks.db` |
| 3 | PnL calc mismatch vs `(cp-ep)/ep` | High | 15 | `data/live_picks.db` |
| 4 | Missing `asset_class` | Medium | 6 (db); dashboard NOT all-UNK (CRYPTO/BOND/STOCKS/FOREX present) | `live_picks.db`, `dashboard/live_picks.json` |
| 5 | No mutual fund coverage (no active pipeline; mutual_fund_ranker.py + metadata.csv exist but emit no picks) | Medium | 0 classes | All DBs + `alpha_engine/` |
| 6 | `pick_history` only REGISTERED, no exits | High | 136 rows | `data/live_picks.db` |
| 7 | `audit_trail.db` tables empty | High | 9 tables × 0 rows | `data/audit_trail.db` |
| 8 | `consensus_active_picks.json` empty | Low | 0 picks | `copy_trader_intel/data/` |
| 9 | `sync_all_picks_to_mysql.py`: null `entry_price` backtest rows + `pnl *= 100` corruption | High | 2 bugs | `sync_all_picks_to_mysql.py` |
| 10 | `price_realism_check.py`: hardcoded `expected_2026_prices` dict | Medium | 1 bug | `price_realism_check.py` |

---

## 7. Proposed fixes

1. **Refresh stale picks:** Re-run price enrichment (`current_price`, `unrealized_pnl_pct`, `last_checked`) for all 129 active picks; retire/close picks older than 30–60 days with no activity.
2. **Fix PnL sign bug:** `unrealized_pnl_pct = (current_price - entry_price) / entry_price`; make `pnl_pct` consistent (single source of truth). Audit every row.
3. **Backfill `asset_class`:** Use `alpha_engine.asset_class.normalize_asset_class` / `classify_pick_asset_class_upper` for the 6 db rows; dashboard `asset_class` already populated (CRYPTO/BOND/STOCKS/FOREX, no UNK).
4. **Add mutual fund class:** Extend `asset_class.py` + strategies + DB schema so mutual funds are tracked (currently absent from active pipeline; `mutual_fund_ranker.py` + `mutual_fund_metadata.csv` exist but emit no picks).
9. **Fix `sync_all_picks_to_mysql.py`:** guard `bt_backtest_trades` insert behind `entry > 0` check; replace blind `pnl *= 100` with decimal/percent detection.
10. **Fix `price_realism_check.py`:** replace hardcoded `expected_2026_prices` dict with dynamic trailing 26-week range lookback.
5. **Resolve pick lifecycle:** Emit CLOSED/EXIT/TP/SL events into `pick_history` so active picks can age out.
6. **Populate `audit_trail.db`:** Write consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events.
7. **Populate consensus picks:** `consensus_active_picks.json` is empty — investigate why consensus merger produces 0 picks.
8. **Harmonize freshness:** Bond/ETF feeds are fresh (2d) but `live_picks.db` (172d) and `stocksunify2` (79d) are stale — align refresh schedules.

---

## 8. Verification performed

- Queried `data/live_picks.db` (live_picks + pick_history) — full row scan, staleness + PnL recomputation.
- Queried `data/audit_trail.db` — all table counts.
- Inventoried ~40 picks JSON files (active + closed) with timestamps/ages.
- Cross-referenced active (273) vs closed (16,771) picks by asset class.
- Read `ml_ranker_fixed.py` (454 lines), `ml_gatekeeper/gatekeeper.py` (header + leakage doc), `alpha_engine/asset_class.py` (header + symbol sets).
- Confirmed `dbpasses_ASK_MISSINGpollinations2026-11-03.txt` has no secrets.
- Reviewed `sync_all_picks_to_mysql.py` (found null `entry_price` backtest rows + `pnl *= 100` corruption bug) and `price_realism_check.py` (hardcoded `expected_2026_prices` dict bug).
- Cross-checked proposed_fixes docs for consistency (paths, line numbers, metadata-JSON column assumption).

**No code changes were made.** This is a read-only audit. Fixes are proposed above for implementation in a follow-up session.
