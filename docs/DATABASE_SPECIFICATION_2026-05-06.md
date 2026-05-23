# FindTorontoEvents Database Specification

Date: 2026-05-06  
Sources:
- MySQL dumps from `mysql.50webs.com`:
  - `10_123_0_33 (16).sql` ... `(8).sql`
- Runtime usage scan across this repo (`*.php`, `*.py`, workflows)

## 1) Database Catalog

## `ejaguiar1_stocks`
- Primary role: audit + trading pipeline operational store.
- Critical runtime surfaces:
  - `findtorontoevents.ca/audit` generator support (notably `trading_picks` path via `audit_trail/mysql_client.py`)
  - live-monitor stocks APIs (`live-monitor/api/*`)
  - pipeline/workflow writers (`sync_all_picks_to_mysql.py`, audit trail writers)
- Representative table families:
  - `at_*` (audit trail, consensus, raw picks, gate/discord logs)
  - `alpha_*` (alpha engine staging and metadata)
  - `algorithm_*` (algorithm stats/perf)
  - Backtest-heavy tables currently under migration:
    - `bt_backtest_trades`
    - `bt_backtest_runs`
    - `backtest_trades`
    - `backtest_results`
    - `at_large_backtest_results`
    - `at_incubator_backtest_results`

## `ejaguiar1_backtests`
- Primary role: dedicated backtesting archive/store (currently/previously sparse).
- Dump observation: `10_123_0_33 (9).sql` had DB header but no table DDL in sample output.
- Target role (planned/active migration): host the 6 backtest-heavy tables moved from `ejaguiar1_stocks`.

## `ejaguiar1_sportsbet`
- Primary role: sports-betting operational DB for live-monitor sports endpoints.
- Representative tables:
  - `lm_sports_*` (bets, odds, value bets, ml predictions, bankroll)
  - league-specific `lm_nba_*`, `lm_nfl_*`, `lm_nhl_*`, `lm_mlb_*`
  - `lm_arena_*` (strategy/bankroll snapshots)
- Runtime surfaces:
  - `live-monitor/api/sports_*.php`
  - sports dashboards and sports betting page.

## `ejaguiar1_favcreators`
- Primary role: FavCreators app data store (users, preferences, creator tracking, accountability).
- Representative tables:
  - `users`, `creators`, `creator_status_updates`, `streamer_*`
  - `accountability_*` family
  - `user_*` notes/preferences/lists/events
  - local app telemetry (`page_view_log`, `click_log`)
- Runtime surfaces:
  - `favcreators/docs/api/*`

## `ejaguiar1_events`
- Primary role: events ingestion and analytics for events feeds.
- Representative tables:
  - `events_log`, `event_pulls`, `event_sources`, `event_title_index`, `stats_summary`
- Runtime surfaces:
  - events API/config paths (including favcreators events DB config).

## `ejaguiar1_memecoin`
- Primary role: memecoin/pump analytics, picks, scans, and model output.
- Representative tables:
  - `mc_winners`, `pump_forensics_*`, `meme_ml_*`, `psi_*`, `he_*`, `sf_*`, `tv_signals`
- Runtime surfaces:
  - cross-DB reads in live-monitor (`goldmine_tracker`, `pair_fingerprint`)
  - memecoin analytics pipelines.

## `ejaguiar1_tvmoviestrailers`
- Primary role: movies/trailers/watchlist/playlists/user preference subsystem.
- Representative tables:
  - `movies`, `trailers`, `thumbnails`, `streaming_providers`,
  - `content_sources`, `playlist_items`, `shared_playlists`, `user_preferences`, `user_queues`
- Runtime surfaces:
  - `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS*` APIs.

## `ejaguiar1_news`
- Primary role: news articles + source catalog.
- Representative tables:
  - `news_articles`, `news_sources`
- Runtime surfaces:
  - primarily auxiliary data paths.

## `ejaguiar1_deals`
- Dump observation: DB header present, no table DDL found in provided sample.
- Likely role: reserved/deals vertical; currently minimal/empty usage in runtime code paths.

## 2) Table Inventory Snapshot (from dumps)

## `ejaguiar1_stocks` (sampled table names from dump)
- `algorithms`
- `algorithm_performance`
- `algorithm_rolling_perf`
- `alpha_earnings`
- `alpha_factor_scores`
- `alpha_fundamentals`
- `alpha_macro`
- `alpha_picks`
- `at_aggregation_runs`
- `at_audit_events`
- `at_consensus_picks`
- `at_discord_gate_log`
- `at_discord_notifications`
- `at_discord_sent`
- `at_filter_log`
- `at_futures_symbol_edge`
- `at_incubator_backtest_results`
- `at_incubator_strategies`
- `at_large_backtest_results`
- `at_raw_picks`
- `at_signal_outcomes`
- `at_strategy_stats`
- `backtest_results`
- `backtest_trades`
- `bt_backtest_runs`
- `bt_backtest_trades`

## `ejaguiar1_sportsbet` (sampled)
- `lm_arena_bankrolls`
- `lm_arena_bets`
- `lm_arena_snapshots`
- `lm_arena_strategies`
- `lm_nba_*`, `lm_nfl_*`, `lm_nhl_*`, `lm_mlb_*`
- `lm_sports_bankroll`
- `lm_sports_bets`
- `lm_sports_daily_picks`
- `lm_sports_odds`
- `lm_sports_value_bets`
- `lm_sports_ml_predictions`
- `lm_sports_ml_metrics`

## `ejaguiar1_favcreators` (sampled)
- `users`
- `creators`
- `creator_mentions`
- `creator_status_updates`
- `streamer_last_seen`
- `streamer_content`
- `event_subscriptions`
- `user_saved_events`
- `user_notes`
- `user_preferences`
- `user_link_lists`
- `accountability_*` family

## `ejaguiar1_events`
- `events_log`
- `event_pulls`
- `event_sources`
- `event_title_index`
- `stats_summary`

## `ejaguiar1_memecoin` (sampled)
- `mc_winners`
- `mc_daily_snapshots`
- `mc_scan_log`
- `pump_forensics_audit`
- `pump_forensics_scans`
- `meme_ml_models`
- `meme_ml_predictions`
- `psi_results`
- `psi_signals`
- `sf_signals`

## `ejaguiar1_tvmoviestrailers` (sampled)
- `content_sources`
- `movies`
- `thumbnails`
- `trailers`
- `streaming_providers`
- `streaming_provider_history`
- `playlist_items`
- `shared_playlists`
- `user_preferences`
- `user_queues`

## `ejaguiar1_news`
- `news_articles`
- `news_sources`

## `ejaguiar1_backtests`
- No table DDL surfaced in sampled dump header scan.
- Intended dedicated target for backtest-heavy table set.

## `ejaguiar1_deals`
- No table DDL surfaced in sampled dump header scan.

## 3) Ownership and Routing Rules

- Keep `AUDIT_DB_*` pointed at `ejaguiar1_stocks` for non-backtest operational tables (`trading_picks`, `at_raw_picks`, consensus/audit logs).
- Use `BACKTESTS_DB_*` for backtest-heavy tables after cutover.
- Do not globally switch all workloads from `AUDIT_DB_NAME=ejaguiar1_stocks` to `ejaguiar1_backtests`; route by table family.

## 4) Dashboard Impact Summary

- `findtorontoevents.ca/audit`:
  - Primary runtime delivery is static JSON output; migration risk is via generators/writers, not direct browser SQL.
- `findtorontoevents.ca/audit/hyrotrader`:
  - JSON-driven surface; no direct dependency on the 6 moved tables in browser runtime.
- Live monitor dashboards:
  - Mostly unaffected by moving backtest-heavy tables if stocks/sports operational tables remain.

## 5) Migration-Specific Spec (Backtests Split)

Target dedicated DB: `ejaguiar1_backtests`  
Table set:
- `bt_backtest_trades`
- `bt_backtest_runs`
- `backtest_trades`
- `backtest_results`
- `at_large_backtest_results`
- `at_incubator_backtest_results`

Required operational guarantees:
- row-count parity + key-range parity
- schema parity (`SHOW CREATE TABLE`)
- writer path routing to `BACKTESTS_DB_*`
- 72h observation window before source-table decommission

