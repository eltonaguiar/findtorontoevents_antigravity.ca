# DSR trial baselines raised to the measured search space — what flips

**Question (open since 2026-11-20):** three entries in `NB_TRIALS_BY_CLASS` were
still labelled "legacy lower bound" (CRYPTO 14, FOREX 6, COMMODITY 3) while the
search space that produced those classes is far larger. If the baselines are
raised to the measured space, which class verdicts flip, and in which direction?

**Answer: exactly one — CRYPTO, and it flips from PASS to FAIL.** No other class
moves, and no class can be rescued by a *larger* trial count, because Deflated
Sharpe is monotone decreasing in `nb_trials`.

## The change

| class | before | after | source |
|---|---|---|---|
| CRYPTO | 14 | **629** | pf_registry policy-clean cells |
| FOREX | 6 | **18** | pf_registry policy-clean cells |
| COMMODITY | 3 | **9** | pf_registry policy-clean cells |
| EQUITY | 19 | 19 | unchanged |
| ETF | 12 | 12 | unchanged |
| BOND | 2 | 2 | unchanged |
| FUTURES | 3 | 3 | unchanged |

Baseline := distinct strategy cells in `by_asset_class_strategy_policy_clean_net`,
the same policy-clean book the verdict reads. `tools/dsr_trial_baseline_report.py
--strict` now exits 0 with every class `ok` (previously CRYPTO/FOREX/COMMODITY
were `UNDER`).

### The two books disagree, and that matters

The audit3 ledger counts cells differently from the policy-clean registry:

| class | ledger `cells` | registry cells | used |
|---|---|---|---|
| CRYPTO | 230 | 629 | 629 |
| EQUITY | 54 | 19 | 19 |
| ETF | 40 | 12 | 12 |
| FOREX | 22 | 18 | 18 |
| COMMODITY | 8 | 9 | 9 |
| BOND | 12 | 2 | 2 |
| FUTURES | 1 | 3 | 3 |

The registry figure is the one the gate is actually deflating against, so that is
the honest baseline. Using the ledger's 230 for CRYPTO would under-deflate by
2.7×; using the registry's 19 for EQUITY when the ledger measured 54 cells is the
opposite error. **This disagreement is unresolved and is the next thing to fix** —
two artifacts that both claim to count "cells tested per class" differ by up to
3×, and no current check compares them.

## What flips

Returns from `alpha_engine/data/closed_picks.json` (deduped, resolved only),
scored by `tools/dsr_baseline_flip.py`, whose arithmetic is asserted equal to the
live `_dsr_gate` at the effective baseline (`mirror of _dsr_gate verified on 7
classes`). Threshold 0.95.

| class | n | DSR at 14/6/3-class legacy | DSR at measured | flip | breakpoint |
|---|---|---|---|---|---|
| CRYPTO | 149 | **0.9978 (PASS)** | **0.9284 (FAIL)** | **YES** | 345 |
| COMMODITY | 106 | 0.0000 | 0.0000 | no | — |
| FOREX | 159 | 0.0000 | 0.0000 | no | — |
| ETF | 16 | non-finite → None | None | no | — |
| EQUITY | 8 | not estimable (<10) | not estimable | — | — |
| BOND | 2 | not estimable | not estimable | — | — |
| FUTURES | 4 | not estimable | not estimable | — | — |

CRYPTO's breakpoint is **345 trials**: at any trial count above that, its DSR
cannot clear 0.95 on this return series. The measured space is 629, so it is
deflated well past its own breakpoint.

Before the change the CRYPTO DSR gate **passed** (0.9978) while the class's
verdict was KILL — the kill came from the net-expectancy CI sitting entirely
below zero, not from DSR. That is the finding worth keeping: the DSR gate was
silently green on a class the rest of the tribunal had already killed, purely
because 14 trials were assumed.

## Why nothing else can flip upward

`expected_max_sharpe` grows with `nb_trials` while the standard error of the
Sharpe estimate does not, so DSR falls monotonically as trials are added. Raising
a baseline can therefore only turn a pass into a fail. Every class already
scoring 0.0 at its current baseline (the ledger records `dsr: 0.0` for all seven
class aggregates at `dsr_n_trials: 658`) is permanently past the gate until the
*returns* change, not the trial count. Any future "raise the baseline" exercise
should be read as a check that cannot improve a verdict.

## Secondary finding: the dict may soon be irrelevant

`_dsr_gate` calls `effective_n_trials(local, family=cls)`, i.e.
`max(local, global_total, family_total)`. `reports/trial_counter.json` does not
exist in the tree, so the global total is 0 today and the per-class numbers
govern. The moment the global counter is populated above 629, these baselines
stop mattering and every class deflates by the global figure. That is the correct
conservative behaviour, but it means the per-class table is a floor, not the
control.

## Limitations

- The return series is the repo's `closed_picks.json` snapshot (149 CRYPTO rows),
  not the ledger's 6,874-row class aggregate. DSR magnitudes are snapshot-specific;
  the *direction* of the flip is not, since it follows from monotonicity plus the
  observed 0.9978 → 0.9284 movement.
- EQUITY (n=8), BOND (n=2) and FUTURES (n=4) cannot be estimated from this
  snapshot at all — `_dsr_gate` skips them below 10 returns. Their flip status is
  "cannot pass today" by the ledger's own `dsr: 0.0`, not a computed result.
- ETF's 16 returns produce a non-finite `sr_variance` and the gate fails closed
  with `None`; that is the documented contract, not a bug.

## Reproduce

```bash
python3 tools/dsr_baseline_flip.py                # table + mirror self-check
python3 tools/dsr_baseline_flip.py --json         # reports/dsr_baseline_flip_2026-11-21.json
python3 tools/dsr_trial_baseline_report.py --strict   # exit 0 == mapped == cells
```
