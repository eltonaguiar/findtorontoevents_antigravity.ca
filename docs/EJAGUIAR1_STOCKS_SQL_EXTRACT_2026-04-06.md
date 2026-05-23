# `ejaguiar1_stocks` — SQL extract analysis (Apr 6, 2026)

**Source file:** `C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql`  
**Size:** ~3.92 GiB (4,209,539,011 bytes)  
**Dump tool:** phpMyAdmin 5.2.1  
**Host (export):** `10.123.0.33:3306`  
**Server:** MySQL **8.4.7**  
**Database:** `ejaguiar1_stocks` (utf8mb4 / utf8mb4_0900_ai_ci)

This note is derived from **streaming the dump** (header, all `CREATE TABLE` blocks, and approximate `INSERT` batch statistics). The file is too large to load whole-file in typical editors.

---

## 1. Why the file is huge

Almost all bytes are **`bt_backtest_trades`**: multi-line `INSERT`s with **one tuple per line** and large **`raw_data` JSON**. An early parser that only counted `),(` on a single line reported **~80k** rows — that was **wrong**.

**Updated (2026-04-02):** `tools/analyze_sql_dump_stats.py` now takes  
`max("),(" delimiters, lines starting with `(` inside each INSERT batch)`  
per table (summed across all batches). Spot-check with `SELECT COUNT(*)` after restoring the dump if you need audit-grade counts.

| Table | ~Rows (revised stream count) | Role |
|-------|-----------------------------:|------|
| **`bt_backtest_trades`** | **~3,501,788** | Bulk imported backtest/simulated trades — **drives file size** |
| **`at_filter_log`** | **~598,771** | Gate/filter audit trail |
| **`at_audit_events`** | **~36,635** | Event log + JSON payloads |
| **`at_discord_gate_log`** | **~19,905** | Discord gate diagnostics |
| **`at_raw_picks`** | **~65,154** | Aggregator raw picks |
| **`at_consensus_picks`** | **~7,119** | Consensus layer (smaller than raw — expected) |
| **`alpha_picks`** | **~3,777** | Equity-style scored picks |
| **`algorithms`** | **142** | Strategy catalog |
| `at_strategy_stats` | 0 (empty in this dump) | Rollups may be computed elsewhere |

**Tool:** `python tools/analyze_sql_dump_stats.py "<path-to-dump.sql>"` → TSV to stdout.

---

## 2. Schema families (how to think about the DB)

### A. **Stock alpha / factor pipeline (mostly MyISAM)**

| Table | Purpose |
|-------|---------|
| `algorithms` | Catalog of named strategies (CAN SLIM, factors, “No-Bed-Time”, academic factors, etc.) — **metadata**, not live picks |
| `algorithm_performance` | Rolled-up stats per `algorithm_name` |
| `algorithm_rolling_perf` | Rolling windows (`period` e.g. `30d`, `calc_date`) |
| `alpha_universe` | Universe membership (`ticker`, sector, cap tier, `active`) |
| `alpha_fundamentals` | Per-ticker fundamentals snapshot + `raw_json` |
| `alpha_factor_scores` | Rich factor grid: momentum/quality/value/vol/growth/composite + `factors_json` |
| `alpha_earnings` | EPS actual vs estimate / surprise |
| `alpha_macro` | Daily macro regime row: VIX, SPY, yields, DXY, `regime`, `regime_detail` |
| `alpha_picks` | **Equity-style picks:** `ticker`, `strategy`, `pick_date`, `entry_price`, **`score`**, conviction, horizon, **% TP/SL**, rationale, hashes |
| `alpha_refresh_log` / `alpha_status` | ETL health, counts, `summary_json` |

**Implication:** This is a **parallel** “quant equity” layer: factors + macro + catalog. It aligns with docs like `docs/STOCKS_DATABASE_EDGES_ANALYSIS_2026-04-05.md` / `EDGE_FINDINGS_2026-04-06.md` (non-crypto edge discussion).

### B. **Cross-asset aggregator / audit trail (InnoDB, `at_*`)**

Shared **`asset_class` enum:** `CRYPTO`, `FOREX`, `EQUITY`, `PENNY_STOCK`, `MEMECOIN`, `SPORTS`, `FUTURES`, `ETF`, `COMMODITY`, `UNKNOWN`.

| Table | Purpose |
|-------|---------|
| `at_aggregation_runs` | Run UUID, status, counts, `regime_data` JSON, drawdown snapshot |
| `at_raw_picks` | Ingested signals: `source_system`, `strategy`, prices, `confidence`, **`raw_payload` JSON**, dedup/stale/ban flags, **settlement** (`status`, `pnl_pct`, `closed_at`) |
| `at_consensus_picks` | Merged consensus: `agreement_count`, `source_systems` / `source_strategies` JSON, tiers, Discord ids, outcomes |
| `at_filter_log` | **Why** picks were filtered (`filter_reason`, `details`) — key for debugging gates |
| `at_audit_events` | Generic audit events: `event_type`, `pick_id`, `payload` JSON |
| `at_signal_outcomes` | Simpler outcome ledger (legacy or parallel to raw/consensus) |
| `at_strategy_stats` | Aggregated strategy performance |
| `at_strategy_symbol_performance` | Per-strategy symbol stats (Sharpe, PF, etc.) |
| `at_discord_*` | Gate state, notifications, sent messages |
| `at_sqlite_imports` | Provenance for SQLite → MySQL imports |
| `at_incubator_*` / `at_large_backtest_results` | Incubator / large backtest bookkeeping |
| `at_permutation_*` | Permutation / robustness experiments |
| `at_local_picks` | Local pick buffer vs aggregator |

**Repo link:** `audit_trail/mysql_client.py` documents **`INSERT IGNORE INTO at_raw_picks`** — this schema matches the **live** audit path described in `CHATWITHIT.MD` / `TESTING_PROTOCOL.MD`.

### C. **Legacy / UI backtests (MyISAM)**

| Table | Purpose |
|-------|---------|
| `backtest_results` / `backtest_trades` | Portfolio-level backtest summary + trades (`algorithm_name`, `hold_days`, commissions) |

### D. **Bulk backtest import (InnoDB `bt_*`)**

| Table | Purpose |
|-------|---------|
| `bt_backtest_runs` | Import run metadata: `source_db`, `source_table`, strategy, asset class, headline metrics |
| `bt_backtest_trades` | **Very large** trade-level history: direction, TP/SL, times, `pnl_pct`, **`raw_data` JSON** |

**Implication:** The **~4 GB** dump is **mostly `bt_backtest_trades`** (~3.5M rows of JSON-heavy history), **not** live aggregator volume. For **operational** prediction quality, prioritize **`at_raw_picks` / `at_consensus_picks` / `alpha_picks`** and closed `pnl_pct`. Use **`bt_*`** only when the research question explicitly targets those import runs (`source_db`, `source_table` on `bt_backtest_runs`).

---

## 3. Full per-table stream counts (this extract)

Regenerate anytime:

`python tools/analyze_sql_dump_stats.py "C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql"`

Snapshot from that command (2026-04-02), **sorted by row count (desc)**:

```
3501788  bt_backtest_trades
598771   at_filter_log
65154    at_raw_picks
36635    at_audit_events
19905    at_discord_gate_log
14775    at_discord_notifications
14411    at_aggregation_runs
11752    at_local_picks
7119     at_consensus_picks
4422     audit_log
3777     alpha_picks
2538     algorithm_rolling_perf
2132     alpha_factor_scores
2132     alpha_fundamentals
1614     at_permutation_picks
1581     at_discord_sent
1006     at_incubator_backtest_results
857      at_large_backtest_results
684      audit_trails
536      alpha_refresh_log
410      at_strategy_symbol_performance
304      at_raw_picks_anomaly_log
285      bt_backtest_runs
220      alpha_earnings
209      at_incubator_strategies
165      alpha_macro
142      algorithms
121      at_signal_outcomes
50       backtest_trades
28       at_permutation_snapshots
23       algorithm_performance
2        backtest_results
1        alpha_status
0        at_strategy_stats, at_sqlite_imports, at_discord_gate_state
```

### Next steps — done in repo

| Step | Status |
|------|--------|
| Fix dump row counter for multiline `INSERT` | Done — `tools/analyze_sql_dump_stats.py` |
| Read-only SQL templates for score / filter / consensus analytics | Done — `tools/sql/ejaguiar1_stocks_readonly_analytics.sql` |
| Dashboard JSON score vs `pnl_pct` (Spearman / quintiles) | Run: `python tools/analyze_audit_scores_vs_pnl.py` → `tools/data/score_pnl_analysis.json`. Example (2026-04-02, repo `audit_dashboard/data/dashboard_data.json`): strongest rank correlation was **`elite_score` on recent closed non-crypto** (Spearman ≈ **0.35**); **`smart_score` on crypto** closed ≈ **0.23**. Re-run after refreshing JSON. |

### Next steps — need live DB or SQL restore

1. **`SHOW TABLES`** on `mysql.50webs.com` — confirm extra tables vs this dump (`trading_picks`, `strategy_registry`, etc.).  
2. Run **`SELECT COUNT(*)`** on `bt_backtest_trades` and `at_raw_picks` after import — validate stream counts (~3.5M / ~65k).  
3. Execute §1–§6 queries in `tools/sql/ejaguiar1_stocks_readonly_analytics.sql` (confidence quintiles vs `pnl_pct`, `filter_reason` histogram).  
4. Optional: export a **thin** slice (`WHERE recorded_at >= ... LIMIT` / by `asset_class`) for notebook work so you do not move multi-GB JSON repeatedly.

---

## 4. Evaluation hooks (scores vs outcomes)

| Question | Where to measure |
|----------|------------------|
| Does **`alpha_picks.score`** predict realized edge? | Join `alpha_picks` to a price/outcome source, or export closed picks with `pick_hash` / date + ticker |
| Does **`at_raw_picks.confidence`** or consensus tier predict `pnl_pct`? | Filter `status IN ('WON','LOST','CLOSED')`, rank by confidence / `agreement_count`, compare mean `pnl_pct` |
| Why were good signals dropped? | `at_filter_log` × `at_raw_picks` on `raw_pick_id` / run id |
| Multi-asset parity | Same queries with `asset_class` slice (aligns with `EDGE_FINDINGS` equity vs commodity notes) |

---

## 5. Gaps and optimizations (schema-level)

1. **No single “smart_score” column** in this extract for `at_*` rows — scoring may live in **`raw_payload` JSON** or downstream JSON (`dashboard_data.json`). Extract keys with SQL JSON functions or Python loads.
2. **`bt_*` vs `at_*`**: Different provenance; do not merge without `source_db` / `source_table` discipline.
3. **MyISAM `alpha_*` tables** — no FK/transactions; fine for read-heavy catalogs, risk of partial loads on failure (check `alpha_refresh_log`).
4. **Version drift**: Live `mysql.50webs.com` may have **extra tables** (e.g. `trading_picks`, `strategy_registry` mentioned in repo docs) **not** in this dump — confirm with `SHOW TABLES` on the server.

---

## 6. Related repo artifacts

- `audit_trail/mysql_client.py` — `at_raw_picks` insert shape  
- `live-monitor/api/db_config.php` — `ejaguiar1_stocks` credentials pattern (env on deploy)  
- `EDGE_FINDINGS_2026-04-06.md` — Part 4 MySQL discussion  
- `docs/PREDICTION_DB_SCORING_ANALYSIS_GUIDE_2026-04.md` — JSON vs SQL, Redis envelopes  
- `tools/sql/ejaguiar1_stocks_readonly_analytics.sql` — analytics query templates  
- `tools/analyze_audit_scores_vs_pnl.py` — IC / quintiles on `audit_dashboard/data/dashboard_data.json`  
- **`docs/EJAGUIAR1_STOCKS_EDGE_FEEDBACK_2026-04-08.md`** — P0/P1/P2 **further edge** recommendations from this schema  

---

## Revision log

| Date | Change |
|------|--------|
| 2026-04-02 | Initial analysis from `ejaguiar1_stocks_apr62026_extract.sql` stream parse |
| 2026-04-02 | Multiline INSERT row counting fixed; revised row estimates (~3.5M `bt_backtest_trades`); SQL templates + next-steps checklist |
| 2026-04-08 | Linked edge-feedback memo (`EJAGUIAR1_STOCKS_EDGE_FEEDBACK_2026-04-08.md`) |
