# Cross-system consensus (pump-watch → audit3 translation)

**Date:** 2026-11-23T04:14Z · **Author:** Kilo · Paper only.

## Tool
`tools/cross_system_consensus.py` reads the same live pick files `pump-watch.html` aggregates
(alpha_engine, KIMI, crypto_ml_edge, ml_battleground, rapid_fire, crypto_signal_engine, genome),
normalises `(symbol, direction)` (mapping KIMI's `signal:BUY/SELL`), and reports multi-system agreement.

## Result (local snapshot)
- Systems with live picks: alpha_engine **31**, KIMI **15**, rapid_fire 1, crypto_signal_engine 1;
  crypto_ml_edge / ml_battleground / genome had 0 active rows.
- **Consensus (≥2 systems): 3**
  - **BTCUSDT LONG** ← alpha_engine, kimi
  - **ETHUSDT LONG** ← crypto_signal_engine, kimi
  - **TLT LONG** ← alpha_engine, kimi
- Single-system symbols: 36.

## The caveat that matters (operator Finding 5)
Agreement is **not** a recommendation and **not** evidence of edge. All three consensus names are
**LONG majors/T-bills** — the systems share a long bias, so they agree trivially. This is exactly the
"correlation masquerading as diversification" failure. The tool states this in its output.

## What it is actually useful for
As an **audit3 coverage instrument**: it shows which systems are alive, how many picks each emits, and
where universes overlap — so a reader can see that "3 systems agree" means one long-beta bet, not three
confirmations. Wiring this into an audit3 panel is a display/transparency improvement, not an edge.

*Paper only. Zero investment advice.*
