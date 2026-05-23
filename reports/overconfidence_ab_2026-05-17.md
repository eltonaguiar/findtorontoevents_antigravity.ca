# Overconfidence-Decay A/B Harness (A2) — 2026-05-17

## Problem

`alpha_engine/score_booster.py::_apply_overconfidence_decay(pick)` decays a
pick's score excess above 80 (mimics Gemini RAKO `score *= 0.8` on the excess,
caps the adjustment at -10). It was **all-or-nothing**: env-gated
`OVERCONFIDENCE_DECAY=0/1`, and when on it decayed *every* pick. With no
control group, there was **no way to measure** whether the decay actually
improves realized win rate or just shaves score off good picks.

## What changed (3 files)

### 1. `alpha_engine/score_booster.py`

Two new module-level helpers:

- `_overconf_ab_key(pick)` — stable identity key: prefers `pick['id']`, falls
  back to `symbol + "|" + timestamp` so id-less picks are still deterministically
  bucketed instead of all collapsing into one arm.
- `_overconf_ab_bucket(key)` — `sha1(key) % 2` -> `'A'` (control) / `'B'`
  (treatment). Empty key falls to `'A'` (never silently treat an unidentifiable
  pick). Verified ~50/50 split (B = 50.6% over 2000 sample keys).

`_apply_overconfidence_decay` is now **hash-bucketed**:

- `OVERCONFIDENCE_DECAY=0` — kill-switch unchanged: no arm stamp, no decay,
  pick left entirely untouched.
- `OVERCONFIDENCE_DECAY=1` (default) — A/B mode: stamps
  `pick['_overconfidence_arm'] = 'A'|'B'` on **every** pick (so outcomes are
  attributable), then applies the decay to **arm B only**. Arm A is the
  untreated control.

Decay math (threshold 80, `-0.2 * excess`, capped at -10) is unchanged.
Additive + fail-soft (bare `except` returns 0). The application loop at
`score_booster.py:~934` is unchanged in mechanics; only the comment block was
updated to document the A/B modes.

### 2. `tools/overconfidence_ab_report.py` (new)

Attribution harness. Loads closed picks, filters to those carrying
`_overconfidence_arm`, and computes per-arm:

- `n`, realized WR, PF (whole arm)
- **top-quartile** (top 25% by score) `n`, WR, PF — this is where
  overconfidence decay actually bites

Verdict:

- `TREATMENT-OK` — arm B top-quartile WR >= arm A top-quartile WR - 1pp,
  AND both arms have top-quartile `n >= 50`.
- `REGRESSION` — both arms have `n >= 50` but arm B top-quartile WR falls
  more than 1pp below arm A.
- `INSUFFICIENT-N` — either arm has top-quartile `n < 50`.

`--selftest` proves bucketing is deterministic + ~50/50, id-less fallback
keys correctly, the helpers match `score_booster`, and modes 1/0 behave
correctly (mode 1 stamps + decays B only; mode 0 stamps nothing, decays
nothing). All 7 self-tests pass.

### 3. This report.

## Current status — n = 0 (expected)

```
 OVERCONFIDENCE-DECAY A/B REPORT (A2)
metric                     arm A (control)     arm B (decay)
n (closed)                               0                 0
top-quartile n                           0                 0
untagged closed picks (no _overconfidence_arm): 8421
VERDICT: INSUFFICIENT-N
  top-quartile n below threshold (min_n=50): A tq_n=0, B tq_n=0
  -- NO picks tagged yet (expected until the flag runs live)
```

There are 8,421 closed picks on disk but **none carry `_overconfidence_arm`** —
they were all generated before this harness existed. This is the correct and
expected result: the verdict will stay `INSUFFICIENT-N` until the modified
booster runs live and tags new picks, which then close over the next ~30 days.

## How to run the 30-day A/B

1. Ensure the production pipeline runs the score booster with
   `OVERCONFIDENCE_DECAY=1` (the default — this is now A/B mode, not
   all-or-nothing). Every new pick gets `_overconfidence_arm` stamped; only
   arm B is decayed.
2. Let picks accumulate and close for ~30 days.
3. Check progress any time:
   ```
   python tools/overconfidence_ab_report.py
   ```
4. Read the verdict once both arms reach top-quartile `n >= 50`.

## Acceptance bar

- **Promote (keep the decay):** verdict `TREATMENT-OK` — arm B (decayed)
  top-quartile WR is within 1pp of, or better than, arm A (control), with
  both arms at top-quartile `n >= 50`. The decay is not costing realized
  edge, so it stays.
- **Roll back:** verdict `REGRESSION` — arm B top-quartile WR is more than
  1pp below control. Set `OVERCONFIDENCE_DECAY=0` (kill-switch) and revisit
  the decay math.
- **Keep waiting:** verdict `INSUFFICIENT-N`.

## n right now

- Closed picks on disk: 8,421
- Tagged with `_overconfidence_arm`: 0 (arm A: 0, arm B: 0)
- Verdict: `INSUFFICIENT-N` (n = 0, harness just built — correct)
