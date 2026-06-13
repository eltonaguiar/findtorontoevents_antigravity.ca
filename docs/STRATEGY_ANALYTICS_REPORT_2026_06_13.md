# Strategy Analytics — Statistical Validation Report

**Date:** 2026-06-13 01:35 UTC  
**Author:** Kilo (automated via strategy_analytics.py)  
**Data Source:** 9,890 resolved trades from `at_pick_outcomes`

---

## Executive Summary

Analyzed 32 strategies with ≥30 resolved trades using:
- Binomial significance test (H0: WR = 50%)
- Annualized Sharpe ratio
- Maximum drawdown
- 70/30 purged OOS backtest

### Key Findings

| Metric | Count | % |
|--------|-------|---|
| **Significant Edge** | 6 | 18.8% |
| **Significant Drain** | 15 | 46.9% |
| **No Signal** | 11 | 34.4% |
| **Overfit Risk** | 10 | 31.3% |

**Critical Insight:** 46.9% of strategies show statistically significant negative edge (p < 0.05). Only 18.8% show significant positive edge. The system is net-negative.

---

## SIGNIFICANT EDGE Strategies (6)

These strategies show statistically significant positive edge (p < 0.05, WR > 50%).

### 1. CRYPTO: `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack`
| Metric | Value |
|--------|-------|
| n | 35 |
| WR | 91.4% |
| Sharpe | 15.902 |
| PF | 8.867 |
| MDD | 4.8% |
| **OOS Decay** | train=95.83% → test=81.82% (14.01pp decay) |

**Assessment:** Exceptional performance but high overfit risk. 91.4% WR on 35 trades is suspicious — likely regime-specific. OOS decay of 14pp confirms degradation. **Recommendation: Paper-trade for 60 days before live.**

### 2. CRYPTO: `prediction_market_consensus`
| Metric | Value |
|--------|-------|
| n | 103 |
| WR | 84.5% |
| Sharpe | 4.984 |
| PF | 13.198 |
| MDD | 7.5% |
| **OOS Decay** | train=88.89% → test=46.67% (42.22pp decay) |

**Assessment:** High WR but **extreme overfit risk**. OOS decay of 42pp is catastrophic — strategy performs well in-sample but fails out-of-sample. **Recommendation: Retire or heavily restrict.**

### 3. CRYPTO: `hs_lb_None`
| Metric | Value |
|--------|-------|
| n | 202 |
| WR | 65.3% |
| Sharpe | 9.605 |
| PF | 3.296 |
| MDD | 13.0% |

**Assessment:** Solid edge with decent sample size. 202 trades with 65.3% WR is meaningful. **Recommendation: Increase position size, monitor for decay.**

### 4. CRYPTO: `battleground_ml_relaxed_mut`
| Metric | Value |
|--------|-------|
| n | 31 |
| WR | 71.0% |
| Sharpe | 11.850 |
| PF | 4.346 |
| MDD | 14.7% |

**Assessment:** Strong edge but small sample (31 trades). Needs more data. **Recommendation: Continue paper trading, validate with 100+ trades.**

### 5. CRYPTO: `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`
| Metric | Value |
|--------|-------|
| n | 31 |
| WR | 83.9% |
| Sharpe | 8.860 |
| PF | 7.947 |
| MDD | 19.3% |
| **OOS Decay** | train=85.71% → test=80.0% (5.71pp decay) |

**Assessment:** Strong but small sample. OOS decay is moderate (5.71pp). **Recommendation: Paper-trade for 60 days.**

### 6. CRYPTO: `signal_validation`
| Metric | Value |
|--------|-------|
| n | 37 |
| WR | 70.3% |
| Sharpe | -1.034 |
| PF | 0.756 |
| MDD | 213.5% |

**Assessment:** **PARADOX** — WR is 70.3% but Sharpe is negative and PF < 1. This means winners are small and losers are large. **Recommendation: Retire — positive skew is negative.**

---

## SIGNIFICANT DRAIN Strategies (15)

These strategies show statistically significant negative edge (p < 0.05). All are already blocked or should be.

| # | Asset Class | Strategy | n | WR | Sharpe | PF | Status |
|---|-------------|----------|---|-----|--------|-----|--------|
| 1 | COMMODITY | futures_momentum | 681 | 37.3% | -2.80 | 0.25 | ✅ Blocked |
| 2 | COMMODITY | cta_cross_asset_tsmom | 96 | 19.8% | -8.88 | 0.28 | ✅ Blocked |
| 3 | CRYPTO | luxalgo_confluence | 2058 | 46.0% | 1.24 | 1.20 | ⚠️ NOT blocked |
| 4 | CRYPTO | unknown | 275 | 44.4% | 2.23 | 1.34 | ⚠️ NOT blocked |
| 5 | CRYPTO | luxalgo_filters | 115 | 23.5% | -4.77 | 0.50 | ✅ Blocked |
| 6 | CRYPTO | ensemble | 103 | 40.8% | -4.44 | 0.24 | ✅ Blocked |
| 7 | CRYPTO | enhanced_ml_A_xgboost | 62 | 29.0% | -2.33 | 0.70 | ✅ Blocked |
| 8 | CRYPTO | ml_enhanced_DYDXUSDT | 31 | 32.3% | -8.93 | 0.13 | ⚠️ NOT blocked |
| 9 | EQUITY | MomentumEMA | 54 | 18.5% | -8.70 | 0.34 | ✅ Blocked |
| 10 | FOREX | forex_rsi2_mean_reversion | 732 | 42.4% | -0.75 | 0.37 | ✅ Blocked |
| 11 | FOREX | ig_contrarian_sentiment | 485 | 36.9% | 0.63 | 1.94 | ⚠️ NOT blocked |
| 12 | FOREX | myfxbook_retail_contrarian | 466 | 39.9% | 0.22 | 1.27 | ⚠️ NOT blocked |
| 13 | FOREX | forex_carry_momentum | 154 | 7.8% | 1.64 | 9.88 | ✅ Blocked |
| 14 | FOREX | fx_smart_carry_trade_momentum | 54 | 37.0% | -2.22 | 0.74 | ✅ Blocked |
| 15 | UNKNOWN | ml_bg_system_f | 33 | 0.0% | -117.77 | 0.00 | ⚠️ NOT blocked |

### Critical Unblocked Drains

**3 strategies with significant drain are NOT in the blocklist:**

1. **`luxalgo_confluence`** (CRYPTO, n=2058, WR=46.0%)
   - 2,058 trades with negative Sharpe
   - High volume drain — should be blocked

2. **`unknown`** (CRYPTO, n=275, WR=44.4%)
   - 275 trades with unidentified strategy
   - Likely a bug in strategy attribution

3. **`ig_contrarian_sentiment`** (FOREX, n=485, WR=36.9%)
   - Significant drain but PF=1.94 (positive skew)
   - **Paradox:** Negative WR but positive profit factor
   - Kill switch already blocked it (WR < 35%)

4. **`myfxbook_retail_contrarian`** (FOREX, n=466, WR=39.9%)
   - Similar pattern to ig_contrarian_sentiment
   - Already blocked by kill switch

5. **`ml_enhanced_DYDXUSDT`** (CRYPTO, n=31, WR=32.3%)
   - Very negative Sharpe (-8.93)
   - Small sample but clearly toxic

6. **`ml_bg_system_f`** (UNKNOWN, n=33, WR=0.0%)
   - **0% win rate** — deterministic loser
   - Must be blocked immediately

---

## OVERFIT RISK Strategies (10)

These strategies show OOS degradation >10pp WR or Sharpe decay >1.0.

### Critical Overfit Cases

| Strategy | Train WR | Test WR | Decay | Assessment |
|----------|----------|---------|-------|------------|
| `prediction_market_consensus` | 88.9% | 46.7% | **42.2pp** | Catastrophic overfit |
| (unnamed CRYPTO) | 51.5% | 21.1% | **30.5pp** | Catastrophic overfit |
| `non_crypto_consensus` | 53.2% | 38.9% | 14.3pp | Significant overfit |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 95.8% | 81.8% | 14.0pp | Moderate overfit |
| `ensemble` | 43.1% | 35.5% | 7.6pp | Moderate overfit |

**Key Insight:** The `prediction_market_consensus` strategy has 84.5% WR overall but only 46.7% OOS. This is classic data snooping — the strategy memorized training data.

---

## Actionable Recommendations

### Immediate (This Week)

1. **Kill 3 unblocked significant drains:**
   - `luxalgo_confluence` (n=2058, WR=46%, Sharpe=1.24 but PF=1.20 — marginal positive)
   - `ml_enhanced_DYDXUSDT` (n=31, WR=32.3%, Sharpe=-8.93)
   - `ml_bg_system_f` (n=33, WR=0.0% — deterministic loser)

2. **Restrict `prediction_market_consensus`:**
   - 42pp OOS decay = data snooping
   - Cap position size at 0.5% until validated

3. **Paper-trade top 3 edge strategies:**
   - `hs_lb_None` (n=202, WR=65.3%)
   - `battleground_ml_relaxed_mut` (n=31, WR=71.0%)
   - `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=31, WR=83.9%)

### Week 2-3

4. **Run 90-day forward validation** on edge strategies
5. **Build significance test into CI** — auto-flag new strategies with p > 0.05
6. **Consolidate strategy count** — 514 buckets → 30-50 genuine ideas

### Month 2+

7. **Deploy FOREX-1** (carry + volatility gate) with pair filter
8. **Expand EQUITY-1** universe with S&P 500 fundamentals
9. **Build replay harness** for continuous validation

---

## Appendix: Full Results

See `audit_dashboard/data/strategy_analytics.json` for complete per-strategy breakdown.

---

**Last updated:** 2026-06-13 01:35 UTC
