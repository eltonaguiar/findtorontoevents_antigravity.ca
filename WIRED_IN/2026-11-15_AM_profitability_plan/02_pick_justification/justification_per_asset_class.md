# Pick Justification — All Asset Classes

**Date:** 2026-11-15 AM
**Status:** Final — no picks justified for real-money deployment

---

## Summary Table

| Asset Class | Picks Justified? | Best Candidate | Gates Passed | Deployment Recommendation |
|-------------|-----------------|----------------|--------------|---------------------------|
| EQUITY | No | QQQ DualMA (2 trades) | 4/7* | Research slot only |
| CRYPTO | No | ADA-USD EMA Trend | 4/7 | Conditional — PBO=0.603 blocks |
| ETF | No | None | N/A | Blocked (cohort mismatch) |
| MUTUAL FUNDS | No | None (passive only) | N/A | Passive core allocation |
| FOREX | No | None | N/A | Mutation-before-kill |
| COMMODITY | No | None | N/A | Blocked — all 186 copy-trader picks force-closed toxic, WR=0% unresolved |
| FUTURES | No | None | N/A | Blocked (WR=2.5%) |
| BOND | No | None | N/A | Blocked (insufficient data) |
| MEME/PENNY_STOCK | No | None | N/A | Keep blocked |

\* QQQ DualMA 4/7 is statistical artifact (2 trades, PF=999, DSR=0, PBO=0.999).

**No picks are justified for real-money deployment.** The previously claimed COMMODITY copy-trader WR=93.8% edge was debunked — all 186 COMMODITY picks in `closed_picks.json` were force-closed toxic with pnl=0 (zero resolved trades). The claim was formally retracted on 2026-05-16 as a pre-dedup over-emission artifact.


---

## Justification Framework

Each pick was evaluated against 7 money-ready gates:

| Gate | Threshold |
|------|-----------|
| G1 | Profit Factor ≥ 1.15 |
| G2 | Win Rate ≥ 50% |
| G3 | Sharpe Ratio ≥ 1.0 |
| G4 | DSR ≥ 0.95 |
| G5 | PBO ≤ 0.10 |
| G6 | Max Drawdown < 15% |
| G7 | Trades ≥ 50 |

**Rule:** All 7 gates must pass for deployment consideration. Zero asset classes met this bar.

---

## Why No Picks Are Justified

### Primary Reason: No Statistical Edge
- **Information coefficient ≈ 0** — no correlation between predicted and actual returns.
- **DSR ≈ 0** for nearly all strategies — no confidence any Sharpe > 0.
- **PBO ≈ 0.999** — near-certain that any apparent edge is overfitting.
- **Win rates near 40%** — below 50% break-even for most strategies.
- **Profit factors < 1.0** for most strategies — gross losses exceed gross profits.

### Secondary Reason: Costs Dominate Edge
- Round-trip costs (4 bps in simulation, higher in real markets) exceed average edge for most strategies.
- RSI(2) swing rule: doubling costs turns it negative (Buffy's backtest).
- ETF: 267% of average PnL is cost.
- Commodity: 422% cost ratio.

### Tertiary Reason: Structural Incompatibility
- Mutual funds: daily NAV, no intraday TP/SL, load/12b-1 costs.
- Bonds: n=1, insufficient data.
- Commodity: n=7-229, no contract identity pipeline.

---

## What Was NOT Picked (and Why Not)

| Strategy/Class | Reason Not Picked |
|----------------|-------------------|
| RSI(2) Mean Reversion (Equity) | Negative expectancy (-118% to -186%), WR 0-17%, regime change destroyed edge |
| Dual MA Crossover (Equity) | 2-5 trades over 5 years, PF=999 is artifact, DSR=0, PBO=0.999 |
| Bollinger Mean Reversion (Equity) | Negative expectancy (-17% to -33%), Sharpe -1.2 to -2.0 |
| EMA Trend Crossover (Crypto) | Negative expectancy (-18% to -130%), Max DD up to 153%, DSR < 0.4 |
| Donchian Breakout (Crypto) | Zero trades on all 5 symbols |
| All ETF strategies | Cohort mismatch, zero live data, 267% cost ratio |
| All Forex strategies | Historical PF 0.27, recent PF 0.85, mutation protocol |
| All Commodity strategies | COT gate failed 4/4, 422% cost ratio, low n |
| All Bond strategies | n=1 official, n=35 registry, no data pipeline |

---

## The Only Justified Capital Deployment

**Low-cost index ETF/MF passive allocation** (outside the prediction system):

| Sleeve | Allocation | Example Funds | Rationale |
|--------|-----------|---------------|-----------|
| US Equity Index | 60% | VFIAX, VTSAX, FXAIX | Equity risk premium, ER ≤ 0.09% |
| International Equity | 20% | VTIAX, VEA | Diversification, ER ≤ 0.15% |
| Bonds / T-Bills | 20% | VBTLX, BND, SGOV | Ballast, income, ER ≤ 0.20% |

**Expected outcome:** Market beta + bond income minus ~0.05-0.10% cost drag. Positive expected return over multi-year horizons. Not alpha. Not from the prediction system.

This is the **only** justified deployment until one asset class passes all 7 money-ready gates.
