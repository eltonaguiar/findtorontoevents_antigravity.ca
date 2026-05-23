# GitHub Actions Audit — 2026-05-17

`/swarm-actions-audit` — Opus 4.7. Scope: every workflow whose **latest** run is
a failure with no subsequent green run (the `/fix-gh-actions` criterion), plus
the chronic-failure history.

## Overview

- Total workflows: **335**
- Failures in last 50 failure-runs: **CI Tests 35, Secret Scan 8**, then 7 × n=1.
- Workflows with latest-run = failure (the real targets): **5**.

## Findings + fixes

| Workflow | Root cause | Status |
|----------|-----------|--------|
| Automated Reporting | `git push` 403 — no `permissions:` block, `github.token` fallback is read-only when `GH_PAT` is empty | **fixed — PR #1173** |
| Incubator Pipeline — Strategy Graduation | same 403 push | **fixed — PR #1173** |
| FRED Macro Refresh | same 403 push (the FRED API 400s in the fetch step are non-fatal warnings the sidecar tolerates) | **fixed — PR #1173** |
| Quant Auditor (deep nightly) | `FileNotFoundError` — the commit step's `OUT=` writes `<date>.json` but the summary step's `OUT_FILE` env reads `<timestamp>.json`; filename-variable mismatch | **fixed — PR #1175** |
| db-freshness-check | two faults: (a) same 403 push; (b) **schema drift** — the check queried `at_signal_outcomes.exit_time` and a `timestamp` column on `bt_backtest_trades`; neither column exists (`1054 Unknown column`) → freshness graded RED → `exit 2` | **fixed — PR #1176** |

## Already resolved earlier this session

- **CI Tests** — 7-run failure burst (10:35–10:50) from the M-069 slippage units
  change not migrating `tests/test_outcome_resolver_slippage_wire.py`. The test
  file is now on the post-M-069 fraction convention; CI Tests green since 11:00.
- **Secret Scan (M-043)** — 10–20 min full-history checkout on a ~3.7 GiB repo
  throttled every merge. Fixed via `filter: blob:none` partial clone — PR #1168.
- **[torontoevent.net] Deploy Rise of the Claw** — verify step failed deploys on
  a curl timeout (exit 28 under `bash -e`). Fixed — PR #1165.

## db-freshness-check column drift — fixed (PR #1176)

`tools/db_freshness_check.py` hardcoded column names that no longer exist.
Corrected against the committed schema doc
`docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` (not a re-guess):

- `check_signal_outcomes()` — `at_signal_outcomes` has no `exit_time`; its
  datetime columns are `opened_at` / `closed_at` / `created_at`. Outcome-
  resolution freshness → **`closed_at`**.
- `check_backtests()` — `bt_backtest_trades` has no `created_at` / `timestamp`;
  its datetime columns are `entry_time` / `exit_time` / `imported_at`. Row-
  insertion freshness (per the docstring) → **`imported_at`**.
- Added `permissions: contents: write` for the snapshot commit push.

## Structural notes (non-blocking)

- Every workflow's git post-cleanup logs `fatal: No url found for submodule path
  'openclaude' in .gitmodules` (exit 128, **warning-only** — does not fail runs).
  A stale `openclaude` submodule gitlink with no `.gitmodules` entry. Cosmetic;
  fix is to either register or `git rm --cached` the gitlink.
- `actions/checkout@v4` + `setup-python@v5` on several workflows emit the Node 20
  deprecation warning (forced to Node 24 on 2026-06-02). Bulk bump to `@v6`
  recommended before that date.
