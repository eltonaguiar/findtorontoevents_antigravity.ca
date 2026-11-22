# Code: effective trial count, and a forward recorder so the pod clock can run

**Date:** 2026-11-22 · **Owner:** buffy

## 1. `tools/effective_trials.py` (new) — and two bugs I wrote in it

**What it is for.** The DSR (29 trials → 0.9469) and Hansen SPA (p = 0.0152) disagree on the same
34 cells. The difference is the independence assumption, so the effective trial count had to be
measured rather than assumed.

**Bug 1 — the nulls inherited the data's drift.** The first version bootstrapped the raw return
matrix. That centres the null on the *observed* statistics, so "percentile of the observed t" is
meaningless: it reported H-201's t at the **47.5th percentile of its own null**, and both the
correlated and independent percentiles pinned to the solver cap at 6.09. Fixed by recentring each
column on zero, so the two nulls differ *only* in cross-cell correlation.

**Bug 2 — mixed units between the two literatures.** The solve multiplied the normal order
statistic by `sd_sr·√T` (1.393), comparing the DSR's cross-**trial** dispersion against a bootstrap
null whose cells are already standardised to sampling sd 1. It returned **N = 3** for both the
correlated and the independent null — an answer produced entirely by the scaling error. Fixed by
dropping the rescale, and then, because the analytic order statistic is itself compressed against
this bootstrap (it returns 19 for a 34-cell family), by replacing it with a **calibration curve**
built from the same block bootstrap on random subsets of the real cells.

**Also fixed before it could publish:** the DSR side first used the 34-cell subset's Sharpe
dispersion, giving 0.9761 at N=29 instead of the known 0.9469 and shifting the pass boundary to
N=58. It now reconstructs `sqrt(var_sr)` from the frozen artifact over all 40 cells and **aborts**
if the rebuilt bar does not match the frozen one to 1e-4.

**Result:** ρ̄ = 0.19; variance-of-sum N_eff = 4.67 (the *average*); correlation narrows the
max-tail by only **1.45%**; N_eff for a max statistic ≈ **25** (band 20–30); DSR boundary
**N ≤ 27**. H-201 stays `NOT_PROVEN`, because 25 ± 5 straddles 27.

## 2. `tools/pod_forward.py` (new) — the 77-day clock had no engine

`pod_status.py` reports gate state and never advances `n_days`, because nothing recorded forward
observations. A pod journal would therefore read `n_days = 0` forever no matter how often it ran.

The recorder computes the pod's own declared rule from real prices only: 6-month total return at
the last **completed** month-end, entry at the **next session's open**, 11 bp per side, marks to
market daily against T-bill, no look-ahead, no invented rows. The path is rebuilt deterministically
from an anchor month-end, so re-running is idempotent.

**It bars itself from issuing a PASS.** The pod spec requires a point-in-time universe of ≥ 22
names; the universe available here is 10 mega-caps, which item 16 showed is survivorship
contaminated. A contaminated universe can inflate a pass, so a pass is inadmissible — while a KILL
remains admissible, because failing to clear zero *despite* the inflation is a real result. Every
row carries `universe_ok` and the block reason.

**Bug fixed on the first run:** entry cost was summed over the (empty) *existing* holdings instead
of the basket being bought, so the first and most certain trade was booked at **0 bp**. Now
charges once per name from the basket being purchased. Also: a 15-day bootstrap CI is a number with
no content, so inference and vol-matching now start at 30 days and the row reports the cumulative
excess instead of a meaningless CI.

## 3. Verification

| check | command | result |
|---|---|---|
| Effective-trial tool | `python3 tools/effective_trials.py` | `RC=0`; bar reconstructs to 0.04695; DSR(29) = 0.9469 |
| New tests | `pytest tests/test_effective_trials.py tests/test_pbo_reality_check_invvol.py -q` | **18 passed** |
| Power test for the near-zero finding | in the above | ρ=0.9 narrows the max-tail > 15%, ρ=0.19 < 12% |
| Pod recorder, dry run | `python3 tools/pod_forward.py --dry-run` | `RC=0`, 15 sessions, entry cost now charged |
| Pod recorder, real run | `python3 tools/pod_forward.py` | appends rows; verdict barred by universe size |

The power test is the load-bearing one: the headline result is that correlation barely matters for
a maximum, and a near-zero effect is only credible if the same code detects a large one. On
synthetic families with ρ = 0.9 the measured narrowing exceeds 15%; at ρ = 0.19 it stays under 12%.
