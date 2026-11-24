# Coverage excluded-summary wiring (2026-11-24)

## What was broken

`audit_trail.excluded_cohorts.summarize_excluded()` had no caller in
`audit_trail/dashboard_generator.py`. The dashboard dropped the auto-expired
cohort before computing every metric, but never published that cohort's size or
realised PnL, so nobody reading `dashboard_data.json` could tell whether the
retained book was flattered by the exclusions. `tools/excluded_cohorts_report.py`
already flagged this and named the fix at its line 67.

## What changed

- `audit_trail/excluded_cohorts.py`: added `coverage_excluded_summary()`, a thin
  payload shaper over `summarize_excluded()`. It forces `reason="auto_expired"`
  because the generator stamps `_auto_expired` - a key `summarize_excluded()`
  does not read - so without the explicit reason every row would be counted
  under `unknown`.
- `audit_trail/dashboard_generator.py`: added a top-level
  `coverage.excluded_summary` object to the payload, built from the
  `auto_expired` list already in scope at payload-assembly time. The import sits
  beside the existing `audit_trail` imports.
- `tools/excluded_cohorts_report.py`: added `--coverage` to print the new block,
  and to say plainly when an artifact predates the wiring.

## Scope

Auto-expired cohort only. The mirror-duplicate and invalid-row exclusions exist
only as counters by payload time, so they are not measured here and the payload
says so (`scope: auto_expired_only`).

## Verification

Unit tests:

```
$ python3 -m pytest tests/test_excluded_cohorts_coverage.py \
    tests/test_excluded_cohorts.py tests/test_excluded_cohorts_report.py -q
17 passed
```

```
$ python3 -m pytest tests/test_dashboard_coverage_wiring.py -q
4 passed
```

Generator still compiles:

```
$ python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"
COMPILE OK
```

Against the real payload present in the checkout
(`audit_dashboard/data/dashboard_data.json`, 25,804,703 bytes, dated Nov 22):

```
$ python3 tools/excluded_cohorts_report.py \
    --payload audit_dashboard/data/dashboard_data.json --coverage
payload has no coverage.excluded_summary (generator not wired for this artifact)
EXIT=3
```

That exit 3 is the expected result, not a failure: the artifact was built before
this change. It will report a live measurement once the hourly dashboard build
next regenerates the payload.

Synthetic proof of the shaper:

```
scope       : auto_expired_only
total       : 1
n_with_pnl  : 1
by_reason   : ['auto_expired']
reason stats: {'n': 1, 'n_with_pnl': 1, 'win_rate': 0.0, 'mean_pnl_pct': 0.0,
               'sum_pnl_pct': 0.0, 'long': 1, 'short': 0, 'unknown': 0,
               'top_symbols': {'BTCUSDT': 1},
               'first_closed': None, 'last_closed': None}
```

The `by_reason` key is `auto_expired` rather than `unknown`, which is the
behaviour the forced reason exists to guarantee.

## Additive proof

- `summary.auto_expired_excluded` (the pre-existing integer) is untouched; the
  new object is a sibling under a new top-level `coverage` key.
- No data file and no workflow file was modified. `tests/**` is already a CI
  trigger path in `.github/workflows/ci-tests.yml`, so the new tests are gated
  without touching the workflow.
