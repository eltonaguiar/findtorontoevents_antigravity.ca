# Strong Signals Blueprint — Institutional Audit Report
**Date:** 2026-03-24
**Source:** External quantitative review + internal peer analysis

---

## System Overview
- **Asset Classes:** Crypto, Forex, Equities, Commodities
- **Strategy Type:** Quantitative, regime-aligned with multi-factor filtering
- **Goal:** >60% WR, Profit Factor > 1.5, controlled drawdowns

---

## Performance Analysis (Current vs Target)

| Metric | Current (All Picks) | Strong Signal Target | Institutional Threshold |
|--------|--------------------|-----------------------|------------------------|
| Win Rate | 41.9% | 65-70% | >60% |
| Profit Factor | 1.19 | 1.8-2.2 | >1.5 |
| Avg Win | +4.04% | +5.2% | — |
| Avg Loss | -2.46% | -1.8% | — |
| Expectancy | +0.26% | +1.8% | >0 |
| Max Drawdown | Unknown | <15% | <20% |
| Sharpe Ratio | 2.95 (inflated) | 1.5-2.0 | >1.0 |
| Trades/week | ~50 | 5-10 | — |

---

## Data-Backed Findings (Ranked by Impact)

### 1. R:R Sweet Spot — 73.7% WR
- R:R 2.0-2.5 = 73.7% WR vs 39% for R:R < 1.5
- **Action:** Hard-block R:R < 1.5, boost 2.0-2.5

### 2. Regime Alignment — 64% vs 41.9% WR
- LONG in bull / SHORT in bear = 64% median WR
- **Action:** Increase regime_match weight to 0.50

### 3. Leverage Safety — 67% WR, +1.21% P/L
- Stop distance 1.5-3% + ML confidence >= 0.80
- **Action:** Implement as scoring component

### 4. Strategy Track Record — PF 0.76 to 1.90
- Doubling track record weight improved PF from 0.76 to 1.90 in top quintile
- **Action:** Double weight to 20 points

### 5. Confidence Inversion — 0.60-0.70 BEST
- 0.60-0.70 = 61% WR (best)
- 0.80+ = 49% WR (overconfidence)
- **Action:** Fix scoring — currently penalizes best zone

---

## Institutional Audit: Strengths

1. **Regime alignment as signal enhancer** — aligns with Markov Regime Switching models
2. **Multi-factor filtering** — reduces false positives, aligns with modern factor investing
3. **Empirical thresholds** — data-driven, not arbitrary
4. **Focus on expectancy & asymmetry** — positive skewness, tail risk management
5. **Risk-reward filtering** — aligns with robust risk management (Kelly, fractional Kelly)

---

## Institutional Audit: Critical Gaps

### Statistical Rigor
- **Overfitting risk:** Thresholds tuned on past data need cross-validation and out-of-sample testing
- **Data snooping:** Bootstrap methods or walk-forward analysis needed
- **Distributional assumptions:** Returns stationarity may not hold (especially crypto)
- **Need:** Formal p-values, confidence intervals on all threshold choices

### Risk Management
- **No formal Kelly sizing** — blueprint describes it but it's not implemented
- **No portfolio-level drawdown controls** — no recovery or tranche-based capital deployment
- **Correlation & systemic risk** — crypto/equity crash correlation not accounted for
- **Leverage amplification** — tight stops + leverage = tail risk in flash crashes
- **Need:** Volatility targeting, liquidity-adjusted sizing, tail correlation metrics

### Regime Detection
- **Lag risk:** Current regime detection uses lagging indicators
- **Transition phases:** Misclassification during regime shifts
- **Need:** Bayesian or Hidden Markov Model (HMM) frameworks for responsiveness

### Alpha Sustainability
- **Alpha decay:** Continuous re-optimization needed
- **Need:** Dynamic threshold adaptation via ML or Bayesian updates

---

## Priority Implementation Plan

### Phase 1: Hard Gates (This Week) — Highest Impact
| Gate | Expected Impact | Effort |
|------|----------------|--------|
| R:R >= 1.5 hard block | 73.7% WR in sweet spot | Low |
| Regime alignment hard gate | 64% vs 42% WR | Low |
| Strategy validation (10+ trades, 45%+ WR) | Eliminates unproven strategies | Low |
| Confidence 0.55-0.80 band | Blocks noise and overconfidence | Low |

### Phase 2: Scoring Fixes (Next Week)
| Fix | Expected Impact | Effort |
|-----|----------------|--------|
| Confidence scoring inversion (0.60-0.70 = best) | +10-15% WR improvement | Low |
| Track record weight doubled to 20 pts | PF 0.76 → 1.90 | Low |
| Regime match weight 0.40 → 0.50 | Better regime filtering | Low |
| Kelly position sizing | Optimal capital allocation | Medium |

### Phase 3: Advanced (Month 1)
| Enhancement | Expected Impact | Effort |
|-------------|----------------|--------|
| HMM/Bayesian regime detection | Faster regime transitions | High |
| Portfolio correlation monitoring | Systemic risk reduction | Medium |
| Walk-forward validation framework | Anti-overfitting | High |
| Stress testing (flash crash, gap) | Tail risk identification | Medium |
| Formal audit trails | Institutional compliance | Medium |

---

## Forex-Specific Adjustments

The blueprint's thresholds are crypto-calibrated. Forex needs:
- **Stop distance:** 0.5-1.5% (not 1.5-3%) — forex ATR is 0.3-0.8% daily
- **TP cap:** 0.8% max (not 3-5% crypto scale)
- **R:R calculation:** Use pip-based, not percentage-based
- **Regime:** DXY trend + interest rate differentials > crypto Fear & Greed
- **Session timing:** London/NY overlap = best liquidity window

---

## Expected Outcome

572 picks → ~40 strong signals (7% pass rate)
- **Win Rate:** 65-70%
- **Profit Factor:** 1.8-2.2
- **Expectancy:** +1.8% per trade
- **Trades/week:** 5-10 (quality over quantity)

---

*Generated from Strong Signals Blueprint analysis + external institutional quantitative review*
