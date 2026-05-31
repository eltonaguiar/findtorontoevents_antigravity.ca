# EQUITY Candidate Refuted — Wilson Lower-Bound Correction

**Date:** 2026-05-31 (correction posted as 2026-06-01 EST update)
**Author:** claude-opus-4-7 (peer)
**Related PRs:** #304 (initial "close candidate" framing), #306 (Wilson LB independent recompute)
**Subject strategies:**
- CRYPTO `volatility_breakout` (WR 61.2%, n=85) — *borderline survives*
- EQUITY `stocks_rsi2_pullback` (WR 59%, n=39) — **REFUTED**

---

## TL;DR

PR #304 surfaced two strategies as "close candidates" for promotion based on raw
win rate alone. PR #306 independently computed the Wilson 95% lower-bound for
each. **Only CRYPTO `volatility_breakout` clears the LB > 0.50 threshold (LB =
0.5057). EQUITY `stocks_rsi2_pullback` does NOT (LB = 0.4344).** The 59% WR on
n=39 is **not statistically distinguishable from random noise** at 95%
confidence.

This is the 7th fabrication-class error caught today and the first one
originating from my own narrative — same verbatim+RT (red-team) discipline got
applied to it, and it should have been from the start.

---

## Wilson 95% Lower-Bound Formula

For a binomial proportion `p̂ = wins/n` with sample size `n`, the Wilson score
lower bound at confidence `1 − α` is:

```
              p̂ + z²/(2n) − z · sqrt( p̂(1−p̂)/n + z²/(4n²) )
    LB =    ─────────────────────────────────────────────────
                            1 + z²/n
```

where `z = 1.96` for 95% confidence.

---

## EQUITY stocks_rsi2_pullback — REFUTED

```
n  = 39
w  = 23
p̂  = 23 / 39 = 0.5897   (≈ 59%)
z  = 1.96
z² = 3.8416

Numerator   = 0.5897 + 3.8416/78 − 1.96 · sqrt(0.5897 · 0.4103 / 39 + 3.8416 / 6084)
            = 0.5897 + 0.04925   − 1.96 · sqrt(0.006204 + 0.000632)
            = 0.6389              − 1.96 · sqrt(0.006836)
            = 0.6389              − 1.96 · 0.08268
            = 0.6389              − 0.16205
            = 0.4769

Denominator = 1 + 3.8416 / 39 = 1.0985

LB          = 0.4769 / 1.0985 ≈ 0.4341
```

Independent recompute in PR #306: **LB ≈ 0.4344** (matches within rounding).

**LB 0.4344 < 0.50 → cannot reject H₀ that true WR ≤ 50% at 95% confidence.**
At n=39 the 95% interval is roughly `[0.43, 0.73]` — way too wide to claim
edge.

---

## CRYPTO volatility_breakout — BORDERLINE (survives)

```
n  = 85
w  = 52
p̂  = 52 / 85 = 0.6118   (≈ 61.2%)
z  = 1.96

(same algebra)
LB ≈ 0.5057
```

`LB ≈ 0.5057 > 0.50` — *barely* clears, single notch above random. Not strong
enough to size up; appropriate action is **continued tracking, not priority
shadow-pilot until n ≥ 100 or LB ≥ 0.55**.

---

## How much more data does EQUITY need?

If true WR holds at 0.59, the LB clears 0.50 at roughly:

```
solve for n such that:
   0.59 − 1.96 · sqrt(0.59 · 0.41 / n)  ≥ 0.50    (Wald approximation, suffices here)
   1.96 · sqrt(0.2419 / n)              ≤ 0.09
   sqrt(0.2419 / n)                     ≤ 0.0459
   0.2419 / n                           ≤ 0.002106
   n                                    ≥ 0.2419 / 0.002106 ≈ 114.8
```

Wilson exact form pushes this a bit higher (~125-140 typically). So roughly
**n ≈ 120-140 needed**, i.e. **80-100 more closed samples** at the current WR
to reach a *testable* state. At a more conservative assumed true WR of 0.55,
the required n balloons past 350.

**Conclusion:** `stocks_rsi2_pullback` is not yet a candidate. It needs ~80-100
more closed trades just to **test** whether there is any edge — and that's
before any promotion gate.

---

## NO_EDGE chain (unchanged at 8)

This correction does not remove any source from the NO_EDGE chain — it removes
EQUITY `stocks_rsi2_pullback` from the *candidate* list. The 8 NO_EDGE sources
stand; CRYPTO `volatility_breakout` is the only LB-borderline strategy under
continued tracking.

---

## BUILD swarm w2cgju6i9 — unaffected

The 7 fresh academic strategies being built from scratch via the Cursor
framework (BUILD swarm w2cgju6i9) are independent academic implementations,
not statistical promotions of existing strategies. This correction does not
change that work.

---

## Discipline pattern reinforced

| # | Source | Claim | Status |
|---|--------|-------|--------|
| 1-6 | (earlier today) | various external/peer claims | red-teamed and verified or rejected |
| **7** | **My own PR #304 narrative** | **"two close candidates"** | **REFUTED — applied verbatim+RT to my own output** |

The same discipline that catches outside fabrications now catches my own
optimistic framing. That is the intended steady state.

---

## Recommended next actions

1. Track CRYPTO `volatility_breakout` as **borderline-only** — no shadow-pilot
   prioritization yet.
2. Surface `stocks_rsi2_pullback` as **NOT_A_CANDIDATE_INSUFFICIENT_N** on
   `/audit/pick_funnel.html`, with current n=39 / LB=0.4344 / required n≈125.
3. Apply Wilson LB pre-check to **every** "close candidate" surfaced in any
   future audit — promote-by-WR-alone is banned.

— claude-opus-4-7
