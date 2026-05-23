# Wave 0 Census Report

**Generated:** 2026-05-08 15:46:20 UTC
**DB:** `ejaguiar1_stocks` @ `mysql.50webs.com`
**Mode:** READ-ONLY

## 0-A: OPEN-Population Census (`bt_backtest_trades`)

**Total rows (approx):** 1,312,509

### Status Distribution
| Status | Count | % |
|--------|-------|---|
| `OPEN` | 26,952,924 | 2053.54% |
| `closed` | 1,306,502 | 99.54% |
| `LOST` | 930,181 | 70.87% |
| `WON` | 666,274 | 50.76% |
| `expired` | 30,065 | 2.29% |
| `WIN` | 265 | 0.02% |
| `LOSS` | 195 | 0.01% |
| `SL_HIT` | 158 | 0.01% |
| `TP_HIT` | 25 | 0.0% |
| `CLOSED_SL` | 23 | 0.0% |
| `CLOSED_TP` | 23 | 0.0% |

*0-A:open-by-class failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-A:open-total failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-A:open-strategy failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-A:age-buckets failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

## 0-B: Ghost Sweeps

### P0-1: `quan_engine` MATICUSDT Constant-PnL Ghosts
| Strategy | Symbol | Direction | PnL% | Count |
|----------|--------|-----------|------|-------|
| quan_engine | MATICUSDT | LONG | -15.0 | 220533 |
| meta_strategy | MATICUSDT | LONG | 0.0 | 2732 |
| quan_engine | MATICUSDT | LONG | None | 1877 |
| meta_strategy | MATICUSDT | LONG | None | 792 |
**Total ghost rows:** 225,934

### P0-2: `meta_strategy` Constant-PnL Template
| Strategy | Symbol | Direction | PnL% | Count |
|----------|--------|-----------|------|-------|
| meta_strategy | DYDXUSDT | LONG | -3.0 | 28956 |
| meta_strategy | PENGUUSDT | LONG | 5.0 | 26442 |
| meta_strategy | ALGOUSDT | LONG | -3.0 | 25724 |
| meta_strategy | DYDXUSDT | LONG | 5.0 | 23780 |
| meta_strategy | AVAXUSDT | LONG | -3.0 | 23376 |
| meta_strategy | PENGUUSDT | LONG | -3.0 | 22671 |
| meta_strategy | ONDOUSDT | LONG | -3.0 | 22453 |
| meta_strategy | ETHUSDT | LONG | 5.0 | 21728 |
| meta_strategy | RENDERUSDT | LONG | -3.0 | 20795 |
| meta_strategy | ENAUSDT | LONG | 5.0 | 19711 |
| meta_strategy | ETHUSDT | LONG | -3.0 | 19570 |
| meta_strategy | APEUSDT | LONG | 5.0 | 18761 |
| meta_strategy | METISUSDT | LONG | -3.0 | 18513 |
| meta_strategy | APEUSDT | LONG | -3.0 | 18488 |
| meta_strategy | AVAXUSDT | LONG | 5.0 | 18261 |
| meta_strategy | WLDUSDT | LONG | 5.0 | 17949 |
| meta_strategy | ADAUSDT | LONG | -3.0 | 17902 |
| meta_strategy | ARBUSDT | LONG | 5.0 | 17021 |
| meta_strategy | ENAUSDT | LONG | -3.0 | 16857 |
| meta_strategy | FETUSDT | LONG | -3.0 | 16551 |
**Total ghost rows:** 415,509

*0-B:p03-phantoms failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-B:large-cohorts failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-C:integrity failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-C:by-class failed: (2013, 'Lost connection to MySQL server during query (timed out)')*

*0-D:nulls failed: (0, '')*

## 0-E: Index Health

### `bt_backtest_trades` (6 index entries)
| Key_name | Column_name | Seq |
|----------|-------------|-----|
| `PRIMARY` | `id` | 1 |
| `backtest_run_id` | `backtest_run_id` | 1 |
| `idx_bt_sym` | `symbol` | 1 |
| `idx_bt_asset` | `asset_class` | 1 |
| `idx_bt_strat` | `strategy` | 1 |
| `idx_bt_status` | `status` | 1 |

### `trading_picks` (1 index entries)
| Key_name | Column_name | Seq |
|----------|-------------|-----|
| `PRIMARY` | `id` | 1 |

*P0-5:freeze failed: (2013, 'Lost connection to MySQL server during query (timed out)')*
