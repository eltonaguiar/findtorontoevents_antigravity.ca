# PRE-REGISTRATION — H-2026-11-23-01 (turn-of-month, CRYPTO)

**Frozen:** 2026-11-23 (before any outcome measurement)
**Machine-readable:** `reports/prereg_H-2026-11-23-01.json`
**Harness:** `tools/tom_forward_clock.py` (refuses pre-freeze dates, emits 0 rows)
**Status:** PRE_REGISTERED · forward clock start 2026-11-23 · cost 1 trial

## Why this axis
The registry holds 108 hypotheses across ~90 families. `turn-of-month` appears
**0 times** — it is genuinely unspent. It needs **only price + timestamps**, so it
cannot be blocked on the PIT-fundamentals gap, and CRYPTO perps are PIT-clean
(opened≤closed 430/430 measured).

Axis ranking (fresh / measurable-now / PIT-clean):
1. **turn-of-month, CRYPTO** — fresh, measurable, PIT-clean → **chosen**
2. weekday-of-entry asymmetry — partly fresh, measurable, PIT-clean
3. PEAD on EQUITY with measured 34d lag — **blocked** (tool not on branch) and **survivorship-biased** (0 delisted names)

## Hypothesis (single)
CRYPTO longs entered on the **last trading day of the calendar month** and held
**5 calendar days** have positive net expectancy that **beats same-symbol
buy-and-hold** over the identical window.

## Frozen kill rule (two hurdles — both required)
1. net annualised > **4.32%** (T-bill), and
2. paired bootstrap 95% CI on **(net − benchmark_leg)** excludes 0 on **BOTH
   mean AND median** — a mean-only pass is a fat-tail artifact (see
   `updates/2026-11-23-two-hurdle-kill-rule.md`; H-119 was "rescued" by the mean
   and killed by the median),
plus forward **n ≥ 100**, and interim kill if CI-LB ≤ 0 at day 30 or 60.

## Cost
4.97 bp round trip primary (copilot, 191 names) · 12.87 bp conservative bound
(mine) · **every bp figure states its ticket size** ($1k → 27–34 bp, $25k → 5.8–12.9 bp).

## No-peeking declaration
No outcome data for entries dated ≥ 2026-11-23 has been examined. The harness
returns exit 2 for any pre-freeze date. This spends **one** trial, not five.

## Expected outcome
Calendar effects in crypto are weak and decaying; the honest prior is **KILL**.
A kill is a valid, valuable result: it retires an axis and does not widen SR*.

*Paper only. Zero capital. Not investment advice.*
