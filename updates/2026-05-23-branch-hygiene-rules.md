# 2026-05-23 Branch Hygiene Rules

## What was changed

1. Enabled repository setting to automatically delete PR head branches after merge.
2. Added a new scheduled workflow `.github/workflows/stale-branch-cleanup.yml` to enforce a branch-age cleanup policy for merged branches.

## Branch-age policy details

- Schedule: weekly (Monday 06:17 UTC).
- Threshold: 45 days by default.
- Scope: deletes only branches that are:
  - not the default branch,
  - not protected,
  - not a reserved long-lived name (`main`, `master`, `develop`, `dev`, `staging`, `production`, `prod`, `release/*`),
  - not associated with an open PR,
  - already merged into the default branch.
- Supports manual runs with `workflow_dispatch` and `dry_run` input.

## Verification performed

- Verified repo setting:
  - `deleteBranchOnMerge: true`
- Added workflow file successfully in the repository.

## Why this helps

- Prevents stale branch accumulation after merges.
- Adds deterministic branch lifecycle cleanup for old merged branches.
- Keeps clone/fetch operations lighter over time by limiting active refs.
