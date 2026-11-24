# Full-suite verification against the production test command (BLOCK 46)

**Date:** 2026-11-23
**Measured at:** `cf2a13152a5b581ef4f3d0f64c5ec9b1b4296ea0` (origin/main tip at measurement time;
the session's own PRs #1082–#1099 landed earlier at `b9bd6f7bb2cdbe27eab9087d44ce9f75eacc7f20`)
**Verdict:** No breakage attributable to this session's changes. Nothing to fix.

## What production actually runs

From `.github/workflows/ci-tests.yml` (job `test`, matrix Python 3.11 and 3.12,
`timeout-minutes: 30`, steps install `requirements.txt`, `alpha_engine/requirements.txt`,
`pytest>=7,<9 pytest-cov pytest-timeout`):

```
python -m pytest tests/ paper_trading/tests/ alpha_engine/tests/ tools/tests/ \
  -v \
  --tb=short \
  --durations=10 \
  --timeout=120 --timeout-method=thread \
  --junitxml=test-results.xml \
  --cov=alpha_engine --cov=audit_trail --cov=tools \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=10 \
  --no-cov-on-fail \
  -m "not integration and not network" \
  $DESELECTS
```

with `FRED_MACRO_DISABLED: '1'` in the step env, and `$DESELECTS` built from a
69-node-ID known-drift quarantine list written by the preceding step
(`--deselect=` per line, comments/blank lines skipped). The job also runs two Node
guards (`tests/test_card_metrics.js`, `tests/test_active_pick_why_justification.js`)
and a non-blocking run of the quarantined tests.

## What I had been running

Only `pytest tests/test_verify_peer_claims.py tests/test_capacity_model.py
tests/test_edge_research_tally_consistency.py` by name. That bypasses the full-tree
collection, the quarantine deselects, the markers, the timeout plugin and the
coverage gate.

## Baseline

- **Last green `CI Tests` on main before PR #1082:** run `45105769782`, success,
  `3e73c8e299d80146daf4eff1387fc2349bcaede9`, 2026-11-23T03:24:13Z (merge of PR #1077).
- **`CI Tests` on main after PR #1099:** run `45134909923`, success,
  `b9bd6f7bb2cdbe27eab9087d44ce9f75eacc7f20`, 2026-11-23T07:57:54Z.
- Main is green before and after the session.

## Local full run (fresh non-shallow clone, `--filter=blob:none`, is-shallow = false)

Environment: Python 3.12.3, pytest 8.4.2, deps from the same two requirements files.

- collected 7802 items / 87 deselected / 10 skipped / 7715 selected
- **7666 passed, 57 skipped, 87 deselected, 2 xfailed, 0 failed, 0 errors**
- wall clock **251.86s (0:04:11)**; coverage 14.70% (gate 10% reached)
- summary line: `= 7666 passed, 57 skipped, 87 deselected, 2 xfailed, 27 warnings in 251.86s (0:04:11) =`

My three files inside that collection: `tests/test_verify_peer_claims.py` 39 passed,
`tests/test_capacity_model.py` 16 passed, `tests/test_edge_research_tally_consistency.py`
25 passed (the programme tally `0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` test
included). None of them is in the quarantine list. No (M) failures exist.

## Classification (M) mine vs (P) pre-existing

- **(M) mine:** none.
- **(P) pre-existing:** none *in a production-equivalent environment*.

### PHP caveat (environment, not code)

This workstation has no `php` binary (CI's `ubuntu-latest` runner does — the movie tests are
not quarantined and CI is green). Without PHP, a first local run showed
`41 failed, 7625 passed` (27 `test_movies_db_config.py`, 13 `test_movies_rating_refresh.py`,
1 `test_movies_legacy_wrapper.py`), all failing on `assert PHP` or a `None` executable.
A separate clone at the pre-session baseline `8df41b09121ded4808dcf156d5b608697b59f1c5`
produced the **identical 41-node-ID failure set** (`diff` empty), and none of those three
files was touched between the baseline and main. With PHP provided (docker `php-cli-ubuntu24`,
PHP 8.3.6) the same set is `46 passed`. Those failures are environmental and unrelated.

## Discrepancy worth noting

The workflow header comment still says "~747 tests (558 root + 103 walkforward elite + 86
alpha_engine)"; the actual collection is **7802 items**. The comment is stale.

## What remains unverified

- Python **3.11** was not run locally (only 3.12.3); CI runs both.
- PHP locally is a dockerized PHP 8.3.6, not the runner's native PHP.
- The CI job's exact runner image and cached pip state differ from this machine.

No code changed in this block, so there is nothing to fix or regress.
