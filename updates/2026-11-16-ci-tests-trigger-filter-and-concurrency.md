# CI Tests: stop letting data commits trigger and cancel the suite

**Date:** 2026-11-16
**File:** `.github/workflows/ci-tests.yml` (trigger + concurrency only — no test or job logic changed)
**Measured on:** `main` runs 05:16–07:50Z, `CI Tests` last 20 runs

## What was broken

`CI Tests` is the only workflow that actually gates `main`, and it was reporting **cancelled** instead of pass/fail far too often. Last 20 runs on `main`:

| Conclusion | Count |
|---|---|
| success | 12 |
| failure | 4 |
| **cancelled** | **4** |

A cancelled run is not a gate. Half the value of the suite is knowing a specific commit was red; when the run is superseded, a genuinely broken `main` shows up as "cancelled" and nobody looks.

Two separate causes, both in this one file:

### 1. The path filter matched generated data, not code

`push.paths` listed whole directories:

```yaml
- 'paper_trading/**'
- 'alpha_engine/**'
- 'audit_trail/**'
```

The hourly scanners commit generated JSON into those very directories (`alpha_engine/data/*.json`, `audit_trail/...`), so almost every data push re-triggered the full suite even though no testable code changed.

Evidence — commit `2edc6d65d9d` (the push that superseded my 07:58Z run), 300 files, replayed against both filters:

| Filter | Files matched | Which |
|---|---|---|
| old (`alpha_engine/**` etc.) | **94** | `alpha_engine/data/active_picks.json`, `active_picks_etf.json`, `adaptive_tp_sl.json`, … |
| new (`*.py` only) | **2** | `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js` |

94 data files were enough to look like "code changed" on every scan cycle.

### 2. `cancel-in-progress: true` on a storm-commit repo

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

With a commit landing roughly every minute and a suite that takes ~6 minutes, the in-flight run was routinely killed before it could report. The workflow's own comment already admitted this history ("~18/19 runs cancelled, CI never a gate") — the path filter was the previous attempt at it, and it did not go far enough.

## What changed

1. **Paths narrowed to Python** (plus the two dashboard assets and requirements). Each package lists both `dir/*.py` and `dir/**/*.py` rather than relying on one `**` form:

```yaml
- 'paper_trading/*.py'
- 'paper_trading/**/*.py'
- 'alpha_engine/*.py'
- 'alpha_engine/**/*.py'
- 'audit_trail/*.py'
- 'audit_trail/**/*.py'
- 'audit_dashboard/template.html'
- 'audit_dashboard/dashboard_enhancements.js'
- 'tests/**'
- 'conftest.py'
- 'pytest.ini'
- 'requirements.txt'
- 'alpha_engine/requirements.txt'
- '.github/workflows/ci-tests.yml'
```

2. **Cancellation limited to pull requests**, so `main` runs queue and finish:

```yaml
cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

No test selection, job, matrix, or timeout changed. `fail-fast: false`, `timeout-minutes: 30`, and the known-drift deselect logic are untouched.

## How it was verified

| Check | Result |
|---|---|
| YAML parses after edit | OK — `on.push.paths` 14 entries, `on.pull_request.paths` 14, `concurrency.cancel-in-progress` is the expression |
| Pattern replay on the real trigger commit `2edc6d65d9d` | old filter 94 files, new filter 2 files (both genuine code) |
| Suite still runs on a code change | covered by the two matched files above, plus `tests/**` and `*.py` |

**Limitation, stated plainly:** the replay is a simulation of GitHub's filter semantics, not an observation. The real confirmation is behavioural — subsequent data-only commits should produce no `CI Tests` runs, and the next code commit should produce one that is allowed to finish. That has not yet been observed at the time of writing.

## Follow-up worth doing

Even with the narrower filter, a burst of `.py` commits can still queue several `main` runs behind each other. If queueing becomes the complaint, the next step is `cancel-in-progress: false` on `main` plus a `timeout-minutes` cap already in place — not a return to cancelling main runs.
