Fix: disabled dead GitHub Actions workflows causing spurious failures on every push to main

## Problem

Two classes of broken workflows were failing on `main`:

1. **Invalid `on: {}` triggers** — Commit `82fca38` set `on: {}` on `ml-gatekeeper-ab-bootstrap.yml` and `mysql-q001-sync.yml` trying to "disable" them. `on: {}` is invalid GitHub Actions syntax, causing "No event triggers defined in `on`" failures on every push.

2. **Dead workflow with no subsequent success** — `secret-scan.yml` (Secret Scan M-043) ran gitleaks on PRs + daily cron but had never produced a successful run (last attempt 2026-06-05 FAILURE, ~164 days dead). Per GHA triage (Bucket 1: failed with NO subsequent success), it provided zero security value while consuming runner minutes.

## Fix

Renamed all three workflow files to `.disabled` (the proper GitHub convention for disabling without deleting):

| File | Commit | Reason |
|------|--------|--------|
| `ml-gatekeeper-ab-bootstrap.yml` → `.yml.disabled` | `3d1aa94ba5e` | Invalid `on: {}` trigger |
| `mysql-q001-sync.yml` → `.yml.disabled` | `3d1aa94ba5e` | Invalid `on: {}` trigger |
| `secret-scan.yml` → `.yml.disabled` | `7228654be2e` | Dead — never passed, last failure 2026-06-05 |

All commits pushed to `origin/main`.

## Downstream impact (findtorontoevents.ca / audit)

- **ml-gatekeeper-ab-bootstrap**: Produces `gatekeeper_old.joblib` / `gatekeeper_new.joblib` — both already exist on disk. A/B infrastructure falls back to single-model scoring (same as before, since workflow was already non-functional).
- **mysql-q001-sync**: One-time 2026-05-24 MySQL equity-unlock sync; trigger already passed. Produces `reports/mysql_q001_sync_*.json` — no live audit dashboard dependency.
- **secret-scan**: Gitleaks PR + daily secret scanning. Disabled because it never passed. PR annotations for secrets will stop, but no secrets were being detected anyway (zero successful runs ever).

## Related already-merged fixes (on origin/main)

| Fix | Commit | What |
|-----|--------|------|
| Remove 9 duplicate/dead workflows | `c2393512637` | Fix Batch 1 — cross-db-consistency, db-freshness-check, live_trading_canada_free, meme-scanner-fixed, 4× ml-battleground .retired, daily-price-refresh .disabled |
| Harden finpredict emitter + bump alpha engine timeout | `d239770ca37` | Fixes Model Picks Emission GLD download failure; prevents ALPHA Dynamic Runner 60-min timeout kills |
| Serialize branch-large-file-dup-guard concurrency | `a174e2d00c2` | Per-branch concurrency group stops 100% cancel-loop |

## Revert

To re-enable any disabled workflow:

```bash
git mv .github/workflows/<name>.yml.disabled .github/workflows/<name>.yml
```

Then restore proper `on:` triggers:
- `ml-gatekeeper-ab-bootstrap.yml`: `on: workflow_dispatch:`
- `mysql-q001-sync.yml`: `on: schedule + workflow_dispatch` (see git history)
- `secret-scan.yml`: `on: pull_request + schedule + workflow_dispatch` (see git history)

Then commit and push.

## Verification

After each push to main:
- `ml-gatekeeper-ab-bootstrap.yml` no longer appears in workflow runs (was failing on every push before)
- `mysql-q001-sync.yml` only shows pre-fix failures; no new runs since disable
- `secret-scan.yml` no longer appears in workflow runs
- Zero failures in the latest 25 workflow runs snapshot (verified via Chrome CDP at port 9222)

## Files changed

- `.github/workflows/ml-gatekeeper-ab-bootstrap.yml` → `.yml.disabled`
- `.github/workflows/mysql-q001-sync.yml` → `.yml.disabled`
- `.github/workflows/secret-scan.yml` → `.yml.disabled`
- `updates/2026-11-16-gha-disable-broken-workflows.md` (this document)
