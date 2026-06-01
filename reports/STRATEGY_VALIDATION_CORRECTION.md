# Strategy Validation Correction — 2026-06-01

## Correction: "PROMISING" labels on 5 candidates were WRONG

Per Claude's independent review: all 5 MC-validated candidates have permutation p > 0.05:

| Candidate | Perm p | Bootstrap CI>0 | Correct Verdict |
|-----------|--------|----------------|-----------------|
| mega_mutation (unnamed) | 0.9984 | Yes | NOT SIGNIFICANT (artifact) |
| cta_golden_cross_200 | 0.2316 | Yes | NOT SIGNIFICANT |
| non_crypto_consensus | 0.5422 | Yes | NOT SIGNIFICANT |
| ig_contrarian_sentiment | 0.9178 | Yes | NOT SIGNIFICANT |
| luxalgo_confluence | 0.9922 | Yes | NOT SIGNIFICANT |

**Bootstrap CI>0 alone is NOT statistical significance.** Permutation p<0.05 is required.
By cursor framework, all 5 fail the significance gate.

## Correction: mega_mutation (unnamed) is a DB artifact

The "strategy" with n=283/426 and strategy='' (empty string) is NOT a coherent strategy.
It's a heterogeneous collection of mislabeled trades grouped by the empty-string key.
This was incorrectly identified as our best candidate.

## Correction: 32 strategies are Layer 1 only

All strategies sit at Layer 1 (IS backtest) of the 8-layer TESTING_PROTOCOL stack.
Layers 2-7 (OOS, walk-forward, Holm-FDR, bootstrap, regime stratification, forward-test, promotion) are all pending.
None are production-ready.

## What this means

- No statistically proven winners exist yet
- The 32 strategy files are legitimate scaffolding for future testing
- §15 dedup (565 simultaneous BTCUSDT LONG picks) must be fixed before honest paper-pilot
- n≥500 gate is non-negotiable before any promotion
