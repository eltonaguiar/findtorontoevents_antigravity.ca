# Cost-headroom gate: `breakeven_cost_bp > cost_high_bp`

**Date:** 2026-11-23
**Todo:** #27 (was deferred)
**Branch:** `copilot/hub-audit-2026-11-23`

## What was missing

`tools/cost_sensitivity.py` computed `breakeven_cost_bp` — the cost at which a
strategy's net return reaches zero — but nothing consumed it. The repo charged
between **0.98 bp** (measured) and **25 bp** (worst constant any backtest uses),
so a strategy whose breakeven sat inside that band could be reported as viable
while the pessimistic case silently wiped it out.

The rule: a strategy earns a cost-headroom PASS only when

```
breakeven_cost_bp > cost_high_bp
```

## What changed

`tools/cost_sensitivity.py`:

- `COST_HEADROOM_RULE` — the rule text, so callers and tests cannot drift from it.
- `cost_headroom_gate(breakeven_cost_bp, cost_high_bp=COST_HIGH_BP) -> dict` —
  pure function returning `status` of `PASS` / `FAIL` / `UNKNOWN`, plus
  `headroom_bp` and a human-readable `reason`.
- `analyse()` now emits `cost_headroom_gate`. **Additive only** — no existing key
  changed meaning, so recorded verdicts keep their interpretation.
- `--gate` CLI flag: exits **1** when the gate does not PASS, so it can be
  enforced wherever somebody chooses to enforce it.

### Deliberate non-decision

The gate is **not** wired into pick promotion. Turning a `FAIL` into an automatic
demotion would silently reclassify live strategies and could invert verdicts
recorded under the previous rule. That stays an explicit owner decision; what
changed is that the answer is now computed, named, and enforceable rather than
inferred by hand.

### Semantics worth pinning

- The comparison is **strict**, so a breakeven exactly equal to the high constant
  FAILS — surviving only by assuming the pessimistic case is never reached.
- `UNKNOWN` (not PASS, not FAIL) when turnover is zero: there is no cost drag, so
  the constant cannot bind and the rule has nothing to say.

## How it was verified

- `tests/test_cost_sensitivity_gate.py` — **12 passed**, covering pass, fail,
  the strict-equality boundary, `None`/zero-turnover `UNKNOWN`, additivity of the
  new key, CLI exit codes both directions, and cross-checks that the gate agrees
  with `ROBUSTLY-KILLED` / `ROBUSTLY-PASSES`.
- End-to-end on the recorded HML result:

```
gross 0.00109/yr · turnover 1.770 RT/yr · hurdle 4.32%
  breakeven cost   6.1582 bp
  cost headroom    FAIL  (breakeven_cost_bp > cost_high_bp)
  ASSESSMENT       ROBUSTLY-KILLED
```

  headroom **−18.8418 bp**. The gate agrees with the pre-existing assessment: HML
  is killed at both cost levels, so the cost constant was never what rejected it.
