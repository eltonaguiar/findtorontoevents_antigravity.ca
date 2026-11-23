# Per-class evidence rows — and only 2 of 11 have a measured net edge

**Date:** 2026-11-23
**Tool:** `tools/per_class_evidence.py` · **Artifact:** `reports/per_class_evidence.json`

## The table

| Class | Row | n | basis | net bp/yr | clears 432bp | verdict |
|---|---|---|---|---|---|---|
| EQUITY | R1 HML long/short | **44** | monthly rebalances | **2.1** | no | KILL |
| CRYPTO | R2b funding/carry | **4,235** | 8h funding intervals | **306.7** | no | DEAD |
| CRYPTO | R2 directional | 728 | trades | **null** | – | DEAD |
| FOREX | R6 momentum | 53 | trades | **null** | – | DEAD |
| COMMODITY | R7 trend | 28 | trades | **null** | – | DEAD |
| BOND | R3 govt/credit | 8 | trades | **null** | – | UNKNOWN |
| ETF | R4 / R4b | 24 | symbols (risk only) | **null** | – | CANDIDATE |
| PREDICTION_MARKETS | – | 0 | none | null | – | UNKNOWN |
| MUTUAL_FUNDS | – | 0 | none | null | – | UNKNOWN |
| OPTIONS | – | 0 | none | null | – | UNKNOWN |
| PRIVATE_CREDIT | – | 0 | none | null | – | UNKNOWN |

**10 classes covered, 11 rows, 2 with a measured net bp, 0 clearing the 432bp hurdle.**

## The distinction the table exists to enforce

Five rows have a documented win-rate or profit factor but **no measured net-of-cost
basis-point figure**, and the tool writes `null` with the reason rather than `0`. A PF of
0.31 is a disappointment; "no net bp measured" is an absence of evidence. Rendering both
as 0 would be the same class of error as every other defect found this week — a number
that looks present but is not.

`net_bp_basis` is declared per row (`per_year` here) because a yield and a per-trade edge
are different quantities and mixing them silently makes the table meaningless.

## What it means for the ranked list

Only two classes can be ranked on measurements at all, and both fail:

- EQUITY/HML: +2.1 bp/yr vs 432 bp needed.
- CRYPTO/carry: +306.7 bp/yr vs 432 bp needed.

Everything else is ranked on *risk characteristics and documented PF*, not on a measured
edge — and the ranked-list draft already says so. The #1 position (ETF) rests on measured
Sharpe 0.44 and measured 1–2 bp cost, with **no strategy test yet**; that is stated in the
row rather than papered over.

Zero capital sanctioned. Not investment advice.
