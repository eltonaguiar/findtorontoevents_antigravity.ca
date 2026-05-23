# Uncharted Tables Reconnaissance — 2026-05-08

**DB:** `mysql.50webs.com / ejaguiar1_stocks` (MySQL 8.4.7)
**Mode:** read-only via `audit_trail.mysql_client._create_connection`
**Scope:** table families NOT covered by `reports/db_action_plan_delta_2026-05-08.md` —
memecoin, mutual-fund (mf_/mf2_), goldmine (gm_), penny-stock, crypto-whale (cr_/crypto_whale_), forex-pro (fxp_).
**Reproducer:** `python tools/recon_uncharted_tables.py` + `python tools/recon_followups.py`

Verdict legend: ACTIVE = write within 7d (≥2026-05-01) · STALE = 7–90d ago · DEAD = >90d · SCAFFOLDING = always-empty.

---

## 1. Memecoin family — `meme_*`, `mc_winners`

| Table | Exact rows | Last write | Verdict |
|---|---:|---|---|
| `meme_signals` | 50 | 2026-02-12 22:29:27 | DEAD |
| `meme_signal_results` | 50 | 2026-02-12 22:31:05 | DEAD |
| `meme_ml_models` | 0 | n/a | SCAFFOLDING |
| `meme_ml_predictions` | 0 | n/a | SCAFFOLDING |
| `mc_winners` | 0 | n/a | SCAFFOLDING |

**Schema reality:** column is `coin_symbol` (not `symbol`); there is no `closed_at` column.
The 1m38s ghost-interval test from the earlier deep-dive cannot run against this schema —
those columns don't exist. Resolution lives in `meme_signal_results.resolved_at`, joined by `signal_id`.

**Fixture-pattern confirmation:** `meme_signal_results` first three rows are a textbook canned-fixture trio:
- `meme_20260113_0` outcome=`win`, `profit_loss_pct=45.20`
- `meme_20260114_1` outcome=`win`, `profit_loss_pct=38.50`
- `meme_20260114_2` outcome=`win`, `profit_loss_pct=52.10`

`max_profit_pct` and `max_loss_pct` are NULL on every row → resolver never ran; these are seed data, not realized PnL.
All 50/50 rows were inserted in a 90-second window on 2026-02-12 between 22:28:37 and 22:31:05 (server `CREATE_TIME`/`UPDATE_TIME` straddle that window). Confirms `reports/meme_sports_edge_2026-05-07.md`'s synthetic-fixture claim.

**Verdict:** DEAD/scaffolding bundle. **Do NOT wire to /audit Goal #1.** Flag for archival OR rebuild from scratch with a real resolver before re-enabling. No edge to harvest.

---

## 2. Mutual-fund v1 — `mf_*` (18 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `mf_algo_performance` | 10 | 2026-02-09 17:17:56 | DEAD |
| `mf_algorithms` | 10 | 2026-02-09 (CREATE) | DEAD |
| `mf_audit_log` | 260 | 2026-03-28 21:56:51 | STALE |
| `mf_backtest_results` | 0 | n/a | SCAFFOLDING |
| `mf_backtest_trades` | 0 | n/a | SCAFFOLDING |
| `mf_benchmarks` | 0 | n/a | SCAFFOLDING |
| `mf_category_perf` | 0 | n/a | SCAFFOLDING |
| `mf_comparisons` | 0 | n/a | SCAFFOLDING |
| `mf_fund_picks` | 15 | 2026-02-09 (single batch) | DEAD |
| `mf_funds` | 20 | 2026-02-09 | DEAD |
| `mf_nav_history` | 5,000 | 2026-02-09 05:39:24 | DEAD |
| `mf_portfolios` | 8 | 2026-02-09 05:39:09 | DEAD |
| `mf_report_cache` | 2 | 2026-03-28 21:56:51 | STALE |
| `mf_selections` | 34 | 2026-02-09 | DEAD |
| `mf_simulation_grid` | 0 | n/a | SCAFFOLDING |
| `mf_simulation_meta` | 0 | n/a | SCAFFOLDING |
| `mf_strategies` | 10 | 2026-02-09 | DEAD |
| `mf_whatif_scenarios` | 8 | 2026-02-09 08:41:58 | DEAD |

**Verdict:** DEAD v1 schema. The peer claim of "incomplete v1→v2 migration" is confirmed — v1 tables have not been written to since 2026-02-09 (89 days). v1 was abandoned, not migrated.

## 2b. Mutual-fund v2 — `mf2_*` (15 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `mf2_algo_performance` | 10 | **2026-05-08 12:42:45** | ACTIVE |
| `mf2_audit_log` | 328 | **2026-05-08 12:42:45** | ACTIVE |
| `mf2_algorithms` | 10 | (catalog) | ACTIVE |
| `mf2_backtest_results` | 10 | 2026-02-12 23:45:51 | DEAD |
| `mf2_backtest_trades` | 450 | 2026-02-12 23:45:52 | DEAD |
| `mf2_fund_picks` | 600 | pick_date 2026-03-29 | STALE (40d) |
| `mf2_funds` | 15 | catalog | (catalog) |
| `mf2_nav_history` | 6,860 | 2026-03-29 04:38:36 | STALE (40d) |
| `mf2_portfolios` | 12 | 2026-02-09 | DEAD |
| `mf2_tracked_picks` | 75 | 2026-02-15 (status: 40 open / 35 closed) | DEAD |
| `mf2_tracking_daily` | 3 | 2026-02-15 | DEAD |
| `mf2_tracking_lessons` | 9 | 2026-02-15 | DEAD |
| `mf2_whatif_scenarios` | 2 | 2026-03-29 | STALE |
| `mf2_category_perf` | 0 | n/a | SCAFFOLDING |
| `mf2_comparisons` | 0 | n/a | SCAFFOLDING |

**Schema diff vs v1 (peer claim verified):**
- `mf_nav_history` cols: `ticker`, `nav_price`, `adj_nav`, `change_pct`
- `mf2_nav_history` cols: `symbol`, `nav`, `prev_nav`, `daily_return_pct`
- Only 3 columns shared — these are different tables, not a migration.

**Schema diff vs v1 (picks table):**
- v1 `mf_fund_picks` and v2 `mf2_fund_picks` schemas are nearly identical (12 cols each, both keyed by `symbol`+`algorithm_id`+`pick_date`). v2 added `rationale_json`. v1 has 15 rows; v2 has 600. v2 won.

**Backtest reality:** `mf2_backtest_trades` has `return_pct` like `0.5939%`, `0.5941%` per trade (max_hold exits) — mediocre. 450 trades all from one backtest run (`backtest_id=21`) on 2026-02-12. No subsequent backtests.

**Verdict:** v2 audit_log + algo_performance are still being written today (2026-05-08), but `fund_picks` and `nav_history` froze 2026-03-29. **Pipeline is half-alive: a heartbeat is firing but no new picks/NAVs.** Worth investigating: who owns `mf2_audit_log` writes? Probably a cron heartbeat with a broken pick generator. **Don't wire to /audit until pick/nav generation is unblocked.** Mutual funds are not currently in scope for Goal #1 anyway (no asset class).

---

## 3. Goldmine — `gm_*` (6 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `gm_failure_alerts` | 414 | 2026-04-30 00:23:22 | STALE (8d) |
| `gm_news_sentiment` | 140 | 2026-02-16 18:37:51 | DEAD |
| `gm_sec_13f_holdings` | 2,084 | 2026-03-22 06:17:11 | STALE (47d) |
| `gm_sec_insider_trades` | 714 | **2026-05-08 13:42:04** | **ACTIVE** |
| `gm_system_health` | 272 | 2026-04-30 00:23:22 | STALE (8d) |
| `gm_unified_picks` | 1,846 | 2026-02-16 18:40:20 | DEAD |

**Insider-trades freshness day-by-day:**
2026-05-08:8, 05-07:13, 05-06:23, 05-05:19, 05-01:14, 04-30:8, 04-29:7 — daily SEC Form 4 ingest is alive.

**gm_unified_picks status enum:** sl_hit:664, max_hold:486, tp_hit:363, expired:272, open:61.
With 1846 picks that resolved (only 61 open), this is a **fully-resolved historical dataset** — perfect for backtest analysis. `tp_hit / (tp_hit + sl_hit) = 363/1027 = 35.3% TP rate`. Below 50% — not edge as-is. But it's clean (status enum is real, not all 0-PnL).

**Verdict:** Mixed. SEC insider-trades feed is the only ACTIVE component (Goal #1 candidate as a feature/signal source for EQUITY picks — wire as a **feature input** to existing scorers, not as a separate pick stream). Everything else (`gm_unified_picks`, news_sentiment, 13F holdings, system_health) is STALE/DEAD — `gm_unified_picks` froze the same day as `meme_signals` (2026-02-16) suggesting a coordinated pipeline halt 2026-02-16.

---

## 4. Penny stocks — `penny_*` (3 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `penny_picks` | 1,029 | 2026-04-27 12:40:52 (status: 698 active / 331 closed) | STALE (11d) |
| `penny_picks_daily` | 54 | 2026-04-27 12:40:52 | STALE (11d) |
| `penny_stocks` | 0 | n/a | SCAFFOLDING |

**Schema (40 cols):** rich scoring stack — `composite_score`, `health_score`, `momentum_score`, `volume_score`, `technical_score`, `earnings_score`, `smart_money_score`, `quality_score`, `z_score`, `f_score`, `current_ratio`, `rsi`, `ema_alignment`, `rvol`, `mom_3m`, `mom_6m`, `inst_pct`, `short_pct`, `ann_volatility` — and outcome columns `current_price`, `current_return_pct`, `exit_price`, `exit_date`, `exit_reason`.

**0-pnl phantom check:** `exit_price=0` on 698/698 active rows (expected — picks not yet exited; `current_price` populated normally with only 3 NULL/0 rows out of 1029). **Not a phantom-row pattern like `lm_signals`.**

**Status distribution:** active=698, closed=331 (32% closed rate). Realistic resolution loop. Last cron run 2026-04-27 — picker stopped 11 days ago, similar to the sports-DB pattern noted in MEMORY.md (`reference_sports_db_credentials.md` — "stale page is pick-generator stopped Apr 25, NOT a DB-connection failure").

**Verdict:** STALE but architecturally sound. The cron generator is likely down (same pattern as sports). **High-priority candidate for /audit Goal #1 EQUITY** — 1,029 resolved penny-stock picks with rich features could lift EQUITY n=421 → ~1,400, easily over the n=1,000 charter floor. **First step: find why the cron stopped on 2026-04-27 and rerun.** Then wire `penny_picks` into the EQUITY asset_class_health aggregator.

---

## 5. Crypto whale — `crypto_whale_*` + `cr_*` (2 + 18 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `crypto_whale_movements` | 0 | n/a | SCAFFOLDING |
| `crypto_whale_wallets` | 0 | n/a | SCAFFOLDING |
| `cr_pair_picks` | 952 | **2026-05-07 (server UPDATE_TIME 23:53:01)** | **ACTIVE** |
| `cr_price_history` | 4,529 | **2026-05-07 23:53:06** | **ACTIVE** |
| `cr_audit_log` | 393 | **2026-05-07 23:53:06** | **ACTIVE** |
| `cr_algo_performance` | 8 | **2026-05-08 06:23:27** | **ACTIVE** |
| `cr_algorithms` | 8 | catalog | (catalog) |
| `cr_pairs` | 10 | catalog | (catalog) |
| `cr_portfolios` | 10 | 2026-02-09 | DEAD |
| `cr_whatif_scenarios` | 3 | 2026-03-28 | DEAD |
| `cr_backtest_results` | 0 | n/a | SCAFFOLDING |
| `cr_backtest_trades` | 0 | n/a | SCAFFOLDING |
| `cr_category_perf` | 0 | n/a | SCAFFOLDING |
| `cr_comparisons` | 0 | n/a | SCAFFOLDING |
| `crypto_assets` | 14 | 2026-02-14 | DEAD (catalog) |
| `crypto_exchange_netflow` | 20 | 2026-02-16 | DEAD (all-zero netflow values — fixture) |
| `crypto_indicators` | 0 | n/a | SCAFFOLDING |
| `crypto_ohlcv` | 0 | n/a | SCAFFOLDING |
| `crypto_patterns` | 0 | n/a | SCAFFOLDING |
| `crypto_signals` | 0 | n/a | SCAFFOLDING |

**`crypto_whale_*` (long-prefix):** the whale-movements/wallets pair is empty scaffolding — never built.

**`cr_pair_picks` schema (14 cols):** `symbol, algorithm_id, algorithm_name, pick_date, pick_time, entry_price, direction, score, rating, risk_level, timeframe, pick_hash, rationale_json` — **NO outcome columns** (`exit_price`, `pnl_pct`, `status`, `exit_date` all absent). This is an **idea-stream-only** table — entries get inserted, nothing resolves them. Pure pick generator.

**Symbols:** sample shows BTCUSD with `algorithm_name='CR Halving Cycle'` and `'CR Trend Following'`. Generic crypto, not whale-tracking despite the prefix.

**Verdict:** ACTIVE pick stream, but **no resolver — every pick is unresolved forever**. Wiring to /audit would require either (a) writing a resolver that marks status / pnl_pct against `cr_price_history` (4,529 rows, also active), or (b) joining `cr_pair_picks → cr_price_history` at read time to derive outcome. **Medium-priority Goal #1 candidate for CRYPTO** — 952 resolved-via-join picks could help dilute the `quan_engine` 18% drag noted in CLAUDE.md, BUT only if join-resolution shows real edge. Audit before wiring.

---

## 6. Forex pro — `fxp_*` (12 tables)

| Table | Rows | Last write | Verdict |
|---|---:|---|---|
| `fxp_pair_picks` | 1,184 | **2026-05-07 23:51:58** | **ACTIVE** |
| `fxp_price_history` | 2,658 | **2026-05-07 23:52:01** | **ACTIVE** |
| `fxp_audit_log` | 380 | **2026-05-07 23:52:01** | **ACTIVE** |
| `fxp_algo_performance` | 8 | **2026-05-08 06:23:49** | **ACTIVE** |
| `fxp_algorithms` | 8 | catalog | (catalog) |
| `fxp_pairs` | 8 | catalog | (catalog) |
| `fxp_portfolios` | 10 | 2026-02-09 | DEAD |
| `fxp_whatif_scenarios` | 3 | 2026-02-16 | DEAD |
| `fxp_backtest_results` | 0 | n/a | SCAFFOLDING |
| `fxp_backtest_trades` | 0 | n/a | SCAFFOLDING |
| `fxp_category_perf` | 0 | n/a | SCAFFOLDING |
| `fxp_comparisons` | 0 | n/a | SCAFFOLDING |

**Schema:** identical idea-stream pattern as `cr_pair_picks` — 13 cols, NO outcome columns, NO status enum. Sample row: EURUSD LONG @ 1.0845, score 82, "FX Trend Following". Mirrors the cr_ generator.

**Verdict:** ACTIVE pick stream. **Same wiring caveat as cr_pair_picks — no resolver exists.** Highest leverage point given CLAUDE.md's "FOREX is genuinely sub-floor (PF 0.27 / WR 46.4% / n=1169 post-noise)" — adding 1,184 fxp_pair_picks to the FOREX pool could **double the n** AND test whether a fresh idea-source (CR/FX algorithms) outperforms the existing FOREX strategies. But only AFTER applying the mutate-before-kill protocol; do NOT promote blindly to live picks.

---

## Highest-Priority Findings (Top 5)

1. **`gm_sec_insider_trades` is the only quietly-active feature feed** — 714 rows, 8 fresh today, daily Form-4 ingest from SEC. Wire as a **scoring feature** (insider-buy density → equity confidence boost), NOT as a pick stream. Lift candidate for the EQUITY n=421 path. Already 47/47 days fresh in last week.

2. **`penny_picks` (1,029 rows, 698 active, 331 closed) cron stopped 2026-04-27** — same "pick generator died but DB connection works" pattern as sports. Restoring the cron unlocks the largest dormant EQUITY backlog (~1,000 rows w/ 40-col scoring schema). Highest leverage Goal #1 win.

3. **`fxp_pair_picks` (1,184 rows) and `cr_pair_picks` (952 rows) are ACTIVE but resolver-less idea streams** — every pick written, none resolved. FOREX especially urgent given the PF 0.27 sub-floor diagnosis. Build a join-time resolver against the corresponding `_price_history` tables before wiring; otherwise these inflate counts without truth-grade outcome data.

4. **Memecoin family is confirmed dead synthetic fixtures** — 50/50 rows, three canned wins (45.20%, 38.50%, 52.10%), all NULL on `max_profit_pct`/`max_loss_pct`, frozen 2026-02-12. Flag for archival. Do NOT cite these in any /audit performance number. The `meme_ml_models` and `meme_ml_predictions` tables are empty scaffolding — never built.

5. **Mutual-fund v1→v2 was an abandonment, not a migration** — completely different schemas (`ticker`/`nav_price` vs `symbol`/`nav`, only 3 of 7 cols shared). v2 is half-alive: heartbeat firing on `mf2_audit_log` (2026-05-08), but `mf2_fund_picks` and `mf2_nav_history` froze 2026-03-29 (40-day pick-generator outage). Mutual funds are out of scope for Goal #1 (no asset class) — flag the v1 family for archival; investigate v2 cron only if mutual funds re-enter scope.

## /audit Goal #1 Disposition

**WIRE to /audit (Goal #1):**
- `gm_sec_insider_trades` → EQUITY scoring feature (`insider_buy_pressure`).
- `penny_picks` (after cron restart) → EQUITY pick stream, asset_class_health aggregator.
- `cr_pair_picks` (after building price_history-join resolver) → CRYPTO pick stream candidate.
- `fxp_pair_picks` (after building price_history-join resolver) → FOREX pick stream rescue candidate.

**FLAG FOR ARCHIVAL:**
- All `meme_*` + `mc_winners` (synthetic fixtures, never resolved).
- All `mf_*` v1 (abandoned schema, 89-day write gap).
- `crypto_whale_movements`, `crypto_whale_wallets` (empty scaffolding).
- `crypto_signals`, `crypto_ohlcv`, `crypto_indicators`, `crypto_patterns` (empty scaffolding).
- `cr_/fxp_/mf2_` SCAFFOLDING children: `*_backtest_results`, `*_backtest_trades`, `*_category_perf`, `*_comparisons` (always empty).
- `gm_unified_picks`, `gm_news_sentiment`, `gm_sec_13f_holdings` (frozen 2026-02-16 / 2026-03-22).
- `crypto_exchange_netflow` (20 rows, all `0E-8` netflow values — fixture seed).

**INVESTIGATE (don't archive yet):**
- `mf2_fund_picks` / `mf2_nav_history` cron — heartbeat alive but pick generation dead 40+ days. Out of Goal #1 scope but worth noting for any future MF push.
- `gm_failure_alerts` / `gm_system_health` — 8-day staleness suggests a watchdog that itself stopped. Could be the meta-signal that explains other freezes.

---

## Reproduction

```bash
python tools/recon_uncharted_tables.py > .tmp_recon_out.json
python tools/recon_followups.py > .tmp_recon_fu.json
```

Both scripts are read-only; they set `MAX_EXECUTION_TIME=120000` per session and use `audit_trail.mysql_client._create_connection`. Output JSON is gitignored at the repo root via `.tmp_recon_*` prefix.

— recon by Claude Opus 4.7 (1M ctx), peer id `gm68eya5`-window
