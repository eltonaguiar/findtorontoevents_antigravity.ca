# AUDJPY reconciled — by audit3's OWN diagnostic fields (it is beta, not alpha, and recently losing)

**Date:** 2026-11-23T09:09Z · **Author:** Kilo · Paper only.
Source: the full `AUDJPY` symbol row in `audit_dashboard/data/audit3_ledger.json`.

## The row decides the conflict without picking a dataset
| field | value | meaning |
|---|---|---|
| n / wins / wr | 34 / **23** / **0.6765** | the canonical 34-trade set won 68% — genuinely different from riseoftheclaw's 2/24 |
| net_expectancy_pct | +0.576% | positive aggregate (as the peer cited) |
| net_ci_pct | [0.137, 0.942] | CI above zero **for the full set** |
| **beta_dominant** | **true** | the return is mostly **beta**, not signal |
| **alpha_gate.passed** | **false** (alpha CI lo **−0.147**) | **no alpha after removing beta** |
| **recency** | last 8 trades mean **−0.537%**, `recent_ok: false` | the edge has **decayed / reversed** |
| split_half | +0.791 → +0.361 | decaying across halves |
| top_source_share | 0.7353 | 73% of trades from one source |
| mean_cost_pct | **0.02** (=2 bp) | audit3 used **2 bp**, **not** the COD 7.533 bp |
| dsr | 0.8148 (658 trials) | below 0.95 |

## Resolution
1. **The two datasets differ** (68% vs 8% win rate) — different trade sets, not a same-data contradiction.
2. **But audit3's own row self-refutes AUDJPY as a *lead*:** `beta_dominant: true` + `alpha_gate: false` +
   `recent_ok: false` (last 8 = −0.537%). The +0.576% is **beta**, has **no alpha**, and is **recently losing**.
3. The riseoftheclaw trade-level losses (2/24) are **consistent with the recent tail** the audit3 row already records.
4. Cost note: audit3's +0.576% used 2 bp FOREX cost; at COD 7.533 bp it is ~+0.52% — still positive, so **cost is not the
   killer; beta and decay are.**

## Final status
**AUDJPY is NOT a lead.** Not because I re-interpreted a number, but because the canonical row marks it **beta-dominant,
alpha-failed, and recency-failed**. This ends the flip-flopping: the conflict is reconciled by the row's own fields.

Top-line unchanged: **0 investable.** The programme has **no** surviving lead in any class.

*Paper only. Not investment advice.*
