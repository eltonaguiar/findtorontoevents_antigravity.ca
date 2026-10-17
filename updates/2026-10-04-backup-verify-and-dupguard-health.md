# CI health: backup-verify false-failure + issue spam, and dup-guard 2-3h scan

**Date:** 2026-10-04
**Worktree:** `.worktrees/health-fix` (branch `fix/ci-backup-verify-and-dupguard`)
**Scope:** `.github/workflows/backup-verify.yml`, `.github/workflows/branch-large-file-dup-guard.yml`

## 1. `backup-verify.yml` — guaranteed monthly false failure + duplicate-issue spam

### What was broken
`Backup Restore Verification` (monthly cron `0 6 15 * *`) has **failed every month**
(2026-07-15, 2026-08-15, 2026-09-15). The failure detail from issue #686 / run
`34935369660`:

```
dashboard_data.json NOT FOUND
Critical file missing: audit_dashboard/data/dashboard_data.json
```

Root cause: `audit_dashboard/data/dashboard_data.json` is **intentionally
gitignored** (`.gitignore:216`), so it is never present at `actions/checkout`.
The workflow treated its absence as a hard failure — a permanent false negative.

Second defect: run `34935369660` has **`run_attempt: 9`** (retried 9× by the
`fix-gh-actions` / `check-gh-actions` skills running `gh run rerun --failed`).
The `Open failure issue` step was **not idempotent**, so each attempt created a
fresh issue — 9 duplicate issues (686-694) for a single run. Issue counts by
month: 5 (Jun) → 6 (Jul) → 9 (Aug) → 9 (Sep), i.e. spam growing over time.

### What changed
- Added a `Fetch dashboard_data.json from production` step that curls the live
  published copy (`https://findtorontoevents.ca/audit/data/dashboard_data.json`),
  mirroring `pick-funnel-nightly.yml`. Fetch failure emits `::warning::` and the
  run continues.
- Query 1 (trading_picks proxy): absence now emits `::warning::` and is skipped
  instead of failing; an empty leaderboard is a `::warning::`, not a failure.
- Removed `audit_dashboard/data/dashboard_data.json` from `critical_files`
  (it is validated by Query 1 and is untracked by design).
- Made `Open failure issue` idempotent: it looks for an existing **open**
  `backup-verify` issue with today's title and adds a comment instead of
  creating a duplicate.

### Verification
- `yaml.safe_load` parses the workflow; steps list includes the new fetch step.
- Embedded Python compiles (`py_compile`).
- `Open failure issue` script passes `node --check`.

## 2. `branch-large-file-dup-guard.yml` — 2-3h scan never completing

### What was broken
The scan runs on every push to a non-main branch and was taking **2-3 hours**,
so with `concurrency: cancel-in-progress: true` (added in #705) every new push
cancelled the in-flight scan — observed 7 consecutive `cancelled` runs, i.e. the
guard effectively never completed and starved runners.

Root cause (empirically confirmed on a `blob:none` partial clone):
`git ls-tree -r -l` must print blob sizes, but a partial clone has no blobs, so
git **lazy-fetches every blob in every branch**. Adding `-l` to `ls-tree` cost a
full-repo blob fetch.

Measured on a synthetic partial clone (3 non-main branches):

| command | objects fetched |
|---|---|
| `git ls-tree -r -l HEAD` | 1,549 → **155,200** bytes (all blobs) |
| `git ls-tree -r HEAD` | 1,549 → 1,549 bytes (no fetch) |
| `cat-file --batch-check` (1 sha) | 1,549 → 52,766 bytes (only that blob) |

### What changed
Rewrote the scan into two passes:
1. **Pass 1** — `git ls-tree -r` (no `-l`) per branch: SHA + path only, **no lazy
   fetch**. Build `blob -> set(branches)`.
2. **Pass 2** — only blobs present in `>= min_branch_copies` branches are
   candidates; resolve their sizes with a single batched
   `git cat-file --batch-check=%(objectname) %(objectsize)`, then apply the size
   threshold.

### Verification (correctness parity + speed)
Ran the **old** (from `origin/main`) and **new** scan against identical fresh
partial clones of a synthetic repo (a 25 MB blob shared across 3 branches, plus
small duplicates and per-branch 30 MB uniques):

| | findings | objects fetched | wall time |
|---|---|---|---|
| old | 1 (23.84 MB, 3 branches) | +115,045,920 B | 2.35 s |
| new | 1 (23.84 MB, 3 branches) | +25,011,240 B | 0.53 s |

Identical findings; **4.6× less data fetched** on the toy repo (the gap grows
with repo size — the old path fetched *all* blobs, the new one only candidates).

**Live run (real repo, PR #713 branch, run `37184725900`):** the scan step now
**completes in ~21 min** (`07:05:31` → `07:26:16`) with `success`, producing
4 genuine findings (duplicate blobs across 3-4 non-main branches), versus the
previous 2-3h runs that `cancel-in-progress` kept killing before they finished.

Note: because most branches fork from `main`, the candidate set (blobs present
in >= 3 branches) is large, so 21 min is a big but not maximal improvement.
Further gains would need cheap blob sizes (e.g. the trees API) — left as a
follow-up; the job is no longer the never-completing/runner-starving case.

## Also observed (not changed)
- `db-freshness-check.yml`, `ml-gatekeeper-ab-bootstrap.yml` — `workflow_dispatch`
  only; their old failures are manual one-shots, superseded by
  `db-freshness-guardian.yml`.
- `mysql-q001-sync.yml` — has an annual `schedule: 0 8 24 5 *` (fires again
  2027-05-24); last run failed. Low priority (once/year).
- `/audit` still 404s on `data/strategy_tribunal_latest.json` — fixed in #712,
  awaits the next deploy/cron to publish.
