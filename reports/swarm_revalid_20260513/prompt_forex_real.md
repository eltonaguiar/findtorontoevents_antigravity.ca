# Re-validate FOREX asset-class edge against REAL per-symbol mutation data

## Context

Prior live FOREX class metrics (`audit_dashboard/data/dashboard_data.json::performance.asset_class_health` 2026-05-12):
- n = 1169, WR = 46.4%, PF = **0.27** (sub-floor, genuine bleed)

But this class number HIDES extreme heterogeneity per `reports/aa7_forex_per_symbol_mutation_20260513.md`:

**Per-symbol decomposition of `multi_asset_copytrader` × FOREX (n=662 terminal):**

| Symbol | n | WR% | PF | PnL% sum |
|---|---:|---:|---:|---:|
| EURJPY=X | 154 | 1.9 | 0.02 | -0.77 |
| USDJPY=X | 132 | 3.0 | 0.04 | -0.66 |
| GBPJPY=X | 84 | 7.1 | 0.10 | -0.35 |
| AUDJPY=X | 77 | 3.9 | 0.06 | -0.35 |
| NZDUSD=X | 58 | 15.5 | 0.29 | -0.17 |
| CADJPY=X | 37 | 10.8 | 0.14 | -0.14 |
| USDCAD=X | 31 | 35.5 | 0.74 | -0.02 |
| EURGBP=X | 38 | 63.2 | 2.35 | +0.04 |
| GBPUSD=X | 26 | 61.5 | 1.87 | +0.05 |
| AUDUSD=X | 16 | 62.5 | 2.67 | +0.05 |
| USDCHF=X | 8 | 100.0 | ∞ | +0.06 |

**Pattern:** ALL 5 JPY-cross pairs are catastrophic (n=484, ~4% WR). ALL non-JPY majors are positive-edge (n=88, ~65% WR). Likely root cause: BoJ tightening 2024-2025 inverted prior LONG-USD-vs-JPY carry bias without strategy update.

## Question to engines

You are a quant researcher reviewing FOREX. The class WR/PF aggregate is misleading — kill the class and you destroy real edge on EURGBP/GBPUSD/AUDUSD/USDCHF. Keep the class as-is and JPY-cross drag continues.

**Your job:** propose 3-5 concrete strategy or gate changes that RESCUE the non-JPY major edge while ELIMINATING the JPY-cross bleed. Return strict JSON ONLY:

```json
{
  "strategies": [
    {
      "name": "<short_identifier>",
      "thesis": "<1-sentence why this works>",
      "signal_construction": "<exact rule>",
      "universe": ["<FOREX symbols>"],
      "expected_pf": <number>,
      "expected_sharpe": <number>,
      "expected_mdd_pct": <number>,
      "differentiation_from_existing": "<how is this different from multi_asset_copytrader>",
      "implementation_hours": <integer>,
      "wire_target": "<file in alpha_engine/ or audit_trail/quality_gates.py>",
      "data_source": "<yfinance / FRED / OANDA / etc.>",
      "fail_mode": "<most likely overfit/decay scenario>"
    }
  ],
  "killers": ["<existing FOREX strategy that should be retired with reason>"],
  "block_proposals": ["<surgical (CLASS, STRATEGY, SYMBOL) triple to add to BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES>"],
  "tier2_attainability_pct": <0-100>,
  "single_most_important_finding": "<one sentence>"
}
```

## Constraints

- MUST propose surgical symbol-level fixes, NOT class-wide block
- MUST handle the JPY carry-regime change root cause (not just block by symbol)
- All signals reproducible with yfinance, FRED (rates differentials), no order-book
- Reject proposals requiring >30 day holding
- Reject `expected_pf` below 1.5 (TIER-2 floor)
- Must propose AT LEAST ONE strategy that uses interest-rate differentials (FRED) — JPY-cross failure is a rate-regime story
