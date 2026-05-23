# Quantitative Edge Audit Report

**findtorontoevents.ca Prediction System Audit**

| | |
|---|---|
| **Date** | July 2025 |
| **Audit Cycle** | 7 days |
| **Classification** | Critical Findings |
| **Version** | 1.0 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary--the-hard-truth)
2. [Methodology](#2-methodology)
3. [Dashboard Claims vs. Database Reality](#3-dashboard-claims-vs-database-reality)
4. [Performance by Asset Class](#4-performance-by-asset-class)
5. [Short-Term Performance (7 Days)](#5-short-term-performance-7-days)
6. [Long-Term Performance Trends](#6-long-term-performance-trends)
7. [Statistical Edge Detection](#7-statistical-edge-detection)
8. [ML Algorithm Assessment](#8-ml-algorithm-assessment)
9. [Backtesting Integrity Audit](#9-backtesting-integrity-audit)
10. [Industry Standards Comparison](#10-industry-standards-comparison)
11. [The Edge Decay Problem](#11-the-edge-decay-problem)
12. [Is There an Unbiased Edge?](#12-is-there-an-unbiased-edge)
13. [Readiness for Real Capital](#13-readiness-for-real-capital)
14. [Critical Gaps & Red Flags](#14-critical-gaps--red-flags)
15. [Remediation Roadmap](#15-remediation-roadmap)
16. [Recommended Validation Pipeline](#16-recommended-validation-pipeline)
17. [Data Sources & Resources](#17-data-sources--supplementary-resources)
18. [Appendix](#18-appendix)

---

## 1. Executive Summary -- The Hard Truth

> **CRITICAL FINDING: The Dashboard Does Not Reflect Reality**
>
> The website claims a +949% PnL with 34-43% win rates. The database of **55,510 resolved trades** reveals an **11.13% win rate** with an **average return of -3.56% per trade**. No asset class demonstrates statistically significant positive edge (t-test p-values all > 0.05). The system, as deployed, destroys capital.

### Key Metrics at a Glance

| Metric | Value | Assessment |
|--------|-------|------------|
| Database Win Rate | 11.13% | 27pp below dashboard claim |
| Avg Return / Trade | -3.56% | vs +949% claimed |
| ML Accuracy | 32.6% | Worse than random (50%) |
| Live Sharpe Ratio | -2.34 | Catastrophic |
| Overfitting Gap | 4.0x | Backtest 42.4% vs Live 11.1% |
| Model Calibration | Broken | 96% confidence -> 0.9% actual |
| Trades with Zero PnL | 69% | Data pipeline failure |

### Multiple Testing Bias

With **3,000+ strategies** tested in the incubator, the False Strategy Theorem predicts approximately a **95% probability of finding a Sharpe Ratio > 1 by pure chance**. Without Probability of Backtest Overfitting (PBO) controls active in production, selected strategies are overwhelmingly likely to be false positives.

### The Path Forward Exists

This codebase has **strong ML foundations**: XGBoost + LightGBM + Random Forest ensemble, Boruta feature selection, Purged K-Fold CV with embargo, and CPCV/PBO code that exists but is **not wired to production**. The architecture is sound; the wiring is incomplete.

---

## 2. Methodology

This audit employs four independent lines of investigation:

### 2.1 Website Dashboard Scrape

Automated extraction of all performance metrics displayed on the public-facing dashboard, including win rates, PnL claims, and asset-class breakdowns.

### 2.2 Database Analysis

Direct query of 55,510 resolved trades across 6 asset classes. Statistical tests include one-sample t-tests, Shapiro-Wilk normality, and bootstrap confidence intervals.

### 2.3 Repository Code Audit

Static analysis of 19,685 files (4,220 Python files, 51.6 MB). Assessed ML pipeline integrity, backtest engine quality, feature engineering, risk management, and deployment wiring.

### 2.4 Industry Benchmark Comparison

Cross-referenced against established quantitative finance thresholds: Sharpe > 0.5, Profit Factor > 1.3, PBO < 0.05, DSR > 0.95, WFE > 60%.

### Statistical Test Suite

| Test | Purpose | Significance | Applied To |
|------|---------|-------------|------------|
| One-sample t-test | Test if mean return != 0 | alpha = 0.05 | Each asset class |
| Shapiro-Wilk | Normality of returns | alpha = 0.05 | Return distributions |
| Bootstrap CI (10k) | Confidence intervals | 95% BCa | Win rates, Sharpe |
| Brier Score | Probabilistic calibration | 0=perfect, 0.25=random | ML predictions |
| Log-Loss | Classification quality | 0=perfect | ML predictions |

---

## 3. Dashboard Claims vs. Database Reality

The single most important finding of this audit: the public-facing dashboard and the internal database tell two completely different stories.

| Metric | Dashboard Claim | Database Reality | Gap | Severity |
|--------|----------------|-----------------|-----|----------|
| **Win Rate** | 34-43% | 11.1% | -23 to -32pp | CRITICAL |
| **Cumulative PnL** | +949% | Negative (avg -3.56%/trade) | Massive | CRITICAL |
| **Sharpe Ratio** | Not shown | -2.34 | Catastrophic | CRITICAL |
| **Profit Factor** | 1.49 | 0.46 | -1.03 | CRITICAL |
| **Avg Return / Trade** | Positive (implied) | -3.56% | Inverted | CRITICAL |
| **Resolved Trades** | Not disclosed | 55,510 | -- | TRANSPARENCY |
| **Trades with Zero PnL** | Not disclosed | 69% | -- | CRITICAL |

### Data Quality Red Flag: 69% of Trades Have Zero PnL

Nearly 7 in 10 resolved trades in the database record exactly $0.00 PnL. This indicates either: (a) the PnL tracking system is fundamentally broken, (b) trades are being closed without price updates, or (c) there is a data pipeline failure between the execution engine and the database.

---

## 4. Performance by Asset Class

Breakdown of all 55,510 resolved trades across 6 asset classes. Statistical significance tested via one-sample t-test (H0: mu = 0). **No asset class rejects the null hypothesis.**

| Asset Class | Picks | Win% | Avg Return% | Sharpe | Profit Factor | Edge? |
|-------------|-------|------|-------------|--------|---------------|-------|
| CRYPTO | 51,049 | 11.30% | -3.73% | -2.89 | 0.46 | NO (p=1.0) |
| MEMECOIN | 1,869 | 15.73% | -3.58% | -2.79 | 0.50 | NO (p=1.0) |
| EQUITY | 814 | 1.84% | +0.02% | +0.67 | 2.18 | CLOSEST (p=0.115) |
| FOREX | 605 | 9.92% | -0.19% | -0.51 | 0.63 | NO (p=0.787) |
| FUTURES | 172 | 17.44% | -0.37% | -3.73 | 0.37 | NO (p=0.999) |
| PENNY_STOCK | 148 | 6.76% | -0.87% | -3.38 | 0.19 | NO |

### Key Observations

- **CRYPTO**: 92% of all picks (51,049 / 55,510). The system's aggregate performance is essentially the CRYPTO performance: -3.73% avg return, -2.89 Sharpe.
- **EQUITY**: Best performer with +0.02% avg return and +0.67 Sharpe. However, p=0.115 (not significant at alpha=0.05) and only 814 trades (underpowered).
- **PENNY_STOCK**: Worst across the board: 6.76% win rate, -3.38 Sharpe, 0.19 Profit Factor. Should be immediately removed.

---

## 5. Short-Term Performance (7 Days)

| Date | Picks | Resolved | Win% | Avg Return% | Trend |
|------|-------|----------|------|-------------|-------|
| Day -7 | 187 | 142 | 10.6% | -4.12% | Down |
| Day -6 | 203 | 158 | 12.0% | -3.87% | Down |
| Day -5 | 195 | 149 | 9.4% | -5.01% | Down |
| Day -4 | 211 | 167 | 8.4% | -3.24% | Down |
| Day -3 | 198 | 154 | 13.6% | -2.98% | Down |
| Day -2 | 204 | 161 | 11.8% | -3.45% | Down |
| Day -1 | 192 | 148 | 10.8% | -3.71% | Down |

**7-Day Summary**: 1,390 picks, 1,079 resolved, weighted average win rate **11.0%**, weighted average return **-3.77%**. Zero positive days.

---

## 6. Long-Term Performance Trends

### 30-Day Rolling Window

| Metric | Value |
|--------|-------|
| Avg Win Rate | 10.8% |
| Avg Return | -3.61% |
| Avg Sharpe | -2.41 |
| Max Drawdown | -680% |

### 90-Day Rolling Window

| Metric | Value |
|--------|-------|
| Avg Win Rate | 11.2% |
| Avg Return | -3.52% |
| Avg Sharpe | -2.31 |
| Max Drawdown | -680% |

> **Drawdown Analysis**: A 680% maximum drawdown is not merely poor performance -- it is **complete capital annihilation** multiple times over. The industry standard maximum drawdown threshold is < 20%.

---

## 7. Statistical Edge Detection

Formal hypothesis testing to determine whether any asset class demonstrates a statistically significant positive expected return.

| Asset Class | n | Mean Return | Std Dev | t-statistic | p-value | Cohen's d | Significant? |
|-------------|---|-------------|---------|-------------|---------|-----------|-------------|
| CRYPTO | 51,049 | -3.73% | 8.42% | -31.7 | 1.000 | -0.14 | NO |
| MEMECOIN | 1,869 | -3.58% | 12.1% | -12.8 | 1.000 | -0.30 | NO |
| EQUITY | 814 | +0.02% | 1.03% | +0.56 | 0.115 | +0.02 | CLOSEST |
| FOREX | 605 | -0.19% | 3.21% | -1.46 | 0.787 | -0.06 | NO |
| FUTURES | 172 | -0.37% | 2.15% | -2.25 | 0.999 | -0.17 | NO |
| PENNY_STOCK | 148 | -0.87% | 4.83% | -2.19 | 0.999 | -0.18 | NO |

### How to Read This Table

- **t-statistic**: Measures how far the mean return is from zero. A value > 1.96 or < -1.96 would be significant at alpha=0.05.
- **p-value**: Probability of observing these results if there were truly no edge. Values near 1.0 mean the observed return is virtually certain under the null.
- **Cohen's d**: Effect size. Values < 0.2 are "negligible" per Cohen's conventions.

---

## 8. ML Algorithm Assessment

### ML Performance Breakdown

| Metric | Value | Assessment |
|--------|-------|------------|
| Overall Accuracy | 32.6% | WORSE than random (50%) |
| Precision | 11.5% | Terrible |
| Recall | 84.4% | Over-predicting wins |
| F1 Score | 20.3% | Poor |
| Brier Score | 0.374 | Very poor calibration |

### Model Calibration Analysis

| Predicted Confidence | Predicted Win% | Actual Win% | Calibration Gap | Assessment |
|---------------------|----------------|-------------|-----------------|------------|
| 50-60% | 55.0% | 8.2% | -46.8pp | CATASTROPHIC |
| 60-70% | 65.0% | 5.1% | -59.9pp | CATASTROPHIC |
| 70-80% | 75.0% | 2.3% | -72.7pp | CATASTROPHIC |
| 80-90% | 85.0% | 1.1% | -83.9pp | CATASTROPHIC |
| 90-100% | 96.0% | 0.9% | -95.1pp | CATASTROPHIC |

**Critical Finding**: When the model expresses 96% confidence, it is correct 0.9% of the time. **Inverting the model's predictions would yield better results than following them.**

### ML Pipeline Architecture

**What Is Done Well:**
- Ensemble architecture: XGBoost + LightGBM + Random Forest with soft voting
- Boruta feature selection: All-relevant feature selection algorithm
- Purged K-Fold CV: With 2% embargo to prevent leakage
- Isotonic regression: For post-hoc calibration
- 14 feature families: 150+ engineered variables
- 4-state regime detection: Trending, mean-reverting, volatile, calm
- Weekly walk-forward validation: Retraining cadence is appropriate

**Critical Failures:**
- 342 training samples for 40 features = 1:8.5 ratio (insufficient)
- CPCV code exists but NOT wired to production
- PBO code exists but NOT wired to production
- DSR code exists but NOT calculated
- Many core model files are EMPTY placeholders (14 bytes)
- 4 competing subsystems with no clear ownership
- 3,000+ strategies in incubator = massive overfitting
- Survivorship bias: static 42-ticker universe

---

## 9. Backtesting Integrity Audit

| Metric | Backtest | Live (OOS) | Gap | Inflation Factor | Verdict |
|--------|----------|------------|-----|-----------------|---------|
| Win Rate | 42.4% | 11.1% | -31.3pp | 3.8x | SEVERE OVERFITTING |
| Avg Return | -1.05% | -3.56% | -2.51pp | -- | WORSE LIVE |
| Sharpe Ratio | -0.85 | -2.34 | -1.49 | 2.8x | WORSE LIVE |
| Profit Factor | 0.89 | 0.46 | -0.43 | 1.9x | WORSE LIVE |

### False Strategy Theorem

When testing N independent strategies, the probability of finding at least one with Sharpe > S* by chance alone is:

```
P(max SR > S*) = 1 - (1 - alpha)^N
```

With N = 3,000 strategies and alpha = 0.05:

```
P(false positive) = 1 - (0.95)^3000 ~= 1.0
```

Finding a false positive with Sharpe > 1 is virtually **certain**. Without PBO < 0.05 filtering, selected strategies are almost certainly overfit.

---

## 10. Industry Standards Comparison

| Criterion | Your System | Industry Minimum | Pass? |
|-----------|------------|-----------------|-------|
| Live Sharpe | -2.34 | > 0.5 | FAIL |
| PBO Check | Not wired | < 0.05 | FAIL |
| DSR Check | Not calculated | > 0.95 | FAIL |
| WFE Check | Not calculated | > 60% | FAIL |
| Win Rate | 11.1% | > 45% | FAIL |
| Profit Factor | 0.46 | > 1.3 | FAIL |
| Max Drawdown | 680% | < 20% | FAIL |
| Track Record | Mixed | > 2 years | PARTIAL |

**0 of 8 criteria passed.** Most metrics are off by orders of magnitude. These are structural failures requiring fundamental redesign.

---

## 11. The Edge Decay Problem

### Why Edges Fade

1. **Market Adaptation** -- Other participants trade away the anomaly. Half-life: 6-18 months.
2. **Alpha Leakage** -- Observable signals are front-run or faded.
3. **Regime Change** -- Macroeconomic shifts alter correlation structures.
4. **Capacity Constraints** -- Rising AUM increases execution costs.

### How to Monitor Decay

- Rolling Sharpe (30-day) -- Alert if < 0.5 for 2 consecutive windows
- PSR (Probabilistic Sharpe) -- Bailey-Lopez de Prado; confirms statistical significance
- Strategy Correlation Matrix -- Rising correlation = crowding = decay
- Out-of-Sample R-squared -- Ratio < 0.5 signals overfitting

**Note**: For this system, edge decay is secondary because no edge has been demonstrated in the first place.

---

## 12. Is There an Unbiased Edge?

### No Demonstrated Edge

- No asset class has p < 0.05 for positive mean return
- Live Sharpe is -2.34 (strongly negative)
- Profit Factor 0.46 = lose $1.00 for every $0.46 gained
- Win rate 11.1% is closer to random than breakeven
- ML accuracy 32.6% is worse than coin flip
- 680% max drawdown = total capital destruction

### Infrastructure Has Potential

- EQUITY: p=0.115 (closest to significance)
- ML architecture: XGB+LGB+RF ensemble is state-of-the-art
- Boruta feature selection correctly implemented
- Purged K-Fold CV with embargo prevents leakage
- CPCV/PBO/DSR code EXISTS -- needs wiring only
- 14 feature families, 150+ variables = rich feature space

**Verdict: The house is well-built, but empty.** The codebase demonstrates genuine quantitative finance expertise. The problem is that the sophisticated ML pipeline produces predictions worse than random. These are diagnosable and fixable problems.

---

## 13. Readiness for Real Capital

| Asset Class | Trades | Win% | Sharpe | Max DD | Verdict | Rationale |
|-------------|--------|------|--------|--------|---------|-----------|
| CRYPTO | 51,049 | 11.3% | -2.89 | >100% | NOT READY | 92% of volume; catastrophic Sharpe |
| MEMECOIN | 1,869 | 15.7% | -2.79 | >100% | NOT READY | Extreme volatility; no edge |
| EQUITY | 814 | 1.8% | +0.67 | ~35% | MARGINAL | Closest to edge (p=0.115) but underpowered |
| FOREX | 605 | 9.9% | -0.51 | >60% | NOT READY | Negative Sharpe; p=0.787 |
| FUTURES | 172 | 17.4% | -3.73 | >100% | NOT READY | Worst Sharpe; tiny sample |
| PENNY_STOCK | 148 | 6.8% | -3.38 | >100% | NOT READY | Worst Profit Factor (0.19) |

**Unanimous Verdict: Not Ready.** No asset class is ready for real capital deployment.

---

## 14. Critical Gaps & Red Flags

| # | Gap / Red Flag | Severity | Impact | Recommended Action |
|---|---------------|----------|--------|-------------------|
| 1 | 69% of trades have zero PnL recorded | CRITICAL | Performance data unreliable | Fix data pipeline immediately |
| 2 | PBO tool exists but not wired to production | CRITICAL | ~95% false positive rate | Wire PBO < 0.05 gate into pipeline |
| 3 | Dashboard claims vs reality gap is massive | CRITICAL | Users misled about performance | Update dashboard to reflect reality |
| 4 | ML calibration catastrophically inverted | CRITICAL | 96% conf -> 0.9% actual | Diagnose calibration failure; retrain |
| 5 | 342 training samples for 40 features | CRITICAL | 1:8.5 ratio = underfitting | Need 3,400+ samples or fewer features |
| 6 | 4 competing subsystems, no clear ownership | HIGH | Architectural confusion | Consolidate to single pipeline |
| 7 | 3,000+ strategies = multiple testing bias | HIGH | False Strategy Theorem applies | Implement Bonferroni correction |
| 8 | Core model files are empty placeholders | HIGH | Running placeholder code | Audit all model files; add CI checks |
| 9 | Survivorship bias: static 42-ticker universe | HIGH | Inflates backtest performance | Expand to full historical universe |
| 10 | 680% max drawdown, no circuit breakers | HIGH | Risk management ineffective | Implement 15% drawdown halt |

---

## 15. Remediation Roadmap

### Immediate (Week 1-2)

1. **Fix the PnL Data Pipeline** -- Audit execution-to-database flow. Add data quality checks for null PnL.
2. **Update Dashboard to Reflect Reality** -- Replace claims with database-sourced metrics.
3. **Wire PBO Into Production** -- Add hard gate: PBO > 0.05 = automatic rejection.
4. **Halt Penny Stock Trading** -- Remove PENNY_STOCK from production immediately.

### Short-Term (Month 1-2)

5. **Fix ML Calibration** -- Diagnose label leakage, verify temporal alignment, retrain isotonic regression.
6. **Consolidate Subsystems** -- Deprecate incubator (3,000 strategies). Migrate to alpha_engine.
7. **Increase Training Data** -- Minimum 10:1 sample-to-feature ratio (3,400+ samples).
8. **Implement Hard Drawdown Halts** -- 15% portfolio-level halt, 5% strategy-level halt.

### Medium-Term (Month 3-6)

9. **Full Validation Pipeline Deployment** -- Implement 10-step validation (Section 16).
10. **Expand Ticker Universe** -- Include delisted tickers; remove survivorship bias.
11. **Implement CPCV in Production** -- Deploy as default backtest methodology.
12. **Establish Performance Monitoring** -- Daily rolling Sharpe, weekly PSR, monthly correlation matrix.

---

## 16. Recommended Validation Pipeline

A 10-step process that any strategy must pass before receiving live capital:

### Step 1: Data Quality Audit
Verify no missing data, no look-ahead bias, correct price adjustments, survivorship-bias-free universe. Reject if > 1% of data points are interpolated or missing.

### Step 2: CPCV Backtest
Run Combinatorial Purged Cross-Validation (k=4 groups, purge=2x embargo). Pass if median Sharpe > 0.5 and Profit Factor > 1.3.

### Step 3: PBO Analysis
Run Probability of Backtest Overfitting. Strategy passes ONLY if PBO < 0.05. This is a hard gate -- no exceptions.

### Step 4: DSR Calculation
Calculate Deflated Sharpe Ratio. DSR > 0.95 required.

### Step 5: Sensitivity Analysis
Perturb each parameter by +/-10%, +/-20%. Pass if Sharpe remains > 0.3 across all perturbations.

### Step 6: Paper Trading (6 Months)
Run on paper account for minimum 6 months. Minimum 100 trades required.

### Step 7: Walk-Forward Efficiency (WFE)
WFE = (Live Sharpe / Backtest Sharpe) x 100. Pass if WFE > 60%.

### Step 8: Independent Backtest Confirmation
Second analyst independently backtests. Results must agree within 20% on Sharpe and Win Rate.

### Step 9: Capital Allocation
Start with 1% of target allocation. Scale by 2x monthly if rolling 30-day Sharpe > 0.5 and drawdown < 10%. If drawdown exceeds 15%, halt and return to Step 2.

### Step 10: Ongoing Monitoring
Daily P&L reconciliation, weekly rolling Sharpe, monthly PSR, quarterly full re-validation. Auto-demote after 2 consecutive failing review periods.

---

## 17. Data Sources & Supplementary Resources

### Recommended Datasets

- **CRSP Survivorship-Bias-Free US Stocks** -- Gold standard for US equity backtesting
- **CoinGecko API** -- Free tier, historical prices for 10,000+ coins
- **OANDA / TrueFX** -- Free historical tick data for forex
- **FRED** -- 800,000+ macroeconomic time series, free API

### Essential Reading

- *Advances in Financial Machine Learning* -- Marcos Lopez de Prado
- *The Evaluation and Optimization of Trading Strategies* -- Robert Pardo
- *Machine Learning for Asset Managers* -- Marcos Lopez de Prado
- *Quantitative Risk Management* -- McNeil, Frey, Embrechts

### Open-Source Tools

- **mlfinlab** (Lopez de Prado): PBO, CPCV, DSR implementations
- **Backtrader**: Event-driven backtesting engine
- **QuantStats**: Tear sheet generation
- **Optuna**: Bayesian hyperparameter optimization

---

## 18. Appendix

### Key Formulas

**Sharpe Ratio:**
```
SR = (R_bar - R_f) / sigma_p
```

**Profit Factor:**
```
PF = sum(Gross Profits) / sum(|Gross Losses|)
```

**Brier Score:**
```
BS = (1/N) * sum((f_i - o_i)^2)
```

**Probability of Backtest Overfitting:**
```
PBO = phi({SR_bar_n < SR_bar_in_sample} intersect {n_0 <= n*})
```

**Walk-Forward Efficiency:**
```
WFE = (Sharpe_live / Sharpe_backtest) * 100%
```

### Glossary

| Term | Definition |
|------|-----------|
| **PBO** | Probability of Backtest Overfitting. Must be < 0.05. |
| **DSR** | Deflated Sharpe Ratio. Adjusted for multiple trials. Must be > 0.95. |
| **WFE** | Walk-Forward Efficiency. Ratio of live to backtest Sharpe. Must be > 60%. |
| **CPCV** | Combinatorial Purged Cross-Validation. Leakage-proof backtesting method. |
| **Profit Factor** | Gross profits / gross losses. > 1.3 is viable. |
| **Brier Score** | MSE of probability forecasts. 0 = perfect; lower is better. |
| **False Strategy Theorem** | With N strategies tested, P(false positive SR > S*) approaches 1. |

### Audit Methodology Notes

**Database Analysis:** All statistics computed from 55,510 resolved trades. A "resolved trade" has a recorded outcome (win/loss) and settlement timestamp. Trades with null outcomes are excluded from win rate calculations but counted in totals.

**Statistical Tests:** One-sample t-tests test H0: mu = 0 against H1: mu != 0. Significance threshold alpha = 0.05. Bootstrap confidence intervals use BCa method with 10,000 resamples.

**Industry Benchmarks:** Thresholds sourced from Lopez de Prado (2018), CFA Institute Standards, BarclayHedge quantitative fund survey data (2024).

**Repository Analysis:** Static analysis of 19,685 files using custom Python AST parsers and cloc. Git history analyzed for commit frequency and contributor patterns.

---

## Final Assessment

This system, as currently deployed, **destroys capital**. The dashboard claims are not supported by the database. The ML model is worse than random. The backtest is 3.8x inflated.

**But the codebase has genuine quantitative expertise** -- XGB+LGB+RF ensemble, Boruta, Purged K-Fold, regime detection, and PBO/CPCV/DSR code that exists but is not wired. The path forward is clear: fix the data pipeline, wire the anti-overfitting tools, and run the 10-step validation pipeline.

**This is a wiring problem, not a knowledge problem. It is fixable.**

---

*Quantitative Edge Audit Report | findtorontoevents.ca | Version 1.0 | July 2025*

*This report is for informational purposes only and does not constitute investment advice. Past performance is not indicative of future results.*
