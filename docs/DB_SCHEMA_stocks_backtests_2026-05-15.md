# MySQL Schema — ejaguiar1_stocks & ejaguiar1_backtests

Generated: 2026-05-15T14:33:48.486226Z · host `mysql.50webs.com:3306`
Source of truth: live `SHOW TABLES` / `DESCRIBE` introspection. Credentials redacted.

## `ejaguiar1_stocks`

- 322 tables

### `KIMI_GOLDMINE_ALERTS`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| alert_type | enum('new_goldmine','goldmine_lost','streak_hot','streak_cold','mega_winner','major_drawdown','system_error') | NO | MUL |  |
| severity | enum('info','warning','critical') | YES | MUL | info |
| source_type | varchar(50) | YES |  |  |
| source_name | varchar(100) | YES |  |  |
| algorithm_name | varchar(100) | YES |  |  |
| asset_symbol | varchar(50) | YES |  |  |
| pick_uuid | varchar(64) | YES |  |  |
| title | varchar(255) | YES |  |  |
| message | text | YES |  |  |
| details_json | json | YES |  |  |
| is_read | tinyint(1) | YES | MUL | 0 |
| read_at | datetime | YES |  |  |
| read_by | varchar(100) | YES |  |  |
| action_taken | varchar(50) | YES |  |  |
| action_result | text | YES |  |  |
| created_at | datetime | YES | MUL | CURRENT_TIMESTAMP |

### `KIMI_GOLDMINE_DAILY_SNAPSHOT`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | UNI |  |
| total_picks_active | int | YES |  | 0 |
| total_sources_active | int | YES |  | 0 |
| total_goldmines_active | int | YES |  | 0 |
| avg_return_all_active | decimal(10,4) | YES |  |  |
| best_performing_source | varchar(200) | YES |  |  |
| best_performing_return | decimal(10,4) | YES |  |  |
| worst_performing_source | varchar(200) | YES |  |  |
| worst_performing_return | decimal(10,4) | YES |  |  |
| new_picks_today | int | YES |  | 0 |
| new_winners_today | int | YES |  | 0 |
| new_goldmines_today | int | YES |  | 0 |
| alerts_generated | int | YES |  | 0 |
| critical_alerts | int | YES |  | 0 |
| snapshot_json | json | YES |  |  |
| created_at | datetime | YES | MUL | CURRENT_TIMESTAMP |

### `KIMI_GOLDMINE_PERFORMANCE`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| period | varchar(20) | NO | MUL |  |
| period_start | date | NO |  |  |
| period_end | date | NO |  |  |
| source_type | enum('stock','penny_stock','crypto','meme_coin','forex','mutual_fund','sports','alpha_engine') | NO | MUL |  |
| source_name | varchar(100) | NO |  |  |
| algorithm_name | varchar(100) | YES | MUL |  |
| total_picks | int | YES |  | 0 |
| active_picks | int | YES |  | 0 |
| resolved_picks | int | YES |  | 0 |
| winning_picks | int | YES |  | 0 |
| losing_picks | int | YES |  | 0 |
| win_rate_pct | decimal(6,2) | YES |  |  |
| win_rate_significance | varchar(20) | YES |  |  |
| avg_return_pct | decimal(10,4) | YES |  |  |
| median_return_pct | decimal(10,4) | YES |  |  |
| best_pick_return | decimal(10,4) | YES |  |  |
| worst_pick_return | decimal(10,4) | YES |  |  |
| total_return_pct | decimal(10,4) | YES |  |  |
| sharpe_ratio | decimal(8,4) | YES |  |  |
| sortino_ratio | decimal(8,4) | YES |  |  |
| max_drawdown_pct | decimal(8,4) | YES |  |  |
| profit_factor | decimal(8,4) | YES |  |  |
| expectancy | decimal(10,4) | YES |  |  |
| consecutive_wins | int | YES |  | 0 |
| consecutive_losses | int | YES |  | 0 |
| streak_status | enum('hot','cold','neutral') | YES |  | neutral |
| avg_days_held | decimal(6,2) | YES |  |  |
| avg_days_to_target | decimal(6,2) | YES |  |  |
| avg_days_to_stop | decimal(6,2) | YES |  |  |
| rank_by_return | int | YES |  |  |
| rank_by_sharpe | int | YES |  |  |
| rank_by_winrate | int | YES |  |  |
| overall_score | decimal(6,2) | YES | MUL |  |
| is_goldmine_worthy | tinyint(1) | YES | MUL | 0 |
| goldmine_reason | varchar(255) | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `KIMI_GOLDMINE_PICKS`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pick_uuid | varchar(64) | NO | UNI |  |
| source_type | enum('stock','penny_stock','crypto','meme_coin','forex','mutual_fund','sports','alpha_engine') | NO | MUL |  |
| source_name | varchar(100) | NO | MUL |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_symbol | varchar(50) | NO | MUL |  |
| asset_name | varchar(200) | YES |  |  |
| pick_direction | enum('long','short','neutral','over','under','spread') | NO |  | long |
| entry_price | decimal(15,6) | YES |  |  |
| entry_price_actual | decimal(15,6) | YES |  |  |
| target_price | decimal(15,6) | YES |  |  |
| stop_loss | decimal(15,6) | YES |  |  |
| target_pct | decimal(6,2) | YES |  |  |
| stop_pct | decimal(6,2) | YES |  |  |
| confidence_score | int | YES |  |  |
| kelly_fraction | decimal(6,4) | YES |  |  |
| suggested_position | decimal(10,2) | YES |  |  |
| timeframe_days | int | YES |  |  |
| pick_date | datetime | NO | MUL |  |
| pick_timestamp | int | YES |  |  |
| expected_exit_date | date | YES | MUL |  |
| current_price | decimal(15,6) | YES |  |  |
| current_return_pct | decimal(10,4) | YES | MUL |  |
| current_pnl | decimal(15,4) | YES |  |  |
| highest_price | decimal(15,6) | YES |  |  |
| lowest_price | decimal(15,6) | YES |  |  |
| peak_return_pct | decimal(10,4) | YES |  |  |
| exit_price | decimal(15,6) | YES |  |  |
| exit_date | datetime | YES |  |  |
| exit_return_pct | decimal(10,4) | YES |  |  |
| exit_pnl | decimal(15,4) | YES |  |  |
| exit_reason | enum('target_hit','stop_hit','time_exit','manual','expired','active') | YES |  |  |
| status | enum('pending','active','target_hit','stop_hit','partial_exit','closed','expired') | YES | MUL | pending |
| raw_data | json | YES |  |  |
| factors_json | json | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP |
| resolved_at | datetime | YES |  |  |

### `KIMI_GOLDMINE_SOURCES`  (14 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_type | enum('stock','penny_stock','crypto','meme_coin','forex','mutual_fund','sports','alpha_engine') | NO | MUL |  |
| source_name | varchar(100) | NO |  |  |
| source_slug | varchar(100) | NO | MUL |  |
| algorithm_name | varchar(100) | YES |  |  |
| algorithm_slug | varchar(100) | YES |  |  |
| display_name | varchar(200) | YES |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(100) | YES |  |  |
| ideal_timeframe | varchar(50) | YES |  |  |
| risk_level | enum('low','medium','high','very_high') | YES |  | medium |
| is_active | tinyint(1) | YES | MUL | 1 |
| auto_import | tinyint(1) | YES |  | 1 |
| import_frequency | varchar(20) | YES |  |  |
| source_api_endpoint | varchar(500) | YES |  |  |
| source_db_table | varchar(100) | YES |  |  |
| min_win_rate_for_goldmine | decimal(5,2) | YES |  | 55.00 |
| min_return_for_goldmine | decimal(6,2) | YES |  | 10.00 |
| min_sharpe_for_goldmine | decimal(5,2) | YES |  | 1.00 |
| min_samples_for_goldmine | int | YES |  | 10 |
| current_goldmine_status | tinyint(1) | YES | MUL | 0 |
| goldmine_achieved_date | date | YES |  |  |
| goldmine_lost_date | date | YES |  |  |
| total_goldmine_periods | int | YES |  | 0 |
| total_picks_all_time | int | YES |  | 0 |
| total_wins_all_time | int | YES |  | 0 |
| avg_return_all_time | decimal(10,4) | YES |  |  |
| best_streak | int | YES |  | 0 |
| worst_streak | int | YES |  | 0 |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `KIMI_GOLDMINE_WINNERS`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pick_uuid | varchar(64) | NO | MUL |  |
| source_type | enum('stock','penny_stock','crypto','meme_coin','forex','mutual_fund','sports','alpha_engine') | NO | MUL |  |
| source_name | varchar(100) | NO |  |  |
| algorithm_name | varchar(100) | NO |  |  |
| asset_symbol | varchar(50) | NO |  |  |
| asset_name | varchar(200) | YES |  |  |
| entry_price | decimal(15,6) | YES |  |  |
| pick_date | datetime | YES |  |  |
| exit_price | decimal(15,6) | YES |  |  |
| exit_return_pct | decimal(10,4) | YES | MUL |  |
| exit_date | datetime | YES |  |  |
| days_held | int | YES |  |  |
| winner_category | enum('mega_winner','consistent_performer','quick_hit','comeback_kid','hidden_gem') | NO | MUL |  |
| winner_reason | text | YES |  |  |
| outperformed_spy | tinyint(1) | YES |  | 0 |
| spy_return_same_period | decimal(10,4) | YES |  |  |
| alpha_generated | decimal(10,4) | YES |  |  |
| featured_date | date | YES | MUL |  |
| featured_in_newsletter | tinyint(1) | YES |  | 0 |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `algorithm_performance`  (23 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `algorithm_rolling_perf`  (3536 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_table | varchar(30) | NO | MUL | stock_picks |
| algorithm_name | varchar(100) | NO | MUL |  |
| period | varchar(10) | NO |  | 30d |
| calc_date | date | NO | MUL |  |
| total_picks | int | NO |  | 0 |
| resolved_picks | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(8,4) | NO |  | 0.0000 |
| created_at | datetime | NO |  |  |

### `algorithms`  (142 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |
| pros | text | YES |  |  |
| cons | text | YES |  |  |

### `alpha_earnings`  (242 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| quarter_end | date | NO |  |  |
| eps_actual | decimal(12,4) | NO |  | 0.0000 |
| eps_estimate | decimal(12,4) | NO |  | 0.0000 |
| eps_surprise | decimal(12,4) | NO |  | 0.0000 |
| surprise_pct | decimal(12,4) | NO |  | 0.0000 |
| fetch_date | date | NO | MUL |  |

### `alpha_factor_scores`  (2860 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| score_date | date | NO | MUL |  |
| momentum_12m | decimal(12,4) | NO |  | 0.0000 |
| momentum_6m | decimal(12,4) | NO |  | 0.0000 |
| momentum_3m | decimal(12,4) | NO |  | 0.0000 |
| momentum_1m | decimal(12,4) | NO |  | 0.0000 |
| momentum_score | decimal(12,4) | NO |  | 0.0000 |
| momentum_rank | int | NO |  | 0 |
| quality_roe | decimal(12,4) | NO |  | 0.0000 |
| quality_margins | decimal(12,4) | NO |  | 0.0000 |
| quality_fcf_yield | decimal(12,4) | NO |  | 0.0000 |
| quality_debt | decimal(12,4) | NO |  | 0.0000 |
| quality_score | decimal(12,4) | NO |  | 0.0000 |
| quality_rank | int | NO |  | 0 |
| value_pe | decimal(12,4) | NO |  | 0.0000 |
| value_pb | decimal(12,4) | NO |  | 0.0000 |
| value_ps | decimal(12,4) | NO |  | 0.0000 |
| value_div_yield | decimal(12,6) | NO |  | 0.000000 |
| value_score | decimal(12,4) | NO |  | 0.0000 |
| value_rank | int | NO |  | 0 |
| earnings_surprise_avg | decimal(12,4) | NO |  | 0.0000 |
| earnings_beat_rate | decimal(12,4) | NO |  | 0.0000 |
| earnings_growth_rate | decimal(12,4) | NO |  | 0.0000 |
| earnings_score | decimal(12,4) | NO |  | 0.0000 |
| earnings_rank | int | NO |  | 0 |
| vol_realized_60d | decimal(12,4) | NO |  | 0.0000 |
| vol_beta | decimal(12,4) | NO |  | 0.0000 |
| vol_max_dd_90d | decimal(12,4) | NO |  | 0.0000 |
| vol_score | decimal(12,4) | NO |  | 0.0000 |
| vol_rank | int | NO |  | 0 |
| growth_revenue | decimal(12,4) | NO |  | 0.0000 |
| growth_earnings | decimal(12,4) | NO |  | 0.0000 |
| growth_score | decimal(12,4) | NO |  | 0.0000 |
| growth_rank | int | NO |  | 0 |
| composite_score | decimal(12,4) | NO |  | 0.0000 |
| composite_rank | int | NO | MUL | 0 |
| regime_adj_score | decimal(12,4) | NO |  | 0.0000 |
| regime_adj_rank | int | NO | MUL | 0 |
| factors_json | text | YES |  |  |

### `alpha_fundamentals`  (2964 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| fetch_date | date | NO | MUL |  |
| market_cap | decimal(20,2) | NO |  | 0.00 |
| pe_trailing | decimal(12,4) | NO |  | 0.0000 |
| pe_forward | decimal(12,4) | NO |  | 0.0000 |
| peg_ratio | decimal(12,4) | NO |  | 0.0000 |
| price_to_book | decimal(12,4) | NO |  | 0.0000 |
| price_to_sales | decimal(12,4) | NO |  | 0.0000 |
| ev_to_ebitda | decimal(12,4) | NO |  | 0.0000 |
| return_on_equity | decimal(12,4) | NO |  | 0.0000 |
| return_on_assets | decimal(12,4) | NO |  | 0.0000 |
| gross_margins | decimal(12,4) | NO |  | 0.0000 |
| operating_margins | decimal(12,4) | NO |  | 0.0000 |
| profit_margins | decimal(12,4) | NO |  | 0.0000 |
| revenue_growth | decimal(12,4) | NO |  | 0.0000 |
| earnings_growth | decimal(12,4) | NO |  | 0.0000 |
| total_debt | decimal(20,2) | NO |  | 0.00 |
| total_cash | decimal(20,2) | NO |  | 0.00 |
| debt_to_equity | decimal(12,4) | NO |  | 0.0000 |
| current_ratio | decimal(12,4) | NO |  | 0.0000 |
| free_cashflow | decimal(20,2) | NO |  | 0.00 |
| operating_cashflow | decimal(20,2) | NO |  | 0.00 |
| dividend_yield | decimal(12,6) | NO |  | 0.000000 |
| payout_ratio | decimal(12,4) | NO |  | 0.0000 |
| shares_outstanding | bigint | NO |  | 0 |
| beta | decimal(12,4) | NO |  | 0.0000 |
| fifty_two_week_high | decimal(12,4) | NO |  | 0.0000 |
| fifty_two_week_low | decimal(12,4) | NO |  | 0.0000 |
| fifty_day_avg | decimal(12,4) | NO |  | 0.0000 |
| two_hundred_day_avg | decimal(12,4) | NO |  | 0.0000 |
| avg_volume | bigint | NO |  | 0 |
| regular_market_price | decimal(12,4) | NO |  | 0.0000 |
| raw_json | text | YES |  |  |

### `alpha_macro`  (181 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trade_date | date | NO | UNI |  |
| vix_close | decimal(12,4) | NO |  | 0.0000 |
| spy_close | decimal(12,4) | NO |  | 0.0000 |
| spy_sma50 | decimal(12,4) | NO |  | 0.0000 |
| spy_sma200 | decimal(12,4) | NO |  | 0.0000 |
| tnx_close | decimal(12,4) | NO |  | 0.0000 |
| two_yr_yield | decimal(12,4) | NO |  | 0.0000 |
| yield_spread | decimal(12,4) | NO |  | 0.0000 |
| dxy_close | decimal(12,4) | NO |  | 0.0000 |
| dxy_sma50 | decimal(12,4) | NO |  | 0.0000 |
| regime | varchar(50) | NO |  | unknown |
| regime_score | int | NO |  | 0 |
| regime_detail | text | YES |  |  |

### `alpha_picks`  (5043 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| strategy | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| score | decimal(12,4) | NO |  | 0.0000 |
| conviction | varchar(20) | NO |  | medium |
| expected_horizon | varchar(20) | NO |  | 1m |
| risk_level | varchar(20) | NO |  | Medium |
| position_size_pct | decimal(12,4) | NO |  | 0.0000 |
| stop_loss_pct | decimal(12,4) | NO |  | 0.0000 |
| take_profit_pct | decimal(12,4) | NO |  | 0.0000 |
| rationale | text | YES |  |  |
| top_factors | text | YES |  |  |
| avoid_reasons | text | YES |  |  |
| pick_hash | varchar(64) | NO | UNI |  |
| created_at | datetime | NO |  |  |

### `alpha_refresh_log`  (731 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| refresh_date | datetime | NO | MUL |  |
| step | varchar(100) | NO | MUL |  |
| status | varchar(20) | NO |  | started |
| details | text | YES |  |  |
| duration_seconds | int | NO |  | 0 |
| tickers_processed | int | NO |  | 0 |
| errors_count | int | NO |  | 0 |

### `alpha_status`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI | 1 |
| last_refresh_start | datetime | YES |  |  |
| last_refresh_end | datetime | YES |  |  |
| last_refresh_status | varchar(20) | NO |  | never |
| next_expected_refresh | datetime | YES |  |  |
| universe_count | int | NO |  | 0 |
| factors_computed | int | NO |  | 0 |
| picks_generated | int | NO |  | 0 |
| current_regime | varchar(50) | NO |  | unknown |
| regime_detail | text | YES |  |  |
| summary_json | text | YES |  |  |

### `alpha_universe`  (52 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| ticker | varchar(10) | NO | PRI |  |
| company_name | varchar(200) | NO |  |  |
| sector | varchar(100) | NO | MUL |  |
| industry | varchar(200) | NO |  |  |
| market_cap_tier | varchar(20) | NO |  | large |
| added_date | date | NO |  |  |
| active | tinyint | NO | MUL | 1 |

### `at_aggregation_runs`  (25853 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| run_id | char(36) | NO | PRI |  |
| started_at | datetime | NO | MUL |  |
| finished_at | datetime | YES |  |  |
| status | enum('RUNNING','COMPLETED','FAILED') | NO | MUL | RUNNING |
| systems_loaded | int | YES |  | 0 |
| raw_picks_count | int | YES |  | 0 |
| consensus_count | int | YES |  | 0 |
| regime_data | json | YES |  |  |
| portfolio_drawdown | decimal(10,4) | YES |  | 0.0000 |
| source | varchar(50) | YES |  | aggregator |

### `at_audit_events`  (61294 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| event_type | varchar(100) | NO | MUL |  |
| pick_id | char(36) | YES | MUL |  |
| aggregation_run_id | char(36) | YES | MUL |  |
| symbol | varchar(50) | YES | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES |  | UNKNOWN |
| payload | json | YES |  |  |
| origin | varchar(50) | YES |  | aggregator |
| created_at | datetime | NO |  |  |

### `at_consensus_picks`  (11919 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | char(36) | NO | PRI |  |
| aggregation_run_id | char(36) | NO | MUL |  |
| symbol | varchar(50) | NO | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | NO | MUL | UNKNOWN |
| direction | enum('LONG','SHORT') | NO |  |  |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| risk_reward | decimal(10,4) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| agreement_count | int | YES |  |  |
| source_systems | json | YES |  |  |
| source_strategies | json | YES |  |  |
| system_confidences | json | YES |  |  |
| consensus_tier | varchar(50) | YES |  |  |
| classification | varchar(50) | YES |  |  |
| regime_data | json | YES |  |  |
| discord_channel | varchar(100) | YES |  |  |
| discord_message_id | varchar(100) | YES |  |  |
| status | enum('OPEN','WON','LOST','EXPIRED','CLOSED') | YES | MUL | OPEN |
| exit_price | decimal(18,8) | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| slippage_estimate | decimal(10,4) | YES |  |  |
| generated_at | datetime | NO |  |  |
| closed_at | datetime | YES |  |  |

### `at_discord_gate_log`  (41513 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | varchar(10) | NO |  | LONG |
| system_name | varchar(100) | YES |  |  |
| strategy | varchar(100) | YES |  |  |
| gate_name | varchar(30) | NO | MUL |  |
| gate_result | varchar(10) | NO |  | REJECT |
| reason | varchar(255) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| entry_price | decimal(18,8) | YES |  |  |
| created_at | datetime | NO | MUL | CURRENT_TIMESTAMP |

### `at_discord_gate_state`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| channel | varchar(100) | NO | MUL |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | varchar(10) | YES |  |  |
| gate_status | varchar(50) | YES |  |  |
| total_scanned | int | YES |  | 0 |
| blocked_count | int | YES |  | 0 |
| entry_price | decimal(18,8) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| system_name | varchar(100) | YES |  |  |
| recorded_at | datetime | NO |  |  |

### `at_discord_notifications`  (42982 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | varchar(10) | NO |  | LONG |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| agreement_count | int | YES |  |  |
| source_systems | json | YES |  |  |
| strategy | varchar(100) | YES |  |  |
| signal_tier | varchar(20) | YES |  |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| discord_channel | varchar(50) | NO | MUL |  |
| discord_webhook | varchar(50) | YES |  |  |
| discord_message_id | varchar(100) | YES |  |  |
| event_type | varchar(30) | NO | MUL |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| payload | json | YES |  |  |
| created_at | datetime | NO | MUL | CURRENT_TIMESTAMP |

### `at_discord_sent`  (4662 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| channel | varchar(100) | NO | MUL |  |
| webhook_name | varchar(100) | YES |  |  |
| symbol | varchar(50) | NO | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| direction | enum('LONG','SHORT') | YES |  |  |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| strategy | varchar(200) | YES |  |  |
| source_system | varchar(100) | YES |  |  |
| dedup_key | varchar(200) | YES | UNI |  |
| consensus_pick_id | char(36) | YES |  |  |
| sent_at | datetime | NO | MUL |  |
| discord_message_id | varchar(100) | YES |  |  |
| sent_payload | json | YES |  |  |

### `at_filter_log`  (818190 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| aggregation_run_id | char(36) | YES | MUL |  |
| raw_pick_id | char(36) | YES |  |  |
| symbol | varchar(50) | YES | MUL |  |
| direction | varchar(10) | YES |  |  |
| source_system | varchar(100) | YES |  |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES |  | UNKNOWN |
| filter_reason | varchar(100) | NO | MUL |  |
| details | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `at_futures_symbol_edge`  (4 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| symbol | varchar(32) | NO | PRI |  |
| asset_class | varchar(20) | NO |  |  |
| strategy | varchar(80) | NO |  |  |
| is_validated_strategy | tinyint(1) | NO |  | 0 |
| sample_size | int | YES |  |  |
| win_rate_pct | decimal(6,2) | YES |  |  |
| profit_factor | decimal(8,3) | YES |  |  |
| expectancy_pct | decimal(8,3) | YES |  |  |
| edge_label | varchar(64) | NO |  |  |
| evidence_source | varchar(255) | NO |  |  |
| last_updated_utc | varchar(40) | NO |  |  |

### `at_incubator_backtest_results`  (1616 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| perm_id | varchar(20) | NO | MUL |  |
| archetype | varchar(80) | NO |  |  |
| symbol | varchar(30) | NO | MUL |  |
| params_json | json | NO |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(6,4) | YES |  | 0.0000 |
| sharpe | decimal(10,4) | YES | MUL | 0.0000 |
| sortino | decimal(10,4) | YES |  | 0.0000 |
| max_drawdown | decimal(10,6) | YES |  | 0.000000 |
| profit_factor | decimal(10,4) | YES |  | 0.0000 |
| total_return | decimal(10,6) | YES |  | 0.000000 |
| avg_trade_pnl | decimal(10,6) | YES |  | 0.000000 |
| avg_hold_bars | decimal(6,1) | YES |  | 0.0 |
| slippage_pct | decimal(6,4) | YES |  | 0.0000 |
| commission_pct | decimal(6,4) | YES |  | 0.0000 |
| backtest_type | enum('fast','full') | YES |  | fast |
| created_at | datetime | NO |  |  |

### `at_incubator_strategies`  (328 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| perm_id | varchar(20) | NO | PRI |  |
| archetype | varchar(80) | NO | MUL |  |
| seed_strategy | varchar(100) | YES |  |  |
| params_json | json | NO |  |  |
| combined_sharpe | decimal(10,4) | YES |  | 0.0000 |
| combined_sortino | decimal(10,4) | YES |  | 0.0000 |
| combined_max_dd | decimal(10,6) | YES |  | 0.000000 |
| combined_pf | decimal(10,4) | YES |  | 0.0000 |
| combined_wr | decimal(6,4) | YES |  | 0.0000 |
| combined_trades | int | YES |  | 0 |
| combined_return | decimal(10,6) | YES |  | 0.000000 |
| composite_score | decimal(10,4) | YES | MUL | 0.0000 |
| status | enum('INCUBATOR','PAPER_READY','PAPER_TESTING','GRADUATED','REJECTED','ARCHIVED') | YES | MUL | INCUBATOR |
| ready_for_paper | tinyint | YES |  | 0 |
| rejection_reasons | text | YES |  |  |
| per_symbol_json | json | YES |  |  |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |

### `at_large_backtest_results`  (1390 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| perm_id | varchar(20) | NO | MUL |  |
| archetype | varchar(80) | NO |  |  |
| symbol | varchar(30) | NO |  |  |
| params_json | json | NO |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(6,4) | YES |  | 0.0000 |
| sharpe | decimal(10,4) | YES | MUL | 0.0000 |
| sortino | decimal(10,4) | YES |  | 0.0000 |
| max_drawdown | decimal(10,6) | YES |  | 0.000000 |
| profit_factor | decimal(10,4) | YES |  | 0.0000 |
| total_return | decimal(10,6) | YES |  | 0.000000 |
| avg_trade_pnl | decimal(10,6) | YES |  | 0.000000 |
| avg_hold_bars | decimal(6,1) | YES |  | 0.0 |
| slippage_pct | decimal(6,4) | YES |  | 0.0000 |
| commission_pct | decimal(6,4) | YES |  | 0.0000 |
| equity_curve_json | json | YES |  |  |
| trade_log_json | json | YES |  |  |
| created_at | datetime | NO |  |  |

### `at_local_picks`  (29980 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | varchar(10) | YES |  | LONG |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| strategy | varchar(100) | YES | MUL |  |
| source_system | varchar(100) | NO | MUL |  |
| source_file | varchar(200) | YES |  |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| status | varchar(20) | YES | MUL | OPEN |
| exit_price | decimal(18,8) | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| signal_timestamp | datetime | YES | MUL |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP |

### `at_permutation_picks`  (1614 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_id | int | NO |  |  |
| permutation_id | varchar(100) | NO | MUL |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | enum('LONG','SHORT') | NO |  |  |
| agreement_count | int | YES |  | 1 |
| source_systems | json | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| pick_status | enum('ACTIVE','CLOSED') | NO | MUL | ACTIVE |
| recorded_at | datetime | NO |  |  |

### `at_permutation_snapshots`  (28 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_type | enum('SYSTEM','STRATEGY') | NO | MUL |  |
| permutation_id | varchar(100) | NO | MUL |  |
| permutation_name | varchar(200) | NO |  |  |
| category | varchar(50) | YES |  |  |
| systems | json | YES |  |  |
| strategies | json | YES |  |  |
| min_agreement | int | YES |  | 1 |
| trust_score | decimal(5,1) | YES | MUL | 0.0 |
| trust_tier | varchar(50) | YES |  | Unproven |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,1) | YES |  | 0.0 |
| total_pnl | decimal(12,4) | YES |  | 0.0000 |
| avg_pnl | decimal(10,4) | YES |  | 0.0000 |
| profit_factor | decimal(10,4) | YES |  |  |
| active_pick_count | int | YES |  | 0 |
| closed_pick_count | int | YES |  | 0 |
| snapshot_at | datetime | NO | MUL |  |

### `at_raw_picks`  (145879 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | char(36) | NO | PRI |  |
| aggregation_run_id | char(36) | NO | MUL |  |
| source_system | varchar(100) | NO | MUL |  |
| symbol | varchar(50) | NO | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | NO | MUL | UNKNOWN |
| direction | enum('LONG','SHORT') | NO |  |  |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| risk_reward | decimal(10,4) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| strategy | varchar(200) | YES |  |  |
| raw_payload | json | YES |  |  |
| signal_timestamp | datetime | YES | MUL |  |
| recorded_at | datetime | NO |  |  |
| dedup_hash | char(64) | YES | UNI |  |
| was_stale | tinyint(1) | YES |  | 0 |
| was_banned | tinyint(1) | YES |  | 0 |
| was_demoted | tinyint(1) | YES |  | 0 |
| was_wr_suppressed | tinyint(1) | YES |  | 0 |
| created_by | varchar(50) | YES |  | aggregator |
| status | enum('OPEN','WON','LOST','EXPIRED','CLOSED') | YES | MUL | OPEN |
| exit_price | decimal(18,8) | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| closed_at | datetime | YES |  |  |

### `at_raw_picks_anomaly_log`  (304 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| raw_pick_id | bigint | YES |  |  |
| reason | varchar(64) | NO |  |  |
| original_pnl_pct | double | YES |  |  |
| captured_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `at_signal_outcomes`  (121 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(50) | NO | MUL |  |
| direction | varchar(10) | YES |  | LONG |
| entry_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| exit_price | decimal(18,8) | YES |  |  |
| outcome | varchar(20) | YES | MUL |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| source_system | varchar(100) | NO | MUL |  |
| strategy | varchar(100) | YES |  |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| opened_at | datetime | YES |  |  |
| closed_at | datetime | YES |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP |

### `at_sqlite_imports`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_db_path | varchar(500) | NO | MUL |  |
| source_table | varchar(100) | NO |  |  |
| rows_imported | int | YES |  | 0 |
| target_table | varchar(100) | NO |  |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| imported_at | datetime | NO |  |  |
| notes | text | YES |  |  |

### `at_strategy_stats`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| strategy | varchar(200) | NO | PRI |  |
| source_system | varchar(100) | NO | PRI |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| total_picks | int | YES |  | 0 |
| consensus_picks | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,4) | YES |  | 0.0000 |
| avg_pnl_pct | decimal(10,4) | YES |  | 0.0000 |
| best_pnl | decimal(10,4) | YES |  | 0.0000 |
| worst_pnl | decimal(10,4) | YES |  | 0.0000 |
| avg_risk_reward | decimal(10,4) | YES |  | 0.0000 |
| last_updated | datetime | YES |  |  |

### `at_strategy_symbol_performance`  (410 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| strategy_name | varchar(100) | NO | MUL |  |
| display_name | varchar(200) | YES |  |  |
| symbol | varchar(20) | NO |  |  |
| portfolio_type | varchar(50) | YES |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| win_rate | decimal(5,2) | YES |  | 0.00 |
| avg_pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| profit_factor | decimal(8,3) | YES |  | 0.000 |
| sharpe | decimal(8,3) | YES |  | 0.000 |
| max_drawdown_pct | decimal(8,4) | YES |  | 0.0000 |
| best_trade_pct | decimal(8,4) | YES |  | 0.0000 |
| worst_trade_pct | decimal(8,4) | YES |  | 0.0000 |
| test_interval | varchar(10) | YES |  | 1h |
| test_bars | int | YES |  | 500 |
| is_catered | tinyint(1) | YES |  | 0 |
| tested_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `audit_log`  (5949 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `audit_trails`  (684 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(50) | NO | MUL |  |
| symbol | varchar(50) | NO |  |  |
| pick_timestamp | datetime | NO |  |  |
| generation_source | varchar(100) | NO |  |  |
| reasons | text | YES |  |  |
| supporting_data | text | YES |  |  |
| pick_details | text | YES |  |  |
| formatted_for_ai | text | YES |  |  |

### `backtest_results`  (2 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| algorithm_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_commissions | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| sortino_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `backtest_trades`  (50 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| ticker | varchar(10) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| entry_date | date | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| shares | int | NO |  | 0 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| commission_paid | decimal(8,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `bt_backtest_runs`  (285 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | char(36) | NO | PRI |  |
| source_db | varchar(200) | NO |  |  |
| source_table | varchar(100) | NO |  |  |
| strategy | varchar(200) | YES | MUL |  |
| symbol | varchar(50) | YES | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,4) | YES |  |  |
| profit_factor | decimal(10,4) | YES |  |  |
| total_return | decimal(10,4) | YES |  |  |
| sharpe | decimal(10,4) | YES |  |  |
| max_drawdown | decimal(10,4) | YES |  |  |
| imported_at | datetime | NO |  |  |

### `bt_backtest_trades`  (32724171 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_run_id | char(36) | YES | MUL |  |
| source_db | varchar(200) | NO |  |  |
| source_table | varchar(100) | NO |  |  |
| symbol | varchar(50) | NO | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| direction | enum('LONG','SHORT') | YES |  |  |
| strategy | varchar(200) | YES | MUL |  |
| entry_price | decimal(18,8) | YES |  |  |
| exit_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| entry_time | datetime | YES |  |  |
| exit_time | datetime | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| status | varchar(20) | YES | MUL |  |
| confidence | decimal(5,4) | YES |  |  |
| raw_data | json | YES |  |  |
| imported_at | datetime | NO |  |  |

### `challenge_200_days`  (124 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| challenge_date | date | NO | MUL |  |
| mode | varchar(20) | NO | MUL | consensus |
| capital | decimal(12,2) | NO |  | 5000.00 |
| picks_count | int | NO |  | 0 |
| total_invested | decimal(12,2) | NO |  | 0.00 |
| daily_pnl | decimal(12,2) | NO |  | 0.00 |
| daily_return_pct | decimal(10,4) | NO |  | 0.0000 |
| target_amount | decimal(12,2) | NO |  | 200.00 |
| target_hit | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| best_pick | varchar(10) | NO |  |  |
| best_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_pick | varchar(10) | NO |  |  |
| worst_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| cumulative_pnl | decimal(12,2) | NO |  | 0.00 |
| cumulative_days | int | NO |  | 0 |
| win_streak | int | NO |  | 0 |
| lessons_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `challenge_200_trades`  (620 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| challenge_date | date | NO | MUL |  |
| mode | varchar(20) | NO |  | consensus |
| ticker | varchar(10) | NO | MUL |  |
| company_name | varchar(100) | NO |  |  |
| direction | varchar(10) | NO |  | LONG |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| shares | decimal(12,4) | NO |  | 0.0000 |
| invested | decimal(12,2) | NO |  | 0.00 |
| pnl | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| consensus_count | int | NO |  | 0 |
| consensus_score | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(30) | NO |  |  |
| algo_notes | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `circuit_breaker_log`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trigger_date | date | NO | MUL |  |
| breaker_type | varchar(50) | NO | MUL |  |
| trigger_value | varchar(200) | NO |  |  |
| threshold | varchar(100) | NO |  |  |
| action_taken | varchar(200) | NO |  |  |
| is_active | tinyint | NO | MUL | 1 |
| expires_at | datetime | YES |  |  |
| resolved_at | datetime | YES |  |  |
| created_at | datetime | NO |  |  |

### `consensus_history`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| consensus_date | date | NO | MUL |  |
| consensus_count | int | NO | MUL | 0 |
| consensus_score | decimal(10,4) | NO | MUL | 0.0000 |
| source_algos | text | YES |  |  |
| source_tables | text | YES |  |  |
| avg_entry_price | decimal(12,4) | NO |  | 0.0000 |
| latest_price | decimal(12,4) | NO |  | 0.0000 |
| direction | varchar(10) | NO |  | LONG |
| created_at | datetime | NO |  |  |

### `consensus_lessons`  (348 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| lesson_date | date | NO | MUL |  |
| lesson_type | varchar(30) | NO | MUL |  |
| lesson_title | varchar(200) | NO |  |  |
| lesson_text | text | NO |  |  |
| confidence | int | NO | MUL | 50 |
| supporting_data | text | YES |  |  |
| applied | int | NO |  | 0 |
| impact_score | decimal(6,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `consensus_performance_daily`  (62 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| track_date | date | NO | UNI |  |
| open_positions | int | NO |  | 0 |
| total_closed | int | NO |  | 0 |
| total_wins | int | NO |  | 0 |
| total_losses | int | NO |  | 0 |
| win_rate | decimal(6,2) | NO |  | 0.00 |
| total_pnl_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| best_ticker | varchar(10) | NO |  |  |
| best_return_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_ticker | varchar(10) | NO |  |  |
| worst_return_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_days | decimal(6,1) | NO |  | 0.0 |
| current_streak | int | NO |  | 0 |
| portfolio_value | decimal(12,2) | NO |  | 10000.00 |
| created_at | datetime | NO |  |  |

### `consensus_tracked`  (318 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| company_name | varchar(100) | NO |  |  |
| entry_date | date | NO | MUL |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| consensus_count | int | NO |  | 0 |
| consensus_score | decimal(10,4) | NO |  | 0.0000 |
| direction | varchar(10) | NO |  | LONG |
| source_algos | text | YES |  |  |
| target_tp_pct | decimal(6,2) | NO |  | 8.00 |
| target_sl_pct | decimal(6,2) | NO |  | 4.00 |
| max_hold_days | int | NO |  | 14 |
| current_price | decimal(12,4) | NO |  | 0.0000 |
| current_return_pct | decimal(10,4) | NO |  | 0.0000 |
| peak_price | decimal(12,4) | NO |  | 0.0000 |
| trough_price | decimal(12,4) | NO |  | 0.0000 |
| status | varchar(20) | NO | MUL | open |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| exit_reason | varchar(30) | NO |  |  |
| final_return_pct | decimal(10,4) | NO | MUL | 0.0000 |
| hold_days | int | NO |  | 0 |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |
| discord_sent | tinyint(1) | NO | MUL | 0 |
| discord_channel | varchar(50) | YES |  |  |
| discord_message_id | varchar(100) | YES |  |  |
| discord_sent_at | datetime | YES |  |  |

### `consolidated_cache`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(64) | NO | UNI |  |
| cache_data | longtext | YES |  |  |
| generated_at | datetime | NO |  |  |
| expires_at | datetime | NO |  |  |

### `cp_audit_log`  (19 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO |  |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO |  |  |

### `cp_backtest_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| run_name | varchar(200) | NO |  |  |
| strategy_filter | varchar(500) | NO |  |  |
| params_json | text | YES |  |  |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_fees | decimal(12,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `cp_pairs`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| pair | varchar(15) | NO | PRI |  |
| pair_name | varchar(100) | NO |  |  |
| base_asset | varchar(10) | NO |  |  |
| quote_asset | varchar(10) | NO |  | USD |
| category | varchar(50) | NO |  | large_cap |
| yahoo_ticker | varchar(20) | NO |  |  |

### `cp_prices`  (4857 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(15) | NO | MUL |  |
| trade_date | date | NO | MUL |  |
| open_price | decimal(18,8) | NO |  | 0.00000000 |
| high_price | decimal(18,8) | NO |  | 0.00000000 |
| low_price | decimal(18,8) | NO |  | 0.00000000 |
| close_price | decimal(18,8) | NO |  | 0.00000000 |
| volume | bigint | NO |  | 0 |

### `cp_report_cache`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| report_date | date | NO | UNI |  |
| report_json | longtext | YES |  |  |
| created_at | datetime | NO |  |  |

### `cp_signals`  (174 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(15) | NO | MUL |  |
| strategy_name | varchar(100) | NO | MUL |  |
| signal_date | date | NO | MUL |  |
| signal_time | datetime | NO |  |  |
| direction | varchar(10) | NO |  | long |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| stop_loss_price | decimal(18,8) | NO |  | 0.00000000 |
| take_profit_price | decimal(18,8) | NO |  | 0.00000000 |
| signal_hash | varchar(64) | NO |  |  |
| score | int | NO |  | 0 |

### `cp_strategies`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | trend |
| ideal_timeframe | varchar(20) | NO |  | 1d |

### `cr_algo_performance`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `cr_algorithms`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |

### `cr_audit_log`  (401 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `cr_backtest_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| algorithm_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| annualized_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| best_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_fees | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| sortino_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_days | decimal(8,2) | NO |  | 0.00 |
| fee_drag_pct | decimal(10,4) | NO |  | 0.0000 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `cr_backtest_trades`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| direction | varchar(10) | NO |  | LONG |
| entry_date | date | NO |  |  |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(18,8) | NO |  | 0.00000000 |
| position_size | decimal(12,4) | NO |  | 0.0000 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| fees_paid | decimal(8,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `cr_category_perf`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| category | varchar(200) | NO | MUL |  |
| period | varchar(20) | NO |  | 1m |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| top_pair | varchar(20) | NO |  |  |
| worst_pair | varchar(20) | NO |  |  |
| pair_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `cr_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `cr_pair_picks`  (1008 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| direction | varchar(10) | NO | MUL | LONG |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |
| rationale_json | text | YES |  |  |

### `cr_pairs`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| symbol | varchar(20) | NO | PRI |  |
| base_asset | varchar(20) | NO |  |  |
| quote_asset | varchar(10) | NO |  | USD |
| category | varchar(50) | NO |  | major |
| pair_name | varchar(200) | NO |  |  |

### `cr_portfolios`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | balanced |
| algorithm_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| stop_loss_pct | decimal(5,2) | NO |  | 10.00 |
| take_profit_pct | decimal(5,2) | NO |  | 20.00 |
| max_hold_days | int | NO |  | 90 |
| position_size_pct | decimal(5,2) | NO |  | 20.00 |
| max_positions | int | NO |  | 5 |
| created_at | datetime | NO |  |  |

### `cr_price_history`  (4579 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| price_date | date | NO | MUL |  |
| open | decimal(18,8) | NO |  | 0.00000000 |
| high | decimal(18,8) | NO |  | 0.00000000 |
| low | decimal(18,8) | NO |  | 0.00000000 |
| close | decimal(18,8) | NO |  | 0.00000000 |
| volume | decimal(24,2) | NO |  | 0.00 |

### `cr_whatif_scenarios`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `crypto_assets`  (14 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | UNI |  |
| name | varchar(100) | NO |  |  |
| asset_type | enum('major','altcoin','meme','defi','nft','layer2') | YES | MUL | altcoin |
| market_cap_category | enum('mega','large','mid','small','micro','nano') | YES |  | mid |
| is_meme | tinyint(1) | YES | MUL | 0 |
| blockchain | varchar(50) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `crypto_exchange_netflow`  (20 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| blockchain | varchar(20) | NO | MUL |  |
| exchange_name | varchar(50) | YES |  |  |
| netflow_24h | decimal(20,8) | YES |  |  |
| netflow_7d | decimal(20,8) | YES |  |  |
| calculated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `crypto_indicators`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| timeframe | varchar(10) | NO |  |  |
| timestamp | bigint | NO |  |  |
| rsi_14 | decimal(8,4) | YES |  |  |
| macd | decimal(18,8) | YES |  |  |
| macd_signal | decimal(18,8) | YES |  |  |
| ema_9 | decimal(18,8) | YES |  |  |
| ema_21 | decimal(18,8) | YES |  |  |
| sma_50 | decimal(18,8) | YES |  |  |
| sma_200 | decimal(18,8) | YES |  |  |
| bb_upper | decimal(18,8) | YES |  |  |
| bb_lower | decimal(18,8) | YES |  |  |
| atr_14 | decimal(18,8) | YES |  |  |
| volume_sma_20 | decimal(24,8) | YES |  |  |
| stochastic_k | decimal(8,4) | YES |  |  |
| adx_14 | decimal(8,4) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `crypto_ohlcv`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| timeframe | varchar(10) | NO |  |  |
| timestamp | bigint | NO |  |  |
| open | decimal(18,8) | NO |  |  |
| high | decimal(18,8) | NO |  |  |
| low | decimal(18,8) | NO |  |  |
| close | decimal(18,8) | NO |  |  |
| volume | decimal(24,8) | NO |  |  |

### `crypto_patterns`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| pattern_type | varchar(50) | NO |  |  |
| pattern_name | varchar(100) | NO |  |  |
| timeframe | varchar(10) | NO |  |  |
| start_timestamp | bigint | NO |  |  |
| end_timestamp | bigint | NO |  |  |
| confidence | decimal(5,2) | NO | MUL |  |
| price_at_detection | decimal(18,8) | YES |  |  |
| target_price | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| embedding_vector | json | YES |  |  |
| features | json | YES |  |  |
| success_rating | decimal(3,2) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `crypto_signals`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| signal_id | varchar(50) | NO | UNI |  |
| symbol | varchar(20) | NO | MUL |  |
| signal_type | enum('buy','sell','strong_buy','strong_sell') | NO |  |  |
| entry_price | decimal(18,8) | NO |  |  |
| target_price | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| status | enum('active','closed','stopped') | YES | MUL | active |
| pnl_percent | decimal(8,4) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `crypto_whale_movements`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| blockchain | varchar(20) | NO | MUL |  |
| from_address | varchar(100) | YES |  |  |
| to_address | varchar(100) | YES |  |  |
| amount | decimal(20,8) | YES |  |  |
| amount_usd | decimal(15,2) | YES |  |  |
| transaction_hash | varchar(100) | YES | UNI |  |
| movement_type | varchar(50) | YES | MUL |  |
| detected_at | timestamp | YES | MUL | CURRENT_TIMESTAMP |

### `crypto_whale_wallets`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| blockchain | varchar(20) | NO | MUL |  |
| wallet_address | varchar(100) | NO |  |  |
| balance | decimal(20,8) | YES |  |  |
| balance_usd | decimal(15,2) | YES |  |  |
| last_transaction_time | timestamp | YES |  |  |
| transaction_count_24h | int | YES |  | 0 |
| is_exchange | tinyint(1) | YES | MUL | 0 |
| wallet_label | varchar(100) | YES |  |  |
| last_updated | timestamp | YES |  | CURRENT_TIMESTAMP |

### `cw_scan_log`  (712 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scan_id | varchar(20) | NO | MUL |  |
| pair | varchar(30) | NO |  |  |
| price | double | NO |  |  |
| score | int | NO |  | 0 |
| factors_json | text | YES |  |  |
| verdict | varchar(20) | NO |  | SKIP |
| chg_24h | double | YES |  | 0 |
| vol_usd_24h | double | YES |  | 0 |
| created_at | datetime | NO | MUL |  |

### `cw_winners`  (351 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scan_id | varchar(20) | NO | MUL |  |
| pair | varchar(30) | NO | MUL |  |
| price_at_signal | double | NO |  |  |
| price_at_resolve | double | YES |  |  |
| score | int | NO |  | 0 |
| factors_json | text | YES |  |  |
| verdict | varchar(20) | NO |  | SKIP |
| target_pct | double | NO |  | 2 |
| risk_pct | double | NO |  | 1.5 |
| pnl_pct | double | YES |  |  |
| outcome | varchar(20) | YES | MUL |  |
| vol_usd_24h | double | YES |  | 0 |
| chg_24h | double | YES |  | 0 |
| created_at | datetime | NO | MUL |  |
| resolved_at | datetime | YES |  |  |

### `daily_prices`  (49340 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| trade_date | date | NO | MUL |  |
| open_price | decimal(12,4) | NO |  | 0.0000 |
| high_price | decimal(12,4) | NO |  | 0.0000 |
| low_price | decimal(12,4) | NO |  | 0.0000 |
| close_price | decimal(12,4) | NO |  | 0.0000 |
| adj_close | decimal(12,4) | NO |  | 0.0000 |
| volume | bigint | NO |  | 0 |

### `daytrader_sim_days`  (176 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| sim_date | date | NO | MUL |  |
| budget | decimal(12,2) | NO |  | 500.00 |
| picks_used | int | NO |  | 0 |
| total_invested | decimal(12,2) | NO |  | 0.00 |
| total_pnl | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| best_pick_ticker | varchar(10) | NO |  |  |
| best_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_pick_ticker | varchar(10) | NO |  |  |
| worst_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| algo_version | varchar(20) | NO |  | original |
| cumulative_pnl | decimal(12,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `daytrader_sim_trades`  (838 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| sim_date | date | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| strategy_name | varchar(100) | NO |  |  |
| source_table | varchar(30) | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| shares | int | NO |  | 0 |
| invested | decimal(12,2) | NO |  | 0.00 |
| pnl | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| algo_version | varchar(20) | NO | MUL | original |
| created_at | datetime | NO |  |  |

### `eh_alerts`  (13 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(60) | NO | MUL |  |
| alert_type | varchar(30) | NO |  |  |
| severity | varchar(15) | NO |  | INFO |
| message | text | YES |  |  |
| old_grade | varchar(2) | YES |  |  |
| new_grade | varchar(2) | YES |  |  |
| created_at | datetime | YES |  |  |

### `eh_engine_grades`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(60) | NO | UNI |  |
| health_score | float | YES |  | 0 |
| health_grade | varchar(2) | YES |  | F |
| total_signals | int | YES |  | 0 |
| resolved_signals | int | YES |  | 0 |
| win_rate | float | YES |  | 0 |
| total_pnl | float | YES |  | 0 |
| avg_pnl | float | YES |  | 0 |
| sharpe_estimate | float | YES |  | 0 |
| data_freshness_hours | float | YES |  | 999 |
| signal_frequency_daily | float | YES |  | 0 |
| recommendation | varchar(30) | YES |  | INVESTIGATE |
| details | text | YES |  |  |
| graded_at | datetime | YES |  |  |

### `eh_grade_history`  (168 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(60) | NO | MUL |  |
| health_score | float | YES |  | 0 |
| health_grade | varchar(2) | YES |  | F |
| win_rate | float | YES |  | 0 |
| total_pnl | float | YES |  | 0 |
| resolved_signals | int | YES |  | 0 |
| snapshot_at | datetime | YES |  |  |

### `fx_algo_performance`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_pips | decimal(10,2) | NO |  | 0.00 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `fx_algorithms`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |

### `fx_audit_log`  (89 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO |  |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO |  |  |

### `fx_backtest_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| run_name | varchar(200) | NO |  |  |
| strategy_filter | varchar(500) | NO |  |  |
| params_json | text | YES |  |  |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_spread_cost | decimal(12,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `fx_backtest_trades`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| direction | varchar(10) | NO |  | LONG |
| entry_date | date | NO |  |  |
| entry_price | decimal(12,6) | NO |  | 0.000000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,6) | NO |  | 0.000000 |
| lot_size | decimal(12,4) | NO |  | 0.0000 |
| pip_profit | decimal(10,2) | NO |  | 0.00 |
| spread_cost | decimal(8,2) | NO |  | 0.00 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `fx_category_perf`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| category | varchar(200) | NO | MUL |  |
| period | varchar(20) | NO |  | 1m |
| avg_pips | decimal(10,2) | NO |  | 0.00 |
| top_pair | varchar(20) | NO |  |  |
| worst_pair | varchar(20) | NO |  |  |
| pair_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `fx_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `fx_pair_picks`  (16 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_price | decimal(12,6) | NO |  | 0.000000 |
| direction | varchar(10) | NO |  | LONG |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |

### `fx_pairs`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| pair | varchar(10) | NO | PRI |  |
| pair_name | varchar(100) | NO |  |  |
| base_currency | varchar(5) | NO |  |  |
| quote_currency | varchar(5) | NO |  |  |
| category | varchar(50) | NO |  | major |
| pip_value | decimal(10,6) | NO |  | 0.000100 |
| yahoo_ticker | varchar(20) | NO |  |  |

### `fx_portfolios`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | balanced |
| algorithm_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| leverage | int | NO |  | 1 |
| spread_pips | decimal(6,2) | NO |  | 1.50 |
| stop_loss_pips | decimal(8,2) | NO |  | 50.00 |
| take_profit_pips | decimal(8,2) | NO |  | 100.00 |
| max_hold_days | int | NO |  | 30 |
| position_size_pct | decimal(5,2) | NO |  | 2.00 |
| max_positions | int | NO |  | 5 |
| created_at | datetime | NO |  |  |

### `fx_price_history`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| price_date | date | NO | MUL |  |
| open_price | decimal(12,6) | NO |  | 0.000000 |
| high_price | decimal(12,6) | NO |  | 0.000000 |
| low_price | decimal(12,6) | NO |  | 0.000000 |
| close_price | decimal(12,6) | NO |  | 0.000000 |
| volume | bigint | NO |  | 0 |

### `fx_prices`  (3855 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(10) | NO | MUL |  |
| trade_date | date | NO | MUL |  |
| open_price | decimal(12,6) | NO |  | 0.000000 |
| high_price | decimal(12,6) | NO |  | 0.000000 |
| low_price | decimal(12,6) | NO |  | 0.000000 |
| close_price | decimal(12,6) | NO |  | 0.000000 |
| volume | bigint | NO |  | 0 |

### `fx_report_cache`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| report_date | date | NO | UNI |  |
| report_json | longtext | YES |  |  |
| created_at | datetime | NO |  |  |

### `fx_signals`  (585 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(10) | NO | MUL |  |
| strategy_name | varchar(100) | NO | MUL |  |
| signal_date | date | NO | MUL |  |
| signal_time | datetime | NO |  |  |
| direction | varchar(10) | NO |  | long |
| entry_price | decimal(12,6) | NO |  | 0.000000 |
| stop_loss_price | decimal(12,6) | NO |  | 0.000000 |
| take_profit_price | decimal(12,6) | NO |  | 0.000000 |
| signal_hash | varchar(64) | NO |  |  |
| score | int | NO |  | 0 |

### `fx_strategies`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | trend |
| ideal_timeframe | varchar(20) | NO |  | 1d |

### `fx_whatif_scenarios`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `fxp_algo_performance`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_pips | decimal(10,2) | NO |  | 0.00 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `fxp_algorithms`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |

### `fxp_audit_log`  (388 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `fxp_backtest_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| algorithm_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| annualized_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pips | decimal(10,2) | NO |  | 0.00 |
| avg_loss_pips | decimal(10,2) | NO |  | 0.00 |
| best_trade_pips | decimal(10,2) | NO |  | 0.00 |
| worst_trade_pips | decimal(10,2) | NO |  | 0.00 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_spread_cost | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| sortino_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy_pips | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_days | decimal(8,2) | NO |  | 0.00 |
| leverage_used | int | NO |  | 1 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `fxp_backtest_trades`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| direction | varchar(10) | NO |  | LONG |
| entry_date | date | NO |  |  |
| entry_price | decimal(12,6) | NO |  | 0.000000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,6) | NO |  | 0.000000 |
| lot_size | decimal(12,4) | NO |  | 0.0000 |
| pip_profit | decimal(10,2) | NO |  | 0.00 |
| spread_cost | decimal(8,2) | NO |  | 0.00 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `fxp_category_perf`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| category | varchar(200) | NO | MUL |  |
| period | varchar(20) | NO |  | 1m |
| avg_pips | decimal(10,2) | NO |  | 0.00 |
| top_pair | varchar(20) | NO |  |  |
| worst_pair | varchar(20) | NO |  |  |
| pair_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `fxp_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `fxp_pair_picks`  (1248 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_price | decimal(12,6) | NO |  | 0.000000 |
| direction | varchar(10) | NO |  | LONG |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |

### `fxp_pairs`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| symbol | varchar(20) | NO | PRI |  |
| base_currency | varchar(10) | NO |  |  |
| quote_currency | varchar(10) | NO |  |  |
| category | varchar(30) | NO |  | major |
| pip_value | decimal(10,6) | NO |  | 0.000100 |

### `fxp_portfolios`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | balanced |
| algorithm_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| leverage | int | NO |  | 1 |
| spread_pips | decimal(6,2) | NO |  | 1.50 |
| stop_loss_pips | decimal(8,2) | NO |  | 50.00 |
| take_profit_pips | decimal(8,2) | NO |  | 100.00 |
| max_hold_days | int | NO |  | 30 |
| position_size_pct | decimal(5,2) | NO |  | 2.00 |
| max_positions | int | NO |  | 5 |
| created_at | datetime | NO |  |  |

### `fxp_price_history`  (2694 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| price_date | date | NO | MUL |  |
| open_price | decimal(12,6) | NO |  | 0.000000 |
| high_price | decimal(12,6) | NO |  | 0.000000 |
| low_price | decimal(12,6) | NO |  | 0.000000 |
| close_price | decimal(12,6) | NO |  | 0.000000 |
| volume | bigint | NO |  | 0 |

### `fxp_whatif_scenarios`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `gm_failure_alerts`  (414 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| alert_date | date | NO | MUL |  |
| source_system | varchar(30) | NO | MUL |  |
| alert_type | varchar(30) | NO |  |  |
| severity | varchar(10) | NO |  | warning |
| title | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| affected_tickers | text | YES |  |  |
| metric_value | decimal(10,4) | NO |  | 0.0000 |
| threshold_value | decimal(10,4) | NO |  | 0.0000 |
| page_url | varchar(200) | NO |  |  |
| is_active | int | NO | MUL | 1 |
| resolved_at | datetime | YES |  |  |
| created_at | datetime | NO |  |  |

### `gm_news_sentiment`  (140 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| fetch_date | date | NO | MUL |  |
| articles_analyzed | int | NO |  | 0 |
| sentiment_score | decimal(6,4) | NO | MUL | 0.0000 |
| positive_count | int | NO |  | 0 |
| negative_count | int | NO |  | 0 |
| neutral_count | int | NO |  | 0 |
| buzz_score | decimal(8,4) | NO |  | 0.0000 |
| sector_avg_sentiment | decimal(6,4) | NO |  | 0.0000 |
| relative_sentiment | decimal(6,4) | NO |  | 0.0000 |
| source | varchar(20) | NO |  | finnhub |
| created_at | datetime | NO |  |  |

### `gm_sec_13f_holdings`  (2084 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cik | varchar(20) | NO | MUL |  |
| fund_name | varchar(200) | NO |  |  |
| ticker | varchar(10) | NO | MUL |  |
| cusip | varchar(9) | NO |  |  |
| name_of_issuer | varchar(200) | NO |  |  |
| value_thousands | bigint | NO |  | 0 |
| shares | bigint | NO |  | 0 |
| filing_quarter | varchar(10) | NO | MUL |  |
| filing_date | date | NO |  |  |
| prev_shares | bigint | NO |  | 0 |
| change_pct | decimal(10,4) | NO |  | 0.0000 |
| change_type | varchar(20) | NO | MUL |  |
| created_at | datetime | NO |  |  |

### `gm_sec_insider_trades`  (718 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cik | varchar(20) | NO |  |  |
| ticker | varchar(10) | NO | MUL |  |
| filer_name | varchar(200) | NO |  |  |
| filer_title | varchar(100) | NO |  |  |
| transaction_date | date | NO | MUL |  |
| transaction_type | varchar(10) | NO | MUL |  |
| shares | decimal(18,4) | NO |  | 0.0000 |
| price_per_share | decimal(12,4) | NO |  | 0.0000 |
| total_value | decimal(18,2) | NO |  | 0.00 |
| shares_owned_after | decimal(18,4) | NO |  | 0.0000 |
| filing_date | date | NO | MUL |  |
| accession_number | varchar(30) | NO | MUL |  |
| is_director | int | NO |  | 0 |
| is_officer | int | NO |  | 0 |
| is_ten_pct_owner | int | NO |  | 0 |
| created_at | datetime | NO |  |  |

### `gm_system_health`  (272 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snap_date | date | NO | MUL |  |
| source_system | varchar(30) | NO |  |  |
| total_picks | int | NO |  | 0 |
| closed_picks | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| expired | int | NO |  | 0 |
| win_rate | decimal(6,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_hours | decimal(10,2) | NO |  | 0.00 |
| best_pick_ticker | varchar(30) | NO |  |  |
| best_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_pick_ticker | varchar(30) | NO |  |  |
| worst_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| accuracy_7d | decimal(6,2) | NO |  | 0.00 |
| accuracy_30d | decimal(6,2) | NO |  | 0.00 |
| is_failing | int | NO | MUL | 0 |
| failure_reason | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `gm_unified_picks`  (1846 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_system | varchar(30) | NO | MUL |  |
| source_page | varchar(100) | NO |  |  |
| source_id | int | NO |  | 0 |
| source_table | varchar(50) | NO |  |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| asset_type | varchar(20) | NO | MUL | stock |
| ticker | varchar(30) | NO | MUL |  |
| asset_name | varchar(200) | NO |  |  |
| direction | varchar(10) | NO |  | LONG |
| algorithm_name | varchar(100) | NO | MUL |  |
| algo_count | int | NO |  | 1 |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| target_price | decimal(18,8) | NO |  | 0.00000000 |
| stop_loss_price | decimal(18,8) | NO |  | 0.00000000 |
| target_pct | decimal(8,4) | NO |  | 0.0000 |
| stop_loss_pct | decimal(8,4) | NO |  | 0.0000 |
| confidence_score | int | NO | MUL | 0 |
| hold_period_hours | int | NO |  | 0 |
| metadata_json | text | YES |  |  |
| status | varchar(20) | NO | MUL | open |
| current_price | decimal(18,8) | NO |  | 0.00000000 |
| current_return_pct | decimal(10,4) | NO |  | 0.0000 |
| peak_price | decimal(18,8) | NO |  | 0.00000000 |
| trough_price | decimal(18,8) | NO |  | 0.00000000 |
| exit_price | decimal(18,8) | NO |  | 0.00000000 |
| exit_date | datetime | YES |  |  |
| exit_reason | varchar(50) | NO |  |  |
| final_return_pct | decimal(10,4) | NO |  | 0.0000 |
| hold_hours | decimal(10,2) | NO |  | 0.00 |
| dividends_earned | decimal(10,4) | NO |  | 0.0000 |
| earnings_events | int | NO |  | 0 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |

### `goldmine_cursor_algo_scorecard`  (7 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| week_start | date | NO | MUL |  |
| week_end | date | NO |  |  |
| asset_class | varchar(20) | NO |  |  |
| algorithm | varchar(80) | NO |  |  |
| total_picks | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| win_rate | decimal(6,2) | NO |  | 0.00 |
| avg_gain_pct | decimal(8,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(8,4) | NO |  | 0.0000 |
| profit_factor | decimal(8,4) | NO |  | 0.0000 |
| expectancy | decimal(8,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(8,4) | YES |  |  |
| sortino_ratio | decimal(8,4) | YES |  |  |
| max_drawdown_pct | decimal(8,4) | YES |  |  |
| benchmark_return_pct | decimal(8,4) | YES |  |  |
| alpha_pct | decimal(8,4) | YES |  |  |
| deflated_sharpe | decimal(8,4) | YES |  |  |
| regime | varchar(20) | NO |  | unknown |
| verdict | varchar(20) | NO | MUL | neutral |
| snapshot_at | datetime | NO |  |  |

### `goldmine_cursor_benchmarks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| benchmark | varchar(20) | NO | MUL |  |
| trade_date | date | NO |  |  |
| close_price | decimal(16,6) | NO |  |  |

### `goldmine_cursor_circuit_breaker`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm | varchar(80) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| triggered_at | datetime | NO |  |  |
| drawdown_pct | decimal(8,4) | NO |  |  |
| threshold_pct | decimal(8,4) | NO |  | 15.0000 |
| status | varchar(20) | NO | MUL | triggered |
| notes | text | YES |  |  |

### `goldmine_cursor_correlation_matrix`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| computed_date | date | NO | MUL |  |
| algo_a | varchar(80) | NO |  |  |
| algo_b | varchar(80) | NO |  |  |
| overlap_pct | decimal(6,2) | NO |  | 0.00 |
| return_correlation | decimal(6,4) | YES |  |  |

### `goldmine_cursor_data_health`  (9 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| checked_at | datetime | NO |  |  |
| source_system | varchar(50) | NO | MUL |  |
| last_data_time | datetime | YES |  |  |
| hours_stale | decimal(8,2) | YES |  |  |
| status | varchar(20) | NO | MUL | ok |
| details | text | YES |  |  |

### `goldmine_cursor_predictions`  (478 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| prediction_id | varchar(64) | NO | UNI |  |
| asset_class | varchar(20) | NO | MUL |  |
| ticker | varchar(30) | NO |  |  |
| algorithm | varchar(80) | NO | MUL |  |
| direction | varchar(10) | NO |  | long |
| entry_price | decimal(16,6) | NO |  | 0.000000 |
| target_price | decimal(16,6) | NO |  | 0.000000 |
| stop_loss | decimal(16,6) | NO |  | 0.000000 |
| confidence_score | int | NO |  | 0 |
| source_system | varchar(50) | NO | MUL |  |
| logged_at | datetime | NO | MUL |  |
| market_regime | varchar(20) | NO | MUL | unknown |
| status | varchar(20) | NO | MUL | open |
| exit_price | decimal(16,6) | YES |  |  |
| exit_date | datetime | YES |  |  |
| pnl_pct | decimal(8,4) | YES |  |  |
| benchmark_return_pct | decimal(8,4) | YES |  |  |
| hold_days | int | YES |  |  |
| resolved_at | datetime | YES |  |  |

### `goldmine_cursor_regime_log`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| detected_date | date | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| regime | varchar(20) | NO |  |  |
| vix_level | decimal(8,2) | YES |  |  |
| sma50_trend | varchar(10) | YES |  |  |
| sma200_trend | varchar(10) | YES |  |  |
| notes | text | YES |  |  |

### `kelly_sizing_log`  (1702 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_table | varchar(30) | NO | MUL | stock_picks |
| algorithm_name | varchar(100) | NO | MUL |  |
| calc_date | date | NO | MUL |  |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| full_kelly | decimal(8,4) | NO |  | 0.0000 |
| half_kelly | decimal(8,4) | NO |  | 0.0000 |
| quarter_kelly | decimal(8,4) | NO |  | 0.0000 |
| recommended_pct | decimal(8,4) | NO |  | 0.0000 |
| trades_used | int | NO |  | 0 |
| created_at | datetime | NO |  |  |

### `lm_alert_configs`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| alert_type | varchar(30) | NO | UNI |  |
| alert_name | varchar(100) | NO |  |  |
| threshold_value | int | NO |  | 0 |
| threshold_direction | varchar(10) | NO |  | above |
| cooldown_hours | int | NO |  | 24 |
| is_active | tinyint | NO |  | 1 |
| created_at | datetime | NO |  |  |

### `lm_algo_health`  (28 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  | ALL |
| rolling_sharpe_30d | decimal(8,4) | NO |  | 0.0000 |
| rolling_win_rate_30d | decimal(6,4) | NO |  | 0.0000 |
| rolling_pnl_30d | decimal(12,4) | NO |  | 0.0000 |
| online_weight | decimal(8,6) | NO |  | 1.000000 |
| decay_status | varchar(20) | NO |  | healthy |
| trades_30d | int | NO |  | 0 |
| consecutive_losses | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `lm_algo_performance`  (2 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snap_date | date | NO | MUL |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(10) | NO |  |  |
| param_source | varchar(10) | NO | MUL | original |
| signals_count | int | NO |  | 0 |
| trades_count | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| expired | int | NO |  | 0 |
| total_pnl_pct | decimal(12,4) | NO |  | 0.0000 |
| avg_pnl_pct | decimal(10,4) | NO |  | 0.0000 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| best_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_hours | decimal(8,2) | NO |  | 0.00 |
| tp_used | decimal(6,2) | NO |  | 0.00 |
| sl_used | decimal(6,2) | NO |  | 0.00 |
| hold_used | int | NO |  | 0 |
| created_at | datetime | NO |  |  |

### `lm_analyst_ratings`  (84 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| period | date | NO |  |  |
| strong_buy | int | NO |  | 0 |
| buy | int | NO |  | 0 |
| hold | int | NO |  | 0 |
| sell | int | NO |  | 0 |
| strong_sell | int | NO |  | 0 |
| fetch_date | date | NO | MUL |  |
| created_at | datetime | NO |  |  |
| source | varchar(30) | NO |  | finnhub |

### `lm_breaker_log`  (133 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trigger_time | datetime | NO | MUL |  |
| breaker_type | varchar(50) | NO | MUL |  |
| trigger_value | varchar(200) | NO |  |  |
| threshold | varchar(100) | NO |  |  |
| action_taken | varchar(200) | NO |  |  |
| is_active | tinyint | NO | MUL | 1 |
| expires_at | datetime | YES |  |  |
| resolved_at | datetime | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_bridge_congress`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| signal_type | varchar(50) | NO | MUL |  |
| strength | int | NO |  | 50 |
| members_buying | int | NO |  | 0 |
| description | text | YES |  |  |
| updated_at | datetime | NO |  |  |

### `lm_bridge_cusum`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | UNI |  |
| decay_status | varchar(20) | NO |  | unknown |
| recommended_weight | decimal(6,3) | NO |  | 1.000 |
| last_sharpe | decimal(8,4) | NO |  | 0.0000 |
| last_win_rate | decimal(6,4) | NO |  | 0.0000 |
| change_points | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `lm_bridge_entropy`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| role | varchar(20) | NO |  | neutral |
| outgoing_te | decimal(10,6) | NO |  | 0.000000 |
| incoming_te | decimal(10,6) | NO |  | 0.000000 |
| net_te | decimal(10,6) | NO |  | 0.000000 |
| updated_at | datetime | NO |  |  |

### `lm_bridge_onchain`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| metric_name | varchar(50) | NO | UNI |  |
| metric_value | decimal(20,4) | NO |  | 0.0000 |
| metric_label | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_bridge_options`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| spot_price | decimal(12,2) | NO |  | 0.00 |
| net_gex | decimal(20,0) | NO |  | 0 |
| gex_signal | varchar(30) | NO |  |  |
| pc_oi_ratio | decimal(8,3) | NO |  | 0.000 |
| pcr_signal | varchar(30) | NO |  |  |
| unusual_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `lm_bridge_portfolio`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| strategy_name | varchar(30) | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| weight | decimal(8,4) | NO |  | 0.0000 |
| updated_at | datetime | NO |  |  |

### `lm_bridge_sentiment`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| sentiment_score | decimal(8,4) | NO |  | 0.0000 |
| sentiment_label | varchar(20) | NO |  | neutral |
| confidence | decimal(6,4) | NO |  | 0.0000 |
| num_articles | int | NO |  | 0 |
| positive_pct | decimal(5,1) | NO |  | 0.0 |
| negative_pct | decimal(5,1) | NO |  | 0.0 |
| updated_at | datetime | NO |  |  |

### `lm_challenger_showdown`  (49 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| period_start | date | NO | MUL |  |
| period_end | date | NO |  |  |
| challenger_trades | int | NO |  | 0 |
| challenger_wins | int | NO |  | 0 |
| challenger_win_rate | decimal(5,2) | NO |  | 0.00 |
| challenger_pnl | decimal(12,2) | NO |  | 0.00 |
| challenger_sharpe | decimal(6,3) | NO |  | 0.000 |
| challenger_max_dd | decimal(6,2) | NO |  | 0.00 |
| best_algo_name | varchar(100) | NO |  |  |
| best_algo_trades | int | NO |  | 0 |
| best_algo_wins | int | NO |  | 0 |
| best_algo_win_rate | decimal(5,2) | NO |  | 0.00 |
| best_algo_pnl | decimal(12,2) | NO |  | 0.00 |
| best_algo_sharpe | decimal(6,3) | NO |  | 0.000 |
| best_algo_max_dd | decimal(6,2) | NO |  | 0.00 |
| challenger_rank | int | NO |  | 0 |
| total_algos | int | NO |  | 0 |
| snapshot_date | date | NO | MUL |  |
| created_at | datetime | NO |  |  |

### `lm_conviction_alerts`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| alert_type | varchar(30) | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| message | varchar(255) | NO |  |  |
| severity | varchar(10) | NO |  | info |
| details_json | text | YES |  |  |
| is_read | tinyint | NO | MUL | 0 |
| created_at | datetime | NO | MUL |  |

### `lm_conviction_history`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| calc_date | date | NO | MUL |  |
| conviction_score | int | NO | MUL | 50 |
| conviction_label | varchar(20) | NO |  | neutral |
| whale_score | int | NO |  | 50 |
| insider_score | int | NO |  | 50 |
| analyst_score | int | NO |  | 50 |
| crowd_score | int | NO |  | 50 |
| fear_greed_score | int | NO |  | 50 |
| regime_score | int | NO |  | 50 |
| value_score | int | NO |  | 50 |
| growth_score | int | NO |  | 50 |
| momentum_score | int | NO |  | 50 |
| entry_price | decimal(12,2) | NO |  | 0.00 |
| detail_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_conviction_performance`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| conviction_date | date | NO | MUL |  |
| conviction_score | int | NO | MUL | 50 |
| conviction_label | varchar(20) | NO |  | neutral |
| entry_price | decimal(12,2) | NO |  | 0.00 |
| price_7d | decimal(12,2) | NO |  | 0.00 |
| price_14d | decimal(12,2) | NO |  | 0.00 |
| price_30d | decimal(12,2) | NO |  | 0.00 |
| return_7d | decimal(8,4) | NO |  | 0.0000 |
| return_14d | decimal(8,4) | NO |  | 0.0000 |
| return_30d | decimal(8,4) | NO |  | 0.0000 |
| outcome_30d | varchar(10) | NO |  | pending |
| filled_7d | tinyint | NO | MUL | 0 |
| filled_14d | tinyint | NO |  | 0 |
| filled_30d | tinyint | NO | MUL | 0 |
| created_at | datetime | NO |  |  |

### `lm_conviction_stats`  (9 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| stat_period | varchar(20) | NO | MUL |  |
| conviction_bucket | varchar(20) | NO |  |  |
| total_signals | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| pending_count | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return | decimal(8,4) | NO |  | 0.0000 |
| max_return | decimal(8,4) | NO |  | 0.0000 |
| min_return | decimal(8,4) | NO |  | 0.0000 |
| calculated_at | datetime | NO |  |  |

### `lm_cross_correlation`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algo_a | varchar(100) | NO |  |  |
| asset_a | varchar(20) | NO |  |  |
| algo_b | varchar(100) | NO |  |  |
| asset_b | varchar(20) | NO |  |  |
| correlation | decimal(5,4) | YES |  |  |
| sample_size | int | YES |  | 0 |
| calc_date | date | NO | MUL |  |
| created_at | datetime | YES |  |  |

### `lm_daily_price_history`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| trade_date | date | NO | MUL |  |
| open_price | decimal(12,2) | NO |  | 0.00 |
| high_price | decimal(12,2) | NO |  | 0.00 |
| low_price | decimal(12,2) | NO |  | 0.00 |
| close_price | decimal(12,2) | NO |  | 0.00 |
| volume | bigint | NO |  | 0 |
| source | varchar(30) | NO |  | finnhub |
| created_at | datetime | NO |  |  |

### `lm_discovered_movers`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | UNI |  |
| binance_symbol | varchar(20) | NO |  |  |
| price | decimal(18,8) | NO |  | 0.00000000 |
| change_24h_pct | decimal(10,4) | NO |  | 0.0000 |
| volume_usd | decimal(24,2) | NO |  | 0.00 |
| direction | varchar(10) | NO |  |  |
| signal_count | int | NO |  | 0 |
| signals | text | YES |  |  |
| discovered_at | datetime | NO | MUL |  |

### `lm_ensemble_weights`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| ensemble_weight | decimal(5,4) | YES |  | 0.0000 |
| rolling_sharpe_30d | decimal(8,4) | YES |  |  |
| rolling_win_rate_30d | decimal(5,2) | YES |  |  |
| correlation_to_portfolio | decimal(5,4) | YES |  |  |
| information_ratio | decimal(8,4) | YES |  |  |
| calc_date | date | NO |  |  |
| created_at | datetime | YES |  |  |

### `lm_fear_greed`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source | varchar(20) | NO | MUL |  |
| score | int | NO |  | 50 |
| classification | varchar(30) | NO |  | neutral |
| components | text | YES |  |  |
| fetch_date | date | NO | MUL |  |
| fetch_time | datetime | NO |  |  |

### `lm_feature_importance`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| feature_name | varchar(100) | NO |  |  |
| importance_score | decimal(8,4) | YES |  | 0.0000 |
| importance_rank | int | YES |  | 0 |
| calc_date | date | NO |  |  |
| sample_size | int | YES |  | 0 |
| created_at | datetime | YES |  |  |

### `lm_guru_picks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| guru_id | int | NO | MUL | 0 |
| pick_type | varchar(20) | NO |  |  |
| ticker_or_team | varchar(50) | NO | MUL |  |
| pick_description | varchar(255) | NO |  |  |
| odds_or_target | decimal(10,2) | NO |  | 0.00 |
| source_url | varchar(255) | NO |  |  |
| posted_at | datetime | NO | MUL |  |
| result | varchar(20) | NO | MUL | pending |
| profit_loss | decimal(8,2) | NO |  | 0.00 |
| resolved_at | date | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_guru_tracker`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| guru_name | varchar(100) | NO | MUL |  |
| platform | varchar(50) | NO |  |  |
| specialty | varchar(50) | NO |  |  |
| tracked_since | date | NO |  |  |
| total_picks | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO | MUL | 0.00 |
| roi_percent | decimal(8,2) | NO |  | 0.00 |
| avg_return | decimal(8,2) | NO |  | 0.00 |
| credibility_score | int | NO | MUL | 0 |
| last_updated | date | NO |  |  |
| created_at | datetime | NO |  |  |

### `lm_hour_learning`  (223 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(10) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| calc_date | date | NO |  |  |
| best_tp_pct | decimal(6,2) | NO |  | 0.00 |
| best_sl_pct | decimal(6,2) | NO |  | 0.00 |
| best_hold_hours | int | NO |  | 0 |
| best_return_pct | decimal(10,4) | NO |  | 0.0000 |
| best_win_rate | decimal(5,2) | NO |  | 0.00 |
| best_profit_factor | decimal(8,4) | NO |  | 0.0000 |
| trades_tested | int | NO |  | 0 |
| profitable_combos | int | NO |  | 0 |
| total_combos | int | NO |  | 0 |
| current_wr | decimal(5,2) | NO |  | 0.00 |
| optimized_wr | decimal(5,2) | NO |  | 0.00 |
| verdict | varchar(50) | NO |  |  |
| created_at | datetime | NO |  |  |

### `lm_injury_intel_cache`  (4 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(100) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_insider_sentiment`  (11 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| year | int | NO |  |  |
| month | int | NO |  |  |
| mspr | decimal(10,4) | NO |  | 0.0000 |
| change_val | decimal(18,2) | NO |  | 0.00 |
| fetch_date | date | NO | MUL |  |
| created_at | datetime | NO |  |  |
| source | varchar(30) | NO |  | finnhub |

### `lm_intelligence`  (169 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| metric_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO | MUL | ALL |
| symbol | varchar(30) | NO | MUL |  |
| metric_value | decimal(18,8) | NO |  | 0.00000000 |
| metric_label | varchar(100) | NO |  |  |
| metadata | text | YES |  |  |
| updated_at | datetime | NO | MUL |  |

### `lm_kelly_fractions`  (9 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  | ALL |
| win_rate | decimal(6,4) | NO |  | 0.0000 |
| avg_win_pct | decimal(8,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(8,4) | NO |  | 0.0000 |
| full_kelly | decimal(8,6) | NO |  | 0.000000 |
| half_kelly | decimal(8,6) | NO |  | 0.000000 |
| sample_size | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |
| vol_adjusted_kelly | decimal(8,6) | NO |  | 0.000000 |

### `lm_market_regime`  (228 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| date | datetime | NO | MUL |  |
| hmm_regime | varchar(20) | NO | MUL | sideways |
| hmm_confidence | decimal(6,4) | NO |  | 0.5000 |
| hmm_persistence | decimal(6,4) | NO |  | 0.5000 |
| hurst | decimal(6,4) | NO |  | 0.5000 |
| hurst_regime | varchar(20) | NO |  | random |
| ewma_vol | decimal(10,8) | NO |  | 0.00000000 |
| vol_annualized | decimal(8,4) | NO |  | 0.0000 |
| composite_score | decimal(6,2) | NO |  | 50.00 |
| strategy_toggles | text | YES |  |  |
| vix_level | decimal(8,2) | YES |  |  |
| vix_regime | varchar(20) | NO |  | normal |
| yield_curve | varchar(20) | NO |  | normal |
| yield_spread | decimal(8,4) | YES |  |  |
| macro_score | decimal(6,2) | NO |  | 50.00 |
| ticker_regimes | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_meta_labeler`  (6 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trained_at | datetime | NO | MUL |  |
| training_samples | int | NO |  | 0 |
| positive_rate | decimal(6,4) | NO |  | 0.0000 |
| avg_precision | decimal(6,4) | NO |  | 0.0000 |
| avg_recall | decimal(6,4) | NO |  | 0.0000 |
| avg_f1 | decimal(6,4) | NO |  | 0.0000 |
| cv_results | text | YES |  |  |
| top_features | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_meta_labels`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_id | int | NO | MUL | 0 |
| algorithm_name | varchar(100) | NO |  |  |
| symbol | varchar(30) | NO |  |  |
| prediction | decimal(6,4) | NO |  | 0.0000 |
| confidence | decimal(6,4) | NO |  | 0.0000 |
| features | text | YES |  |  |
| created_at | datetime | NO | MUL |  |

### `lm_ml_status`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| closed_trades | int | YES |  | 0 |
| min_trades_needed | int | YES |  | 20 |
| ml_ready | tinyint | YES |  | 0 |
| current_tp | decimal(5,2) | YES |  |  |
| current_sl | decimal(5,2) | YES |  |  |
| current_hold | int | YES |  |  |
| param_source | varchar(20) | YES |  | default |
| current_win_rate | decimal(5,2) | YES |  |  |
| current_sharpe | decimal(8,4) | YES |  |  |
| current_pf | decimal(5,3) | YES |  |  |
| total_pnl | decimal(10,2) | YES |  | 0.00 |
| last_optimization | datetime | YES |  |  |
| optimization_count | int | YES |  | 0 |
| best_sharpe_ever | decimal(8,4) | YES |  |  |
| backtest_sharpe | decimal(8,4) | YES |  |  |
| backtest_grade | varchar(5) | YES |  |  |
| backtest_trades | int | YES |  | 0 |
| forward_backtest_overlap | tinyint | YES |  | 0 |
| status | varchar(30) | YES |  | collecting_data |
| status_reason | text | YES |  |  |
| updated_at | datetime | YES |  |  |
| created_at | datetime | YES |  |  |

### `lm_mlb_stats_cache`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(50) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_model_versions`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| version | int | YES |  | 1 |
| tp_pct | decimal(5,2) | YES |  |  |
| sl_pct | decimal(5,2) | YES |  |  |
| max_hold_hours | int | YES |  |  |
| sharpe_at_deploy | decimal(8,4) | YES |  |  |
| win_rate_at_deploy | decimal(5,2) | YES |  |  |
| trades_at_deploy | int | YES |  | 0 |
| is_active | tinyint | YES |  | 1 |
| deployed_at | datetime | YES |  |  |
| retired_at | datetime | YES |  |  |
| retire_reason | varchar(200) | YES |  |  |
| created_at | datetime | YES |  |  |

### `lm_multi_dimensional`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| calc_date | date | NO | MUL |  |
| whale_score | int | NO |  | 50 |
| insider_score | int | NO |  | 50 |
| analyst_score | int | NO |  | 50 |
| crowd_score | int | NO |  | 50 |
| fear_greed_score | int | NO |  | 50 |
| regime_score | int | NO |  | 50 |
| value_score | int | NO |  | 50 |
| growth_score | int | NO |  | 50 |
| momentum_score | int | NO |  | 50 |
| conviction_score | int | NO | MUL | 50 |
| conviction_label | varchar(20) | NO |  | neutral |
| dimension_detail | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_nba_games_today`  (14 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| game_id | varchar(30) | NO | UNI |  |
| game_date | date | NO |  |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| home_abbr | varchar(10) | YES |  |  |
| away_abbr | varchar(10) | YES |  |  |
| venue | varchar(100) | YES |  |  |
| start_time | varchar(30) | YES |  |  |
| status | varchar(30) | YES |  | scheduled |
| home_score | int | YES |  | 0 |
| away_score | int | YES |  | 0 |
| updated_at | datetime | NO |  |  |

### `lm_nba_stats_cache`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(50) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_nba_team_stats`  (30 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| team_id | varchar(20) | NO | UNI |  |
| abbreviation | varchar(10) | NO |  |  |
| name | varchar(100) | NO |  |  |
| short_name | varchar(60) | NO |  |  |
| conference | varchar(20) | YES |  |  |
| division | varchar(30) | YES |  |  |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_pct | decimal(5,3) | YES |  | 0.000 |
| home_wins | int | YES |  | 0 |
| home_losses | int | YES |  | 0 |
| away_wins | int | YES |  | 0 |
| away_losses | int | YES |  | 0 |
| streak | varchar(10) | YES |  |  |
| last10_wins | int | YES |  | 0 |
| last10_losses | int | YES |  | 0 |
| ppg | decimal(5,1) | YES |  | 0.0 |
| opp_ppg | decimal(5,1) | YES |  | 0.0 |
| rpg | decimal(5,1) | YES |  | 0.0 |
| apg | decimal(5,1) | YES |  | 0.0 |
| fg_pct | decimal(5,1) | YES |  | 0.0 |
| three_pct | decimal(5,1) | YES |  | 0.0 |
| ft_pct | decimal(5,1) | YES |  | 0.0 |
| pace | decimal(5,1) | YES |  | 0.0 |
| off_rating | decimal(5,1) | YES |  | 0.0 |
| def_rating | decimal(5,1) | YES |  | 0.0 |
| net_rating | decimal(5,1) | YES |  | 0.0 |
| source | varchar(30) | YES |  | espn |
| updated_at | datetime | NO |  |  |

### `lm_nfl_stats_cache`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(50) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_nhl_stats_cache`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(50) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_opportunities`  (4 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scan_id | varchar(40) | NO | MUL |  |
| asset_class | varchar(10) | NO |  |  |
| symbol | varchar(20) | NO |  |  |
| current_price | decimal(18,8) | NO |  | 0.00000000 |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| direction | varchar(10) | NO |  | BUY |
| trend_strength | varchar(20) | NO |  | weak |
| confidence_score | int | NO | MUL | 0 |
| signal_count | int | NO |  | 0 |
| momentum_signals | text | YES |  |  |
| volume_confirmation | varchar(255) | NO |  |  |
| key_reason_now | text | YES |  |  |
| holding_period | varchar(20) | NO |  |  |
| avg_tp_pct | decimal(6,2) | NO |  | 0.00 |
| avg_sl_pct | decimal(6,2) | NO |  | 0.00 |
| data_source | varchar(100) | NO |  |  |
| data_latency_seconds | int | NO |  | 0 |
| notes | text | YES |  |  |
| signal_ids | text | YES |  |  |
| scan_time | datetime | NO | MUL |  |

### `lm_picks_bridge`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_table | varchar(50) | NO | MUL |  |
| source_id | int | NO |  |  |
| signal_id | int | YES |  |  |
| algorithm_name | varchar(100) | NO |  |  |
| ticker | varchar(20) | NO |  |  |
| pick_date | date | NO | MUL |  |
| direction | varchar(10) | YES |  | LONG |
| entry_price | decimal(12,4) | YES |  |  |
| tp_pct | decimal(5,2) | YES |  |  |
| sl_pct | decimal(5,2) | YES |  |  |
| max_hold_hours | int | YES |  | 168 |
| status | varchar(20) | YES | MUL | pending |
| created_at | datetime | YES |  |  |

### `lm_position_sizing`  (1541 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| date | datetime | NO | MUL |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| kelly_base | decimal(8,4) | NO |  | 0.0000 |
| vol_scalar | decimal(8,2) | NO |  | 1.00 |
| regime_modifier | decimal(8,2) | NO |  | 1.00 |
| decay_weight | decimal(8,2) | NO |  | 1.00 |
| final_size_pct | decimal(8,2) | NO |  | 5.00 |
| dollar_amount | decimal(12,2) | NO |  | 500.00 |
| algo_sharpe_30d | decimal(8,3) | NO |  | 0.000 |
| is_decaying | tinyint | NO |  | 0 |
| regime_composite | decimal(6,2) | NO |  | 50.00 |
| created_at | datetime | NO |  |  |

### `lm_prediction_calibration`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| confidence_bucket | varchar(20) | NO |  |  |
| total_predictions | int | YES |  | 0 |
| correct_predictions | int | YES |  | 0 |
| actual_accuracy | decimal(5,2) | YES |  |  |
| calibration_error | decimal(5,4) | YES |  |  |
| calc_date | date | NO |  |  |
| created_at | datetime | YES |  |  |

### `lm_price_cache`  (66 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(10) | NO | MUL |  |
| symbol | varchar(20) | NO |  |  |
| price | decimal(18,8) | NO |  | 0.00000000 |
| bid_price | decimal(18,8) | NO |  | 0.00000000 |
| ask_price | decimal(18,8) | NO |  | 0.00000000 |
| spread_pct | decimal(8,4) | NO |  | 0.0000 |
| volume_24h | decimal(24,2) | NO |  | 0.00 |
| change_1h_pct | decimal(10,4) | NO |  | 0.0000 |
| change_24h_pct | decimal(10,4) | NO |  | 0.0000 |
| high_24h | decimal(18,8) | NO |  | 0.00000000 |
| low_24h | decimal(18,8) | NO |  | 0.00000000 |
| data_source | varchar(50) | NO |  |  |
| data_delay_seconds | int | NO |  | 0 |
| last_updated | datetime | NO | MUL |  |
| prev_close | decimal(12,2) | NO |  | 0.00 |
| day_high | decimal(12,2) | NO |  | 0.00 |
| day_low | decimal(12,2) | NO |  | 0.00 |
| volume | bigint | NO |  | 0 |
| source | varchar(30) | NO |  | finnhub |
| updated_at | datetime | YES |  |  |

### `lm_price_targets`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| target_high | decimal(12,2) | NO |  | 0.00 |
| target_low | decimal(12,2) | NO |  | 0.00 |
| target_mean | decimal(12,2) | NO |  | 0.00 |
| target_median | decimal(12,2) | NO |  | 0.00 |
| last_updated | date | NO |  |  |
| fetch_date | date | NO | MUL |  |
| created_at | datetime | NO |  |  |
| num_analysts | int | NO |  | 0 |
| source | varchar(30) | NO |  | finnhub |

### `lm_quant_bridge`  (6 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| module_name | varchar(50) | NO | MUL |  |
| run_source | varchar(30) | NO |  | github |
| status | varchar(20) | NO | MUL | success |
| result_data | longtext | YES |  |  |
| summary | text | YES |  |  |
| run_at | datetime | NO | MUL |  |

### `lm_schedule_intel_cache`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| cache_key | varchar(100) | NO | UNI |  |
| cache_data | longtext | NO |  |  |
| source | varchar(100) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `lm_scraped_data`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| data_type | varchar(30) | NO |  |  |
| data_json | text | NO |  |  |
| scraped_at | datetime | NO |  |  |
| expires_at | datetime | NO | MUL |  |

### `lm_signal_performance`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_source | varchar(50) | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| signal_date | date | NO | MUL |  |
| signal_direction | varchar(10) | NO |  |  |
| entry_price | decimal(12,2) | NO |  | 0.00 |
| price_7d | decimal(12,2) | NO |  | 0.00 |
| price_30d | decimal(12,2) | NO |  | 0.00 |
| price_90d | decimal(12,2) | NO |  | 0.00 |
| return_7d | decimal(8,2) | NO |  | 0.00 |
| return_30d | decimal(8,2) | NO |  | 0.00 |
| return_90d | decimal(8,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `lm_signals`  (35544 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(10) | NO | MUL |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| signal_type | varchar(20) | NO |  | BUY |
| signal_strength | int | NO |  | 0 |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| target_tp_pct | decimal(6,2) | NO |  | 5.00 |
| target_sl_pct | decimal(6,2) | NO |  | 3.00 |
| max_hold_hours | int | NO |  | 24 |
| timeframe | varchar(20) | NO |  | 1h |
| rationale | text | YES |  |  |
| param_source | varchar(10) | NO |  | original |
| tp_original | decimal(6,2) | NO |  | 0.00 |
| sl_original | decimal(6,2) | NO |  | 0.00 |
| hold_original | int | NO |  | 0 |
| signal_time | datetime | NO | MUL |  |
| expires_at | datetime | NO |  |  |
| status | varchar(20) | NO | MUL | active |
| exit_price | decimal(18,8) | YES |  | 0.00000000 |
| pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| exit_reason | varchar(30) | YES |  |  |
| resolved_at | datetime | YES |  |  |
| current_price | decimal(18,8) | YES |  | 0.00000000 |

### `lm_smart_consensus`  (588 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| calc_date | date | NO | MUL |  |
| overall_score | int | NO | MUL | 0 |
| technical_score | int | NO |  | 0 |
| smart_money_score | int | NO |  | 0 |
| insider_score | int | NO |  | 0 |
| analyst_score | int | NO |  | 0 |
| momentum_score | int | NO |  | 0 |
| social_score | int | NO |  | 0 |
| signal_direction | varchar(10) | NO | MUL |  |
| confidence | varchar(20) | NO |  |  |
| regime | varchar(20) | NO |  | neutral |
| explanation | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_snapshots`  (2193 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_time | datetime | NO | MUL |  |
| total_value_usd | decimal(12,2) | NO |  | 10000.00 |
| cash_usd | decimal(12,2) | NO |  | 10000.00 |
| invested_usd | decimal(12,2) | NO |  | 0.00 |
| open_positions | int | NO |  | 0 |
| unrealized_pnl_usd | decimal(12,2) | NO |  | 0.00 |
| realized_pnl_today | decimal(12,2) | NO |  | 0.00 |
| cumulative_pnl_usd | decimal(12,2) | NO |  | 0.00 |
| total_trades | int | NO |  | 0 |
| total_wins | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| peak_value | decimal(12,2) | NO |  | 10000.00 |
| drawdown_pct | decimal(8,4) | NO |  | 0.0000 |

### `lm_sports_bankroll`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | UNI |  |
| bankroll | decimal(10,2) | NO |  | 1000.00 |
| total_bets | int | NO |  | 0 |
| total_wins | int | NO |  | 0 |
| total_losses | int | NO |  | 0 |
| total_pushes | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| total_wagered | decimal(10,2) | NO |  | 0.00 |
| total_pnl | decimal(10,2) | NO |  | 0.00 |
| roi_pct | decimal(6,2) | NO |  | 0.00 |

### `lm_sports_bets`  (74 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| event_id | varchar(100) | NO | MUL |  |
| sport | varchar(50) | NO | MUL |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| commence_time | datetime | NO |  |  |
| game_date | date | YES | MUL |  |
| bet_type | varchar(30) | NO |  | moneyline |
| market | varchar(20) | NO |  | h2h |
| pick | varchar(100) | NO |  |  |
| pick_point | decimal(6,2) | YES |  |  |
| bookmaker | varchar(50) | NO |  |  |
| bookmaker_key | varchar(50) | NO |  |  |
| odds | decimal(10,4) | NO |  | 0.0000 |
| implied_prob | decimal(6,4) | NO |  | 0.0000 |
| bet_amount | decimal(10,2) | NO |  | 0.00 |
| potential_payout | decimal(10,2) | NO |  | 0.00 |
| algorithm | varchar(50) | NO | MUL | value_bet |
| ev_pct | decimal(6,2) | NO |  | 0.00 |
| status | varchar(20) | NO | MUL | pending |
| result | varchar(20) | YES |  |  |
| pnl | decimal(10,2) | YES |  |  |
| settled_at | datetime | YES |  |  |
| actual_home_score | int | YES |  |  |
| actual_away_score | int | YES |  |  |
| placed_at | datetime | NO | MUL |  |

### `lm_sports_clv`  (20607 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| event_id | varchar(100) | NO | MUL |  |
| sport | varchar(50) | NO | MUL |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| commence_time | datetime | NO | MUL |  |
| bookmaker_key | varchar(50) | NO |  |  |
| market | varchar(20) | NO |  | h2h |
| outcome_name | varchar(100) | NO |  |  |
| opening_price | decimal(10,4) | NO |  | 0.0000 |
| closing_price | decimal(10,4) | YES |  |  |
| opening_implied_prob | decimal(8,6) | YES |  |  |
| closing_implied_prob | decimal(8,6) | YES |  |  |
| clv_pct | decimal(8,4) | YES |  |  |
| first_seen | datetime | NO |  |  |
| last_updated | datetime | NO |  |  |

### `lm_sports_credit_usage`  (132 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| request_time | datetime | NO | MUL |  |
| sport | varchar(50) | NO |  | all |
| credits_used | int | NO |  | 0 |
| credits_remaining | int | YES |  |  |

### `lm_sports_daily_picks`  (222 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pick_date | date | NO | MUL |  |
| generated_at | datetime | NO |  |  |
| sport | varchar(50) | NO | MUL |  |
| event_id | varchar(100) | NO | MUL |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| commence_time | datetime | NO |  |  |
| market | varchar(20) | NO |  |  |
| pick_type | varchar(50) | NO |  |  |
| outcome_name | varchar(100) | NO |  |  |
| best_book | varchar(50) | NO |  |  |
| best_book_key | varchar(50) | NO |  |  |
| best_odds | decimal(10,4) | NO |  | 0.0000 |
| ev_pct | decimal(6,2) | NO |  | 0.00 |
| kelly_bet | decimal(10,2) | NO |  | 0.00 |
| algorithm | varchar(50) | NO |  | value_bet |
| confidence | varchar(20) | NO |  | medium |
| result | varchar(20) | YES | MUL |  |
| pnl | decimal(10,2) | YES |  |  |
| all_odds | text | YES |  |  |

### `lm_sports_ml_metrics`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| metric_date | date | NO | MUL |  |
| model_type | varchar(50) | NO |  | ensemble |
| n_training_bets | int | NO |  | 0 |
| accuracy | decimal(6,4) | YES |  |  |
| auc_roc | decimal(6,4) | YES |  |  |
| brier_score | decimal(6,4) | YES |  |  |
| precision_score | decimal(6,4) | YES |  |  |
| recall_score | decimal(6,4) | YES |  |  |
| f1_score | decimal(6,4) | YES |  |  |
| avg_clv | decimal(8,4) | YES |  |  |
| positive_clv_pct | decimal(6,2) | YES |  |  |
| top_features | text | YES |  |  |
| notes | text | YES |  |  |
| recorded_at | datetime | NO |  |  |

### `lm_sports_ml_predictions`  (79 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| value_bet_id | int | NO |  | 0 |
| event_id | varchar(100) | NO | MUL |  |
| sport | varchar(50) | NO |  |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| outcome_name | varchar(100) | NO |  |  |
| market | varchar(20) | NO |  | h2h |
| ev_pct | decimal(6,2) | NO |  | 0.00 |
| best_odds | decimal(10,4) | NO |  | 0.0000 |
| ml_win_prob | decimal(6,4) | NO | MUL | 0.5000 |
| ml_prediction | varchar(20) | NO | MUL | lean |
| ml_confidence | varchar(20) | NO |  | low |
| ml_should_bet | tinyint | NO |  | 0 |
| model_type | varchar(50) | NO |  | baseline |
| predicted_at | datetime | NO | MUL |  |

### `lm_sports_odds`  (502 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| sport | varchar(50) | NO | MUL |  |
| event_id | varchar(100) | NO | MUL |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| commence_time | datetime | NO | MUL |  |
| bookmaker | varchar(50) | NO | MUL |  |
| bookmaker_key | varchar(50) | NO |  |  |
| market | varchar(20) | NO |  |  |
| outcome_name | varchar(100) | NO |  |  |
| outcome_price | decimal(10,4) | NO |  | 0.0000 |
| outcome_point | decimal(6,2) | YES |  |  |
| last_updated | datetime | NO |  |  |

### `lm_sports_value_bets`  (375 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| event_id | varchar(100) | NO | MUL |  |
| sport | varchar(50) | NO | MUL |  |
| home_team | varchar(100) | NO |  |  |
| away_team | varchar(100) | NO |  |  |
| commence_time | datetime | NO | MUL |  |
| market | varchar(20) | NO |  |  |
| bet_type | varchar(50) | NO |  |  |
| outcome_name | varchar(100) | NO |  |  |
| best_book | varchar(50) | NO |  |  |
| best_book_key | varchar(50) | NO |  |  |
| best_odds | decimal(10,4) | NO |  | 0.0000 |
| consensus_implied_prob | decimal(6,4) | NO |  | 0.0000 |
| true_prob | decimal(6,4) | NO |  | 0.0000 |
| edge_pct | decimal(6,2) | NO |  | 0.00 |
| ev_pct | decimal(6,2) | NO | MUL | 0.00 |
| kelly_fraction | decimal(6,4) | NO |  | 0.0000 |
| kelly_bet | decimal(10,2) | NO |  | 0.00 |
| all_odds | text | YES |  |  |
| detected_at | datetime | NO |  |  |
| status | varchar(20) | NO | MUL | active |

### `lm_supplemental_dimensions`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| calc_date | date | NO |  |  |
| options_score | int | NO |  | 50 |
| short_interest_score | int | NO |  | 50 |
| technical_score | int | NO |  | 50 |
| earnings_quality_score | int | NO |  | 50 |
| composite_supplemental | int | NO |  | 50 |
| detail_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_trades`  (201 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(10) | NO | MUL |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| signal_id | int | NO | MUL | 0 |
| direction | varchar(10) | NO |  | LONG |
| entry_time | datetime | NO | MUL |  |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| position_size_units | decimal(18,8) | NO |  | 0.00000000 |
| position_value_usd | decimal(12,2) | NO |  | 0.00 |
| target_tp_pct | decimal(6,2) | NO |  | 5.00 |
| target_sl_pct | decimal(6,2) | NO |  | 3.00 |
| max_hold_hours | int | NO |  | 24 |
| current_price | decimal(18,8) | NO |  | 0.00000000 |
| unrealized_pnl_usd | decimal(12,2) | NO |  | 0.00 |
| unrealized_pct | decimal(10,4) | NO |  | 0.0000 |
| highest_price | decimal(18,8) | NO |  | 0.00000000 |
| lowest_price | decimal(18,8) | NO |  | 0.00000000 |
| status | varchar(20) | NO | MUL | open |
| exit_time | datetime | YES |  |  |
| exit_price | decimal(18,8) | NO |  | 0.00000000 |
| exit_reason | varchar(50) | NO |  |  |
| realized_pnl_usd | decimal(12,2) | NO |  | 0.00 |
| realized_pct | decimal(10,4) | NO |  | 0.0000 |
| fees_usd | decimal(8,2) | NO |  | 0.00 |
| hold_hours | decimal(8,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `lm_virtual_comparison`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trade_id | int | NO | MUL | 0 |
| signal_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(10) | NO |  |  |
| symbol | varchar(20) | NO |  |  |
| direction | varchar(10) | NO |  |  |
| entry_price | decimal(18,8) | NO |  | 0.00000000 |
| actual_param_source | varchar(10) | NO | MUL | original |
| actual_tp | decimal(6,2) | NO |  | 0.00 |
| actual_sl | decimal(6,2) | NO |  | 0.00 |
| actual_hold | int | NO |  | 0 |
| actual_pnl_pct | decimal(10,4) | NO |  | 0.0000 |
| actual_outcome | varchar(10) | NO |  |  |
| original_tp | decimal(6,2) | NO |  | 0.00 |
| original_sl | decimal(6,2) | NO |  | 0.00 |
| original_hold | int | NO |  | 0 |
| virtual_original_pnl | decimal(10,4) | NO |  | 0.0000 |
| virtual_original_outcome | varchar(10) | NO |  |  |
| learned_tp | decimal(6,2) | NO |  | 0.00 |
| learned_sl | decimal(6,2) | NO |  | 0.00 |
| learned_hold | int | NO |  | 0 |
| virtual_learned_pnl | decimal(10,4) | NO |  | 0.0000 |
| virtual_learned_outcome | varchar(10) | NO |  |  |
| opened_at | datetime | YES |  |  |
| closed_at | datetime | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_walk_forward`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| asset_class | varchar(20) | NO |  |  |
| train_start | date | NO |  |  |
| train_end | date | NO |  |  |
| test_start | date | NO |  |  |
| test_end | date | NO | MUL |  |
| train_sharpe | decimal(8,4) | YES |  |  |
| train_win_rate | decimal(5,2) | YES |  |  |
| train_trades | int | YES |  | 0 |
| test_sharpe | decimal(8,4) | YES |  |  |
| test_win_rate | decimal(5,2) | YES |  |  |
| test_trades | int | YES |  | 0 |
| test_pnl | decimal(10,2) | YES |  |  |
| tp_pct | decimal(5,2) | YES |  |  |
| sl_pct | decimal(5,2) | YES |  |  |
| max_hold_hours | int | YES |  |  |
| sharpe_decay_pct | decimal(5,2) | YES |  |  |
| is_overfit | tinyint | YES |  | 0 |
| created_at | datetime | YES |  |  |

### `lm_webhook_config`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| webhook_url | varchar(500) | NO |  |  |
| is_active | tinyint | NO |  | 0 |
| last_sent | datetime | YES |  |  |
| last_response | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `lm_wsb_sentiment`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| scan_date | date | NO | MUL |  |
| mentions_24h | int | NO |  | 0 |
| sentiment | decimal(5,3) | NO |  | 0.000 |
| total_upvotes | int | NO |  | 0 |
| wsb_score | decimal(8,2) | NO | MUL | 0.00 |
| top_post_title | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |
| top_posts | text | YES |  |  |
| fetch_date | date | YES |  |  |

### `market_regimes`  (562 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| trade_date | date | NO | UNI |  |
| spy_close | decimal(10,2) | NO |  | 0.00 |
| spy_sma200 | decimal(10,2) | NO |  | 0.00 |
| vix_close | decimal(10,2) | NO |  | 0.00 |
| regime | varchar(20) | NO |  | unknown |
| sp500_close | decimal(10,2) | NO |  | 0.00 |
| sp500_change_pct | decimal(8,4) | NO |  | 0.0000 |
| source | varchar(30) | NO |  | computed |
| created_at | datetime | YES |  |  |

### `mc_daily_snapshots`  (1 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | UNI |  |
| signals | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | double | YES |  | 0 |
| avg_pnl | double | YES |  | 0 |
| total_pnl | double | YES |  | 0 |
| best_trade | double | YES |  | 0 |
| worst_trade | double | YES |  | 0 |
| unique_coins | int | YES |  | 0 |
| updated_at | datetime | YES |  |  |

### `mc_scan_log`  (6 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scan_id | varchar(20) | NO | MUL |  |
| pair | varchar(30) | NO |  |  |
| price | double | NO |  |  |
| score | int | NO |  | 0 |
| factors_json | text | YES |  |  |
| verdict | varchar(20) | NO |  | SKIP |
| chg_24h | double | YES |  | 0 |
| vol_usd_24h | double | YES |  | 0 |
| tier | varchar(10) | YES |  |  |
| created_at | datetime | NO | MUL |  |

### `mc_winners`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scan_id | varchar(20) | NO | MUL |  |
| pair | varchar(30) | NO | MUL |  |
| price_at_signal | double | NO |  |  |
| price_at_resolve | double | YES |  |  |
| score | int | NO |  | 0 |
| factors_json | text | YES |  |  |
| verdict | varchar(20) | NO |  | SKIP |
| target_pct | double | NO |  | 3 |
| risk_pct | double | NO |  | 2 |
| pnl_pct | double | YES |  |  |
| outcome | varchar(20) | YES | MUL |  |
| vol_usd_24h | double | YES |  | 0 |
| chg_24h | double | YES |  | 0 |
| tier | varchar(10) | YES | MUL | tier1 |
| created_at | datetime | NO | MUL |  |
| resolved_at | datetime | YES |  |  |

### `meme_ml_models`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| model_id | varchar(50) | YES | UNI |  |
| weights_json | text | YES |  |  |
| feature_importance_json | text | YES |  |  |
| metrics_json | text | YES |  |  |
| sample_count | int | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `meme_ml_predictions`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_id | varchar(50) | YES | MUL |  |
| model_id | varchar(50) | YES | MUL |  |
| predicted_probability | decimal(5,4) | YES |  |  |
| predicted_outcome | tinyint | YES |  |  |
| actual_outcome | tinyint | YES |  |  |
| feature_values_json | text | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `meme_ml_signals`  (50 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_id | varchar(50) | YES | UNI |  |
| coin_symbol | varchar(20) | YES | MUL |  |
| features_json | text | YES |  |  |
| outcome | varchar(10) | YES | MUL |  |
| profit_loss_pct | decimal(10,2) | YES |  |  |
| created_at | datetime | YES | MUL |  |
| resolved_at | datetime | YES |  |  |

### `meme_signal_results`  (50 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_id | varchar(50) | YES | UNI |  |
| outcome | varchar(10) | YES | MUL |  |
| profit_loss_pct | decimal(10,2) | YES |  |  |
| max_profit_pct | decimal(10,2) | YES |  |  |
| max_loss_pct | decimal(10,2) | YES |  |  |
| resolved_at | datetime | YES |  |  |

### `meme_signals`  (50 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| signal_id | varchar(50) | YES | UNI |  |
| coin_symbol | varchar(20) | YES | MUL |  |
| explosive_volume | decimal(5,2) | YES |  |  |
| parabolic_momentum | decimal(5,2) | YES |  |  |
| rsi_hype_zone | decimal(5,2) | YES |  |  |
| social_momentum_proxy | decimal(5,2) | YES |  |  |
| volume_concentration | decimal(5,2) | YES |  |  |
| breakout_4h | decimal(5,2) | YES |  |  |
| low_market_cap_bonus | decimal(5,2) | YES |  |  |
| tier | varchar(10) | YES |  |  |
| total_score | int | YES |  |  |
| created_at | datetime | YES | MUL |  |

### `mf2_algo_performance`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `mf2_algorithms`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |
| pros | text | YES |  |  |
| cons | text | YES |  |  |

### `mf2_audit_log`  (340 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `mf2_backtest_results`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| algorithm_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| annualized_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| best_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_trade_pct | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_fees | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| sortino_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| avg_hold_days | decimal(8,2) | NO |  | 0.00 |
| fee_drag_pct | decimal(10,4) | NO |  | 0.0000 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `mf2_backtest_trades`  (450 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| entry_date | date | NO |  |  |
| entry_nav | decimal(12,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_nav | decimal(12,4) | NO |  | 0.0000 |
| units | decimal(12,4) | NO |  | 0.0000 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| fees_paid | decimal(8,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `mf2_category_perf`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| category | varchar(200) | NO | MUL |  |
| period | varchar(20) | NO |  | 1m |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| top_fund | varchar(20) | NO |  |  |
| worst_fund | varchar(20) | NO |  |  |
| fund_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `mf2_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `mf2_fund_picks`  (600 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_nav | decimal(12,4) | NO |  | 0.0000 |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |
| rationale_json | text | YES |  |  |

### `mf2_funds`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| symbol | varchar(20) | NO | PRI |  |
| fund_name | varchar(300) | NO |  |  |
| fund_family | varchar(200) | NO |  |  |
| category | varchar(200) | NO |  |  |
| asset_class | varchar(50) | NO |  |  |
| expense_ratio | decimal(6,4) | NO |  | 0.0000 |
| min_investment | decimal(12,2) | NO |  | 0.00 |
| inception_date | date | YES |  |  |
| morningstar_rating | tinyint | NO |  | 0 |

### `mf2_nav_history`  (6860 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| nav_date | date | NO | MUL |  |
| nav | decimal(12,4) | NO |  | 0.0000 |
| prev_nav | decimal(12,4) | NO |  | 0.0000 |
| daily_return_pct | decimal(10,6) | NO |  | 0.000000 |
| volume | bigint | NO |  | 0 |

### `mf2_portfolios`  (12 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | balanced |
| algorithm_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| commission_buy | decimal(6,2) | NO |  | 0.00 |
| commission_sell | decimal(6,2) | NO |  | 0.00 |
| redemption_fee_pct | decimal(5,2) | NO |  | 0.00 |
| target_return_pct | decimal(5,2) | NO |  | 10.00 |
| stop_loss_pct | decimal(5,2) | NO |  | 8.00 |
| max_hold_days | int | NO |  | 90 |
| position_size_pct | decimal(5,2) | NO |  | 20.00 |
| max_positions | int | NO |  | 5 |
| created_at | datetime | NO |  |  |

### `mf2_tracked_picks`  (75 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| pick_date | date | NO |  |  |
| entry_nav | decimal(12,4) | NO |  |  |
| current_nav | decimal(12,4) | YES |  |  |
| current_return_pct | decimal(8,4) | YES |  |  |
| status | enum('open','closed') | YES | MUL | open |
| exit_date | date | YES |  |  |
| exit_nav | decimal(12,4) | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| final_return_pct | decimal(8,4) | YES |  |  |
| peak_nav | decimal(12,4) | YES |  |  |
| trough_nav | decimal(12,4) | YES |  |  |
| hold_days | int | YES |  | 0 |
| score | decimal(5,2) | YES |  |  |
| rating | varchar(10) | YES |  |  |
| created_at | datetime | YES |  |  |

### `mf2_tracking_daily`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| track_date | date | NO | UNI |  |
| open_positions | int | YES |  | 0 |
| total_closed | int | YES |  | 0 |
| total_wins | int | YES |  | 0 |
| total_losses | int | YES |  | 0 |
| win_rate | decimal(5,2) | YES |  | 0.00 |
| avg_win_pct | decimal(8,4) | YES |  | 0.0000 |
| avg_loss_pct | decimal(8,4) | YES |  | 0.0000 |
| avg_return_pct | decimal(8,4) | YES |  | 0.0000 |
| best_symbol | varchar(20) | YES |  |  |
| worst_symbol | varchar(20) | YES |  |  |
| avg_hold_days | decimal(5,1) | YES |  | 0.0 |
| created_at | datetime | YES |  |  |

### `mf2_tracking_lessons`  (9 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| lesson_date | date | NO | MUL |  |
| lesson_type | varchar(50) | NO | MUL |  |
| lesson_title | varchar(200) | NO |  |  |
| lesson_text | text | NO |  |  |
| confidence | decimal(5,2) | YES |  | 0.00 |
| supporting_data | text | YES |  |  |
| applied | tinyint | YES |  | 0 |
| impact_score | decimal(5,2) | YES |  |  |
| created_at | datetime | YES |  |  |

### `mf2_whatif_scenarios`  (2 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `mf_algo_performance`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_type | varchar(50) | NO |  |  |
| total_picks | int | NO |  | 0 |
| total_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| best_for | varchar(200) | NO |  |  |
| worst_for | varchar(200) | NO |  |  |
| updated_at | datetime | NO |  |  |

### `mf_algorithms`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| algo_type | varchar(50) | NO |  | general |
| ideal_timeframe | varchar(20) | NO |  |  |
| pros | text | YES |  |  |
| cons | text | YES |  |  |

### `mf_audit_log`  (260 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `mf_backtest_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| strategy_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| annualized_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_expenses | decimal(12,2) | NO |  | 0.00 |
| total_commissions | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| alpha | decimal(10,4) | NO |  | 0.0000 |
| beta | decimal(10,4) | NO |  | 0.0000 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `mf_backtest_trades`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| ticker | varchar(15) | NO | MUL |  |
| strategy_name | varchar(200) | NO |  |  |
| entry_date | date | NO |  |  |
| entry_nav | decimal(12,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_nav | decimal(12,4) | NO |  | 0.0000 |
| shares | decimal(12,4) | NO |  | 0.0000 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| expense_cost | decimal(8,2) | NO |  | 0.00 |
| commission_paid | decimal(8,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `mf_benchmarks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(15) | NO | MUL |  |
| bench_name | varchar(200) | NO |  |  |
| bench_type | varchar(50) | NO | MUL |  |
| nav_date | date | NO |  |  |
| nav_price | decimal(12,4) | NO |  | 0.0000 |

### `mf_category_perf`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| category | varchar(200) | NO | MUL |  |
| period | varchar(20) | NO |  | 1m |
| avg_return_pct | decimal(10,4) | NO |  | 0.0000 |
| top_fund | varchar(20) | NO |  |  |
| worst_fund | varchar(20) | NO |  |  |
| fund_count | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `mf_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `mf_fund_picks`  (15 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_nav | decimal(12,4) | NO |  | 0.0000 |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |
| rationale_json | text | YES |  |  |

### `mf_funds`  (20 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| ticker | varchar(15) | NO | PRI |  |
| fund_name | varchar(300) | NO |  |  |
| category | varchar(150) | NO |  |  |
| family | varchar(150) | NO |  |  |
| expense_ratio | decimal(5,4) | NO |  | 0.0000 |
| min_investment | decimal(12,2) | NO |  | 0.00 |
| load_type | varchar(30) | NO |  | no-load |
| front_load_pct | decimal(5,2) | NO |  | 0.00 |
| back_load_pct | decimal(5,2) | NO |  | 0.00 |
| morningstar_rating | tinyint | NO |  | 0 |
| asset_class | varchar(50) | NO |  |  |
| inception_date | date | YES |  |  |
| net_assets | varchar(30) | NO |  |  |

### `mf_nav_history`  (5000 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(15) | NO | MUL |  |
| nav_date | date | NO | MUL |  |
| nav_price | decimal(12,4) | NO |  | 0.0000 |
| adj_nav | decimal(12,4) | NO |  | 0.0000 |
| change_pct | decimal(8,4) | NO |  | 0.0000 |
| volume | bigint | NO |  | 0 |

### `mf_portfolios`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | balanced |
| strategy_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| commission_buy | decimal(6,2) | NO |  | 0.00 |
| commission_sell | decimal(6,2) | NO |  | 0.00 |
| hold_period_days | int | NO |  | 90 |
| rebalance_freq | varchar(20) | NO |  | quarterly |
| target_return_pct | decimal(5,2) | NO |  | 0.00 |
| stop_loss_pct | decimal(5,2) | NO |  | 0.00 |
| expense_drag_annual | decimal(5,4) | NO |  | 0.0000 |
| created_at | datetime | NO |  |  |

### `mf_report_cache`  (2 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| cache_key | varchar(50) | NO | PRI |  |
| cache_data | longtext | YES |  |  |
| updated_at | datetime | YES |  |  |

### `mf_selections`  (34 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(15) | NO | MUL |  |
| strategy_id | int | NO |  | 0 |
| strategy_name | varchar(200) | NO | MUL |  |
| select_date | date | NO | MUL |  |
| nav_at_select | decimal(12,4) | NO |  | 0.0000 |
| category | varchar(150) | NO |  |  |
| expense_ratio | decimal(5,4) | NO |  | 0.0000 |
| morningstar_rating | tinyint | NO |  | 0 |
| rationale | text | YES |  |  |
| select_hash | varchar(64) | NO |  |  |

### `mf_simulation_grid`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| batch_id | int | YES |  | 0 |
| strategy | varchar(200) | YES | MUL |  |
| hold_days | int | YES |  | 90 |
| stop_loss | decimal(6,2) | YES |  | 0.00 |
| target_return | decimal(6,2) | YES |  | 0.00 |
| commission | decimal(6,2) | YES |  | 0.00 |
| total_trades | int | YES |  | 0 |
| winning_trades | int | YES |  | 0 |
| win_rate | decimal(6,2) | YES |  | 0.00 |
| total_return_pct | decimal(10,4) | YES | MUL | 0.0000 |
| annualized_return_pct | decimal(10,4) | YES |  | 0.0000 |
| final_value | decimal(12,2) | YES |  | 10000.00 |
| max_drawdown_pct | decimal(8,4) | YES |  | 0.0000 |
| sharpe_ratio | decimal(8,4) | YES |  | 0.0000 |
| total_pnl | decimal(12,2) | YES |  | 0.00 |
| total_expenses | decimal(10,2) | YES |  | 0.00 |
| created_at | datetime | YES |  |  |

### `mf_simulation_meta`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| meta_key | varchar(50) | NO | PRI |  |
| meta_value | text | YES |  |  |
| updated_at | datetime | YES |  |  |

### `mf_strategies`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO | UNI |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | general |
| selection_criteria | text | YES |  |  |
| ideal_timeframe | varchar(30) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |

### `mf_whatif_scenarios`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `miracle_audit2`  (678 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `miracle_audit3`  (424 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| action_type | varchar(50) | NO | MUL |  |
| details | text | YES |  |  |
| ip_address | varchar(45) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `miracle_learning3`  (428 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| strategy_name | varchar(100) | NO | MUL |  |
| param_name | varchar(50) | NO |  |  |
| old_value | decimal(10,4) | NO |  | 0.0000 |
| new_value | decimal(10,4) | NO |  | 0.0000 |
| reason | text | YES |  |  |
| backtest_win_rate | decimal(5,2) | NO |  | 0.00 |
| backtest_return_pct | decimal(10,4) | NO |  | 0.0000 |
| applied_at | datetime | NO | MUL |  |

### `miracle_picks2`  (249 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| strategy_name | varchar(100) | NO | MUL |  |
| scan_date | date | NO | MUL |  |
| scan_time | datetime | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| stop_loss_price | decimal(12,4) | NO |  | 0.0000 |
| take_profit_price | decimal(12,4) | NO |  | 0.0000 |
| stop_loss_pct | decimal(5,2) | NO |  | 0.00 |
| take_profit_pct | decimal(5,2) | NO |  | 0.00 |
| score | int | NO |  | 0 |
| confidence | varchar(20) | NO |  | medium |
| signals_json | text | YES |  |  |
| is_cdr | tinyint | NO |  | 0 |
| questrade_fee | decimal(8,2) | NO |  | 0.00 |
| net_profit_if_tp | decimal(12,2) | NO |  | 0.00 |
| risk_reward_ratio | decimal(5,2) | NO |  | 0.00 |
| outcome | varchar(20) | NO | MUL | pending |
| outcome_price | decimal(12,4) | NO |  | 0.0000 |
| outcome_pct | decimal(10,4) | NO |  | 0.0000 |
| outcome_date | date | YES |  |  |
| pick_hash | varchar(64) | NO | MUL |  |

### `miracle_picks3`  (672 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| company_name | varchar(200) | NO |  |  |
| strategy_name | varchar(100) | NO | MUL |  |
| scan_date | date | NO | MUL |  |
| scan_time | datetime | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| stop_loss_price | decimal(12,4) | NO |  | 0.0000 |
| take_profit_price | decimal(12,4) | NO |  | 0.0000 |
| stop_loss_pct | decimal(5,2) | NO |  | 0.00 |
| take_profit_pct | decimal(5,2) | NO |  | 0.00 |
| score | int | NO | MUL | 0 |
| confidence | varchar(20) | NO |  | medium |
| direction | varchar(10) | NO |  | LONG |
| signals_json | text | YES |  |  |
| is_cdr | tinyint | NO |  | 0 |
| is_canadian | tinyint | NO |  | 0 |
| questrade_buy_fee | decimal(8,2) | NO |  | 0.00 |
| questrade_sell_fee | decimal(8,2) | NO |  | 0.00 |
| net_profit_if_tp | decimal(12,2) | NO |  | 0.00 |
| risk_reward_ratio | decimal(5,2) | NO |  | 0.00 |
| outcome | varchar(20) | NO | MUL | pending |
| outcome_price | decimal(12,4) | NO |  | 0.0000 |
| outcome_pct | decimal(10,4) | NO |  | 0.0000 |
| outcome_date | date | YES |  |  |
| outcome_reason | varchar(50) | NO |  |  |
| pick_hash | varchar(64) | NO | MUL |  |

### `miracle_portfolios2`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| position_size_pct | decimal(5,2) | NO |  | 10.00 |
| max_positions | int | NO |  | 5 |
| fee_model | varchar(20) | NO |  | questrade |
| prefer_cdr | tinyint | NO |  | 1 |
| created_at | datetime | NO |  |  |

### `miracle_portfolios3`  (6 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO | UNI |  |
| description | text | YES |  |  |
| strategy_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| position_size_pct | decimal(5,2) | NO |  | 10.00 |
| max_positions | int | NO |  | 5 |
| fee_model | varchar(20) | NO |  | questrade |
| prefer_cdr | tinyint | NO |  | 1 |
| created_at | datetime | NO |  |  |

### `miracle_results2`  (143 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO |  | 0 |
| strategy_name | varchar(100) | NO | MUL |  |
| period | varchar(20) | NO |  | daily |
| calc_date | date | NO | MUL |  |
| total_picks | int | NO |  | 0 |
| winners | int | NO |  | 0 |
| losers | int | NO |  | 0 |
| pending_count | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_gain_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| total_pnl | decimal(12,2) | NO |  | 0.00 |
| best_pick_ticker | varchar(10) | NO |  |  |
| best_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_pick_ticker | varchar(10) | NO |  |  |
| worst_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| created_at | datetime | NO |  |  |

### `miracle_results3`  (80 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO |  | 0 |
| strategy_name | varchar(100) | NO | MUL |  |
| period | varchar(20) | NO |  | daily |
| calc_date | date | NO | MUL |  |
| total_picks | int | NO |  | 0 |
| winners | int | NO |  | 0 |
| losers | int | NO |  | 0 |
| pending_count | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_gain_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| total_pnl | decimal(12,2) | NO |  | 0.00 |
| best_pick_ticker | varchar(10) | NO |  |  |
| best_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| worst_pick_ticker | varchar(10) | NO |  |  |
| worst_pick_pct | decimal(10,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| created_at | datetime | NO |  |  |

### `miracle_strategies2`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  |  |
| description | text | YES |  |  |
| scan_type | varchar(50) | NO |  | momentum |
| ideal_hold | varchar(20) | NO |  | 1d |
| default_tp_pct | decimal(5,2) | NO |  | 5.00 |
| default_sl_pct | decimal(5,2) | NO |  | 3.00 |
| enabled | tinyint | NO |  | 1 |

### `miracle_strategies3`  (8 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(100) | NO | UNI |  |
| family | varchar(50) | NO |  | day_trade |
| description | text | YES |  |  |
| scan_type | varchar(50) | NO |  | momentum |
| ideal_hold | varchar(20) | NO |  | 1d |
| default_tp_pct | decimal(5,2) | NO |  | 5.00 |
| default_sl_pct | decimal(5,2) | NO |  | 3.00 |
| min_score | int | NO |  | 50 |
| enabled | tinyint | NO |  | 1 |
| created_at | datetime | YES |  |  |

### `miracle_watchlist2`  (68 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| company_name | varchar(200) | NO |  |  |
| sector | varchar(100) | NO |  |  |
| reason | text | YES |  |  |
| is_cdr | tinyint | NO |  | 0 |
| added_date | date | NO |  |  |
| source | varchar(50) | NO |  | scanner |
| active | tinyint | NO |  | 1 |

### `miracle_watchlist3`  (56 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| company_name | varchar(200) | NO |  |  |
| sector | varchar(50) | NO |  |  |
| is_cdr | tinyint | NO |  | 0 |
| is_canadian | tinyint | NO |  | 0 |
| reason | text | YES |  |  |
| added_date | date | NO |  |  |
| source | varchar(50) | NO |  | seed |
| active | tinyint | NO |  | 1 |

### `ml_ab_tests`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| test_id | varchar(50) | NO | UNI |  |
| model_a_id | varchar(50) | NO |  |  |
| model_b_id | varchar(50) | NO |  |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| started_at | datetime | YES |  |  |
| ended_at | datetime | YES |  |  |
| a_predictions | int | YES |  | 0 |
| a_wins | int | YES |  | 0 |
| a_total_pnl | float | YES |  | 0 |
| a_sharpe | float | YES |  | 0 |
| b_predictions | int | YES |  | 0 |
| b_wins | int | YES |  | 0 |
| b_total_pnl | float | YES |  | 0 |
| b_sharpe | float | YES |  | 0 |
| p_value | float | YES |  | 1 |
| winner | varchar(10) | YES |  | NONE |
| confidence_level | float | YES |  | 0 |
| status | varchar(20) | YES | MUL | RUNNING |

### `ml_calibration_log`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(50) | NO | MUL |  |
| confidence_bucket | int | NO |  |  |
| total_predictions | int | YES |  | 0 |
| correct_predictions | int | YES |  | 0 |
| actual_rate | float | YES |  | 0 |
| calibration_error | float | YES |  | 0 |
| computed_at | datetime | YES |  |  |

### `ml_ensemble_weights`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | YES |  | ALL |
| asset_class | varchar(20) | YES |  | CRYPTO |
| engine_name | varchar(50) | NO | MUL |  |
| weight | float | YES |  | 1 |
| weight_reason | varchar(100) | YES |  |  |
| win_rate | float | YES |  | 0 |
| sample_size | int | YES |  | 0 |
| computed_at | datetime | YES |  |  |

### `ml_feature_store`  (396 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| timestamp | datetime | NO |  |  |
| timeframe | varchar(10) | YES | MUL | 4H |
| close_price | float | YES |  | 0 |
| return_1 | float | YES |  | 0 |
| return_5 | float | YES |  | 0 |
| return_20 | float | YES |  | 0 |
| log_return | float | YES |  | 0 |
| rsi_14 | float | YES |  | 0 |
| macd_value | float | YES |  | 0 |
| macd_signal | float | YES |  | 0 |
| macd_histogram | float | YES |  | 0 |
| stoch_k | float | YES |  | 0 |
| stoch_d | float | YES |  | 0 |
| williams_r | float | YES |  | 0 |
| cci_20 | float | YES |  | 0 |
| roc_10 | float | YES |  | 0 |
| sma_20 | float | YES |  | 0 |
| sma_50 | float | YES |  | 0 |
| ema_9 | float | YES |  | 0 |
| ema_21 | float | YES |  | 0 |
| adx_14 | float | YES |  | 0 |
| plus_di | float | YES |  | 0 |
| minus_di | float | YES |  | 0 |
| price_vs_sma20 | float | YES |  | 0 |
| price_vs_sma50 | float | YES |  | 0 |
| atr_14 | float | YES |  | 0 |
| bollinger_upper | float | YES |  | 0 |
| bollinger_lower | float | YES |  | 0 |
| bollinger_width | float | YES |  | 0 |
| bollinger_pct_b | float | YES |  | 0 |
| realized_vol_20 | float | YES |  | 0 |
| volume | float | YES |  | 0 |
| volume_sma_20 | float | YES |  | 0 |
| volume_ratio | float | YES |  | 0 |
| obv | float | YES |  | 0 |
| hurst_exponent | float | YES |  | 0.5 |
| autocorrelation_1 | float | YES |  | 0 |
| volatility_stability | float | YES |  | 0 |
| signal_noise_ratio | float | YES |  | 0 |
| pattern_detected | varchar(50) | YES |  |  |
| pattern_strength | float | YES |  | 0 |
| engines_bullish | int | YES |  | 0 |
| engines_bearish | int | YES |  | 0 |
| engines_total | int | YES |  | 0 |
| engine_agreement | float | YES |  | 0 |
| target_1h | float | YES |  |  |
| target_4h | float | YES |  |  |
| target_24h | float | YES |  |  |
| target_direction | varchar(10) | YES |  |  |

### `ml_learning_curve`  (14 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(50) | NO | MUL |  |
| data_date | date | NO |  |  |
| sample_count | int | YES |  | 0 |
| rolling_win_rate | float | YES |  | 0 |
| rolling_sharpe | float | YES |  | 0 |
| rolling_profit_factor | float | YES |  | 0 |
| improvement_rate | float | YES |  | 0 |

### `ml_model_performance`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| model_id | int | NO | MUL |  |
| prediction_date | date | NO | MUL |  |
| symbol | varchar(20) | NO |  |  |
| predicted_signal | varchar(20) | YES |  |  |
| actual_outcome | varchar(20) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| was_correct | tinyint(1) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `ml_model_registry`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| model_id | varchar(50) | NO | UNI |  |
| model_name | varchar(100) | NO |  |  |
| model_type | varchar(50) | NO | MUL |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| target_horizon | varchar(20) | YES |  | 4H |
| features_used | text | YES |  |  |
| hyperparameters | text | YES |  |  |
| training_start | date | YES |  |  |
| training_end | date | YES |  |  |
| training_samples | int | YES |  | 0 |
| accuracy | float | YES |  | 0 |
| precision_score | float | YES |  | 0 |
| recall_score | float | YES |  | 0 |
| f1_score | float | YES |  | 0 |
| auc_roc | float | YES |  | 0 |
| sharpe_ratio | float | YES |  | 0 |
| profit_factor | float | YES |  | 0 |
| max_drawdown | float | YES |  | 0 |
| wf_accuracy | float | YES |  | 0 |
| wf_sharpe | float | YES |  | 0 |
| overfit_score | float | YES |  | 0 |
| status | varchar(20) | YES |  | TRAINING |
| is_active | tinyint | YES | MUL | 0 |
| deployed_at | datetime | YES |  |  |
| retired_at | datetime | YES |  |  |
| created_at | datetime | YES |  |  |

### `ml_models`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| model_name | varchar(100) | NO | MUL |  |
| model_version | varchar(20) | NO |  |  |
| model_type | varchar(50) | YES |  |  |
| asset_class | varchar(20) | YES |  |  |
| training_start | date | YES |  |  |
| training_end | date | YES |  |  |
| accuracy | decimal(5,4) | YES |  |  |
| precision_score | decimal(5,4) | YES |  |  |
| recall | decimal(5,4) | YES |  |  |
| f1_score | decimal(5,4) | YES |  |  |
| features_used | json | YES |  |  |
| hyperparameters | json | YES |  |  |
| is_active | tinyint(1) | YES | MUL | 0 |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `ml_platform_daily`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| metric_date | date | NO | UNI |  |
| total_signals_generated | int | YES |  | 0 |
| signals_crypto | int | YES |  | 0 |
| signals_stocks | int | YES |  | 0 |
| signals_forex | int | YES |  | 0 |
| signals_sports | int | YES |  | 0 |
| resolved_today | int | YES |  | 0 |
| wins_today | int | YES |  | 0 |
| losses_today | int | YES |  | 0 |
| daily_win_rate | float | YES |  | 0 |
| daily_pnl | float | YES |  | 0 |
| cumulative_pnl | float | YES |  | 0 |
| avg_predictability | float | YES |  | 0 |
| high_pred_win_rate | float | YES |  | 0 |
| low_pred_win_rate | float | YES |  | 0 |
| engines_active | int | YES |  | 0 |
| engines_total | int | YES |  | 0 |
| api_uptime_pct | float | YES |  | 100 |
| created_at | datetime | YES |  |  |

### `ml_regime_snapshots`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | MUL |  |
| asset_class | varchar(20) | YES |  | CRYPTO |
| btc_trend | varchar(10) | YES |  | NEUTRAL |
| market_fear_greed | int | YES |  | 50 |
| avg_hurst | float | YES |  | 0.5 |
| avg_correlation | float | YES |  | 0 |
| volatility_percentile | float | YES |  | 50 |
| trending_pairs | int | YES |  | 0 |
| mean_reverting_pairs | int | YES |  | 0 |
| random_pairs | int | YES |  | 0 |
| recommended_strategy | varchar(30) | YES |  | MULTI_INDICATOR |
| regime_confidence | float | YES |  | 0 |
| created_at | datetime | YES |  |  |

### `now_history`  (40647 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| run_id | varchar(36) | NO |  |  |
| scan_time | datetime | NO | MUL |  |
| symbol | varchar(20) | NO | MUL |  |
| direction | enum('LONG','SHORT') | NO |  |  |
| strategy | varchar(50) | NO | MUL |  |
| entry_price | decimal(20,8) | NO |  |  |
| sl_price | decimal(20,8) | YES |  |  |
| tp_price_1_5 | decimal(20,8) | YES |  |  |
| tp_price_2_0 | decimal(20,8) | YES |  |  |
| sl_pct | decimal(8,4) | YES |  |  |
| confidence | decimal(5,2) | YES |  |  |
| reason | text | YES |  |  |
| outcome_1_5 | enum('PENDING','TP_HIT','SL_HIT','EXPIRED') | YES | MUL | PENDING |
| outcome_2_0 | enum('PENDING','TP_HIT','SL_HIT','EXPIRED') | YES |  | PENDING |
| peak_price | decimal(20,8) | YES |  |  |
| trough_price | decimal(20,8) | YES |  |  |
| resolved_at | datetime | YES |  |  |
| actual_pnl_pct | decimal(8,4) | YES |  |  |

### `now_strategy_stats`  (17 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| strategy | varchar(50) | NO | PRI |  |
| total_picks | int | YES |  | 0 |
| wins_1_5 | int | YES |  | 0 |
| losses_1_5 | int | YES |  | 0 |
| wins_2_0 | int | YES |  | 0 |
| losses_2_0 | int | YES |  | 0 |
| expired | int | YES |  | 0 |
| win_rate_1_5 | decimal(5,2) | YES |  | 0.00 |
| win_rate_2_0 | decimal(5,2) | YES |  | 0.00 |
| avg_pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| best_trade_pct | decimal(8,4) | YES |  | 0.0000 |
| worst_trade_pct | decimal(8,4) | YES |  | 0.0000 |
| last_updated | datetime | YES |  |  |

### `paper_portfolio_daily`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | UNI |  |
| open_positions | int | NO |  | 0 |
| total_invested | decimal(12,2) | NO |  | 0.00 |
| unrealized_pnl | decimal(12,2) | NO |  | 0.00 |
| realized_pnl_today | decimal(12,2) | NO |  | 0.00 |
| cumulative_realized_pnl | decimal(12,2) | NO |  | 0.00 |
| total_trades | int | NO |  | 0 |
| total_wins | int | NO |  | 0 |
| total_losses | int | NO |  | 0 |
| win_rate_to_date | decimal(5,2) | NO |  | 0.00 |
| peak_equity | decimal(12,2) | NO |  | 0.00 |
| current_drawdown_pct | decimal(8,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(8,4) | NO |  | 0.0000 |
| regime | varchar(20) | NO |  |  |
| created_at | datetime | NO |  |  |

### `paper_trades`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| enter_date | date | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| source_table | varchar(30) | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| target_tp_pct | decimal(6,2) | NO |  | 5.00 |
| target_sl_pct | decimal(6,2) | NO |  | 3.00 |
| max_hold_days | int | NO |  | 7 |
| position_size_pct | decimal(6,2) | NO |  | 10.00 |
| kelly_fraction | decimal(8,4) | NO |  | 0.0000 |
| regime_at_entry | varchar(20) | NO |  |  |
| score | int | NO |  | 0 |
| status | varchar(20) | NO | MUL | open |
| current_price | decimal(12,4) | NO |  | 0.0000 |
| unrealized_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| hold_days | int | NO |  | 0 |
| created_at | datetime | NO |  |  |
| resolved_at | datetime | YES |  |  |

### `penny_picks`  (1029 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pick_date | date | NO | MUL |  |
| symbol | varchar(20) | NO | MUL |  |
| name | varchar(200) | NO |  |  |
| price | decimal(10,4) | NO |  | 0.0000 |
| composite_score | decimal(5,2) | NO | MUL | 0.00 |
| rating | varchar(20) | NO | MUL | HOLD |
| market_cap | bigint | NO |  | 0 |
| exchange_name | varchar(30) | NO |  |  |
| country | varchar(5) | NO |  |  |
| rrsp_eligible | tinyint | NO |  | 0 |
| avg_volume | int | NO |  | 0 |
| stop_loss_pct | decimal(5,2) | NO |  | 15.00 |
| take_profit_pct | decimal(5,2) | NO |  | 30.00 |
| max_hold_days | int | NO |  | 90 |
| position_size_pct | decimal(5,2) | NO |  | 1.50 |
| health_score | decimal(5,2) | NO |  | 0.00 |
| momentum_score | decimal(5,2) | NO |  | 0.00 |
| volume_score | decimal(5,2) | NO |  | 0.00 |
| technical_score | decimal(5,2) | NO |  | 0.00 |
| earnings_score | decimal(5,2) | NO |  | 0.00 |
| smart_money_score | decimal(5,2) | NO |  | 0.00 |
| quality_score | decimal(5,2) | NO |  | 0.00 |
| z_score | decimal(6,2) | NO |  | 0.00 |
| f_score | int | NO |  | 0 |
| current_ratio | decimal(6,2) | NO |  | 0.00 |
| rsi | decimal(5,1) | NO |  | 50.0 |
| ema_alignment | int | NO |  | 0 |
| rvol | decimal(6,2) | NO |  | 1.00 |
| mom_3m | decimal(8,2) | NO |  | 0.00 |
| mom_6m | decimal(8,2) | NO |  | 0.00 |
| inst_pct | decimal(5,1) | NO |  | 0.0 |
| short_pct | decimal(5,1) | NO |  | 0.0 |
| ann_volatility | decimal(6,1) | NO |  | 0.0 |
| status | varchar(20) | NO | MUL | active |
| current_price | decimal(10,4) | NO |  | 0.0000 |
| current_return_pct | decimal(8,2) | NO |  | 0.00 |
| exit_price | decimal(10,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_reason | varchar(50) | NO |  |  |
| created_at | datetime | NO |  |  |

### `penny_picks_daily`  (54 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snap_date | date | NO | MUL |  |
| total_scored | int | NO |  | 0 |
| top_picks_count | int | NO |  | 0 |
| avg_score | decimal(5,2) | NO |  | 0.00 |
| buy_count | int | NO |  | 0 |
| strong_buy_count | int | NO |  | 0 |
| active_picks | int | NO |  | 0 |
| closed_picks | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_return_pct | decimal(8,2) | NO |  | 0.00 |
| total_return_pct | decimal(8,2) | NO |  | 0.00 |
| created_at | datetime | NO |  |  |

### `penny_stocks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | UNI |  |
| avg_volume_30d | bigint | YES |  |  |
| volatility_30d | decimal(8,4) | YES | MUL |  |
| float_shares | bigint | YES |  |  |
| short_interest | decimal(8,4) | YES |  |  |
| catalyst_news | text | YES |  |  |
| pump_score | int | YES | MUL |  |
| is_premarket_gainer | tinyint(1) | YES |  | 0 |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `pf_alerts`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(15) | NO | MUL | CRYPTO |
| alert_type | varchar(30) | NO |  | PATTERN_MATCH |
| pattern_name | varchar(50) | NO |  |  |
| confidence_pct | decimal(5,2) | YES | MUL | 0.00 |
| entry_price | decimal(20,10) | YES |  | 0.0000000000 |
| target_tp_pct | decimal(6,2) | YES |  | 0.00 |
| target_sl_pct | decimal(6,2) | YES |  | 0.00 |
| max_hold_hours | int | YES |  | 24 |
| signal_type | varchar(10) | YES |  | BUY |
| rationale | text | YES |  |  |
| status | varchar(20) | YES | MUL | active |
| exit_price | decimal(20,10) | YES |  | 0.0000000000 |
| pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| exit_reason | varchar(30) | YES |  |  |
| created_at | datetime | NO | MUL |  |
| resolved_at | datetime | YES |  |  |

### `pf_challenge_positions`  (62 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | varchar(50) | NO | MUL |  |
| position_id | varchar(20) | NO |  |  |
| symbol | varchar(20) | NO | MUL |  |
| direction | varchar(10) | NO |  |  |
| strategy | varchar(100) | NO |  |  |
| source_system | varchar(50) | YES |  |  |
| entry_price | decimal(20,8) | NO |  |  |
| take_profit | decimal(20,8) | YES |  | 0.00000000 |
| stop_loss | decimal(20,8) | YES |  | 0.00000000 |
| exit_price | decimal(20,8) | YES |  | 0.00000000 |
| size_usd | decimal(12,2) | NO |  |  |
| pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| pnl_usd | decimal(12,2) | YES |  | 0.00 |
| net_pnl_usd | decimal(12,2) | YES |  | 0.00 |
| commission_entry | decimal(8,2) | YES |  | 0.00 |
| commission_exit | decimal(8,2) | YES |  | 0.00 |
| exit_reason | varchar(20) | YES |  |  |
| status | varchar(20) | NO | MUL | OPEN |
| opened_at | varchar(40) | NO |  |  |
| closed_at | varchar(40) | YES |  |  |
| rr_ratio | decimal(6,2) | YES |  | 0.00 |
| sys_wr | decimal(5,2) | YES |  | 0.00 |
| sys_pf | decimal(6,2) | YES |  | 0.00 |
| confidence | decimal(4,2) | YES |  | 0.00 |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP |

### `pf_fingerprints`  (47 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(15) | NO | MUL | CRYPTO |
| behavior_type | varchar(30) | NO | MUL | UNKNOWN |
| momentum_corr | decimal(8,4) | YES |  | 0.0000 |
| mean_revert_score | decimal(8,4) | YES |  | 0.0000 |
| trend_score | decimal(8,4) | YES |  | 0.0000 |
| breakout_score | decimal(8,4) | YES |  | 0.0000 |
| pump_susceptibility | decimal(8,4) | YES |  | 0.0000 |
| avg_volatility_pct | decimal(8,4) | YES |  | 0.0000 |
| optimal_tp_pct | decimal(6,2) | YES |  | 0.00 |
| optimal_sl_pct | decimal(6,2) | YES |  | 0.00 |
| optimal_hold_hours | int | YES |  | 24 |
| best_algorithm | varchar(100) | YES |  |  |
| best_algo_wr | decimal(5,2) | YES |  | 0.00 |
| best_hour_utc | int | YES |  | -1 |
| best_session | varchar(20) | YES |  |  |
| total_signals | int | YES |  | 0 |
| total_wins | int | YES |  | 0 |
| win_rate | decimal(5,2) | YES | MUL | 0.00 |
| avg_pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| pattern_json | text | YES |  |  |
| updated_at | datetime | NO |  |  |

### `pf_pair_patterns`  (51 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(15) | NO |  | CRYPTO |
| pattern_name | varchar(50) | NO |  |  |
| occurrences | int | YES |  | 0 |
| win_rate | decimal(5,2) | YES | MUL | 0.00 |
| avg_return_pct | decimal(8,4) | YES |  | 0.0000 |
| avg_duration_hours | decimal(8,2) | YES |  | 0.00 |
| last_triggered | datetime | YES |  |  |
| updated_at | datetime | NO |  |  |

### `portfolio_comparisons`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| comparison_name | varchar(200) | NO |  |  |
| scenarios_json | text | YES |  |  |
| best_scenario | varchar(200) | NO |  |  |
| worst_scenario | varchar(200) | NO |  |  |
| created_at | datetime | NO |  |  |

### `portfolio_daily_equity`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL |  |
| snapshot_date | date | NO | MUL |  |
| equity_value | decimal(12,2) | NO |  | 0.00 |
| cash_balance | decimal(12,2) | NO |  | 0.00 |
| open_positions | int | NO |  | 0 |
| daily_return_pct | decimal(10,4) | NO |  | 0.0000 |
| cumulative_return_pct | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| spy_close | decimal(10,2) | NO |  | 0.00 |

### `portfolio_positions`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL |  |
| ticker | varchar(10) | NO | MUL |  |
| company_name | varchar(200) | NO |  |  |
| algorithm_name | varchar(100) | NO |  |  |
| entry_date | date | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| shares | decimal(12,4) | NO |  | 0.0000 |
| allocated_amount | decimal(12,2) | NO |  | 0.00 |
| current_price | decimal(12,4) | NO |  | 0.0000 |
| unrealized_pnl | decimal(12,2) | NO |  | 0.00 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| realized_pnl | decimal(12,2) | NO |  | 0.00 |
| exit_reason | varchar(50) | NO |  |  |
| status | varchar(20) | NO | MUL | open |

### `portfolio_resets`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | varchar(50) | NO | MUL |  |
| reset_num | int | NO |  |  |
| equity_at_reset | decimal(15,2) | NO |  |  |
| pnl_usd | decimal(12,2) | NO |  |  |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| max_drawdown_pct | decimal(8,4) | NO |  | 0.0000 |
| reason | text | YES |  |  |
| reset_at | datetime | NO |  | CURRENT_TIMESTAMP |

### `portfolio_snapshots`  (26 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | varchar(50) | NO | MUL |  |
| portfolio_name | varchar(100) | NO |  |  |
| methodology | varchar(50) | NO |  |  |
| category | varchar(20) | NO |  | signal |
| status | varchar(20) | NO |  | ACTIVE |
| equity | decimal(15,2) | NO |  |  |
| initial_capital | decimal(15,2) | NO |  |  |
| pnl_pct | decimal(8,4) | NO |  | 0.0000 |
| pnl_usd | decimal(12,2) | NO |  | 0.00 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| total_trades | int | NO |  | 0 |
| open_positions | int | NO |  | 0 |
| max_drawdown_pct | decimal(8,4) | NO |  | 0.0000 |
| sharpe_ratio | decimal(8,4) | NO |  | 0.0000 |
| profit_factor | decimal(8,4) | NO |  | 0.0000 |
| total_commission | decimal(10,2) | NO |  | 0.00 |
| resets | int | NO |  | 0 |
| snapshot_at | datetime | NO | MUL | CURRENT_TIMESTAMP |

### `portfolio_strategy_stats`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| strategy | varchar(100) | NO | UNI |  |
| total_picks | int | NO |  | 0 |
| wins | int | NO |  | 0 |
| losses | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| total_pnl_usd | decimal(12,2) | NO |  | 0.00 |
| avg_pnl_pct | decimal(8,4) | NO |  | 0.0000 |
| best_pnl_pct | decimal(8,4) | NO |  | 0.0000 |
| worst_pnl_pct | decimal(8,4) | NO |  | 0.0000 |
| avg_hold_hours | decimal(8,2) | NO |  | 0.00 |
| last_updated | datetime | NO |  | CURRENT_TIMESTAMP |

### `portfolios`  (39 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| description | text | YES |  |  |
| strategy_type | varchar(50) | NO |  | single_algo |
| algorithm_filter | varchar(500) | NO |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| commission_buy | decimal(6,2) | NO |  | 10.00 |
| commission_sell | decimal(6,2) | NO |  | 10.00 |
| stop_loss_pct | decimal(5,2) | NO |  | 5.00 |
| take_profit_pct | decimal(5,2) | NO |  | 10.00 |
| max_hold_days | int | NO |  | 7 |
| slippage_pct | decimal(5,4) | NO |  | 0.0050 |
| created_at | datetime | NO |  |  |

### `ps_history`  (684 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| predictability_score | float | YES |  | 0 |
| hurst_exponent | float | YES |  | 0.5 |
| computed_at | datetime | YES |  |  |

### `ps_scores`  (36 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | UNI |  |
| asset_class | varchar(20) | NO |  | CRYPTO |
| hurst_exponent | float | YES |  | 0.5 |
| hurst_regime | varchar(20) | YES |  | RANDOM |
| autocorrelation_1 | float | YES |  | 0 |
| autocorrelation_5 | float | YES |  | 0 |
| volatility_stability | float | YES |  | 0 |
| signal_noise_ratio | float | YES |  | 0 |
| engine_agreement | float | YES |  | 0 |
| engines_bullish | int | YES |  | 0 |
| engines_bearish | int | YES |  | 0 |
| engines_total | int | YES |  | 0 |
| historical_tp_rate | float | YES |  | 0 |
| historical_signals | int | YES |  | 0 |
| predictability_score | float | YES |  | 0 |
| predictability_grade | varchar(5) | YES |  | F |
| best_strategy | varchar(30) | YES |  | UNKNOWN |
| computed_at | datetime | YES |  |  |

### `rapid_signals`  (35425 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| signal_id | int | NO | PRI |  |
| strategy_name | varchar(100) | NO | MUL |  |
| pair | varchar(20) | NO |  |  |
| signal_type | varchar(10) | NO |  |  |
| strength | decimal(5,2) | NO |  |  |
| entry_price | decimal(20,8) | YES |  |  |
| take_profit | decimal(20,8) | YES |  |  |
| stop_loss | decimal(20,8) | YES |  |  |
| created_at | timestamp | YES | MUL | CURRENT_TIMESTAMP |
| status | varchar(20) | YES | MUL | open |
| outcome | varchar(20) | YES |  |  |
| closed_at | timestamp | YES |  |  |
| pnl | decimal(10,2) | YES |  |  |

### `report_cache`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| cache_key | varchar(50) | NO | PRI |  |
| cache_data | longtext | YES |  |  |
| updated_at | datetime | YES |  |  |

### `saved_portfolios`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_name | varchar(200) | NO |  |  |
| portfolio_key | varchar(64) | NO | MUL |  |
| horizon | varchar(20) | NO |  | swing |
| initial_capital | decimal(12,2) | NO |  | 1000.00 |
| current_equity | decimal(12,2) | NO |  | 0.00 |
| take_profit_pct | decimal(5,2) | NO |  | 10.00 |
| stop_loss_pct | decimal(5,2) | NO |  | 5.00 |
| max_hold_days | int | NO |  | 30 |
| status | varchar(20) | NO | MUL | active |
| ip_address | varchar(45) | NO | MUL |  |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |

### `simulation_grid`  (6000 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| batch_id | int | YES | MUL | 0 |
| direction | varchar(5) | YES | MUL | LONG |
| algorithm | varchar(80) | YES | MUL |  |
| algo_combo | varchar(255) | YES |  |  |
| tp | decimal(6,2) | YES |  |  |
| sl | decimal(6,2) | YES |  |  |
| hold_days | int | YES |  |  |
| commission | decimal(6,2) | YES |  |  |
| regime | varchar(20) | YES |  | all |
| total_trades | int | YES |  | 0 |
| winning_trades | int | YES |  | 0 |
| win_rate | decimal(6,2) | YES |  | 0.00 |
| total_return_pct | decimal(10,4) | YES | MUL | 0.0000 |
| final_value | decimal(12,2) | YES |  | 10000.00 |
| max_drawdown_pct | decimal(8,4) | YES |  | 0.0000 |
| sharpe_ratio | decimal(8,4) | YES |  | 0.0000 |
| profit_factor | decimal(8,4) | YES |  | 0.0000 |
| total_pnl | decimal(12,2) | YES |  | 0.00 |
| total_commissions | decimal(10,2) | YES |  | 0.00 |
| created_at | datetime | YES |  |  |

### `simulation_meta`  (3 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| meta_key | varchar(50) | NO | PRI |  |
| meta_value | text | YES |  |  |
| updated_at | datetime | YES |  |  |

### `social_influencers`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| platform | varchar(20) | NO | MUL |  |
| username | varchar(100) | NO |  |  |
| follower_count | int | YES |  |  |
| influence_score | decimal(5,2) | YES |  |  |
| category | varchar(50) | YES |  |  |
| last_updated | timestamp | YES |  | CURRENT_TIMESTAMP |

### `social_sentiment`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| asset_class | varchar(20) | NO |  |  |
| symbol | varchar(20) | NO | MUL |  |
| platform | varchar(20) | NO |  |  |
| mention_count_24h | int | YES |  | 0 |
| sentiment_score | decimal(3,2) | YES |  |  |
| engagement_score | int | YES |  | 0 |
| influencer_mentions | int | YES |  | 0 |
| viral_coefficient | decimal(5,2) | YES |  |  |
| calculated_at | timestamp | YES | MUL | CURRENT_TIMESTAMP |

### `sp_batches`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| batch_id | varchar(30) | NO | UNI |  |
| generated_at | datetime | NO |  |  |
| regime | varchar(20) | NO |  | NEUTRAL |
| fear_greed | int | YES |  |  |
| btc_price | decimal(14,2) | YES |  |  |
| total_scored | int | YES |  | 0 |
| picks_count | int | YES |  | 0 |
| crypto_count | int | YES |  | 0 |
| non_crypto_count | int | YES |  | 0 |
| resolved | tinyint(1) | YES |  | 0 |
| resolved_at | datetime | YES |  |  |
| final_wr | decimal(5,1) | YES |  |  |
| final_avg_pnl | decimal(8,3) | YES |  |  |
| final_pf | decimal(8,2) | YES |  |  |
| final_tp_hits | int | YES |  |  |
| final_sl_hits | int | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `sp_daily_performance`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| snapshot_date | date | NO | UNI |  |
| batches_count | int | YES |  | 0 |
| picks_count | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,1) | YES |  |  |
| avg_pnl | decimal(8,3) | YES |  |  |
| total_pnl | decimal(10,3) | YES |  |  |
| profit_factor | decimal(8,2) | YES |  |  |
| best_pick | varchar(30) | YES |  |  |
| best_pnl | decimal(8,3) | YES |  |  |
| worst_pick | varchar(30) | YES |  |  |
| worst_pnl | decimal(8,3) | YES |  |  |
| regime | varchar(20) | YES |  |  |
| crypto_wr | decimal(5,1) | YES |  |  |
| equity_wr | decimal(5,1) | YES |  |  |
| forex_wr | decimal(5,1) | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `sp_picks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| batch_id | varchar(30) | NO | MUL |  |
| symbol | varchar(30) | NO | MUL |  |
| asset_class | varchar(20) | NO | MUL | CRYPTO |
| direction | varchar(10) | NO |  | LONG |
| tier | varchar(15) | YES |  | SWING |
| strategy | varchar(100) | YES | MUL |  |
| source_system | varchar(50) | YES |  |  |
| smart_score | decimal(5,1) | YES |  |  |
| validated_score | decimal(5,1) | YES |  |  |
| ml_composite | decimal(6,4) | YES |  |  |
| entry_price | decimal(14,6) | YES |  |  |
| tp_price | decimal(14,6) | YES |  |  |
| sl_price | decimal(14,6) | YES |  |  |
| confidence | decimal(4,3) | YES |  |  |
| fwd_wr | decimal(5,1) | YES |  |  |
| fwd_trades | int | YES |  |  |
| regime | varchar(20) | YES |  |  |
| rr_ratio | decimal(5,2) | YES |  |  |
| pnl_at_snapshot | decimal(8,3) | YES |  |  |
| final_pnl | decimal(8,3) | YES |  |  |
| final_status | varchar(20) | YES |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |

### `ss_baselines`  (82 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(15) | NO |  | CRYPTO |
| avg_volume_24h | decimal(20,4) | YES |  | 0.0000 |
| avg_price_change_1h | decimal(8,4) | YES |  | 0.0000 |
| avg_price_change_4h | decimal(8,4) | YES |  | 0.0000 |
| avg_price_change_24h | decimal(8,4) | YES |  | 0.0000 |
| volatility_1h | decimal(8,4) | YES |  | 0.0000 |
| volatility_24h | decimal(8,4) | YES |  | 0.0000 |
| scan_count | int | YES |  | 0 |
| updated_at | datetime | NO |  |  |

### `ss_spikes`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| pair | varchar(30) | NO | MUL |  |
| asset_class | varchar(15) | NO | MUL | CRYPTO |
| spike_type | varchar(30) | NO |  | VOLUME_SPIKE |
| severity | varchar(10) | NO | MUL | WATCH |
| volume_zscore | decimal(8,4) | YES |  | 0.0000 |
| price_change_pct | decimal(8,4) | YES |  | 0.0000 |
| volume_ratio | decimal(8,4) | YES |  | 0.0000 |
| current_price | decimal(20,10) | YES |  | 0.0000000000 |
| entry_price | decimal(20,10) | YES |  | 0.0000000000 |
| target_tp_pct | decimal(6,2) | YES |  | 0.00 |
| target_sl_pct | decimal(6,2) | YES |  | 0.00 |
| max_hold_hours | int | YES |  | 8 |
| signal_type | varchar(10) | YES |  | BUY |
| rationale | text | YES |  |  |
| fingerprint_behavior | varchar(30) | YES |  |  |
| status | varchar(20) | YES | MUL | active |
| exit_price | decimal(20,10) | YES |  | 0.0000000000 |
| pnl_pct | decimal(8,4) | YES |  | 0.0000 |
| exit_reason | varchar(30) | YES |  |  |
| created_at | datetime | NO | MUL |  |
| resolved_at | datetime | YES |  |  |

### `stock_analyst_recs`  (4 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| period | varchar(10) | NO |  | 0m |
| strong_buy | int | NO |  | 0 |
| buy | int | NO |  | 0 |
| hold_count | int | NO |  | 0 |
| sell | int | NO |  | 0 |
| strong_sell | int | NO |  | 0 |
| updated_at | datetime | NO |  |  |

### `stock_assets`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| symbol | varchar(20) | NO | UNI |  |
| name | varchar(200) | NO |  |  |
| exchange | varchar(20) | YES |  |  |
| sector | varchar(50) | YES | MUL |  |
| industry | varchar(100) | YES |  |  |
| market_cap_category | enum('mega','large','mid','small','micro','nano') | YES |  | mid |
| is_penny | tinyint(1) | YES | MUL | 0 |
| is_etf | tinyint(1) | YES |  | 0 |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `stock_dividends`  (831 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| ex_date | date | NO | MUL |  |
| payment_date | date | YES |  |  |
| amount | decimal(10,6) | NO |  | 0.000000 |
| frequency | varchar(20) | NO |  | quarterly |
| source | varchar(20) | NO |  | yahoo_v8 |
| updated_at | datetime | NO |  |  |

### `stock_earnings`  (381 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| quarter_end | date | NO |  |  |
| earnings_date | date | YES | MUL |  |
| eps_actual | decimal(10,4) | YES |  |  |
| eps_estimate | decimal(10,4) | YES |  |  |
| eps_surprise | decimal(10,4) | YES |  |  |
| surprise_pct | decimal(10,4) | YES |  |  |
| revenue_actual | bigint | YES |  |  |
| revenue_estimate | bigint | YES |  |  |
| source | varchar(20) | NO |  | yahoo_v10 |
| updated_at | datetime | NO |  |  |

### `stock_fundamentals`  (119 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | UNI |  |
| trailing_eps | decimal(10,4) | YES |  |  |
| forward_eps | decimal(10,4) | YES |  |  |
| trailing_pe | decimal(10,4) | YES |  |  |
| forward_pe | decimal(10,4) | YES |  |  |
| peg_ratio | decimal(10,4) | YES |  |  |
| dividend_rate | decimal(10,4) | YES |  |  |
| dividend_yield | decimal(10,6) | YES |  |  |
| trailing_annual_div_rate | decimal(10,4) | YES |  |  |
| trailing_annual_div_yield | decimal(10,6) | YES |  |  |
| five_yr_avg_div_yield | decimal(10,6) | YES |  |  |
| payout_ratio | decimal(10,4) | YES |  |  |
| ex_dividend_date | date | YES |  |  |
| next_earnings_date | date | YES |  |  |
| price_to_book | decimal(10,4) | YES |  |  |
| enterprise_to_revenue | decimal(10,4) | YES |  |  |
| total_revenue | bigint | YES |  |  |
| ebitda | bigint | YES |  |  |
| total_debt | bigint | YES |  |  |
| current_ratio | decimal(10,4) | YES |  |  |
| roe | decimal(10,4) | YES |  |  |
| gross_margins | decimal(10,4) | YES |  |  |
| operating_margins | decimal(10,4) | YES |  |  |
| recommendation_key | varchar(20) | YES |  |  |
| target_mean_price | decimal(10,4) | YES |  |  |
| source | varchar(20) | NO |  | yahoo_v10 |
| updated_at | datetime | NO |  |  |

### `stock_ohlcv`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| symbol | varchar(20) | NO | MUL |  |
| timeframe | varchar(10) | NO |  |  |
| timestamp | bigint | NO |  |  |
| open | decimal(12,4) | NO |  |  |
| high | decimal(12,4) | NO |  |  |
| low | decimal(12,4) | NO |  |  |
| close | decimal(12,4) | NO |  |  |
| volume | bigint | NO |  |  |
| source | varchar(50) | YES |  | yahoo |

### `stock_picks`  (7239 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| ticker | varchar(10) | NO | MUL |  |
| algorithm_id | int | NO |  | 0 |
| algorithm_name | varchar(100) | NO | MUL |  |
| pick_date | date | NO | MUL |  |
| pick_time | datetime | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| simulated_entry_price | decimal(12,4) | NO |  | 0.0000 |
| score | int | NO |  | 0 |
| rating | varchar(20) | NO |  |  |
| risk_level | varchar(20) | NO |  | Medium |
| timeframe | varchar(20) | NO |  |  |
| stop_loss_price | decimal(12,4) | NO |  | 0.0000 |
| pick_hash | varchar(64) | NO | MUL |  |
| indicators_json | text | YES |  |  |
| verified | tinyint | NO |  | 0 |

### `stock_signals`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| signal_id | varchar(50) | NO | UNI |  |
| symbol | varchar(20) | NO | MUL |  |
| signal_type | enum('buy','sell','strong_buy','strong_sell') | NO |  |  |
| entry_price | decimal(12,4) | NO |  |  |
| target_price | decimal(12,4) | YES |  |  |
| stop_loss | decimal(12,4) | YES |  |  |
| position_size | decimal(8,4) | YES |  |  |
| risk_reward | decimal(5,2) | YES |  |  |
| confidence | decimal(5,2) | YES |  |  |
| strategy | varchar(50) | YES |  |  |
| catalyst | text | YES |  |  |
| status | enum('active','closed','stopped') | YES | MUL | active |
| pnl_percent | decimal(8,4) | YES |  |  |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `stocks`  (153 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| ticker | varchar(10) | NO | PRI |  |
| company_name | varchar(200) | NO |  |  |
| sector | varchar(100) | NO |  |  |
| market_cap | varchar(20) | NO |  |  |

### `strategy_health`  (56 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_system | varchar(100) | NO | MUL |  |
| strategy | varchar(200) | NO |  |  |
| asset_class | varchar(20) | YES |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,4) | YES |  | 0.0000 |
| avg_win_pct | decimal(10,4) | YES |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | YES |  | 0.0000 |
| expectancy | decimal(10,4) | YES |  | 0.0000 |
| fees_adj_expect | decimal(10,4) | YES |  | 0.0000 |
| profit_factor | decimal(10,4) | YES |  |  |
| rolling_30d_wr | decimal(5,4) | YES |  |  |
| tier | enum('CORE','INCUBATOR','BANNED') | YES | MUL | INCUBATOR |
| tier_changed_at | datetime | YES |  |  |
| tier_reason | text | YES |  |  |
| wf_passed | tinyint(1) | YES |  |  |
| wf_last_checked | datetime | YES |  |  |
| last_evaluated | datetime | YES |  |  |

### `strategy_health_audit`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_system | varchar(100) | YES |  |  |
| strategy | varchar(200) | YES | MUL |  |
| old_tier | enum('CORE','INCUBATOR','BANNED') | YES |  |  |
| new_tier | enum('CORE','INCUBATOR','BANNED') | YES |  |  |
| reason | text | YES |  |  |
| metrics_snapshot | json | YES |  |  |
| created_at | datetime | YES | MUL | CURRENT_TIMESTAMP |

### `strategy_registry`  (1195 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| strategy_id | varchar(100) | NO | MUL |  |
| strategy_name | varchar(200) | YES |  |  |
| system_name | varchar(100) | NO | MUL |  |
| section_name | varchar(200) | YES |  |  |
| module_file | varchar(300) | YES |  |  |
| asset_class | varchar(20) | YES | MUL | CRYPTO |
| strategy_type | varchar(50) | YES |  |  |
| win_rate | varchar(30) | YES |  |  |
| sharpe | varchar(30) | YES |  |  |
| source_ref | varchar(200) | YES |  |  |
| is_banned | tinyint(1) | NO | MUL | 0 |
| is_active | tinyint(1) | NO |  | 1 |
| notes | text | YES |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  |  |

### `strategy_status_history`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | bigint | NO | PRI |  |
| strategy_id | varchar(128) | NO | MUL |  |
| from_status | varchar(32) | YES |  |  |
| to_status | varchar(32) | NO |  |  |
| reason | text | YES |  |  |
| changed_at | datetime | NO |  |  |

### `strategy_symbol_coverage`  (34 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| strategy_id | varchar(128) | NO | PRI |  |
| symbol | varchar(64) | NO | PRI |  |
| asset_class | varchar(32) | NO |  |  |
| tested_backtest | tinyint(1) | YES |  | 0 |
| tested_walkforward | tinyint(1) | YES |  | 0 |
| tested_forward | tinyint(1) | YES |  | 0 |
| last_result_at | datetime | YES |  |  |

### `strategy_test_runs`  (51 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| run_id | bigint | NO | PRI |  |
| strategy_id | varchar(128) | NO | MUL |  |
| test_layer | varchar(32) | NO | MUL |  |
| symbol | varchar(64) | YES |  |  |
| asset_class | varchar(32) | YES |  |  |
| period_start | datetime | YES |  |  |
| period_end | datetime | YES |  |  |
| trades | int | YES |  | 0 |
| win_rate | decimal(8,4) | YES |  |  |
| profit_factor | decimal(10,4) | YES |  |  |
| sharpe | decimal(10,4) | YES |  |  |
| max_drawdown | decimal(10,4) | YES |  |  |
| p_value | decimal(12,8) | YES |  |  |
| q_value_bh | decimal(12,8) | YES |  |  |
| p_value_bonf | decimal(12,8) | YES |  |  |
| pass_flag | tinyint(1) | YES |  | 0 |
| metadata_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `strategy_whatif_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| whatif_id | bigint | NO | PRI |  |
| strategy_id | varchar(128) | NO | MUL |  |
| variant_name | varchar(128) | NO |  |  |
| variant_type | varchar(32) | NO |  |  |
| params_json | text | NO |  |  |
| baseline_win_rate | decimal(8,4) | YES |  |  |
| baseline_pf | decimal(10,4) | YES |  |  |
| baseline_trades | int | YES |  |  |
| variant_win_rate | decimal(8,4) | YES |  |  |
| variant_pf | decimal(10,4) | YES |  |  |
| variant_trades | int | YES |  |  |
| delta_win_rate | decimal(8,4) | YES |  |  |
| delta_pf | decimal(10,4) | YES |  |  |
| delta_trades | int | YES |  |  |
| accepted | tinyint(1) | YES |  | 0 |
| created_at | datetime | NO |  |  |

### `super_strategy_candidates`  (26 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| strategy_id | varchar(128) | NO | PRI |  |
| symbols_passed | int | YES |  | 0 |
| asset_classes_passed | int | YES |  | 0 |
| regimes_passed | int | YES |  | 0 |
| concentration_ratio | decimal(10,4) | YES |  |  |
| fisher_p | decimal(12,8) | YES |  |  |
| status | varchar(32) | NO |  |  |
| notes | text | YES |  |  |
| updated_at | datetime | NO |  |  |

### `test_portfolio_positions`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| portfolio_name | varchar(64) | NO |  |  |
| position_id | bigint | NO | PRI |  |
| strategy_id | varchar(128) | NO | MUL |  |
| symbol | varchar(64) | NO |  |  |
| direction | varchar(8) | NO |  |  |
| entry_price | decimal(18,8) | NO |  |  |
| take_profit | decimal(18,8) | NO |  |  |
| stop_loss | decimal(18,8) | NO |  |  |
| status | varchar(16) | NO | MUL |  |
| opened_at | datetime | NO |  |  |
| closed_at | datetime | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| metadata_json | text | YES |  |  |

### `tracked_portfolio_picks`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL |  |
| ticker | varchar(20) | NO | MUL |  |
| company_name | varchar(200) | YES |  |  |
| algorithm | varchar(100) | YES |  |  |
| entry_price | decimal(12,4) | NO |  |  |
| current_price | decimal(12,4) | YES |  |  |
| take_profit | decimal(12,4) | NO |  |  |
| stop_loss | decimal(12,4) | NO |  |  |
| tp_pct | decimal(6,2) | NO |  | 10.00 |
| sl_pct | decimal(6,2) | NO |  | 5.00 |
| hold_days | int | NO |  | 7 |
| status | varchar(20) | NO | MUL | active |
| current_return_pct | decimal(10,4) | YES |  | 0.0000 |
| peak_price | decimal(12,4) | YES |  |  |
| trough_price | decimal(12,4) | YES |  |  |
| exit_price | decimal(12,4) | YES |  |  |
| exit_date | date | YES |  |  |
| exit_reason | varchar(50) | YES |  |  |
| entry_date | date | NO |  |  |
| days_held | int | YES |  | 0 |
| last_price_date | date | YES |  |  |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |

### `tracked_portfolios`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| name | varchar(200) | NO |  |  |
| strategy_type | varchar(50) | NO |  | custom |
| category | varchar(20) | NO |  | swing |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| status | varchar(20) | NO |  | active |
| total_picks | int | NO |  | 0 |
| tp_hits | int | NO |  | 0 |
| sl_hits | int | NO |  | 0 |
| active_picks | int | NO |  | 0 |
| total_return_pct | decimal(10,4) | YES |  | 0.0000 |
| best_pick | varchar(20) | YES |  |  |
| worst_pick | varchar(20) | YES |  |  |
| last_refreshed | datetime | YES |  |  |
| created_at | datetime | NO |  |  |
| updated_at | datetime | NO |  |  |

### `trading_picks`  (69024 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | varchar(100) | NO | PRI |  |
| symbol | varchar(20) | YES |  |  |
| direction | varchar(10) | YES |  |  |
| strategy | varchar(100) | YES |  |  |
| entry_price | decimal(20,8) | YES |  |  |
| take_profit | decimal(20,8) | YES |  |  |
| stop_loss | decimal(20,8) | YES |  |  |
| confidence | decimal(5,4) | YES |  |  |
| elite_score | int | YES |  |  |
| trust_score | int | YES |  |  |
| category | varchar(20) | YES |  |  |
| source_system | varchar(50) | YES |  |  |
| status | varchar(20) | YES |  | ACTIVE |
| pnl_pct | decimal(10,4) | YES |  |  |
| exit_price | decimal(20,8) | YES |  |  |
| created_at | datetime | YES |  |  |
| closed_at | datetime | YES |  |  |
| exit_reason | varchar(30) | YES |  |  |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### `ua_engine_stats`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(50) | NO | MUL |  |
| asset_class | varchar(20) | YES |  | ALL |
| total_predictions | int | YES |  | 0 |
| resolved | int | YES |  | 0 |
| tp_hits | int | YES |  | 0 |
| sl_hits | int | YES |  | 0 |
| expired | int | YES |  | 0 |
| win_rate | float | YES |  | 0 |
| avg_pnl | float | YES |  | 0 |
| total_pnl | float | YES |  | 0 |
| best_trade_pnl | float | YES |  | 0 |
| worst_trade_pnl | float | YES |  | 0 |
| avg_hold_hours | float | YES |  | 0 |
| sharpe_ratio | float | YES |  | 0 |
| profit_factor | float | YES |  | 0 |
| computed_at | datetime | YES |  |  |

### `ua_predictions`  (355 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| engine_name | varchar(50) | NO | MUL |  |
| engine_signal_id | varchar(50) | YES |  |  |
| asset_class | varchar(20) | NO |  | CRYPTO |
| pair | varchar(30) | NO | MUL |  |
| direction | varchar(10) | NO |  |  |
| confidence | float | YES |  | 0 |
| entry_price | float | YES |  | 0 |
| tp_price | float | YES |  | 0 |
| sl_price | float | YES |  | 0 |
| tp_pct | float | YES |  | 0 |
| sl_pct | float | YES |  | 0 |
| predictability_score | float | YES |  | 0 |
| signal_time | datetime | YES |  |  |
| expires_at | datetime | YES |  |  |
| status | varchar(20) | YES | MUL | ACTIVE |
| exit_price | float | YES |  | 0 |
| pnl_pct | float | YES |  | 0 |
| exit_reason | varchar(30) | YES |  |  |
| resolved_at | datetime | YES |  |  |
| hold_hours | float | YES |  | 0 |
| collected_at | datetime | YES |  |  |

### `walk_forward_results`  (0 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_table | varchar(30) | NO | MUL | stock_picks |
| algorithm_name | varchar(100) | NO | MUL |  |
| strategy_name | varchar(100) | NO | MUL |  |
| fold_num | int | NO |  | 0 |
| total_folds | int | NO |  | 0 |
| train_start | date | NO |  |  |
| train_end | date | NO |  |  |
| test_start | date | NO |  |  |
| test_end | date | NO |  |  |
| train_picks | int | NO |  | 0 |
| test_picks | int | NO |  | 0 |
| is_best_tp | decimal(6,2) | NO |  | 0.00 |
| is_best_sl | decimal(6,2) | NO |  | 0.00 |
| is_best_hold | int | NO |  | 0 |
| is_win_rate | decimal(5,2) | NO |  | 0.00 |
| is_avg_return | decimal(10,4) | NO |  | 0.0000 |
| is_profit_factor | decimal(8,4) | NO |  | 0.0000 |
| oos_win_rate | decimal(5,2) | NO |  | 0.00 |
| oos_avg_return | decimal(10,4) | NO |  | 0.0000 |
| oos_profit_factor | decimal(8,4) | NO |  | 0.0000 |
| oos_trades | int | NO |  | 0 |
| wf_efficiency | decimal(8,4) | NO |  | 0.0000 |
| regime_at_test | varchar(20) | NO |  |  |
| created_at | datetime | NO | MUL |  |

### `walk_forward_summary`  (10 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| source_table | varchar(30) | NO | MUL | stock_picks |
| algorithm_name | varchar(100) | NO |  |  |
| strategy_name | varchar(100) | NO |  |  |
| total_folds | int | NO |  | 0 |
| avg_wf_efficiency | decimal(8,4) | NO |  | 0.0000 |
| avg_oos_win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_oos_return | decimal(10,4) | NO |  | 0.0000 |
| avg_is_win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_is_return | decimal(10,4) | NO |  | 0.0000 |
| best_robust_tp | decimal(6,2) | NO |  | 0.00 |
| best_robust_sl | decimal(6,2) | NO |  | 0.00 |
| best_robust_hold | int | NO |  | 0 |
| overfitting_flag | tinyint | NO |  | 0 |
| naive_is_return | decimal(10,4) | NO |  | 0.0000 |
| updated_at | datetime | NO |  |  |

### `whatif_scenarios`  (120 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| scenario_name | varchar(200) | NO |  |  |
| query_text | text | YES |  |  |
| params_json | text | YES |  |  |
| results_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

## `ejaguiar1_backtests`

- 6 tables

### `at_incubator_backtest_results`  (1285 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| perm_id | varchar(20) | NO | MUL |  |
| archetype | varchar(80) | NO |  |  |
| symbol | varchar(30) | NO | MUL |  |
| params_json | json | NO |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(6,4) | YES |  | 0.0000 |
| sharpe | decimal(10,4) | YES | MUL | 0.0000 |
| sortino | decimal(10,4) | YES |  | 0.0000 |
| max_drawdown | decimal(10,6) | YES |  | 0.000000 |
| profit_factor | decimal(10,4) | YES |  | 0.0000 |
| total_return | decimal(10,6) | YES |  | 0.000000 |
| avg_trade_pnl | decimal(10,6) | YES |  | 0.000000 |
| avg_hold_bars | decimal(6,1) | YES |  | 0.0 |
| slippage_pct | decimal(6,4) | YES |  | 0.0000 |
| commission_pct | decimal(6,4) | YES |  | 0.0000 |
| backtest_type | enum('fast','full') | YES |  | fast |
| created_at | datetime | NO |  |  |

### `at_large_backtest_results`  (1105 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| perm_id | varchar(20) | NO | MUL |  |
| archetype | varchar(80) | NO |  |  |
| symbol | varchar(30) | NO |  |  |
| params_json | json | NO |  |  |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(6,4) | YES |  | 0.0000 |
| sharpe | decimal(10,4) | YES | MUL | 0.0000 |
| sortino | decimal(10,4) | YES |  | 0.0000 |
| max_drawdown | decimal(10,6) | YES |  | 0.000000 |
| profit_factor | decimal(10,4) | YES |  | 0.0000 |
| total_return | decimal(10,6) | YES |  | 0.000000 |
| avg_trade_pnl | decimal(10,6) | YES |  | 0.000000 |
| avg_hold_bars | decimal(6,1) | YES |  | 0.0 |
| slippage_pct | decimal(6,4) | YES |  | 0.0000 |
| commission_pct | decimal(6,4) | YES |  | 0.0000 |
| equity_curve_json | json | YES |  |  |
| trade_log_json | json | YES |  |  |
| created_at | datetime | NO |  |  |

### `backtest_results`  (2 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| portfolio_id | int | NO | MUL | 0 |
| run_name | varchar(200) | NO |  |  |
| algorithm_filter | varchar(500) | NO |  |  |
| strategy_type | varchar(50) | NO | MUL |  |
| start_date | date | YES |  |  |
| end_date | date | YES |  |  |
| initial_capital | decimal(12,2) | NO |  | 10000.00 |
| final_value | decimal(12,2) | NO |  | 0.00 |
| total_return_pct | decimal(10,4) | NO |  | 0.0000 |
| total_trades | int | NO |  | 0 |
| winning_trades | int | NO |  | 0 |
| losing_trades | int | NO |  | 0 |
| win_rate | decimal(5,2) | NO |  | 0.00 |
| avg_win_pct | decimal(10,4) | NO |  | 0.0000 |
| avg_loss_pct | decimal(10,4) | NO |  | 0.0000 |
| max_drawdown_pct | decimal(10,4) | NO |  | 0.0000 |
| total_commissions | decimal(12,2) | NO |  | 0.00 |
| sharpe_ratio | decimal(10,4) | NO |  | 0.0000 |
| sortino_ratio | decimal(10,4) | NO |  | 0.0000 |
| profit_factor | decimal(10,4) | NO |  | 0.0000 |
| expectancy | decimal(10,4) | NO |  | 0.0000 |
| params_json | text | YES |  |  |
| created_at | datetime | NO |  |  |

### `backtest_trades`  (50 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_id | int | NO | MUL | 0 |
| ticker | varchar(10) | NO | MUL |  |
| algorithm_name | varchar(100) | NO |  |  |
| entry_date | date | NO |  |  |
| entry_price | decimal(12,4) | NO |  | 0.0000 |
| exit_date | date | YES |  |  |
| exit_price | decimal(12,4) | NO |  | 0.0000 |
| shares | int | NO |  | 0 |
| gross_profit | decimal(12,2) | NO |  | 0.00 |
| commission_paid | decimal(8,2) | NO |  | 0.00 |
| net_profit | decimal(12,2) | NO |  | 0.00 |
| return_pct | decimal(10,4) | NO |  | 0.0000 |
| exit_reason | varchar(50) | NO |  |  |
| hold_days | int | NO |  | 0 |

### `bt_backtest_runs`  (285 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | char(36) | NO | PRI |  |
| source_db | varchar(200) | NO |  |  |
| source_table | varchar(100) | NO |  |  |
| strategy | varchar(200) | YES | MUL |  |
| symbol | varchar(50) | YES | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| total_trades | int | YES |  | 0 |
| wins | int | YES |  | 0 |
| losses | int | YES |  | 0 |
| win_rate | decimal(5,4) | YES |  |  |
| profit_factor | decimal(10,4) | YES |  |  |
| total_return | decimal(10,4) | YES |  |  |
| sharpe | decimal(10,4) | YES |  |  |
| max_drawdown | decimal(10,4) | YES |  |  |
| imported_at | datetime | NO |  |  |

### `bt_backtest_trades`  (28705218 rows)

| Column | Type | Null | Key | Default |
|---|---|---|---|---|
| id | int | NO | PRI |  |
| backtest_run_id | char(36) | YES | MUL |  |
| source_db | varchar(200) | NO |  |  |
| source_table | varchar(100) | NO |  |  |
| symbol | varchar(50) | NO | MUL |  |
| asset_class | enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') | YES | MUL | UNKNOWN |
| direction | enum('LONG','SHORT') | YES |  |  |
| strategy | varchar(200) | YES | MUL |  |
| entry_price | decimal(18,8) | YES |  |  |
| exit_price | decimal(18,8) | YES |  |  |
| take_profit | decimal(18,8) | YES |  |  |
| stop_loss | decimal(18,8) | YES |  |  |
| entry_time | datetime | YES |  |  |
| exit_time | datetime | YES |  |  |
| pnl_pct | decimal(10,4) | YES |  |  |
| status | varchar(20) | YES | MUL |  |
| confidence | decimal(5,4) | YES |  |  |
| raw_data | json | YES |  |  |
| imported_at | datetime | NO |  |  |
