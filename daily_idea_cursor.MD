# DAILY IDEA CURSOR

## 2026-05-14 — Cursor suggestions (GitHub Actions + MySQL edge pipeline)

Focus for this idea set: improve prediction-system reliability and edge-detection speed by tightening CI/CD gates and database quality controls around:

- Host: `mysql.50webs.com`
- Databases: `ejaguiar1_stocks`, `ejaguiar1_backtests`
- Secrets from Windows env vars: `DB_PASS_STOCKS`, `DB_PASS_BACKTESTS`

---

## 1) Add a "DB Freshness Guardian" GitHub Action

Create a scheduled workflow that checks stale tables per database and fails when core tables stop updating for too long.

Suggested checks:
- `ejaguiar1_stocks`: recent inserts/updates for live picks, active picks, and resolver outputs
- `ejaguiar1_backtests`: recent writes for backtest runs and summary tables
- Alert thresholds by table class (fast-moving vs slow-moving)

Why this matters:
- Catches silent pipeline stalls before `/audit` drifts out of sync with reality.

---

## 2) Build a "Schema Drift Audit" workflow

Nightly job to snapshot `information_schema` metadata and diff against a committed baseline.

Suggested outputs:
- Added/removed columns
- Type changes (e.g., float -> varchar regressions)
- Index drift (missing or altered indexes on hot query paths)

Why this matters:
- Prevents subtle regressions where jobs still run but model features degrade.

---

## 3) Add cross-database consistency checks

Implement a workflow that compares strategy/system keys across both DBs and flags mismatches.

Examples:
- Strategy exists in backtests but never appears in live-tracking tables
- Asset-class label mismatch (`CRYPTO` vs `UNKNOWN`) between DBs
- Time-window mismatch between backtest and forward tables

Why this matters:
- Stops "false confidence" from backtests that are disconnected from production emissions.

---

## 4) Introduce SQL-based asset-class anomaly detectors

Run anomaly queries daily and publish a markdown summary artifact.

Suggested detectors:
- Sudden WR/PF jumps caused by tiny sample size
- Symbol-to-asset-class misclassification
- Duplicate pick IDs or duplicated close events
- Unusually high unresolved-pick age

Why this matters:
- Gives a practical early-warning system for data-quality bugs that can look like edge.

---

## 5) Add a "stale model / stale strategy" CI gate

Use DB + file timestamps to detect active workflows with stale model artifacts or dormant emitters.

Suggested gate rules:
- Workflow still runs but no new strategy emissions in N days
- Model expected to retrain but artifact age exceeds policy
- High-score model with deteriorating realized outcomes (decay alert)

Why this matters:
- Keeps AI pipelines from silently becoming historical artifacts.

---

## 6) Add a "query performance budget" workflow

Benchmark key SQL queries used by dashboard generation and gating logic.

Suggested checks:
- Query runtime p95 threshold
- Explain-plan index usage on top 10 queries
- Regression fail when runtime crosses budget

Why this matters:
- Prevents dashboard/update lag and keeps Actions jobs inside reliable runtime windows.

---

## 7) Add deterministic backtest reproducibility checks

Run a small pinned-symbol/pinned-window backtest subset daily in Actions and compare to reference outputs.

Suggested outputs:
- Diff report for WR/PF/PNL deltas vs baseline
- Hard fail on unexplained delta above tolerance

Why this matters:
- Catches accidental logic changes in strategy evaluation code before they pollute performance history.

---

## 8) Build a "DB connection preflight" utility for workflows

Create a shared script used by all Actions jobs before heavy tasks begin.

Checks:
- Host reachable: `mysql.50webs.com`
- Correct DB selected (`ejaguiar1_stocks` or `ejaguiar1_backtests`)
- Password env var present (`DB_PASS_STOCKS` / `DB_PASS_BACKTESTS`)
- Read/write smoke query succeeds

Why this matters:
- Fast-fails misconfigured runs and reduces noisy post-failure debugging.

---

## 9) Add score-confidence calibration tracking in SQL

Persist bins of predicted confidence vs realized outcomes and track calibration drift over time.

Suggested use:
- If confidence inverts (higher confidence -> lower win rate), automatically demote or quarantine that model family.

Why this matters:
- Directly targets one of the most expensive failure modes: confident but wrong picks.

---

## 10) Ship a weekly "edge reliability" report workflow

Generate one artifact that combines:
- Asset-class PF/WR by recent window and lifetime
- Top systems by robustness (not just peak PF)
- Drawdown + unresolved-risk snapshots
- Data freshness + schema drift status

Why this matters:
- Gives one decision surface for "deploy / shadow / pause" each week.

---

## Implementation order (recommended)

1. DB connection preflight (Idea 8)
2. DB freshness guardian (Idea 1)
3. Schema drift audit (Idea 2)
4. Cross-database consistency (Idea 3)
5. Weekly edge reliability report (Idea 10)
6. Reproducibility + calibration gates (Ideas 7 + 9)

This order yields the fastest reduction in silent failures while improving trust in per-asset-class edge claims.

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Shipped vs. Open — Cursor Idea Scorecard

| Idea | Status | Notes |
|---|---|---|
| **Idea 1 — DB Freshness Guardian** | ✅ SHIPPED | `.github/workflows/db-freshness-guardian.yml` hourly cron live |
| **Idea 2 — Schema Drift Audit** | 🔄 OPEN | No workflow found yet; high value |
| **Idea 3 — Cross-DB Consistency** | ✅ SHIPPED | `.github/workflows/cross-db-audit.yml` daily cron live |
| **Idea 4 — SQL Anomaly Detectors** | 🔄 OPEN | `tools/mysql_prediction_anomaly_scanner.py` not yet shipped |
| **Idea 5 — Stale Model/Strategy Gate** | 🔄 OPEN | No dormancy monitor yet |
| **Idea 6 — Query Performance Budget** | 🔄 OPEN | Index audit blocked (MySQL access from current IP) |
| **Idea 7 — Backtest Reproducibility** | 🔄 OPEN | High value; no implementation yet |
| **Idea 8 — DB Connection Preflight** | ✅ PARTIAL | Connectivity smoke-test exists; shared module not standardized |
| **Idea 9 — Score-Confidence Calibration** | 🔄 OPEN | `at_confidence_calibration` table not yet created |
| **Idea 10 — Weekly Edge Reliability Report** | ✅ SHIPPED | `tools/filter_generator.py` + `reports/weekly_filter_*.md` via money-maker-readyv2 skill |

### High-Value Remaining Items

**Schema Drift Audit (Idea 2) — Highest Remaining Value**
- Pro: Silent schema changes have caused prior production breakages. A nightly snapshot + drift diff against a committed baseline in `schemas/` catches regressions before the dashboard generator fails.
- Con: Requires MySQL `information_schema` access from GH Actions; `DB_PASS_STOCKS` secret must be valid. Low coding effort (~2h) once secrets confirmed.
- **Action:** Ship `.github/workflows/schema-drift-audit.yml` calling `tools/db_schema_snapshot.py`; commit baseline to `schemas/ejaguiar1_stocks_baseline.json`.

**Score-Confidence Calibration (Idea 9) — Directly Impacts Real Money**
- Pro: CRYPTO/ETF confidence inversion is confirmed (ρ negative). An `at_confidence_calibration` table with bucket-level `actual_wr` vs `expected_wr` makes the inversion visible in the dashboard and auto-quarantines on `calibration_gap < -50pp`.
- Con: Requires `at_pick_outcomes` table first (blocked by `DB_PASS_BACKTESTS` GH secret).
- **Action (blocked on user):** Add `DB_PASS_BACKTESTS` GH secret → then ship `at_confidence_calibration` table + cron.

**SQL Anomaly Detectors (Idea 4) — Medium Priority**
- Pro: Catches inverted confidence, direction conflicts, silent-dead strategies via direct SQL query rather than JSON parsing. No new dependencies.
- Con: Low urgency since daily `dashboard_data.json` already surfaces most anomalies.
- **Action:** Ship `tools/mysql_prediction_anomaly_scanner.py` with 4 query classes; add to weekly edge report.

**Enhancements A-D (§5 bottom section)**
- Model registry metadata (`trained_at`, `feature_set_version`): Pro: essential for decay detection. Con: requires `at_model_registry` table + backfill.
- Drawdown-based throttle policy: Pro: already partially enforced via hedge_fund_quality_gate MDD checks. Con: not yet per-system throttle.
- Per-class min-sample gates before promotion: ✅ ALREADY ENFORCED via `quality_gates.py` charter floors.

### Critical Blocker (User Action Required)
`DB_PASS_BACKTESTS` is not confirmed in GitHub secrets. This single missing secret blocks Ideas 2 (partially), 9, and the `at_pick_outcomes` + `at_predictor_scorecard` tables. **Estimated unblock value: 4 P0/P1 items.**

---

## Enhancement package to include in next execution cycle

### A) Reliability enhancements
- Add workflow-level retry + timeout templates for DB-dependent jobs.
- Add a shared MySQL connector module for Actions jobs so all workflows use the same auth + failover behavior.
- Add an "artifact contract" check so dashboard jobs fail when expected JSON payload keys are missing.

### B) Data-quality enhancements
- Add canonical symbol + asset-class mapping table and validate every ingest against it.
- Add unresolved-pick watchdog (`age > SLA`) to prevent stale open-position bias in class stats.
- Add duplicate resolver protection with deterministic idempotency keys.

### C) Model-governance enhancements
- Add model registry metadata (`trained_at`, `feature_set_version`, `expected_refresh_hours`).
- Add confidence calibration report per model and per asset class.
- Add automatic probation tier when forward divergence exceeds policy threshold.

### D) Execution/risk enhancements
- Add per-class minimum sample-size gates before promoting any strategy.
- Add cross-class correlation cap alerts before portfolio concentration grows.
- Add drawdown-based throttle policy to reduce emissions from decaying systems.

---

## Projected benefits (if package is implemented)

- **Incident reduction:** 40-60% fewer silent pipeline failures from stale tables/schema drift.
- **Detection speed:** anomaly-to-alert latency reduced from days to <1 hour on scheduled workflows.
- **Data trust:** 70%+ reduction in asset-class mislabel and duplicate-resolution incidents.
- **Model quality:** faster decay detection, expected 15-25% reduction in "high-confidence wrong picks."
- **Operational efficiency:** fewer manual triage cycles; expected 4-6 engineering hours saved weekly.
- **Decision clarity:** weekly edge report provides one consistent go/no-go surface for deployment.

---

## Institutional-quality target definition

For this schedule, "institutional quality" means all of:
- Sustained forward performance at or above class thresholds (PF > 1.5, WR > 50%, controlled drawdown)
- Minimum statistically meaningful sample (`n >= 200` closed picks for active class strategies)
- Stable CI/data pipeline (freshness + schema + drift monitors all green for 4 consecutive weeks)
- No unresolved critical data-integrity issues in `ejaguiar1_stocks` or `ejaguiar1_backtests`

---

## Delivery schedule (EST)

Project start baseline: **2026-05-15 09:00 EST**

### Phase timeline
- Phase 1 (platform hardening): 2026-05-15 09:00 EST -> 2026-05-22 18:00 EST
- Phase 2 (data and schema controls): 2026-05-23 09:00 EST -> 2026-06-05 18:00 EST
- Phase 3 (model governance + calibration): 2026-06-08 09:00 EST -> 2026-06-26 18:00 EST
- Phase 4 (forward validation + class promotion gates): 2026-06-29 09:00 EST -> 2026-08-14 18:00 EST

### Projected institutional-quality ETA by asset class (EST)

These ETAs assume the enhancement package above is delivered on schedule and no critical external-data outages occur.

| Asset Class | Current Read (relative) | Projected Institutional ETA (EST) | Reasoning |
|---|---|---|---|
| COMMODITY | strongest edge base | **2026-07-24 17:00 EST** | already near target profile; needs governance + sustained forward sample |
| EQUITY | close to target | **2026-08-07 17:00 EST** | needs stronger live consistency and calibration stability |
| CRYPTO | mixed (high variance) | **2026-09-04 17:00 EST** | needs confidence-inversion fixes + concentration control |
| ETF | borderline | **2026-09-18 17:00 EST** | requires higher sample size and robust forward consistency |
| BOND | thin sample | **2026-10-16 17:00 EST** | main blocker is sample accumulation and stable emission cadence |
| FOREX | stressed | **2026-11-13 17:00 EST** | requires strategy rehab + stricter drift controls before promotion |
| FUTURES | near-silent/dead | **2026-12-11 17:00 EST** | requires emitter revival plus minimum-sample qualification period |

---

## Practical milestone checkpoints

- **2026-05-22 18:00 EST:** all DB preflight/freshness checks active in Actions.
- **2026-06-05 18:00 EST:** schema drift + cross-DB consistency checks enforced.
- **2026-06-26 18:00 EST:** model registry + calibration reports available per asset class.
- **2026-08-14 18:00 EST:** first full 4-week institutional-readiness audit window complete.

---

## Cross-agent insight addendum (2026-05-14 23:24 EST poll)

Peer broadcast surfaced additional high-priority items that should be integrated into this plan:

1. Resolve large unresolved-pick backlog (resolver gap) as a reliability blocker.
2. Enforce hard kill/probation on confirmed toxic high-volume crypto strategy sources.
3. Complete migration hygiene so backtest data is canonical in `ejaguiar1_backtests`.

### Incorporation into roadmap

- Add resolver-gap burn-down metric to weekly edge report (`open_unresolved_count`, aged unresolved buckets).
- Add strategy toxicity gate criteria (PF floor + WR floor + minimum sample) with mandatory quarantine action.
- Add post-migration parity checks between `ejaguiar1_stocks` and `ejaguiar1_backtests` during transition windows.

### Expected impact from addendum

- Faster closure velocity on unresolved picks improves class-level metric integrity.
- Lower risk of class-wide drag from known toxic emitters.
- Cleaner separation of live vs backtest datasets, reducing analysis contamination.

---

## Cross-agent insight addendum (2026-05-14 23:31 EST poll)

New peer `SESSION_SUMMARY` highlighted operational items that should be folded into this roadmap immediately:

1. Prioritize a drift-freshness gate in dashboard generation (prevent stale walk-forward/drift snapshots from appearing production-ready).
2. Treat `hf_quality_gates.json` as canonical gate-policy source and keep `per_asset_thresholds.json` explicitly non-canonical unless fully re-wired.
3. Clear stale GitHub Actions failures tied to submodule hygiene and rotated DB credentials.

### Incorporation into roadmap

- Add drift-freshness guardrails to CI and dashboard-publish prechecks.
- Add a "canonical-policy parity" test lane that fails on policy-source drift.
- Add explicit GHA maintenance tasks:
  - Sync-state/submodule integrity check
  - Backfill workflow secret validation for `DB_PASS_STOCKS` / `DB_PASS_BACKTESTS`
  - Failed-run rerun protocol after gating fixes land

### Expected impact from this second addendum

- Reduces false-positive confidence from stale risk payloads.
- Prevents configuration drift between intended policy and runtime behavior.
- Improves CI reliability and keeps database workflows executable after credential rotations.
