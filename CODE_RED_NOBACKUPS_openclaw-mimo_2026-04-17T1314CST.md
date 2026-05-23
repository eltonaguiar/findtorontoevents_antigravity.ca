# CODE_RED_NOBACKUPS.MD — GitHub Actions Failure Audit

**Agent:** {{}} (OpenClaw MiMo)  
**Generated:** 2026-04-17 13:14 CST (Asia/Shanghai)  
**Repository:** [eltonaguiar/findtorontoevents_antigravity.ca](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca)  
**Scope:** Audit all 284 GitHub Actions workflows for failures, missing failover sources, and strategy-breaking errors.

---

## 0. Audit Summary

| Metric | Count |
|--------|-------|
| Total workflows | 284 |
| Failing (latest run = failure) | 10 |
| High fail rate (≥50% of last 10) | 18 |
| No recent runs | 7 |
| CODE RED (no backup source) | 6 |
| Strategy-breaking failures | 4 |

---

## 1. 🔴 CODE RED — No Backup Data Source

These workflows are **single points of failure** with NO alternative pipeline if they go down.

### 1.1 ALPHA ENGINE — Dynamic Runner (Production Scanner)
**File:** `dynamic-alpha-engine.yml`  
**Schedule:** Every 30 min (`:18` and `:48`)  
**Fail rate:** 3/5 (60%)  
**Status:** Latest run = None (likely timed out)

**What it does:** Runs `production_scanner.py` — the core engine that generates ALL active picks for the audit dashboard. When this stops, NO new picks are generated.

**Why it's CODE RED:**
- This is the **only** pipeline that feeds `active_picks.json`
- If it fails, the audit dashboard shows stale/empty picks
- 60% failure rate means roughly 18 out of 30 hourly runs fail per month
- No fallback scanner exists

**Root causes (from workflow YAML):**
- 120-minute timeout on ubuntu-latest runners (often insufficient for ML inference)
- `catboost` install failure silently ignored (`pip install catboost 2>/dev/null || echo "optional"`)
- Git push race conditions (multiple concurrent runs trying to push to main)
- WSL runner path assumes `E:` drive exists (`/mnt/e/findtorontoevents_antigravity.ca`)

**Impact:** When this fails, the dashboard shows picks from hours/days ago. Strategies go stale. New market conditions get missed.

---

### 1.2 Alpha Engine — Weekly Validation Suite
**File:** `alpha-weekly-validation.yml`  
**Schedule:** Monday 06:00 UTC  
**Fail rate:** 5/5 (100%)  
**Failed step:** "Run Risk Metrics (Sortino + Realistic Sharpe + IC)"

**What it does:** Runs `risk_metrics.py` and `rolling_walk_forward.py` — computes Sortino ratio, realistic Sharpe, information coefficient, and rolling walk-forward validation.

**Why it's CODE RED:**
- **100% failure rate** — this has NEVER succeeded in the last 5 runs
- Without this, the system has **NO automated risk metrics**
- Walk-forward validation doesn't run → no anti-overfitting check
- Risk metrics don't update → system can't detect strategy degradation

**Root cause:** The `risk_metrics.py` script is likely crashing (import error, missing data, or computation failure). The 15-minute timeout may be too short.

**Impact:** The system operates **without any automated strategy validation**. Strategies that degrade continue to generate picks blindly.

---

### 1.3 Validate HF by Asset Class
**File:** `validate-hf-asset-class.yml`  
**Schedule:** Daily 06:35 UTC  
**Fail rate:** 4/5 (80%)  
**Failed step:** "Unit tests (stats + contracts + dashboard mirror)"

**What it does:** Runs pytest on `test_hf_validation_stats.py`, `test_hf_pick_contracts.py`, `test_dashboard_hc_rules.py` — validates HIGH CONVICTION picks by asset class.

**Why it's CODE RED:**
- Unit tests are failing → code has bugs that prevent validation
- Without this, HIGH CONVICTION picks for equity/forex/commodity can't be validated
- Non-crypto asset classes have NO validation pipeline working

**Root cause:** Test failures suggest the validation code is out of sync with the data format or scoring logic.

**Impact:** HIGH CONVICTION tier picks for non-crypto assets are unvalidated. Users see HC badges on picks that may not meet the criteria.

---

### 1.4 Walk-Forward Backtest (Weekly)
**File:** `walk-forward-backtest.yml`  
**Schedule:** Weekly  
**Fail rate:** 2/3 (67%)  
**Failed step:** "Run institutional backtest suite"

**What it does:** Runs the institutional-grade walk-forward backtest — the primary anti-overfitting mechanism.

**Why it's CODE RED:**
- Walk-forward is the **only** defense against overfitting
- 67% failure = most weeks, the system has NO backtest validation
- Without it, strategies may be curve-fit to historical data

**Impact:** No way to verify if strategies work out-of-sample. The system may be trading on overfit signals.

---

### 1.5 STOCKSUNIFY Daily Stock Picks
**File:** `stocks-daily-stocksunify.yml`  
**Schedule:** Daily  
**Fail rate:** 3/5 (60%)

**What it does:** Generates daily stock picks from the CAN SLIM + technical momentum algorithms.

**Why it's CODE RED:**
- The **only** equities pipeline
- No backup stock scanner exists
- 60% failure rate = equities picks are stale ~60% of the time
- The EDGEFINDER report identified equity as the best non-crypto asset class (+111% PnL) — but the pipeline feeding it is broken

**Impact:** Equities edge exists (47.4% WR, +111% PnL) but the pipeline to generate new picks is unreliable.

---

### 1.6 ALPHA ENGINE Live Autonomous Scanner
**File:** `alpha-engine-live.yml`  
**Status:** Latest = None (no recent runs detected)

**What it does:** Live autonomous scanner for real-time picks.

**Why it's CODE RED:** If this is supposed to be running and isn't, there's a gap in live scanning.

---

## 2. 🟡 HIGH RISK — Failing But Less Critical

| Workflow | File | Fail Rate | Impact |
|----------|------|-----------|--------|
| Monthly DNA Tournament | `monthly-tournament.yml` | 4/5 (80%) | Strategy evolution/selection broken |
| Overnight Mutations | `overnight-mutations.yml` | 3/5 (60%) | Strategy mutation engine failing |
| Algorithm Competition Refresh | `algorithm-competition-refresh.yml` | 2/5 (40%) | Algo leaderboard stale |
| Forward Test Daily | `forward-test-daily.yml` | 2/5 (40%) | Forward testing gaps |
| Feature Stability Check | `feature-stability-check.yml` | 2/5 (40%) | Feature drift detection unreliable |
| 2-Hour Strategy Challenge | `2hour_challenge.yml` | 10/10 (100%) | Completely broken, consider removing |
| Real 2-Hour Challenge | `real_2hour_challenge.yml` | 10/10 (100%) | Completely broken, consider removing |
| AsterDEX Paper Trader | `asterdex-paper-trader.yml` | 10/10 (100%) | Disabled but still failing on schedule |
| HC Nightly Rebuild | `hc-nightly-rebuild.yml` | 10/10 (100%) | HIGH CONVICTION rebuild never runs |

---

## 3. 🟢 PASSING — Key Workflows Currently OK

| Workflow | Status | Notes |
|----------|--------|-------|
| Outcome Resolver | ✅ 0/5 failures | TP/SL validation working |
| Copy Trader Forward Test | ✅ 0/5 failures | (but 0 runs = may not be triggering) |
| Polymarket Signals | ✅ 0/5 failures | Prediction market integration OK |
| Enhanced ML Crypto | ✅ 0/5 failures | ML pipeline healthy |
| Forward Test (Strategy Validation) | ✅ 0/5 failures | Core validation working |
| Alpha Engine Daily Picks | ✅ last success | Daily pick generation OK |
| ML Battleground ABC | ✅ 0/5 failures | Multi-model system OK |

---

## 4. Missing Failover Patterns

### 4.1 Production Scanner (Single Source = Single Point of Failure)

```
CURRENT:
  production_scanner.py → active_picks.json → dashboard
  ❌ No backup scanner
  ❌ No circuit breaker
  ❌ No fallback data source

SHOULD BE:
  production_scanner.py (primary) → active_picks.json
    └─[fail]→ fast_scanner.py (fallback) → active_picks.json
      └─[fail]→ last_known_good.json (cache)
```

### 4.2 Risk Metrics (No Source At All)

```
CURRENT:
  risk_metrics.py → risk_metrics.json
  ❌ ALWAYS FAILS (100% failure rate)
  ❌ No alternative risk computation
  ❌ System runs WITHOUT risk metrics entirely

SHOULD BE:
  risk_metrics.py (primary) → risk_metrics.json
    └─[fail]→ simplified_risk.py (fallback, just Sharpe + max DD)
      └─[fail]→ last_known_good.json (cache with staleness warning)
```

### 4.3 Stock Picks (Single Pipeline)

```
CURRENT:
  stocks-daily-stocksunify.yml → daily-stocks.json → dashboard
  ❌ 60% failure rate
  ❌ No backup stock screener

SHOULD BE:
  stocks-daily-stocksunify.yml (primary)
    └─[fail]→ stocks-basic-screener.yml (fallback, just RSI + volume)
      └─[fail]→ yesterday's picks (stale cache)
```

### 4.4 HF Validation (Test Failures = No Validation)

```
CURRENT:
  validate-hf-asset-class.yml → unit tests → report
  ❌ Unit tests failing (code bug)
  ❌ No validation output when tests fail

SHOULD BE:
  validate-hf-asset-class.yml (primary)
    └─[test fail]→ skip tests, run validation directly
      └─[fail]→ generate validation report from closed_picks.json
```

---

## 5. Jobs That Should Be Disabled

These workflows have 100% failure rates and should be disabled or removed to reduce noise:

| Workflow | Fail Rate | Action |
|----------|-----------|--------|
| 2-HOUR STRATEGY CHALLENGE (REAL DATA) | 10/10 (100%) | DISABLE or REMOVE |
| REAL 2-HOUR CHALLENGE | 10/10 (100%) | DISABLE or REMOVE |
| AsterDEX Paper Trader | 10/10 (100%) | Already marked DISABLED — remove from schedule |
| HC Nightly Rebuild | 10/10 (100%) | FIX or DISABLE |
| Weekly Score Quartile Spread | 1/1 (100%) | FIX or DISABLE |

---

## 6. Immediate Actions Required

### P0 — Fix Today (Strategy-Critical)

| # | Action | Workflow | Impact |
|---|--------|----------|--------|
| 1 | Fix `risk_metrics.py` crash | `alpha-weekly-validation.yml` | System has no risk metrics (100% failure) |
| 2 | Fix Dynamic Runner timeout/push | `dynamic-alpha-engine.yml` | Core scanner fails 60% of the time |
| 3 | Fix HF validation unit tests | `validate-hf-asset-class.yml` | Non-crypto picks unvalidated |
| 4 | Add fallback scanner for production | New workflow | Single point of failure for all picks |

### P1 — Fix This Week

| # | Action | Workflow | Impact |
|---|--------|----------|--------|
| 5 | Fix Walk-Forward Backtest | `walk-forward-backtest.yml` | No anti-overfitting validation |
| 6 | Fix STOCKSUNIFY daily pipeline | `stocks-daily-stocksunify.yml` | Equities pipeline unreliable |
| 7 | Fix Overnight Mutations | `overnight-mutations.yml` | Strategy evolution broken |
| 8 | Fix Monthly DNA Tournament | `monthly-tournament.yml` | Strategy selection broken |
| 9 | Disable 100% failure workflows | Multiple | Reduce noise, save Actions minutes |

### P2 — Structural Improvements

| # | Action | Impact |
|---|--------|--------|
| 10 | Add circuit breaker to production scanner | Auto-failover when primary fails |
| 11 | Add caching to all data workflows | Last-known-good fallback |
| 12 | Add health check workflow | Monitor all workflow failures centrally |
| 13 | Reduce total workflow count (284 → ~50) | Many are redundant or broken |

---

## 7. Data Source Dependency Map

```
CRITICAL PATH (no redundancy):

  Binance API
    └─→ production_scanner.py (Dynamic Runner, 60% failure)
          └─→ active_picks.json
                └─→ audit dashboard
                      └─→ EVERYTHING

  Yahoo Finance (yfinance)
    └─→ production_scanner.py (same SPOF above)
    └─→ risk_metrics.py (100% failure)
    └─→ walk-forward backtest (67% failure)

  GitHub Actions Runner
    └─→ ALL of the above
    └─→ 120-min timeout often insufficient
    └─→ Git push race conditions between concurrent runs
```

**The entire system depends on ONE workflow (`dynamic-alpha-engine.yml`) that fails 60% of the time, with no fallback.**

---

## 8. Quantified Impact

| Failure | Trades Affected | PnL Impact |
|---------|-----------------|------------|
| Dynamic Runner down (60% of time) | No new picks generated for ~14h/day | Missed opportunities |
| Weekly Validation broken (100%) | All strategies run without risk metrics | Can't detect degradation |
| HF Validation broken (80%) | Non-crypto HC picks unvalidated | False conviction signals |
| STOCKSUNIFY broken (60%) | Equities picks stale | Missing equity edge (+111% PnL system) |
| Walk-Forward broken (67%) | No anti-overfitting check | Overfit strategies trade live |

---

*This report should be reviewed weekly. Update status as fixes are deployed.*
