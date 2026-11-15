# FIX-005 — Sports smoke Playwright runner incompatibility

**File:** `.github/workflows/sports-smoke-and-e2e.yml`
**Severity:** P1
**Status:** Applied (branch `fix/gha-backup-verify-dedup-2026-11-15`, PR #790)

## What was broken
The `smoke` job runs Playwright e2e tests. It used `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. `ubuntu-latest` now resolves to **Ubuntu 26.04**, which Playwright 1.58.2 does not support:

```
BEWARE: your OS is not officially supported by Playwright; installing dependencies for ubuntu26.04-x64 as a fallback.
Cannot install dependencies for ubuntu26.04-x64 with Playwright 1.58.2!
Error: ERROR: Playwright does not support chromium on ubuntu26.04-x64
```

This made the job fail on every run (repeated failures all morning on 2026-11-15).

## What changed
Pinned the `smoke` job to `ubuntu-24.04` (the newest GitHub-hosted image Playwright 1.58.2 supports), while keeping the `vars.ACTIONS_RUNNER_LABEL` override for self-hosted runners.

## How to verify
- `yaml.safe_load` parses the workflow ✅
- Re-run "Sports endpoint smoke + Playwright" → `Install Playwright (chromium only)` step should succeed past browser install.
- If a repo variable `ACTIONS_RUNNER_LABEL` is set, behavior is unchanged (self-hosted still wins).

## Note
The `deploy-guard` job (line ~144) does not use Playwright and was left on `ubuntu-latest`.