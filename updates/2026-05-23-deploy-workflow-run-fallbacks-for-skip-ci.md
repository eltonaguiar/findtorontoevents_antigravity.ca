# 2026-05-23 - Deploy fallback hardening for skip-ci upstream commits

## What was broken

Several deploy workflows relied primarily on `push` path triggers. Multiple upstream automation workflows commit generated files with `[skip ci]`, which can suppress push-triggered workflows.

This created stale-deploy risk when data changed in the repo but deploy jobs did not run immediately.

## What changed

1. Updated `.github/workflows/deploy-battleground-ftp.yml`
- Added `workflow_run` triggers for:
  - `Audit Impact Tracker`
  - `Battleground Mass Backtest`
  - `Battleground Mass Backtest (Part 2 - Babies)`
- Added job guard:
  - `if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'`

2. Updated `.github/workflows/deploy-competition-to-site.yml`
- Expanded existing `workflow_run` trigger list to include:
  - `Conviction Picks Ultra-Selective Discord Alert`
  - `Contested Pick Checker (Claude vs Antigravity)`

3. Updated `.github/workflows/deploy-findcryptopairs-ftp.yml`
- Added `workflow_run` trigger for:
  - `Rapid Fire - NOW Scanner`
- Added job guard:
  - `if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'`

## Why this fix

These fallback triggers let deploy workflows run after successful upstream workflow completion, even when upstream commits use `[skip ci]` and push-trigger execution is skipped.

## Verification

- Confirmed YAML edits applied in all three workflow files.
- Confirmed exact upstream workflow names match each source workflow `name:`.
- Confirmed deploy jobs keep existing push/schedule/manual triggers and only add safe fallback activation on successful `workflow_run` completion.
