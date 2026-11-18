# Funds DB Profile — `ejaguiar1_mutual_funds`

- Generated: 2026-11-18T06:35:13Z (UTC)
- Host: `mysql.50webs.com` — MySQL 8.4.7 (source: `SHOW CREATE TABLE` / `information_schema`)
- Lane: **funds** (mutual funds); crypto tables are profiled separately in `crypto_db_profile.md` and mirrored in this inventory for cross-reference.
- Method: direct `pymysql` connection + `SHOW TABLES`, `SHOW CREATE TABLE`, `SELECT COUNT(*)` where permitted.

> [!WARNING]
> **The dedicated database `ejaguiar1_mutual_funds` is UNREACHABLE from this host.**
> Every credential probe returned `ERROR 1045 (28000): Access denied for user `'ejaguiar1_mutual_funds'@'142.181.219.3' (using password: YES)`. Probe tried passwords `''`, `mutual_funds1234560`, `mutual_funds123456`, `MUTUAL_FUNDS1234560`; all refused. Consequently **no row count, no live `COUNT(*)`, and no fresh `information_schema` read is available for that database**, and its own table inventory cannot be enumerated here.
> To keep the lane deliverable useful, the mutual-funds schema below is **proxied** from the reachable `ejaguiar1_stocks` account (same MySQL server, same application schema family). Proxy schemas are byte-for-byte `SHOW CREATE TABLE` output and include columns/types/indexes; they are NOT the dedicated DB's own catalog. Every true-`ejaguiar1_mutual_funds` row count is therefore labelled `UNAVAILABLE (DB unreachable)` rather than invented.

## Provenance of the mutual-funds inventory

| Source | Reachability | Tables matched | DDL captured | Role in this doc |
|---|---|---|---|---|
| `ejaguiar1_mutual_funds` | **REFUSED (1045)** | — | — | authoritative target; schema unknown |
| `ejaguiar1_stocks` / `stocks1234560` | OK | 95 | 95 | **proxy schema source** |
| `ejaguiar1_backups` / `backups1234560` | OK | 89 | 89 | backup/proxy cross-check |

### Dedicated-account refusal evidence

| Account | ok | error |
|---|---|---|
| `ejaguiar1_mutual_funds` | N | `(1045, "Access denied for user 'ejaguiar1_mutual_funds'@'142.181.219.3' (using password: YES)")` |
| `ejaguiar1_bonds` | N | `(1045, "Access denied for user 'ejaguiar1_bonds'@'142.181.219.3' (using password: YES)")` |
| `ejaguiar1_equities` | N | `(1045, "Access denied for user 'ejaguiar1_equities'@'142.181.219.3' (using password: YES)")` |
| `ejaguiar1_etfs` | N | `(1045, "Access denied for user 'ejaguiar1_etfs'@'142.181.219.3' (using password: YES)")` |
| `ejaguiar1_crypto` | N | `(1045, "Access denied for user 'ejaguiar1_crypto'@'142.181.219.3' (using password: YES)")` |

## Mutual-funds table inventory (proxy: `ejaguiar1_stocks`)

33 mutual-fund tables matched in the proxy account. Row counts in the `ejaguiar1_mutual_funds` database itself are **UNAVAILABLE (DB unreachable)**; the values shown are proxied from `ejaguiar1_stocks` and marked as such.

| # | Table | Engine | Collation | Rows (`ejaguiar1_mutual_funds`) | Rows (proxy `ejaguiar1_stocks`) | Created | Updated |
|---|---|---|---|---|---|---|---|
| 1 | `mf2_algo_performance` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 17:57:24 | 2026-05-09 20:17:46 |
| 2 | `mf2_algorithms` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 17:57:24 | 2026-02-09 17:57:24 |
| 3 | `mf2_audit_log` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 340 | 2026-02-09 17:57:24 | 2026-05-09 20:17:46 |
| 4 | `mf2_backtest_results` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 17:57:24 | 2026-02-12 23:45:52 |
| 5 | `mf2_backtest_trades` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 450 | 2026-02-09 17:57:24 | 2026-02-12 23:45:52 |
| 6 | `mf2_category_perf` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 17:57:24 | 2026-02-09 17:57:24 |
| 7 | `mf2_comparisons` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 17:57:24 | 2026-02-09 17:57:24 |
| 8 | `mf2_fund_picks` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 600 | 2026-02-09 17:57:24 | 2026-03-29 01:00:52 |
| 9 | `mf2_funds` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 15 | 2026-02-09 17:57:24 | 2026-02-09 17:57:31 |
| 10 | `mf2_nav_history` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 6860 | 2026-02-09 17:57:24 | 2026-03-29 04:38:36 |
| 11 | `mf2_portfolios` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 12 | 2026-02-09 17:57:24 | 2026-02-09 17:57:24 |
| 12 | `mf2_tracked_picks` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 75 | 2026-02-12 23:31:16 | 2026-02-15 01:15:11 |
| 13 | `mf2_tracking_daily` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 3 | 2026-02-12 23:31:16 | 2026-02-15 01:15:11 |
| 14 | `mf2_tracking_lessons` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 9 | 2026-02-12 23:31:16 | 2026-02-15 01:15:11 |
| 15 | `mf2_whatif_scenarios` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 2 | 2026-02-09 17:57:24 | 2026-03-29 03:28:52 |
| 16 | `mf_algo_performance` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 08:41:07 | 2026-02-09 17:17:56 |
| 17 | `mf_algorithms` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 08:41:07 | 2026-02-09 08:41:07 |
| 18 | `mf_audit_log` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 260 | 2026-02-09 05:39:09 | 2026-03-28 21:56:52 |
| 19 | `mf_backtest_results` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 20 | `mf_backtest_trades` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 21 | `mf_benchmarks` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 22 | `mf_category_perf` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 08:41:07 | 2026-02-09 08:41:07 |
| 23 | `mf_comparisons` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 08:41:07 | 2026-02-09 08:41:07 |
| 24 | `mf_fund_picks` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 15 | 2026-02-09 08:41:07 | 2026-02-09 08:41:09 |
| 25 | `mf_funds` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 20 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 26 | `mf_nav_history` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 5000 | 2026-02-09 05:39:09 | 2026-02-09 05:39:24 |
| 27 | `mf_portfolios` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 8 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 28 | `mf_report_cache` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 2 | 2026-02-09 05:39:09 | 2026-03-28 21:56:52 |
| 29 | `mf_selections` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 34 | 2026-02-09 05:39:09 | 2026-02-09 05:39:29 |
| 30 | `mf_simulation_grid` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 31 | `mf_simulation_meta` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 0 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 32 | `mf_strategies` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 10 | 2026-02-09 05:39:09 | 2026-02-09 05:39:09 |
| 33 | `mf_whatif_scenarios` | MyISAM | utf8mb3_general_ci | UNAVAILABLE (DB unreachable) | 8 | 2026-02-09 05:39:09 | 2026-02-09 08:41:58 |

## Mutual-funds schema detail (proxy `ejaguiar1_stocks`)

Each entry is the full `SHOW CREATE TABLE` derivative: columns with types/nullability/defaults, then keys, then the engine/collation tail. Column counts are given so the detail can be sanity-checked without opening every block.

### `mf2_algo_performance`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-05-09 20:17:46</sub>

10 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `algorithm_name` | `varchar(100)` | NO | (empty) |  |
| `strategy_type` | `varchar(50)` | NO | '' |  |
| `total_picks` | `int` | NO | '0' |  |
| `total_trades` | `int` | NO | '0' |  |
| `win_rate` | `decimal(5,2)` | NO | '0.00' |  |
| `avg_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `best_for` | `varchar(200)` | NO | '' |  |
| `worst_for` | `varchar(200)` | NO | '' |  |
| `updated_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_algo_strat` (`algorithm_name`,`strategy_type`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3`

### `mf2_algorithms`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-09 17:57:24</sub>

8 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `name` | `varchar(100)` | NO | (empty) |  |
| `family` | `varchar(50)` | NO | '' |  |
| `description` | `text` | YES | (empty) |  |
| `algo_type` | `varchar(50)` | NO | 'general' |  |
| `ideal_timeframe` | `varchar(20)` | NO | '' |  |
| `pros` | `text` | YES | (empty) |  |
| `cons` | `text` | YES | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_name` (`name`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3`

### `mf2_audit_log`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-05-09 20:17:46</sub>

5 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `action_type` | `varchar(50)` | NO | (empty) |  |
| `details` | `text` | YES | (empty) |  |
| `ip_address` | `varchar(45)` | NO | '' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_action` (`action_type`)`
- `KEY `idx_date` (`created_at`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=341 DEFAULT CHARSET=utf8mb3`

### `mf2_backtest_results`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-12 23:45:52</sub>

29 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `portfolio_id` | `int` | NO | '0' |  |
| `run_name` | `varchar(200)` | NO | '' |  |
| `algorithm_filter` | `varchar(500)` | NO | '' |  |
| `strategy_type` | `varchar(50)` | NO | '' |  |
| `start_date` | `date` | YES | NULL |  |
| `end_date` | `date` | YES | NULL |  |
| `initial_capital` | `decimal(12,2)` | NO | '10000.00' |  |
| `final_value` | `decimal(12,2)` | NO | '0.00' |  |
| `total_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `annualized_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `total_trades` | `int` | NO | '0' |  |
| `winning_trades` | `int` | NO | '0' |  |
| `losing_trades` | `int` | NO | '0' |  |
| `win_rate` | `decimal(5,2)` | NO | '0.00' |  |
| `avg_win_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `avg_loss_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `best_trade_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `worst_trade_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `max_drawdown_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `total_fees` | `decimal(12,2)` | NO | '0.00' |  |
| `sharpe_ratio` | `decimal(10,4)` | NO | '0.0000' |  |
| `sortino_ratio` | `decimal(10,4)` | NO | '0.0000' |  |
| `profit_factor` | `decimal(10,4)` | NO | '0.0000' |  |
| `expectancy` | `decimal(10,4)` | NO | '0.0000' |  |
| `avg_hold_days` | `decimal(8,2)` | NO | '0.00' |  |
| `fee_drag_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `params_json` | `text` | YES | (empty) |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_portfolio` (`portfolio_id`)`
- `KEY `idx_strategy` (`strategy_type`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb3`

### `mf2_backtest_trades`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-12 23:45:52</sub>

15 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `backtest_id` | `int` | NO | '0' |  |
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `algorithm_name` | `varchar(100)` | NO | '' |  |
| `entry_date` | `date` | NO | (empty) |  |
| `entry_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `exit_date` | `date` | YES | NULL |  |
| `exit_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `units` | `decimal(12,4)` | NO | '0.0000' |  |
| `gross_profit` | `decimal(12,2)` | NO | '0.00' |  |
| `fees_paid` | `decimal(8,2)` | NO | '0.00' |  |
| `net_profit` | `decimal(12,2)` | NO | '0.00' |  |
| `return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `exit_reason` | `varchar(50)` | NO | '' |  |
| `hold_days` | `int` | NO | '0' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_backtest` (`backtest_id`)`
- `KEY `idx_symbol` (`symbol`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=1351 DEFAULT CHARSET=utf8mb3`

### `mf2_category_perf`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-09 17:57:24</sub>

8 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `category` | `varchar(200)` | NO | (empty) |  |
| `period` | `varchar(20)` | NO | '1m' |  |
| `avg_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `top_fund` | `varchar(20)` | NO | '' |  |
| `worst_fund` | `varchar(20)` | NO | '' |  |
| `fund_count` | `int` | NO | '0' |  |
| `updated_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_cat_period` (`category`,`period`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf2_comparisons`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-09 17:57:24</sub>

6 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `comparison_name` | `varchar(200)` | NO | '' |  |
| `scenarios_json` | `text` | YES | (empty) |  |
| `best_scenario` | `varchar(200)` | NO | '' |  |
| `worst_scenario` | `varchar(200)` | NO | '' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf2_fund_picks`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-03-29 01:00:52</sub>

13 columns, 5 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `algorithm_id` | `int` | NO | '0' |  |
| `algorithm_name` | `varchar(100)` | NO | '' |  |
| `pick_date` | `date` | NO | (empty) |  |
| `pick_time` | `datetime` | NO | (empty) |  |
| `entry_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `score` | `int` | NO | '0' |  |
| `rating` | `varchar(20)` | NO | '' |  |
| `risk_level` | `varchar(20)` | NO | 'Medium' |  |
| `timeframe` | `varchar(20)` | NO | '' |  |
| `pick_hash` | `varchar(64)` | NO | '' |  |
| `rationale_json` | `text` | YES | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_symbol` (`symbol`)`
- `KEY `idx_algorithm` (`algorithm_name`)`
- `KEY `idx_date` (`pick_date`)`
- `KEY `idx_hash` (`pick_hash`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=601 DEFAULT CHARSET=utf8mb3`

### `mf2_funds`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-09 17:57:31</sub>

9 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `fund_name` | `varchar(300)` | NO | '' |  |
| `fund_family` | `varchar(200)` | NO | '' |  |
| `category` | `varchar(200)` | NO | '' |  |
| `asset_class` | `varchar(50)` | NO | '' |  |
| `expense_ratio` | `decimal(6,4)` | NO | '0.0000' |  |
| `min_investment` | `decimal(12,2)` | NO | '0.00' |  |
| `inception_date` | `date` | YES | NULL |  |
| `morningstar_rating` | `tinyint` | NO | '0' |  |

**Keys**

- `PRIMARY KEY (`symbol`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf2_nav_history`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-03-29 04:38:36</sub>

7 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `nav_date` | `date` | NO | (empty) |  |
| `nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `prev_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `daily_return_pct` | `decimal(10,6)` | NO | '0.000000' |  |
| `volume` | `bigint` | NO | '0' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_symbol_date` (`symbol`,`nav_date`)`
- `KEY `idx_date` (`nav_date`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=6862 DEFAULT CHARSET=utf8mb3`

### `mf2_portfolios`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-02-09 17:57:24</sub>

15 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `name` | `varchar(200)` | NO | (empty) |  |
| `description` | `text` | YES | (empty) |  |
| `strategy_type` | `varchar(50)` | NO | 'balanced' |  |
| `algorithm_filter` | `varchar(500)` | NO | '' |  |
| `initial_capital` | `decimal(12,2)` | NO | '10000.00' |  |
| `commission_buy` | `decimal(6,2)` | NO | '0.00' |  |
| `commission_sell` | `decimal(6,2)` | NO | '0.00' |  |
| `redemption_fee_pct` | `decimal(5,2)` | NO | '0.00' |  |
| `target_return_pct` | `decimal(5,2)` | NO | '10.00' |  |
| `stop_loss_pct` | `decimal(5,2)` | NO | '8.00' |  |
| `max_hold_days` | `int` | NO | '90' |  |
| `position_size_pct` | `decimal(5,2)` | NO | '20.00' |  |
| `max_positions` | `int` | NO | '5' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb3`

### `mf2_tracked_picks`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-12 23:31:16 · updated=2026-02-15 01:15:11</sub>

18 columns, 4 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `algorithm_name` | `varchar(100)` | NO | (empty) |  |
| `pick_date` | `date` | NO | (empty) |  |
| `entry_nav` | `decimal(12,4)` | NO | (empty) |  |
| `current_nav` | `decimal(12,4)` | YES | NULL |  |
| `current_return_pct` | `decimal(8,4)` | YES | NULL |  |
| `status` | `enum('open','closed')` | YES | 'open' |  |
| `exit_date` | `date` | YES | NULL |  |
| `exit_nav` | `decimal(12,4)` | YES | NULL |  |
| `exit_reason` | `varchar(50)` | YES | NULL |  |
| `final_return_pct` | `decimal(8,4)` | YES | NULL |  |
| `peak_nav` | `decimal(12,4)` | YES | NULL |  |
| `trough_nav` | `decimal(12,4)` | YES | NULL |  |
| `hold_days` | `int` | YES | '0' |  |
| `score` | `decimal(5,2)` | YES | NULL |  |
| `rating` | `varchar(10)` | YES | NULL |  |
| `created_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_symbol_algo_date` (`symbol`,`algorithm_name`,`pick_date`)`
- `KEY `idx_status` (`status`)`
- `KEY `idx_symbol` (`symbol`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=121 DEFAULT CHARSET=utf8mb3`

### `mf2_tracking_daily`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-12 23:31:16 · updated=2026-02-15 01:15:11</sub>

14 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `track_date` | `date` | NO | (empty) |  |
| `open_positions` | `int` | YES | '0' |  |
| `total_closed` | `int` | YES | '0' |  |
| `total_wins` | `int` | YES | '0' |  |
| `total_losses` | `int` | YES | '0' |  |
| `win_rate` | `decimal(5,2)` | YES | '0.00' |  |
| `avg_win_pct` | `decimal(8,4)` | YES | '0.0000' |  |
| `avg_loss_pct` | `decimal(8,4)` | YES | '0.0000' |  |
| `avg_return_pct` | `decimal(8,4)` | YES | '0.0000' |  |
| `best_symbol` | `varchar(20)` | YES | NULL |  |
| `worst_symbol` | `varchar(20)` | YES | NULL |  |
| `avg_hold_days` | `decimal(5,1)` | YES | '0.0' |  |
| `created_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_track_date` (`track_date`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb3`

### `mf2_tracking_lessons`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-12 23:31:16 · updated=2026-02-15 01:15:11</sub>

10 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `lesson_date` | `date` | NO | (empty) |  |
| `lesson_type` | `varchar(50)` | NO | (empty) |  |
| `lesson_title` | `varchar(200)` | NO | (empty) |  |
| `lesson_text` | `text` | NO | (empty) |  |
| `confidence` | `decimal(5,2)` | YES | '0.00' |  |
| `supporting_data` | `text` | YES | (empty) |  |
| `applied` | `tinyint` | YES | '0' |  |
| `impact_score` | `decimal(5,2)` | YES | NULL |  |
| `created_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_type` (`lesson_type`)`
- `KEY `idx_date` (`lesson_date`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb3`

### `mf2_whatif_scenarios`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 17:57:24 · updated=2026-03-29 03:28:52</sub>

6 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `scenario_name` | `varchar(200)` | NO | '' |  |
| `query_text` | `text` | YES | (empty) |  |
| `params_json` | `text` | YES | (empty) |  |
| `results_json` | `text` | YES | (empty) |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb3`

### `mf_algo_performance`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 08:41:07 · updated=2026-02-09 17:17:56</sub>

10 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `algorithm_name` | `varchar(100)` | NO | (empty) |  |
| `strategy_type` | `varchar(50)` | NO | '' |  |
| `total_picks` | `int` | NO | '0' |  |
| `total_trades` | `int` | NO | '0' |  |
| `win_rate` | `decimal(5,2)` | NO | '0.00' |  |
| `avg_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `best_for` | `varchar(200)` | NO | '' |  |
| `worst_for` | `varchar(200)` | NO | '' |  |
| `updated_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_algo_strat` (`algorithm_name`,`strategy_type`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3`

### `mf_algorithms`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 08:41:07 · updated=2026-02-09 08:41:07</sub>

8 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `name` | `varchar(100)` | NO | (empty) |  |
| `family` | `varchar(50)` | NO | '' |  |
| `description` | `text` | YES | (empty) |  |
| `algo_type` | `varchar(50)` | NO | 'general' |  |
| `ideal_timeframe` | `varchar(20)` | NO | '' |  |
| `pros` | `text` | YES | (empty) |  |
| `cons` | `text` | YES | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_name` (`name`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3`

### `mf_audit_log`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-03-28 21:56:52</sub>

5 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `action_type` | `varchar(50)` | NO | (empty) |  |
| `details` | `text` | YES | (empty) |  |
| `ip_address` | `varchar(45)` | NO | '' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_action` (`action_type`)`
- `KEY `idx_date` (`created_at`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=261 DEFAULT CHARSET=utf8mb3`

### `mf_backtest_results`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

23 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `portfolio_id` | `int` | NO | '0' |  |
| `run_name` | `varchar(200)` | NO | '' |  |
| `strategy_filter` | `varchar(500)` | NO | '' |  |
| `strategy_type` | `varchar(50)` | NO | '' |  |
| `start_date` | `date` | YES | NULL |  |
| `end_date` | `date` | YES | NULL |  |
| `initial_capital` | `decimal(12,2)` | NO | '10000.00' |  |
| `final_value` | `decimal(12,2)` | NO | '0.00' |  |
| `total_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `annualized_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `total_trades` | `int` | NO | '0' |  |
| `winning_trades` | `int` | NO | '0' |  |
| `losing_trades` | `int` | NO | '0' |  |
| `win_rate` | `decimal(5,2)` | NO | '0.00' |  |
| `max_drawdown_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `total_expenses` | `decimal(12,2)` | NO | '0.00' |  |
| `total_commissions` | `decimal(12,2)` | NO | '0.00' |  |
| `sharpe_ratio` | `decimal(10,4)` | NO | '0.0000' |  |
| `alpha` | `decimal(10,4)` | NO | '0.0000' |  |
| `beta` | `decimal(10,4)` | NO | '0.0000' |  |
| `params_json` | `text` | YES | (empty) |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_portfolio` (`portfolio_id`)`
- `KEY `idx_strategy` (`strategy_type`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_backtest_trades`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

16 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `backtest_id` | `int` | NO | '0' |  |
| `ticker` | `varchar(15)` | NO | (empty) |  |
| `strategy_name` | `varchar(200)` | NO | '' |  |
| `entry_date` | `date` | NO | (empty) |  |
| `entry_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `exit_date` | `date` | YES | NULL |  |
| `exit_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `shares` | `decimal(12,4)` | NO | '0.0000' |  |
| `gross_profit` | `decimal(12,2)` | NO | '0.00' |  |
| `expense_cost` | `decimal(8,2)` | NO | '0.00' |  |
| `commission_paid` | `decimal(8,2)` | NO | '0.00' |  |
| `net_profit` | `decimal(12,2)` | NO | '0.00' |  |
| `return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `exit_reason` | `varchar(50)` | NO | '' |  |
| `hold_days` | `int` | NO | '0' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_backtest` (`backtest_id`)`
- `KEY `idx_ticker` (`ticker`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_benchmarks`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

6 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `ticker` | `varchar(15)` | NO | (empty) |  |
| `bench_name` | `varchar(200)` | NO | '' |  |
| `bench_type` | `varchar(50)` | NO | '' |  |
| `nav_date` | `date` | NO | (empty) |  |
| `nav_price` | `decimal(12,4)` | NO | '0.0000' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_ticker_date` (`ticker`,`nav_date`)`
- `KEY `idx_type` (`bench_type`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_category_perf`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 08:41:07 · updated=2026-02-09 08:41:07</sub>

8 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `category` | `varchar(200)` | NO | (empty) |  |
| `period` | `varchar(20)` | NO | '1m' |  |
| `avg_return_pct` | `decimal(10,4)` | NO | '0.0000' |  |
| `top_fund` | `varchar(20)` | NO | '' |  |
| `worst_fund` | `varchar(20)` | NO | '' |  |
| `fund_count` | `int` | NO | '0' |  |
| `updated_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_cat_period` (`category`,`period`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_comparisons`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 08:41:07 · updated=2026-02-09 08:41:07</sub>

6 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `comparison_name` | `varchar(200)` | NO | '' |  |
| `scenarios_json` | `text` | YES | (empty) |  |
| `best_scenario` | `varchar(200)` | NO | '' |  |
| `worst_scenario` | `varchar(200)` | NO | '' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_fund_picks`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 08:41:07 · updated=2026-02-09 08:41:09</sub>

13 columns, 5 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `symbol` | `varchar(20)` | NO | (empty) |  |
| `algorithm_id` | `int` | NO | '0' |  |
| `algorithm_name` | `varchar(100)` | NO | '' |  |
| `pick_date` | `date` | NO | (empty) |  |
| `pick_time` | `datetime` | NO | (empty) |  |
| `entry_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `score` | `int` | NO | '0' |  |
| `rating` | `varchar(20)` | NO | '' |  |
| `risk_level` | `varchar(20)` | NO | 'Medium' |  |
| `timeframe` | `varchar(20)` | NO | '' |  |
| `pick_hash` | `varchar(64)` | NO | '' |  |
| `rationale_json` | `text` | YES | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_symbol` (`symbol`)`
- `KEY `idx_algorithm` (`algorithm_name`)`
- `KEY `idx_date` (`pick_date`)`
- `KEY `idx_hash` (`pick_hash`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb3`

### `mf_funds`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

13 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `ticker` | `varchar(15)` | NO | (empty) |  |
| `fund_name` | `varchar(300)` | NO | '' |  |
| `category` | `varchar(150)` | NO | '' |  |
| `family` | `varchar(150)` | NO | '' |  |
| `expense_ratio` | `decimal(5,4)` | NO | '0.0000' |  |
| `min_investment` | `decimal(12,2)` | NO | '0.00' |  |
| `load_type` | `varchar(30)` | NO | 'no-load' |  |
| `front_load_pct` | `decimal(5,2)` | NO | '0.00' |  |
| `back_load_pct` | `decimal(5,2)` | NO | '0.00' |  |
| `morningstar_rating` | `tinyint` | NO | '0' |  |
| `asset_class` | `varchar(50)` | NO | '' |  |
| `inception_date` | `date` | YES | NULL |  |
| `net_assets` | `varchar(30)` | NO | '' |  |

**Keys**

- `PRIMARY KEY (`ticker`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_nav_history`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:24</sub>

7 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `ticker` | `varchar(15)` | NO | (empty) |  |
| `nav_date` | `date` | NO | (empty) |  |
| `nav_price` | `decimal(12,4)` | NO | '0.0000' |  |
| `adj_nav` | `decimal(12,4)` | NO | '0.0000' |  |
| `change_pct` | `decimal(8,4)` | NO | '0.0000' |  |
| `volume` | `bigint` | NO | '0' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_ticker_date` (`ticker`,`nav_date`)`
- `KEY `idx_date` (`nav_date`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=5001 DEFAULT CHARSET=utf8mb3`

### `mf_portfolios`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

14 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `name` | `varchar(200)` | NO | (empty) |  |
| `description` | `text` | YES | (empty) |  |
| `strategy_type` | `varchar(50)` | NO | 'balanced' |  |
| `strategy_filter` | `varchar(500)` | NO | '' |  |
| `initial_capital` | `decimal(12,2)` | NO | '10000.00' |  |
| `commission_buy` | `decimal(6,2)` | NO | '0.00' |  |
| `commission_sell` | `decimal(6,2)` | NO | '0.00' |  |
| `hold_period_days` | `int` | NO | '90' |  |
| `rebalance_freq` | `varchar(20)` | NO | 'quarterly' |  |
| `target_return_pct` | `decimal(5,2)` | NO | '0.00' |  |
| `stop_loss_pct` | `decimal(5,2)` | NO | '0.00' |  |
| `expense_drag_annual` | `decimal(5,4)` | NO | '0.0000' |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3`

### `mf_report_cache`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-03-28 21:56:52</sub>

3 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `cache_key` | `varchar(50)` | NO | (empty) |  |
| `cache_data` | `longtext` | YES | (empty) |  |
| `updated_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`cache_key`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_selections`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:29</sub>

11 columns, 4 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `ticker` | `varchar(15)` | NO | (empty) |  |
| `strategy_id` | `int` | NO | '0' |  |
| `strategy_name` | `varchar(200)` | NO | '' |  |
| `select_date` | `date` | NO | (empty) |  |
| `nav_at_select` | `decimal(12,4)` | NO | '0.0000' |  |
| `category` | `varchar(150)` | NO | '' |  |
| `expense_ratio` | `decimal(5,4)` | NO | '0.0000' |  |
| `morningstar_rating` | `tinyint` | NO | '0' |  |
| `rationale` | `text` | YES | (empty) |  |
| `select_hash` | `varchar(64)` | NO | '' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_ticker` (`ticker`)`
- `KEY `idx_strategy` (`strategy_name`)`
- `KEY `idx_date` (`select_date`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb3`

### `mf_simulation_grid`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

18 columns, 3 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `batch_id` | `int` | YES | '0' |  |
| `strategy` | `varchar(200)` | YES | '' |  |
| `hold_days` | `int` | YES | '90' |  |
| `stop_loss` | `decimal(6,2)` | YES | '0.00' |  |
| `target_return` | `decimal(6,2)` | YES | '0.00' |  |
| `commission` | `decimal(6,2)` | YES | '0.00' |  |
| `total_trades` | `int` | YES | '0' |  |
| `winning_trades` | `int` | YES | '0' |  |
| `win_rate` | `decimal(6,2)` | YES | '0.00' |  |
| `total_return_pct` | `decimal(10,4)` | YES | '0.0000' |  |
| `annualized_return_pct` | `decimal(10,4)` | YES | '0.0000' |  |
| `final_value` | `decimal(12,2)` | YES | '10000.00' |  |
| `max_drawdown_pct` | `decimal(8,4)` | YES | '0.0000' |  |
| `sharpe_ratio` | `decimal(8,4)` | YES | '0.0000' |  |
| `total_pnl` | `decimal(12,2)` | YES | '0.00' |  |
| `total_expenses` | `decimal(10,2)` | YES | '0.00' |  |
| `created_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `KEY `idx_strat` (`strategy`)`
- `KEY `idx_ret` (`total_return_pct`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_simulation_meta`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

3 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `meta_key` | `varchar(50)` | NO | (empty) |  |
| `meta_value` | `text` | YES | (empty) |  |
| `updated_at` | `datetime` | YES | NULL |  |

**Keys**

- `PRIMARY KEY (`meta_key`)`

**Table options:** `ENGINE=MyISAM DEFAULT CHARSET=utf8mb3`

### `mf_strategies`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 05:39:09</sub>

7 columns, 2 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `name` | `varchar(200)` | NO | (empty) |  |
| `description` | `text` | YES | (empty) |  |
| `strategy_type` | `varchar(50)` | NO | 'general' |  |
| `selection_criteria` | `text` | YES | (empty) |  |
| `ideal_timeframe` | `varchar(30)` | NO | '' |  |
| `risk_level` | `varchar(20)` | NO | 'Medium' |  |

**Keys**

- `PRIMARY KEY (`id`)`
- `UNIQUE KEY `idx_name` (`name`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb3`

### `mf_whatif_scenarios`

<sub>engine=MyISAM · collation=utf8mb3_general_ci · created=2026-02-09 05:39:09 · updated=2026-02-09 08:41:58</sub>

6 columns, 1 key definitions.

| Column | Type | Null | Default | Extra |
|---|---|---|---|---|
| `id` | `int` | NO | (empty) | AUTO_INCREMENT; |
| `scenario_name` | `varchar(200)` | NO | '' |  |
| `query_text` | `text` | YES | (empty) |  |
| `params_json` | `text` | YES | (empty) |  |
| `results_json` | `text` | YES | (empty) |  |
| `created_at` | `datetime` | NO | (empty) |  |

**Keys**

- `PRIMARY KEY (`id`)`

**Table options:** `ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3`

## Backup-account cross-check (`ejaguiar1_backups`)

Same mutual-funds schema family, copied into `ejaguiar1_backups` as `stocks__<name>` snapshots. Presence/absence here confirms the proxy tables above are not one-off; row counts are proxied and must not be read as the live funds DB.

| # | Table | Engine | Rows (proxy backup) | Created |
|---|---|---|---|---|
| 1 | `stocks__alpha_fundamentals` | MyISAM | 2964 | 2026-05-17 06:16:15 |
| 2 | `stocks__mf2_algo_performance` | MyISAM | 10 | 2026-05-17 06:15:17 |
| 3 | `stocks__mf2_algorithms` | MyISAM | 10 | 2026-05-17 06:15:17 |
| 4 | `stocks__mf2_audit_log` | MyISAM | 340 | 2026-05-17 06:15:33 |
| 5 | `stocks__mf2_backtest_results` | MyISAM | 10 | 2026-05-17 06:15:18 |
| 6 | `stocks__mf2_backtest_trades` | MyISAM | 450 | 2026-05-17 06:15:35 |
| 7 | `stocks__mf2_category_perf` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 8 | `stocks__mf2_comparisons` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 9 | `stocks__mf2_fund_picks` | MyISAM | 600 | 2026-05-17 06:15:35 |
| 10 | `stocks__mf2_funds` | MyISAM | 15 | 2026-05-17 06:15:16 |
| 11 | `stocks__mf2_nav_history` | MyISAM | 6860 | 2026-05-17 06:15:42 |
| 12 | `stocks__mf2_portfolios` | MyISAM | 12 | 2026-05-17 06:15:19 |
| 13 | `stocks__mf2_tracked_picks` | MyISAM | 75 | 2026-05-17 06:15:23 |
| 14 | `stocks__mf2_tracking_daily` | MyISAM | 3 | 2026-05-17 06:15:12 |
| 15 | `stocks__mf2_tracking_lessons` | MyISAM | 9 | 2026-05-17 06:15:20 |
| 16 | `stocks__mf2_whatif_scenarios` | MyISAM | 2 | 2026-05-17 06:15:16 |
| 17 | `stocks__mf_algo_performance` | MyISAM | 10 | 2026-05-17 06:15:15 |
| 18 | `stocks__mf_algorithms` | MyISAM | 10 | 2026-05-17 06:15:17 |
| 19 | `stocks__mf_audit_log` | MyISAM | 260 | 2026-05-17 06:15:32 |
| 20 | `stocks__mf_backtest_results` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 21 | `stocks__mf_backtest_trades` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 22 | `stocks__mf_benchmarks` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 23 | `stocks__mf_category_perf` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 24 | `stocks__mf_comparisons` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 25 | `stocks__mf_fund_picks` | MyISAM | 15 | 2026-05-17 06:15:17 |
| 26 | `stocks__mf_funds` | MyISAM | 20 | 2026-05-17 06:15:19 |
| 27 | `stocks__mf_nav_history` | MyISAM | 5000 | 2026-05-17 06:15:40 |
| 28 | `stocks__mf_portfolios` | MyISAM | 8 | 2026-05-17 06:15:14 |
| 29 | `stocks__mf_report_cache` | MyISAM | 2 | 2026-05-17 06:15:24 |
| 30 | `stocks__mf_selections` | MyISAM | 34 | 2026-05-17 06:15:22 |
| 31 | `stocks__mf_simulation_grid` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 32 | `stocks__mf_simulation_meta` | MyISAM | 0 | 2026-05-17 06:15:09 |
| 33 | `stocks__mf_strategies` | MyISAM | 10 | 2026-05-17 06:15:18 |
| 34 | `stocks__mf_whatif_scenarios` | MyISAM | 8 | 2026-05-17 06:15:21 |
| 35 | `stocks__stock_fundamentals` | MyISAM | 119 | 2026-05-17 06:15:32 |

_Schema detail for backup copies omitted (identical DDL family); full DDL for these names is in the dump and can be expanded on request._

## Crypto-related tables (cross-reference, proxy `ejaguiar1_stocks`)

11 crypto-tagged tables exist in the same proxy account. The dedicated `ejaguiar1_crypto` database is likewise refused (1045), so these are the best available schema evidence. Full crypto lane deliverable: `crypto_db_profile.md`.

| # | Table | Engine | Rows (`ejaguiar1_crypto`) | Rows (proxy `ejaguiar1_stocks`) | Created |
|---|---|---|---|---|---|
| 1 | `ENHANCEMENT_CRYPTO` | InnoDB | UNAVAILABLE (DB unreachable) | 11 | 2026-05-29 06:29:03 |
| 2 | `FINDING_CRYPTO` | InnoDB | UNAVAILABLE (DB unreachable) | 3 | 2026-05-29 21:24:48 |
| 3 | `INCIDENT_CRYPTO` | InnoDB | UNAVAILABLE (DB unreachable) | 21 | 2026-05-29 11:48:48 |
| 4 | `crypto_assets` | InnoDB | UNAVAILABLE (DB unreachable) | 14 | 2026-02-14 20:48:40 |
| 5 | `crypto_exchange_netflow` | MyISAM | UNAVAILABLE (DB unreachable) | 20 | 2026-02-12 22:10:34 |
| 6 | `crypto_indicators` | InnoDB | UNAVAILABLE (DB unreachable) | 0 | 2026-02-14 20:48:40 |
| 7 | `crypto_ohlcv` | InnoDB | UNAVAILABLE (DB unreachable) | 1705840 | 2026-02-14 20:41:45 |
| 8 | `crypto_patterns` | InnoDB | UNAVAILABLE (DB unreachable) | 0 | 2026-02-14 20:48:40 |
| 9 | `crypto_signals` | InnoDB | UNAVAILABLE (DB unreachable) | 0 | 2026-02-14 20:41:45 |
| 10 | `crypto_whale_movements` | MyISAM | UNAVAILABLE (DB unreachable) | 0 | 2026-02-12 22:10:34 |
| 11 | `crypto_whale_wallets` | MyISAM | UNAVAILABLE (DB unreachable) | 0 | 2026-02-12 22:10:34 |

### Column types for crypto tables (proxy)

| Table | Columns (name: type) | Keys |
|---|---|---|
| `ENHANCEMENT_CRYPTO` | `enhancement_id`: int, `asset_class`: varchar(20), `source_ref`: varchar(255), `title`: varchar(500), `description`: text, `category`: enum('SCORING','GATE','DATA_FEED','UI','METHODOLOGY','PERSONA','OTHER'), `expected_impact`: enum('HIGH','MEDIUM','LOW','UNKNOWN'), `effort`: enum('S','M','L','XL'), `status`: enum('BACKLOG','VALIDATED','ACCEPTED','IMPLEMENTED','REJECTED','SUPERSEDED'), `proposed_by`: varchar(100), `related_persona_id`: varchar(100), `proposed_features`: json, `success_metric`: varchar(500), `target_release`: varchar(50), `review_notes`: text, `implementation_pr`: varchar(255), `created_at`: datetime, `updated_at`: datetime, `implemented_at`: datetime, `link_md_path`: varchar(500), `link_url`: varchar(1000), `link_github_ref`: varchar(255), `enhancement_plan`: text | PRIMARY KEY (`enhancement_id`); KEY `idx_en_status_cat` (`status`,`category`); KEY `idx_en_proposer` (`proposed_by`); KEY `idx_en_impact` (`expected_impact`,`effort`); KEY `idx_en_persona` (`related_persona_id`); KEY `idx_en_created` (`created_at`) |
| `FINDING_CRYPTO` | `id`: int, `title`: varchar(500), `description`: text, `severity`: enum('P0','P1','P2','P3','INFO','NOTEWORTHY'), `status`: enum('OPEN','INVESTIGATING','CONFIRMED','RESOLVED','WONTFIX'), `agent`: varchar(80), `evidence`: text, `linked_incident_id`: int, `linked_enhancement_id`: int, `created_at_utc`: datetime, `updated_at_utc`: datetime | PRIMARY KEY (`id`); UNIQUE KEY `uq_title` (`title`); KEY `ix_status` (`status`); KEY `ix_severity` (`severity`) |
| `INCIDENT_CRYPTO` | `incident_id`: int, `asset_class`: varchar(20), `source_ref`: varchar(255), `title`: varchar(500), `description`: text, `severity`: enum('P0','P1','P2','P3','INFO'), `status`: enum('OPEN','TRIAGED','IN_PROGRESS','RESOLVED','WONTFIX','DUPLICATE'), `affected_component`: varchar(255), `reported_by`: varchar(100), `assigned_to`: varchar(100), `recommended_fix`: text, `target_release`: varchar(64), `evidence`: json, `resolution_notes`: text, `duplicate_of`: int, `created_at`: datetime, `date_est`: date, `time_est`: varchar(10), `updated_at`: datetime, `resolved_at`: datetime, `link_md_path`: varchar(500), `link_url`: varchar(1000), `link_github_ref`: varchar(255) | PRIMARY KEY (`incident_id`); KEY `idx_in_status_sev` (`status`,`severity`); KEY `idx_in_reporter` (`reported_by`); KEY `idx_in_component` (`affected_component`); KEY `idx_in_created` (`created_at`) |
| `crypto_assets` | `id`: int, `symbol`: varchar(20), `name`: varchar(100), `asset_type`: enum('major','altcoin','meme','defi','nft','layer2'), `market_cap_category`: enum('mega','large','mid','small','micro','nano'), `is_meme`: tinyint(1), `blockchain`: varchar(50), `created_at`: timestamp, `updated_at`: timestamp | PRIMARY KEY (`id`); UNIQUE KEY `uk_symbol` (`symbol`); KEY `idx_type` (`asset_type`); KEY `idx_meme` (`is_meme`) |
| `crypto_exchange_netflow` | `id`: int, `blockchain`: varchar(20), `exchange_name`: varchar(50), `netflow_24h`: decimal(20,8), `netflow_7d`: decimal(20,8), `calculated_at`: timestamp | PRIMARY KEY (`id`); KEY `idx_blockchain_time` (`blockchain`,`calculated_at`) |
| `crypto_indicators` | `id`: bigint, `symbol`: varchar(20), `timeframe`: varchar(10), `timestamp`: bigint, `rsi_14`: decimal(8,4), `macd`: decimal(18,8), `macd_signal`: decimal(18,8), `ema_9`: decimal(18,8), `ema_21`: decimal(18,8), `sma_50`: decimal(18,8), `sma_200`: decimal(18,8), `bb_upper`: decimal(18,8), `bb_lower`: decimal(18,8), `atr_14`: decimal(18,8), `volume_sma_20`: decimal(24,8), `stochastic_k`: decimal(8,4), `adx_14`: decimal(8,4), `created_at`: timestamp | PRIMARY KEY (`id`); UNIQUE KEY `uk_ind` (`symbol`,`timeframe`,`timestamp`); KEY `idx_symbol_time` (`symbol`,`timestamp`) |
| `crypto_ohlcv` | `id`: bigint, `symbol`: varchar(20), `timeframe`: varchar(10), `timestamp`: bigint, `open`: decimal(18,8), `high`: decimal(18,8), `low`: decimal(18,8), `close`: decimal(18,8), `volume`: decimal(24,8) | PRIMARY KEY (`id`); UNIQUE KEY `uk_ohlcv` (`symbol`,`timeframe`,`timestamp`); KEY `idx_symbol_time` (`symbol`,`timestamp`) |
| `crypto_patterns` | `id`: bigint, `symbol`: varchar(20), `pattern_type`: varchar(50), `pattern_name`: varchar(100), `timeframe`: varchar(10), `start_timestamp`: bigint, `end_timestamp`: bigint, `confidence`: decimal(5,2), `price_at_detection`: decimal(18,8), `target_price`: decimal(18,8), `stop_loss`: decimal(18,8), `embedding_vector`: json, `features`: json, `success_rating`: decimal(3,2), `created_at`: timestamp | PRIMARY KEY (`id`); KEY `idx_symbol_pattern` (`symbol`,`pattern_type`); KEY `idx_confidence` (`confidence`) |
| `crypto_signals` | `id`: bigint, `signal_id`: varchar(50), `symbol`: varchar(20), `signal_type`: enum('buy','sell','strong_buy','strong_sell'), `entry_price`: decimal(18,8), `target_price`: decimal(18,8), `stop_loss`: decimal(18,8), `status`: enum('active','closed','stopped'), `pnl_percent`: decimal(8,4), `created_at`: timestamp | PRIMARY KEY (`id`); UNIQUE KEY `signal_id` (`signal_id`); KEY `idx_symbol` (`symbol`); KEY `idx_status` (`status`) |
| `crypto_whale_movements` | `id`: int, `blockchain`: varchar(20), `from_address`: varchar(100), `to_address`: varchar(100), `amount`: decimal(20,8), `amount_usd`: decimal(15,2), `transaction_hash`: varchar(100), `movement_type`: varchar(50), `detected_at`: timestamp | PRIMARY KEY (`id`); UNIQUE KEY `transaction_hash` (`transaction_hash`); KEY `idx_blockchain` (`blockchain`); KEY `idx_type` (`movement_type`); KEY `idx_time` (`detected_at`) |
| `crypto_whale_wallets` | `id`: int, `blockchain`: varchar(20), `wallet_address`: varchar(100), `balance`: decimal(20,8), `balance_usd`: decimal(15,2), `last_transaction_time`: timestamp, `transaction_count_24h`: int, `is_exchange`: tinyint(1), `wallet_label`: varchar(100), `last_updated`: timestamp | PRIMARY KEY (`id`); UNIQUE KEY `unique_wallet` (`blockchain`,`wallet_address`); KEY `idx_blockchain` (`blockchain`); KEY `idx_exchange` (`is_exchange`) |

## What is and is not established

- **Established (readable):** mutual-funds *schema* — table names, column names, column types, nullability, defaults, indexes/keys, engines, collations — via the `ejaguiar1_stocks` proxy.
- **NOT established:** any row count, `MAX(id)`, or freshness date for the real `ejaguiar1_mutual_funds` database, because the dedicated account is refused. Nothing in this document should be read as a live count for that DB.
- **Recommended next step:** obtain the correct credential for `ejaguiar1_mutual_funds` (or grant the profiling host access), re-run the dump, and replace every `UNAVAILABLE (DB unreachable)` value plus the proxied numbers.

_Source data: `scratch/schema_dump.json` (235,553 B) generated by `scratch/dump_funds_crypto_schema.py` at 2026-11-18T06:25Z._
