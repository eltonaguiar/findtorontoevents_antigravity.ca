# GitHub Actions / PR / Issue Audit — 2026-11-15T07:38Z

Repository: `eltonaguiar/findtorontoevents_antigravity.ca`
Scope: all GitHub Actions workflows, open pull requests, open issues, plus a
profitability-direction review of `WIRED_IN/` and main-branch changes over the
last 48h.

## TL;DR

The repository is **not** blocked by a mysterious failure. It is blocked by four
concrete, fixable problems, three of which are configuration bugs and one of
which is process sprawl:

1. **`backup-verify.yml` checks a gitignored file and can never pass.** It opens
   a new GitHub Issue on every run, and `actions-failure-guardian.yml` re-runs
   the failure every 30 minutes, so the issue queue is flooded (43 open
   `backup-verify` duplicates, 5 opened today).
2. **`ubuntu-latest` now resolves to 24.04→26.04**, which Playwright refuses.
   Three Playwright workflows are exposed; only `sports-smoke-and-e2e.yml` is
   fixed in an unmerged PR (786). `social-prediction-tracker.yml` and
   `sports-betting-refresh.yml` remain broken.
3. **`qa-market-validation.yml` runs with no equity quote-chain credentials**, so
   it fails every hour on infrastructure, not on bad data. Fixed in PR 786.
4. **363 active workflows, 313 on a cron schedule, 236 that push to `main`**
   (83 every single minute). This is the systemic cause of push races, rebase
   storms, cancelled runs, and Actions-minute burn.

The four highest-value actions, in order:

| # | Action | Owner file(s) | Effort |
|---|--------|---------------|--------|
| 1 | Merge PR 786 (QA keys, ubuntu pin, rebase-before-retry) | workflows | 5 min |
| 2 | Fix `backup-verify` + add issue dedup + guardian exclude-list | `backup-verify.yml`, `scripts/actions_failure_guardian.py` | 30 min |
| 3 | Close 43 stale `backup-verify` issues + consolidate secret-rotation issues | issues | 10 min |
| 4 | Pin all Playwright jobs to `ubuntu-24.04`; prune/merge cron sprawl | workflows | 2–4 h |

## Document index

| File | Contents |
|------|----------|
| `01_WORKFLOW_HEALTH.md` | Run-level evidence, per-workflow root causes, sprawl metrics |
| `02_OPEN_PRS.md` | Every open PR, mergeability, recommendation (merge/close/rebase) |
| `03_OPEN_ISSUES.md` | Every open issue class, the backup-verify flood, real bugs |
| `04_SUGGESTED_FIXES.md` | Copy-paste fixes: backup-verify, guardian, runner pins, cron hygiene |
| `(moved)` | The WIRED_IN + 48h profitability review and the finalized per-class proof plan now live in `WIRED_IN/final_v001/2026-11-15T0741Z_wire-fix-ghactions-pr-issues-v2/`. |
| `06_PATCHES/` | Ready-to-apply patch snippets (not yet applied to main) |

## What is already red on `main` (latest run per workflow)

- `Backup Restore Verification` — failure (by design impossible to pass)
- `Sports endpoint smoke + Playwright` — failure (`ubuntu26.04-x64`, Playwright
  refuses chromium)
- `QA Market Validation` — failure (`ALL 7 sources failed`, no API keys)
- `rsi5070 Forward-Test Snapshot`, `Operator Review snapshot` — push loops with
  no rebase (PR 786 fixes)

Everything else sampled is green; the volume of `cancelled` runs (11 of the last
100) is the sprawl symptom, not a code fault.
