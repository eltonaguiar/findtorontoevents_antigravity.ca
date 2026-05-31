# Strategy Build Report — FX Carry Trade (LRV 2011)

**Date:** 2026-05-31
**Builder:** peer_claude
**Slug:** `fx_carry`
**Build dir:** `/tmp/strategy_builds_2026-05-31/fx_carry/`

## Academic Source

Lustig, Roussanov, Verdelhan (2011). *Common Risk Factors in Currency Markets*. RFS 24(11).

## Implementation Summary

- **Universe:** 9 G10 crosses vs USD (AUD/CAD/CHF/EUR/GBP/JPY/NOK/NZD/SEK)
- **Signal:** rate differential (FRED 3M interbank series, `IR3TIB01*` family + DGS3MO for USD)
- **Selection:** long top-3, short bottom-3 by carry, equal weight, 5x default leverage
- **Rebalance:** monthly
- **Crisis filter:** 3M realized vol JPY/USD > 6% annualized -> halve leverage
- **Data plumbing:** direct FRED REST (urllib stdlib, no pandas dep) - 0.15s pacing between series, key from `dbpasses.txt`
- **Paper-pilot:** writes JSON to `/tmp/.../paper_picks/fx_carry_paper_picks.json` (NEVER to `ejaguiar1_*` DBs)

## Cursor Statistical Framework

- Wilson LB on WR (95% z=1.96)
- Bonferroni alpha = 0.05/7 = 0.00714
- n_floor = 500 trade-months before live promotion
- Promotion gate in `paper_pilot_harness.stats_summary()` returns `promotable` boolean

## Files Delivered

| File | Lines | Purpose |
|---|---|---|
| `strategy.py` | ~200 | Signal + pick + stats helpers |
| `paper_pilot_harness.py` | ~70 | JSON persistence + stats |
| `tests.py` | ~70 | 10 unit tests |
| `README.md` | ~60 | Rules + citation + gate |
| `ai_consult_grok.txt` | 9 bullets | Crisis-handling consult |

## Tests

```
Ran 10 tests in 0.000s
OK
```

## AI Consult (Grok-4)

Asked Grok about crisis-period handling (JPY/USD vol proxy, threshold tuning, halve-vs-flat, 2nd-axis filters). Verbatim response captured in `ai_consult_grok.txt`. Key insights folded into README v2 plan:

1. Replace JPY/USD vol with G10 FX-vol index when feasible
2. Raise vol threshold from 6% -> 8-10% annualized
3. Dual-threshold: halve at 8%, flat at 12% or RR<-2%
4. Add 25-delta JPY risk-reversal as 2nd-axis skew filter
5. Use 1M realized vol for responsiveness

## Risks / Caveats

- LRV is well-known and crowded; live Sharpe likely 0.4-0.6, not the 0.7-0.9 in-sample
- Negative skew tail risk persists - 2008 saw ~30% MDD on naive carry
- FRED publication lag (1-3 days) for some series - rebalance on T+3 to avoid look-ahead
- G10 FX-vol index not yet wired (Grok recommendation); v1 ships with JPY/USD proxy

## Status

- Build complete: yes
- Tests pass: 10/10
- AI consulted: grok-4-latest
- Production wiring: paper-pilot only (per cursor framework + Wire-Up Rule opt-in sidecar)
