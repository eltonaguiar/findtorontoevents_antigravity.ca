# FOREX — Concrete Profitability Strategy

**Asset Class:** FOREX
**Status:** NOT_PROVED (Pure gap — no tested strategies)
**Date:** 2026-11-14
**Sources:** finpredict-v3 carry basket, finpredict-v2 trend overlay

---

## Strategy: Carry Basket + Trend Overlay

### Method
- **Carry component:** Long high-yield currencies, short low-yield currencies, equal-risk-weighted
  - Long: AUD, NZD (higher rates)
  - Short: JPY, CHF (lower rates)
  - Pairs: AUD/JPY, NZD/JPY, USD/CHF
- **Trend overlay:** 200-day SMA filter — only trade carry when pair is above 200d SMA (avoids trending-against positions)
- **Holding period:** 1–4 weeks (carry accrues overnight)
- **Volatility target:** 8% annualized (FX is lower vol than crypto)
- **Costs:** 0.02% spread + rollover/swap costs

### Why It Might Work
FX carry is one of the oldest documented risk premia. High-yield currencies tend to appreciate or depreciate less than the interest differential, producing positive carry returns. The trend overlay removes positions where the pair is trending against the carry direction (e.g., AUD/JPY falling during risk-off).

### Why It Might Fail
1. **No real carry feed** — current repo has no reliable interest-rate data feed
2. **Frozen phantoms** — 11 frozen FOREX picks with no live prices
3. **Hard-disabled** — PR#6 has 0 call sites; FOREX pipeline is not wired
4. **Date-only timestamps** — 105–277 picks have date-only entry_time (no intraday precision)
5. **Low Sharpe** — realistic Sharpe ~0.3–0.6; this is a diversifier, not a headline edge
6. **Crash risk** — carry trades unwind violently during risk-off events (2008, 2020)

### Required Fixes Before Deployment
1. **Fix price feed** — wire real forex data (Frankfurter API for free rates, or OANDA)
2. **Purge phantoms** — quarantine 11 frozen FOREX picks
3. **Enable call sites** — wire PR#6 into production pipeline
4. **Build carry feed** — fetch central bank rates (FRED, ECB, RBA, BOJ) for interest differentials
5. **Add crash protection** — cut carry positions when VIX spikes >30 or JPY strengthens >2% in a day

### Proof Criteria
- n ≥ 60 closed trades
- Net Sharpe > 0.3
- PF > 1.1
- Max drawdown < 15% (carry crashes are the risk)
- Positive carry return after swap costs
- 90-day paper trading

---

## Alternative: Vol-Targeted Trend on FX Majors

### Method
- **Signal:** 50d/200d SMA trend on major pairs (EUR/USD, USD/JPY, GBP/USD, AUD/USD)
- **Direction:** Long or short based on SMA cross
- **Volatility target:** 8% annualized
- **Costs:** 0.02% spread

### Why It Might Work
Time-series momentum extends to FX majors. The same trend premium that works in CRYPTO and commodities also exists in currencies, albeit with lower magnitude.

### Why It Might Fail
1. **Central bank intervention** — CBs can cap/peg currencies, destroying trend signals
2. **Lower vol = lower returns** — realistic Sharpe ~0.3–0.6
3. **Same data problems** — frozen prices, phantoms, disabled pipeline

### Verdict
**Secondary to carry basket.** Trend overlay on carry is more promising than pure trend.

---

## FOREX Implementation Roadmap

| Phase | Timeline | Task | Deliverable |
|-------|----------|------|-------------|
| A | Month 1 | Fix price feed (Frankfurter/OANDA) | Live forex prices in repo |
| B | Month 1 | Purge phantoms + enable PR#6 call sites | Clean FOREX pipeline |
| C | Month 2 | Build carry feed (FRED/ECB rates) | Interest differential database |
| D | Month 2–3 | Backtest carry + trend overlay | 5+ year backtest report |
| E | Month 4–6 | Paper trading (if backtest passes) | Paper log |
| F | Month 6+ | Deploy as 10% diversifier sleeve | Live with 1% risk/trade |

---

## Honest Assessment

FOREX is a **diversifier, not a headline edge.** The realistic Sharpe is 0.3–0.6, which means it reduces portfolio volatility but won't drive returns. The carry basket is the most promising approach, but the repo has **zero FOREX infrastructure today** — no feed, no call sites, no proven strategies. This is a **6-month build** minimum. Priority: below CRYPTO and ETF.
