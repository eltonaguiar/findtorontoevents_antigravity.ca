# Outperform S&P 500 / Outperform Buy & Hold — The Missing Bar
**Date:** 2026-11-15  
**Purpose:** Address the gap explicitly flagged by the user: earlier analysis did not sufficiently cover "outperform S&P 500" and "outperform buy & hold" as required bars for any equity/ETF edge claim.  
**Status:** Required reading before any equity/ETF promotion discussion.

---

## 1. Why this bar matters

A prediction system that generates positive raw PnL but **does not beat SPY total return** or **buy & hold of the same universe** is not delivering alpha — it is delivering beta (or luck) at higher cost, complexity, and risk. The honest bar for any equity/ETF sleeve is:

> **Can this strategy, after all costs, beat a transparent, passive benchmark over the same out-of-sample window, with comparable or lower risk?**

If the answer is no, the strategy is not worth deploying — regardless of its backtest WR or PF.

---

## 2. The required evidence (per strategy/class)

For any equity or ETF claim, the agent/analyst must produce:

| Evidence item | What to show |
|---------------|--------------|
| **Excess return vs SPY total return** | Strategy cumulative return minus SPY total return (dividends reinvested) over the same OOS window |
| **t-stat / significance** | Is the excess return statistically distinguishable from zero? (Correct for multiple testing.) |
| **Buy & hold comparison** | Same-entry-date buy-and-hold of the traded universe vs the strategy's actual entries/exits |
| **Cost-adjusted** | Deduct per-class slippage/commissions/fees BEFORE comparing to benchmark |
| **Risk-adjusted** | Report Sharpe/Sortino/Calmar vs benchmark, not just raw return |
| **Multiple-testing corrected** | Correct `nb_trials`; DSR ≥ 0.95; SPA p ≤ 0.10 |
| **Published n** | Forward trades count must be stated; n ≥ 100 (Tier 2) / ≥ 500 (Tier 1) |

**Without all of the above, the claim is unverifiable and should be treated as a hypothesis, not an edge.**

---

## 3. Current state — nothing has cleared this bar

| System / sleeve | Raw claim | Cost-adjusted vs SPY total return? | OOS with published n? | Verdict |
|-----------------|-----------|-----------------------------------|----------------------|---------|
| `stocks_rsi2_pullback` | 75.7% WR, p=6×10⁻⁶, Sharpe 4.84 | Not yet demonstrated on clean OOS | Not yet (n at floor, backtest-oriented) | Hypothesis only |
| Profitable Approach Variant C | PF 1.26, +98.7pp over 8 months | vs SPY total return not yet run | 8 months forward, n=237 | Pilot-grade; PF < 1.5 |
| `multi_asset_cot` | PF 21.33, WR 88.2% | Not verified; likely one-symbol concentration | Not verified | Likely artifact |
| All other 22 hypotheses | Various WR/PF | None cleared IC ≈ 0, IC ≈ 0 | None | All failed |

**Result: zero strategies in this system have demonstrated a clean, cost-adjusted, out-of-sample beat of SPY total return or buy & hold.** Until one does, the honest capital deployment is the boring alternative.

---

## 4. The boring alternative — why it wins by default

| Option | Expected return | Risk | Effort | Requires prediction system? |
|--------|----------------|------|--------|------------------------------|
| Low-cost broad index ETF (SPY, VTI, ITOT) | Equity risk premium (~7-10%/yr long-run) | Market drawdown (~50% in bad crises) | Near zero | No |
| Passive mutual fund (VFIAX, VTSAX, FXAIX) | Same as above + expense drag (~0.04-0.05%) | Same | Near zero | No |
| Short-duration bonds / T-bills | Risk-free rate (~4-5%) | Very low | Near zero | No |
| Any unproven prediction-system signal | Unknown (likely negative after costs) | High (overfit, stale data, costs) | High (monitoring, gates) | Yes — but unproven |

**Conclusion:** Until the prediction system produces **one** clean, cost-adjusted, out-of-sample strategy that beats SPY total return with published n, the highest-probability lower-risk deployment is diversified low-cost index exposure — not the system's signals.

---

## 5. How an agent should test this (prompt addition)

Add to every EQUITY/ETF agent's work instructions:

> **Benchmark test (mandatory):**
> 1. Pull the strategy's forward trades (entry date, exit date, direction, size, PnL).
> 2. Build a same-window buy-and-hold of SPY (total return, dividends reinvested) for the same capital.
> 3. Build a same-entry-date buy-and-hold of the traded universe (buy at each entry price, hold until each exit).
> 4. Compute strategy excess return vs both benchmarks, cost-adjusted.
> 5. Report t-stat, Sharpe, Sortino, Calmar vs benchmark.
> 6. Require n ≥ 100 forward, DSR ≥ 0.95 with correct `nb_trials`, and excess return > 0 after costs.
> 7. If the strategy does NOT beat both benchmarks on clean OOS, report "no alpha vs benchmark" — do not promote.

---

## 6. Bottom line

"Outperform S&P 500" and "outperform buy & hold" are not optional extras — they are the **defining test** of whether a prediction system has any edge at all. Positive raw PnL without beating a passive benchmark is just expensive beta. No strategy in this system has passed that test yet. Deploy capital to low-cost index exposure until one does.

---
