# DB Tables — what to care about

Two MySQL databases on `mysql.50webs.com` feed `/audit`. `ejaguiar1_stocks` has 323
tables — but only ~10 are on the pick-flow path. The rest are sports betting (`lm_*`),
mutual funds (`mf*`), crypto-pair sandboxes (`cr_*`/`cp_*`/`fx*`), and ML/experiment
staging. Ignore them for a pick-flow audit.

Connection: `audit_trail/mysql_client.py:39-62`. Env vars `AUDIT_DB_HOST`
(`mysql.50webs.com`), `AUDIT_DB_USER`, `AUDIT_DB_PASS`, `AUDIT_DB_NAME`. Backtests DB:
`BACKTESTS_DB_NAME` / `BACKTESTS_DB_USER` / `BACKTESTS_DB_PASS`. MySQL 8.4.7, InnoDB,
event_scheduler ON. Full schema dump: `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md`.

## `ejaguiar1_stocks` — the pick-flow tables

| Table | Rows* | Role | Key columns |
|-------|-------|------|-------------|
| **`at_raw_picks`** | ~146k | **Core ledger.** Every raw pick from every source, full lifecycle incl. close. | `id`, `aggregation_run_id`, `source_system`, `symbol`, `asset_class`, `direction`, `confidence`, `strategy`, `status`, `pnl_pct`, `dedup_hash`, `was_stale/banned/demoted`, `recorded_at`, `closed_at` |
| **`at_filter_log`** | ~818k | Every gate **REJECTION** (no PASS rows). `raw_pick_id` links back. | `raw_pick_id`, `symbol`, `asset_class`, `filter_reason`, `details`, `created_at` |
| **`at_consensus_picks`** | ~12k | Picks that survived multi-source agreement — the published layer. | `aggregation_run_id`, `symbol`, `agreement_count`, `consensus_tier`, `classification`, `status`, `pnl_pct` |
| **`at_signal_outcomes`** | ~120 | Resolved-outcome ledger (entry/exit/pnl). Sparse. | `symbol`, `entry_price`, `exit_price`, `outcome`, `pnl_pct`, `opened_at`, `closed_at` |
| **`at_aggregation_runs`** | ~26k | One row per aggregation cycle; ties raw→consensus. | `run_id`, `started_at`, `raw_picks_count`, `consensus_count`, `regime_data` |
| **`at_filter_log`** ↑ | | (largest pick-flow table) | |
| **`trading_picks`** | ~69k | Dashboard-facing pick store with score fields. | `symbol`, `strategy`, `elite_score`, `trust_score`, `category`, `status`, `pnl_pct` |
| **`alpha_picks`** | ~5k | Alpha-engine equity pick staging (factor-scored). | `ticker`, `strategy`, `score`, `conviction`, `position_size_pct` |
| `at_audit_events` | ~61k | Generic per-pick audit event log. | `event_type`, `pick_id`, `payload` |
| `at_strategy_stats` | 0 | Per-strategy WR/PF rollup (currently EMPTY). | `strategy`, `win_rate`, `avg_pnl_pct` |
| `strategy_registry` | ~1.2k | Strategy catalog / status. | strategy metadata |
| **`at_pick_audit_trail`** | new | Full per-gate PASS/REJECT trace. Opt-in writer. | see `audit_integration/05_pick_audit_trail_schema.sql` |
| **`at_pick_flow_daily`** | new | Nightly per-class funnel rollup. | `flow_date`, `asset_class`, `raw_emitted`, `rejected_total`, `closed_count`, `win_rate`, `profit_factor` |
| **`at_job_log`** | new | Scheduled-event run log. | `job_name`, `run_time`, `status` |

\* row counts approximate, 2026-05.

**The funnel chain:** `at_aggregation_runs` (cycle) → `at_raw_picks` (raw) →
`at_filter_log` (rejections) → `at_consensus_picks` (published) →
`at_signal_outcomes` + `at_raw_picks.status/pnl_pct` (outcome) → `trading_picks`
(dashboard store).

## `ejaguiar1_backtests` — research archive, NOT on the live path

| Table | Rows | Role |
|-------|------|------|
| `bt_backtest_trades` | ~28.7M | Individual backtest trades (size driver — split off `ejaguiar1_stocks` 2026-05-04). |
| `bt_backtest_runs` | ~285 | One row per backtest run. |
| `at_incubator_backtest_results` | ~1.3k | Incubator strategy backtest results. |
| `at_large_backtest_results` | ~1.1k | Large-universe backtest results. |
| `backtest_results` / `backtest_trades` | 2 / 50 | Legacy/sample. |

None of `ejaguiar1_backtests` feeds live pick generation — it is validation evidence only.

## Onboarding shortcut

To teach someone the pipeline in 5 minutes, point them at exactly four tables:
1. `at_raw_picks` — "this is every pick ever, with how it ended."
2. `at_filter_log` — "this is why picks got rejected."
3. `at_consensus_picks` — "this is what actually got published."
4. `at_pick_flow_daily` — "this is the daily scoreboard per asset class."

Everything else is detail or noise.

## Known data-quality gaps (verify before trusting)

- `at_raw_picks.closed_at` is frequently NULL even when `status` is terminal
  (CLOSED/WON/LOST/EXPIRED). Outcome rollups keyed on `closed_at` undercount.
- Non-crypto picks are often closed with `pnl_pct = 0.0` placeholder (resolver gap —
  see `feedback_noncrypto_resolver_live_close_bug`).
- `status` enum is inconsistent: both `CLOSED` and `WON`/`LOST`/`EXPIRED` appear as
  terminal states. Normalize before aggregating.
- `at_strategy_stats` is empty — do not rely on it; compute rollups from `at_raw_picks`.
