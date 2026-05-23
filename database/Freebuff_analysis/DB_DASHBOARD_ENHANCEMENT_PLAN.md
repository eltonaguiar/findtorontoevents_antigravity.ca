# Dashboard Enhancement Plan — Freebuff Analysis

**Date:** 2026-05-08  
**Sources:** Wave 0 Census (`reports/wave0_census_final_2026-05-08.md`), Kimi DB Review (`kimi_db_review/FULL_DATABASE_REVIEW.md`)  
**Target:** `findtorontoevents.ca/audit` + `findtorontoevents.ca/audit/hyrotrader` + infrastructure

---

## Context

Two independent audits converged on the same conclusion: the `ejaguiar1_stocks` MySQL database has critical data quality issues that silently corrupt the signals displayed on both the main audit dashboard and the HyroTrader challenge tracker. This plan maps each finding to a specific, implementable dashboard enhancement with priority, effort estimate, and implementation notes.

---

## Tier 1 — CRITICAL: Data Quality Indicators (Main Audit Dashboard)

These are the highest-impact additions. They surface data corruption that is currently invisible to the user.

### 1.1 PnL Integrity Badge

**Finding:** 58% of sampled closed rows have >1% mismatch between stored `pnl_pct` and recomputed `(exit_price - entry_price) / entry_price × 100`.

**Enhancement:** Add a "PnL Integrity" badge row to the `dashboard_enhancements.js` summary cards area that shows:
- Integrity % (green >95%, yellow 85-95%, red <85%)
- Last checked timestamp
- Row count sampled

**Implementation:**
- Add a new Python script: `tools/db_health_check.py` — runs on cron/hourly, writes `audit_dashboard/data/db_health.json`
- Add a new section to `dashboard_enhancements.js` that reads `db_health.json` via `fetch()` and renders a PnL integrity card
- The script runs `SELECT SUM(CASE WHEN entry_price>0 AND exit_price>0 AND ABS(pnl_pct - ((exit_price-entry_price)/entry_price*100)) > 1 THEN 1 ELSE 0 END) AS mismatches, COUNT(*) AS total FROM (SELECT entry_price, exit_price, pnl_pct FROM bt_backtest_trades WHERE status IN ('WON','LOST','WIN','LOSS') AND pnl_pct IS NOT NULL LIMIT 100000) t` (and the equivalent for `trading_picks`)

**Effort:** ~2h  
**Files to create/modify:**
- NEW: `tools/db_health_check.py`
- NEW: `audit_dashboard/data/db_health.json` (output)
- MODIFY: `audit_dashboard/dashboard_enhancements.js` — add `renderDbHealth()`
- MODIFY: `.github/workflows/audit-dashboard.yml` — add path trigger for `tools/db_health_check.py`

### 1.2 Ghost Row Counter

**Finding:** ~639K constant-PnL ghost rows identified: `quan_engine` MATICUSDT (225,916) + `meta_strategy` template rows (413,112) with synthetic ±3%/+5% PnL.

**Enhancement:** Add a "Signal Authenticity" section to the dashboard that shows:
- Ghost row count per strategy family
- % of total rows that are synthetic/template
- "Clean Ratio" — what % of data is real

**Implementation:**
- Extend `tools/db_health_check.py` to run ghost detection queries:
```sql
SELECT strategy, COUNT(*) AS ghosts
FROM bt_backtest_trades
WHERE pnl_pct IS NOT NULL
GROUP BY strategy, symbol, direction, ROUND(pnl_pct, 4)
HAVING COUNT(*) > 1000 AND COUNT(DISTINCT entry_price) < 5
ORDER BY ghosts DESC LIMIT 20
```
- Render a "Data Authenticity" scorecard in `dashboard_enhancements.js`

**Effort:** ~1.5h  
**Files:** Same as 1.1 (extends existing script and JS)

### 1.3 OPEN Bloat Warning

**Finding:** 26.96M OPEN rows = 90.4% of `bt_backtest_trades`. `information_schema` under-reported by 23x. Forward validator appears frozen.

**Enhancement:** Add a prominent "OPEN Bloat" warning banner (amber/red) that appears when:
- OPEN rows > 50% of total table
- Last WON/LOST write > 24h ago (validator frozen)
- Total rows exceed `information_schema` estimate by >10x

**Implementation:**
- Query in `tools/db_health_check.py`:
```sql
SELECT 
  (SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN') AS open_count,
  (SELECT COUNT(*) FROM bt_backtest_trades) AS total_count,
  (SELECT TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='bt_backtest_trades') AS info_estimate,
  (SELECT TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) FROM bt_backtest_trades WHERE status IN ('WON','LOST')) AS hours_since_last_close
```
- Banner in `dashboard_enhancements.js` above the filter tabs

**Effort:** ~1h  
**Files:** Same as 1.1 (extends existing script and JS)

---

## Tier 2 — HIGH: Asset-Class Data Quality (Main Audit Dashboard)

### 2.1 Phantom EXPIRED Row Detector

**Finding:** 100% of non-crypto EXPIRED rows have pnl_pct=0 AND exit_price=entry_price — 15,744 phantom rows that were never tracked. FOREX, FUTURES, EQUITY, ETF, COMMODITY all affected.

**Enhancement:** Add an "Asset Class Data Quality" table that shows:
- Per asset class: total rows, phantom %, closed-with-PnL %, NULL entry %
- Color-coded: green >90% clean, yellow 70-90%, red <70%

**Implementation:**
- Query in `tools/db_health_check.py`:
```sql
SELECT asset_class,
  COUNT(*) AS total,
  SUM(CASE WHEN status='expired' AND pnl_pct=0 AND exit_price=entry_price THEN 1 ELSE 0 END) AS phantoms,
  SUM(CASE WHEN status IN ('WON','LOST','WIN','LOSS') AND pnl_pct IS NOT NULL THEN 1 ELSE 0 END) AS closed_with_pnl,
  SUM(CASE WHEN entry_price IS NULL OR entry_price=0 THEN 1 ELSE 0 END) AS null_entry
FROM bt_backtest_trades
GROUP BY asset_class
ORDER BY total DESC
```
- New section in `dashboard_enhancements.js` with a compact table

**Effort:** ~1.5h  
**Files:** Same as 1.1 (extends)

### 2.2 Outcome Coverage Gauge

**Finding (Kimi):** Outcome tracking covers only 0.09% of signals (121 outcomes for 136K+ raw picks). `alpha_picks` and `stock_picks` have NO exit tracking columns.

**Enhancement:** Add an "Outcome Coverage" gauge showing:
- % of raw picks that have resolved outcomes
- % of prediction tables with exit tracking
- List of "fire-and-forget" tables (no exit_price column)

**Implementation:**
- Query in `tools/db_health_check.py`:
```sql
SELECT 
  (SELECT COUNT(*) FROM at_raw_picks WHERE exit_price IS NOT NULL AND pnl_pct IS NOT NULL) AS raw_with_outcome,
  (SELECT COUNT(*) FROM at_raw_picks) AS raw_total,
  (SELECT COUNT(*) FROM trading_picks WHERE status IN ('TP_HIT','SL_HIT','CLOSED','WON','LOST')) AS tp_with_outcome,
  (SELECT COUNT(*) FROM trading_picks) AS tp_total
```
- Gauge visualization in `dashboard_enhancements.js`

**Effort:** ~1h  
**Files:** Same as 1.1 (extends)

---

## Tier 3 — MEDIUM: HyroTrader Dashboard Enhancements

### 3.1 ML Training Data Readiness Indicator

**Finding (Kimi):** `ml_feature_store` has ALL NULL targets (396 rows) — cannot be used for supervised ML training. The ML Edge Optimizer (Table 5) on the HyroTrader page may be training on garbage.

**Enhancement:** Add a training data readiness badge to the HyroTrader ML Edge Optimizer card:
- Shows % of feature store rows with non-NULL targets
- Shows training sample count
- Warns when training data is insufficient or corrupted

**Implementation:**
- Add query to `tools/db_health_check.py` for `ml_feature_store` target column NULL ratio
- Modify `audit_dashboard/hyrotrader/index.html` ML card to fetch and display readiness
- OR extend `tools/hyro_ml_pick_optimizer.py` to include `training_data_quality` in its output JSON

**Effort:** ~1.5h  
**Files to modify:**
- `tools/db_health_check.py` — add ml_feature_store check
- `tools/hyro_ml_pick_optimizer.py` — add training_data_quality to output
- `audit_dashboard/hyrotrader/index.html` — render readiness badge

### 3.2 Synthetic Data Flag

**Finding (Kimi):** `goldmine_cursor_predictions` has hardcoded PnL: exactly +5.0% for wins, -3.0% for losses. Every. Single. One.

**Enhancement:** Add a "Data Source Authenticity" column to the HyroTrader signal strength table (Table 4) showing whether performance data comes from:
- Real resolved outcomes
- Goldmine synthetic predictions
- Backtest template rows

**Implementation:**
- Extend `tools/hyro_pick_performance_validator.py` to tag each strategy's data source
- Add a "Source" column with badges: REAL / SYNTHETIC / MIXED
- Color-code: green for real, amber for mixed, red for synthetic-only

**Effort:** ~1.5h  
**Files:**
- `tools/hyro_pick_performance_validator.py` — add source tagging
- `audit_dashboard/hyrotrader/index.html` — render source badges

### 3.3 Signal Count Consistency Check

**Finding:** The HyroTrader QuanEngine bridge can go 16+ days stale (Tier-B #6 fix already added). But there's no cross-reference showing whether the signal counts in the dashboard match what's in the database.

**Enhancement:** Add a "Signal Consistency" card to the HyroTrader page that cross-checks:
- QuanEngine bridge signal count vs `at_consensus_picks` count
- Performance validator signal count vs `at_signal_outcomes` count
- Flags discrepancies > 10%

**Implementation:**
- New section in `tools/hyro_quan_bridge.py` output: `db_consistency` object
- Query `at_consensus_picks` count for matching symbols/timeframe
- Render in hyrotrader page

**Effort:** ~1h  
**Files:**
- `tools/hyro_quan_bridge.py`
- `audit_dashboard/hyrotrader/index.html`

---

## Tier 4 — LOWER: Infrastructure & Performance

### 4.1 DB Index Health Panel

**Finding:** 4 composite indexes missing that would fix all timed-out queries on shared hosting.

**Enhancement:** Add a "DB Performance" panel showing:
- Index health score
- Missing recommended indexes
- Query timeout rate

**Implementation:**
- `tools/db_health_check.py` runs `SHOW INDEX FROM bt_backtest_trades` + checks for recommended composites:
  1. `(status, entry_time)` — for age-bucket queries
  2. `(status, imported_at)` — for freeze detection
  3. `(strategy, symbol, pnl_pct)` — for ghost detection
  4. `(asset_class, status, pnl_pct)` — for phantom detection
- Panel in `dashboard_enhancements.js`

**Effort:** ~1h  
**Files:** Same as 1.1

### 4.2 QuanEngine Bridge Staleness — Already Partially Fixed

**Status:** Tier-B #6 fix (2026-05-04) already added staleness pill to hyrotrader page. Shows age in min/h/d and truncated-symbol warning.

**Remaining gap:** No server-side health check that triggers an alert. The bridge only shows staleness on page load — if nobody visits the page for 3 days, nobody knows it's broken.

**Enhancement:** Add a GitHub Actions health check step that:
- Parses `audit_dashboard/data/hyro_quan_bridge.json`
- If `generated_at` > 3h old, fails the workflow step (amber, not red)
- If `generated_at` > 24h old, fails red
- If symbol count < 10, fails red

**Implementation:**
- New script: `tools/check_quan_bridge_freshness.py`
- Add to `.github/workflows/audit-dashboard.yml` as a pre-deploy check

**Effort:** ~0.5h  
**Files:**
- NEW: `tools/check_quan_bridge_freshness.py`
- MODIFY: `.github/workflows/audit-dashboard.yml`

---

## Tier 5 — STRETCH: New Dashboard Sections

### 5.1 Database Health Dashboard (Standalone Page)

**Rationale:** Currently, all DB health knowledge lives in markdown reports. No live visibility.

**Enhancement:** Create `findtorontoevents.ca/audit/db-health` — a standalone page showing:
- Row counts per major table (live from `information_schema`)
- OPEN bloat % gauge
- PnL integrity score
- Ghost row counts
- Index health
- Last validator write timestamp
- Phantom row % by asset class
- Outcome coverage %
- ML readiness indicator

**Architecture:**
- `tools/db_health_check.py` writes `audit_dashboard/data/db_health.json` (hourly cron)
- NEW: `audit_dashboard/db_health.html` — static HTML + JS that fetches `db_health.json`
- Same dark theme as main audit dashboard
- Linked from main audit nav and hyrotrader page

**Effort:** ~3h  
**Files:**
- NEW: `audit_dashboard/db_health.html`
- NEW: `tools/db_health_check.py` (consolidates all health queries)
- MODIFY: `audit_dashboard/template.html` — add nav link
- MODIFY: `audit_dashboard/hyrotrader/index.html` — add nav link
- MODIFY: `.github/workflows/audit-dashboard.yml` — add path + trigger

### 5.2 Per-Asset-Class Quality Gates Dashboard

**Finding:** Quality gate implementation plan already exists (`updates/2026-05-02-per-asset-quality-gate-implementation-plan.md`). This would surface per-asset-class data quality scores.

**Enhancement:** Add a "Quality Gates" tab/section to the main audit dashboard showing:
- Per asset class: quality score (0-100), phantom %, PnL integrity %, outcome coverage %
- Trust tier: TRUSTED / CAUTION / UNTRUSTED
- Recommendations: which asset classes are safe to trade based on data quality

**Implementation:**
- Extend `tools/db_health_check.py` output
- New section in `dashboard_enhancements.js`
- Uses existing quality gate logic from `updates/2026-05-02-per-asset-quality-implementation-notes.md`

**Effort:** ~2h  
**Files:**
- `tools/db_health_check.py` — add per-asset quality scoring
- `audit_dashboard/dashboard_enhancements.js` — add quality gates section

---

## Implementation Sequence (Recommended Order)

| Wave | Items | Total Effort | Impact |
|------|-------|-------------|--------|
| **A** | 1.1 PnL Integrity + 1.2 Ghost Counter + 1.3 OPEN Bloat + 4.1 Index Health | ~5.5h | CRITICAL: Surfaces data corruption immediately |
| **B** | 2.1 Phantom Detector + 2.2 Outcome Coverage + 5.1 DB Health Page | ~5.5h | HIGH: Per-asset-class visibility + standalone health page |
| **C** | 3.1 ML Readiness + 3.2 Synthetic Data Flag + 3.3 Signal Consistency | ~4h | MEDIUM: HyroTrader-specific quality indicators |
| **D** | 5.2 Quality Gates Dashboard + 4.2 Bridge Freshness Alert | ~2.5h | STRETCH: Full quality gate integration |

**Total:** ~17.5h across 4 waves

### Quick Wins (< 2h total)

If time is extremely limited, these two changes deliver the most value:

1. **`tools/db_health_check.py`** — single script that runs all health queries and writes `db_health.json` (~1h)
2. **PnL Integrity Badge in `dashboard_enhancements.js`** — one new card that shows the 58% mismatch rate (~45min)

These two alone would surface the most critical finding (PnL data is corrupted) to anyone viewing the audit dashboard.

---

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `tools/db_health_check.py` | **NEW** | Consolidated DB health queries → `audit_dashboard/data/db_health.json` |
| `tools/check_quan_bridge_freshness.py` | **NEW** | CI check for stale bridge data |
| `audit_dashboard/data/db_health.json` | **NEW** | Machine-readable DB health payload |
| `audit_dashboard/db_health.html` | **NEW** | Standalone DB health dashboard page |
| `audit_dashboard/dashboard_enhancements.js` | **MODIFY** | Add: PnL integrity, ghost counter, OPEN bloat, index health, quality gates |
| `audit_dashboard/hyrotrader/index.html` | **MODIFY** | Add: ML readiness badge, synthetic data flags, signal consistency card |
| `tools/hyro_ml_pick_optimizer.py` | **MODIFY** | Add `training_data_quality` to output JSON |
| `tools/hyro_pick_performance_validator.py` | **MODIFY** | Add data source tagging (REAL/SYNTHETIC/MIXED) |
| `tools/hyro_quan_bridge.py` | **MODIFY** | Add `db_consistency` cross-check to output |
| `.github/workflows/audit-dashboard.yml` | **MODIFY** | Add path triggers for new scripts |
| `audit_dashboard/template.html` | **MODIFY** | Add nav link to db-health page |

---

## Related Documents

- `reports/wave0_census_final_2026-05-08.md` — Wave 0 census findings with SQL
- `kimi_db_review/FULL_DATABASE_REVIEW.md` — Kimi's comprehensive DB review
- `kimi_db_review/backtests_crossvalidation.md` — Kimi's backtest cross-validation
- `updates/2026-05-02-per-asset-quality-gate-implementation-plan.md` — Quality gates plan
- `updates/2026-05-08-mysql-comprehensive-audit.md` — Initial audit before Wave 0
- `schema-baseline.sql` — 322-table DDL snapshot
