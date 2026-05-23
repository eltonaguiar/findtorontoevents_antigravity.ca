# DB Review — Vetted Summary 2026-05-08

Single source of truth for the 2026-05-07/08 forensic sweep. Every claim below is either CONFIRMED with cited evidence or explicitly DISPUTED. Speculative / hallucinated / unverified claims removed.

Inputs combined:
- `reports/db_master_synthesis_2026-05-07.md` (initial forensic synthesis)
- `reports/db_action_plan_2026-05-08.md` (24-todo execution plan)
- `reports/db_action_plan_delta_2026-05-08.md` (peer-audit reconciliation)
- `reports/peer_audit_factcheck_2026-05-08.md` + `_part2_2026-05-08.md` (10 peer claims verified)
- `reports/uncharted_tables_recon_2026-05-08.md` (6 family sweep)
- `reports/freeze_2026_04_02_root_cause_2026-05-08.md` (smoking gun)
- `reports/forensic_q1_q4_2026-05-07.md` + `q5_q7` + `crypto_edge_hunt_2026-05-07.md` + `non_crypto_resolver_gap_2026-05-07.md`
- User-supplied 7-step framework (Preparation → Wave 0 → Wave 1 → Wave 2 → Wave 3 → Reporting → Next Steps)

---

## 🔴 SMOKING GUN — root cause of all 5 broken pipelines

`alpha_engine/data/circuit_breaker_state.json` is checked into the repo at:

```json
{"level": "HALT", "max_picks": 0, "min_confidence": 1.0, "timestamp": "2026-03-24T06:08:02", ...}
```

— **45 days stale**, never refreshed.

Mechanism (verified via grep + file read):
- `production_scanner.py:3513` does `MAX_ACTIVE_PICKS = min(MAX_ACTIVE_PICKS, _cb_state["max_picks"])`
- With `max_picks=0`, every pick-generation cron emits zero new picks
- `forward_validator.py:1292` is the ONLY WON/LOST writer in `run_generation`. Downstream of pick generation, so it never fires.
- Cascade: no closes → MySQL sync flatlines on `bt_backtest_trades` → `algorithm_rolling_perf` writer freezes → `at_consensus_picks` resolver gets stale rows (explains the time-travel `closed_at < generated_at`) → `lm_signals` expire-cron skips `outcome_resolver` → discord `signal_tier` writer never fires.

Triggers in the file cite `loss_streak=175` against `closed_picks_count=527`. Today's `closed_picks.json` has 34,860 rows — the breaker computed against truncated data and never re-evaluated.

**This is a textbook re-occurrence of `feedback_circuit_breaker_stale_state_leak.md`** — same bug filed for 2026-04-27 (~115h lockout). The earlier 2026-03-24 leak was never caught because the patch addressed the symptom, not the persistence pattern.

### Three candidate root-cause commits (evidence in `reports/freeze_2026_04_02_root_cause_2026-05-08.md`)

| candidate | severity | fix |
|---|---|---|
| **A** stale HALT state file | highest | delete `circuit_breaker_state.json` + add 6h TTL guard |
| **B** commit `79aec7d7356` deleted `mysql_fetch_closed_non_crypto` one day after it was added | medium | resurrect or compute equivalent from MySQL |
| **C** commit `5a6112736c4` "reset stale LONGs" truncated `closed_picks.json` | lower | review truncation; re-run breaker against full closed_picks.json |

---

## DB scale — vetted numbers

| metric | vetted value | source |
|---|---|---|
| DB | `ejaguiar1_stocks` (mirror exists at `ejaguiar1_backtests`) | live `SHOW DATABASES` |
| Engine | **MySQL 8.4.7** (NOT MariaDB; peer audit mislabel) | live `SELECT VERSION()` |
| Total tables | 322 | live `information_schema.TABLES` |
| `bt_backtest_trades` rows | **29,845,129** (29.85M, growing) | live `COUNT(*)` |
| `bt_backtest_trades` data + index | 1,419 MB + 125 MB = **1.54 GB** | `DATA_LENGTH + INDEX_LENGTH` |
| Total DB size | ~2.06 GB | `SUM(DATA_LENGTH+INDEX_LENGTH)` |
| **Date range** | 2024-02-07 → 2026-05-08 | `MIN/MAX(entry_time)` |
| Indexes on `bt_backtest_trades` | 5 single-column: PK, backtest_run_id, symbol, asset_class, strategy, status | live `SHOW INDEX` |

Note: `information_schema.TABLES.TABLE_ROWS` reports 1,312,509 for `bt_backtest_trades` — a **22.7× under-count** vs real `COUNT(*)`. This is normal InnoDB behavior. NEVER cite TABLE_ROWS for InnoDB sizing decisions.

---

## ✅ CONFIRMED critical findings (with evidence)

### F1. Forward-validator + 4 downstream pipelines frozen since 2026-03-24

| pipeline | symptom | evidence |
|---|---|---|
| Forward-validator | WON/LOST writes stopped | `MAX(imported_at) WHERE status IN ('WON','LOST')` returns 2026-04-02 ish (35d ago) |
| `algorithm_rolling_perf` | last write 2026-04-27 (11d) | last_updated query |
| `at_consensus_picks` resolver | 5,268 / 9,188 rows (57.3%) have `closed_at < generated_at`, avg 35.66h ahead, max 149h | live SQL count |
| `lm_signals` expire-cron | 32,019 / 33,289 expired (96.2%) have exit_price=0 | live SQL count |
| `at_discord_notifications.signal_tier` | 40,174 / 40,179 (99.99%) NULL | live SQL count |

Root cause = stale circuit-breaker file. See SMOKING GUN above.

### F2. Ghost-row pollution in `bt_backtest_trades`

| pattern | row count | evidence |
|---|---|---|
| `quan_engine MATICUSDT LONG @ pnl_pct=-15.0000` | **215,248** rows ALL constant | live SQL: STDDEV=0, COUNT(DISTINCT pnl_pct)=1 |
| `meta_strategy MATICUSDT LONG @ 0.0` | **2,444** rows ALL zero | same |
| `meta_strategy` template family (constant pnl_pct ∈ {+5.0, −3.0}) | **~1.6M** rows across ~140 (symbol, direction) tuples | live SQL groupby |
| `KIMI_signal_tracker ETH/BTC LONG` multi-TP template | 4 win-buckets × 597 + 1 loss × 606 | live SQL groupby |
| `irb_hoffman ADAUSDT SHORT` 50/50 | exact split at −1.78 / +30.30 | live SQL groupby |
| `funding_rate_carry ROBOUSDT LONG` | 566× −99.26 (delisting force-close) | live SQL groupby |

### F3. Phantom-closed rows (TTL-expirer bug)

| asset_class | phantom rows | evidence |
|---|---|---|
| EQUITY | 3,840 | `status='EXPIRED' AND pnl_pct=0 AND exit_price=entry_price` |
| FUTURES | 4,800 | same |
| ETF | 960 | same |
| FOREX | 80.7% (5,280 / 6,544) | same pattern + bimodal at −27.93%/−9.14% |

Plus 18.3% of FOREX rows are duplicate `KIMI_signal_tracker` re-imports (AUDUSD/EURUSD picks 5-10× duplicated).

### F4. `at_consensus_picks` time-travel

5,268 of 9,188 rows (57.3%) have `closed_at < generated_at` — avg 35.66h ahead, max 149h. Resolver retro-stamps `closed_at` to the historical price-bar that triggered TP/SL, while `generated_at` is the cron-write time. Same class as `feedback_noncrypto_resolver_live_close_bug.md` but on the supposedly-clean crypto path.

### F5. Confidence inverts at high end (CRYPTO)

| conf bucket | n | WR % | PF |
|---|---|---|---|
| 0.4 | 78k | 36.18 | 0.68 |
| 0.5 | 830k | 41.95 | 0.50 |
| 0.6 | 775k | 38.27 | 0.46 |
| 0.7 | 508k | 47.42 | 0.81 |
| 0.8 | 191k | 38.89 | 0.94 |
| **0.9** | **70k** | **22.97** | **0.23** |

`>=0.85` confidence is anti-predictive on CRYPTO and MEMECOIN. Confirms `feedback_confidence_is_not_edge.md`.

### F6. Every CRYPTO hour has PF<1

Best=22 UTC PF 0.79 / WR 56.5%; Worst=11 UTC PF 0.30 / WR 28.8%. No hour-of-day cohort meets Tier 2.

### F7. Tier verdicts (using canonical terminal status + pnl_pct sign)

| asset_class | n closed | WR % | PF | tier |
|---|---|---|---|---|
| CRYPTO | 1.15M | 32.08 | 0.41 | sub-floor |
| MEMECOIN | 38,731 | 46.82 | 0.56 | sub-floor |
| FOREX | 6,304 | 0.71 | 0.002 | broken (resolver+phantom+dup) |
| EQUITY | 3,680 | 0.0 (all phantom) | — | phantom |
| FUTURES | 4,600 | 0.0 (all phantom) | — | phantom |
| ETF | 920 | 0.0 (all phantom) | — | phantom |
| PENNY_STOCK | 1,694 | 35.12 | 0.28 | sub-floor |

**No asset class meets Tier 2.** EQUITY/FUTURES/ETF currently uncomputable.

### F8. `at_discord_notifications.signal_tier` 99.99% NULL — STRONG TAKE pipeline broken

40,174 / 40,179 rows NULL. Only 3 STRONG + 2 MODERATE survive. Direction empty 21,326. source_systems NULL 21,587. strategy NULL/empty 24,769. The HTML peer report's "NBA STRONG TAKE +164% / NHL STRONG TAKE −100% (n=3 each)" was computed off these 5 surviving rows.

### F9. `trading_picks` direction dual-vocab (two writer paths)

LONG 28,239 + SHORT 30,592 + **BUY 3,290 + SELL 1,364** + 449 empty. 2,668 rows have empty/null `strategy`. Two writers feeding one table.

### F10. `lm_signals` exit_price=0 96.2% on expired

32,019 / 33,289 expired have exit_price=0. `trading_picks`: TIME_EXIT 100%, SL_HIT 96.5%, TP_HIT 96.0% NULL exit_price. Resolver computes pnl from SL/TP target but never writes back actual exit price.

### F11. `simulation_grid` 100% LONG (6,000 / 6,000, 0 SHORT)

Parameter grid for backtests has no SHORT coverage. Every conclusion drawn from this grid is LONG-only-conditional.

### F12. `asset_class=''` empty-enum bug (sql_mode non-strict)

at_raw_picks 2,490 rows; at_audit_events 490; at_consensus_picks 279. Both `''` and `UNKNOWN` coexist. Python None → "" instead of `UNKNOWN`.

### F13. `meme_signals` 50-row table is synthetic training fixture

Every winning symbol has a "2"-suffixed loser counterpart (PEPE/PEPE2). First 30 rows = 100% wins, last 20 = 100% losses. Every row resolves exactly 1m38s after creation. `max_profit_pct`/`max_loss_pct` NULL on every row. `meme_ml_models` was trained on those same 50 rows → recall=1.0 in-sample. **Not real edge.**

### F14. Memecoin production cohort no edge

`bt_backtest_trades.MEMECOIN`: n=123,648 closed, **WR 31.6% / PF 0.58**. No edge in production-scale data.

### F15. Sports DB partial-stale

`lm_sports_value_bets` fresh (last 2026-05-04, 65 in 7d), `lm_sports_daily_picks` fresh (5/3, 9 in 7d). Cold: `lm_sports_ml_predictions` since 2026-02-16, `lm_sports_clv` since 2026-02-12. `lm_arena_bets` 344 rows all `pending` never settled. NCAAB CLV −1.46%, NBA −0.93%. Sports does NOT meet "proven" per charter (≥4-week + non-negative CLV).

### F16. 102 empty tables (73 abandoned, 9 rotation, 3 lazy-init)

Confirmed exact count + 10/10 spot-checks empty. Categories: `KIMI_GOLDMINE_*`, `lm_bridge_*`, `goldmine_cursor_*`, `cp_*`, `cr_*`, `fxp_*`, `mf_*`, `portfolio_*`, `sp_*`, `strategy_lifecycle_*`.

### F17. `gm_sec_insider_trades` is the only quietly-active feature feed

714 rows, 8 fresh today. Daily SEC Form-4 ingest. Wire as EQUITY scoring feature, not a pick stream.

### F18. `penny_picks` cron stopped 2026-04-27 — same freeze pattern

1,029 rows, 40-col scoring schema, 698 active / 331 closed. Same "DB-OK, pick-cron-dead" pattern as sports + algorithm_rolling_perf. **Restarting unlocks ~1k EQUITY rows over the charter n=1k floor — highest-leverage Goal #1 win.**

### F19. `fxp_pair_picks` (1,184) + `cr_pair_picks` (952) ACTIVE through 2026-05-07 — but no outcome columns

Both freshly written but **no `status`/`exit_price`/`pnl_pct` columns**. Pure idea streams that never resolve. Build a price-history-join resolver before wiring; otherwise inflate counts without truth-grade data.

### F20. Mutual-fund v1→v2 was abandonment, not migration

`mf_*` 89 days dead. `mf2_*` has heartbeat (`mf2_audit_log` writes today) but pick generator dead 40 days. Schemas differ (`ticker/nav_price` vs `symbol/nav`, 3 of 7 cols shared). Out of Goal #1 scope.

---

## ❌ DISPUTED / RETRACTED claims (do NOT cite)

| claim | source | actual |
|---|---|---|
| `bt_backtest_trades` = 1.31M rows | peer audit summary | **29.85M** (peer used InnoDB info_schema = 22.7× under-count) |
| Engine: MariaDB | peer audit summary | MySQL 8.4.7 |
| Total DB rows ~2.26M | peer audit summary | ~30M+ (info_schema sum unreliable) |
| `consensus_tracked` 100% synthetic | peer audit summary | 0/318 future-dated; only 6 round prices; 83 zero-returns explicable; **looks like real equity backtest data** |
| `rapid_signals` 50/50 win/loss improbable | peer audit summary | n=35K, 95% CI fits 49.48-50.52% — statistically NORMAL. Real bug = 5,237 rows (14.8%) labeled win/loss with pnl=0 |
| 97.6% PnL recompute mismatch | gemini swarm | actual 67.7-79.9% on **computable rows only** (only 12.3% of total) |
| 86% missing strategy attribution | gemini swarm | 5.7% |
| Mixed BUY/SELL/LONG/SHORT in at_raw_picks | gemini swarm | LONG/SHORT only in at_raw_picks. Mixed vocab DOES exist in `trading_picks` (F9). |
| meme_signals tier1 60% WR is real edge | HTML report | mathematically true on n=50 fixture, but synthetic + leakage (F13) |
| meta_strategy + TRXUSDT 62.5% / +9.33% is top edge | HTML report | n=8 in HTML scope; full bt_backtest_trades cohort is templated PnL (F2) |
| MATICUSDT 1,061 picks / 0% WR | HTML report (last-7d at_raw_picks scope) | true in scope, but 215K polluted rows in bt_backtest_trades = strategy bug, not symbol bug |

---

## Vetted execution plan (incorporates user's 7-step framework)

### Step 1 — Preparation & Baseline (do FIRST, today)

| sub | action | command | rationale |
|---|---|---|---|
| 1.1 | Create branch | `git switch -c audit-review-2026-05-08 && git add reports/ && git commit -m "chore(audit): land 2026-05-08 forensic reports"` | clean repo state; reference reports from branch |
| 1.2 | Schema baseline | `mysqldump --no-data -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks > reports/schema_baseline_2026-05-08.sql` | snapshot before any DDL |
| 1.3 | Read-only user check | already have `ejaguiar1_stocks` SELECT-only effectively (no observed writes from this credential) | low-risk; we can run anything |
| 1.4 | Skip general query log on shared host (no ACCESS) | n/a | can't enable on 50webs shared; rely on `swarm_runs/_calls.jsonl` + `audit_log` table |

### Wave 0 — Census + ghost sweep + integrity (read-only; today)

| sub | task | tool / SQL | gate |
|---|---|---|---|
| 0-A | Census per table | already have via this report | done — 322 tables, 29.85M rows in bt_backtest_trades |
| 0-B | Ghost sweep (orphan FK) | `SELECT t.id FROM bt_backtest_trades t LEFT JOIN bt_backtest_runs r ON r.id=t.backtest_run_id WHERE t.backtest_run_id IS NOT NULL AND r.id IS NULL` | dangling < 1% of 29.85M |
| 0-C | PnL recompute integrity | `SELECT 100*SUM(ABS(pnl_pct - (exit_price-entry_price)/entry_price*100) > 1)/COUNT(*) FROM bt_backtest_trades WHERE entry_price>0 AND exit_price>0` | mismatch < 5% on computable rows |
| 0-D | Numeric NULL sanity | `SELECT COUNT(*) FROM bt_backtest_trades WHERE pnl_pct IS NULL AND status NOT IN ('OPEN')` | NULL ratio reported per asset_class |
| 0-E | Index health | `ANALYZE TABLE bt_backtest_trades` (DB writes — use `--skip-write-binlog` if available; else accept it's metadata-only) | confirms cardinality stats |
| 0-F | OPEN-population census (NEW) | `SELECT asset_class, COUNT(*), AVG(TIMESTAMPDIFF(DAY,entry_time,NOW())) FROM bt_backtest_trades WHERE status='OPEN' GROUP BY asset_class` | identify 35d-frozen OPEN rows per class |
| 0-G | bt_backtest_trades synthetic sweep (NEW) | extend `audit_synthetic_patterns.py` to scan all asset_classes for constant-pnl cohorts (n>1000) | already known: 5 cohorts in CRYPTO; check EQUITY/COMMODITY/BOND |

### Wave 1 — UNFREEZE first, then quarantine (P0)

**Reordered for the smoking gun**: unfreeze must come before quarantine. Quarantining ghost rows is meaningless if no new rows can land for 35 days.

| step | todo | implementation |
|---|---|---|
| 1 | **NEW-P0-X** Delete `alpha_engine/data/circuit_breaker_state.json`. Add 6h TTL guard at `production_scanner.py:3513` so a stale file gets ignored. | `rm` the file + git commit; edit production_scanner.py; deploy via `audit-dashboard.yml` cycle; watch one cycle to confirm WON/LOST writes resume. |
| 2 | **P0-5** Verify forward-validator unfrozen (Q-V2 from action plan) | `MAX(imported_at) WHERE status IN ('WON','LOST')` should return < 26h |
| 3 | **P0-1+P0-2** Quarantine MATIC + meta_strategy ghost rows (ingest filter) | `audit_trail/dashboard_generator.py:_filter_picks` |
| 4 | **P0-3** Drop phantom EXPIRED rows | same file |
| 5 | **NEW-P0-7** at_consensus_picks time-travel filter | `WHERE closed_at >= generated_at` |
| 6 | **NEW-P0-8** lm_signals expire-without-resolve fix | invoke resolver from expire-cron (find writer in `live-monitor/` or similar) |
| 7 | **P0-6** Hunt quan_engine constant-pnl writer | grep + minimal repro |
| 8 | **NEW-P0-10** Wire `at_discord_notifications.signal_tier` writer + filter event_type | trace writer in `audit_trail/recorder.py` or discord adapter |

### Wave 2 — Schema (P1)

Existing P1-7 to P1-12 from `db_action_plan_2026-05-08.md` + delta P1-13/14/15 (trading_picks vocab unify, asset_class='' backfill, simulation_grid SHORT rerun).

### Wave 3 — Re-route + retrain (P2)

Existing P2-13 to P2-18 from action plan + delta P2-19 (rapid_signals pnl=0 scrubber). **Add NEW-P2-20**: restart `penny_picks` cron — same freeze pattern, 1k+ EQUITY rows unblocked = highest-leverage Goal #1 win.

### Wave 4 — Dashboard + housekeeping (per user's section 6)

- DB Health dashboard (`audit_dashboard/db_health.html`): row counts per table, orphan counts, PnL delta warnings, dup count, NULL ratios, resolver-freshness ages.
- `audit_log` table for script-execution trail (timestamp, script, user, affected rows).
- Update `AUDIT_BLUEPRINT.md` to reflect circuit-breaker TTL + 30-todo plan.
- Drop 73 abandoned tables after manual review.

---

## QA verification queries (Q-V1 to Q-V14, consolidated)

| # | gate | sql / file ref | pass |
|---|---|---|---|
| Q-V1 | CRYPTO PF post-quarantine | see `db_action_plan_2026-05-08.md` | PF > 0.7 |
| Q-V2 | Forward-validator unfrozen | `MAX(imported_at) WHERE status IN ('WON','LOST')` | hours_ago < 26 |
| Q-V3 | FOREX dedupe | dupe count by (strategy, symbol, entry_time, direction) | dupes < 30 |
| Q-V4 | terminal_outcome integrity | mismatch query | = 0 |
| Q-V5 | terminal_outcome index used | EXPLAIN | key NOT NULL, type ref/range |
| Q-V6 | Importer fix — confidence NULL | `AVG(confidence IS NULL) WHERE imported_at > NOW()-7d` | < 5% |
| Q-V7 | challenge_200_trades positive cohort holds | WR + PF + n | WR>50% AND PF>1.2 AND n≥600 |
| Q-V8 | Phantom EXPIRED dropping | weekly trend | down WoW |
| Q-V9 | OPEN avg age | `AVG(TIMESTAMPDIFF(DAY,entry_time,NOW())) WHERE status='OPEN'` | <7d (was 35) |
| Q-V10 | meta_strategy template not in dashboard | dashboard payload count of those rows | unchanged in DB but CRYPTO WR rises 0.32→>0.40 |
| Q-V11 | time-travel filter active | `at_consensus_picks WHERE closed_at < generated_at AND time_travel_flag=FALSE` | = 0 |
| Q-V12 | lm_signals resolver fix | `100*SUM(exit_price=0)/COUNT(*) WHERE status='expired'` | < 5% (was 96.2%) |
| Q-V13 | signal_tier writer | `100*SUM(signal_tier IS NULL)/COUNT(*) WHERE event_type='PICK_POSTED'` | < 5% (was 99.99%) |
| Q-V14 | trading_picks direction unified | `direction NOT IN ('LONG','SHORT')` | = 0 |

---

## Outstanding artifacts

All listed in `reports/db_action_plan_delta_2026-05-08.md` plus this file + `reports/uncharted_tables_recon_2026-05-08.md` + `reports/freeze_2026_04_02_root_cause_2026-05-08.md`.

---

## Decision: Option A vs Option B (per user's section 7)

**Recommend Option A** (Git housekeeping + Wave 0 census today). Reason:
- Without `schema_baseline_2026-05-08.sql`, every Wave 2 schema change is unwindable only via guesswork.
- Wave 0 census is read-only, low-risk, surfaces unknowns before any quarantine.
- The smoking-gun unfreeze is a 1-line `rm` + 1-file edit + 1 cycle wait — fits inside a Wave 0.5 step before the rest of Wave 1.

Proceed: 1.1 → 1.2 → 0-F (OPEN census) → **1.5 unfreeze (delete circuit_breaker_state.json)** → 0-A through 0-G → Wave 1 quarantines.
