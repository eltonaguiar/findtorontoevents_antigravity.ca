# Peer Audit Fact-Check, Part 2 — 2026-05-08

Read-only verification of 5 new findings against live `ejaguiar1_stocks` MySQL 8.4.7 at `mysql.50webs.com`.
Connection: `audit_trail.mysql_client._create_connection()` with `MAX_EXECUTION_TIME=120s`.

---

## Finding 1 — `algorithm_rolling_perf` resolver disconnect

**Verdict: PARTIALLY_TRUE.**

Peer claim was "3,536 rows where `resolved_picks=0` AND `win_rate=0` AND `avg_return=0`". Real numbers:

| Metric | Value |
|---|---|
| Total rows | 3,536 (peer cited this as the all-zero count — actually the table size) |
| `resolved_picks=0 AND win_rate=0 AND avg_return_pct=0` | **1,677** (47.4%) |
| `resolved_picks > 0` (resolver-OK) | 1,859 (52.6%) |
| `total_picks=0` (writer never had data — empty algos) | 1,592 |
| **`total_picks > 0` BUT `resolved_picks=0`** (the actual resolver-link bug) | **85** |
| `created_at` range | 2026-02-09 → 2026-04-27 (writer is alive, last write 11 days ago) |
| `period` | 30d (1,768) and 7d (1,768) — clean even split |
| `source_table` | `stock_picks` 2,786, `miracle_picks3` 750 |

**Schema note:** peer used `algorithm` and `lookback_window`; actual cols are `algorithm_name` and `period`, `created_at` (no `last_updated`).

**Diagnosis:** Writer is **NOT broken** — it dutifully inserts a row per (source_table, algorithm_name, period, calc_date) tuple every cycle, even when there are zero picks. The 1,592 `total_picks=0` rows are *empty algos* (nothing to score that day), not a resolver bug. The legitimate resolver-link gap is the **85 rows where `total_picks>0` but `resolved_picks=0`** (resolver missed picks the writer saw). Plus the table is **stale by 11 days** — last `created_at = 2026-04-27 23:54:26`, today is 2026-05-08. So the cron itself appears to have stopped after Apr 27.

**Impact:** Audit dashboard rolling-perf widget shows zero-WR/zero-PF for half the algo rows by design (no picks that day), masking the 85 true resolver gaps. Two-tier fix needed.

**Suggested fix:**
1. **P1 — restart the rolling-perf cron** (last write Apr 27 — 11 days dark). Check `algorithm_rolling_perf_cron.sh` or whichever script writes here.
2. **P2 — change the writer to skip insertion when `total_picks=0`** OR add a `data_status ENUM('NO_PICKS','PARTIAL','RESOLVED')` column so dashboards can distinguish "empty algo" from "resolver gap".
3. **P2 — backfill the 85 `total_picks>0, resolved_picks=0` rows** by re-running the resolver against their (algorithm_name, calc_date, period) tuple.

---

## Finding 2 — `at_discord_notifications` `signal_tier` broken

**Verdict: CONFIRMED.**

| Metric | Peer claim | Actual |
|---|---|---|
| `signal_tier` NULL | 40K NULL ("None") | **40,174 NULL of 40,179 (99.99%)** |
| `signal_tier` populated | 5 rows STRONG/MODERATE | **STRONG=3, MODERATE=2** |
| `direction` empty | 21K empty | **`<empty>` 21,326 of 40,179** (LONG 18,372, SHORT 481) |
| `source_systems` NULL | "many empty" | **21,587 NULL of 40,179 (53.7%)** |
| `strategy` NULL/empty | not specified | **NULL=21,362, empty=3,407 = 24,769 total (61.6%)** |

`source_systems` is `JSON` type. `signal_tier` is `varchar(20)`. Date range: 2026-02-25 → 2026-05-08 14:50 (active ~now).

**Looking at the 3 most-recent rows (id 40751, 40750, 40749):**
- id 40751 `event_type=FORWARD_TEST_UPDATE`: direction='', source_systems=NULL, strategy=NULL, signal_tier=NULL — these are *summary/heartbeat rows*, not picks
- id 40750 `event_type=COMBO_FINDINGS`: same pattern — summary row
- id 40749 `event_type=PICK_POSTED`: direction='LONG', source_systems valid JSON, strategy='RSI Divergence Scalp', **signal_tier=NULL** — pick row, but signal_tier still NULL

**Diagnosis:** Two distinct bugs:
- **Bug A (signal_tier writer broken everywhere):** Even legitimate `PICK_POSTED` rows have `signal_tier=NULL`. The writer never populates this column. The 5 surviving STRONG/MODERATE rows are likely from an earlier code path that was removed. **Not a JSON-deserialization bug** — `signal_tier` is plain varchar.
- **Bug B (event_type pollution):** Summary rows (FORWARD_TEST_UPDATE, COMBO_FINDINGS, etc.) leave `direction`, `source_systems`, `strategy` NULL/empty because they don't apply to non-pick events. Whoever queries `at_discord_notifications` for analytics is conflating heartbeats with picks.

**Impact:** Anything reading `at_discord_notifications` and filtering by `signal_tier='STRONG'` returns ~0 rows — gates that depend on tier are silently no-ops. Anyone counting picks by `direction` overcounts by ~21K heartbeat rows.

**Suggested fix:**
1. **P1 — wire the signal_tier writer.** Find the `INSERT INTO at_discord_notifications` site and add `signal_tier` from the upstream tier classifier.
2. **P1 — add an `event_type` filter to all analytics queries** (`WHERE event_type='PICK_POSTED'`) OR split the table into `at_discord_picks` and `at_discord_events`.
3. **P2 — backfill `signal_tier`** on existing PICK_POSTED rows from `confidence`/`agreement_count`/`source_systems` payload.

---

## Finding 3 — `trading_picks` mixed direction vocab + empty strategy

**Verdict: CONFIRMED.**

`trading_picks` total = **63,934 rows**. Direction distribution:

| Value | Count | Pct |
|---|---|---|
| `SHORT` | 30,592 | 47.9% |
| `LONG` | 28,239 | 44.2% |
| `BUY` | 3,290 | 5.1% |
| `SELL` | 1,364 | 2.1% |
| `<empty>` | **449** | 0.7% |
| `<NULL>` | 0 | — |

**Both vocabularies are present** — 4,654 rows use BUY/SELL (7.3%), the rest use LONG/SHORT. **449 empty matches peer.** No NULLs — column has empty-string default.

**`strategy` empty:** **2,668 rows have `strategy=''`** (NULL count = 0). Peer's 2,668 figure is exact. Empty-strategy rows include `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, etc. as *populated* peers, so this is a writer-path bug, not a schema-default.

**Diagnosis:** Two writer paths feeding the same table — one emits LONG/SHORT (likely the new perp/futures strategies), one emits BUY/SELL (legacy stock-style writer). `trading_picks.id` format (`{SYMBOL}_{TF}_{DATE}_{HHMM}`) suggests the BUY/SELL ones are from the older `stock_picks`-style code path that hasn't been migrated. Empty `direction`/`strategy` are likely consensus-aggregation rows where the upstream lookup failed (similar to Finding 2's heartbeat rows).

**Impact:** Any `WHERE direction='LONG'` query silently misses 3,290 BUY rows. Any GROUP BY strategy aggregates 2,668 rows under `''`, polluting per-strategy WR/PF rankings.

**Suggested fix:**
1. **P1 — add a `direction` migration script:** `UPDATE trading_picks SET direction='LONG' WHERE direction='BUY'; UPDATE … SET direction='SHORT' WHERE direction='SELL';` (validate first that BUY ≠ SHORT-cover anywhere). Then add a CHECK constraint `direction IN ('LONG','SHORT')`.
2. **P1 — find and fix the 2 writer paths** so new inserts use a consistent vocab. Grep for `INSERT INTO trading_picks` in `audit_trail/`, `alpha_engine/`, and the cron/CGI dirs.
3. **P2 — backfill or delete the 449 empty-direction + 2,668 empty-strategy rows** after confirming they're not recoverable from the source pick.

---

## Finding 4 — `exit_price=0` for closed positions

**Verdict: CONFIRMED, much worse than peer described.**

### `trading_picks` (63,934 total)

| Status | Rows w/ exit_price=0 or NULL | Total | Rate |
|---|---|---|---|
| `TIME_EXIT` | **19** | 19 | **100%** |
| `SL_HIT` | **789** | 818 | **96.5%** |
| `TP_HIT` | **604** | 629 | **96.0%** |
| `EXPIRED` | 387 | 1,358 | 28.5% |
| `LOST` | 52 | 3,067 | 1.7% |
| `WON` | 22 | 2,547 | 0.9% |
| `CLOSED` | 2 | 177 | 1.1% |
| `LOSS`/`WIN`/`CLOSED_SL`/`CLOSED_TP` | 0 | 859 | 0% |
| **Total CLOSED-like w/ exit_price=0/NULL** | **1,782** | 9,475 | 18.8% |
| Of those, also `pnl_pct=0`/NULL | **288** | | |

The `<empty>` value here is `NULL`, not 0 — the writer never sets `exit_price` for these rows. Sample shows `pnl_pct` IS populated (e.g. -6.73, 0.16), so resolver computed PnL but discarded the price.

### `lm_signals` (33,557 total)

| Status | Rows w/ exit_price=0 or NULL | Total | Rate |
|---|---|---|---|
| `expired` | **32,019** | 33,289 | **96.2%** |
| `executed` | **199** | 199 | **100%** |
| `resolved` | 0 | 10 | 0% |
| Of expired+executed, also `pnl_pct=0` | 31,537 | | |

Sample: `(33512, 'FLOKIUSD', 'BUY', 'expired', entry=0.00003601, exit=0E-8, pnl=0.0000, resolved_at=NULL, signal_time=2026-05-08 13:04:21)` — entry was set, exit defaulted to `0E-8`, pnl=0, `resolved_at=NULL`. So the "expired" status is being applied by a *time-based sweeper* without ever fetching the actual exit price.

**Diagnosis:**
- **`lm_signals`:** `exit_price` defaults to `0E-8` (numeric zero) in the schema. The 'expired' status is set by a time-based cron (rows where `signal_time` is past `expires_at`), but **the cron does NOT call the resolver** — it just stamps `status='expired'` and leaves `exit_price=0`, `pnl_pct=0`, `resolved_at=NULL`. Effectively all `expired` rows are unresolved-but-mislabeled. Only the 10 `resolved` rows have legitimate exit data.
- **`trading_picks`:** Different bug. `SL_HIT`/`TP_HIT` rows have `pnl_pct` populated (the resolver computed it from entry vs SL/TP target), but `exit_price` was never written back. So the resolver knows it hit SL/TP and back-derives pnl from the SL/TP target prices, but doesn't store the realized fill price. `TIME_EXIT` is 100% missing — same time-sweeper issue as `lm_signals.expired`.

**Impact:** Any backtest/replay that needs realized exit prices (slippage modelling, CLV calc, after-fees PnL) is broken for ~33,801 rows across both tables. Aggregated WR/PF figures using `pnl_pct` are still usable for `trading_picks` (since pnl_pct was computed off SL/TP targets), but `lm_signals` aggregates are *garbage* — 96% of rows show pnl=0 because nothing resolved.

**Suggested fix:**
1. **P0 — `lm_signals` resolver gap.** The "expire-stamp without resolve" cron is the root cause. Either (a) merge the expire and resolve crons so every status transition fetches the actual close price, or (b) have the audit pipeline ignore `lm_signals.expired` rows where `exit_price=0` and re-resolve them async.
2. **P1 — `trading_picks` exit_price write-back.** When the resolver computes pnl_pct from SL/TP target, it already has the price — write it to `exit_price`. Roughly 1-line patch wherever `UPDATE trading_picks SET status='SL_HIT', pnl_pct=…` is issued.
3. **P1 — backfill** the historic 33,801 rows: re-resolve expired rows via yfinance/Binance OHLC at `expires_at`, write `exit_price` + `resolved_at`.

---

## Finding 5 — 102 empty tables

**Verdict: CONFIRMED (102 exact match, all 10 spot-checks empty).**

```
SELECT COUNT(*) FROM information_schema.TABLES
WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_ROWS=0  →  102
Total tables in schema: 322 (32% empty)
```

Spot-check via actual `COUNT(*)` on 10 randomly-sampled tables — **10/10 returned 0**, so InnoDB stats are accurate here (not stale).

### Categorization

| Category | Count | Examples | Verdict |
|---|---|---|---|
| **`lm_*` (LM bridge)** | 19 | lm_bridge_congress, lm_bridge_entropy, lm_ensemble_weights, lm_walk_forward, lm_meta_labels, lm_feature_importance | **abandoned** — LM bridge concept never shipped writers |
| **`fx_*` / `fxp_*`** | 11 | fx_backtest_results, fxp_category_perf, fx_price_history, fxp_comparisons | **scaffolding** — FX backtest tables created but never populated |
| **`mf_*`** | 7 | mf_backtest_results, mf_benchmarks, mf_category_perf | **scaffolding** — mutual-fund tables likely never wired |
| **`crypto_*`** | 6 | crypto_indicators, crypto_ohlcv, crypto_patterns, crypto_signals, crypto_whale_movements | **rotation-target** — crypto features now live in other tables (e.g., `at_discord_notifications.payload`, `trading_picks`) |
| **`ml_*`** | 6 | ml_ab_tests, ml_calibration_log, ml_ensemble_weights, ml_model_performance | **scaffolding** — ML observability never wired |
| **`KIMI_GOLDMINE_*`** | 5 | KIMI_GOLDMINE_ALERTS, _PICKS, _WINNERS, _PERFORMANCE | **abandoned** — Kimi goldmine experiment died, no writer |
| **`portfolio_*`** | 5 | portfolio_positions, portfolio_daily_equity, portfolio_resets, portfolio_comparisons | **abandoned** — portfolio tracker never persisted, P&L lives elsewhere |
| **`cr_*` / `cp_*`** | 6 | cr_backtest_results, cr_backtest_trades, cp_report_cache | **scaffolding** — backtest cache never populated |
| **`goldmine_cursor_*`** | 4 | goldmine_cursor_circuit_breaker, _correlation_matrix, _regime_log | **abandoned** — Cursor-driven goldmine experiment never shipped |
| **`at_*`** | 3 | at_discord_gate_state, at_sqlite_imports, at_strategy_stats | **mixed** — gate_state likely lazy-init, sqlite_imports one-off migration scaffold |
| **`sp_*`** | 3 | sp_batches, sp_daily_performance, sp_picks | **abandoned** — naming overlaps `stock_picks` cluster but never written |
| **`stock_*`** | 3 | stock_assets, stock_ohlcv, stock_signals | **rotation-target** — stock data now in `stock_picks` and `miracle_picks3` |
| **`strategy_*`** | 3 | strategy_health_audit, strategy_status_history, strategy_whatif_results | **abandoned** — strategy lifecycle persistence never wired |
| Other (mc_, meme_, social_sentiment, consensus_history, consolidated_cache, circuit_breaker_log, etc.) | ~20 | | **mostly abandoned** |

**Impact:** Schema bloat — `SHOW TABLES` adds 32% noise, makes audit/migration scripts heavier. Monitoring tools that probe row counts emit 102 spurious "empty" alerts. No correctness impact (nothing reads them, nothing writes them), but every new dev/agent has to learn which 220 tables are real.

**Suggested fix:**
1. **P2 — drop the abandoned tier first** (~73 tables): all `KIMI_GOLDMINE_*`, all `lm_bridge_*` + experimental `lm_*`, all `goldmine_cursor_*`, all `cp_*`/`cr_*`/`fxp_*`/`mf_*` backtest scaffolds, `portfolio_*`, `sp_*`, `strategy_*` lifecycle, `consensus_history`, `consolidated_cache`, `circuit_breaker_log`, `social_sentiment`. Verify via `grep -r '<table_name>' .` returns 0 readers/writers before drop.
2. **P3 — keep the rotation-targets** (`crypto_*`, `stock_*`) as deprecated-but-documented; they have schemas worth referencing if/when the data path is rebuilt.
3. **P3 — keep lazy-init tier** (`at_discord_gate_state` etc.) — these may legitimately be empty at rest.

Recommend a `DROP TABLE` migration PR with a rollback list, not a one-shot script.

---

## Summary — Findings to add to action plan beyond existing 24

| # | Verdict | New Action | Tier |
|---|---|---|---|
| 1 | PARTIALLY_TRUE | Restart `algorithm_rolling_perf` cron (dark since Apr 27); add `data_status` enum; backfill 85 resolver-gap rows | P1 |
| 2 | CONFIRMED | Wire `signal_tier` writer in `at_discord_notifications`; split heartbeat events from picks via `event_type` filter | P1 |
| 3 | CONFIRMED | Migrate BUY/SELL → LONG/SHORT in `trading_picks`; fix dual writer path; CHECK constraint | P1 |
| 4 | CONFIRMED (worse) | **`lm_signals` 96% expired-without-resolve** — merge expire/resolve crons; backfill 33,801 rows; write `exit_price` in `trading_picks` resolver | **P0** |
| 5 | CONFIRMED | Drop ~73 abandoned tables in 4 buckets (KIMI_GOLDMINE, lm_bridge, goldmine_cursor, cp/cr/fxp/mf scaffolds); keep rotation-targets documented | P2 |

The P0 escalation is Finding 4: `lm_signals` is structurally unresolved for 32K rows because the time-expire cron and the resolver are separate crons that never talk to each other. Any analytics on `lm_signals` PnL aggregates is currently meaningless.
