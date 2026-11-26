# Pin sudo/node jobs to hosted runners before any self-hosted flip

**Date:** 2026-11-26

## Why

`.github/workflows/runner-smoke-test-linux.yml` (run 45759679260) proved that the `gx10` ARM64 runner has
**no passwordless sudo** and **no node/npm**. Every workflow runs on
`${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`, so setting that repo variable would silently break
any job that apt-installs or shells out to npm.

## What changed

Pinned `runs-on: ubuntu-latest` in the 17 workflows that need root or a node toolchain:

- algorithm-competition-refresh.yml
- alpha-engine-daily-picks.yml
- asterdex-paper-trading.yml
- db-backup-email.yml
- db-sync-bidirectional.yml
- db-sync-to-mirror.yml
- deploy-competition-to-site.yml
- deploy-fc-api-env-godaddy.yml
- deploy-riseoftheclaw.yml
- kimi-feb172026-live.yml
- meme-scanner-v2.yml
- mirror-site.yml
- ml-model-autotraining.yml
- sports-data-snapshots.yml
- torontoevent-algorithm-refresh.yml
- torontoevent-deploy-competition.yml
- worldclass-pipeline.yml

Two of the 19 candidates needed no change: `ci-tests.yml` is already pinned to `ubuntu-latest`, and
`audit-dashboard.yml` selects the runner through an explicit `inputs.runner` that already defaults to the
cloud runner.

## Verification

- Each replacement is anchored to a `runs-on:` line, so `uses:`, `run:` blocks and job names are untouched.
- `actionlint` on all 17 files: **0 syntax-check errors**.
- Diff: 17 files changed, 23 insertions / 23 deletions — nothing but runner selection.

After this lands, `ACTIONS_RUNNER_LABEL=gx10` can be set with a one-command rollback (delete the variable)
without breaking these workflows.
