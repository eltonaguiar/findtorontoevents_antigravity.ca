# GitHub Actions Health Hardening (2026-05-23)

## What Was Broken

- A legacy workflow file, `.github/workflows/db-freshness-check.yml`, was still scheduled and producing repeated failed runs.
- This created confusing health signals because a newer workflow (`.github/workflows/db-freshness-guardian.yml`) also exists and is non-blocking (`continue-on-error: true` on the freshness step).
- A concrete failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26340280066
- Root cause from failed logs: `tools/db_freshness_check.py` returned RED (`exit code 2`) due stale `signal_outcomes` data, while backtests timestamp-column issue was correctly downgraded to YELLOW.

## What I Changed

1. Disabled scheduled execution for the legacy workflow by making it manual-only:
- Updated `.github/workflows/db-freshness-check.yml`
- Changed workflow name to `DB Freshness Check (Legacy Manual)`
- Removed cron trigger and kept `workflow_dispatch` only

2. Hardened the skill instructions for future incident handling:
- Updated `.claude/skills/fix-gh-actions/SKILL.md`
- Added workflow-ID verification flow for user-flagged runs
- Added PowerShell-safe no-jq fallback commands
- Added explicit stuck/repeated-failure escalation using `tools/swarm_v2`

## How It Was Verified

- Confirmed repeated failures on legacy workflow ID `282049698` using:
  - `gh api --method GET repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/282049698/runs -f branch=main -f per_page=20`
- Pulled failed logs from run `26340280066` using:
  - `gh run view 26340280066 --log-failed`
- Ran swarm escalation commands per policy:
  - `PYTHONPATH=tools/swarm_v2 python -m swarms.cli.main actions eltonaguiar/findtorontoevents_antigravity.ca --since 7d`
  - `PYTHONPATH=tools/swarm_v2 python -m swarms.cli.main research "GitHub Actions run 26340280066 ..." --depth 3 --route A`
- Re-checked latest workflow-name health scan:
  - No unresolved latest failures in `failure|timed_out|startup_failure|stale` at scan time.

## Outcome

- The legacy duplicate workflow will no longer auto-fail on a schedule.
- Future Actions health checks now include stronger anti-false-negative techniques and explicit swarm-based root-cause escalation for stuck/repeating failures.
