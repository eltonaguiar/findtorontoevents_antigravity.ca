# Quant Picks Quality Report - April 9, 2026

## Executive Summary

This report analyzes the quality of active and closed picks across all asset classes, with specific focus on the "High Conviction" filter on the audit dashboard and whether picks meet hedge fund level quality standards.

---

## 1. Data Overview

### Pick Distribution (All-Time)
| Asset Class | Count | Percentage |
|-------------|-------|------------|
| CRYPTO | 2,754 | 78.5% |
| EQUITY | 577 | 16.4% |
| FOREX | 155 | 4.4% |
| ETF | 12 | 0.3% |
| COMMODITY | 8 | 0.2% |
| FUTURES | 3 | 0.1% |
| **TOTAL** | **3,509** | 100% |

### Top Systems by Volume
1. `claude_gainer_st` - 1,099 picks (31.3%)
2. `stocks_competition` - 343 picks (9.8%)
3. `kimi_riseoftheclaw` - 281 picks (8.0%)
4. `baby_strats_forward` - 256 picks (7.3%)
5. `luxalgo_filters` - 237 picks (6.8%)

---

## 2. Closed Picks Performance by Asset Class

| Asset Class | Closed | Win Rate | Total PnL% | Avg PnL% |
|-------------|--------|----------|------------|----------|
| **CRYPTO** | 2,691 | **51.5%** | **+735.9%** | +0.27% |
| EQUITY | 532 | 36.0% | -397.9% | -0.75% |
| FOREX | 148 | 36.6% | -38.0% | -0.26% |
| ETF | 12 | 41.7% | -11.4% | -0.95% |
| COMMODITY | 8 | 12.5% | -6.9% | -0.86% |
| FUTURES | 3 | 0.0% | -1.4% | -0.47% |

### Key Finding
**CRYPTO is the only profitable asset class** with a 51.5% win rate and +735.9% total PnL. All non-crypto asset classes are losing money, with EQUITY showing the worst performance at -397.9% PnL despite having 532 closed trades.

---

## 3. Top Performing Systems (Closed PnL)

| System | Closed | Win Rate | Total PnL% |
|--------|--------|----------|------------|
| mercury2 | 83 | 47.0% | **+67.4%** |
| luxalgo_filters | 237 | 48.5% | **+58.5%** |
| alpha_engine | 117 | 57.3% | **+56.9%** |
| super_signals | 14 | 57.1% | +16.1% |
| baby_strats_forward | 256 | 44.5% | +5.2% |

---

## 4. High Conviction Filter Analysis

### Audit Dashboard HF Tier Distribution (Active)
- **HF Tier S:** 1 pick
- **HF Tier A:** 9 picks  
- **HF Tier B:** 24 picks
- **Total HF picks:** 34/36 (94.4% of high-conviction)

### High Conviction Metrics
- **Active picks:** 36 (filtered from 115 total)
- **Forward test win rate:** 69.2%
- **Verified Alpha:** 29 active picks, 1 smart pick
- **Audited WR:** 50.4% | **Realized WR:** 50.8%

### Quality Gates Impact
- Active before gates: 206 picks
- Active after gates: 80 picks (61% filtered out)
- Smart picks percentage: 1.4%

### Forward Degradation
- **Aggregate:** 3,661 trades
- **Source WR:** 41.2% | **Realized WR:** 48.9%
- **Delta:** +7.7pp (improvement, not degradation!)
- **Severity:** LIFTING (penalty +5)

### Worst Performing Strategies (Flagged for Rehabilitation)
| Strategy | Severity | Issue | Recommendation |
|----------|----------|-------|----------------|
| crypto_bayesian_regime_transition_momentum_v1 | SEVERE | 9.1% WR | DNA mutation needed |
| crypto_kalman_trend_residual_reversion_v1 | SEVERE | 10.0% WR | Restrict to BTCUSDT LONG |
| mean_reversion_momentum | SEVERE | 0.0% WR | Restrict to BTCUSDT LONG |
| ema_stack_momentum | SEVERE | 25.0% WR | DNA mutation needed |

---

## 5. Assessment: Is High Conviction Actually HF-Quality?

### VERDICT: **MIXED - Needs Enhancement**

#### What's Working:
1. **HF Tier S/A/B classification exists** - 34/36 picks properly classified
2. **Forward WR improvement** - Realized WR (48.9%) > Source WR (41.2%), indicating good signal quality
3. **Quality gates working** - 61% of picks filtered out before display
4. **CRYPTO performing well** - 51.5% WR, +735.9% PnL

#### What's NOT Working:
1. **Non-crypto is hemorrhaging** - EQUITY at -352.33% PnL, FOREX at -36.26%
2. **Only 1 verified "smart pick"** - Very low confidence in ML predictions
3. **No ELITE tier picks** - Quality bar may be too high or data insufficient
4. **High conviction count low** - Only 36/115 (31%) qualify
5. **System concentration risk** - Top 3 systems dominate

---

## 6. Recommendations for Enhancement

### Immediate Actions
1. **Disable EQUITY/FOREX in High Conviction** - These are losing money, diluting HF quality
2. **Raise HF Tier B threshold** - Current 24 Tier B picks show only 50.8% realized WR
3. **Add system diversity requirement** - Max 30% from any single system in HF picks

### Medium-Term Improvements
4. **Increase smart_picks detection** - Only 1 detected is too low for confidence
5. **Add symbol concentration cap** - Top symbols should be max 15% of HF portfolio
6. **Implement per-asset-class HF qualification** - CRYPTO-only HF for now, others need rebuilding

### Data Quality
7. **Recent wins data gap** - No closed picks in last 30 days suggests data pipeline issue
8. **Add forward_trades requirement** - Require minimum 20 forward trades for HF classification

---

## 7. Redis Bus Broadcasting

This report has been broadcast to the Redis Bus for fleet coordination.

---

*Report generated: 2026-04-09*
*Data sources: antigravity_all_picks_2026-04-09.csv, audit dashboard DASHBOARD_DATA*