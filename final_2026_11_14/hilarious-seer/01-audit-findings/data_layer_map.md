# Data Layer Map — Pick-Trading Audit System

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Agent:** ML algorithms audit asset classes stale data fixes

---

## 1. Databases (schema from code; .db files gitignored)

### `data/live_picks.db`
- **Tables:** `live_picks`, `pick_history`
- **Schema:** `live_picks_tracker.py:56-86`
- **State (peer SQLite forensics):** 129 active rows (69 ACTIVE + 60 OPEN), all `last_updated` = 2026-05-25T20:50:25
- **Asset-class split:** STOCKS 5, CRYPTO 101, FOREX 4, BOND 2, EQUITY 6, COMMODITY 5, UNKNOWN 6 — zero mutual funds
- **pick_history:** 136 rows, 100% `event='REGISTERED'`, zero CLOSED/EXIT/TP/SL events

### `data/audit_trail.db`
- **11 tables:** `meta`, `aggregation_runs`, `raw_picks`, `consensus_picks`, `audit_events`, `filter_log`, `strategy_stats`, `bt_backtest_runs`, `bt_backtest_trades`, `feature_edge_snapshots`, `symbol_strategy_stats`
- **State:** 8 of 11 tables have 0 rows. Only `bt_backtest_runs`=20 and `meta`=1 populated. Drained since March 2026 (was 6,432 raw_picks / 73 consensus_picks).

### Other DBs (all absent/gitignored)
`alpha_engine/data/audit_consolidated.db`, `paper_trading/data/paper.db`, `coinglass_strategies/data/coinglass.db`, `quan_engine/data/quan_engine.db`, `crypto_data.db`, `meta_strategy/data/meta_strategy.db`, `trading/data/positions.db`, `genome/*.db`, `KIMI_*/data/kimi_trading.db`, `mlflow.db`

---

## 2. Zombie / Stale Rows

| Population | Count | Evidence |
|---|---|---|
| live_picks.db active picks ~172 days stale | **129/129** | ML-AUDIT:42 |
| pick_history rows with no resolution event | **136 (all REGISTERED)** | ML-AUDIT:80 |
| Dashboard picks.active_raw EXPIRED rows | **3,377** (CRYPTO 3,100) | prediction-system-audit:36 |
| inverse_mutations / inverse_luxalgo_confluence zombie rows | **2,267** EXPIRED, **2,255 with pnl==0.0**, 2,254 null price | crypto_commodity.md:261 |
| Non-crypto raw rows _auto_expired/expired_no_pnl | **277 of 571 (48.5%)** | MASTER_AUDIT:110 |
| Non-crypto rows >30 days stale | **274** | MASTER_AUDIT:111 |
| TIME_EXIT picks never resolved | **4,220 of 4,820** | OVERALL_QUICK_WINS:18 |
| Ghost MEMECOIN rows (DOGEUSDT x3,569 identical) | **22,947** | OVERALL_QUICK_WINS:17 |

**Duplicate / non-unique IDs:**
- active_raw: 4,148 rows but only 3,851 unique IDs → 218 duplicated IDs; 55 IDs conflict across active_raw/recent_closed
- live_picks PK is `UNIQUE(id, system)` — same pick ID can coexist across systems; 1,864 duplicate groups in CRYPTO 90-day raw

---

## 3. PnL Columns — Units, Signs, Mismatches

**Unit split-brain (root cause of untrustworthy PnL):**

| Writer | Formula | Unit | Location |
|---|---|---|---|
| mercury2 scanner | `round((price - entry) / entry * 100, 4)` | **percent** | mercury2/scanner.py:481-483 |
| outcome resolver | `round((current - entry) / entry, 4)` | **decimal ratio** | copy_trader_intel/outcome_resolver.py:252,263 |
| Dashboard display | `{unrealized_pnl_pct:+.2f}%` printed raw | **unit-blind → 100x error** | dashboard/generate_dashboard.py:24 |
| Closed-pick JSONs | e.g. `-0.0424`, `0.00625` | **ratio** | multi_asset/data/multi_asset_closed.json |
| live_picks.db stored values | e.g. `-0.129339`, `+0.128512` | **ratio** | ML-AUDIT:58-63 |

**Measured corruption in live_picks.db (129 active rows):**
- **8 sign contradictions** — unrealized_pnl_pct has opposite sign of price move vs entry
- **15 calc mismatches** vs canonical `(current_price - entry_price) / entry_price`
- Sign convention is direction-aware and correct only in `outcome_resolver.py:242-263`

**Aggregate consequence:** dashboard PF vs raw-DB PF diverge 4.9x–226x by class (CRYPTO 1.801 vs 0.371; FOREX 2.02 vs 0.108; FUTURES 0.582 vs 131.6)

---

## 4. Frozen Prices

- Only **123 of 691 OPEN rows (17.8%)** carry a genuinely live, entry-differing price with non-zero PnL; **485 have null price**; **29 are bit-exact `current == entry`**
- Per class frozen-at-0%: CRYPTO 334/402 (83%), FOREX 93/118 (79%), FUTURES 3/3 (100%), SPORTS 2/2 (100%)
- **Live cross-check (Binance/Frankfurter, 2026-11-14):** XRPUSDT SHORT frozen at entry 0.9842 (live 0.9742 → +1.0% true), BTCUSDT frozen at 66,300 (live 65,839 → +0.7%)
- **Forex/commodity caches frozen at 2026-06-06 (161 days)**
- `data/equity_quote_cache/` contains only `.gitkeep` — **empty**
- `audit_trail/dashboard_generator.py:1681-1688` documents the freeze failure mode

---

## 5. JSON Payloads (freshness as of 2026-11-14 ~18:15Z)

| File | Freshness | Count / state |
|---|---|---|
| `audit_dashboard/data/dashboard_data.json` | generated 2026-11-14T14:30:07Z (fresh) but embeds dead blocks | 20 curated active; 4,148 raw; 3,500 recent_closed |
| `copy_trader_intel/data/consensus_active_picks.json` | **fresh 17:16:14Z but EMPTY** (0 picks) | merger produces nothing |
| `audit_dashboard/data/hyro_pick_performance.json` | **2026-11-08T02:14:09Z → 157h (6.6d) STALE** | 87 total signals |
| `audit_dashboard/data/hyrotrader_picks.json` | **no timestamp field** | unverifiable age |
| `pick_funnel_snapshot.json` | **absent / 404-HTML on live site** | missing |
| `audit_dashboard/data/db_freshness.json` | **2026-05-23T18:29:59Z → 174d STALE, overall: RED** | trading_picks n_active=37,732; at_signal_outcomes 115,782 min (80d) stale |
| `data/data_quality_report.json` | 2026-03-03 (256d) | stale green-wash |
| `audit_dashboard/data/integrity_report.json` | 2026-03-11 (248d) | stale green-wash |

---

## 6. Price-Sync Mechanisms & Last Runs

| Mechanism | What it does | Last run evidence |
|---|---|---|
| `audit_trail/fetch_stock_prices.py` | yfinance batch + FMP fallback | **ran 2026-11-14T17:41:59Z** |
| `.github/workflows/daily-price-refresh.yml` | `fetch_prices.php` ticker refresh | **BROKEN — returns HTTP 404** |
| Binance spot price fetchers (15+ scripts) | `api.binance.com/api/v3/ticker/price` | live-verified working 2026-11-14 |
| `audit_trail/data/pipeline_health.json` | per-step outcomes | **18:04:57Z, status: degraded** — walkforward_validation: failure; hyro_pick_perf: "success" while output 157h stale |
| `audit_trail/universal_pick_resolver.py` | TP/SL/time-exit resolver | **output file does not exist in audit_trail/data/** |

---

## 7. MySQL Sync

**`alpha_engine/audit_sync.py`** — consolidates 12 portfolio JSON sources into SQLite + MySQL.

**`sync_all_picks_to_mysql.py`** — two confirmed bugs:
- **Bug A:** null `entry_price` backfill — `bt_backtest_trades` insert sits outside the guard
- **Bug B:** `pnl *= 100` corruption at `:660-661` (JSON) and `:858-859` (SQLite)
- Hardcoded MySQL credentials in source (`AUDIT_DB_PASS` default `"stocks"`)

---

## TOP 5 DATA-INTEGRITY BLOCKERS

1. **Active-pick inventory is 172 days stale and majority-zombie.** 129/129 active picks frozen; 3,377 EXPIRED in active_raw; 2,267 zombie rows from inverse_mutations alone.
2. **PnL has a ratio-vs-percent split brain with measured corruption.** 8 sign-flipped + 15 miscalculated rows; dashboard-vs-raw PF divergences of 4.9x–226x.
3. **No mark-to-market: prices are frozen at build time.** Only 17.8% of OPEN picks have live prices; forex/commodity caches 161d stale; equity cache empty.
4. **Picks never resolve — lifecycle is broken end-to-end.** 100% REGISTERED in pick_history; resolver output file missing; 4,220 of 4,820 TIME_EXIT picks unresolved.
5. **Three divergent stores and an empty audit trail — no source of truth.** SQLite says 129 active; MySQL says 90,523 open; dashboard shows 20 curated. audit_trail.db 8 of 11 tables at 0 rows.

**Fix-order implication:** P0 = canonical single-unit signed PnL recompute + price refresh + staleness gate; then lifecycle events; then store reconciliation.
