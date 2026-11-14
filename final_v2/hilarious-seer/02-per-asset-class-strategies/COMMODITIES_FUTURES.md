# COMMODITIES & FUTURES — Concrete Profitability Strategy

**Asset Class:** COMMODITIES / FUTURES
**Status:** BLOCKED (no real feed; crypto proxies; 44/44 rows mislabeled)
**Date:** 2026-11-14
**Sources:** finpredict-v3 CTA trend, scratch-hippodraco veto

---

## Strategy: CTA Trend on Liquid Futures (BLOCKED — Prerequisites Not Met)

### Method (Theoretical Only)
- **Signal:** Time-series momentum (12-month lookback) on liquid futures
- **Universe:** ES (S&P 500), NQ (Nasdaq), CL (crude oil), GC (gold), ZN (10-year Treasury), NG (natural gas), ZC (corn), ZS (soybeans)
- **Direction:** Long or short based on 12-month return
- **Weighting:** Risk-parity (equal volatility contribution)
- **Rebalancing:** Monthly
- **Volatility target:** 10% annualized
- **Costs:** 0.02% futures commission + roll costs

### Why It Might Work (If Ever Built)
Managed futures / CTA trend is a $300B+ industry built on this exact strategy. It performs well in crises (trend gets short equities, long bonds, long gold) and provides uncorrelated returns to traditional portfolios. The "trend risk premium" is one of the most robust documented premia across all asset classes.

### Why It Cannot Be Built Today
1. **No real futures feed** — current commodity generator uses crypto proxies (RNDR/ARB/XLM/DOT for silver/oil)
2. **44/44 rows mislabeled** — all commodity rows are actually `=F` futures mislabeled
3. **Date-only timestamps** — no intraday precision for futures entries
4. **No roll handling** — futures expire monthly; continuous contracts require back-adjustment
5. **Class in BLOCKED_ASSET_CLASSES** — explicitly disabled

### Required Prerequisites (All Must Be Met)
1. **Real futures data feed** — CME, ICE, or Bloomberg for front-month prices
2. **Roll handling** — back-adjusted continuous contracts with contango/backwardation accounting
3. **Contango/backwardation model** — roll yield is a major component of futures returns
4. **Cost model** — futures commission, margin, roll costs
5. **Remove from BLOCKED_ASSET_CLASSES** — only after 1–4 are complete

### Proof Criteria (For When Prerequisites Are Met)
- 20+ year backtest (futures have long history)
- Net Sharpe > 0.5
- PF > 1.2
- Max drawdown < 20%
- Positive crisis performance (2008, 2020)
- Walk-forward: ≥60% profitable folds

---

## scratch-hippodraco Veto

> "Discard 'unblock now', 'delete rows', 'fabricate rows' — v2 reviewer veto list is the right filter."

The scratch-hippodraco peer review **explicitly vetoes** any attempt to unblock commodities/futures without a real feed. This is correct and unanimous across peers.

---

## COMMODITIES Implementation Roadmap

| Phase | Timeline | Task | Deliverable |
|-------|----------|------|-------------|
| A | Month 1–3 | Procure real futures data feed (CME/ICE/Bloomberg) | Historical futures prices |
| B | Month 2–4 | Build roll handling + continuous contracts | Back-adjusted price database |
| C | Month 3–5 | Build contango/backwardation model | Roll yield calculator |
| D | Month 4–6 | Backtest CTA trend | 20+ year backtest report |
| E | Month 7–12 | Paper trading (if backtest passes) | Paper log |
| F | Month 12+ | Remove from BLOCKED_ASSET_CLASSES; deploy as 10% sleeve | Live with 1% risk/trade |

---

## Honest Assessment

FUTURES/COMMODITIES have the **highest theoretical potential** (CTA trend is a proven industry) but the **lowest readiness** in this repo. The current system uses crypto proxies for commodities, which is statistical malpractice. **Keep BLOCKED until a real feed exists.** This is a 12-month build minimum. Priority: lowest.
