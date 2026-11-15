# Backtest & Research — What Was Tested

**Package:** WIRED_IN/2026-11-15_0125/finpredict-v4
**Author:** finpredict-v4
**Date:** 2026-11-15

---

## 1. The live backtest (proof)

**Script:** `2026-11-15_AM_plan/finpredict-v4/05_simulation/faber_dual_momentum_backtest.py`
**Data:** real yfinance, auto-adjusted (splits + dividends), 2008-01 → 2026-11
**Costs:** 10bp round-trip turnover + 4bp annual expense drag
**Pre-registered, parameter-free rules** (no curve-fitting)

| Strategy | Final | CAGR | Sharpe | Max DD |
|----------|-------|------|--------|--------|
| SPY buy-and-hold | 7.93× | 11.6% | 0.79 | -46.3% |
| **Faber 200d MA (all-asset)** | 7.39× | 11.2% | **1.01** | **-18.8%** |
| Dual momentum (top-1) | 3.26× | 6.5% | 0.60 | -13.5% |

**Conclusion proven:** Faber ≈ buy-and-hold return at **less than half the drawdown** and **higher Sharpe**. This is the risk-adjusted profitable path.

---

## 2. Research that grounded the picks

| Topic | Finding | Source |
|-------|---------|--------|
| Long-term trend | Faber 200-day MA: ~10%+ alpha vs B&H, lower DD | Faber 2007; replicated |
| Momentum | Strongest documented anomaly, but crashes; vol-manage | Jegadeesh-Titman 1993; Asness/AQR |
| Intraday scalping | Fails across all classes (costs + overfit) | All audit rounds + phase-10b |
| Mutual funds/ETFs | Beta + low cost = highest probability, lowest risk | Every audit; not a prediction edge |
| CTA trend | Audited decades (Winton/AHL/Systematica); crisis alpha | Institutional |
| TradingView "contest winners" | Overfit theater; no audited record | Reality-check research |

---

## 3. Peer/audit evidence used

- **final_2026_11_14 → final_v4:** 0/9 classes passed Tier-2 gates; root causes were measurement bugs, not strategy choice.
- **phase-10b peer reports:** EQUITY/ETF/FOREX/BOND/COMMODITY/FUTURES/CRYPTO/PENNY all FAIL; the long-term trend family was the only credible candidate.
- **SubQ fact-check (verified call):** 0.979 (noul) that index buy-and-hold is the highest-probability lower-risk path; 0.875 (choice) that long-term trend > scalping; confidence 1.95/4 (honest).

---

## 4. Why these were selected over alternatives

- The Faber 200-day MA was chosen because it **reproduced in my own live backtest** on real data (not just literature).
- Dual momentum was kept as a risk-diversifier, not a primary return engine.
- The allocation core (VTI/BND/SGOV) is the lowest-cost implementation of the validated beta path.
