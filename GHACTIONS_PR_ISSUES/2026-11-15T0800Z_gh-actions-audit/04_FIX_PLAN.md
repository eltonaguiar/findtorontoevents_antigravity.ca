# Fix Plan — GHActions / PR / Issues Remediation

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-15T08:00Z UTC
**Based on:** GHACTIONS_PR_ISSUES_REPORT.md, 01_GITHUB_ACTIONS_AUDIT.md, 02_OPEN_PRS.md, 03_OPEN_ISSUES.md

---

## P0 — Critical Fixes (Do Immediately)

### Fix 1: Add Missing GitHub API Secrets for QA Market Validation

**Problem:** QA Market Validation workflow (`qa-market-validation.yml`) fails every hour because 5 API keys are not set as GitHub Secrets. Adapters 2-6 return `None`, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky in GHA). Result: "ALL 7 sources failed" for every equity ticker.

**Files affected:**
- `.github/workflows/qa-market-validation.yml` (lines 43-51 reference the missing secrets)

**Secrets to add (GitHub repo Settings → Secrets and variables → Actions):**
| Secret Name | Purpose |
|-------------|---------|
| `FINNHUB_API_KEY` | Finnhub API key for equity quotes |
| `TIINGO_API_KEY` | Tiingo API key for equity quotes |
| `TWELVE_DATA_API_KEY` | Twelve Data API key for equity quotes |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key for equity quotes |
| `FMP_API_KEY` | Financial Modeling Prep API key |

**Evidence:**
- Workflow run #43693232126 failed at step "Run QA ledger" (step 5 of 11)
- Workflow comments explicitly state: "Without these keys this job cannot validate PnL, so it fails every hour forever."
- Run 43688541491 produced "fetch_quote(<ticker>): ALL 7 sources failed" for every equity ticker

**How to apply:**
1. Go to https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/secrets/actions
2. Click "New repository secret" for each of the 5 keys above
3. Enter the key name and value

---

### Fix 2: Pin Sports Smoke Test to ubuntu-24.04

**Problem:** `sports-smoke-and-e2e.yml` uses `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. GitHub's `ubuntu-latest` now resolves to Ubuntu 26.04, and Playwright does not support Chromium on Ubuntu 26.04.

**Files affected:**
- `.github/workflows/sports-smoke-and-e2e.yml` (line: `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`)

**Fix:** Change line:
```yaml
runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
```
to:
```yaml
runs-on: ubuntu-24.04
```

Or set `ACTIONS_RUNNER_LABEL` repo variable to `ubuntu-24.04`.

**Evidence:**
- Run 43689346545 failed at install step with "Playwright does not support chromium on ubuntu26.04-x64"
- Workflow comment explicitly warns: "Pinned: `ubuntu-latest` now resolves to 24.04→26.04, and Playwright's browser download refuses 26.04 outright"

**Related PR:** #786

---

### Fix 3: Merge PR #786

**PR:** `fix(ci): restore QA price validation, snapshot pushes, and sports smoke`
**Branch:** `wired-in/buffy-gh-actions-fix-2026-11-15` → `main`
**Author:** eltonaguiar
**Created:** 2026-11-15T07:33:21Z

**What it fixes:**
1. Adds 5 missing API secrets (FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY)
2. Pins sports smoke test to ubuntu-24.04
3. Restores QA price validation and snapshot pushes

**Evidence:** PR body documents the exact fixes with workflow run numbers and error messages.

**Action:** Merge this PR immediately — it addresses the two most critical failing workflows.

---

## P1 — Do This Week

### Fix 4: Merge PR #785

**PR:** `Restore audit page script tags lost on main + tracker horizon fix`
**Branch:** `wired-in/buffy-2026-11-15-final` → `main`
**Author:** eltonaguiar
**Created:** 2026-11-15T07:26:36Z

**What it fixes:**
- Restores `excess_column.js` / `forward_clock.js` script tags in `audit_dashboard/template.html`
- Fixes tracker horizon issue: mixed naive/aware timestamps raised TypeError, leaving 3,500 rows NOT MEASURED; 3,392/3,500 now measured

**Action:** Merge this PR — restores critical audit dashboard functionality.

---

### Fix 5: Fix CI Concurrency Group

**Problem:** `ci-tests.yml` uses:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.sha }}
  cancel-in-progress: false
```

Since every push has a different SHA, every push starts a new CI run. With "storm-commit" behavior (many rapid commits), CI Tests are constantly being cancelled and restarted, never completing.

**Fix:** Change to:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**Files affected:** `.github/workflows/ci-tests.yml`

**Evidence:**
- Workflow comment acknowledges: "Storm-commit repo: without a path filter EVERY push (incl. docs/report/ data commits) triggered the full 747-test suite, and the next push cancelled it via concurrency — ~18/19 runs cancelled, CI never a gate."
- 30+ cancelled CI Tests runs visible in `gh run list --status cancelled`

---

### Fix 6: Investigate Backup Restore Verification Failures

**Problem:** `backup-verify.yml` fails monthly (15th at 06:00 UTC). ~30+ open issues titled "[backup-verify] Restore check FAILED" from August 2026 to November 2026.

**Files affected:** `.github/workflows/backup-verify.yml`

**Investigation needed:**
1. Check if `audit_dashboard/data/dashboard_data.json` exists and is valid JSON
2. Check if `alpha_engine/data/recent_exits.json` exists and is valid JSON
3. Check if critical files exist: `alpha_engine/data/recent_exits.json`, `alpha_engine/data/ml_health_status.json`, `audit_dashboard/data/pcg5_log.json`
4. Check Python syntax of key engine files

**Related issues:** #787, #783, #782, #781, #780, #728-721, #694-668, #686-676, #674-668

---

### Fix 7: Add CODEOWNERS file

**Problem:** No CODEOWNERS file exists, so PRs don't get automatic reviewer assignment.

**Fix:** Create `.github/CODEOWNERS`:
```yaml
# Code owners
*       @eltonaguiar
/docs/    @eltonaguiar
/tests/   @eltonaguiar
/alpha_engine/  @eltonaguiar
/audit_trail/   @eltonaguiar
```

---

### Fix 8: Add Dependabot config

**Problem:** No automated dependency updates.

**Fix:** Create `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

---

### Fix 9: Add CONTRIBUTING.md and CODE_OF_CONDUCT.md

**Problem:** No contribution guidelines or code of conduct visible in repo root.

**Fix:** Create both files with standard templates.

---

## P2 — Do This Month

| # | Action |
|---|--------|
| 10 | Review and merge or close 30+ open PRs |
| 11 | Triage ~50 open issues |
| 12 | Review 17 disabled/retired workflows |
| 13 | Review 40+ open PRs for relevance |

---

## Deployment Instructions

### Fix 1 (API Secrets) — Via GitHub UI only

1. Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/secrets/actions
2. Click "New repository secret" for each key:
   - `FINNHUB_API_KEY`
   - `TIINGO_API_KEY`
   - `TWELVE_DATA_API_KEY`
   - `ALPHA_VANTAGE_API_KEY`
   - `FMP_API_KEY`
3. Enter each key name and value
4. Click "Add secret"

**Verification:** After adding secrets, trigger the QA Market Validation workflow manually:
- Go to https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/qa-market-validation.yml
- Click "Run workflow"
- Verify it passes

### Fix 2 (Sports smoke pin) — Via git commit

1. Edit `.github/workflows/sports-smoke-and-e2e.yml`
2. Change `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}` to `runs-on: ubuntu-24.04`
3. Commit and push to main

### Fix 3 (PR #786) — Via GitHub UI or CLI

1. Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/786
2. Click "Merge pull request"
3. Or via CLI: `gh pr merge 786 --merge --admin`

### Fix 4 (PR #785) — Via GitHub UI or CLI

1. Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/785
2. Click "Merge pull request"
3. Or via CLI: `gh pr merge 785 --merge --admin`

### Fix 5 (CI concurrency) — Via git commit

1. Edit `.github/workflows/ci-tests.yml`
2. Change:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.sha }}
     cancel-in-progress: false
   ```
   to:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
3. Commit and push to main

---

## Success Criteria

| Fix | Success Metric |
|-----|----------------|
| QA API secrets | QA Market Validation workflow passes on next hourly run |
| Sports smoke pin | Sports smoke test passes on next hourly run |
| PR #786 merged | Both QA and Sports workflows pass on main |
| PR #785 merged | Audit dashboard script tags restored |
| CI concurrency | CI Tests complete without cancellation on push |
| Backup verify | Monthly backup verify passes |
| CODEOWNERS | PRs auto-assign to reviewers |
| Dependabot | Automated dependency PRs created |
