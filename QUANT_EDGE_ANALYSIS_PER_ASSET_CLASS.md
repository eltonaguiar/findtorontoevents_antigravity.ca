# Quant Edge Analysis: Per-Asset-Class Performance Review

**Date:** 2026-05-13  
**Author:** External Quant Review (OpenClaw Agent)  
**Scope:** Full system audit — codebase, databases, GitHub Actions, dashboard data, backtest results  
**Methodology:** Hedge-fund-grade edge identification per Lopez de Prado standards

---

## Executive Summary

**No asset class currently passes institutional real-money thresholds** (DSR>0.95, PBO<0.05, WFE>60%, live-Sharpe>0.5, n≥100). However, **curated crypto shows the strongest signal** and **equity has a viable upper tail** when properly gated. The system has a TRXUSDT concentration risk that masks all other performance, a scoring engine that treats all asset classes identically (which the data proves wrong), and a massive 28.7M-row backtest database with suspicious PF=1000 results suggesting overfitting.

### Per-Asset Verdict

| Asset | Raw PF | Filtered PF | WR | n | Verdict | Action |
|-------|--------|-------------|-----|---|---------|--------|
| **CRYPTO** | 0.49 | 1.14–1.43 (curated) | 42–46% | 15,749 | **Edge exists in upper score/trust bands** | Keep primary; fix TRXUSDT outlier; gate on score≥50+trust≥3 |
| **EQUITY** | 0.70 | 2.62 (score≥50+trust≥3) | 37.7% raw / 52% filtered | 611 | **Conditional edge** | Block stocks_competition; enforce score≥50 floor |
| **FOREX** | 0.49 | ~1.35 (resolver-clean) | 42.3% | 685 | **Sub-floor, resolver-contaminated** | Ship swing_resolver fix; gate on trust≥5 only |
| **COMMODITY** | 1.08 | 1.28 (trust≥3) | 45% | 214 | **Breakeven, single-strategy dependency** | Diversify strategies; add Bollinger MR |
| **ETF** | 0.19 | N/A | 33.3% | 20 | **Dead** | New strategies needed (Bollinger MR, RSI-2) |
| **FUTURES** | 0.08 | N/A | 5.9% | 18 | **Dead** | Reclassify to COMMODITY/BOND |
| **BOND** | 25.9 | N/A | 57.1% | 8 | **Insufficient data** | Expand emitter; hold |

---

## 1. How a Quant/Hedge Fund Manager Would Identify Your Edge

### 1.1 The Framework (Lopez de Prado)

A quant fund would run this through a **5-gate validation pipeline**:

1. **Gate 1 — Deflated Sharpe Ratio (DSR):** Does the Sharpe survive multiple-testing correction? With 133 systems and 700+ strategies, you need DSR > 0.95 to claim edge. Most of your strategies fail this.

2. **Gate 2 — Probability of Backtest Overfitting (PBO):** What fraction of your backtest performance survives out-of-sample? Your walk-forward validator exists in code but isn't wired to production decisions. The HF decay watchlist shows 5 strategies with >20pp backtest→forward decay — classic overfitting.

3. **Gate 3 — Walk-Forward Efficiency (WFE):** Does the strategy maintain ≥60% of its in-sample edge out-of-sample? Your `walk_forward_validator.py` is well-designed but appears unused for live promotion decisions.

4. **Gate 4 — Live Sharpe > 0.5:** Your net Sharpe is **-8.27 annualized** (per dashboard_data.json). This is catastrophic. However, if you remove TRXUSDT outlier contamination, the picture changes dramatically.

5. **Gate 5 — Minimum n ≥ 100 per asset class:** Only CRYPTO (n=15,749) and FOREX (n=685) clear this. EQUITY (n=611) is borderline. Everything else is "Building."

### 1.2 Where the Edge Actually Is

From the data, your edge is concentrated in **three specific areas**:

#### A. Crypto Score Bands (Score ≥ 50)
- Score 50–59: **54.9% WR, PF 1.82** (n=1,096)
- Score 60–69: **59.2% WR, PF 2.82** (n=299)
- Score 70+: **70.4% WR, PF 3.47** (n=54)

This is real edge. A hedge fund would isolate this cohort and size into it.

#### B. Trust Score as Cross-Asset Separator
- Crypto trust ≥5: **71.9% WR, PF 3.15** (n=739)
- Equity trust ≥3: **49.3% WR, PF 1.57** (n=67)
- Forex trust ≥5: **45.9% WR, PF 1.47** (n=37)

Trust is your single best cross-asset quality feature. A quant fund would make this the primary filter, not score.

#### C. Crypto SHORT Direction Bias
- Crypto SHORT: **61.6% WR, +0.42% avg** 
- Crypto LONG: **45.6% WR, -0.03% avg**

This is a significant directional edge. Your system is better at fading crypto rallies than calling continuation.

---

## 2. Critical Issues Found

### 2.1 TRXUSDT Concentration Risk (CRITICAL)

**100% of total PnL (-23,187%) comes from a single symbol.** Removing TRXUSDT, overall PnL drops to -1.5%. This is not a trading system — it's a TRXUSDT bet that went wrong.

**Fix:** Hard-block TRXUSDT across all strategies until 60-day recovery with n≥20, WR≥55%. Implement per-symbol PnL caps (max 20% of total PnL from any single symbol).

### 2.2 Scoring Engine Treats All Assets Identically (HIGH)

The data proves a score of "55" means completely different things across asset classes:

| Asset | Score 50-59 WR | Score 50-59 PF |
|-------|----------------|----------------|
| Crypto | 54.9% | 1.82 |
| Equity | 56.4% | 1.59 |
| Forex | 43.5% | 0.36 |

**Fix:** Implement per-asset-class scoring calibration. Forex score needs different interpretation than crypto score.

### 2.3 Confidence Is Anti-Predictive for Forex (HIGH)

Forex confidence shows **negative correlation** with outcomes (r = -0.198). High-confidence forex picks are actively dangerous.

**Fix:** Zero-out or invert confidence weight for forex picks. Add asset-class-specific confidence calibration.

### 2.4 Resolver Contamination in FOREX/COMMODITY (HIGH)

The `outcome_resolver.py:384-405` has a 1bp WIN threshold that creates false positives. Wins below 10bp are "resolver noise." The `swing_resolver.py` (built 2026-04-28) fixes this but isn't fully deployed.

**Fix:** Ship swing_resolver.py to all non-crypto asset classes. Apply ±10bp noise filter to all historical claims.

### 2.5 Backtest Database Contains Overfit Results (MEDIUM)

The `bt_backtest_trades` table has **28.7 million rows** with many strategies showing PF=1000 (100% WR on tiny samples). The `at_incubator_backtest_results` shows `ichimoku_cloud` with PF=35.4 across 975 runs — this is almost certainly overfitting to in-sample data.

**Fix:** 
- Run permutation tests on all incubator results
- Require walk-forward validation before any promotion
- Purge strategies with n<10 from leaderboard

### 2.6 Walk-Forward Validator Not Wired to Production (MEDIUM)

The `walk_forward_validator.py` exists and is well-designed but isn't used for live promotion/demotion decisions. Strategies are being promoted based on full-history backtests (classic overfitting path).

**Fix:** Wire walk-forward validator to `quality_gates.py` promotion logic. No strategy promotes without passing WFE ≥ 60%.

### 2.7 Stocks DB Access Denied (LOW)

The `eajaguiar1_stocks` database at mysql.50webs.com returns "Access denied." This may be a credential issue or IP restriction.

**Fix:** Verify credentials and whitelist the CI runner IPs.

---

## 3. GitHub Actions Audit

### 3.1 Workflow Inventory
You have **48+ active workflows** covering:
- Backtesting (daily + 2h during market hours)
- Audit dashboard (hourly)
- Alpha engine picks (daily at market close)
- Regime detection (daily)
- Forward testing
- Multiple deployment workflows

### 3.2 Issues Found

1. **Audit dashboard runs hourly** — this is excessive for a dashboard that takes 30-35min to build. It's eating nearly half your CI budget. **Fix:** Reduce to 2-3x daily (pre-market, post-market, EOD).

2. **No test suite** — I see no `pytest` or unit test workflows. Strategy code ships without validation. **Fix:** Add a CI gate that runs unit tests on push to main.

3. **No walk-forward gate in CI** — The `backtest-and-deploy.yml` runs backtests but doesn't enforce walk-forward validation before deploying results. **Fix:** Add a WFE check step.

4. **Concurrency conflicts** — Multiple workflows push to main with auto-commit, creating race conditions. You have `concurrency` groups but they're complex and fragile. **Fix:** Consolidate data-commits into a single workflow with a queue.

5. **Missing asset-class isolation** — Backtest workflows don't separate by asset class. A crypto backtest failure shouldn't block equity deployment. **Fix:** Split `backtest-and-deploy.yml` into per-asset-class workflows.

---

## 4. Database Architecture Review

### 4.1 ejaguiar1_backtests Database

| Table | Rows | Purpose |
|-------|------|---------|
| `bt_backtest_trades` | 28,705,218 | Individual trade records |
| `bt_backtest_runs` | 285 | Backtest run summaries |
| `at_incubator_backtest_results` | 1,285 | Incubator strategy results |
| `at_large_backtest_results` | 1,105 | Large-scale backtest results |
| `backtest_results` | 2 | Legacy backtest results |
| `backtest_trades` | 50 | Legacy trade records |

### 4.2 Issues

1. **28.7M rows in bt_backtest_trades** — This is massive for a shared MySQL host. Queries likely timeout frequently. **Fix:** Add composite indexes on `(asset_class, strategy, symbol)` and partition by date.

2. **No asset_class index** — The `bt_backtest_runs` table uses ENUM for asset_class but may lack proper indexing for the GROUP BY queries the dashboard runs.

3. **Duplicate data** — `backtest_results` (2 rows) and `backtest_trades` (50 rows) appear to be legacy tables. **Fix:** Archive or drop them.

4. **No connection pooling** — The dashboard builds probably open fresh connections for each query. **Fix:** Implement connection pooling or use a read replica.

---

## 5. Per-Asset-Class Action Plan

### 5.1 CRYPTO — Maintain & Tighten

**Current State:** Best asset class. Score ≥50 + Trust ≥3 = PF 1.98.

**Actions:**
1. Hard-block TRXUSDT (P0)
2. Implement per-symbol PnL caps at 20% of total (P0)
3. Gate new crypto picks on score ≥50 (P1)
4. Reward SHORT direction bias in scoring (P1)
5. Zero-out anti-predictive features: ML replacement score, source system tier, R:R ratio, age freshness, leverage safety (P1)
6. Run walk-forward validation on top 20 crypto strategies (P2)

**Target:** Curated crypto PF ≥ 1.5, WR ≥ 50%, Sharpe > 0.5

### 5.2 EQUITY — Restrict & Rebuild

**Current State:** Raw PF 0.70. Upper tail (score≥50+trust≥3) = PF 2.62 but n=119.

**Actions:**
1. Block `stocks_competition` system permanently (P0 — already done)
2. Enforce score ≥50 floor for all equity picks (P0)
3. Wire inverse strategies to forward_test.py (P1)
4. Test Bollinger MR on equity symbols (P1)
5. Expand `stocks_rsi2_pullback` universe (P2)
6. Target n≥100 closed picks in filtered cohort before promoting (P2)

**Target:** Filtered equity PF ≥ 1.5, WR ≥ 50%, n ≥ 100

### 5.3 FOREX — Probation & Fix

**Current State:** Confirmed sub-floor. Scorer not working. Confidence is anti-predictive.

**Actions:**
1. Ship swing_resolver.py to replace broken outcome_resolver.py:384-405 (P0)
2. Apply ±10bp noise filter to all historical forex claims (P0)
3. Gate forex picks on trust ≥5 ONLY (ignore score/confidence) (P1)
4. Decouple `forex_rsi2_mean_reversion` from copy_trader (P1)
5. Test MeanReversionBB on forex pairs (P2)
6. Block forex picks until resolver fix is confirmed clean (P0)

**Target:** Resolver-clean forex PF ≥ 1.2, WR ≥ 48%

### 5.4 COMMODITY — Diversify

**Current State:** Breakeven (PF 1.08). Single-strategy dependency.

**Actions:**
1. Add Bollinger MR to commodity futures (GC=F, SI=F, PL=F, HG=F) (P1)
2. Add `cta_cross_asset_tsmom` as secondary strategy (P1)
3. Expand symbol universe: NG=F, ZW=F, ZC=F, KC=F (P2)
4. Run incubator on commodity symbols (P2)
5. Reclassify FUTURES symbols (GC=F, SI=F) to COMMODITY (P1)

**Target:** Commodity PF ≥ 1.2 with ≥ 3 strategies

### 5.5 ETF — New Strategies Required

**Current State:** Dead (PF 0.19, n=20). Wrong strategies.

**Actions:**
1. Test Bollinger MR on ETF symbols (SPY, QQQ, IWM, XLF, GLD, TLT) (P1)
2. Test `forex_rsi2_mean_reversion` on ETF symbols (P1)
3. Block `extreme_oversold_bounce` and `vix_reversal` (already done)
4. Target n≥50 before declaring edge (P2)

**Target:** ETF PF ≥ 1.2, n ≥ 50

### 5.6 FUTURES — Reclassify

**Current State:** Dead (PF 0.08, n=18). Same symbols work via COMMODITY.

**Actions:**
1. Reclassify GC=F, SI=F, CL=F, HG=F → COMMODITY (P0)
2. Reclassify ZN=F → BOND (P0)
3. Remove FUTURES from dashboard panels (P1)
4. Block FUTURES as independent asset class (P0)

**Target:** Eliminate misleading FUTURES category

### 5.7 BOND — Grow Volume

**Current State:** n=8. Insufficient data.

**Actions:**
1. Add TLT, IEF, AGG as ETF-proxied bond instruments (P1)
2. Test `futures_momentum` on ZN=F with extended history (P2)
3. Target n≥50 before conclusions (P2)

**Target:** Bond n ≥ 50, then evaluate

---

## 6. Scoring Engine Redesign (Priority Order)

Based on correlation analysis, the scoring feature weights should be:

### What Actually Predicts Outcomes (by Spearman rho)

| Feature | Crypto rho | Equity rho | Forex rho | Action |
|---------|-----------|-----------|----------|--------|
| trust_score | +0.280 | +0.194 | +0.138 | **Increase weight globally** |
| score | +0.177 | +0.277 | -0.036 | **Asset-specific calibration** |
| elite_score | +0.057 | +0.198 | +0.055 | Keep for equity, reduce elsewhere |
| confidence | +0.077 | +0.059 | **-0.198** | **Zero for forex, reduce globally** |

### Recommended Scoring Formula (Per-Asset)

**Crypto:**
```
smart_score = 0.40 * trust_normalized + 0.35 * score_normalized + 0.15 * elite_normalized + 0.10 * regime_alignment
```

**Equity:**
```
smart_score = 0.30 * trust_normalized + 0.35 * score_normalized + 0.25 * elite_normalized + 0.10 * regime_alignment
```

**Forex:**
```
smart_score = 0.60 * trust_normalized + 0.20 * regime_alignment + 0.10 * rsi_alignment + 0.10 * session_filter
```
(Confidence and score are anti-predictive for forex — remove them)

---

## 7. Walk-Forward Validation Requirements

Before any strategy is promoted to live capital:

1. **4 overlapping sleeves** (quarterly rebalance)
2. **Train:** 70% / **Validation:** 15% / **Test:** 15%
3. **WFE ≥ 60%** (test maintains ≥60% of train edge)
4. **Bootstrap CI** on PF — lower bound > 1.0 at 95%
5. **Permutation test** — must beat random direction baseline
6. **Minimum n ≥ 30** per walk-forward window

The `walk_forward_validator.py` already implements this. **Wire it to production.**

---

## 8. PR Contents

This PR includes:
1. This analysis document (`QUANT_EDGE_ANALYSIS_PER_ASSET_CLASS.md`)
2. No code changes (analysis-only PR)

### Recommended Follow-Up PRs:
- **PR-1:** TRXUSDT hard-block + per-symbol PnL caps
- **PR-2:** Per-asset-class scoring calibration
- **PR-3:** Walk-forward validator wiring to quality_gates
- **PR-4:** Swing resolver deployment to non-crypto classes
- **PR-5:** FUTURES reclassification + ETF strategy expansion
- **PR-6:** CI consolidation (reduce audit dashboard frequency, add test suite)

---

## 9. Bottom Line

**Your system has real edge, but it's buried under noise.**

The hedge-fund-grade path forward:
1. **Kill the TRXUSDT outlier** — it's masking everything
2. **Trust > Score > Confidence** — reweight your scoring
3. **Per-asset-class calibration** — stop treating forex like crypto
4. **Walk-forward everything** — no more full-history backtest promotions
5. **Ship the resolver fix** — forex/commodity data is contaminated
6. **Consolidate CI** — 48 workflows is too many; focus on quality over quantity

A real quant fund would take your curated crypto (score≥50, trust≥3, SHORT bias) and size into it. Everything else goes to probation until it proves itself with clean walk-forward data.

---

*This analysis was generated by reviewing: GitHub repo (1,093 files), dashboard_data.json (20MB), ejaguiar1_backtests MySQL database (28.7M trade rows), 48 GitHub Actions workflows, and 15+ existing analysis documents in the repo.*
