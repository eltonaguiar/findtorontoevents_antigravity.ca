# BOND credit-spread + duration-rotation overlays — swarm projections NOT MET

**Date:** 2026-05-13
**Tools:** `tools/backtest_bond_credit_spread_overlay.py`, `tools/backtest_bond_duration_rotation.py`
**Swarm projection:** Sharpe 0.57 → 1.0+ (4/4 BOND engines)
**Actual:** Sharpe lift marginal (+0.00 to +0.05). **Projection FAILED.**

## Result table

| Variant | n | PF | Sharpe | MDD% | Total% | vs Baseline |
|---|---:|---:|---:|---:|---:|---|
| Baseline HYG/LQD 6m mom | 224 | 1.64 | **0.58** | 29.1 | +140 | — |
| Credit-spread HYG-LQD Δ > -1% | 173 | 1.60 | 0.58 | 22.0 | +78.6 | flat Sharpe; -44% return |
| Credit-spread HYG-LQD Δ > -2% | 193 | 1.41 | 0.41 | 28.6 | +58.4 | worse |
| Credit-spread HYG-LQD Δ > -3% | 208 | 1.44 | 0.44 | 28.2 | +72.1 | worse |
| Credit-spread HYG-LQD Δ > -5% | 221 | 1.61 | 0.58 | 28.6 | +123 | minimal change |
| Duration rotation TLT/IEF/SHY (10y-5y spread) | 279 | 1.34 | **0.36** | 27.3 | +117 | worse than baseline |
| Buy-and-hold TLT benchmark | — | — | 0.31 | — | +113 | — |

## Why the projections failed

**Credit-spread variant:** Used HYG-LQD 1-month return delta as proxy for OAS spread widening. The proxy is too coarse — swarm engines proposed `BAMLH0A0HYM2` (HY OAS from FRED), which has tighter signal-to-noise. The price-delta sometimes lags the actual spread move by ~weeks.

**Duration rotation:** Used `^TNX - ^FVX` (10y-5y) as proxy for 10y-2y curve. Result: 10y-5y spread never inverted in 22-year sample, so the defensive (SHY) bucket never triggered. Real 10y-2y was inverted Jul 2022-Sep 2024, but 10y-5y was not — the proxy is the wrong curve point.

## Lessons

1. **yfinance proxies aren't substitutes for FRED.** Real-money BOND strategies need actual OAS spreads + actual 2y yield, not price-derived approximations.
2. **Swarm projections rely on idealized signal quality.** When swarm proposes a strategy citing "BAMLH0A0HYM2" or "DGS10-DGS2", the projection assumes those exact series — not whatever proxy we have lying around.
3. **BOND class is genuinely hard.** Of all 5 classes tested this session, BOND has the weakest backtested edge. Live `/audit` PF 0.66 may not be a bug — it may be the asymptotic limit of free-tier BOND signal.

## Recommendation

Defer BOND overlay wire-in until FRED API key is operational + adapter implementation. Per `reports/swarm_revalid_20260513/synthesis_equity_bond.md`:

```
BD4 — Wire FRED data adapter (existing fred_data_fetcher.py + FRED_API_KEY) for all above
```

Until FRED is wired, BOND class stays at baseline PF 1.62 (HYG/LQD momentum) without overlay enhancement.

## What was learned that DOES help

Compare to EQUITY VIX-regime overlay shipped same day:
- VIX is available via yfinance `^VIX` cleanly — high-quality signal
- BOND OAS spreads need FRED — yfinance only gives raw HYG/LQD prices

**Signal quality lesson:** when swarm proposes overlay strategies, evaluate the **data source quality** before projecting Sharpe lifts. yfinance is great for price/vol; weak for fundamental spreads.

## Cross-references

- `tools/backtest_bond_tlt_ief_momentum.py` — baseline (PF 1.62 / Sharpe 0.57)
- `reports/swarm_revalid_20260513/synthesis_equity_bond.md` — original projection
- `reports/equity_vix_regime_breakthrough_20260513.md` — successful overlay (VIX worked)

NFA. No production change.
