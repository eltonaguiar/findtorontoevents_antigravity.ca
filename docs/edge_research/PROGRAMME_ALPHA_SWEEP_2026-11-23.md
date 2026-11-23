# THE definitive finding: the canonical surface has ZERO alpha

**Date:** 2026-11-23T09:14Z · **Author:** Kilo · Paper only.
Source: `audit_dashboard/data/audit3_ledger.json` (canonical). Machine: `reports/programme_alpha_sweep.json`.

## Result — read straight from the ledger's own alpha gate
| measure | value |
|---|---|
| symbols with `beta_dominant: true` | **69 / 69** |
| symbols passing `alpha_gate` | **0 / 69** |
| cells (asset×strategy×direction) passing `alpha_gate` | **0 / 362** |
| range of `alpha_ci_lo` across all 362 cells | **−6.885 … −0.1442** |
| cells with `alpha_ci_lo > −0.10` | **0 / 361** |
| median `alpha_ci_lo` | **−0.9446** |

## What it means (no reinterpretation, no dataset choice)
The canonical ledger computes, for every cell, a confidence interval on **alpha after removing beta**. Across the entire
surface — 362 cells, 69 symbols — **not one** has an alpha-CI lower bound above **−14.4%**; the median is **−94%**.
Every symbol is flagged **beta-dominant**.

So the honest, final statement is not "it's expensive" or "n is small" or "my table vs the peer's table". It is:

> **The programme's own canonical alpha gate rejects 100% of the surface (0/69 symbols, 0/362 cells), and the best
> alpha lower bound anywhere is −14.4%. There is zero demonstrated alpha in this estate.**

That is why nothing is investable, and it supersedes every per-class net figure — the returns that look positive are
**beta**, which a low-cost index ETF delivers more cheaply.

## Consequence
- This is the cleanest possible answer to "find something worth investing in": the canonical engine has already
  evaluated every candidate against an alpha gate and found none.
- Any future claim of an edge must show **`alpha_gate.passed: true`** on a canonical cell — a single, checkable criterion.
  My CI invariant (`tools/assert_no_investable.py`) can be extended to assert `alpha_gate` too.

*Paper only. Not investment advice.*

---

## Refinement 2026-11-23T09:17Z — the alpha gate is CLASS-level (not per-cell)
Checking the distinct values showed `alpha_ci_lo` takes only 1–2 unique values **per asset class** — the gate is computed
at the class level, applied to every cell in that class. The clean per-class verdict:

| class | cells | best `alpha_ci_lo` | passed |
|---|---:|---:|---:|
| **FOREX** | 23 | **−0.1442** | 0 |
| ETF | 36 | −0.3088 | 0 |
| EQUITY | 53 | −0.3614 | 0 |
| BOND | 12 | −0.4305 | 0 |
| CRYPTO | 229 | −0.9446 | 0 |
| COMMODITY | 8 | −5.5118 | 0 |
| FUTURES | 1 | (n/a) | 0 |

**No class passes alpha.** FOREX is closest and still **−14.4%** short — i.e. it would need ~14.4% more beta-adjusted alpha,
or far more independent observations, before its alpha CI could reach zero. The earlier "closest cell needs +14.4%" is
restated correctly as **"closest class (FOREX) needs +14.4%"**, since the gate is class-scoped.

The conclusion is unchanged and cleaner: **zero classes have positive alpha; the programme's own gate rejects the whole
surface at the class level.**
