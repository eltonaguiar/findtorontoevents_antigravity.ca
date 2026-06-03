# ETF Dual-Momentum — Purged-Embargoed OOS Confirmation (2026-06-03)

Cross-review demanded out-of-sample proof beyond the full-sample PF 3.57 (PR #502).
`verified_strategies/etf_dual_momentum_cv.py` splits the 48 walk-forward monthly returns into an
EARLY train window vs a LATER held-out test window with a 1-month embargo gap.

## Result — HOLDS out-of-sample
| Segment | n | PF | Sharpe |
|---|---|---|---|
| Full | 48 | 3.57 | 1.62 |
| Train (early) | 28 | 2.30 | 1.08 |
| Test (late, post-embargo) | 19 | **5.37** | **2.16** |

**Decay: −133%** (i.e. test PF is *higher* than train — no degradation). Verdict: **HOLDS_OOS** —
both halves profitable (PF>1), both Sharpe>1, no decay.

## Honest caveats
- Test segment is 19 months → **test-only attribution can't run** (needs ≥20 aligned periods); the
  full-sample attribution (t=2.36, beta 0.34) from PR #502 stands but isn't re-confirmed on test alone.
- Test PF *exceeding* train may carry a recent-regime tailwind (2024-25 equity strength) — negative
  "decay" is good but the magnitude should not be over-read; the honest claim is "no decay, edge
  persists," not "edge strengthening."
- Still a single train/test split (not full k-fold); 48 months total.

## Verdict
ETF dual-momentum **stays a VALIDATED forward-test candidate** — now with OOS confirmation that the
edge does not decay. Next: pre-register (M-107) + forward shadow-size ≤0.5% via #67. money_ready stays [].

## Reproduce
`python3 verified_strategies/etf_dual_momentum_cv.py`
