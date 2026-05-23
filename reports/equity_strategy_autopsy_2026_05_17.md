# EQUITY Strategy Autopsy — 2026-05-17

## Summary

`multi_asset_copytrader` EQUITY resolved picks (n=39) show per-symbol divergence:
strong performance on NVDA/RIOT but negative on AMD/NIO. Sample sizes are too small
for statistical blocking (AMD n=12, NIO n=4) but document a pattern worth monitoring.

## Data (from closed_picks.json, 2026-05-17T19:15Z)

### multi_asset_copytrader EQUITY by symbol:

| Symbol | n | WR | avg_pnl |
|--------|---|----|---------|
| RIOT | 14 | 50% | +1.00% |
| AMD | 12 | 8% | -2.33% |
| NVDA | 5 | 80% | +3.40% |
| NIO | 4 | 0% | -6.90% |
| AVGO | 2 | 0% | -3.00% |
| PFE | 1 | 100% | +4.13% |
| CVX | 1 | 0% | -3.00% |

### Overall EQUITY by strategy:

| Strategy | n | WR | avg_pnl |
|----------|---|----|---------|
| multi_asset_copytrader | 39 | 33% | -0.76% |
| ? (unknown) | 3 | 67% | -0.07% |
| auto_dna_mutation | 1 | 0% | -2.03% |
| copy_trader_intel | 1 | 100% | +3.50% |

## Key Observations

1. **AMD is the primary drag**: n=12, WR=8%, avg=-2.33%. Most resolved picks with bad results.
   - NOT blockable yet: MIN_N_STRATEGY=20 for statistical gates; n=12 is below floor.
   - Action when n≥20: reassess AMD blocking.

2. **NVDA shows promise**: n=5, WR=80%, avg=+3.40%. Too small to confirm (n<20).

3. **NIO is terrible**: n=4, WR=0%, avg=-6.90% (worst single-trade losses -7% range).
   - Also too small for blocking.

4. **No EQUITY strategy passes DSR/SPA gates** because n<20 for any single strategy.
   - money_ready_verdict() uses dashboard_fallback (n=238, WR=54.2%) but SPA=0.

## EQUITY Path to MONEY_READY

Unlike COMMODITY (where CT=F has n=231 and is clearly the edge), EQUITY needs
accumulation across strategies. Fastest paths:

1. **Multi_asset_copytrader needs AMD/NIO picks to resolve badly OR symbol-level 
   blocking of AMD/NIO** — reduces drag, improves WR. Needs n≥20 for AMD first.
2. **Second EQUITY strategy with n≥20** — `connors_rsi2_scanner` (shadow mode)
   or `stocks_rsi2_pullback_wide/tight` accumulation.

## Comparison to COMMODITY Pattern

COMMODITY: CT=F WR=86% (231 picks), non-CT=F WR=12% (123 picks) — clear split
EQUITY: NVDA WR=80% (5 picks), AMD WR=8% (12 picks) — suggestive split, too small

The COMMODITY autopsy was actionable (cta_replicator n=83, safe to block).
The EQUITY autopsy is monitoring-only (all non-NVDA samples n<20).

## Generated

2026-05-17T19:15Z — Session BC
