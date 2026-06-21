# Crypto edge-hunt at FULL SCALE (honest replay, read-only) — 2026-06-20
**Author:** claude-opus · honest first-touch (SL-wins-ties) on EXISTING crypto_ohlcv 1h, net@16bp, stored TP/SL · no DB mutation

## What & why
The coverage finding said only ~1,261 crypto picks were honestly resolved. But the crypto pick book (trading_picks, stored TP/SL) spans only 2026-02→06 — INSIDE crypto_ohlcv's existing ~181d window. So I replayed **14,335** of them honestly in-memory (top-40 symbols = 84% of the book) — a 11× larger honest sample — to answer: at full coverage, does ANY crypto strategy clear the bar?

## Result — NO production crypto strategy clears the bar (DEFINITIVE)
Overall n=14,335. Per-strategy honest net@16bp PF + cluster-bootstrap CI-LB (symbol-day):
| strategy | n | WR | net PF | CI-LB | n_eff | verdict |
|---|---|---|---|---|---|---|
| prediction_market_consensus | 3218 | 38.3% | **0.07** | 0.02 | 385 | catastrophic loss |
| luxalgo_confluence | 2452 | 39.6% | 0.93 | 0.85 | 1090 | losing |
| short_dominant_engine | 1036 | 41.7% | 0.94 | 0.83 | 497 | losing |
| cg_whale_divergence | 220 | 70.5% | 3.53 | 2.05 | **51** | **ARTIFACT (below)** |
| pm_whale / copy_pm_* | 100-650 | — | 0.3-1.7 | <0.95 | <60 | sub-bar + low n_eff |

The high-n workhorses are honestly **losing or breakeven**. No strategy meets CI-LB>1.15 @ n_eff≥80.

## cg_whale_divergence — false lead, DEBUNKED
CI-LB 2.05 looked promotable but is a **4-day concentration artifact**: 129/220 picks (59%) from May 19-22 2026; 60% of gross wins from 3 days; OOS PF 12.14 = single-cluster outlier; n_eff=51<80. Mostly SHORT (168/220) winning together in a market-wide selloff. NOT generalizable.

## Implications (honesty update)
1. **The crypto strategy book has no promotable edge at scale** — money-protecting truth, now measured at 11× the prior sample, not assumed.
2. **The OHLCV backfill lever is DOWNGRADED.** The resolvable picks (already in coverage) show no edge, and the book doesn't predate the coverage window — so deeper history adds few resolvable picks and won't rescue these strategies. The backfill retains narrower value (the rsi5070_us *overlay* subset, which selects by RSI condition and isn't tested here; + fair multi-regime funding/cointegration re-tests) but is NOT the program-saving unlock it appeared.
3. **The real bottleneck is edge, not just coverage** — at least for the existing crypto book. New mechanisms (not the current strategies) or non-crypto classes are where any edge must come from.

## Caveat
This tests the production strategies' stored TP/SL. It does NOT test the rsi5070_us entry-condition overlay (a filter on a pick subset) — that remains the sole honest lead (CI-LB 0.95, n-gated). Tail symbols (363, 16% of book) untested but unlikely to hold a generalizable class edge.
