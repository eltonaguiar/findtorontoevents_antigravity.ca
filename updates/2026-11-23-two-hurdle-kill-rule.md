# Defect fixed: kill rule had ONE hurdle, needs TWO (copilot correction #2)

**Date:** 2026-11-23  **Worktree:** vanilla-handsaw  **Author:** Kilo

## What was broken
`reports/kill_rule_ledger.json` (v1) used a single hurdle: "CI-LB<=0 at day 30/60 or
forward n<100". A rule that is long the benchmark 90% of the time clears a cash
hurdle on **beta alone** while its signal contributes nothing. Copilot flagged this;
it is a real defect in my artefact, now fixed.

## New frozen rule (two hurdles)
A pick survives only if **both** hold:
1. net annualised > **4.32%** (T-bill hurdle), and
2. paired bootstrap 95% CI on **(net − benchmark_leg)** excludes zero on **BOTH the
   mean AND the median**,
plus forward n ≥ 100.

## The trap I caught during implementation
First implementation used the **mean-only** paired bootstrap and reported
H-119 as passing (mean CI [+0.19%, +2.28%], annualised +20.6%). That was wrong.
Diagnosis: the benchmark leg has a fat **left** tail (mean −0.92%, median +0.17%;
min −68% from crypto-crash rows) while gross has a fat **right** tail (mean +0.41%,
median −1.00%). A mean-only test therefore "wins" on outliers, not on edge.

Robust re-test on the same 343 paired rows:
- median paired diff **−0.15%**, median CI **[−0.51%, +0.17%]** → includes 0
- fraction of trades beating benchmark **47.8%**
- two-sided sign test **p = 0.45**

## Verdict
**H-119 KILLS.** Consistent with the published ledger (net PF CI-LB 0.9213 < 1.0).
No disagreement between the robust two-hurdle test and the tribunal.

## Files
- `tools/two_hurdle_kill.py` (new; mean CI + median CI + sign test + trimmed mean)
- `reports/two_hurdle_kill.json` (measured)
- `reports/kill_rule_ledger.json` (rule_v2 + CRYPTO_H119 verdict)
- `audit_dashboard/audit2.js` + `tests/test_assert_surface_parity.py` (P2-9, committed separately)

## Numbers
343 paired rows (87 unpaired excluded of 430) · cost 12.87 bp RT @ $25k ·
mean hold 4.92 d · net annualised +20.56% (mean) but median trade −0.15% vs bench →
KILL.

*Paper only. Zero capital. Not investment advice.*
