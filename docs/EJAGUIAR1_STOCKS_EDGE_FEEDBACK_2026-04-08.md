# `ejaguiar1_stocks` SQL extract — feedback & further edge (Apr 2026)

**Reviewed dump:** `C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql` (~3.92 GiB, MySQL 8.4.7, phpMyAdmin)  
**Schema inventory & row-scale context:** `docs/EJAGUIAR1_STOCKS_SQL_EXTRACT_2026-04-06.md`  
**Read-only query starters:** `tools/sql/ejaguiar1_stocks_readonly_analytics.sql`  
**Repo wiring:** `audit_trail/mysql_client.py` (`at_raw_picks`, consensus, etc.)

This memo is **feedback on where incremental edge can come from** in *data + process*, not a re-spec of every column.

---

## 1. What the database is good for (use as-is)

| Area | Edge lever |
|------|------------|
| **`at_raw_picks` (~65k rows)** | Join **`confidence`**, **`strategy`**, **`asset_class`**, settlement **`pnl_pct`** / **`status`** with **`raw_payload` JSON** — feature store for calibration and “what we actually ran.” |
| **`at_consensus_picks` (~7k)** | **`agreement_count`**, **`source_systems` JSON**, **`consensus_tier`** vs **`pnl_pct`** — empirical value of multi-system agreement (aligns with audit “SMART / consensus” narrative). |
| **`at_filter_log` (~599k)** | **Largest operational signal in the dump.** Mine **`filter_reason`** × outcomes of *nearby* picks (same run / symbol / time window) to see if gates **remove winners** systematically or correctly drop noise. |
| **`alpha_*` + `alpha_picks` (~3.8k picks)** | Factor grid (`alpha_factor_scores`), macro (`alpha_macro`), **`alpha_picks.score`** vs realized outcomes — equity-style edge separate from crypto JSON dashboard. |
| **`bt_backtest_trades` (~3.5M)** | Research sandpit: **do not** mix naïvely with `at_*` live ledger; use **`bt_backtest_runs.source_db` / `source_table`** for provenance-aware studies (regime/strategy priors). |

---

## 2. High-impact gaps → further edge

### P0 — Close the loop with the audit stack

1. **No `smart_score` / gate tier in this schema** — live ranking lives in Python (`quality_gates.py`) and **`dashboard_data.json`**. **Edge:** persist **`smart_score`** (and optional tier) on insert/update for `at_raw_picks` / `at_consensus_picks` so MySQL and dashboard can be reconciled without export-only analysis.
2. **`at_strategy_stats` empty in extract** — rollups are high-leverage for **dynamic bans** (see `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_2026-04-07.md`). **Edge:** cron-fill from closed `at_raw_picks` + same definitions as `strategy_performance.json`.
3. **Live DB drift** — repo mentions **`trading_picks`**, **`strategy_registry`**; this dump has **37** tables. **Edge:** `SHOW TABLES` on `mysql.50webs.com` and document mapping; avoid building queries only against an old extract.

### P1 — Extract signal from JSON columns

4. **`raw_payload` (at_raw_picks)** — keys likely mirror pick metadata. **Edge:** MySQL 8 `JSON_TABLE` / generated columns for 3–5 stable features (e.g. RR, regime flags) + periodic export to Python for IC vs `pnl_pct`.
5. **`bt_backtest_trades.raw_data`** — same idea at scale: **sampling** + clustering by strategy/asset to find **overfit vs structural** subsets before any weight touches live gates.
6. **`at_audit_events.payload`** — sequence mining (event types before WON vs LOST) for **operational** edge (aggregator bugs, stale feeds).

### P2 — Factor + macro layer (equity path)

7. **Join `alpha_picks` → `alpha_factor_scores` / `alpha_macro` on ticker + date** — test whether **composite_factor** or **regime** slices improve hit rate; feed results back into **non-crypto** weights (elite already ranks better off-crypto in dashboard studies).
8. **`algorithm_rolling_perf`** — align rolling windows with **walk-forward** rules in `HEDGE_FUND_ENHANCEMENT_PLAN.md` so DB metrics and promotion gates use the **same** horizon labels.

### Process / science

9. **Filter log A/B narrative** — stratify `at_filter_log` by **`aggregation_run_id`** and compare **forward** outcomes of filtered vs accepted cohorts (with time alignment caveats). **False negative rate** on filters = direct P&L leakage.
10. **Confidence calibration** — dashboard work shows **weak** confidence–PnL link in places; use **`at_raw_picks`** NTILE queries (see SQL file) **by `source_system` × `asset_class`** to recalibrate or down-weight.

---

## 3. Risks to avoid

- **Joining `bt_*` to `at_*` without `source_*` keys** — spurious “alpha.”  
- **MyISAM `alpha_*` partial loads** — check `alpha_refresh_log` after ETL failures.  
- **Treating phpMyAdmin export as production truth** — refresh extracts or query live read-only for decisions.

---

## 4. Suggested next artifacts (repo)

| Deliverable | Purpose |
|-------------|---------|
| `tools/sync_dashboard_scores_to_mysql.md` or small job | Spec to add `smart_score` / tier columns + upsert path |
| `tools/sql/ejaguiar1_filter_log_outcome_analysis.sql` | Filter reason vs counterfactual cohort (template) |
| Monthly **row-count + checksum** job vs `analyze_sql_dump_stats.py` | Detect silent sync drift |

---

## 5. Redis bus

Topic **`EJAGUIAR1_STOCKS_EDGE_FEEDBACK`** — publish with `python tools/bus_post_ejaguiar1_stocks_edge_feedback.py` (example post **2026-04-06T21:34:38Z**).

---

## Revision

| Date | Author | Notes |
|------|--------|--------|
| 2026-04-08 | cursor-composer | Edge-focused feedback from Apr 6 2026 extract + repo alignment |
