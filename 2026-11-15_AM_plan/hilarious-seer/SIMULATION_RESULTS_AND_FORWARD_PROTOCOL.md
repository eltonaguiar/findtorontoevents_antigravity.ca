# Simulation Results & Forward Test Protocol
**Date:** 2026-11-15 AM  
**Worktree:** hilarious-seer  
**Status:** Simulations complete. Brutal honesty: only passive beta works.

---

## Executive Summary

We ran three backtest simulations to "prove" the path forward:

| Simulation | Asset Class | Ann Return | Sharpe | Max DD | vs Benchmark | Verdict |
|------------|-------------|------------|--------|--------|--------------|---------|
| **Passive Beta (VTI/BND 60/40)** | ETF/MF | **8.8%** | **0.40** | **-21.8%** | Underperforms SPY by 5.5% | **DEPLOYABLE** (beta only) |
| **Connors RSI-2 (SPY)** | EQUITY | **-12.6%** | **-0.03** | **-46.0%** | Underperforms SPY by 358% | **ELIMINATED** |
| **Dual Momentum (Faber)** | MULTI-ASSET | **9.1%** | **0.40** | **-23.9%** | Underperforms SPY by 5.6% | **FAIL** |

**The only profitable path is passive beta.** Every active strategy tested failed to beat buy-and-hold after costs. This is not a bug in the simulation — it is the mathematical reality that the audit has been telling us for months.

---

## Simulation 1: Passive Beta (VTI/BND 60/40)

### Strategy
- 60% VTI (Vanguard Total Stock Market ETF)
- 40% BND (Vanguard Total Bond Market ETF)
- Rebalanced annually
- Cost: 0.10% per rebalance

### Results (2015-01-01 to 2026-11-14, ~12 years)

| Metric | Portfolio (60/40) | Benchmark (SPY) |
|--------|-------------------|-----------------|
| Total Return | +164.9% | +353.9% |
| Annualized Return | 8.8% | 14.3% |
| Annualized Volatility | 11.0% | 17.5% |
| Sharpe Ratio | 0.40 | 0.56 |
| Max Drawdown | -21.8% | -33.7% |
| Calmar Ratio | 0.41 | 0.42 |
| Daily Win Rate | 55.0% | 54.6% |

### Interpretation
The 60/40 portfolio **underperformed SPY** by 5.5% annually. This is EXPECTED — bonds drag during a strong equity bull market. However, it achieved this with **35% lower volatility** and **35% smaller max drawdown**.

**Why this is deployable:** It captures the equity risk premium (via VTI) and provides ballast (via BND). It does not claim alpha. It is the honest baseline.

### Forward Test Tracker Verdict: **FULL_LIVE**
- This is not a "strategy" to test — it is an allocation to deploy immediately.
- No gates apply because it is beta, not alpha.

---

## Simulation 2: Connors RSI-2 Mean Reversion (SPY)

### Strategy
- LONG when RSI(2) < 10 AND close > SMA(200)
- SHORT when RSI(2) > 90 AND close < SMA(200)
- TP: 2× ATR(14) | SL: 1× ATR(14)
- Max hold: 10 bars
- Cost: 0.10% round-trip

### Results (2015-01-01 to 2026-11-14)

| Metric | RSI-2 Strategy | Benchmark (SPY) |
|--------|----------------|-----------------|
| Trades | 298 | — |
| Total Return | **-12.6%** | **+345.7%** |
| Win Rate | 47.6% | — |
| Profit Factor | 0.99 | — |
| Expectancy | -0.015% | — |
| Sharpe Ratio | -0.03 | — |
| Max Drawdown | -46.0% | -33.7% |

### Interpretation
This is a **catastrophic failure**. The RSI-2 system lost money while SPY gained 346%. Even though the win rate was nearly 48%, the **expectancy was negative** — small wins were erased by large losses. The max drawdown was WORSE than buy-and-hold.

**Why this failed:**
1. **Mean reversion does not work in trending markets.** 2015–2026 was predominantly a bull market. Buying dips (RSI<10) often meant catching a falling knife or exiting too early.
2. **Short signals were toxic.** SHORT when RSI>90 in a bull market is fighting the primary trend.
3. **Costs matter.** 298 trades × 0.10% = 29.8% in transaction costs alone.
4. **ATR-based stops were too tight.** In volatile regimes, 1× ATR stops were hit frequently before mean reversion could occur.

### Forward Test Tracker Verdict: **ELIMINATED**
- Reason: MaxDD = -46.0% < -35% elimination trigger
- Action: STOP immediately. Do not forward-test.

---

## Simulation 3: Dual Momentum Tactical Allocation

### Strategy (Gary Antonacci-style)
- Universe: SPY, VTI, VXUS, BND, SHY
- Filter: Price > 10-month SMA (absolute momentum)
- Select: Highest 12-month return among passing assets (relative momentum)
- Fallback: SHY (T-bills) if nothing passes
- Rebalance: Monthly
- Cost: 0.10% per rebalance

### Results (2010-01-01 to 2026-11-14)

| Metric | Dual Momentum | Benchmark (SPY) |
|--------|---------------|-----------------|
| Total Return | +204.8% | +620.8% |
| Annualized Return | 9.1% | 14.7% |
| Annualized Volatility | 12.2% | 15.8% |
| Sharpe Ratio | 0.40 | 0.73 |
| Max Drawdown | -23.9% | -23.9% |
| Calmar Ratio | 0.38 | 0.62 |

### Interpretation
Dual momentum also **failed to beat SPY**. It captured some downside protection (equal max drawdown) but at the cost of significant underperformance. The monthly rebalance with 0.10% cost and the delay in switching out of falling assets hurt returns.

**Why this failed in our test:**
1. **The 2010–2026 period was dominated by US equity outperformance.** International (VXUS) and bonds (BND) rarely won the relative momentum race.
2. **The 10-month SMA filter kept the strategy in cash (SHY) during brief corrections** — missing the sharp V-shaped recoveries that characterized this era.
3. **Monthly rebalancing is too slow** for rapid regime shifts.

### Forward Test Tracker Verdict: **FAIL — does not improve on SPY**
- Not eliminated (not toxic), but not deployable as alpha.
- Could be reconsidered in a different regime (e.g., 2000–2010).

---

## What These Simulations Prove

### 1. Passive Beta Is the Only Honest Deployment

| Strategy | Ann Return | Sharpe | Deployable? |
|----------|------------|--------|-------------|
| SPY Buy-and-Hold | 14.3% | 0.56 | Yes (beta) |
| VTI/BND 60/40 | 8.8% | 0.40 | Yes (beta) |
| Connors RSI-2 | -1.1%* | -0.03 | **NO** |
| Dual Momentum | 9.1% | 0.40 | **NO** |

*Negative total return over 12 years.

**Key insight:** The equity risk premium is REAL and has delivered 8–14% annually over the past 12 years. No active strategy we tested captured it better than simply holding SPY.

### 2. Mean Reversion Fails in Trending Markets

The RSI-2 system is designed for sideways, mean-reverting markets. The 2015–2026 period was predominantly trending. This is not a failure of the strategy logic — it is a **regime mismatch**. The strategy might work in a 2000–2010 or 2027–2035 sideways market, but we have no way to predict that.

### 3. Tactical Allocation Fails When One Asset Dominates

Dual momentum requires a diversified universe where leadership rotates. When US equities dominate for 12 years, the strategy is effectively a lagging SPY tracker with higher costs.

### 4. Costs Are the Silent Killer

| Strategy | Trades/Rebals | Cost Drag | Impact |
|----------|---------------|-----------|--------|
| RSI-2 | 298 trades | 29.8% | Turned breakeven into -12.6% |
| Dual Momentum | ~60 rebals | 6.0% | Turned slight edge into underperformance |
| Passive Beta | 12 rebals | 1.2% | Minimal impact |

**Rule:** Any strategy with <1% expectancy per trade will be killed by 0.10% costs.

---

## Forward Test Tracker Protocol

### Purpose
Replace gut-feel decisions with pre-registered statistical rules. Every strategy starts at PAPER and only graduates if it passes all gates.

### Gates

| Gate | n Min | PF Min | WR Min | Max DD | Sharpe Min | Max Days |
|------|-------|--------|--------|--------|------------|----------|
| **Paper** | 10 | 0.80 | 40% | -25% | 0.0 | 30 |
| **Probation** | 30 | 1.00 | 48% | -20% | 0.3 | 90 |
| **Small Live** | 100 | 1.30 | 55% | -15% | 0.8 | 180 |
| **Full Live** | 300 | 1.50 | 55% | -15% | 1.0 | 365 |

### Fast Elimination Triggers (ANY ONE = KILL)

| Trigger | Threshold | Rationale |
|---------|-----------|-----------|
| PF too low | < 0.70 after n=10 | Strategy is losing money, not noise |
| WR too low | < 30% after n=10 | Worse than random |
| Max DD | < -35% at any point | Capital preservation breach |
| Consecutive losses | 7 in a row | Strategy broken or regime shifted |
| Stale | No trade in 14 days | Strategy is dead |

### Extended Hold Triggers (ALL must be true to hold beyond normal gate)

| Trigger | Threshold | Rationale |
|---------|-----------|-----------|
| Improving PF | Last 10 trades PF > 1.05 | Momentum in performance |
| Improving WR | Last 10 trades WR > 50% | Getting better, not worse |
| No blowout | No single loss > 5% | Risk is controlled |
| Regime alignment | Confirmed by external filter | Strategy fits current market |

### Decision Tree

```
Start → PAPER
  │
  ├─ Elimination trigger? → ELIMINATED (stop immediately)
  │
  ├─ Gate failures? → HOLD (continue at current level)
  │
  ├─ All gates pass? → GRADUATE to next level
  │
  └─ Full live + all gates pass? → FULL_LIVE (monitor daily)
```

### Application to Our Simulations

| Strategy | n | PF | WR | Sharpe | Max DD | Tracker Verdict |
|----------|---|----|----|--------|--------|-----------------|
| Passive Beta | N/A | N/A | N/A | 0.40 | -21.8% | **FULL_LIVE** (beta deployment) |
| RSI-2 (SPY) | 298 | 0.99 | 47.6% | -0.03 | -46.0% | **ELIMINATED** (MaxDD trigger) |
| Dual Momentum | N/A | N/A | N/A | 0.40 | -23.9% | **HOLD** (not toxic, not deployable) |

---

## Revised Path Forward (Based on Simulation Evidence)

### Immediate (This Week)
1. **Deploy passive beta sleeve:** VTI 60% / BND 40% (or FXAIX/FSKAX/FXNAX for mutual funds)
2. **ELIMINATE Connors RSI-2** from all production scanners. Do not unblock `stocks_rsi2_pullback`.
3. **Kill all mean-reversion strategies** on EQUITY until a bear-market regime is confirmed.
4. **Archive dual momentum** as "not viable in current regime."

### Short-Term (Next 30 Days)
5. **Test TREND-FOLLOWING, not mean-reversion.** In trending markets, momentum strategies outperform mean-reversion.
6. **Pre-register a 12-1 month momentum test on SPY.** If it beats buy-and-hold after costs, forward-test it.
7. **Build the momentum test harness** in `simulations/prove_equity_momentum.py`.

### Medium-Term (Next 90 Days)
8. **If momentum fails:** Accept that the system has no alpha on EQUITY. Deploy 100% passive.
9. **If momentum passes:** Forward-test with n≥100, PF≥1.3, WR≥55% gates.
10. **Continue CRYPTO fill-fix research** as the only remaining conditional track.

---

## Files Generated

| File | Description |
|------|-------------|
| `simulations/prove_passive_beta.py` | Backtest VTI/BND 60/40 vs SPY |
| `simulations/prove_equity_rsi2.py` | Backtest Connors RSI-2 on SPY |
| `simulations/prove_dual_momentum.py` | Backtest Faber-style dual momentum |
| `simulations/forward_test_tracker.py` | Decision protocol for strategy lifecycle |
| `simulations/results_passive_beta.json` | Raw results |
| `simulations/results_equity_rsi2.json` | Raw results |
| `simulations/results_dual_momentum.json` | Raw results |
| `simulations/forward_test_decisions.json` | Tracker decisions |

---

## The Hardest Truth

> **After 658 strategies, 9 asset classes, 2,198 commits, and now 3 rigorous backtests, the only proven profitable path is passive beta.**

This is not a failure of effort. It is the mathematical reality that:
1. The equity risk premium is real and large (~8–14% annually).
2. Beating it after costs requires genuine alpha, which is rare.
3. Most "strategies" are either beta in disguise, regime-dependent, or destroyed by costs.
4. The system's value is not in finding alpha — it is in **honestly measuring** that no alpha exists yet.

**The money deployment vehicle today:** VTI/BND or FXAIX/FSKAX/FXNAX.
**The research question:** Can ANY strategy beat this after costs on clean data?

---

*Simulations run on 2026-11-15 with real market data from Yahoo Finance. All costs included. All results reproducible.*
