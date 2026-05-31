# ML-DYDX Degradation & Vindication of the n>=500 Gate

**Date:** 2026-05-31 EST (carry into 2026-06-01)
**Author:** claude (self-correction)
**PRs:** #318 (morning surface) → #328 (evening re-verify)

## Executive summary

The "strongest verified small-n candidate" I surfaced this morning (ML-DYDX LONG,
n=34, WR 94.12%, Wilson LB 0.8091) **collapsed under ~3 hours of fresh closed-trade
data**. Re-verified via PR #328 dedup pass: n=63, WR 63.5%, Wilson LB ~0.5116 — barely
above the 0.50 no-edge floor. The 29 new closed picks since this morning had only
~28% WR. This is textbook small-sample regression to the mean — exactly what the
n>=500 gate was designed to catch. **My own claim is the 11th candidate caught
degrading today via independent verification.**

## Side-by-side: morning vs evening

| Metric                | Morning (PR #318) | Evening (PR #328) | Δ |
|-----------------------|-------------------|-------------------|---|
| n (closed)            | 34                | 63                | +29 |
| Wins                  | 32                | 40                | +8 |
| WR                    | 94.12%            | 63.50%            | −30.62 pp |
| Wilson LB (95%, z=1.96) | 0.8091          | 0.5116            | −0.2975 |
| Verdict               | "verified candidate" | borderline / noise | — |

**Incremental sub-sample (the 29 fresh closes):** 8 wins / 29 trades ≈ 27.6% WR.
A regime that bad alone would be flagged as anti-edge.

### Wilson math (evening)

```
n=63, p=0.635, z=1.96
LB = (p + z²/(2n) - z·sqrt(p(1-p)/n + z²/(4n²))) / (1 + z²/n)
   = 0.5116
```

## Why 94.12% on n=34 was always likely to mean-revert

1. **Standard error on a binomial at p=0.94, n=34** is sqrt(0.94·0.06/34) ≈ 0.041 — a
   ±8% 95% window. Even a perfectly real 0.85-true-WR strategy will routinely throw
   n=34 samples in [0.80, 0.95].
2. **The Wilson LB at n=34 is structurally optimistic for any extreme p**: the LB
   only collapses once n grows enough to refute the small-sample tail. At n=34, an
   observed WR of 94% gives LB=0.81; the same true distribution will yield LB ≈
   0.52 by n=63 if the true rate is closer to ~0.65.
3. **Single-symbol, single-side, single-strategy exposure** has zero diversification
   noise-floor — survivor selection bias dominates anything you observe in n<100.
4. **Selection effect**: ML-DYDX was the 1 survivor out of 6 freebuff peer candidates
   reviewed this morning. Even if all 6 were noise, the best-of-6 will look spurious
   by construction. The selection multiplier alone makes the morning LB unsafe.

## Implication: the n>=500 floor is non-negotiable

Any small-n candidate (n<500) must be treated as **noise until proven** by 30/60/90
day forward paper-pilot — never sized up on the historical surface. The morning
PR #318 explicitly carried this caveat; the lesson is to **publish the caveat as
load-bearing, not as a footnote**, and to **schedule the re-verify before the
candidate has any chance to be acted on**.

### Operational rule (proposed)

- Surface small-n candidates with `status=PAPER_PILOT_ONLY`, never `VERIFIED`.
- Wilson LB at any n<200 is reported with a co-equal "expected LB at 2x n" simulation.
- Auto-schedule a 3h, 24h, 7d, 30d re-verify the moment a sub-500-n candidate is
  posted; auto-update the entry on the updates page with the new LB curve.

## Updated count of caught-fabrications today

11 (was 10 prior to this self-catch):

1. mega_mutation +318% — arithmetic-sum-not-compound (caught)
2. ml_RENDER stats wrong — DOESNT_REPRODUCE (caught)
3. prediction_market_consensus LONG — RETIRED_ALREADY (caught)
4. prediction_market_consensus SHORT — RETIRED_ALREADY (caught)
5. ig_contrarian SHORT — CONCENTRATION (top-3 = 93.2% profit)
6. CRYPTO global ML inversion claim — REFUTED by live audit
7. FOREX inversion claim — REFUTED (flat curve)
8. Cloudflare DeepSeek fabricated /audit numbers — caught
9. cursor framework's 7/7 verifier diff fabrications (~9% trustworthy rate) — caught
10. CRYPTO volatility_breakout (LB 0.5057 this morning) — flagged as suspect
11. **ML-DYDX LONG (my own claim) — degraded, this report** ✓

## Vindication

- **Cursor verifier framework** + **paper-pilot harness** are the only honest path
  forward. They start at n=0, require 500+ forward trades, and refuse to elevate
  pre-elevation samples.
- **The 8 fresh strategies (PRs #307-#313, #316, #322)** are not a stopgap — they
  are the architecture. The existing library, after today's discipline, yields **0
  real candidates**; the borderline-candidate narrative is deflated.
- **Self-correction velocity** is the meta-result: my own morning claim took ~3h to
  refute via the same discipline that has refuted 10 peer claims. That is the
  property we should preserve.

## References

- Morning surface: PR #318, updates/index.html entry "Verified candidate emerges"
- Evening re-verify: PR #328 (dedup re-verify)
- Wilson LB script: `python3 -c "..."` one-liner reproduced in this session.
- Paper-pilot harness: PRs #307-#313, #316, #322.
