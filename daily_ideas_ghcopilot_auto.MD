# DAILY IDEAS - GH COPILOT AUTO

## 2026-05-14 - Prediction System Upgrade Plan

This version restores and expands the file with a concrete roadmap for GitHub Actions plus MySQL reliability work on mysql.50webs.com across:
- ejaguiar1_stocks
- ejaguiar1_backtests

Credential policy (mandatory):
- Never put passwords in code or markdown.
- Use env vars and GitHub Actions secrets only:
  - DB_PASS_STOCKS
  - DB_PASS_BACKTESTS

## Strategic Enhancements To Build

### Enhancement 1 - Cross-DB pick lifecycle integrity gate
What to build:
- A scheduled GitHub Action validating that each pick created in stocks has exactly one valid close state in backtests.
- Checks for orphaned opens, duplicate closes, impossible PnL values, and timestamp-order violations.

Projected benefit:
- Reduces false PF/WR inflation risk by 60-80%.
- Improves trustworthiness of dashboard quality metrics.

### Enhancement 2 - Forward vs backtest drift monitor (asset class + strategy)
What to build:
- Daily divergence job producing forward_wr, backtest_wr, divergence_pp, rolling PF, and sample-size confidence bands.
- Automatic issue creation for classes/strategies breaching divergence thresholds.

Projected benefit:
- Earlier decay detection (typically 7-14 days faster than manual review).
- Lowers time spent running underperforming configurations.

### Enhancement 3 - Schema contract watchdog for both MySQL databases
What to build:
- Nightly schema snapshot to JSON (tables, columns, types, indexes, nullability, defaults).
- Drift diff against version-controlled baseline in schemas/.

Projected benefit:
- Prevents silent breakages from upstream schema changes.
- Cuts emergency break/fix incidents tied to DB changes by about 50%.

### Enhancement 4 - Query performance and index optimization loop
What to build:
- Weekly EXPLAIN audit of top 20 critical queries in audit generation, scoring, and active-pick checks.
- Index recommendation output with before/after latency estimates.

Projected benefit:
- 20-40% reduction in heavy job runtime.
- Lower timeout risk for scheduled GitHub Actions.

### Enhancement 5 - Data freshness SLOs by source and asset class
What to build:
- Hourly freshness checks with RED, YELLOW, GREEN status and hard fail on critical staleness.
- Optional notification hook to ops channel.

Projected benefit:
- Prevents stale-data-driven picks from entering production.
- Improves operational reliability and confidence in live signals.

### Enhancement 6 - Safe migration pipeline with rollback checkpoints
What to build:
- Versioned SQL migrations with preflight checks, backup snapshots, post-migration validation, and automatic stop conditions.

Projected benefit:
- Safer schema evolution and lower probability of production regression.
- Faster recovery when migration validation fails.

### Enhancement 7 - Strategy emission and dormancy monitor
What to build:
- Daily report on picks emitted, score distribution, pnl per pick, and dormant high-quality strategies.
- Flags for over-emitting low-edge strategies.

Projected benefit:
- Better throughput allocation toward stronger edges.
- Prevents quiet strategy death from going unnoticed.

### Enhancement 8 - PR guardrails for SQL and secret hygiene
What to build:
- Pull-request checks for leaked credentials, unsafe SQL patterns, missing env-var references, and migration lint.

Projected benefit:
- Reduces security and data-integrity risks before merge.
- Improves CI signal quality and maintainability.

## Projected Benefits Summary (90-day window)

- Data integrity incidents: down 50-70%.
- False-positive strong-strategy classifications: down 30-50%.
- Mean time to detect strategy decay: down from weeks to days.
- Scheduled workflow reliability: up 15-30%.
- Confidence in asset-class leaderboard decisions: materially higher due to cleaner close-state accounting.

## Implementation Schedule (EST)

Assumptions:
- Start date: 2026-05-14.
- Team executes with stable CI capacity and no major infra outages.
- Institutional quality threshold used in this planning doc:
  - Tier 2 minimum: PF > 1.5, WR > 50%, MDD < 20%, and n >= 100 clean trades.

### Phase 1 - Foundations (Week 1-2)
Time window:
- 2026-05-14 10:00 EST to 2026-05-28 18:00 EST

Deliverables:
- Enhancement 1, 3, and 8 live.
- Baseline integrity dashboards and schema drift issues active.

### Phase 2 - Reliability and speed (Week 3-4)
Time window:
- 2026-05-29 09:00 EST to 2026-06-12 18:00 EST

Deliverables:
- Enhancement 4 and 5 live.
- Freshness SLO failures actionable in under 1 hour.

### Phase 3 - Alpha quality controls (Week 5-8)
Time window:
- 2026-06-13 09:00 EST to 2026-07-10 18:00 EST

Deliverables:
- Enhancement 2 and 7 live.
- Drift and dormancy loops feeding strategy mutation and retraining queue.

### Phase 4 - Stabilization and promotion (Week 9-12)
Time window:
- 2026-07-11 09:00 EST to 2026-08-08 18:00 EST

Deliverables:
- Enhancement 6 live.
- Asset-class promotion decisions based on clean 30, 60, 90-day metrics.

## Projected Institutional-Quality ETA By Asset Class (EST)

These are projected target timestamps for first sustained Tier 2 candidacy under the above assumptions.

- EQUITY: 2026-06-21 17:00 EST
  - Rationale: already near threshold; mostly needs data integrity hardening and drift controls.

- COMMODITY: 2026-07-05 17:00 EST
  - Rationale: PF strength exists; win-rate and consistency should improve with cleaner regime filters and freshness controls.

- BOND: 2026-07-19 17:00 EST
  - Rationale: quality looks promising but sample size must ramp to credible institutional floor.

- ETF: 2026-08-02 17:00 EST
  - Rationale: moderate quality profile; expected to benefit from divergence monitoring and index/query improvements.

- CRYPTO: 2026-09-13 17:00 EST
  - Rationale: large volume but quality drag pockets remain; needs emission discipline plus stronger drift management.

- FOREX: 2026-10-25 17:00 EST
  - Rationale: currently weakest profile; requires full mutate-before-kill cycle plus stricter source governance and cross-validation.

- INDEX: 2026-09-27 17:00 EST
  - Rationale: likely reachable after data freshness and drift loops stabilize signal validity.

- FUTURES: 2026-10-11 17:00 EST
  - Rationale: requires scanner reliability expansion, stable emissions, and sufficient clean sample depth.

## Priority Execution Order

1. Cross-DB pick lifecycle integrity gate
2. Schema contract watchdog
3. PR guardrails for SQL and secret hygiene
4. Data freshness SLOs
5. Query and index optimization loop
6. Forward vs backtest drift monitor
7. Strategy emission and dormancy monitor
8. Safe migration pipeline

## Peer Insights Folded In

Recent protocol traffic added two useful guardrails that reinforce this roadmap:
- multi_asset_cot now has a dedicated DB verifier shipped on main and it explicitly needs DB_PASS_STOCKS at runtime.
- The VIX + YC combined gate landed in PR #960, but it is still default-off and should stay in a 7-day shadow period before any broader rollout.

Practical implication:
- Keep the integrity gate and secret hygiene work first-class so the new verifier and gate can be exercised safely in CI and shadow environments.

## Required Secrets / Environment Variables

Use in GitHub Actions:
- DB_HOST=mysql.50webs.com
- DB_NAME_STOCKS=ejaguiar1_stocks
- DB_NAME_BACKTESTS=ejaguiar1_backtests
- DB_PASS_STOCKS=${{ secrets.DB_PASS_STOCKS }}
- DB_PASS_BACKTESTS=${{ secrets.DB_PASS_BACKTESTS }}

Optional split users:
- DB_USER_STOCKS
- DB_USER_BACKTESTS

## Quick starter prompts for next agent round

- Design a robust cross-database pick lifecycle validator with deterministic mismatch categories.
- Generate a schema drift contract format that is stable and CI-friendly for MySQL.
- Propose per-asset-class drift thresholds tied to sample size and confidence intervals.
- Rank index additions by expected latency reduction for the top 20 audit queries.

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Enhancement Implementation Scorecard

| Enhancement | Status | Notes |
|---|---|---|
| **1 — Cross-DB pick lifecycle integrity gate** | ✅ PARTIAL | `cross-db-audit.yml` ships strategy-key consistency; full orphaned-open + duplicate-close checks not yet in workflow |
| **2 — Forward vs backtest drift monitor** | ✅ SHIPPED | Drift detection in `dashboard_generator.py`; `fwd_vs_bt_divergence.rows` in payload |
| **3 — Schema contract watchdog** | 🔄 OPEN | Not shipped; high value — nightly snapshot in `schemas/` not created |
| **4 — Query performance + index optimization** | 🔄 OPEN | Blocked by MySQL access from GH Actions IP |
| **5 — Data freshness SLOs** | ✅ SHIPPED | `db-freshness-guardian.yml` hourly cron |
| **6 — Safe migration pipeline** | 🔄 OPEN | No versioned SQL migration tooling yet |
| **7 — Strategy emission + dormancy monitor** | 🔄 PARTIAL | `ml_crypto_pred_v12` DEAD flag shipped; no general dormancy cron |
| **8 — PR guardrails for SQL + secret hygiene** | ✅ SHIPPED | `secret-scan.yml` cron; SQL linting via existing CI |

### High-Value Remaining Items

**Enhancement 3 (Schema Contract Watchdog):**
- Pro: Nightly `information_schema` snapshot + diff against baseline catches silent column renames, type changes, index drops before they break dashboard generation.
- Con: Minimal effort (~3h). Only blocker is `DB_PASS_STOCKS` validity in GH Actions.
- **Action:** `tools/db_schema_snapshot.py` → commit to `schemas/` → `.github/workflows/schema-drift-audit.yml` nightly.

**Enhancement 7 (Strategy Dormancy Monitor):**
- Pro: "Silent death" of a strategy is currently invisible until the class WR drops. A daily cron flagging strategies with `last_signal_at > 7 days AND status=ACTIVE` directly prevents DEAD strategies from inflating class stats.
- Con: Requires per-strategy `last_signal_at` field in `dashboard_data.json` systems block (already present).
- **Action:** Add dormancy check to `audit_trail/quality_gates.py`; emit to `alpha_engine/data/ml_health_status.json`.

**VIX+YC combined gate:**
- Shipped as +15 score bonus (was +12). Default ON for EQUITY. Shadow period active.
- Pro insight from this document: "still default-off" — CONFIRMED it is now default ON in `quality_gates.py` line 3834.

### Institutional Quality Projections — Revised (2026-05-16)

| Asset Class | Copilot ETA | Revised ETA | Key Delta |
|---|---|---|---|
| EQUITY | 2026-06-21 | **On track** | T2 confirmed; needs 30d clean rolling |
| COMMODITY | 2026-07-05 | **~2026-07-01** | post-dedup Tier 1; CT=F PROBATION resolves 2026-06-06 |
| BOND | 2026-07-19 | **2026-09-01+** | n=18→200 needs ~60 days at 3/day emission rate |
| ETF | 2026-08-02 | **2026-08-15** | n=107; sector rotation not yet shipped |
| CRYPTO | 2026-09-13 | **2026-09-01+** | M-034 gate + quarantine helps; MEME split still OPEN |
| FOREX | 2026-10-25 | **2026-10-01** | FOREX_HARD_DISABLE active; carry-factor scaffold OPEN |
