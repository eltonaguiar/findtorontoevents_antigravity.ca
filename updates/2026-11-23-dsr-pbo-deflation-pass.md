# DSR + PBO pass — the flattering cross-class results are best-of-N flukes

**Date:** 2026-11-23
**Tool:** `tools/quant_metrics_dsr_pbo.py` · **Artifact:** `reports/quant_metrics_dsr_pbo.json`

---

## What was deflated

Block 2 produced six "top picks" (best in-sample Sharpe out of 15 configs each) with
OOS numbers that looked like edges: EQUITY +34%/yr, ETF +16%/yr. This block tests whether
any of that survives selection.

Thresholds fixed in advance: **DSR > 0.95**, **PBO < 0.50**, both required.

## Pass 1 — per-class deflation, N = 15 (the grid within one class)

| Class | Pick | Sharpe ann. | SR\* ann. | DSR | PBO | Survives both |
|---|---|---|---|---|---|---|
| BOND | L21_H10 | −0.19 | 0.44 | 0.0797 | 0.614 | no |
| COMMODITY | L252_H5 | 0.94 | 0.17 | **0.9517** | 0.586 | no |
| CRYPTO | L252_H10 | 0.63 | 0.24 | 0.8563 | 0.771 | no |
| EQUITY | L252_H21 | 0.72 | 0.20 | 0.8822 | 0.600 | no |
| **ETF** | L189_H21 | 1.05 | 0.30 | **0.9543** | **0.443** | **YES** |
| FOREX | L21_H10 | 0.21 | 0.27 | 0.4481 | 0.729 | no |

EQUITY's headline OOS 34%/yr collapses to **DSR 0.882 — fail**. That is the deflation
doing its job: the number was a product of picking the best of 15 configs on one name.

## Pass 2 — programme level, N = 90 (the honest count) — **this is the one that governs**

Each class was deflated at N=15. But the ranked-pick question *"which class is best"* was
answered by searching **six classes × 15 configs = 90 configurations**. Deflating at 15
while having searched 90 is precisely the multiple-testing error the rest of this
programme has spent the week fighting.

| | |
|---|---|
| Pooled trials | **90** |
| σ_SR pooled | 0.031848 |
| **SR\* (expected max under the null)** | **1.259 annualised** |

**ETF's observed Sharpe is 1.05 — BELOW the 1.259 that the best of 90 coin flips is
expected to show.**

| Class | DSR at N=15 | DSR at N=90 | Verdict at N=90 |
|---|---|---|---|
| BOND | 0.0797 | 0.0006 | fail |
| COMMODITY | 0.9517 | 0.2423 | fail |
| CRYPTO | 0.8563 | 0.0423 | fail |
| EQUITY | 0.8822 | 0.1139 | fail |
| **ETF** | **0.9543** | **0.3191** | **fail** |
| FOREX | 0.4481 | 0.0085 | fail |

**0 of 6 classes survive deflation at the honest trial count.**

## The single most useful sentence in this block

> Under the null, the best of 90 trials is expected to show a Sharpe of **1.259**. The best
> we found is **1.05**. Our "edge" is *worse than what pure noise would be expected to
> produce* at this search width.

That is not a disappointment; it is a clean, quantitative answer to "is there an edge in
the cross-class momentum family as tested" — **no**, and here is the number that says so.

## Limits of this block, stated

- Still one instrument per class (n=1), so PBO is computed over the config grid, not over
  instruments. A proper PBO needs a cross-section of instruments *and* configs.
- PBO assumes the blocks are exchangeable; contiguous time blocks in a trending market
  are not perfectly so.
- The ETF row used a conservative 4.97 bp cost when ETF execution measures 1–2 bp; making
  cost more favourable cannot rescue a DSR of 0.32.
- A DSR at N=15 passing for ETF/COMMODITY is retained in the artifact, because dropping a
  result that passed a weaker test would itself be selective reporting.

## Effect on the ranked list

The ranking of classes by *measured risk* (ETF #1) stands — that is a risk statement, not
an edge claim. What this block removes is any suggestion that the cross-class momentum rule
constitutes a tradable edge in any class. **0/6.** Combined with HML (KILL) and crypto
carry (DEAD), the programme's tally of proven edges remains **0**.

Zero capital sanctioned. Not investment advice.
