# EQUITY — Concrete Profitability Strategy

**Asset Class:** EQUITY / STOCKS
**Status:** NOT_PROVED (Closest candidate needs clean forward OOS)
**Date:** 2026-11-14
**Sources:** flaxen-hair H10, finpredict-v3 fundamental factor, finpredict-v2 market-neutral

---

## Strategy 1: RSI(2) Mean Reversion on Broad Indices (Closest to Proven)

### Method
- **Signal:** RSI(2) < 30 = LONG, RSI(2) > 70 = FLAT (or short if market-neutral)
- **Universe:** SPY, QQQ (broad, liquid, low-cost)
- **Holding period:** 1–5 days (mean-reversion horizon)
- **Risk:** 2% per trade
- **Cost model:** 0.05% commission + 0.02% spread (ETF liquidity)

### Evidence (from flaxen-hair H10)
| Metric | Value | Risk |
|--------|-------|------|
| OOS Sharpe | 1.83 | **CONTAMINATED** — OOS created after H7's OOS was inspected |
| Effective N | ~38 | Below n≥60 threshold |
| DSR | 0.9365 | Below 0.95 threshold |
| Best day | +11.20% (2025-04-09) | Single-day dependence |
| 2-day-lag Sharpe | 0.696 | Execution fragility |

### Why It Might Work
Short-term mean reversion in broad equity indices is a documented anomaly (fades after 1–5 days). RSI(2) captures extreme short-term oversold conditions in liquid ETFs with tight spreads.

### Why It Might Fail
1. **OOS contamination** — the "out-of-sample" period was created after inspecting prior OOS results
2. **Single-day dependence** — one day (+11.20%) drives the Sharpe; remove it and results collapse
3. **Execution fragility** — 1-day execution lag drops Sharpe from 1.83 to 0.696
4. **Regime dependence** — works in chop, fails in strong trends
5. **T-bill carry dependency** — returns may be partly explained by cash yield, not edge

### Required Fixes Before Deployment
1. **Clean forward OOS test** — freeze parameters NOW, do not touch them, run for 90 calendar days or 30 round trips
2. **Remove best-day sensitivity** — report Sharpe with and without the best day
3. **2-day-lag test** — confirm Sharpe ≥ 1.0 with realistic execution lag
4. **Risk-matched benchmark** — compare to buy-and-hold with same volatility, not raw Sharpe

### Proof Criteria
- Clean forward OOS: n ≥ 30, Sharpe > 1.0
- DSR ≥ 0.95 after removing best day
- 2-day-lag Sharpe ≥ 1.0
- Risk-matched benchmark outperformance
- 90-day paper trading PF > 1.2

---

## Strategy 2: Fundamental Factor Sleeve (Long-Term)

### Method
- **Signal:** Piotroski F-score (quality) + value (P/B, P/E) + low-volatility
- **Universe:** 50+ liquid US equities
- **Rebalancing:** Monthly
- **Weighting:** Equal-risk-weight across factors
- **Construction:** Market-neutral long/short (long high-score, short low-score)

### Why It Might Work
Cross-sectional factor premia (value, quality, low-vol, momentum) have decades of peer-reviewed support. Market-neutral construction removes beta exposure so edge is measured vs zero, not vs B&H.

### Why It Might Fail
1. **No realized evidence in repo** — current fundamental modules have zero closed-trade history
2. **Data source** — earnings data feed not reliably wired
3. **Factor crowding** — well-known factors may be arbitraged away
4. **Monthly rebalancing** — too slow for the current pick-trading dashboard

### Required Fixes Before Deployment
1. Wire real earnings/fundamental data source (yfinance, FMP, or Quandl)
2. Build monthly walk-forward backtest with 10+ years of history
3. Test vs risk-matched benchmark
4. Confirm net Sharpe > 0.4 after costs

### Proof Criteria
- 10+ year backtest, monthly rebalancing
- Net Sharpe > 0.4
- PF > 1.2
- Positive alpha vs risk-matched benchmark
- Survives 2022 bear market

---

## Strategy 3: PEAD / Earnings Drift (Event-Driven)

### Method
- **Signal:** Post-earnings announcement drift (stocks drift in direction of earnings surprise for 1–60 days)
- **Universe:** Liquid equities with reliable earnings dates
- **Entry:** Day after earnings announcement
- **Holding period:** 5–20 days
- **Risk:** 1% per trade (event-driven = higher variance)

### Why It Might Work
PEAD is one of the most persistent market anomalies. Stocks that beat earnings estimates tend to drift upward for days/weeks after announcement.

### Why It Might Fail
1. **Data dependency** — requires reliable earnings calendar + surprise estimates
2. **Crowding** — well-known; may be arbitraged
3. **Low frequency** — only 4 earnings seasons per year per stock

### Verdict
**Medium-term research project.** Not viable until fundamental data feed is fixed.

---

## EQUITY Implementation Roadmap

| Phase | Timeline | Task | Deliverable |
|-------|----------|------|-------------|
| A | Week 1 | Freeze H10 parameters, start clean forward OOS | Frozen parameter file; daily log |
| A | Weeks 2–13 | Run forward OOS (90 days) | 90-day report: Sharpe, PF, WR, DSR |
| B | Month 4+ | If Phase A passes, paper trade H10 | Paper trading log; continuous monitoring |
| C | Month 6+ | Build fundamental factor backtest | 10+ year backtest report |
| D | Month 9+ | If both A and C pass, blend H10 + fundamental | Combined portfolio backtest |

---

## Position in Portfolio
- **Weight:** 15–20% of total book (if/when proven)
- **Primary:** H10 RSI(2) on SPY/QQQ (if clean forward passes)
- **Secondary:** Fundamental factor sleeve (monthly rebalancing)
- **Risk per trade:** 2% max
- **Daily loss cap:** −5%
- **Re-evaluation:** Weekly StrategyCertifier run
