# Database Schema Review — ejaguiar1_stocks & ejaguiar1_backtests

**Date:** 2026-11-20 · **Seat:** SUBQ- / subq-savant-1.4
**Method:** read-only introspection (`SHOW TABLES`, `SHOW CREATE TABLE`, `COUNT(*)`, `GROUP BY` on status columns, `MAX()` on freshness columns, `information_schema.TABLES` for approximate row counts) via `tools/db_env` credentials.
**No DDL/DML was executed.**

---

## 1. Schema documentation that exists, and whether it is on main

Confirmed with `git ls-files` + `git cat-file -e origin/main:<path>`. All of the following are **tracked on `origin/main`**:

| File | Scope |
|---|---|
| `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` (5,992 lines) | Per-table `DESCRIBE` dump of stocks + backtests |
| `docs/FINANCE_DB_SCHEMA_SPEC.md` (626 lines) | Curated spec, generated 2026-11-19 from `information_schema` + sample rows |
| `docs/DATABASE_SPECIFICATION_2026-05-06.md` | Older general spec |
| `database/README.md`, `schemas/*.json` | Schema JSON bundles (alpha_signals, correlation, baseline) |
| `CROSS_DB_DATA_QUALITY_MATRIX.md` + `..._VERIFY.md` | Cross-DB quality matrix |
| `STOCKS_DATABASE_ANALYSIS_REPORT.md`, `crypto_db_profile.md`, `bonds_db_profile.md` | Per-domain profiles |
| `.claude/skills/db-schema/SKILL.md` | Agent-facing schema skill |

**Answer to "posted as .MD to main branch if not already": they are already there.** Nothing needed posting.

---

## 2. Claimed contract vs live reality (drift)

Live values measured today; documented values from the `.MD` files above.

| Item | Documented | Live (2026-11-20) | Drift |
|---|---|---|---|
| `ejaguiar1_stocks` table count | **322** (`DB_SCHEMA_..._2026-05-15.md`) / **409** (`FINANCE_DB_SCHEMA_SPEC.md`) | **414** | Two docs disagree with each other *and* with reality. The 5-day-old spec is off by 5; the May dump is off by 92. |
| `ejaguiar1_backtests` table count | 10 | **10** | ✅ matches |
| Empty tables in stocks | 110 of 409 | **115 of 414** | +5 empty tables since the Nov-19 spec |
| `trading_picks` rows | ~147k | **148,261** | ~+1k (expected growth) |
| `at_signal_outcomes` rows | ~51k | **51,146** | ✅ matches |
| `bt_backtest_trades` (backtests DB) | ~32.7M | **34,619,493** (approx) | +~1.9M rows, yet see freshness below |
| `bt_backtest_trades` (stocks mirror) | "mirrored from backtests" | **27,212,129** | Mirror is **~7.4M rows behind** the source DB — the "mirror" is stale/incomplete |
| `portfolio_snapshots` freshness | STALE (Mar 2026) | max `snapshot_at` = **2026-03-10** | ✅ doc correct — still stale, 8 months |
| `strategy_registry` freshness | stale-ish (Jun 2026) | max `updated_at` = **2026-06-01** | ✅ doc correct — static |
| `bt_backtest_runs` freshness | STALE (2026-03-06) | max `imported_at` = **2026-03-06** | ✅ doc correct |
| `trading_picks` PK | `id` varchar(100) | `PRIMARY KEY (id)` | ✅ matches |
| `trading_picks.status` type | varchar(20), "OPEN/ACTIVE/WON/LOST..." | varchar(20), **nullable** | Type matches; **the column is nullable** and the doc's example vocabulary is not the live one |

### Freshness of the core tables (all healthy)
`trading_picks.created_at` 2026-11-20 15:47 · `updated_at` 16:00 · `at_signal_outcomes.closed_at` 16:49 · `at_raw_picks.recorded_at` 15:08 · `now_history.scan_time` 16:45 · `at_pick_outcomes.resolved_at` 15:23 · `daily_prices.trade_date` 2026-11-19. Against `tools/db_freshness_check.py` THRESHOLDS (live_picks GREEN < 2h, resolver < 4h, signal_outcomes < 6h, backtests < 48h) the **core pipeline is GREEN**; **backtests is RED** (`bt_backtest_runs` last imported 2026-03-06 = ~259 days).

### Invariant observations
- **`trading_picks.status` is not standardised to one vocabulary:** `OPEN` 95,213 · `TIME_EXIT` 33,646 · `TP_HIT` 7,202 · `LOST` 5,732 · `SL_HIT` 3,931 · `EXPIRED` 2,516 · `ACTIVE` 21. It mixes *open-state* words (`OPEN`, `ACTIVE`) with *outcome* words (`TP_HIT`, `SL_HIT`, `TIME_EXIT`, `EXPIRED`) and *win/loss* words (`LOST`). There is no `WON` — wins are encoded as `TP_HIT`. Note `alpha_engine/hypothesis_status.py` `CANONICAL_STATES` (`PRE_REGISTERED/UNTESTED/BLOCKED_DATA/FORWARD/SUPPORTED/WEAK/REFUTED`) is a **research-hypothesis** vocabulary, not a pick-lifecycle one — it does not apply to `trading_picks.status`, so it is the wrong normaliser for this column. A pick-lifecycle enum is what's missing.
- **`OPEN` count (95,213) is dominated by never-resolved picks** — 64% of the ledger is still open, which is the real driver of the `TIME_EXIT`/`OPEN` imbalance.
- **`at_signal_outcomes.outcome` carries 9 values** including `STALE_INGEST` (4) and `RESOLVE_FAILED` (2) — small but indicates ingest/resolve errors are being persisted as outcomes rather than quarantined.
- **`at_pick_outcomes.status`** is a cleaner 4-value set (`EXPIRED`/`LOST`/`WON`/`FLAT`) — a *different* vocabulary from `at_signal_outcomes.outcome` for conceptually the same thing.

---

## 3. Verdict — is it worth reviewing ejaguiar1_stocks / ejaguiar1_backtests?

**Yes for a narrow, high-value slice; no for a broad sweep.**

**Worth reviewing (evidence-backed):**
1. **The backtests DB freshness gap.** `bt_backtest_runs` has not imported since 2026-03-06 while `bt_backtest_trades` holds 34.6M rows and the stocks mirror trails by ~7.4M. Any downstream metric that reads backtests is computing on a frozen dataset — this is a RED per the repo's own freshness thresholds. One focused review here changes a decision (whether to trust backtest-derived numbers).
2. **The two `bt_backtest_trades` copies.** 27.2M (stocks) vs 34.6M (backtests). A "mirror" that is 21% short is a silent-corruption vector — a query against the wrong DB returns different totals with no error.
3. **Status vocabulary drift** in `trading_picks.status` and between `at_signal_outcomes.outcome` vs `at_pick_outcomes.status`. Any win-rate computed by filtering `status='WON'` returns **zero** on `trading_picks` because wins are `TP_HIT`. That is a concrete, silent-wrong-number risk.

**Not worth reviewing:**
- A full table-by-table audit of all 414 tables — **115 are empty**, and the largest (`at_local_picks` 76.3M, `crypto_ohlcv` 1.16M, `at_filter_log` 505k) are append-only archives nobody re-reads. Diminishing returns.
- The non-finance DBs (`events`, `favcreators`, `news`, `tvmoviestrailers`) — out of scope for schema-drift risk.
- Re-verifying healthy core tables — they are fresh and GREEN today; the freshness guardian already covers them hourly.

**Bottom line:** the DBs are worth reviewing *because* the docs are stale and self-contradictory (322 vs 409 vs 414) and because a few specific invariants (backtest freshness, mirror divergence, status vocabulary) would silently corrupt downstream numbers. A targeted review of those three items is high value; a general schema audit is not.

---

## 4. What I did NOT verify (coverage limits)

- **Column-by-column diff for all 414 tables** — I checked DDL in detail only for 7 core stocks tables and 2 backtests tables. The remaining ~407 were enumerated (name, row count, column count) but not diffed against the docs field-by-field.
- **Index-level drift** — I captured indexes for `trading_prices`… `trading_picks` only; I did not compare documented indexes vs live indexes across the DB.
- **NOT NULL drift across the board** — verified only on the 9 inspected tables.
- **Data-level invariant checks** — only status vocabularies and freshness were sampled; I did not check referential integrity (e.g. orphaned `pick_id`s), duplicate detection, or numeric sanity (negative P&L on wins, etc.).
- **Row counts for huge tables** are `information_schema.TABLE_ROWS` approximations (as the spec itself notes), not exact `COUNT(*)`.
- **Other finance DBs** (`memecoin`, `sportsbet`, `backups`, `deals`) — not introspected.
- I did not run `check_active_picks.py` or `smart_picks_engine.py` (repo rule: only on explicit user request).
