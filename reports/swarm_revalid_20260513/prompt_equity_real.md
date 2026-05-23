# Re-validate EQUITY asset-class edge against REAL backtest data

## Context

`tools/backtest_equity_top_momentum.py` shipped this session: 30 large-cap US universe, top-5 long-only 12-1m momentum, monthly rebalance, 2015-2026.

## Real backtest results

- n = 122 periods (~10 years)
- WR = 64.75%
- Profit Factor = 2.82
- Sharpe (annualized) = 1.34
- Max Drawdown = **24.18%** (just over TIER-1 MDD≤10% threshold, but TIER-2 MDD≤20% also fails)
- Total return = +1516% over backtest vs SPY buy-and-hold +347%

Live `/audit` EQUITY class: PF 1.58 / WR 53.7% / n=421 (TIER-2 confirmed).
Backtest beats live by Δ-PF +1.24, Δ-Sharpe +0.34.

## Tier classification

- TIER-2 confirmed: PF 2.82 > 1.5, WR 64.75 > 50, n=122 > 100
- TIER-1 PF passes (2.82 > 2), WR passes (64.75 > 55), but **MDD 24.18 > 10 = TIER-1 fail**

## Question to engines

You are a quant researcher. The EQUITY backtest delivers TIER-1 PF and WR but fails TIER-1 MDD by 14pp. Live emitters deliver only PF 1.58 (TIER-2 floor).

**Your job:** propose 3-5 changes that (a) close the offline-to-live PF gap (1.58 → 2.5+), AND/OR (b) reduce MDD from 24.18% → <10% without destroying the PF. Return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "thesis": "<1-sentence>",
      "signal_construction": "<exact rule>",
      "universe": ["<symbols or universe rule>"],
      "expected_pf": <number>,
      "expected_sharpe": <number>,
      "expected_mdd_pct": <number>,
      "differentiation_from_existing": "<vs live emitters>",
      "implementation_hours": <integer>,
      "wire_target": "<file>",
      "data_source": "<yfinance / FRED / etc.>",
      "fail_mode": "<most likely failure>"
    }
  ],
  "mdd_reduction_techniques": ["<concrete vol-targeting / regime-filter / position-cap proposals>"],
  "live_to_offline_gap_diagnoses": ["<why live PF 1.58 < offline 2.82>"],
  "killers": ["<existing live EQUITY emitter to retire>"],
  "tier1_attainability_pct": <0-100>,
  "single_most_important_finding": "<one sentence>"
}
```

## Constraints

- Use yfinance + FRED (no Bloomberg / Refinitiv)
- Reject any holding > 60 days
- Reject expected_pf below 2.0 (TIER-1 floor since we already have TIER-2)
- MUST propose at least one regime-filter approach (e.g., VIX or yield-curve based)
- MUST propose at least one MDD-reduction technique that is friction-aware
