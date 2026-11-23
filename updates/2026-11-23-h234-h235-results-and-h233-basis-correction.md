# H-234 ROBUST, H-235 SURVIVES, and a basis bug that changed H-233's story

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

Three pre-registered tests ran in one sequence. Two passed and one needed its own narrative
corrected. The correction came first, because it invalidated numbers I had already published.

## What was broken in H-233 (my own code)

`rebalanced_book()` in `tools/h233_vol_target_replication.py` set the rebalance bucket to the
**constant string** `"daily"` when `freq is None`:

```python
bucket = "daily" if freq is None else d.to_period(freq)   # constant -> fires once
```

so the branch that resets weights fired on the first bar and never again. The book I reported as
"daily rebalanced" was a **never-rebalanced, drifting** book. Fixed by using the timestamp as the
bucket (`bucket = d if freq is None else ...`), verified, and re-run.

Consequences, all of which I had already published and now withdraw:

| claim I made | corrected |
|---|---|
| A: ΔCE +2.3756pp, CI [−0.2182, +4.9008] | +2.033pp, CI [−0.8123, +4.8369] |
| B: ΔCE −0.3549pp (negative) | **+0.2282pp** (positive), CI [−2.5217, +2.8852] |
| B: "vol targeting lowered CAGR 9.97% → 9.58%" | **false** — 8.38% → 8.63%, it raised it |
| "the sign flips between sub-periods" | **false** — sign agreement now holds |
| full sample ΔCE +1.0178pp [−1.03,+3.00] | +1.1355pp, CI [−0.8675, +3.0924] |

**The verdict label does not change: `REFUTED_OOS`.** Criterion 2 (CI lower bound > 0 in the holdout)
fails in every window, and that criterion was written before the run. What changes is the
**diagnosis**: this is a power failure (effect ≈1pp against an interval ~5pp wide), not a sign flip,
and the mechanism's direction is consistent across both windows.

## H-234: H-201's edge is in BOTH halves — `ROBUST`

Pre-registered (`plans/2026-11-23-prereg-H-234-h201-two-window.md`), construction copied verbatim
from `tools/per_class_edge_harness.py` (10 mega caps, 126-day lookback, top 3, 21-day rebalance,
10 bp/unit turnover, SPY benchmark), split at the temporal midpoint, no retuning.

| window | n | mean net | CI 95% | excess vs SPY | halves |
|---|---|---|---|---|---|
| A 2012-01..2019-06 | 1,884 | +10.173 bp | [+5.014, +15.624] | +4.631 | +5.912 / +14.434 |
| B 2019-07..2026-11 | 1,860 | **+12.887 bp** | [+5.884, +19.992] | +6.952 | +14.898 / +10.875 |
| FULL | 3,744 | +11.521 bp | **[+7.246**, +16.071] | +5.784 | +9.991 / +13.051 |

Both windows clear all three criteria, and the second half is **stronger** than the first. The
full-sample CI lower bound reproduces the claimed **+7.246 bp/day** to the third decimal, which
also validates the harness against the artifact that produced C-019.

**This is the first cell in the programme that replicates on both halves of its own sample with
positive benchmark excess.** It does not become PROVEN: the DSR margin (holds to N=28 of 29) and the
76.7-day data margin are untouched by this test, and the extra trial raises N to 30, which moves the
bar the wrong way.

## H-235: the drawdown reduction holds outside the US book — `SURVIVES`, with real caveats

Pre-registered (`plans/2026-11-23-prereg-H-235-drawdown-generalisation.md`).

| book | plain MDD | VT MDD | improvement | plain CAGR → VT | ΔCE [CI] |
|---|---|---|---|---|---|
| US pre-2005 (611 bars) | −9.21% | −8.99% | **+0.22pp** | 12.86% → 14.14% | +1.13pp [−5.57, +7.80] |
| US 2005-2026 (5,506 bars) | −30.04% | −22.03% | **+8.01pp** | 8.24% → 9.47% | +1.13pp [−0.87, +3.06] |
| non-US EFA/BWX (4,808 bars) | −42.61% | −28.22% | **+14.39pp** | 2.95% → **1.35%** | −1.57pp [−4.23, +1.24] |

Drawdown improved in **all three**, so the pre-registered criterion is met. The honest reading is
narrower than the label: the pre-2005 margin is 0.22pp on 611 bars, which says nothing; and in the
ex-US book the drawdown gain was **paid for with half the return**. The rule that survives is
therefore "vol targeting reduces drawdown broadly, and in a high-vol book it is nearly free" — not
"vol targeting is free everywhere".

## The evidence-path sweep

`reports/evidence_path_sweep_2026-11-23.json`, 26 claims / 68 evidence entries:

- **10 resolve on main**, 2 are COMS topics rather than paths.
- **50 resolve only in the unmerged worktree** `/tmp/cv` (C-009…C-025) — every claim from that
  session is unreproducible from main until the branch merges.
- **6 are genuinely missing**, all hung off `reports/horizon_backtest_2026-11-22.json` (C-001, C-003,
  C-005, C-006, C-008) plus `reports/2026-11-22-horizon-allocation-review.md`. Those claims have no
  reachable evidence and need regeneration.

Fixed where possible: `tools/per_class_edge_harness.py` and `tools/vol_target_vs_hold.py` are now on
main, so C-015 and C-014 resolve.

## A second tooling defect, disclosed

My JSON array locator was wrong three times (`raw_decode` started one character before the bracket,
and once I used `t2.index('[')` which found `"verifiers": [` instead of the claims array). Two of the
three were caught by asserting membership in the parsed list; one was not — **H-234 and H-235 ran
before their registry entries existed.** The pre-registration documents themselves were committed
in `5093eb796f8` *before* any run, so M-107's substance was met, but the registry JSON did not carry
them at run time. Both entries are filed now with their results and this timing is recorded rather
than tidied away. The locator now uses a regex on the key and asserts after writing.

## Verification run

- `tools/h234_h201_two_window.py` → exit 0, `ROBUST`, full-sample CI-LB +7.246 reproducing the
  artifact.
- `tools/h235_drawdown_generalisation.py` → exit 0, `SURVIVES`, 3/3 books.
- `tools/h233_vol_target_replication.py` (corrected) → exit 0, `REFUTED_OOS` on criterion 2,
  sign agreement true.
- Registry re-parsed: all three ids present, unique, valid JSON.
- Claim register re-parsed after append: C-027 present once.

## Limitations

- H-234's windows are halves of one 15-year sample of 10 mega caps; both halves share the same
  survivorship-prone universe, so this tests period stability, not universe stability.
- H-234 adds a trial (N 29 → 30), which raises the deflation bar for every cell.
- H-235's pre-2005 book is 611 bars and cannot carry a verdict; the non-US book is US-listed ETFs of
  non-US assets.
- All costs modelled (10 bp H-201, 5 bp/unit vol overlay), none measured.
