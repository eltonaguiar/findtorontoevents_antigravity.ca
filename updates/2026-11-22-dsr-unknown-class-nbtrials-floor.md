> **SUPERSEDED 2026-11-22.** The module change described below was reverted: it
> invented a trial count the gate refuses to measure. See
> `updates/2026-11-22-dsr-skip-contract-restored.md`.

# `_dsr_gate` returned `nb_trials: None` for an unknown asset class — a crash, not a skip

**Date:** 2026-11-22 · **File:** `alpha_engine/money_ready_verdict.py`

## What was broken

CI Tests on `main` had been red since 2026-11-21T08:36, but the visible symptom was
a pytest **collection** error (`ImportError: cannot import name 'merge_gate'`), which
aborted the run before any test executed. Once that was fixed (#1048), the full
suite actually ran: **7,461 passed, 2 failed**. One of the two was this:

```
tests/test_profit_program_math_2026_11_20.py::test_dsr_gate_uses_the_class_trial_count
E   TypeError: '>=' not supported between instances of 'NoneType' and 'int'
```

`_dsr_gate(returns, asset_class="NOPE")` returns `ok: None, skipped: True` — correct,
a missing baseline must not pass. But it also returned `nb_trials: None`, so any
caller that compares or multiplies that field raises `TypeError`. The gate's own
contract (test docstring: "no crash, no zero") says an unknown class should still
carry at least one trial.

## What changed

- `nb_trials` is floored at **1** in the missing-baseline branch. `ok` stays `None`
  and `skipped` stays `True`, so the gate still does not pass — this only stops a
  missing baseline from crashing a caller or reading as zero trials.
- The `note` now says that explicitly instead of claiming a 1-default would pass.

## Verification

- `python3 -c "import py_compile; py_compile.compile('alpha_engine/money_ready_verdict.py', doraise=True)"` — OK
- `python3 -m pytest tests/test_profit_program_math_2026_11_20.py -q` — **10 passed**
- Reproduced the failure first on pristine `main` (`bfbb29f72af`), so this was
  pre-existing and unmasked, not introduced by any open PR.
