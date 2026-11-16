# Phase 1 GHA Inventory & Classification Report

**Repository:** eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-16T02:45 UTC
**Method:** Local PyYAML scan of all `.github/workflows/*.yml` files (no API auth required)

## Summary

| Metric | Count |
|--------|-------|
| Total workflow files | 369 |
| Active | 355 |
| Disabled (.disabled) | 8 |
| Retired (.retired) | 6 |
| No concurrency group | 200 |
| No timeout-minutes | 95 |
| Push trigger, no path filter | 4 |
| No triggers at all | 1 |
| Parse errors | 0 |

## Bucket Classification

### Bucket 1 — Live Scheduled Data/Trading Pipelines (~180 workflows)
Cron-scheduled scanners, pick generators, data refreshes, model trainers. These are the core revenue-relevant workflows. Most lack concurrency groups and timeouts — they stack on every cron tick.

### Bucket 2 — CI / PR Checks (~20 workflows)
ci-tests.yml, conflict-marker-check, branch-large-file-dup-guard, sports-smoke-and-e2e, etc. Some already have concurrency + path filters (ci-tests, sports-smoke). Others need hardening.

### Bucket 3 — One-Time / Bootstrap (candidates for disable)
`Dynamic Runner Template` (no triggers — never runs), plus various `.disabled`/`.retired` files already handled.

### Bucket 4 — Dead / Never-Succeeded-Recently
`secret-scan.yml.disabled`, `ml-gatekeeper-ab-bootstrap.yml.disabled`, `mysql-q001-sync.yml.disabled` — already disabled. `backup-verify.yml` historically fails monthly.

## Highest-Impact Phase 2 Fixes (Low Risk)

### Fix A: Path filters on push-only workflows (4 workflows)
These run on every push to main — wasteful in a storm-commit repo.

| Workflow | Current | Fix |
|----------|---------|-----|
| Branch Large File Duplicate Guard | push, no paths | Already fixed in `a174e2d00c2` (per-ref concurrency) |
| Conflict Marker Check | push, no paths | Add `paths: ['*.py', '*.php', '*.js']` |
| No stale DB passwords | push, no paths | Add `paths: ['**/dbpasses*', 'config/**']` |
| Deploy to GitHub Pages | push, no paths | Already `.disabled` |

### Fix B: Add `timeout-minutes` to 95 workflows missing it
Default is 360 min — one stuck job occupies a runner for 6 hours. Recommended: 15–30 min for most, 60 max for heavy backtests.

### Fix C: Add concurrency groups to 200 workflows missing them
Without concurrency, every cron tick spawns a new run that stacks behind previous ones. Recommended: `group: ${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true` (except for persistent runners like Discord Bot).

## Safe Fixing Principles (from project conventions)

1. **Disable → observe → archive/delete.** Never mass-delete.
2. **Test on feature branches** — the repo has many branches for this.
3. **Prefer proper error handling** over `continue-on-error` / `|| true` that masks real problems.
4. **Keep the existing failure-guardian pattern** — make it smarter about "no subsequent success" and queue depth.
5. **When API rate-limited, use logged-in browser agents** for filter views.

## Recommended Next Step

**Start with Fix A (path filters)** — 3 active workflows, trivial YAML edits, immediate queue relief on every push. Then proceed to Fix B/C on high-frequency cron workflows.

Detailed data: `reports/gha_inventory_phase1.json`
