# CRYPTO — Concrete Profitability Strategy

**Asset Class:** CRYPTO
**Status:** Best Candidate (Only class with tested strategy)
**Date:** 2026-11-14
**Sources:** finpredict-v3 ITERATION-005, flaxen-hair mega_mutation, finpredict-v2 funding carry

---

## Strategy 1: Vol-Targeted Time-Series Momentum (Flagship)

### Method
- **Signal:** 50-day / 200-day SMA time-series momentum, long-only/flat (no shorts)
- **Universe:** 10–40 liquid crypto pairs (BTC, ETH, SOL, LINK, NEAR, AVAX, plus expandable list)
- **Volatility targeting:** 20% annualized volatility target per position
- **Costs:** 0.1% per side (taker fee + slippage stress)
- **Weighting:** Equal-risk-weight across assets (not equal notional)

### Evidence (from finpredict-v3 ITERATION-005)
| Metric | Value |
|--------|-------|
| Net Sharpe | 2.13 |
| t-statistic | 5.56 |
| 95% CI | [1.25, 3.25] |
| OOS Sharpe | 2.06 → 2.33 |
| Positive assets | 10/10 |
| Max Drawdown | −17.4% |
| vs Buy-and-Hold | Under-returns B&H in bull; value is drawdown control |

### Why It Might Work
Time-series momentum (trend-following) is the most robust documented risk premium in crypto. The strategy cuts drawdowns in half vs buy-and-hold (−17% vs −36%) while maintaining positive expectancy. Long-only/flat avoids the funding-cost drag of perpetual short positions.

### Why It Might Fail
1. **B&H outperformance in bull markets** — the strategy under-returns buy-and-hold during strong uptrends
2. **Survivorship bias** — backtest may use coins that survived; dead coins are excluded
3. **Taker-cost stress** — 0.1% assumed; actual costs may be higher during volatility spikes
4. **Single-source concentration** — 94–98% of current signals come from one source (luxalgo)
5. **Data staleness** — current `current_price` is 172 days old for most picks

### Required Fixes Before Deployment
1. Wire `alpha_engine/universal_price_enricher.py` (Binance + yfinance) into dashboard build
2. Fix PnL units to ratio (not percent)
3. Add survivorship-adjusted universe (include delisted/failed coins)
4. Restate vs buy-and-hold benchmark (paired bootstrap)
5. Add taker-cost stress test (0.15%, 0.2% scenarios)

### Proof Criteria
- n ≥ 60 closed trades on fresh data
- Paired bootstrap vs B&H: `pass_95 = true` (frac_positive ≥ 0.95)
- Random-entry MC percentile ≥ 0.90
- PF > 1.05 net of costs
- Max drawdown < 25%
- 90-day paper trading PF > 1.5

---

## Strategy 2: Mega-Mutation MACD+RSI (Secondary)

### Method
- **Signal:** MACD + RSI confluence on tournament-validated gene combinations
- **Symbols:** 8 verified combos — JUPUSDT(m048), ENAUSDT(m084), ADAUSDT(m017), WIFUSDT(m048), STXUSDT(m048), RENDERUSDT(m048), AVAXUSDT(m006), DOTUSDT(m006)
- **Entry:** Exact tournament gene conditions
- **TP/SL:** ATR-based (asymmetric reward/risk)
- **Risk:** 2% per trade
- **Regime filter:** BTC price > 200-day EMA (bull market only)
- **Correlation limit:** Max 1 position per correlated group

### Evidence (from flaxen-hair)
| Metric | Value |
|--------|-------|
| Forward PF | 8.32 |
| Forward WR | 84% |
| Forward n | 50 |
| Lab PF | 2.79 |

### Key Risk
- **Internal contradiction:** flaxen-hair's own files disagree on production readiness (`production_enable=true` vs `false`)
- **pf_drift > 30%** — forward PF (8.32) is 3x lab PF (2.79), which could indicate overfitting or regime shift
- **Small sample** — n=50 forward is below n≥60 gate threshold
- **Data staleness** — tournament genes may be stale if market regime changed

### Verdict
**High-risk candidate.** The forward results look impressive but the pf_drift is concerning. Treat as a secondary sleeve (max 20% of CRYPTO book) only after Strategy 1 is proven. Do NOT deploy as primary.

---

## Strategy 3: BTC Funding/Carry Sleeve (Income)

### Method
- **Signal:** Funding-rate spread carry on BTC perpetual futures
- **Capital cap:** 10–15% of total CRYPTO book
- **Holding period:** As long as funding rate is positive

### Evidence
| Metric | Value |
|--------|-------|
| DSR | 1.0 |
| Real return | ~3.7–4.8% (at 1.5x capital) |
| vs Cash | Clears cash at 1.5x capital |

### Key Risk
- **Capital-intensive** — requires large capital for small return
- **Funding rate can turn negative** — negative carry periods erode returns
- **Exchange risk** — counterparty risk on perpetual futures

### Verdict
**Low-risk, low-return diversifier.** Deploy only after Strategy 1 is live and profitable. Cap at 10–15% of book.

---

## CRYPTO Implementation Roadmap

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Fix price freshness + PnL units | Live `current_price` on all picks; ratio PnL |
| 2 | Run ITERATION-005 on fresh data | Fresh backtest report with B&H benchmark |
| 3 | Add survivorship-adjusted universe | Universe includes delisted coins; restate backtest |
| 4 | Paired bootstrap + MC timing test | `pass_95` and MC percentile report |
| 5–8 | Paper trading (90 days) | Daily PnL log; PF tracking |
| 9+ | If PF > 1.5 for 90 days, deploy with 2% risk/trade | Live trading with continuous monitoring |

---

## Position in Portfolio
- **Weight:** 60–70% of total book (core strategy)
- **Risk per trade:** 2% max
- **Daily loss cap:** −5%
- **Monthly loss cap:** −20%
- **Re-evaluation:** Weekly StrategyCertifier run; demote to paper if any gate fails for 7 consecutive days
