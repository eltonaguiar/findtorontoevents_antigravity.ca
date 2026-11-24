# DSR uses the global trial count (2026-11-19)

**Scope:** `alpha_engine/audit3_tribunal.py` — one line in `build_report`.

## What was wrong

```python
n_trials = sum(1 for g in strat_groups.values() if len(g) >= WR_MIN_N)
```

DSR's `SR0` is the expected maximum Sharpe across **every** configuration that
was emitted and scored. Counting only the configurations that cleared the
reporting floor understates the multiple-testing correction, so DSR was too
generous exactly for the thin cells that need it most.

## Change

```python
n_trials = len(strat_groups)
```

The module docstring now says `n_trials = every emitted strategy`.

## Verification

- audit3 suites: **92 passed**.
- Live canonical rebuild (8,735 rows): top-line verdicts unchanged
  (0 PROVEN, 0 CANDIDATE, 59 WEAK, 8 KILL); only per-cell DSR values tighten.

## Note

This is P0-5 from `NEXT_STEPS.md` ("DSR n_trials = global N, not tested cells").
It can only make promotions harder, never easier.
