# Restore `nb_trials: None` on a skipped DSR gate — and fix the assertion that demanded a number

**Date:** 2026-11-22 · **Supersedes:** `updates/2026-11-22-dsr-unknown-class-nbtrials-floor.md`

## What went wrong

`test_profit_program_math_2026_11_20.py::test_dsr_gate_uses_the_class_trial_count`
asserted `_dsr_gate(rets, asset_class="NOPE")["nb_trials"] >= 1`. That raised
`TypeError` against `None`, so I floored `nb_trials` at 1 in the module (#1051).

That was the wrong layer. Two other tests own this contract and both say `None`:

- `tests/test_dsr_baseline_skip.py::test_missing_asset_class_is_skipped`
- `tests/test_dsr_trial_baselines.py::test_a_class_with_no_tested_cell_still_skips`

Their docstrings record why: before 2026-11-21 the lookup was
`NB_TRIALS_BY_CLASS.get(_cls, 1)`, which applied **zero multiple-testing
correction** and let EQUITY/ETF/BOND publish an undeflated DSR as a pass. The
2026-11-21 fix made "no baseline" return `ok=None, skipped=True, nb_trials=None`.
Inventing `1` re-introduces exactly the number that change deleted — the module
would be handing a caller a trial count it never measured.

I grepped non-test callers: none reads `nb_trials` back out of `_dsr_gate`
(`tools/baby_dsr_scanner.py` only *passes one in*). So the `None` is not a live
crash hazard; the stale assertion was.

## What changed

- `alpha_engine/money_ready_verdict.py` restored to its pre-#1051 content
  (`git show 7624d4a^:…`), i.e. `nb_trials: None` for a skipped gate.
- `tests/test_profit_program_math_2026_11_20.py`: the unknown-class case now
  asserts the real contract — `ok is None`, `skipped is True`, `nb_trials is None`
  — and says in a comment why comparing it numerically is the bug.

This is not a weakened assertion: it checks three fields instead of one, and it
checks the behaviour the module documents rather than a number the module
refuses to invent.

## Verification

- `py_compile alpha_engine/money_ready_verdict.py` — OK
- `pytest tests/test_profit_program_math_2026_11_20.py tests/test_dsr_baseline_skip.py tests/test_dsr_trial_baselines.py -q` — **20 passed** (these three disagreed with each other before this change)
