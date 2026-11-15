# Recommended Fixes — GHACTIONS_PR_ISSUES

**Generated:** 2026-11-15T07:45Z UTC  
**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

---

## P0 — CRITICAL (Do Immediately — These Break Core Functionality)

### Fix 1: Add Missing GitHub Secrets for QA Market Validation

**Problem:** QA Market Validation workflow (`qa-market-validation.yml`) fails every hour because 5 API keys are not set as GitHub Secrets. Without them, 5 of 7 quote adapters return `None`, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky in GHA). Result: "ALL 7 sources failed" for every equity ticker.

**Fix:** Add these secrets to GitHub repo Settings → Secrets and variables → Actions:

| Secret Name | Description | Source |
|-------------|-------------|--------|
| `FINNHUB_API_KEY` | Finnhub API key for equity quotes | https://finnhub.io/ |
| `TIINGO_API_KEY` | Tiingo API key for equity quotes | https://www.tiingo.com/ |
| `TWELVE_DATA_API_KEY` | Twelve Data API key for equity quotes | https://twelvedata.com/ |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key for equity quotes | https://www.alphavantage.co/ |
| `FMP_API_KEY` | Financial Modeling Prep API key | https://site.financialmodelingprep.com/ |

**Related PR:** #786 `fix(ci): restore QA price validation, snapshot pushes, and sports smoke`  
**Related Workflow:** `.github/workflows/qa-market-validation.yml`  
**Related File:** `alpha_engine/equity_price_failover.py` (lines referencing adapters 2-6)

---

### Fix 2: Pin Sports Smoke Test to ubuntu-24.04

**Problem:** `sports-smoke-and-e2e.yml` uses `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}`. GitHub's `ubuntu-latest` now resolves to Ubuntu 26.04, which Playwright does not support ("Playwright does not support chromium on ubuntu26.04-x64"). The job dies at the install step, never running a single test.

**Fix:** Change `runs-on` in `.github/workflows/sports-smoke-and-e2e.yml` from:
```yaml
runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}
```
to:
```yaml
runs-on: ubuntu-24.04
```

Or set the `ACTIONS_RUNNER_LABEL` repo variable to `ubuntu-24.04`.

**Related PR:** #786 addresses this  
**Related Workflow:** `.github/workflows/sports-smoke-and-e2e.yml`  
**Related Issue:** Run 43689346545 failed at Playwright install step

---

### Fix 3: Fix Backup Restore Verification

**Problem:** `backup-verify.yml` fails monthly (15th at 06:00 UTC). There are ~30+ open issues titled "[backup-verify] Restore check FAILED" going back to August 2026.

**Files to check:**
- `audit_dashboard/data/dashboard_data.json` — must exist and be valid JSON
- `alpha_engine/data/recent_exits.json` — must exist
- `alpha_engine/data/recent_closed.json` — DOES NOT EXIST (referenced in code but missing)
- Python syntax of key engine files

**Action:** Investigate and fix the backup verify script. Check if `tools/backup_verify.py` or similar exists.

---

## P1 — HIGH PRIORITY (Do This Week)

### Fix 4: Merge PR #786 and #785

| PR | Title | What It Fixes |
|----|-------|---------------|
| #786 | fix(ci): restore QA price validation, snapshot pushes, and sports smoke | Adds 5 API secrets; pins sports smoke to ubuntu-24.04 |
| #785 | Restore audit page script tags lost on main + tracker horizon fix | Restores `excess_column.js` / `forward_clock.js` script tags; fixes tracker horizon |

Both PRs are from `eltonaguiar` and are ready to merge.

---

### Fix 5: Fix CI Concurrency Causing Cancelled Runs

**Problem:** `ci-tests.yml` uses:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.sha }}
  cancel-in-progress: false
```
Since every push has a different SHA, every push starts a new CI run. With "storm-commit" behavior (many rapid commits), CI Tests are constantly cancelled and restarted, never completing.

**Fix:** Change concurrency group to use branch instead of SHA:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This cancels stale runs on the same branch when a new push arrives, ensuring only the latest code is tested.

---

### Fix 6: Add CODEOWNERS File

**Problem:** No CODEOWNERS file exists, so PRs don't get automatic reviewer assignment.

**Fix:** Create `.github/CODEOWNERS`:
```
# Code owners
*       @eltonaguiar
/docs/    @eltonaguiar
/tests/   @eltonaguiar
/alpha_engine/  @eltonaguiar
/audit_trail/   @eltonaguiar
```

---

### Fix 7: Add Dependabot Config

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

### Fix 8: Add CONTRIBUTING.md and CODE_OF_CONDUCT.md

**Problem:** No contribution guidelines or code of conduct visible in repo root.

**Fix:** Create both files with standard templates.

---

## P2 — MEDIUM PRIORITY (Do This Month)

### Fix 9: Review and Merge or Close 40+ Open PRs

Many PRs from October 2026 are still open:
- #766, #765, #763, #762 (Nov 2026 docs)
- #761, #760, #759 (Oct 2026 fixes)
- #758, #757, #756 (Oct 2026 fixes)
- #751 (Oct 2026 CI health monitor)
- #750 (Oct 2026 Nemotron money ready)
- #749, #747, #746, #745, #744 (Oct 2026 fixes)
- #736, #735 (Oct 2026 fixes)
- #713, #711 (Oct 2026 CI/audit fixes)
- #701, #700, #696 (Oct 2026 fixes)
- #667, #666, #665, #657 (June 2026 features)

**Action:** Review each PR. Merge if ready, close if stale or superseded.

---

### Fix 10: Review and Close Stale Issues

~50 open issues, dominated by:
- `[backup-verify] Restore check FAILED` — ~30+ issues from Aug-Nov 2026
- `[Security] Monthly Secret Rotation Reminder` — monthly recurring
- `#748` Production resolver predates `_priceless_close`

**Action:** Triage backup-verify issues. If the root cause is fixed, close all related issues.

---

### Fix 11: Review Disabled/Retired Workflows

17 workflows are disabled or retired:
- `audit-dashboard.yml.disabled`
- `alpha-engine-alpha-suite-daily-refresh.yml.disabled`
- `fast-variants-master.yml.disabled`
- `ml-battleground-a.yml.retired` through `f.yml.retired`
- `ml-battleground-monitor.yml.retired`
- `paper-trading.yml.retired`
- `rl-agent-ppo.yml.retired`

**Action:** Review each. Either re-enable (if still needed) or delete (if truly retired).

---

### Fix 12: Review `.github/workflows/*.yml.disabled` Files

Same as above — disabled workflows that may need attention.

---

## P3 — LOW PRIORITY (Do This Quarter)

### Fix 13: Add CODE_OF_CONDUCT.md

Community guidelines for contributors.

### Fix 14: Add CONTRIBUTING.md

Documentation for how to contribute to the repo.

### Fix 15: Add Dependabot for All Package Ecosystems

Currently no dependabot config. Add for pip, npm, etc.

### Fix 16: Review All `*.disabled` and `*.retired` Workflow Files

Decide to re-enable or permanently delete each one.

---

## 8. Quick Wins (Can Be Done in <30 Minutes Each)

1. ✅ Add CODEOWNERS file
2. ✅ Add Dependabot config
3. ✅ Add CONTRIBUTING.md
4. ✅ Add CODE_OF_CONDUCT.md
5. Set the 5 missing API secrets (FINNHUB_API_KEY, etc.)
6. Pin sports smoke test to ubuntu-24.04
7. Fix CI concurrency group
8. Review and merge PR #786 and #785
9. Close stale backup-verify issues once root cause is fixed
10. Review disabled workflows

---

## 9. Files Changed/Created in This Audit

| File | Purpose |
|------|---------|
| `GHACTIONS_PR_ISSUES/2026-11-15T0745Z_gh-actions-pr-issues/GHACTIONS_PR_ISSUES_REPORT.md` | This report |
| `WIRED_IN/` | Various worktrees with research and analysis |
| `WIRED_IN/2026-11-15_0700_scratch-hippodraco/` | Quant research worktree with Summary.MD |
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/` | Quant research prompt kit |

---
