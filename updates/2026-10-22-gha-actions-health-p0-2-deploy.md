# P0-2 deploy + GitHub Actions health monitor — 2026-10-22

Agent: **INCEPTION / VLLM**

## What was broken / missing

1. **P0-2 (deploy of frozen-exit resolver fix).** The `_per_pick_price()`
   resolver fix (fix/frozen-exit-resolver) existed only on an unmerged branch.
   `origin/main` still had the frozen-exit stamping bug (`_per_pick_price`
   count = 0), so any walk-forward re-run reproduced the same 19 artifact cells.
2. **No lightweight GitHub Actions health gate.** The repo has a heavyweight
   `gha-summary-report.yml` (full-fleet HTML dashboard, ~360 min), but no
   fast, focused job that watches the *critical audit/measurement pipelines*
   and surfaces their health in a job summary.

## What was changed

### P0-2 — merged + deployed the resolver fix

- Cherry-picked `cf1e992582d` onto latest `origin/main` as `305f9a79561`
  (per-pick price resolution to stop frozen-exit stamping), pushed to `main`.
- `origin/main` now contains `_per_pick_price()` in
  [`audit_trail/universal_pick_resolver.py`](audit_trail/universal_pick_resolver.py).
- Regression tests pass: `pytest tests/test_resolver_frozen_exit_fix.py`
  → `5 passed`.
- This is the documented unlock for the clean **P1-2** re-run.

### GitHub Actions health monitor (new)

- [`tools/check_github_actions_health.py`](tools/check_github_actions_health.py):
  reuses the existing `tools/gha_summary_lib.py` checker library (via the
  `gh` CLI) — **not** a second hand-rolled API client. It enumerates workflows,
  fetches bulk runs for the watched branch, and reports the most recent
  conclusion for each critical workflow within a lookback window (default 48h).
- Critical workflows tracked: walk-forward gate, audit dashboard (2), DB
  freshness (2), cross-DB consistency, nightly pick funnel, and alpha-dashboard
  deploys.
- Non-blocking by default (reports + step summary); `FAIL_IF_UNHEALTHY=1`
  makes it exit non-zero.
- [`.github/workflows/gha-actions-health.yml`](.github/workflows/gha-actions-health.yml):
  scheduled every 6h at `:20` (staggered from the DB-freshness `:10` and the
  artifact-gate `:30` to avoid queue collisions), plus `workflow_dispatch`.

## How it was verified

- `python3 -c "import py_compile; py_compile.compile('tools/check_github_actions_health.py', doraise=True)"` → OK
- `python3 -c "import ...; import check_github_actions_health"` → imports, 9 critical workflows configured
- `pytest tests/test_resolver_frozen_exit_fix.py` → 5 passed
- Pushed to `main` (`305f9a79561`); health job opened as PR #751.

## Remaining (next steps)

- **P1-2 (re-run):** regenerate fixed-resolver data (now that the fix is on
  main) and re-run the walk-forward harness to confirm edge / artifact count.
- **P1-3:** open sealed forward paper cohort for the strongest sleeve.
- **P2:** mutual-fund ranker stable product; tactical rotation post-validation.
