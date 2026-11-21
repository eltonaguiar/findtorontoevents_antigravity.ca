# The anti-overfit gate now fails on regression, not on the standing 6/80

Adopted option (b) from `updates/2026-11-20-anti-overfit-dsr-gate-never-passes.md`,
with the user's decision on 2026-11-21.

## What was wrong

The CI step returned 2 whenever **any** strategy sat below DSR 0.95. 74 of 80
always do, so every hourly run since #1017 was red -- and a red job that is always
red tells you nothing.

## What the gate does now

* **Baseline.** The sidecar reads the payload it is about to overwrite
  (`read_previous_audit`) and records it in the new payload as `dsr_prev_audit`
  (`generated_at`, `pass_count`, `scored_count`, `pass_rate`). The file on disk is
  the previous audit: CI checks out shallow, so git history is not a reliable
  baseline. The post-merge label re-stamp rewrites the payload with a dict
  round-trip, so the block survives it (pinned by a test).
* **Fails on a fall in the pass rate** of more than `--regression-tolerance`
  percentage points (default 1.0) versus that baseline.
* **Fails when the measured population shrinks** by more than
  `--coverage-tolerance` (default 25%): losing data can *raise* the rate.
* **Fails when there are no pass counts at all**: an unmeasurable audit is not a
  pass. A genuinely missing payload is still exit 3.
* **Passes on the first run with no baseline** rather than refusing to run.
* **Always prints the absolute number**, in pass and fail alike.

## What it prints

Steady audit (exit 0):

```
ANTI-OVERFIT GATE: PASS -- 6/80 strategies clear DSR 0.95 (7.5%), 74 below the floor; previous audit 6/80 (7.5%)
exit=0
```

Regression (`6/80 -> 4/80`, exit 2):

```
ANTI-OVERFIT GATE: FAIL -- regression vs the previous audit
  now: 4/80 strategies clear DSR 0.95 (5.0%), 76 below the floor
  - pass rate fell 7.5% (6/80) -> 5.0% (4/80), -2.5pp (tolerance 1.0pp)
exit=2
```

## Why the absolute number is still enforced elsewhere

Moving the *job colour* to "did it get worse" does not drop the finding:

* `publication_label` still marks 74 of 80 rows PROBATION, and the payload still
  carries `dsr_pass_rate` (6/80 = 7.5%) for the dashboard and the log.
* `apply_dsr_probation_labels.py --check` still fails when the labels stop
  describing the rows.
* `tools/detect_merge_hybrid.py` (#1031) still fails when a declared count stops
  matching its own rows.

## Files

* `tools/anti_overfit_audit_sidecar.py` -- `absolute_state`, `read_previous_audit`,
  `regression_reasons`; baseline capture before the write; both gate paths
  (generate and `--check-only`) use the same judgement; two new flags.
* `.github/workflows/audit-dashboard.yml` -- the step is renamed
  `Anti-overfit GATE (blocking — fails only on regression vs the previous audit)`
  and passes both tolerances explicitly.
* `tests/test_anti_overfit_gate_regression.py` -- 13 tests for the policy.
* `tests/test_anti_overfit_gate_2026_11_20.py` -- 3 tests rewritten, because they
  asserted the old contract (fail on any bad DSR). Not weakened: they now assert
  that a steady audit passes, a regression fails, and a payload with no counts
  fails.

## How verified

* 40 tests pass across the regression, gate, label and hybrid suites.
* Stable fixture -> exit 0 with `6/80 ... 7.5%, 74 below the floor`; regression
  fixture -> exit 2 with `-2.5pp (tolerance 1.0pp)`.
* The real committed payload (written before this change, so no baseline block)
  exits 0 and says so; after the next cycle it carries a real baseline.
* Workflow YAML parses; the step is still unique, still blocking, still after
  deploy (the existing structure test enforces that).

## Limits

* At n=80 the 1pp tolerance is 0.8 strategies, so one strategy slipping across
  0.95 (1.25pp) does fail the run. That is the intended sensitivity, but it is a
  knife edge -- raise `--regression-tolerance` if the population is noisy.
* The baseline is whatever payload is on disk. In CI that is the committed one; a
  local run rewrites it with local numbers.
* A duplicate row collapsed by the post-merge re-stamp can shift the declared
  pass count by one, which would read as an improvement rather than a regression.
