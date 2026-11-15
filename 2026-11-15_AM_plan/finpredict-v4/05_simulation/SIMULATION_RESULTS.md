# Simulation Results — Proving the Path Forward

**Date:** 2026-11-15 (AM)
**Simulation:** `05_simulation/faber_dual_momentum_backtest.py` (verified, reproducible)
**Data:** real yfinance prices, auto-adjusted (splits + dividends), 2008-01 → 2026-11
**Costs:** 10bp round-trip turnover + 4bp annual expense drag
**Rules:** parameter-free, pre-registered (Faber 200-day MA; 6-month momentum), no curve-fitting

---

## Results Table

| Strategy | Final multiple | CAGR | Vol | Sharpe | Max drawdown | Excess vs SPY |
|----------|---------------|------|-----|--------|--------------|---------------|
| **SPY buy-and-hold** | 7.93× | 11.62% | 15.53% | 0.79 | **-46.3%** | — |
| **Faber 200d MA (all-asset)** | 7.39× | 11.15% | 11.23% | **1.01** | **-18.8%** | -6.9% |
| **Dual momentum (top-1)** | 3.26× | 6.45% | 11.57% | 0.60 | -13.5% | -58.9% |

---

## The proof (what this actually shows)

1. **Faber 200-day MA ≈ buy-and-hold return, at less than half the drawdown.**
   - 18-year final: 7.39× vs 7.93× — nearly identical.
   - Max drawdown: **-18.8% vs -46.3%** — the trend filter skips the worst bear markets.
   - Sharpe: **1.01 vs 0.79** — better risk-adjusted return.
   - This is the *grounded, defensible* path: you give up ~7% of 18-year cumulative return to cut the worst drawdown by ~27.5 points. For an investor, that is the classic "buy the index, but don't ride the crash" win.

2. **Dual-momentum (top-1) underperforms** — single-asset concentration sacrifices return (3.26×) for lower drawdown. It is a *diversifier/risk* tool, not the primary return engine.

3. **All rules are parameter-free and pre-registered** — no tuning to fit this window, so the result is not a curve-fit artifact. It reproduces Faber's published finding.

---

## Why this proves "profitability at least in backtest"

- It **beats the buy-and-hold benchmark on a risk-adjusted basis** (Sharpe 1.01 > 0.79; DD -18.8% vs -46.3%).
- It is **cost-inclusive** (turnover + expense drag applied).
- It is **mechanistically grounded** (trend persistence + tail-risk avoidance), not pattern-mining.
- It uses **real market data** over an 18-year window spanning multiple regimes (2008, 2020, 2022).

---

## Honest caveats

- Total return is slightly *below* buy-and-hold (7.39× vs 7.93×). The edge is **risk-adjusted**, not absolute.
- Backtest ≠ future. The forward-test protocol (below) is the required next gate.
- Momentum/trend has flat periods (e.g., 2010s for CTAs) — expect drawdowns even with the filter.

---

## The forward-test tracking protocol (to confirm live)

See `05_simulation/FORWARD_TEST_PROTOCOL.md` — a lightweight, drop-in tracker to decide fast whether a strategy can be kept, trimmed, or dropped, and whether holding period should be extended.
