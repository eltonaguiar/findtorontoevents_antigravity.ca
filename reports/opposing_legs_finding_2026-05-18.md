# Finding — Opposing-Direction Picks in the Active Crypto Book (2026-05-18)

Surfaced by the Ling 2.6 consult (`reports/ling_crypto_consult_2026-05-18.md`),
verified against `alpha_engine/data/active_picks.json`.

## What was found

The active crypto book holds **delta-cancelling pairs**: the same symbol
carries both LONG and SHORT picks at near-identical entry prices, emitted
independently by different strategies with no book-level coordination.

**5 of 30 distinct crypto symbols (17%) are conflicted:**

| symbol | picks | pattern |
|--------|-------|---------|
| BTCUSDT | 5 | 4 LONG + 1 SELL, entries 78090-78432 (0.4% spread) |
| ETHUSDT | 3 | 1 LONG + 2 SHORT, entries 2179-2194 |
| DOGEUSDT | 3 | 1 LONG + 2 SHORT, entries 0.1103-0.1116 |
| BNBUSDT | 2 | 1 LONG + 1 SHORT, entries 654.88 / 655.10 |
| XRPUSDT | 2 | 1 LONG + 1 SHORT, entries 1.4188 / 1.4242 |

Consistent emitter pattern: `ml_enhanced_<SYM>` emits a LONG at
`confidence=0.50`; `prediction_market_consensus` emits a SHORT at
`confidence~0.68-0.79` at a near-identical entry. BTCUSDT additionally has
`inverse_ml_enhanced_BTCUSDT_15m_D` SELL stacked against `ml_enhanced` LONGs.

## Why it matters

Holding both sides of the same instrument at the same entry is not a hedge —
it is two strategies independently disagreeing with no arbiter. The
guaranteed outcome: one leg loses, both legs pay fees + half-spread, net
directional alpha is ~0 minus cost. Ling's phrasing: "a multiple-hypothesis
garden — no ex-ante edge, just multiplicity." It mechanically contributes to
the CRYPTO ~44.6% WR / PF ~1.25.

## Root cause

There is **no book-level same-symbol direction-conflict gate.** The
`opposing` logic in `audit_trail/quality_gates.py:3006` is timeframe-level
(within one pick's multi-TF analysis) — it does NOT look across the active
book for the same symbol carrying opposite directions. Each emitter passes
its own gate in isolation; nothing reconciles them.

## Recommended fix (not yet built — operator decision)

A book-level conflict reconciler, applied after pick generation:
- When a symbol has opposing-direction active picks, keep only the side with
  the higher aggregate conviction (or block both if conviction is within a
  tie band — conflict = no edge).
- Env-gated, shadow-first (this is production pick-path logic).
- Acceptance: 0 opposing-direction symbol pairs in the active book after the
  gate; no change to single-direction symbols.

This is hygiene, not edge — it removes self-defeating book construction. It
does not change the EDGE_HUNT_CONCLUSION verdict (no admissible edge); it
stops the book from paying costs to take both sides of a non-edge.
