# `deflated_sharpe.py` — four defects fixed, and the 64.4% headline withdrawn

**Date:** 2026-11-22
**Tool:** `tools/deflated_sharpe.py`
**Artifact:** `tools/deflated_sharpe_results.json` (regenerated)
**Ledger item:** T6

---

## Why this mattered

`tools/deflated_sharpe_results.json` was the only deflation gate in the repo, and it
was reporting that **29 of 45 strategies (64.4%) survived deflation**. That number
was being carried as evidence that the pick-generation side had real, survivable
edge. It was wrong in four independent ways, all verified in source.

## The four defects

### 1. The "DSR" was a z-score — Φ(·) was never applied

```python
def _deflated_sharpe(sr_obs, sr_star, se_sr):
    """DSR = (SR_observed - SR_haircut) / SE(SR)."""     # <-- label is the bug
    return (sr_obs - sr_star) / se_sr
```

The Deflated Sharpe Ratio is `Φ((SR − SR*)/SE)` — a **probability in [0, 1]**. The
function returned the argument of `Φ`, unbounded. The shipped artifact's `dsr` field
ranged **[−23.88, +15.08]**, which is impossible for a probability. A reader seeing
`dsr: 15.0783` reasonably concludes 1507%.

**Fix:** `_deflated_sharpe` now returns `Φ(z)`; the raw z is preserved as `dsr_z`.
**Proof:** `z=+10 → dsr=1.000000` (bounded); `z=+1 → 0.841345`; `z=−1 → 0.158655`.

### 2. The survival gate was `dsr > 0`, i.e. a 50% significance level

`survives = dsr > 0` is `z > 0`, which is one-sided **p < 0.500** — a coin flip. A
95% gate is `z > 1.645`. The 64.4% headline was produced by the coin-flip gate.

**Fix:** `survives = dsr >= CONFIDENCE` with `CONFIDENCE = 0.95`.
**Proof:** a DSR of 0.8413 now **FAILS** (it passed before).

### 3. A hardcoded 2190 trades/year inflated every Sharpe by 46.8×

```python
ANNUAL_TRADES = 6 * 365          # ~6 trades/day for crypto, annualise
sr_ann = sr_trade * math.sqrt(ANNUAL_TRADES)
```

Every strategy got the same `√2190 = 46.80×` multiplier regardless of how often it
actually traded. That is where annualised Sharpes of **43.93** and **93.20** came
from, and why **15 of 45** strategies showed a Sharpe above 10.

**Fix:** the rate is now **measured** per group from its own first-to-last timestamp
(`trades_per_year_observed`, `span_days_observed`). When no span can be established,
`sharpe_annual` is **null** rather than guessed.
**Proof:** a 7-day span containing 2 trades measures **104.36 trades/yr** (expected
104.36); no timestamps → `None`.

### 4. Unit mismatch in the standard error

`_sharpe_se(sr_ann, skew, kurt, T)` was passed an **annualised** Sharpe with `T` =
number of **trades**. `SE(SR) = sqrt((1 + ½SR² − γ₃SR + ((γ₄−3)/4)SR²)/T)` is defined
per period; mixing the two is dimensionally incoherent.

**Fix:** moments, SE and haircut are all computed in **per-trade** units; annualisation
happens once, at presentation.
**Proof:** `SE(T=100)/SE(T=200) = 1.414214` = √2, confirming the 1/√T scaling.

## A fifth thing the fix exposed: the haircut was an unstated assumption

The multiple-testing haircut needs `σ_SR` — the dispersion of Sharpe ratios **across
the trials**. The old code used `√2·erfinv(1 − 2/N)`, which silently assumes
`σ_SR = 1.0`.

That quantity is now **measured** from the cross-section of the sample, with two
estimators reported because the choice matters:

| estimator | value | note |
|---|---|---|
| plain SD | 0.8525 | dominated by one strategy at −4.22 (median is −0.07) |
| **robust (MAD × 1.4826)** | **0.4390** | used for the haircut |

`σ_plain` is 1.9× the robust scale, which the tool prints as a notice. The robust
estimator is a standard heavy-tail scale estimate — chosen **a priori**, not tuned
until something passed, and both values are in the artifact so the sensitivity is
visible.

**Stated caveat:** estimating dispersion from the tested sample includes any genuinely
skilled strategy, which inflates σ and therefore **harshens** the haircut. Conservative,
not flattering. With fewer than 3 trials there is no cross-section and the haircut
collapses to 0 — printed explicitly rather than hidden.

## Corrected result on the live data

3,500 closed picks, 127 strategies, 55 with ≥10 trades.

```
sigma_SR(robust) = 0.4390    sigma_SR(plain) = 0.8525
SR* = 1.014231  (per-trade)
Survival gate: DSR >= 0.95
```

| | old (broken) | corrected |
|---|---|---|
| survivors | **29/45 = 64.4%** | **0/55 = 0.0%** |
| `dsr` range | [−23.88, +15.08] | [0.0000, 0.6605] |
| gate | z > 0 (50%) | DSR ≥ 0.95 |

**Best strategy:** `forex_rsi2_mean_reversion` — 20 trades, 80% WR, per-trade
Sharpe 1.169, **DSR 0.6605**, `survives: false`.

Note the `span_days_observed: 2.7` on that row. Its `sharpe_annual` is **61.28**
because 20 trades in 2.7 days implies ~2,746 trades/yr and multiplies the per-trade
Sharpe by ~52. That is arithmetic, not a forecast — which is exactly why the span is
now published next to the number. It is the hardcoded-2190 defect in miniature, and
the reason the field exists.

**Ensemble (all 3,500 picks):** WR 39.6%, annualised Sharpe **−6.589**,
DSR **0.0000** → FLAGGED.

## A data defect the tool now reports

`MeanReversionBB` has 29 trades with **zero return variance** — identical `pnl_pct` on
every trade. That is not a trading record. It is now emitted as a `::warning::DATA
DEFECT` naming the strategy, rather than silently entering the dispersion estimate.

## Verification

```
python3 tools/deflated_sharpe.py --selftest
  z=+0.0 -> dsr=0.500000 (Phi(z)=0.500000)  ok
  z=+1.0 -> dsr=0.841345 (Phi(z)=0.841345)  ok
  z=-1.0 -> dsr=0.158655 (Phi(z)=0.158655)  ok
  z=+10 huge edge -> dsr=1.000000 (bounded by 1)  ok
  DSR=0.8413 vs gate 0.95: FAIL(correct)
  observed trades/yr from a 7-day span -> 104.36 (want 104.36)  ok
  no timestamps -> None (must be None, not a guess)  ok
  SE(T=100)/SE(T=200) -> 1.414214 (want sqrt(2)=1.414214)  ok
  haircut N=10,sd=.02 -> 0.0315 < N=146,sd=.02 -> 0.0531 < N=146,sd=.04 -> 0.1063  ok
  haircut with no measurable dispersion -> 0.0 (0.0, and reported not hidden)
  ALL DSR SELFTESTS PASSED
```

Artifact invariants re-checked after regeneration: every `dsr` lies in [0,1]; no
`annual_trades` key remains in `config`; `sharpe_annual` is null on 4 of 55 rows where
no span was measurable.

## What this changes downstream

Any conclusion that rested on "64.4% of strategies survive deflation" is withdrawn.
With the gate working, **nothing in the current pick set survives deflation**, which
is consistent with the rest of this programme: gross edge ≈ round-trip cost, and the
binding constraint is measurement rather than strategy discovery.

Zero capital sanctioned. Not investment advice.
