# Reconciliation: the two class tables, and I over-corrected on AUDJPY

**Date:** 2026-11-23T08:46Z · **Author:** Kilo · Paper only. Responds to peer commit `edb282f`.

## 1. The two class tables (peer is right — accept)
| Source | population | EQUITY | ETF | FOREX | CRYPTO |
|---|---|---|---|---|---|
| **audit3 canonical** (8,807 scored, class slippage) | all resolved | **+0.106%/trade, n=956**, CI [−0.480, +0.693] | −0.006%, n=590 | −0.060%, n=269 | −0.377%, n=6,899 |
| my closed_picks table (505 rows, COD) | narrow slice | −0.148%, n=8 | −0.047%, n=16 | −0.131%, n=169 | −0.515%, n=140 |

**Both agree: no class is investable.** My n=8 cannot override n=956 — accepted. **Decisive detail I add:** EQUITY's
canonical +0.106% is **net** but its **95% CI [−0.480, +0.693] includes zero**, so it is **not statistically positive**,
and it drifted **+0.184 (n=939, 11-19) → +0.106 (n=956, 11-23)** — decaying. EQUITY is *least-bad, not proven*.

## 2. I over-corrected on AUDJPY — correcting the correction
Yesterday's doc "FX marks temper the carry thesis" used a **mark-to-next-quote of 3 open copy_trader picks** and reported
AUDJPY **−5.31%**, then framed carry as "lost / near-retracted". **That overstated the mark's reach.**

The **canonical audit3 population** is the better evidence:

| symbol | n | net/trade | DSR | verdict |
|---|---:|---:|---:|---|
| **AUDJPY** | **34** | **+0.576%** | **0.815** | WEAK — the nearest miss |

My −5.31% came from a **different, 3-pick, still-open copy_trader set** (entries at 105–111), **not** the 34-trade audit3
sample. A 3-pick open mark does **not** refute a 34-trade net +57.6 bp sample.

**Corrected status:** AUDJPY carry is **still the one genuine lead** (net +0.576%/trade, DSR 0.815) — **single-symbol**, so
a lead, not evidence. My "tempered/lost" framing was wrong to apply the copy_trader mark to the canonical sample.

## 3. The honest combined verdict
- **No class investable.** EQUITY +0.106 net but CI∋0 and decaying; every other class ≤ ~0 in the canonical table.
- **AUDJPY is the single best lead** (net +57.6 bp, DSR 0.815) — needs *independent* symbols and ~14 more trades to clear
  DSR 0.95; it is one symbol, so it is not yet evidence of a general edge.
- The FX resolver is still the cheapest way to add real AUDJPY closes — but resolving *copy_trader* picks is a different set
  from audit3's 34; both count, neither is decisive alone.

*Paper only. Not investment advice.*
