# Re-validate BOND asset-class edge against REAL backtest data

## Context

`tools/backtest_bond_tlt_ief_momentum.py` shipped this session. Tested 4 variants:
- TLT/IEF 12-1m momentum: underperformed B&H TLT
- **HYG/LQD 6m skip-1 momentum (WINNER)**: PF 1.62 / WR 62.7% / Sharpe 0.57 / Total +161% over 22 years

Universe: HYG (high-yield ETF), LQD (investment-grade ETF). Monthly rebalance, top-1 selection.

## Real backtest results

- n = ~250 periods (~22 years, 2003-2026)
- WR = 62.7%
- Profit Factor = 1.62
- Sharpe (annualized) = 0.57
- Max Drawdown < 20% (passes TIER-2)
- Beats B&H TLT total return

Live `/audit` BOND class: PF 0.66 / WR 54.5% / n=11 (sub-floor, thin sample).

## Tier classification

- TIER-2 confirmed: PF 1.62 > 1.5, WR 62.7 > 50, MDD < 20, n >> 100
- TIER-1 fail: PF 1.62 < 2, Sharpe 0.57 < 1

## Question to engines

You are a quant researcher. BOND class is sub-floor live (PF 0.66, n=11). The HYG/LQD 6m momentum offline beats this 2.5×. Sharpe 0.57 is the weakest of any backtested class this session — the lift comes from PF asymmetry, not consistency.

**Your job:** propose 3-5 strategies that improve Sharpe from 0.57 → 1.0+ on the BOND universe without destroying the PF. Return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "thesis": "<1-sentence>",
      "signal_construction": "<exact rule>",
      "universe": ["<bond ETF tickers>"],
      "expected_pf": <number>,
      "expected_sharpe": <number>,
      "expected_mdd_pct": <number>,
      "differentiation_from_existing": "<vs HYG/LQD baseline>",
      "implementation_hours": <integer>,
      "wire_target": "<file>",
      "data_source": "<yfinance / FRED>",
      "fail_mode": "<most likely failure>"
    }
  ],
  "credit_spread_signals": ["<HYG-LQD spread, AAA-BAA, TED-spread, etc.>"],
  "duration_overlay_proposals": ["<short-duration vs long-duration regime>"],
  "killers": ["<existing live BOND emitter to retire>"],
  "tier1_attainability_pct": <0-100>,
  "single_most_important_finding": "<one sentence>"
}
```

## Constraints

- Universe restricted to liquid US bond ETFs: TLT / IEF / SHY / HYG / LQD / TIP / TIPX / BIL / VTIP / EMB
- Use yfinance + FRED only
- Reject expected_sharpe below 0.8
- MUST propose at least one credit-spread signal (FRED has DGS10, BAMLH0A0HYM2, etc.)
- MUST propose at least one duration-rotation framework
