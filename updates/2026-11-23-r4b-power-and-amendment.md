# R4b had no power calculation — 60 months cannot confirm a plausible edge

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, not advice**

## What was broken

The pre-registration specified checkpoints (interim every 12 months, earliest CONFIRM ~60 months)
and justified them with `SE ≈ 10%/√n years`, concluding that a 4.32% standard error arrives at
n ≈ 5.4 years. It never computed the power of the resulting test. Setting SE equal to the hurdle
does not make the hurdle detectable — the interval is still ±1.645 hurdles wide.

## What I added

- `tools/r4b_power.py` — power/MDE/confirm/refute arithmetic for the frozen universe. Reads **only
  the universe's monthly volatility**; it never runs the momentum rule, so it consumes no trial.
- `tests/test_r4b_power.py` — 9 tests, arithmetic-only, offline.
- `reports/r4b_power_2026-11-23.md` — the analysis and the numbers.
- `docs/preregistration/ETF_TREND_FORWARD_2026-11-23_AMENDMENT-1_PROPOSED.md` — **PROPOSED, not in
  force**. I will not amend a frozen rule on my own authority.

## The finding

Book σ = 3.49%/month at ρ=0.5 (12.1%/yr). At n=60 the SE is **45.0 bp/month**, so CONFIRM needs a
point estimate of **110 bp/month (13.2%/yr)**. Power to confirm a 36 bp/month (4.3%/yr) edge:
**5.0%** — indistinguishable from the false-positive rate. Detecting 36 bp/month needs **736
months (61 years)**; 100 bp/month needs 95 months. Refutation works: 60.5% power at a −50 bp/month
edge, 91.6% at −100.

So R4b is a **cheap, independent refutation instrument with a growing point estimate**, not a
confirmation instrument. Its trial-count-1 property is unchanged and still the reason to run it.

## Verification

- `python3 -m pytest tests/test_r4b_power.py -q` → 9 passed; the suite also re-derives the central
  finding (`confirm_threshold > 4× hurdle`, `power_confirm(36 bp) < 0.20`) so the tool, not just the
  report, asserts it.
- Sensitivity: the conclusion holds at ρ = 0.3, 0.5 and 0.7.
- `python3 tools/r4b_power.py` reproduces every number in the report.

## What this does not fix

It does not make the clock able to confirm a realistic edge — no amendment can, at monthly sampling.
It does not resolve the equity cost dispute (12.0749 vs 1–5 bp), the delisting-aware universe, or the
venue fee tier. It changes no threshold: the republished picks keep their verdicts, with the
"60 months then a verdict" expectation withdrawn.
