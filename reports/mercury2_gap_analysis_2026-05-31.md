# Mercury 2 Gap Analysis — From "Coin Flip" to Production-Ready
**Generated: 2026-05-31 | Buffy (deepseek-v4-pro) | Branch: `blackboxai/gha-heatlh-fixes`**

---

## Executive Summary

The Mercury 2 roadmap is ambitious but **~60% of the infrastructure already exists** in the codebase. The gap is not in building new engines — it's in **connecting, hardening, and enforcing** what's already built. Below is a line-by-line cross-reference.

---

## 1. Secure Foundations

| Mercury 2 Item | Status | Reality |
|---|---|---|
| DB credentials in GitHub Secrets | 🔴 **PARTIAL** | `edge_significance_gate.py` hardcodes `mysql.50webs.com` credentials in plaintext (line 22). `dbpasses.txt` exists on disk. Secrets needed. |
| AI API keys in Secrets | 🟡 **PARTIAL** | Some workflows use `secrets.*`, others likely hardcoded. Full audit needed. |
| Backup before destructive ops | 🔴 **MISSING** | No stored-procedure or automated backup pattern found. |
| Version-controlled docs | 🟢 **DONE** | `docs/` folder + AGENTS.md conventions exist. |

**Priority action:** Move `edge_significance_gate.py` credentials to env vars from GitHub Secrets.

---

## 2. Automated Data Refresh & Auditing

| Item | Status | Reality |
|---|---|---|
| GHA pipeline (cron every 4h) | 🟢 **DONE** | Multiple workflows: `audit-dashboard.yml` (hourly), `smart-picks-tracker.yml`, `pick-funnel-nightly.yml` |
| Raw market data fetch | 🟢 **DONE** | `alpha_engine/production_scanner.py` fetches and normalizes |
| Back-test suite per AI model | 🟡 **PARTIAL** | `alpha_engine/anti_overfit_gate.py` has 8-check suite but NOT run per-model automatically |
| Audit page timestamp | 🔴 **MISSING** | No `<time>` element or DB audit_log timestamp injection found in `dashboard_enhancements.js` |
| Filter-permutation logging | 🟡 **PARTIAL** | `extract_funnel.py` extracts filter data but no `data-filter-id` onclick instrumentation found in JS |

**Priority action:** Add auto-timestamp to `/audit` pages + instrument filter clicks.

---

## 3. Robust Back-Testing Framework

| Item | Status | Reality |
|---|---|---|
| Backtrader/Docker engine | 🔴 **MISSING** | No Docker container for back-testing. Backtests run ad-hoc via scripts. |
| Parallel execution (GHA matrix) | 🟡 **PARTIAL** | GHA matrix exists but not for Dockerized back-tests |
| Data integrity (no look-ahead) | 🟢 **DONE** | `anti_overfit_gate.py` checks OOS/IS correlation, KS test, walk-forward windows |
| Versioned results in DB | 🟡 **PARTIAL** | `backtest_results` table exists via `ejaguiar1_backtests` but not universally used |

---

## 4. Statistical Validation & Edge Detection

This is the **strongest area** — significant infrastructure already exists:

### 4.1 Core Metrics

| Metric | Engine | File |
|---|---|---|
| Win Rate (WR) | ✅ | `edge_analysis.py`, `statistical_validator.py` |
| Profit Factor (PF) | ✅ | Dashboard + audit_trail resolver |
| Sharpe Ratio | ✅ | `edge_significance_gate.py` (Gate 3: bootstrap Sharpe) |
| Sortino Ratio | 🔴 **MISSING** | No downside-only volatility calc |
| Max Drawdown (MaxDD) | ✅ | `drawdown_tracker.py` |
| Calmar Ratio | 🔴 **MISSING** | No CAGR/MaxDD ratio |

### 4.2 Significance Testing

| Test | Status | File |
|---|---|---|
| Binomial test (WR > 50%) | ✅ | `statistical_validator.py:31-39`, `edge_significance_gate.py:25-30` |
| t-test (mean PnL > 0) | ✅ | `edge_significance_gate.py:32-40` |
| Bootstrap CI for Sharpe | ✅ | `statistical_validator.py:42-47`, `edge_significance_gate.py` Gate 3 |
| Wilson CI (WR lower bound) | ✅ | `edge_analysis.py:50-58`, `edge_significance_gate.py:42-48` |
| KS test (IS vs OOS) | ✅ | `anti_overfit_gate.py` (check #7) |
| Monte Carlo random strategy | 🔴 **MISSING** | No random-pick simulation to control for data-snooping |
| Benjamini-Hochberg FDR | 🔴 **MISSING** | No multiple-testing correction applied |

### 4.3 Sample-Size Requirements

| Gate | Current | Mercury 2 Target | Gap |
|---|---|---|---|
| Minimum trades | 30 (`statistical_validator.py`) or 20 (`edge_analysis.py`) | 500 resolved trades | **17-25× gap** |
| WR significance | p < 0.05 binomial | WR > 0.55 AND p < 0.05 | Threshold mismatch |
| Sharpe CI | Bootstrap CI excludes 0 | Sharpe > 0.8 AND 95% CI excludes 0 | Threshold mismatch |

**The 500-trade minimum is the single largest gap.** The current 30-trade floor is too permissive.

---

## 5. Edge-Verification Workflow

| Step | Status | Engine |
|---|---|---|
| In-sample back-test (2018-2022) | 🟡 **PARTIAL** | Ad-hoc scripts, no standardized IS period |
| Out-of-sample forward test (2023-2024) | ✅ | `anti_overfit_gate.py` 8-check suite |
| Walk-forward validation | ✅ | `anti_overfit_gate.py` check #1-8, check #8: ≥67% OOS windows profitable |
| Statistical gate promotion | 🟡 **PARTIAL** | `edge_significance_gate.py` assigns Tier-1/Tier-2 but NOT enforced as Live gate |
| Robustness checks (randomized dates, regime sub-sampling) | 🔴 **MISSING** | No regime-split validation found |

---

## 6. Portfolio Construction & Risk Management

| Layer | Status | File |
|---|---|---|
| Position sizing (volatility-parity) | 🟡 **PARTIAL** | `position_sizing.py` exists but integration unclear |
| Kelly fraction (capped 2%) | 🟡 **PARTIAL** | Same file, enforcement unclear |
| Gross exposure ≤ 150% | 🔴 **MISSING** | No cap found in lifecycle engine |
| Per-position weight ≤ 5% | 🔴 **MISSING** | No cap found |
| Max drawdown per model ≤ 10% | 🟡 **PARTIAL** | `drawdown_tracker.py` tracks but doesn't halt |
| Daily loss limit ≤ 2% | 🔴 **MISSING** | No circuit breaker |
| ≥3 distinct asset classes | 🔴 **MISSING** | No diversification enforcement |
| Slippage + commission simulation | 🔴 **MISSING** | Not in position sizing |

**Note:** User reports model portfolio automation is **broken** — NAV shows $100,000.00 unchanged since May 28.

---

## 7. Production Deployment

| Item | Status |
|---|---|
| Docker containerization | 🔴 **MISSING** |
| K8s/ECS orchestration | 🔴 **MISSING** |
| Prometheus + Grafana | 🔴 **MISSING** |
| Alertmanager (drawdown alerts) | 🔴 **MISSING** |
| Immutable audit_log | 🟡 **PARTIAL** — `audit_log.py` exists but scope unclear |
| S3 off-site snapshots | 🔴 **MISSING** |

---

## 8. Governance & Documentation

| Artifact | Status |
|---|---|
| Model Specification docs | 🟡 Some exist in `docs/` |
| Risk-Management Policy | 🔴 **MISSING** |
| Back-test Results Archive | 🟡 In `ejaguiar1_backtests` DB |
| Leaderboard Methodology | 🟢 AI leaderboard page exists |
| API Key Rotation Log | 🔴 **MISSING** |

---

## 9. Continuous Improvement Loop

| Step | Status |
|---|---|
| Live → training set feedback | 🔴 **MISSING** — no automated feedback loop |
| A/B test live vs research (5% capital slice) | 🔴 **MISSING** |
| Adaptive statistical gates | 🔴 **MISSING** |

---

## 10. Immediate Priority Roadmap (Ordered)

### 🔴 P0 — Fix What's Broken (This Week)
1. **Fix model portfolio lifecycle** — NAV frozen at $100K since May 28, no trades processing
2. **Move hardcoded DB credentials to GitHub Secrets** (`edge_significance_gate.py` line 22)
3. **Add timestamp to `/audit` pages** (simple `<time>` injection in `dashboard_enhancements.js`)

### 🟡 P1 — Enforce What Exists (This Month)
4. **Raise statistical gate minimum from 30→200 trades** (increment toward 500)
5. **Wire `anti_overfit_gate.py` as HARD GATE** for all Smart Picks (already built, just needs enforcement at the emission point)
6. **Add filter-click instrumentation** with `data-filter-id` attributes + fetch POST logger
7. **Wire `drawdown_tracker.py` as circuit breaker** — halt model when DD > 10%
8. **Fix `CONFIDENCE_INVERT_CRYPTO=0`** ✅ **DONE** (this session, PR #227)

### 🟢 P2 — Build Missing Critical Infrastructure (Next Quarter)
9. **Implement Monte Carlo random-strategy baseline** — critical for anti-data-snooping
10. **Add Benjamini-Hochberg FDR correction** — prevents false discoveries from multiple testing
11. **Add Sortino + Calmar ratios** to edge significance gate
12. **Implement regime-split validation** (bull/bear/neutral sub-sampling)
13. **Dockerize back-test engine** with GHA matrix parallelization

### 🔵 P3 — Production Hardening (Quarter+)
14. **Grafana + Prometheus dashboards** for live NAV monitoring
15. **Alertmanager** for drawdown > 10% or WR CI crossing 0.5
16. **K8s deployment** with zero-downtime updates
17. **A/B testing framework** (5% capital slice for research models)
18. **S3 off-site backups** of audit_log and backtest archives

---

## Summary Statistics

| Category | Built | Partial | Missing |
|---|---|---|---|
| Foundations | 1 | 2 | 1 |
| Data Refresh/Audit | 2 | 2 | 1 |
| Back-Testing | 1 | 2 | 1 |
| Statistical Validation | 7 | 1 | 2 |
| Edge Verification | 2 | 2 | 1 |
| Portfolio/Risk | 0 | 3 | 5 |
| Production | 0 | 1 | 4 |
| Governance | 1 | 2 | 2 |
| Continuous Improvement | 0 | 0 | 3 |
| **TOTAL** | **14 (29%)** | **15 (31%)** | **20 (41%)** |

**Verdict:** The statistical and edge-detection engine is strong (7 of 10 metrics built). The gaps are in **enforcement** (gates exist but aren't wired), **scale** (sample-size thresholds too low), and **production** (no Docker, monitoring, or feedback loops). The fastest path to profit is not building new engines — it's **turning on the gates that already exist**.

---

## Files Referenced
- `alpha_engine/statistical_validator.py` — binomial + bootstrap tests, 30-trade minimum
- `alpha_engine/anti_overfit_gate.py` — 8-check walk-forward validation, fail-closed gate
- `alpha_engine/edge_analysis.py` — multi-dimensional edge analysis (WR, confidence, direction, symbol, time)
- `tools/ai_tournament/edge_significance_gate.py` — 4-gate framework (⚠️ hardcoded DB credentials)
- `alpha_engine/position_sizing.py` — volatility-parity + Kelly fraction sizing
- `alpha_engine/drawdown_tracker.py` — maxDD + daily loss tracking
- `tools/edge_filter_engine_v3.py` — pick filtering engine
- `tools/audit_pick_funnel/extract_funnel.py` — pick funnel data extraction
- `audit_trail/audit_log.py` — audit trail logging
- `audit_dashboard/dashboard_enhancements.js` — client-side audit page (needs timestamp + filter instrumentation)
- `.github/workflows/smart-picks-tracker.yml` — PR #227 fix applied (CONFIDENCE_INVERT_CRYPTO=0)
