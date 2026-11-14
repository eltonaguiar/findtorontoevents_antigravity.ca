# BONDS — Concrete Profitability Strategy

**Asset Class:** BONDS / FIXED INCOME
**Status:** INSUFFICIENT_DATA (n=3 closed; effectively inactive)
**Date:** 2026-11-14
**Sources:** finpredict-v3 carry + duration tilt, finpredict-v2 FRED module

---

## Strategy: Duration Trend + Carry on Treasury ETFs

### Method
- **Signal:** Time-series momentum on Treasury ETFs (TLT, IEF, SHY, TBT)
  - Long TLT when price > 200d SMA (rates falling = bond prices rising)
  - Long TBT (inverse) when price < 200d SMA (rates rising)
  - Flat when chop (price within ±5% of 200d SMA)
- **Carry component:** Hold longer-duration bonds when yield curve is steep (term premium)
- **Universe:** TLT (20+ yr), IEF (7–10 yr), SHY (1–3 yr), TBT (inverse 20+ yr)
- **Rebalancing:** Monthly
- **Volatility target:** 6% annualized (bonds are lower vol)
- **Costs:** 0.03% ETF spread

### Why It Might Work
Duration/trend + carry are the canonical bond premia. When rates are trending down, long-duration bonds appreciate. When rates are trending up, inverse ETFs capture the move. The term premium (steep yield curve) rewards holding longer-duration bonds.

### Why It Might Fail
1. **n=3 closed trades** — insufficient for any statistical claim
2. **Null-price seeds** — most bond picks have no `current_price`
3. **No real feed** — FRED module exists but is not wired to pick generation
4. **Low vol = low returns** — realistic Sharpe ~0.3–0.6
5. **Rate regime dependence** — worked 1980–2020 (falling rates), may not work 2020–2030 (rising rates)

### Required Fixes Before Deployment
1. **Backfill real prices** — wire yfinance/FRED for TLT/IEF/SHY/TBT daily prices
2. **Never use `current=entry` placeholder** — label UNQUOTED when feed fails
3. **Gate class until n≥30** — do not claim any edge until 30+ closed trades
4. **Build duration-rotation model** — use yield curve slope (10y–2y spread) to rotate between SHY/TLT

### Proof Criteria
- n ≥ 30 closed trades
- Net Sharpe > 0.3
- PF > 1.1
- Max drawdown < 12% (bonds should not have equity-level drawdowns)
- Positive term premium capture
- Survives 2022–2023 rate-rising regime

---

## Alternative: Rate-Trend / Duration Rotation

### Method
- **Signal:** Yield curve slope (10-year Treasury yield − 2-year Treasury yield)
  - Steep curve (>100 bps): Long TLT (long duration)
  - Flat/Inverted curve (<50 bps): Long SHY (short duration) or cash
- **Data source:** FRED (10-year yield, 2-year yield)
- **Rebalancing:** Monthly

### Why It Might Work
The yield curve slope predicts future rate changes and economic conditions. A steep curve typically precedes economic expansion (good for long duration). An inverted curve typically precedes recession (flight to quality, also good for long duration — but timing matters).

### Why It Might Fail
1. **Lagging indicator** — yield curve inversions can precede recessions by 12–24 months
2. **Fed intervention** — QE/QT can distort yield curve signals
3. **Same data problems** — no wired FRED feed

### Verdict
**Research project, not deployment-ready.** The duration-trend strategy is simpler and more testable.

---

## BONDS Implementation Roadmap

| Phase | Timeline | Task | Deliverable |
|-------|----------|------|-------------|
| A | Month 1 | Wire FRED/yfinance for Treasury ETF prices | Live bond prices |
| B | Month 1–2 | Backfill 5+ years of TLT/IEF/SHY/TBT prices | Historical database |
| C | Month 2–3 | Backtest duration trend | Backtest report |
| D | Month 4–6 | Paper trading (if backtest passes) | Paper log |
| E | Month 6+ | Deploy as 5% ballast sleeve | Live with 0.5% risk/trade |

---

## Honest Assessment

BONDS are **ballast, not alpha.** The realistic Sharpe is 0.3–0.6, and the repo has **virtually no bond data** (n=3 closed trades). The class should be labeled `INSUFFICIENT_DATA` until a real feed is wired and n≥30 is achieved. Priority: below CRYPTO, ETF, and FOREX.
