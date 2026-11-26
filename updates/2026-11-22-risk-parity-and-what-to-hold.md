# Portfolio construction measured, every "beats 60/40" claim withdrawn, VT caveat added

**Date:** 2026-11-22 · **Type:** new measurement + two bugs caught in the new tool + one
correction to an earlier claim of mine
**Files:** `tools/risk_parity_vs_6040.py` (new), `tests/test_risk_parity_vs_6040.py` (new, 7
passing), `reports/portfolio/risk_parity_2026-11-22.json` (new),
`reports/2026-11-22-portfolio-construction.md` (new), `reports/2026-11-22-data-bias-register.md`
(new, item C21), `reports/2026-11-22-retrospective.md` (new, item H50),
`plans/2026-11-22-50-action-items.md` (status log)

## What was missing

With 0 of 40 per-class cells clearing every gate, the only remaining lever needing no new alpha is
how the same assets are weighted. Items E31/E33/E34 (risk parity, HRP, combined book) had no
measurement at all, and E35 ("what to actually hold") had no evidence behind it.

## What changed

1. **`tools/risk_parity_vs_6040.py`** compares 60/40, equal-weight, inverse-vol RP, ERC, HRP and
   each of those plus a 10% vol target on one window (249 months, 2006-03 → 2026-11), one cost
   model and one CE definition (excess over `^IRX`, risk aversion 1).
2. **Every "beats 60/40" claim is gated on a paired bootstrap** of the CE *difference* (5,000
   month-resamples, 90% CI, both CEs restated on the common window). Result: **0 of 5 variants
   exclude zero.** The JSON `verdict.beats_6040_after_cost` reads from the CI, not the point
   estimate, and a test enforces it.
3. **E34 answered with the trap named:** the long-only max-CE solve zeroes **TLT**
   (corr to SPY **−0.079**) — error maximisation in mean returns, not a diversification finding.
   The honest combined book is risk-allocated, and the failed per-class sleeves earn zero under
   every method.
4. **C21 published:** a per-class data-bias register naming the defect, its evidence and its
   direction for all 12 classes, plus the rule that a KILL on flattered data is conservative while
   a survivor is `UNSAFE`.
5. **H50 published:** retrospective with the five rules this round earns.

## Correction to my own earlier claim

I reported vol targeting as real risk control (MDD **−22.37 vs −31.42**, daily, 2005→2026). At
monthly granularity the CE gain survives (**+0.75 pp**, CI includes 0) but the **drawdown benefit
reverses (−33.72 vs −28.45)**: 2006-07 realised vol was ~7%, so a 10% target levers ~1.4× *into*
2008. Corrected statement: **the return benefit is granularity-robust; the drawdown benefit is
not**, and the rebalance frequency must travel with the number.

## Bugs caught in the new tool, both on first execution

- **Bootstrap window mismatch.** The table computed each series' CE over its own span (ERC has a
  24-month burn-in, HRP 36), while the bootstrap ran on the overlap. That turned a **+0.57 pp**
  advantage into a **−1.91 pp** bootstrap mean — the headline was measured on months the bootstrap
  never saw. Fixed by restating both CEs on the common window inside the bootstrap.
- **A test that encoded a false economic claim.** Asserting "a negative-excess asset gets zero
  weight" is only a theorem when the asset is *uncorrelated*; with correlation < 1 a
  negative-return asset can legitimately be held as a hedge. The test now uses a diagonal
  covariance, where the claim is unambiguous, rather than weakening the threshold.

## Verification

- `python3 tools/risk_parity_vs_6040.py` → `RC=0`; 10 strategies, 5 bootstrap comparisons, **all
  CIs include zero**.
- `python3 -m pytest tests/test_risk_parity_vs_6040.py tests/test_dsr_multiplicity_sensitivity.py`
  → **12 passed**.
- Correlation matrix printed from the same run: SPY/TLT −0.079, SPY/GLD +0.103, SPY/DBC +0.448,
  TLT/DBC −0.318, TLT/GLD +0.241, GLD/DBC +0.314.
