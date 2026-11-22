# Paper-Trade Spec — US Large-Cap Momentum Sleeve

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 05:30 EST
**Purpose:** an auto-tracked simulated portfolio to gather the forward evidence that the equity-momentum backtest needs before any real-money decision.

---

## 1. Why this strategy

From `cost_adjusted_walkforward_backtest.json` (cost 20 bps/trade, 27 combos) the best variant is:

| Metric | Value |
|---|---|
| Lookback / skip / n-long | 6m / 2m / top-3 |
| Profit factor | 2.94 |
| Sharpe (annualized) | 1.30 |
| Win rate | 61.7% |
| Total return (2015+) | ~3,699% vs SPY B&H 359% |
| Max drawdown | 29.5% |

**Caveat:** only 4/27 combos raw-pass T2, ~1.35 false passes expected. This is a *hypothesis*, not proof — exactly why it needs a forward paper run.

---

## 2. Sleeve rules

- **Universe:** 30 large caps (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AVGO, ORCL, JPM, BAC, WFC, GS, MS, BLK, JNJ, PFE, UNH, ABBV, LLY, WMT, HD, COST, KO, MCD, XOM, CVX, PG, PEP, TMO).
- **Signal:** rank by 6-month momentum (skip 2m, i.e., use months t−8..t−2); hold **top 3** long.
- **Rebalance:** monthly.
- **Cost model:** 20 bps/trade round-trip (matches backtest).
- **Size:** equal-weight across the 3 positions; start with a nominal paper balance (e.g., $10,000).
- **Benchmark:** SPY buy-and-hold (same window) for IR/alpha comparison.
- **Auto-track:** record each entry/exit in a paper ledger (JSON/CSV) on every rebalance; we will compute forward WR, PF, Sharpe, and 2× cost stress as rows accrue.

---

## 3. Success gate (to decide real-money)

- n ≥ 100 closed forward trades.
- Net-expectancy CI lower bound > 0 at **2×** slippage.
- IR ≥ 0.5 vs SPY.
- Split-half stable.
- **Only then** consider a small real allocation; until then it is 100% paper.

---

## 4. Implementation options

1. **TradingView paper account** (the fleet already uses `tv-paper-trade` / `tv-portfolio-extract`): create a dedicated `MOM3-EQUITY` paper portfolio, place the monthly top-3, and extract every cycle.
2. **Repo-side simulator:** a small script that reads daily closes for the 30-name universe, applies the 6/2 momentum rule, and writes `reports/paper_momentum_ledger.jsonl`.

Recommend option 1 (live, auto-tracked, visible over time) + option 2 as a backstop.

---

## 5. What this produces

The forward rows this ledger creates will feed `reports/forward_observations.jsonl` → the audit2 clock, giving the book its first *testable* confirmatory file for equity.

---
*Not investment advice. Paper only.*
