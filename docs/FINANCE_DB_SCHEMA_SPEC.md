# Finance / Investment Database Schema Specification

**Scope:** All MySQL databases on `<DB_HOST>` that are finance/investment or
backtesting related. Non-finance databases (`events`, `favcreators`, `news`,
`tvmoviestrailers`) are documented only at the inventory level and are **not**
detailed here.

**Generated:** 2026-11-19 (schema pulled live from the server via
`information_schema` + sample rows). Row counts are approximate for very large
tables (`TABLE_ROWS`), exact for the rest.

---

## 1. Connection / Host Layout

- **Host:** `<DB_HOST>:3306`
- **Model:** per-database users — user `ejaguiar1_<db>` accesses only database
  `ejaguiar1_<db>`. A single connection cannot do cross-DB operations; the
  backup tool uses a two-connection copy pattern.
- **10 total databases.** Finance-relevant: `stocks`, `backtests`, `backups`
  (archive), `deals` (empty), `memecoin`, `sportsbet`. Non-finance (inventory
  only): `events`, `favcreators`, `news`, `tvmoviestrailers`.

| Database | Tables | Purpose | Finance? |
|---|---|---|---|
| `ejaguiar1_stocks` | 409 | Primary trading-pick engine, performance, portfolios | ✅ |
| `ejaguiar1_backtests` | 10 | Backtest runs + trade-level results | ✅ |
| `ejaguiar1_backups` | 414 | Archive / point-in-time backups of prod tables | ✅ (archive) |
| `ejaguiar1_memecoin` | 58 | Memecoin / crypto scans, signals, paper trades | ✅ |
| `ejaguiar1_sportsbet` | 49 | Sports betting bankroll, bets, value bets | ✅ |
| `ejaguiar1_deals` | 0 | Empty (no tables) | ✅ (empty) |
| `ejaguiar1_events` | — | Event site | ❌ |
| `ejaguiar1_favcreators` | — | FavCreators | ❌ |
| `ejaguiar1_news` | — | News | ❌ |
| `ejaguiar1_tvmoviestrailers` | — | TV/movie trailers | ❌ |

---

## 2. Primary Database: `ejaguiar1_stocks` (409 tables)

This is the core finance database. It stores the full pick pipeline, backtest
imports, performance accounting, and portfolio snapshots.

### 2.1 Core pick-pipeline tables

#### `trading_picks` (~147k rows) — canonical live/closed pick ledger
| Column | Type | Notes |
|---|---|---|
| `id` | varchar(100) | PK (e.g. `ZW=F_commodity_term_cot_2026-08-13T12:34`) |
| `symbol` | varchar(20) | MUL |
| `direction` | varchar(10) | LONG/SHORT/BUY |
| `strategy` | varchar(100) | MUL |
| `entry_price` | decimal(20,8) | |
| `take_profit` / `stop_loss` | decimal(20,8) | |
| `confidence` | decimal(5,4) | |
| `elite_score` / `trust_score` | int | |
| `category` | varchar(20) | MUL |
| `source_system` | varchar(50) | |
| `status` | varchar(20) | OPEN/ACTIVE/WON/LOST... |
| `pnl_pct` | decimal(10,4) | |
| `exit_price`, `closed_at`, `exit_reason` | | |
| `created_at`, `updated_at`, `market_regime_id`, `sector`, `volatility_atr`, `execution_slippage_pct` | | regime/context |
- **Freshness:** max `created_at` = **2026-11-19 04:48** → active.

#### `at_raw_picks` (~113k rows) — pre-aggregation raw picks
| Column | Type | Notes |
|---|---|---|
| `id` | char(36) | PK |
| `aggregation_run_id` | char(36) | MUL |
| `source_system` | varchar(100) | MUL (AlphaEngine, incubator_gainer, ...) |
| `symbol` | varchar(50) | MUL |
| `asset_class` | enum | CRYPTO/FOREX/EQUITY/PENNY_STOCK/MEMECOIN/SPORTS/FUTURES/ETF/COMMODITY/BOND/UNKNOWN |
| `direction` | enum(LONG,SHORT) | |
| `entry_price`, `take_profit`, `stop_loss`, `risk_reward`, `confidence`, `strategy` | | |
| `raw_payload` | json | |
| `signal_timestamp`, `recorded_at` | datetime | |
| `dedup_hash` | char(64) | UNI |
| `was_stale`, `was_banned`, `was_demoted`, `was_wr_suppressed` | tinyint | flags |
| `status`, `exit_price`, `exit_reason`, `pnl_pct`, `closed_at` | | resolution |
| `reverse_split_affected` | tinyint | |
- **Freshness:** max `recorded_at` = **2026-11-19 05:12** → active.

#### `at_pick_outcomes` (~63k rows) — resolved outcomes for picks
`pick_id` PK, `symbol`, `strategy`, `asset_class`, `status`
(enum OPEN/WON/LOST/EXPIRED/FLAT), `resolution_method` (enum TP_HIT/SL_HIT/
TIME_EXPIRED/MANUAL), `pnl_pct`, `resolved_at`, `resolver_version`,
`forward_test_only`, `forward_validated`, `market_regime_id`, `sector`,
`volatility_atr`, `execution_slippage_pct`.
- **Freshness:** max `resolved_at` = **2026-11-19 03:24** → active.

#### `at_signal_outcomes` (~51k rows) — resolved signal-level outcomes
`id` int PK, `symbol`, `direction`, `entry_price`, `take_profit`, `stop_loss`,
`exit_price`, `outcome`, `pnl_pct`, `source_system`, `strategy`,
`asset_class`, `opened_at`, `closed_at`, `created_at`,
`reverse_split_affected`, `intrabar_status`, `intrabar_pnl_pct`,
`intrabar_ambiguous`, `intrabar_horizon_bars`, `intrabar_resolved_at`.
- **Freshness:** max `closed_at` = **2026-11-19 04:49** → active.

#### `now_history` (~86k rows) — "now" scan history
`run_id`, `scan_time`, `symbol`, `direction`, `strategy`, `entry_price`,
`sl_price`, `tp_price_1_5`, `tp_price_2_0`, `sl_pct`, `confidence`, `reason`,
`outcome_1_5`, `outcome_2_0`, `peak_price`, `trough_price`, `resolved_at`,
`actual_pnl_pct`.
- **Freshness:** max `scan_time` = **2026-11-19 04:38** → active.

#### `at_local_picks` (~76M rows) — largest table, local pick dumps
- **Freshness:** large archive of local picks; populated through 2026-03.

### 2.2 Performance / portfolio tables

#### `portfolio_snapshots` (26 rows)
`portfolio_id`, `portfolio_name`, `methodology`, `category`, `status`,
`equity`, `initial_capital`, `pnl_pct`, `pnl_usd`, `win_rate`,
`total_trades`, `open_positions`, `max_drawdown_pct`, `sharpe_ratio`,
`profit_factor`, `total_commission`, `resets`, `snapshot_at`.
- **Freshness:** max `snapshot_at` = **2026-03-10** → **STALE** (last snapshot
  ~8 months old; portfolios exist but snapshots have not been updated).

#### `consensus_tracked` (318 rows) — tracked consensus picks
`ticker`, `company_name`, `entry_date`, `entry_price`, `consensus_count`,
`consensus_score`, `direction`, `source_algos`, `target_tp_pct`,
`target_sl_pct`, `max_hold_days`, `current_price`, `current_return_pct`,
`peak_price`, `trough_price`, `status`, `exit_date`, `exit_price`,
`exit_reason`, `final_return_pct`, `hold_days`, `discord_*`, `created_at`,
`updated_at`.
- **Freshness:** max `updated_at` = **2026-04-27** → **STALE** (no updates since
  late April; consensus tracking appears inactive).

#### `daily_prices` (~66k rows)
`ticker`, `trade_date`, `open_price`, `high_price`, `low_price`,
`close_price`, `adj_close`, `volume`.
- **Freshness:** max `trade_date` = **2026-11-17** → active (equities).

#### `strategy_registry` (~1962 rows)
`strategy_id`, `strategy_name`, `system_name`, `section_name`, `module_file`,
`asset_class`, `strategy_type`, `win_rate`, `sharpe`, `source_ref`,
`is_banned`, `is_active`, `notes`, `created_at`, `updated_at`,
`total_picks`, `resolved_picks`, `profit_factor`, `source_type`,
`first_seen`, `last_seen`.
- **Freshness:** max `updated_at` = **2026-06-01** → stale-ish (registry last
  updated June; may be static by design).

#### `algorithms` (142 rows) — algorithm reference catalog
`name`, `family`, `description`, `algo_type`, `ideal_timeframe`, `pros`, `cons`.
- **Freshness:** created 2026-05-17 (import). Catalog only.

### 2.3 Backtest-import tables (mirrored from `backtests` DB)
`backtest_results`, `backtest_trades`, `bt_backtest_runs`,
`bt_backtest_trades` (~27M rows), `at_large_backtest_results`,
`at_incubator_backtest_results`, `at_permutation_picks`,
`at_permutation_snapshots`, `at_strategy_symbol_performance`.

### 2.4 Status of the stocks DB overall
- **Active core:** `trading_picks`, `at_raw_picks`, `at_pick_outcomes`,
  `at_signal_outcomes`, `now_history`, `daily_prices`, `at_local_picks`.
- **Stale / inactive:** `portfolio_snapshots` (Mar 2026),
  `consensus_tracked` (Apr 2026), `strategy_registry` (Jun 2026, static).
- **110 of 409 tables are empty** (0 rows) — mostly scaffold/placeholder
  tables (see §5).

---

## 3. `ejaguiar1_backtests` (10 tables)

Backtesting output DB. Holds both run-level metadata and the massive
trade-level backtest ledger.

| Table | Rows | Notes |
|---|---|---|
| `bt_backtest_trades` | ~32.7M | Trade-level backtest rows. Columns: `backtest_run_id`, `source_db`, `source_table`, `symbol`, `asset_class` (enum incl. CRYPTO/FOREX/EQUITY/PENNY_STOCK/MEMECOIN/SPORTS/FUTURES/ETF/COMMODITY/UNKNOWN), `direction`, `strategy`, `entry_price`, `exit_price`, `take_profit`, `stop_loss`, `entry_time`, `exit_time`, `pnl_pct`, `status`, `confidence`, `raw_data` (json), `imported_at` |
| `bt_backtest_runs` | 285 | `id` char(36) PK, `source_db`, `source_table`, `strategy`, `symbol`, `asset_class`, `total_trades`, `wins`, `losses`, `win_rate`, `profit_factor`, `total_return`, `sharpe`, `max_drawdown`, `imported_at` — **freshness: max imported_at = 2026-03-06** (STALE; no backtests imported since March) |
| `at_incubator_backtest_results` | 1285 | `perm_id`, `archetype`, `symbol`, `params_json` (json), `total_trades`, `wins`, `losses`, `win_rate`, `sharpe`, `sortino`, `max_drawdown`, `profit_factor`, `total_return`, `avg_trade_pnl`, `avg_hold_bars`, `slippage_pct`, `commission_pct`, `backtest_type` enum(fast,full), `created_at` |
| `at_large_backtest_results` | 1105 | Same + `equity_curve_json`, `trade_log_json` |
| `backtest_results` / `backtest_trades` | 2 / 50 | small legacy copies |
| `eagle2_consensus_picks` | 15 | `ticker`, `tier`, `conviction`, `cycle`, `status`, `method`, `run_date`, `created_utc` — last run 2026-06-02 |
| `eagle2_methodology` | 10 | methodology reference |
| `stocks_backup_runs` / `stocks_backup_table_log` | 1 / 323 | backup-housekeeping logs |

- **Note:** `bt_backtest_trades` is the single largest finance table (~32.7M
  rows). `bt_backtest_runs` has not received imports since **2026-03-06** →
  the backtest pipeline's live import appears stale, though the data volume
  remains huge.

---

## 4. `ejaguiar1_memecoin` (58 tables)

Memecoin / crypto scanning, signal generation, and paper-trading DB.

### Key tables
| Table | Rows | Notes |
|---|---|---|
| `mc_scan_log` | 2255 | memecoin scan log: `scan_id`, `pair`, `price`, `score`, `factors_json`(text), `verdict`, `chg_24h`, `vol_usd_24h`, `tier`, `created_at`, `on_kraken` — **freshness: max created_at = 2026-05-04** (STALE) |
| `mc_winners` | 476 | resolved scan outcomes: `scan_id`, `pair`, `price_at_signal`, `price_at_resolve`, `score`, `factors_json`, `verdict`, `target_pct`, `risk_pct`, `pnl_pct`, `outcome`, `vol_usd_24h`, `chg_24h`, `tier`, `created_at`, `resolved_at` — **freshness: max resolved_at = 2026-05-04** (STALE) |
| `mc_daily_snapshots` | 84 | daily perf: `snapshot_date` UNI, signals/wins/losses/win_rate/avg_pnl/total_pnl/best_trade/worst_trade/unique_coins/updated_at — last 2026-05-04 |
| `psi_signals` | 12 | `sig_type`, `pair`, `direction`, `entry_price`, `tp_price`, `sl_price`, `tp_pct`, `sl_pct`, `confidence`, `confluence`, `strats_agreed`, `reasoning`, `status`, `current_price`, `pnl_pct`, `peak_pnl`, `trough_pnl`, `exit_price`, `exit_reason`, `checks`, `created_at`, `resolved_at` — last 2026-04-16 |
| `kraken_paper_trades` | 0 | empty (paper trading scaffold) |
| `psi_ohlcv_cache` | 17715 | OHLCV cache |
| `psi_results` | 2400 | strategy results |
| `psi_tournament` | 3616 | tournament results |
| `crypto_assets` | 14 | asset reference |
| `pump_forensics_scans` / `pump_forensics_audit` | 3471 / 380 | pump forensics |

### Freshness summary (memecoin)
- Most active tables last wrote **2026-05-04** (scans, winners, snapshots) →
  the memecoin scanner has been **dormant since May 2026**.
- `psi_signals` last updated 2026-04-16.
- Many ML/model tables are empty (0 rows): `meme_ml_models`,
  `meme_ml_predictions`, `ml_models`, `ml_model_performance`, `crypto_*`
  indicator/signal/pattern tables.

---

## 5. `ejaguiar1_sportsbet` (49 tables)

Sports betting bankroll, bets, odds, and value-bet DB.

### Key tables
| Table | Rows | Notes |
|---|---|---|
| `lm_sports_odds` | 54965 | odds snapshot history — last 2026-05-24 |
| `lm_sports_value_bets` | 4153 | value bets: `event_id`, `sport`, `home_team`, `away_team`, `commence_time`, `market`, `bet_type`, `outcome_name`, `best_book`, `best_book_key`, `best_odds`, `consensus_implied_prob`, `true_prob`, `edge_pct`, `ev_pct`, `kelly_fraction`, `kelly_bet`, `all_odds`, `detected_at`, `status` — **freshness: max detected_at = 2026-05-16** (STALE) |
| `lm_sports_clv` | 10101 | closing line value |
| `lm_sports_daily_picks` | 128 | daily picks — last 2026-05-16 |
| `lm_sports_bets` | 48 | placed bets: event/sport/teams/commence_time/game_date/bet_type/market/pick/pick_point/bookmaker/bookmaker_key/odds/implied_prob/bet_amount/potential_payout/algorithm/ev_pct/ml_* columns/status/result/pnl/settled_at/scores/placed_at/cohort — last placed 2026-05-13 |
| `lm_sports_bankroll` | 7 | `snapshot_date` UNI, bankroll/bets/wins/losses/pushes/win_rate/total_wagered/total_pnl/roi_pct |
| `lm_arena_bankrolls` / `lm_arena_bets` / `lm_arena_snapshots` | 25 / 344 / 75 | betting-arena side; last 2026-10-07 (bankrolls/snapshots) |
| `lm_arena_strategies` | 25 | reference |
| `lm_nba_stats_cache`, `lm_nfl_stats_cache`, `lm_nhl_stats_cache`, `lm_mlb_stats_cache` | 1 each | cache rows, last updated 2026-11-15 (active cache) |
| `lm_schedule_intel_cache` | 4 | last 2026-11-15 |

### Freshness summary (sportsbet)
- Betting/odds pipeline (`lm_sports_*`) last wrote **2026-05-24** (odds) /
  **2026-05-16** (value bets) → dormant since late May 2026.
- Arena side (`lm_arena_*`) bankrolls/snapshots last updated **2026-10-07**,
  and `_stats_cache` / `_intel_cache` tables are **active through 2026-11-15**
  (cache keeps refreshing, but no new bets are placed).
- 20 of 49 tables are empty (0 rows) — mostly odds/injury/referee scaffolds.

---

## 6. `ejaguiar1_backups` (414 tables) — archive DB

Not a live data source — it is the **point-in-time archive** of production
tables. Almost every table carries a dated or incident suffix:

- `trading_picks_20260605T123115Z`, `trading_picks_20260609T181909Z`,
  `trading_picks_20260610T055138Z`, `trading_picks_20260611T222306Z` → dated
  pick backups.
- `at_raw_picks_backup_2026-05-31T04:05:57Z`, etc. → raw-pick archive.
- `INCIDENT_*` tables → incident-related snapshots (e.g. `INCIDENT_OVERALL_*`,
  `INCIDENT_CRYPTO_bk_20260610T182348Z`).
- `stocks__*` tables (hundreds) → the full stocks schema mirrored from the
  2026-05-17 migration snapshot.
- Housekeeping: `db_audit_log`, `audit_operations`, `stocks_backup_table_log`.

**Design intent:** backup/audit ledger. Tables here are expected to be
"stale" by design — they are frozen copies, not live state. The live tables
live in `stocks` / `backtests` / `memecoin` / `sportsbet`.

---

## 7. Stale vs Active classification

"Stale" here means the table's latest data write predates the live pipeline's
expected cadence, or the table is empty/scaffold. Today = **2026-11-19**.

### 7.1 Active (live, written recently)
| DB | Table | Latest write |
|---|---|---|
| stocks | `trading_picks` | 2026-11-19 04:48 |
| stocks | `at_raw_picks` | 2026-11-19 05:12 |
| stocks | `at_pick_outcomes` | 2026-11-19 03:24 |
| stocks | `at_signal_outcomes` | 2026-11-19 04:49 |
| stocks | `now_history` | 2026-11-19 04:38 |
| stocks | `daily_prices` | 2026-11-17 |
| stocks | `at_local_picks` | large archive, live |
| sportsbet | `lm_*_stats_cache` / `lm_*_intel_cache` | 2026-11-15 |

### 7.2 Stale / dormant (pipeline stopped writing)
| DB | Table | Last write | Note |
|---|---|---|
| stocks | `portfolio_snapshots` | 2026-03-10 | portfolios exist, snapshots frozen |
| stocks | `consensus_tracked` | 2026-04-27 | consensus tracking inactive |
| stocks | `strategy_registry` | 2026-06-01 | likely static reference |
| backtests | `bt_backtest_runs` | 2026-03-06 | no backtest imports since March |
| memecoin | `mc_scan_log` | 2026-05-04 | memecoin scanner dormant |
| memecoin | `mc_winners` | 2026-05-04 | dormant |
| memecoin | `mc_daily_snapshots` | 2026-05-04 | dormant |
| memecoin | `psi_signals` | 2026-04-16 | dormant |
| sportsbet | `lm_sports_odds` | 2026-05-24 | odds pipeline dormant |
| sportsbet | `lm_sports_value_bets` | 2026-05-16 | value-bet pipeline dormant |
| sportsbet | `lm_sports_bets` | 2026-05-13 | no new bets placed |
| sportsbet | `lm_sports_daily_picks` | 2026-05-16 | dormant |
| sportsbet | `lm_arena_*` | 2026-10-07 | arena bankrolls/snapshots (cache still active) |

### 7.3 Empty / scaffold tables (0 rows)
- **stocks:** 110 of 409 tables empty (e.g. `paper_trades`,
  `paper_portfolio_daily`, `stock_signals`, `stock_ohlcv`, `stock_assets`,
  `walk_forward_results`, `ml_model_registry`, `ml_models`, `saved_portfolios`,
  `tracked_portfolios`, `sp_picks`, `sp_batches`, `crypto_*` indicator tables,
  `goldmine_cursor_*` benchmark/regime/correlation tables, `lm_bridge_*`
  several, `cr_backtest_*`, `fx_backtest_*`, etc.).
- **sportsbet:** 20 of 49 tables empty (odds/injury/referee/travel/cache
  scaffolds).
- **memecoin:** 9 of 58 tables empty (`kraken_paper_trades`,
  `meme_ml_models`, `meme_ml_predictions`, `ml_models`,
  `ml_model_performance`, `crypto_indicators`, `crypto_patterns`,
  `crypto_signals`, `crypto_market_data`).
- **deals:** entire database empty (0 tables).

---

## 8. Sample records (illustrative)

### `stocks.trading_picks`
```
id=ZW=F_commodity_term_cot_2026-08-13T12:34
symbol=ZW=F  direction=LONG  strategy=commodity_term_cot
entry=656.25  tp=669.375  sl=649.6875  confidence=0.5  elite_score=43
```
```
id=ZROUSDT_15m_20260222_1338
symbol=ZROUSDT  direction=BUY  strategy=''
entry=1.709  tp=1.73214  sl=1.69743  elite=25  trust=2
```

### `stocks.at_raw_picks`
```
source_system=AlphaEngine  symbol=EURGBP=X  asset_class=FOREX  direction=LONG
entry=0.84536  tp=0.85766  sl=0.84282  risk_reward=4.85
source_system=incubator_gainer  symbol=LDOUSDT  asset_class=CRYPTO  direction=LONG
entry=0.3131  tp=0.3253  sl=0.3086  risk_reward=2.69
```

### `stocks.at_pick_outcomes`
```
pick_id=ZROUSDT_15m_20260222_1338  asset_class=CRYPTO
status=LOST  resolution_method=SL_HIT  pnl_pct=-6.73  resolved=2026-02-22 22:12
pick_id=ZKUSDT_15m_20260222_1348
status=WON  resolution_method=TP_HIT  pnl_pct=0.16  resolved=2026-02-22 22:12
```

### `stocks.portfolio_snapshots`
```
portfolio_id=multi_asset_diversified  methodology=sector  category=signal  status=ACTIVE
equity=9997.01  initial=10000  pnl_pct=-0.0299  pnl_usd=-2.99
portfolio_id=forex_carry  methodology=score  equity=9996.53  pnl_pct=-0.0347
```

### `stocks.consensus_tracked`
```
ticker=IBM  company=IBM Corp  entry=2026-04-27  price=241.81
consensus_count=3  score=402  direction=LONG  source=Momentum Continuation, CDR Zero-Fee Prio
ticker=WMT  company=Walmart Inc.  entry=2026-04-27  price=127.59
consensus_count=3  score=688  direction=LONG
```

### `backtests.bt_backtest_runs`
```
source_db=alpha_engine/data/closed_picks.json  strategy=exchange_netflow_reversal
symbol=BNBUSDT  asset_class=CRYPTO  trades=1  wins=0  losses=1  win_rate=0
strategy=volume_profile_value_area  symbol=FILUSDT  trades=1  wins=1  losses=0  win_rate=1.0
```

### `memecoin.mc_winners`
```
scan_id=20260504144224  pair=TST_USDT  price=0.03189  score=70
verdict=LEAN_BUY  target_pct=6.0  risk_pct=3.0
```

### `sportsbet.lm_sports_value_bets`
```
event_id=actionnet_290583  sport=basketball_nba
home=Detroit Pistons  away=Cleveland Cavaliers
market=h2h  bet_type=Cleveland Cavaliers ML  best_book=Bovada
event_id=actionnet_290575  sport=icehockey_nhl
home=Montreal Canadiens  away=Buffalo Sabres
market=totals  bet_type=Under 6.50  best_book=DraftKings
```

---

## 9. Notable observations / risks

1. **Backtest data volume is enormous** — `bt_backtest_trades`
   (~32.7M rows in `backtests`; ~27M mirrored in `stocks`) dominates storage.
   Queries against it time out without tight indexes (confirmed during this
   scan).
2. **Two large copies of backtest trades** exist (`backtests` + `stocks`),
   which doubles footprint. Consider whether the `stocks` mirror is still
   needed.
3. **`deals` database is completely empty** — candidate for decommission or
   re-purpose.
4. **Memecoin and sports-betting pipelines are dormant** (since ~May 2026);
   their `_stats_cache` tables still refresh, so the surrounding code is
   partially alive, but the signal/bet production stopped.
5. **110 empty tables in `stocks`** inflate the schema and add surface area;
   several are clearly legacy scaffolds (paper trading, ML registry, crypto
   OHLCV/patterns, benchmark/regime matrices).
6. **Cross-DB consistency risk** — the per-database user model prevents
   cross-DB joins; any reconciliation must use the two-connection copy pattern
   (see `tools/db_backup_to_backups.py`).

---

## 10. Source

- Live schema pulled 2026-11-19 from `<DB_HOST>` via
  `information_schema.COLUMNS` / `.TABLES` / `.STATISTICS`, plus `SELECT`
  sample rows. Credentials resolved via the repo's a runtime resolver (path not documented here) +
  an operator-local credential store. No credentials or credential paths are documented in this
  document.
- Raw scan dump: `/tmp/db_schema_dump.json`, `/tmp/stocks_tables.json`
  (local, not committed).

---

## Appendix A — Verified corrections and gaps (audit3 review, 2026-11-19)

Checked against the live server while merging this spec. Confirmed correct:
`stocks` has **409** tables; `trading_picks` **147,127** rows with
`max(created_at)=2026-11-19 04:48`; `at_pick_outcomes` **63,108** rows with
`max(resolved_at)=2026-11-19 03:24`; `bt_backtest_runs` **285** rows. The
freshness calls in §2.4 hold.

Four gaps matter enough to fix before this spec is used as ground truth.

### A.1 Price / market-data tables are absent from the spec

These are the tables that make any return, benchmark or selection-alpha
calculation possible, and none of them are documented above:

| Table | Rows | Grain | Note |
|---|---|---|---|
| `crypto_ohlcv` | 1,708,142 | 333 symbols, `timeframe` column, **ms-epoch** `timestamp` | usable to 2026-11-19 |
| `stock_ohlcv` | 459,467 | 1h bars | used by the equity/ETF backtests |
| `equity_daily_ohlcv` | 288,522 | daily | `trade_date` (a `DATE`) |
| `etf_daily_ohlcv` | 125,564 | daily | `trade_date` |
| `fx_prices` | 3,855 | daily, 15 pairs | **stale — span ends 2026-02-09** |
| `cp_prices` | 4,857 | daily crypto pairs | `pair` like `AAVE-USD` |
| `daily_prices` | 66,027 | daily, includes `adj_close` | equities |

A schema doc that omits these makes the audit look impossible: M1b selection
alpha (pick vs same-symbol hold) is computable *only* because they exist.

### A.2 `bt_backtest_runs.asset_class` is not trustworthy

All **285** rows are tagged `CRYPTO`, including `NZDUSD=X`, `AUDJPY=X` and
`GBPUSD=X`. Class must be derived from `symbol`; building class aggregates on the
stored column produces silently wrong results. `alpha_engine/audit3_evidence.py`
derives it and reports the disagreements (11 at the last run).

### A.3 `bt_backtest_trades` cannot be scanned ad hoc

≈**32.7M** rows measured by `COUNT(*)` (`TABLE_ROWS` estimates 34.6M — the
estimate drifts, which is exactly why A.6 says to trust freshness over counts).
Naive `COUNT(*)`/range scans time out from CI. Pre-aggregate by
`(strategy, symbol, asset_class, month)` before any analysis touches it.

### A.4 The forex pipeline is stale end-to-end

`fx_prices` ends **2026-02-09** while the pick ledger runs to 2026-11-19, and its
keys are `AUDCAD`-style while the ledger uses `AUDJPY=X` / `AUD-USD`. Result:
**211 forex picks currently have no computable alpha** — not because the analysis
is hard, but because the data and the naming disagree. Backfill and mapping are
tracked as E11 in `docs/EDGE_IDEAS_BACKLOG_2026-11-19.md`.

### A.5 Two symbol/class conventions worth writing down

- `EURUSDT` appears as `FOREX` in the pick ledger though it is a crypto pair.
  Anything quoting in `USDT`/`USDC` should classify as CRYPTO regardless of the
  stored class.
- Class is a property of the **exposure**, not the wrapper: a row that trades SPY
  or TLT as a proxy should not be reclassified as ETF if it claims EQUITY/BOND.

### A.6 Prefer freshness over row counts

Counts in this spec change hourly (`at_pick_outcomes` and the `bt_*` tables are
written continuously). For staleness detection, `MAX(timestamp_column)` per table
is the durable field; `TABLE_ROWS` is an estimate that drifts.

---

## Appendix B — Machine-learning algorithms in the build

This appendix documents the ML algorithms actually implemented in the repo and
how they map onto the database tables above. It is written from the codebase
(`alpha_engine/`, `ml_consensus/`, `ml_gatekeeper/`, `ml_*` modules), not from
the schema alone. It is a *ground-truth map* of what ML is currently running,
what it is trained on, and which tables hold its artifacts.

### B.1 Inventory of live ML systems

| Module | Algorithm / approach | Trained on | Primary output | Status |
|---|---|---|---|---|
| `alpha_engine/ml_engine_v2.py` | Multi-model ensemble: XGBoost + LightGBM + RandomForest + LogisticRegression (`VotingClassifier`); `CalibratedClassifierCV`; `TimeSeriesSplit` (no shuffle); SMOTE / cost-sensitive / focal-loss for class imbalance; PR-AUC primary metric; validation-threshold tuning | Real closed picks (feedback loop) | Win-probability scores, filtered picks | Active (v2.0) |
| `alpha_engine/ml_ranker.py` | Heterogeneous stacking ensemble — XGBoost/LightGBM primary, RF + CatBoost secondary (CatBoost `has_time=True` ordered boosting); **Boruta feature selection** (shadow features + RF); ~40 engineered features pruned to ~15–20; triple-barrier labels; meta-labeling gate at p=0.65 | Closed picks | Ranked signals, feature importance | Active (Phase 9/13) |
| `ml_gatekeeper/gatekeeper.py` | Two models: (1) Pick-Quality classifier (P(profitable)), (2) Strategy-Regime router (rolling-window profitability per strategy+asset_class). Both trained on real closed picks with real PnL labels | 3,500+ resolved closed picks | Filtered pick JSON for dashboard | Active |
| `ml_consensus/consensus.py` | Multi-system agreement model — learns which *combinations* of independent systems produce winning trades (observed ~65.8–67.6% WR on real closed picks) | Real closed-pick outcomes | Consensus score / combined signals | Active |
| `crypto_fusion_predictor.py` | XGBRegressor ensemble + **GaussianHMM** (4-state regime model, `hmmlearn`) + StandardScaler + TimeSeriesSplit | OHLCV + funding/features | Crypto price/prediction + regime | Active |
| `walkerforward_validator.py` | Rolling-window walk-forward validation; composite score = weighted(Sharpe, CAGR, win-rate, PF, drawdown, beta) + proof score (p-value, bootstrap CI, feature drift) | Closed trades | Ranked strategy list for dashboard | Active |
| `regime_detector.py` / `market_regime_detector.py` | Multi-feature regime classifier (volatility via ATR/EWMA, trend, sentiment, liquidity); sometimes HMM-driven | Price/vol/VIX/macro | Regime label + recommended ensemble | Active |
| `alpha_engine/forward_validator.py` | Forward (out-of-sample) validation; flags overfit | Closed picks | Forward-validation flags | Active |
| `alpha_engine/score_booster.py` | Heuristic score boosting (non-ML, complements ML) | Picks | Boosted scores | Active |

### B.2 Training-data hygiene (important for review)

- **No synthetic data.** The gatekeeper, consensus, and engine all state
  explicitly they train *only* on real resolved picks from the audit dashboard.
- **Look-ahead bias controls.** `ml_engine_v2` uses 50+ properly lagged features,
  time-series-aware splits (`TimeSeriesSplit`), and removes leaky outcome
  features (entry_vs_optimal, hold_duration, MFE/MAE were removed in Phase 11
  of the ranker because they caused AUC=1.0).
- **Triple-barrier labeling.** The ranker labels trades +1 (TP hit) / 0
  (expired/uncertain) / −1 (SL hit) with asymmetric sample weights
  (loss=1.2, uncertain=0.5, win=1.0).
- **Cold-start fallback.** The ranker falls back to heuristic scoring when fewer
  than ~50 closed picks exist.

### B.3 Where ML artifacts live in the DB

The **`stocks`** database holds the ML operational tables. Freshness from the
live scan (2026-11-19):

| Table | What it stores | Rows | Freshness |
|---|---|---|---|
| `lm_signals` | Learning-machine generated signals | 113,134 | **active** (max signal_time 2026-11-19 05:09) |
| `lm_snapshots` | ML portfolio snapshots (value, PnL, drawdown) | 6,004 | **active** (2026-11-19 05:09) |
| `lm_kelly_fractions` | Kelly-criterion bankroll fractions per algo | 14 | **active** (2026-11-19 05:09) |
| `lm_position_sizing` | Kelly × vol-scalar × regime sizing decisions | 3,735 | active (2026-11-18 20:46) |
| `lm_market_regime` | HMM regime labels + Hurst/EWMA-vol/VIX composite | 796 | active (2026-11-18 20:50) |
| `lm_smart_consensus` | Multi-factor consensus scores (technical/smart-money/insider/analyst/momentum/social) | 2,304 | active (2026-11-17) |
| `lm_hour_learning` | Hour-level learning snapshots | 923 | active (2026-11-15) |
| `lm_challenger_showdown` | Tournament/challenger comparison | 192 | active (2026-11-17) |
| `ml_feature_store` | Engineered feature vectors (RSI, MACD, stoch, CCI, ROC, SMA, returns) | 396 | **stale** (max timestamp 2026-02-16) |
| `walk_forward_summary` | Walk-forward validation summary | 10 | **stale** (2026-02-09) |
| `lm_conviction_history` | High-conviction pick history | 12 | stale (2026-02-11) |
| `ml_model_registry` | Model metadata (type, horizon, features, hyperparams, metrics) | 0 | empty |
| `ml_models` | Model store | 0 | empty |
| `lm_model_versions` | Per-algo deployed model versions | 0 | empty |
| `lm_ensemble_weights` / `ml_ensemble_weights` | Ensemble weights | 0 | empty |
| `ml_ab_tests` | A/B experiment log | 0 | empty |
| `lm_prediction_calibration` / `ml_calibration_log` | Calibration curves | 0 | empty |
| `ml_learning_curve` | Learning-curve data | 14 | present |

The **`memecoin`** DB has ML stubs (`meme_ml_models`, `meme_ml_predictions`,
`ml_models`, `ml_model_performance`, `crypto_indicators/patterns/signals`) —
currently **empty** (0 rows). Crypto ML is written to `crypto_ohlcv` and
`psi_*` tables instead.

The **`sportsbet`** DB has an ML-augmented betting pipeline: `lm_sports_bets`
carries `ml_win_prob`, `ml_prediction`, `ml_should_bet`, `ml_model_type`,
`ml_confidence`, `ml_predicted_at`; `lm_sports_ml_predictions` holds the raw
predictions; `lm_sports_ml_metrics` is empty. Freshness: active through
2026-05-13 (bets), 2026-05-24 (odds) — see §5/§7.

### B.4 Recommended review focus for a web-AI strategy reviewer

1. **Ground truth for "what actually works"**: `bt_backtest_trades`
   (~32.7M rows) + `at_pick_outcomes` (63k resolved picks) are the only
   objective labels. Any new strategy evaluation should key off these.
2. **Feature engineering source**: `ml_feature_store` shows the current feature
   set (returns, RSI, MACD, stoch, Williams %R, CCI, ROC, SMA). The ranker's
   Boruta selection (`alpha_engine/ml_ranker.py`) prunes to ~15–20 features —
   review which survive.
3. **Regime conditioning**: `lm_market_regime` (HMM + Hurst + EWMA-vol + VIX +
   yield-curve) is the router that decides which strategy ensemble to run.
   New strategies should be regime-tagged to plug into this router.
4. **Consensus/unions**: `ml_consensus` learns which system *combinations*
   win — a new strategy thesis can be validated by checking it adds uncorrelated
   agreement to the existing ensemble.
5. **Sizing is Kelly-based**: `lm_kelly_fractions` + `lm_position_sizing`
   (Kelly × volatility-scalar × regime-modifier × decay) is the money
   management layer; any new signal should integrate here, not bypass it.
6. **Stale ML surface**: `ml_feature_store` (Feb 2026) and `walk_forward_summary`
   (Feb 2026) are stale; the empty `ml_model_registry`/`ml_models`/registry
   tables mean model versioning is not yet being persisted. A review should flag
   these as gaps — the live systems run on JSON artifacts, not the DB registry.

### B.5 Suggested new-strategy integrations

- **Diversify regime signals**: the regime detector drives ensemble selection;
  adding a correlation/cointegration or order-flow regime input would expand the
  `lm_market_regime` feature set (Hurst, EWMA-vol, VIX, yield curve already there).
- **Feature-store revival**: repopulate `ml_feature_store` (stale since Feb) to
  feed the ranker/gatekeeper from a single canonical feature table rather than
  per-module JSON.
- **Model registry**: start persisting `ml_model_registry` / `ml_models` /
  `lm_model_versions` so drift detection and rollback are DB-backed instead of
  file-backed.
- **Triple-barrier + meta-labeling** are already in the ranker; port the same
  labeling to the sports ML (`lm_sports_bets`) and memecoin pipelines for a
  consistent evaluation standard.
- **Use `bt_backtest_trades` pre-aggregates** (by strategy/symbol/asset_class/
  month) so new strategy backtests can be evaluated without full-table scans
  (A.3).

### B.6 Health & verdict — see the dedicated audit

A full ML health/staleness/verdict audit (live model reports + resolved-pick
ground truth) lives in
[`ML_SYSTEMS_HEALTH_AUDIT_2026-11-19.md`](ML_SYSTEMS_HEALTH_AUDIT_2026-11-19.md).

**Verdict in one line:** the ML layer is worth keeping — but only the validated
**gatekeeper + consensus + ~9 positive-EV strategies**; it is under-deployed,
not broken. Slightly modify + refresh, do not rewrite.

Key empirical numbers (2026-11-19):

- **Gatekeeper:** 12-fold walk-forward mean lift **10.44%** (p=0.008), true
  holdout PF **2.826**, passed-WR 61% vs 52.2% baseline → keep.
- **Consensus:** backtest WR 50.6% vs 41.9% single, cumulative PnL +38 vs −677
  → keep.
- **Mercury2:** top-3 hit rate 0%, IC ≈ 0 → weak/demote.
- **Crypto-ML:** trained 2026-02-25 (STALE ~9mo) → retrain.
- **Overall resolved picks:** WR 41.7%, avg PnL +0.085% → break-even as a
  pool; edge is concentrated in CRYPTO/FOREX and the strategy core above.
- **Positive-EV strategy core:** Multi-Timeframe Trend Alignment (87.1% WR,
  +2.79%), Price Acceleration Detector (77.4%, +2.25%), non_crypto_consensus,
  VerifiedStochRsi, Bollinger Squeeze, CCI Reversal, MeanReversionBB,
  luxalgo_confluence, claude_ml_moderate.
- **Net-negative to suppress:** Crypto RSI Scout (8.5% WR), Extreme Fear
  Contrarian, rapid_rsi_filter, gainer_compression, futures_momentum, meme,
  penny.
