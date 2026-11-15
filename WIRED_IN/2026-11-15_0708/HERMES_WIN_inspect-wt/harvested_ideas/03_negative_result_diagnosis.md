# Negative Result Diagnosis — Candidate Failure Classification

**Date:** 2026-11-15
**Audit ID:** WIRED_IN/2026-11-15_0708/HERMES_WIN_inspect-wt
**Decision owner:** Quant governance (Elton / Hermes)

---

## 1. Decision Rule (pre-registered)

- **DEAD** — fails any of: shuffle control, walk-forward stability, temporal discipline, reproducibility.
- **NEAR-MISS** — passes temporal, shuffle, walk-forward and friction, but fails significance or Monte Carlo **only** because of sample size.
- **ACTIONABLE** — passes all ten proof steps.

Only ACTIONABLE advances. NEAR-MISS may be re-tested with more data or a longer forward test. DEAD is archived and may **never** be re-run with tweaked parameters.

---

## 2. Candidate Classification Matrix

| ID | Candidate | Asset | TF | Steps /10 | Failed At | Verdict | Root cause | Pivot | Next action |
|----|-----------|-------|----|-----------|-----------|---------|------------|-------|-------------|
| F1 | EMA600/40 momentum | equity | D | 4/10 | #6 significance | DEAD | NO_ALPHA_BETA (t=1.05 vs SPY) | none — equity directional closed | archive |
| F2 | LGBM features + VWAP | equity | D | 3/10 | #8 shuffle | DEAD | look-ahead leak | fix feature pipeline | debug |
| F3 | VPIN + LGBM ensemble | equity | D | 8/10 | #4 MC (N<60) | NEAR-MISS | too few trades | extend history / weekly cadence | paper 90d |
| F4 | VPIN mean reversion | equity | D | 4/10 | #2 WFO drift | DEAD | regime dependence | simplify, cut params | archive |
| F5 | Vol-momentum blend | equity | D | 7/10 | #5 friction | NEAR-MISS | cost margin < 2× | lower turnover, maker orders | re-cost |
| F6 | Quality-momentum | equity | D | 5/10 | #3 multiple testing | DEAD | 52-test deflation | new pre-registered trial | Plan/equity |
| F7 | Dual momentum | equity | W | 4/10 | #2 WFO | DEAD | whipsaw in sideways | regime trigger pre-reg | archive |
| F8 | Risk parity | multi | W | 7/10 | #5 friction | NEAR-MISS | PF≈1.00 at gate | vol-target, lower turnover | re-cost |
| F9 | Crypto breakout+carry | crypto | H/D | 3/10 | #8 shuffle | DEAD | look-ahead leak | fix leak first | Plan/crypto |
| F10 | Prediction-market consensus | pm | D | 2/10 | structural | DEAD | zero-sum + bots + fees | do not copy-trade | archive |
| F11 | Token unlock signals | crypto | event | 6/10 | #4 MC (N<30) | NEAR-MISS | low event frequency | longer history | extend |
| F12 | COT + momentum | commodity | W | 7/10 | #6 significance borderline | NEAR-MISS | OOS erosion after costs | TSMOM variant | Plan/commodity |
| F13 | FX carry+trend | forex | D | 4/10 | #5 friction | DEAD | 0.1% spread kills edge | none at retail spread | archive |
| F14 | Turtle fixed-fractional | multi | D | 3/10 | #3 multiple testing | DEAD | grid overfit | none | archive |
| F15 | Bayesian regime switching | multi | D | 3/10 | #8 shuffle | DEAD | unstable regime labels | none | archive |
| F16 | HMM momentum | equity | D | 5/10 | #2 WFO | NEAR-MISS | OOS collapse | recalibrate | paper |
| F17 | Conformal sizing | multi | per-trade | 6/10 | #2 WFO | NEAR-MISS | interval too wide | tighten calibration | re-test |
| F19 | Sterling drawdown scoring | multi | W | 6/10 | #4 MC fat tails | NEAR-MISS | 5th pct very negative | cap tail risk | re-test |
| F21 | Kelly + 3× cost gate | multi | per-trade | 8/10 | #5 friction at threshold | NEAR-MISS | slippage pushes <1.0 | better fills | paper |
| F22 | WFO min_train=20 | multi | D | 7/10 | #6 forward PF<1.15 | NEAR-MISS | forward erosion | forward test | extend |
| F24 | Gap-aware resolver | crypto | H | n/a | misapplied | DEAD (as general fix) | worsens equity | crypto only | keep scoped |
| F25 | Intrabar resolver | equity | D | 7/10 | #6 PF 0.80<1.15 | NEAR-MISS | still below gate | combine w/ F3 | paper |
| F26 | ATR trailing stops | multi | trailing | 6/10 | #2 WFO | NEAR-MISS | regime-dependent | adaptive ATR | re-test |
| F27 | VPIN reversion v2 | equity | D | 5/10 | #2 WFO | NEAR-MISS | OOS IC collapse | simplify | re-test |
| F28 | Equal-risk-parity combo | multi | W | 4/10 | #3 combined deflation | DEAD | 5-signal deflation | cascade deflated Sharpe | archive |
| F29 | Random forest | equity | D | 3/10 | #8 shuffle | DEAD | look-ahead | fix pipeline | debug |
| F30 | Transformer OHLCV | crypto | D | 3/10 | #4 MC all negative | DEAD | N too small | weekly cadence | archive |

Full detail and file citations: `01_failures_taxonomy.md`, `00_inventory.csv`.

---

## 3. Failure-Signature → Pivot Map

| Failed hurdle | Interpretation | Pivot | Reject if |
|---|---|---|---|
| Significance (CI ∋ 0) | Signal = noise | different signal family (carry/vol/cross-sectional) | same family tested > 3× |
| Friction (dies post-cost) | Edge too small to harvest | lower turnover, basket, maker orders, futures | cost margin < 2× breakeven after 3 refinements |
| Walk-forward drift | Overfit / regime dependence | cut params ≥50%, simpler signal, fresh hypothesis | same family fails WFO twice |
| Shuffle control | Pipeline leak / bug | fix code — best failure | leak unfixed in 2 sprints |
| Monte Carlo wide | Too few trades | extend history or lower frequency | still < 60 trades after extension |
| Regime-only wins | Conditional edge | pre-register regime trigger, stand aside otherwise | no deterministic regime trigger |

---

## 4. Near-Miss Register (fail only on sample size / costs)

| ID | Candidate | Trades | Missing | Fix | Horizon |
|----|-----------|--------|---------|-----|---------|
| F3 | VPIN+LGBM | ~45 | 60+ needed | 2× history + weekly | 90 days |
| F11 | Token unlock | ~22 | event density | 3× history | 180 days |
| F21 | Kelly+3× gate | ~80 | cost margin | better fill model | 90 days |
| F25 | Intrabar resolver | ~120 | PF<1.15 | combine w/ F3 | 90 days |

**Rule:** near-misses are **not** deployed. Re-test only by extending data or lengthening forward test — never parameter hunting.

---

## 5. Portfolio-Level Combination (only if single signals fail but near-misses are low-variance)

- Pool 5–8 weakly-positive, pairwise-uncorrelated signals (ρ < 0.3)
- Equal-risk-parity / vol-weighted sizing
- **Must** cascade multiple-testing correction across the combination (deflated Sharpe on *combined* strategy)
- Re-enter as a fresh pre-registered candidate in §2

---

## 6. Final Verdict (fill exactly one)

- [ ] Proven edge found — candidates: ______. Recommend forward test per `proof/PROOF_PROTOCOL.md`.
- [x] **Near-miss only** — candidates: F3, F5, F8, F11, F21, F25. Recommend data extension + longer paper test.
- [ ] No edge — clean negative result.

**Recorded status at audit time:** 0 actionable. Near-miss paper-trading track opened for F3/F21/F25.

---

## 7. Sign-off

| Role | Name | Date |
|------|------|------|
| Lead quant | Hermes (inspect-wt) | 2026-11-15 |
| Statistician | pending independent review | — |
| Governance | Elton | 2026-11-15 |
