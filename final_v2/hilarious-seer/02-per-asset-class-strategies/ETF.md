# ETF — Concrete Profitability Strategy

**Asset Class:** ETF
**Status:** NOT_PROVED (Best candidate needs longer history + real feed)
**Date:** 2026-11-14
**Sources:** finpredict-v3 multi-asset trend, finpredict-v2 cross-sectional momentum

---

## Strategy: Multi-Asset Trend on ETF Universe (Diversifier)

### Method
- **Signal:** Time-series momentum (12-month lookback, or 50d/200d SMA) on ETF universe
- **Universe:** 20–50 liquid ETFs across equity, credit, commodity, FX, rates
  - Equity: SPY, QQQ, IWM, EEM, EFA, VTI
  - Credit: LQD, HYG, TLT, IEF
  - Commodity: GLD, USO, DBC
  - FX: UUP, FXE
  - Rates: TLT, IEF, SHY, TBT
- **Weighting:** Risk-parity (equal volatility contribution, not equal notional)
- **Rebalancing:** Monthly
- **Volatility target:** 10% annualized (lower than CRYPTO to reduce drawdown)
- **Costs:** 0.05% commission + ETF spread (~0.02–0.10%)

### Why It Might Work
Multi-asset trend-following is the most robust documented risk premium across asset classes. It performs well in crises (trend gets short) and provides diversification vs equity buy-and-hold. The " managed futures" CTA industry is built on this exact strategy.

### Evidence from Repo
| Test | Result | Assessment |
|------|--------|------------|
| H16 ETF XS momentum (top 3) | Sharpe 0.98 vs benchmark 1.18 | **Underperforms** — SPA p=0.488 |
| H18 ETF TSMOM breadth | WF 0.37 | **Borderline** |
| H17 ETF XS reversal | Failed | Not viable |
| H5 ETF dual momentum | Failed | Not viable |
| finpredict-v2 cross-sectional | Failed | Sharpe 0.98 vs 1.18 benchmark |

### Why Previous Tests Failed
1. **Insufficient history** — n=15 closed trades is far below statistical threshold
2. **No risk-parity weighting** — equal notional weighting over-concentrates in volatile assets
3. **No cost model** — ETF spreads and trading costs were underestimated
4. **Benchmark mismatch** — compared to B&H instead of risk-matched benchmark
5. **No regime filter** — traded through all regimes, including unfavorable chop

### Required Fixes Before Deployment
1. **Longer history** — need 10+ years of ETF price data for robust backtest
2. **Real cost model** — include ETF spreads, commission, slippage
3. **Risk-parity weighting** — target equal volatility contribution per asset
4. **Regime filter** — only trade when SPY > 200-day SMA (avoids bear-market chop)
5. **Roll handling** — for commodity ETFs, handle contango/backwardation

### Proof Criteria
- 10+ year backtest with monthly rebalancing
- Net Sharpe > 0.5
- PF > 1.2
- Max drawdown < 20%
- Positive alpha vs risk-matched benchmark
- Walk-forward: ≥60% profitable folds, mean OOS PF > 1.2

---

## Why ETFs Are the Natural Diversifier

| Feature | CRYPTO Trend | ETF Multi-Asset Trend |
|---------|-------------|----------------------|
| Correlation to equity | Low | Low-to-moderate |
| Crisis performance | Unknown | Historically positive (trend gets short) |
| Drawdown control | Good (−17%) | Excellent (<−20%) |
| Capacity | Medium | High |
| Costs | Higher (0.1%) | Lower (0.05%) |
| Sharpe target | 0.5–2.1 | 0.4–0.8 |

The ETF sleeve provides ballast when CRYPTO or EQUITY underperforms. It is the natural second strategy after CRYPTO trend is proven.

---

## ETF Implementation Roadmap

| Phase | Timeline | Task | Deliverable |
|-------|----------|------|-------------|
| A | Month 1–2 | Build 10+ year ETF price database | SQLite/JSON with monthly prices for 50 ETFs |
| B | Month 2–3 | Implement risk-parity trend backtest | Backtest report: Sharpe, PF, drawdown, benchmark comparison |
| C | Month 3–4 | Add cost model + regime filter | Cost-adjusted backtest; regime-stratified results |
| D | Month 4–6 | Walk-forward analysis | 10-fold WFA report |
| E | Month 6–9 | Paper trading (if backtest passes) | Paper log; continuous monitoring |
| F | Month 9+ | Deploy as 20% diversifier sleeve | Live with 2% risk/trade |

---

## Position in Portfolio
- **Weight:** 20% of total book (diversifier, lower vol target)
- **Primary:** Multi-asset trend on 20–50 ETFs
- **Risk per trade:** 1% max (lower than CRYPTO due to monthly rebalancing)
- **Daily loss cap:** −3% (lower vol target)
- **Re-evaluation:** Monthly StrategyCertifier run

---

## Honest Assessment

ETF multi-asset trend is the most theoretically sound diversifier strategy, but the repo has **zero proven ETF edge today**. Previous tests (H16, H18) failed because of insufficient data, poor cost models, and wrong benchmarks. This is a **6–9 month build** before deployment. Do not rush.
