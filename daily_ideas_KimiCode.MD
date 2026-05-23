# Daily Ideas — KimiCode Prediction System + MySQL + GitHub Actions

**Date:** 2026-05-14  
**Scope:** Prediction pipeline hardening, MySQL performance, GitHub Actions reliability  
**Databases:** `ejaguiar1_stocks`, `ejaguiar1_backtests` @ `mysql.50webs.com`  
**Credentials:** `DB_PASS_STOCKS`, `DB_PASS_BACKTESTS` (Windows env)  
**Source context:** `DAILY_IDEAS.MD` + swarm-consolidated audit plan + live MySQL schema audit

---

## Peer Insights & Revision Notes

**Revision date:** 2026-05-15
**Peer reviewer:** `claude-desktop-081g9oh` (cross-PC broadcast `08ca1bb7-09d0-4cd5-9e16-6df72a67bbd0`)
**Status:** REVISED per swarm consensus and live audit findings.

### Key peer findings incorporated

| Finding | Impact on this plan | Action taken |
|---------|---------------------|--------------|
| **PR #1017-1020 CLOSED** by 3-engine swarm consensus (Wire-Up violation / Stage H breach) | Mega-PR approach rejected; sub-PR split required | Critical path rewritten; dates shifted +14-21 days |
| **PR #1021 MERGED** -- drift auto-pause gate + crypto-short test fixes | P0 infra now partially shipped | Removed redundant drift-gate items; referenced new canonical config |
| **PR #1030 OPEN** -- Mercury2 P0.1+P0.2+P0.3 (missing JS deploy + gate-policy parity + drift-freshness) | `money_ready_filter.js` now deployed; `per_asset_thresholds.json` marked orphan | Updated deployment status |
| **`hf_stats` refreshed** (was 22 days stale) | Asset-class baselines changed | Updated Appendix B with live numbers: Commodity PF 2.26 (not 3.94), Equity PF 1.82, ETF PF 1.49 |
| **`per_asset_thresholds.json` orphan** | Zero Python readers since PR #660 | Added deprecation notice; canonical config = `hf_quality_gates.json` |
| **`claude_gainer` sparkline contradiction** | Dashboard payload shows +1006% sparkline vs +80% total_pnl_pct | Added to Anomaly Detector scope (P2) |
| **Drift KS_D = 0.0498** vs critical 0.0460 (marginal, not 6.6x as stale snapshot suggested) | Drift alert still TRUE but not catastrophic | Revised risk language |
| **kimi_signal_tracking PF 5.80** is real but legacy (16 pre-blacklist winners) | Blacklist works; no code fix needed | Added cosmetic badge recommendation |

### PR disposition summary

| PR | Original plan | Revised plan | Rationale |
|----|---------------|--------------|-----------|
| #1017 | Merge as state-machine mega-PR | **Split into 5 sub-PRs**: (a) resolver v2 table, (b) kill_switch_ladder hierarchy doc, (c) position_sizer_v2, (d) real_money_state_machine staging, (e) daily_edge_report | Swarm consensus: Wire-Up violation + 581 JSON data files in diff |
| #1018 | Merge as CRYPTO mutations mega-PR | **Split into 4 sub-PRs**: (a) MEME split schema, (b) signal_quality_ml wire, (c) funding_arb backtest, (d) quarantine automation | Same blockers + payload-contract risk |
| #1019 | Merge as EQUITY/FOREX/BOND mega-PR | **Split into 3 sub-PRs**: (a) factor sleeves, (b) G10 carry, (c) yield curve | BOND floor-change without investigation gate |
| #1020 | Merge as COMMODITY/FUTURES/OPTIONS/CEF mega-PR | **Split into 3 sub-PRs**: (a) FUTURES Donchian, (b) OPTIONS defined-risk, (c) CEF NAV discount | Stage H violation (OPTIONS before any Stage F pilot) |

## Executive Summary

The prediction system has **134 registered systems** but only **32 have n≥20**. The MySQL layer is the single source of truth for picks, backtests, and Discord audit trails, yet it carries **1.27M backtest rows (1.4 GB)** in the same DB as live picks. The GitHub Actions sync runs hourly with a 10-minute timeout and fails silently (`|| echo "non-fatal"`).

These ideas focus on **making the prediction system MySQL-native**, not JSON-file-dependent, so the dashboard generator can query the DB directly instead of loading 16.78 MB of JSON into memory every hour.

---

## AREA 1: MySQL Schema Hardening for Prediction Integrity

### 1.1 — Backtest DB Split (P0)
**Current:** `bt_backtest_trades` (1.27M rows / 1.4 GB) lives in `ejaguiar1_stocks`.  
**Problem:** Bloated live-picks DB; backfill queries slow down active-pick inserts.  
**Action:**
- Provision `ejaguiar1_backtests` user + DB on mysql.50webs.com.
- Update `.github/workflows/mysql-trading-sync.yml` to set `BACKTESTS_DB_NAME=ejaguiar1_backtests`.
- Migrate historical `bt_backtest_trades` + `bt_backtest_runs` in batches (10k rows per cron).
- Add `BACKTESTS_DB_PASS` env var fallback to `DB_PASS_BACKTESTS`.

**Acceptance:** `ejaguiar1_stocks` shrinks by >1 GB; backtest inserts no longer block live-pick upserts.

### 1.2 — Prediction Outcome Resolution Table (P0)
**Current:** 0/3,500 picks resolved (resolver gap). Outcomes live in JSON files only.  
**Problem:** MySQL cannot answer "what is our live WR per strategy?" without Python processing.  
**Action:**
- Add `at_pick_outcomes` table:
  ```sql
  CREATE TABLE at_pick_outcomes (
      pick_id CHAR(36) PRIMARY KEY,
      symbol VARCHAR(50),
      strategy VARCHAR(200),
      asset_class ENUM('CRYPTO','FOREX',...),
      status ENUM('OPEN','WON','LOST','EXPIRED','FLAT'),
      resolution_method ENUM('TP_HIT','SL_HIT','TIME_EXPIRED','MANUAL'),
      pnl_pct DECIMAL(10,4),
      resolved_at DATETIME,
      resolver_version VARCHAR(20),
      INDEX idx_po_status (status),
      INDEX idx_po_strategy (strategy),
      INDEX idx_po_resolved (resolved_at)
  );
  ```
- Wire `outcome_resolver_v2.py` to upsert into `at_pick_outcomes` after resolving.
- Add MySQL-only dashboard query: `SELECT strategy, COUNT(*), AVG(pnl_pct) FROM at_pick_outcomes WHERE resolved_at > NOW() - INTERVAL 30 DAY GROUP BY strategy`.

**Acceptance:** Dashboard generator can compute per-strategy WR in <1s via SQL instead of parsing JSON.

### 1.3 — Confidence Calibration Audit Table (P1)
**Current:** ML confidence is inverted (`conf≥0.9` → WR 14.4%). Only logged in JSON.  
**Action:**
- Add `at_confidence_calibration` table tracking buckets:
  ```sql
  CREATE TABLE at_confidence_calibration (
      bucket VARCHAR(10) PRIMARY KEY, -- '0.0-0.1', '0.1-0.2', ...
      asset_class VARCHAR(20),
      n_picks INT,
      n_wins INT,
      actual_wr DECIMAL(5,4),
      expected_wr DECIMAL(5,4),
      calibration_gap DECIMAL(5,4), -- actual - expected
      updated_at DATETIME
  );
  ```
- Hourly cron computes actual WR per confidence bucket from `at_pick_outcomes`.
- Dashboard shows calibration drift: "Bucket 0.9-1.0: expected 90% WR, actual 14.4% → INVERTED".

**Acceptance:** Auto-quarantine rule triggers when `calibration_gap < -50pp` for any bucket.

---

## AREA 2: GitHub Actions Reliability

### 2.1 — MySQL Sync Workflow Hardening (P0)
**Current:** `mysql-trading-sync.yml` has `|| echo "MySQL sync failed (non-fatal)"` on line 43.  
**Problem:** Silent failures. If 50webs is down, we don't know picks are stale.  
**Action:**
- Remove silent-fail wrapper.
- Add retry logic with exponential backoff (3 retries, 5s / 15s / 45s).
- On final failure: open GitHub Issue via `actions/github-script` with failure logs.
- Add `timeout-minutes: 15` (up from 10) because 50webs latency spikes.
- Cache `pymysql` between runs using `actions/setup-python` `cache: 'pip'`.

**YAML snippet:**
```yaml
- name: Sync trading picks to MySQL
  env:
    DB_HOST: mysql.50webs.com
    DB_PORT: '3306'
    DB_USER: ejaguiar1_stocks
    DB_PASS: ${{ secrets.DB_PASS_STOCKS }}
    DB_NAME: ejaguiar1_stocks
  run: |
    for i in 1 2 3; do
      python alpha_engine/mysql_trading_sync.py && break
      echo "Attempt $i failed, retrying in $((5 * i))s..."
      sleep $((5 * i))
    done
```

### 2.2 — Prediction Quality Tracker — DB Integration (P1)
**Current:** `prediction_quality_tracker.py` writes to local JSON (`prediction_quality_history.json`), commits back to repo.  
**Problem:** 720 entries × 14 metrics = 10KB JSON committed hourly. Repo bloat.  
**Action:**
- Add `prediction_quality_tracker.py --mysql` mode that writes to `at_prediction_quality` table instead of JSON.
- Table schema:
  ```sql
  CREATE TABLE at_prediction_quality (
      id INT AUTO_INCREMENT PRIMARY KEY,
      generated_at DATETIME,
      metric_name VARCHAR(50),
      metric_value DECIMAL(10,4),
      asset_class VARCHAR(20),
      source_system VARCHAR(100)
  );
  ```
- Keep JSON as fallback for offline dev, but GHA writes to MySQL.
- `.github/workflows/prediction-quality-tracker.yml` adds `DB_PASS: ${{ secrets.DB_PASS_STOCKS }}` env.

**Acceptance:** Stop committing `prediction_quality_history.json`; query MySQL for historical trends.

### 2.3 — Verify Predictions — MySQL Backfill (P1)
**Current:** `alpha-verify-predictions.yml` runs every 2 hours, writes `prediction_verification_log.json`.  
**Action:**
- Add `--mysql` flag to `verify_predictions.py`.
- Upsert verification results to `at_prediction_verification` table.
- Enable cross-validation queries: "Which predictor had highest verification score last 7 days?"

---

## AREA 3: Prediction System New Capabilities

### 3.1 — MySQL-Driven Swarm Pick Resolver (P1)
**Current:** `tools/swarm/outcome_resolver_swarm.py` uses yfinance + TV MCP fallback. Results go to JSON.  **Problem:** 38 swarm picks tracked in JSON; no SQL analytics possible.  **Action:**
- Add `swarm_picks` table to `ejaguiar1_stocks`:
  ```sql
  CREATE TABLE swarm_picks (
      pick_id CHAR(36) PRIMARY KEY,
      symbol VARCHAR(50),
      direction VARCHAR(10),
      asset_class VARCHAR(20),
      personas JSON,
      consensus_tier VARCHAR(50),
      underlying_model VARCHAR(50),
      entry_price DECIMAL(18,8),
      tp DECIMAL(18,8),
      sl DECIMAL(18,8),
      status ENUM('OPEN','WON','LOST','EXPIRED'),
      pnl_pct DECIMAL(10,4),
      created_at DATETIME,
      resolved_at DATETIME
  );
  ```
- Wire resolver to upsert outcomes into `swarm_picks`.
- Enable SQL leaderboard: `SELECT underlying_model, AVG(pnl_pct) FROM swarm_picks WHERE resolved_at > NOW() - INTERVAL 7 DAY GROUP BY underlying_model`.

**Acceptance:** Model bake-off leaderboard powered by MySQL, not JSON parsing.

### 3.2 — Per-Asset-Class Predictor Scorecard (P1)
**Current:** 134 systems but no centralized predictor scorecard in MySQL.  **Action:**
- Add `at_predictor_scorecard` table:
  ```sql
  CREATE TABLE at_predictor_scorecard (
      predictor VARCHAR(200),
      asset_class VARCHAR(20),
      n_picks INT,
      n_resolved INT,
      win_rate DECIMAL(5,4),
      profit_factor DECIMAL(10,4),
      sharpe DECIMAL(10,4),
      max_drawdown DECIMAL(10,4),
      last_signal_at DATETIME,
      staleness_days INT,
      verdict VARCHAR(50), -- TIER_1, TIER_2, TIER_3, NO_EDGE, STALE
      PRIMARY KEY (predictor, asset_class)
  );
  ```
- Hourly cron populates from `at_pick_outcomes` + `at_raw_picks`.
- Dashboard queries this table instead of computing from JSON.

**Acceptance:** `/audit` shows live scorecard refreshed from MySQL in <2s.

### 3.3 — Prediction Anomaly Detector — MySQL Edition (P2)
**Current:** `alpha_engine/prediction_anomaly_detector.py` exists but may be JSON-only.  **Action:**
- Build `tools/mysql_prediction_anomaly_scanner.py`:
  - Query `at_raw_picks` for picks where `confidence > 0.9` but `pnl_pct < 0` (inverted confidence).
  - Query for `symbol` appearing in `at_raw_picks` with both `LONG` and `SHORT` within 24h (direction conflict).
  - Query for `strategy` with `last_signal_at > 7 days ago` but cron still active (silent-dead strategy).
  - Query dashboard payload for sparkline vs aggregate pnl_pct divergence (e.g., `claude_gainer` shows +1006% sparkline but +80% total_pnl_pct).
- Output: `reports/mysql_anomaly_scan_YYYY-MM-DD.md` + Discord alert.

**New anomaly rule (P2.1): Dashboard Payload Coherence Check**
- Compare `systems[].total_pnl_pct` vs `systems[].sparkline[-1]` in `dashboard_data.json`.
- Flag if divergence > 500pp (indicates arithmetic vs geometric return mix, or double-counting).
- Auto-file issue referencing `audit_trail/dashboard_generator.py` line range.

---

## AREA 4: Database Performance & Monitoring

### 4.1 — Index Audit on `trading_picks` (P0)
**Current:** `trading_picks` table in `ejaguiar1_stocks` has no composite indexes.  **Action:**
- Add indexes:
  ```sql
  CREATE INDEX idx_tp_strategy_status ON trading_picks(strategy, status);
  CREATE INDEX idx_tp_asset_status ON trading_picks(category, status);
  CREATE INDEX idx_tp_created ON trading_picks(created_at);
  CREATE INDEX idx_tp_closed ON trading_picks(closed_at);
  CREATE INDEX idx_tp_confidence ON trading_picks(confidence);
  ```
- Run `EXPLAIN` on common queries from `mysql_trading_sync.py` and `dashboard_generator.py`.

### 4.2 — MySQL Health Dashboard Widget (P2)
**Action:**
- Add `at_mysql_health` table tracked by a new workflow `.github/workflows/mysql-health-check.yml`:
  ```sql
  CREATE TABLE at_mysql_health (
      checked_at DATETIME PRIMARY KEY,
      db_name VARCHAR(50),
      table_count INT,
      total_rows BIGINT,
      total_size_mb DECIMAL(10,2),
      slow_queries INT,
      connection_errors INT
  );
  ```
- Cron runs `SHOW TABLE STATUS` + `SHOW PROCESSLIST` every 6 hours.
- Dashboard shows DB size trend, slow query count, connection health.

### 4.3 — Connection Pooling Fix (P1)
**Current:** `mysql_client.py` uses a `queue.Queue` pool of size 3, but `mysql_trading_sync.py` creates new connections per run.  **Action:**
- Standardize on `mysql_client.py` pool for all DB access.
- Add pool exhaustion metrics: log when `pool.qsize() == 0`.
- Add connection leak detection: auto-close connections idle >5 minutes.

---

## AREA 5: Cross-Cutting Ideas

### 5.1 — GitHub Actions MySQL Dry-Run Mode (P1)
**Action:**
- Add `--dry-run` to `mysql_trading_sync.py` that prints `INSERT/UPDATE` statements without executing.
- Wire into CI: `.github/workflows/mysql-sync-dry-run.yml` runs on every PR, validates SQL syntax without touching DB.
- Prevents bad schema changes from breaking the live sync.

### 5.2 — Windows Environment Variable Migration (P0)
**Current:** Some scripts read `DB_PASS` from GitHub secrets, but local dev expects Windows env vars `DB_PASS_STOCKS` / `DB_PASS_BACKTESTS`.  **Action:**
- Document in `docs/MYSQL_ENV_SETUP.md`:
  ```powershell
  [System.Environment]::SetEnvironmentVariable("DB_PASS_STOCKS", "your_password", "User")
  [System.Environment]::SetEnvironmentVariable("DB_PASS_BACKTESTS", "your_password", "User")
  ```
- Add `env_check.py` script that validates all required env vars are present before running sync.

### 5.3 — MySQL → Audit Dashboard Direct Query (P2)
**Current:** `dashboard_generator.py` reads 30+ JSON files + 16 SQLite DBs, then generates HTML. It does NOT query MySQL.  **Action:**
- Add `audit_trail/mysql_dashboard_loader.py`:
  - Query `trading_picks` for active + closed picks.
  - Query `at_predictor_scorecard` for system health.
  - Query `at_prediction_quality` for quality trends.
  - Emit `dashboard_data.json::mysql` block.
- This is the first step toward making the dashboard **DB-native** instead of file-native.

---

## Execution Roadmap

| Week | Focus | Deliverables |
|------|-------|-------------|
| **Week 1** | Schema + Split | `ejaguiar1_backtests` provisioned; `bt_backtest_trades` migrated; `at_pick_outcomes` table live; index audit on `trading_picks` |
| **Week 2** | Sync Hardening | Silent-fail removed from `mysql-trading-sync.yml`; retry logic added; `prediction_quality_tracker.py --mysql` shipped |
| **Week 3** | Predictor Scorecard | `at_predictor_scorecard` + `at_confidence_calibration` tables; hourly cron; dashboard queries MySQL for scorecard |
| **Week 4** | Anomaly + Health | `mysql_prediction_anomaly_scanner.py`; `mysql-health-check.yml` workflow; connection pool fix |

---

## Quick Wins (Ship Today)

1. **Remove silent fail** from `mysql-trading-sync.yml` line 43.
2. **Add composite index** `idx_tp_strategy_status` on `trading_picks`.
3. **Document env vars** in `docs/MYSQL_ENV_SETUP.md`.
4. **Add `BACKTESTS_DB_NAME` env** to `mysql-trading-sync.yml` with fallback to `ejaguiar1_stocks`.
5. **Verify PR #1030 CI green** -- ensures `money_ready_filter.js` + `hc_filter.js` + `validation_metrics.js` deploy to all 3 sites.

---

## File References

| File | Relevance |
|------|-----------|
| `.github/workflows/mysql-trading-sync.yml` | Primary sync workflow |
| `.github/workflows/prediction-quality-tracker.yml` | Quality metrics pipeline |
| `.github/workflows/alpha-verify-predictions.yml` | Verification pipeline |
| `alpha_engine/mysql_trading_sync.py` | Sync logic |
| `audit_trail/mysql_client.py` | Connection pool + audit logging |
| `audit_trail/mysql_schema.sql` | Schema definitions |
| `alpha_engine/prediction_quality_tracker.py` | Quality metric computation |
| `alpha_engine/prediction_anomaly_detector.py` | Anomaly detection (extend to MySQL) |
| `tools/swarm/outcome_resolver_swarm.py` | Swarm resolver (wire to MySQL) |
| `tools/swarm/weekly_review.py` | Leaderboard (query MySQL instead of JSON) |

---

## Appendix A — Enhancements & Projected Benefits

### System-Wide Benefits

| Enhancement | Metric Before | Metric After | Projected Benefit |
|-------------|---------------|--------------|-------------------|
| Backtest DB split | `ejaguiar1_stocks` = 1.4 GB bloat | `ejaguiar1_stocks` < 500 MB | Live-pick inserts 3× faster; backup time cut 60% |
| Outcome resolution table | 0/3,500 resolved in MySQL | 3,500+ in `at_pick_outcomes` | Dashboard WR queries: 35 min → <1s |
| Confidence calibration | Inverted ML silent | Auto-quarantine + banner | Prevent bad picks entering pipeline; estimated +8–12pp class WR |
| Sync retry logic | Silent fail (unknown downtime) | Alert + retry + GitHub Issue | MTTR from hours to minutes |
| Predictor scorecard | JSON-only, 134 systems unranked | MySQL-live scorecard | Instant visibility into top 10 predictors per class |
| Swarm picks MySQL | 38 picks in JSON | SQL queryable | Model bake-off leaderboard in real time |
| Index audit | Full table scans | Composite indexes | `trading_picks` queries 5–10× faster |
| DB-native dashboard | 16.78 MB JSON payload | MySQL direct query | Generator runtime: 35 min → 20 min |

### Per-Asset-Class Benefits

| Class | Current PF | Current WR | Enhancement Unlock | Projected PF | Projected WR |
|-------|-----------|-----------|-------------------|-------------|-------------|
| **COMMODITY** | 3.94 | 67.8% | `multi_asset_cot` n≥200 + MDD tightening | 4.50 | 72% |
| **EQUITY** | 1.82 | 52.0% | Factor sleeves (sub-PRs #1019a-c) + net-of-cost overlay | 2.20 | 58% |
| **CRYPTO** | 1.36 | 46.5% | MEME split + Signal Quality ML (sub-PRs #1018a-d) + strip losers | 3.00 | 65% |
| **ETF** | 1.34 | 56.1% | NAV discount arb + sector rotation | 1.80 | 58% |
| **BOND** | 0.66 | 54.5% | Yield curve steepener + scanner production wiring | 1.60 | 55% |
| **FOREX** | 0.29 | 46.2% | G10 carry (sub-PRs #1019a-c) + regime filter | 1.40 | 52% |
| **FUTURES** | 0.00 | 0.0% | Donchian + accumulation mode (sub-PRs #1020a-c) | 1.50 | 50% |
| **OPTIONS** | — | — | Defined-risk only (new class, PR #1020) | 1.80 | 55% |
| **MEME** | — | — | Split from CRYPTO + pump detection (new class) | 1.40 | 52% |
| **CEF** | — | — | NAV discount + monthly rebalance (new class) | 1.60 | 54% |

---

## Appendix B — Institutional Quality Roadmap

**Definition of "Institutional"**: Lopez de Prado AFML 10-step readiness gate clear + Tier-1 Renaissance thresholds (PF≥2.0, WR≥55%, MDD≤10%, n≥200) + DSR≥0.95 + 30-day shadow paper Sharpe > 0.7× backtest.

### Current State Snapshot (2026-05-14 EST)

| Rank | Class | PF | WR | MDD | n | DSR | State | Blocker |
|------|-------|----|----|-----|---|-----|-------|---------|
| 1 | **COMMODITY** | 2.26 | 54.0% | 17.8% | 74 | 1.0000 | SHADOW | n<200, MDD>10% |
| 2 | **EQUITY** | 1.82 | 52.0% | ~12% | 271 | ~0.85 | REHAB | PF<2.0, WR<55% |
| 3 | **ETF** | 1.49 | 59.0% | ~14% | 104 | ~0.70 | REHAB | PF<2.0, n<200 |
| 4 | **CRYPTO** | 1.36 | 46.5% | 49.2% | 7,758 | ~0.60 | BLOCKED | MDD too high (losers drag) |
| 5 | **BOND** | 0.66 | 54.5% | ~8% | 18 | — | BLOCKED | n<100, PF<1.5 |
| 6 | **FOREX** | 0.29 | 46.2% | >50% | 1,169 | <0.10 | BLOCKED | PF<1.0, toxic aggregate |
| 7 | **FUTURES** | 0.00 | 0.0% | — | 0 | — | BLOCKED | No production signals |
| — | **OPTIONS** | — | — | — | — | — | NEW | Not yet launched |
| — | **MEME** | — | — | — | — | — | NEW | Split from CRYPTO pending |
| — | **CEF** | — | — | — | — | — | NEW | Not yet launched |

### Projected Institutional Dates (EST)

| Class | Target Date | EST Time | Milestones Required |
|-------|-------------|----------|---------------------|
| **COMMODITY** | **2026-06-30** | 09:00 EST | n≥200 reached (current n=144, need +56 signals @ 3/day = 19 days); MDD cap enforced at 10% via position sizer; DSR already 1.0000; shadow paper started 2026-05-12 |
| **CRYPTO** | **2026-08-01** | 09:00 EST | Merge sub-PRs from #1018 (MEME split + Signal Quality ML); quarantine `luxalgo_filters` + `kimi_signal_tracking`; strip baby_strats_forward losers; top-3 ensemble PF ~3.0; 30-day shadow paper post-MEME-split |
| **EQUITY** | **2026-08-15** | 09:00 EST | Merge sub-PRs from #1019 (factor sleeves); net-of-cost PF uplift from 1.82->2.20; walk-forward WFE>60%; 30-day shadow paper for value/momentum/quality sleeves separately |
| **ETF** | **2026-09-01** | 09:00 EST | NAV discount scanner wired; sector-rotation backtest PF>1.5; n accumulation to 200; shadow paper 30 days |
| **FUTURES** | **2026-09-15** | 09:00 EST | Merge sub-PRs from #1020 (Donchian + accumulation); production scanner wired; n≥200; break-test across contango/backwardation regimes |
| **BOND** | **2026-09-15** | 09:00 EST | Bond scanner production cron active (n=18->200 in ~12 weeks); yield curve steepener + duration rotation; DSR≥0.95; shadow paper 30 days |
| **FOREX** | **2026-10-01** | 09:00 EST | Merge sub-PRs from #1019 (G10 carry + regime filter); quarantine toxic legacy strategies; carry sleeve Sharpe 0.86 target; 30-day shadow paper |
| **OPTIONS** | **2026-10-15** | 09:00 EST | Sub-PRs from #1020 defined-risk strategies deployed; 90-day paper minimum completed; max 5% portfolio cap; iron condor + credit spread only |
| **MEME** | **2026-09-01** | 09:00 EST | Split from CRYPTO complete; pump-dump detection active; n≥200; 30-day shadow paper |
| **CEF** | **2026-10-01** | 09:00 EST | NAV discount tracker live; monthly rebalance cycle proven; n≥200; 30-day shadow paper |

### Critical Path Dependencies

```
2026-05-15 --> PR #1030 merge (Mercury2 P0.1+P0.2+P0.3) -- drift-freshness gate live
     │
     o--> 2026-05-31 --> COMMODITY enters SHADOW (DSR=1.0, n=74->200)
     │
     o--> 2026-06-15 --> Open sub-PRs #1018a-d (MEME split, signal_quality_ml, funding_arb, quarantine)
     │
     o--> 2026-07-15 --> COMMODITY institutional (first class)
     │
     o--> 2026-07-15 --> CRYPTO enters SHADOW post-MEME-split
     │
     o--> 2026-07-15 --> Open sub-PRs #1019a-c (factor sleeves, G10 carry, yield curve)
     │
     o--> 2026-08-15 --> EQUITY institutional
     │
     o--> 2026-08-15 --> Open sub-PRs #1020a-c (FUTURES Donchian, OPTIONS defined-risk, CEF NAV)
     │
     "--> 2026-10-01 --> FOREX institutional (last major class)
```

### Risk Factors That Could Delay Dates

| Risk | Impact | Mitigation |
|------|--------|------------|
| Resolver backfill slower than 2 weeks | All dates slip | Run backfill in parallel; do not block UI phases |
| PR #1018–#1020 merge conflicts | CRYPTO/EQUITY/FOREX slip 2–4 weeks | Staging branch validation before merge |
| 50webs MySQL downtime >24h | All dates slip | Retry logic + alert + local SQLite failover |
| MEME split causes CRYPTO n starvation | CRYPTO slip | Cap MEME at 15% of CRYPTO volume |
| Bond scanner wiring fails | BOND slip | Existing 3 strategies in `alpha_engine/bond_scanner.py` already coded |

---

## Appendix C — Project Schedule (Gantt)

| Phase | Start | End | Owner | Deliverable |
|-------|-------|-----|-------|-------------|
| **A0** Prerequisite cleanup | 2026-05-14 | 2026-05-17 | Quant eng | Deprecate duplicate state machine; `.gitattributes`; hierarchy doc |
| **A** Merge PR #1017 + staging | 2026-05-17 | 2026-05-24 | Quant eng | Staging passes; payload split; backfill running |
| **J** ML banner + auto-quarantine | 2026-05-14 | 2026-05-15 | Frontend | Banner live; CI test passes |
| **B/C** State surface + kill switch | 2026-05-24 | 2026-05-31 | Frontend | Protocol cards; kill-switch header; transition log |
| **J+** Safety hardening | 2026-05-31 | 2026-06-02 | Safety eng | Incident mode; resolver widget; emergency revert |
| **D/E** 6-level tracker + action cards | 2026-06-02 | 2026-06-09 | Frontend | Stepper; per-asset CTAs; dual approval wired |
| **F** 5-AI consensus gate | 2026-06-09 | 2026-06-12 | Backend | Pre-computed scores; adherence badge |
| **G** Shadow paper expansion | 2026-06-12 | 2026-06-19 | Backend | Generic tracker; auto-provision; SQLite atomicity |
| **H** Monkey test + slippage | 2026-06-19 | 2026-06-26 | Backend | Nightly cache; slippage panel |
| **I** Auto real_money.html | 2026-06-19 | 2026-06-26 | Backend | Generator; deploy safety |
| **K** Chaos dry-run + rollback | 2026-06-26 | 2026-06-30 | Safety eng | All scenarios pass; runbook published |
| **MySQL Week 1** | 2026-05-14 | 2026-05-21 | DBA | ejaguiar1_backtests live; at_pick_outcomes; indexes |
| **MySQL Week 2** | 2026-05-21 | 2026-05-28 | Backend | Sync retry; prediction_quality --mysql; verify --mysql |
| **MySQL Week 3** | 2026-05-28 | 2026-06-04 | Backend | Predictor scorecard; confidence calibration table |
| **MySQL Week 4** | 2026-06-04 | 2026-06-11 | DBA | Health widget; anomaly scanner; connection pool fix |

---

## Appendix D — Acceptance Criteria for "Institutional"

Before any asset class is promoted to `LIVE_ELIGIBLE`, the following MUST pass:

1. **Quantitative gates** (all must pass):
   - [ ] Profit Factor ≥ 2.0
   - [ ] Win Rate ≥ 55%
   - [ ] Max Drawdown ≤ 10%
   - [ ] Sample size n ≥ 200
   - [ ] DSR ≥ 0.95 (Lopez de Prado AFML eq 14.5)
   - [ ] PBO < 0.05 (probability of backtest overfitting)
   - [ ] WFE > 60% (walk-forward efficiency)

2. **Safety gates** (all must pass):
   - [ ] Kill-switch ladder tested GREEN→BLACK in synthetic mode
   - [ ] Dual approval enforced for Level 5 transitions
   - [ ] Rollback runbook published and drill-tested
   - [ ] Position sizer v2 active with Kelly×0.25
   - [ ] Correlation guard active (top 3 positions ρ < 0.70)

3. **Operational gates** (all must pass):
   - [ ] 30-day shadow paper completed with live Sharpe > 0.7× backtest
   - [ ] Slippage reality check: net PF > 0.5 × gross PF
   - [ ] Monkey test: beats 95th %ile of 1,000 random strategies
   - [ ] Transaction-cost overlay validated
   - [ ] Resolver coverage ≥ 95% (no phantom unresolved picks)

4. **Governance gates** (all must pass):
   - [ ] User explicit sign-off on asset-class allocation
   - [ ] Paper-pilot graduation gate cleared
   - [ ] All P0/P1 blockers from this plan resolved

---

*Ideas grounded in: live schema audit, DAILY_IDEAS.MD, swarm-consolidated plan, institutional readiness gate, and GitHub Actions workflow review.*
*Projected dates assume PR #1017–#1020 merge on schedule, MySQL 50webs uptime >99%, and resolver backfill completes by 2026-05-31.*

---

## 2026-05-16 — Kimi /audit/v2 Integration Follow-Up

**Prompt to address:**
> Describe the steps necessary to integrate your dashboard and analysis into https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ which would feed into findtorontoevents.ca/audit. We were thinking maybe to make it findtorontoevents.ca/audit/v2 for your landing page. What are the steps to take to integrate your files and test? Are you sure your data is based on real-world data? Is your webpage fully automated, or just a proof of concept? Is it based on real-world data? Dummy data? Prove for each asset class that you have a statistical edge. I believe we likely dont have enough data to be making claims of statistical edge.. right? if not prove me wrong with stats. Or offer other approaches such as a pilot dashboard where we paper trade only, until it reaches a certain state — except for certain exception criteria/asset classes. Also provide the exact filters under findtorontoevents.ca/audit/ where a user could filter by and get to the "winning criteria" you claim we have T1 Grade performance for — are you sure? But we also have a ton of GitHub Actions jobs — we want to be efficient.

**Assessment (verified 2026-05-16):**
- Kimi's trades_2026-05-16.csv: **0 rows** — empty placeholder, not real trades
- CRYPTO Sharpe=15.718, PF=16.566: **impossible for real system** (institutional hedge funds achieve 2–4)
- Proven strategies n=22 (LR_C0.1): **statistically meaningless** (need n≥100 per TESTING_PROTOCOL.MD Layer 2.5)
- Kimi explicitly stated: "Synthetic data (GBM-calibrated) — all code is production-ready for real data swap"
- **Conclusion: proof-of-concept only. All metrics are synthetic.**

**Integration Plan (approved approach):**
- Take Kimi's dashboard HTML/CSS/JS as UI shell (it is well-designed)
- Replace all data with real `audit_dashboard/data/dashboard_data.json` (post-resolver-v2)
- Deploy as `audit_dashboard/v2/index.html` → routes to findtorontoevents.ca/audit/v2
- Add "Paper Trade Mode" banner for classes below T2 (FOREX, BOND, CRYPTO class-wide)
- Exact real filters for "winning" picks: see `tools/edge_analysis/asset_class_edge_registry.py`

---

## Claude Code Analysis — 2026-05-16T22:10Z

### Area 1 (MySQL Schema Hardening) — Status

| Item | Priority | Status | Notes |
|---|---|---|---|
| **1.1 Backtest DB split** | P0 | BLOCKED | `DB_PASS_BACKTESTS` not in GH secrets — user action required |
| **1.2 `at_pick_outcomes` table** | P0 | BLOCKED | Same blocker |
| **1.3 `at_confidence_calibration` table** | P1 | OPEN | No blocker once 1.2 ships; high value |

### Area 2 (GitHub Actions Reliability) — Status

| Item | Status | Notes |
|---|---|---|
| **2.1 MySQL sync silent-fail removal** | 🔄 OPEN | Still has `\|\| echo "non-fatal"` on line 43 of mysql-trading-sync.yml |
| **2.2 Prediction quality tracker MySQL mode** | 🔄 OPEN | Still writes to JSON; blocked on DB_PASS_STOCKS validity |
| **2.3 Verify predictions MySQL backfill** | 🔄 OPEN | — |

**Highest-value quick win:** Remove silent-fail from `mysql-trading-sync.yml` line 43. Zero dependency on DB_PASS_BACKTESTS. Catches DB outages instead of swallowing them. **Effort: XS (5 min edit).**

### Area 3 (Prediction System New Capabilities) — Status

| Item | Status |
|---|---|
| **3.1 MySQL-driven swarm pick resolver** | OPEN — `swarm_picks` table spec complete in this doc; not created |
| **3.2 Per-asset predictor scorecard** | OPEN — `at_predictor_scorecard` spec complete; not created |
| **3.3 MySQL prediction anomaly scanner** | OPEN — `tools/mysql_prediction_anomaly_scanner.py` not yet shipped |

### Appendix B — Current State vs. Projected (2026-05-14)

| Class | Projected PF | Current PF | Delta | Gap Explanation |
|---|---|---|---|---|
| COMMODITY | 4.50 | ~2.57 (post-dedup) | Lagging | CT=F dedup fixed; multi_asset_cot elite but class drag from non-COT strategies |
| EQUITY | 2.20 | 1.56 | Lagging | Factor sleeves (sub-PRs #1019a-c) not merged; PEAD shipped but not yet adding picks |
| CRYPTO | 3.00 | 1.31 (filtered) | Needs quarantine | MEME split + signal quality ML sub-PRs still open; quarantine shipped |
| ETF | 1.80 | 1.32 | Lagging | Risk-parity rotation not shipped |
| BOND | 1.60 | ~0.66 (n=18) | Expected | Scanner wired; need n=200 (months away) |
| FOREX | 1.40 | 0.27 (blocked) | Hard-disabled | Carry-factor scaffold OPEN; ~6 months to rehab |

### /audit/v2 Integration Plan — Status

KimiCode's assessment (synthetic data) is correct. The integration plan is sound:
- KimiCode dashboard HTML/CSS/JS shell: **good UI design, wrong data**
- Real data source: `audit_dashboard/data/dashboard_data.json` ✅
- `audit/v2` deployment: **OPEN** — `audit_dashboard/v2/index.html` not yet created
- Paper Trade Mode banner: **OPEN** — needed for FOREX/BOND/CRYPTO class-wide
- `tools/edge_analysis/asset_class_edge_registry.py`: **needs verification** — may not exist

**Recommended approach for /audit/v2:** Use `tools/edge_filter_engine_v3.py` (KimiCLI session) as the backend data source for v2 dashboard. It already reads real `dashboard_data.json` and outputs per-class verdict JSON. Wire v2 dashboard to `reports/strict_filters_latest.json` for the filter-ready display. **Effort: M (1 day UI + wiring).**

### Critical Path for Next Week

1. **User action:** Add `DB_PASS_BACKTESTS` to GH secrets → unblocks 4 P0/P1 items
2. **XS fix:** Remove silent-fail from `mysql-trading-sync.yml:43`
3. **S item:** Ship `at_confidence_calibration` table once `at_pick_outcomes` is created
4. **M item:** Ship `tools/mysql_prediction_anomaly_scanner.py`
5. **M item:** Create `audit_dashboard/v2/index.html` using KimiCode shell + real data
