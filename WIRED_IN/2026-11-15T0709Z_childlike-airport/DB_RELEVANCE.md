# Database relevance for historical picks

Host: mysql.50webs.com. Counts are information_schema estimates except where a live COUNT is noted. No passwords in this file.

## Use these

| Database | Why | Largest relevant tables |
|---|---|---|
| ejaguiar1_stocks | Primary pick ledger. 409 tables, 115 name-matched to picks, signals, trades, or strategies. | at_local_picks ~76.2M (too large for a full scan; timed out on MIN/MAX). trading_picks live COUNT 143,657 from 2026-02-17 to 2026-11-15, 871 strategies. at_raw_picks COUNT 112,530, 2,065 strategies, mostly CRYPTO. at_pick_outcomes COUNT 62,751, 1,098 strategies. at_signal_outcomes COUNT 50,735, 334 strategies. bt_backtest_trades ~27.2M. |
| ejaguiar1_backtests | Cleaner backtest store. 10 tables. | bt_backtest_trades ~34.6M. backtest_trades 50. eagle2_consensus_picks 15. |
| ejaguiar1_backups | Snapshots of the stocks tables, not a second live book. 414 tables. | stocks__bt_backtest_trades ~31.0M. Many dated copies of at_raw_picks and trading_picks. Use only to recover a row the live table no longer has. |

## Skip for this question

| Database | Tables | Pick-like tables |
|---|---|---|
| ejaguiar1_deals | 0 | 0 |
| ejaguiar1_events | 5 | 0 |
| ejaguiar1_favcreators | 59 | 0 |
| ejaguiar1_news | 2 | 0 |
| ejaguiar1_tvmoviestrailers | 15 | 0 |
| ejaguiar1_memecoin | 58 | 16, all small. Largest is science_engine_picks, 588 rows. |
| ejaguiar1_sportsbet | 49 | 4. Largest is lm_sports_daily_picks, 128 rows. |

## Where to query first

1. `ejaguiar1_stocks.trading_picks` for what the site is calling live or recently closed. It is still being written (max created_at 2026-11-15 06:33).
2. `ejaguiar1_stocks.at_pick_outcomes` for class labels. Live mix: CRYPTO 36,890, FOREX 16,033, COMMODITY 5,882, EQUITY 2,272, FUTURES 473, INDEX 314, ETF 181. That is not a balanced research set.
3. `ejaguiar1_stocks.at_signal_outcomes` for resolver closes. Created 2026-03-04 through 2026-11-14. CRYPTO is 44,480 of 50,735.
4. `ejaguiar1_backtests.bt_backtest_trades` for strategy history that never became a live pick. Do not start with the 76M-row `at_local_picks` table.
5. `ejaguiar1_backups` only when a stocks table was overwritten.

Hypothesis status is not in these databases. It is in `reports/hypothesis_registry.json`. The MySQL incident schedule is the `INCIDENT_*` and `ENHANCEMENT_*` tables inside `ejaguiar1_stocks`, rendered to `/audit/incidents.html`.
