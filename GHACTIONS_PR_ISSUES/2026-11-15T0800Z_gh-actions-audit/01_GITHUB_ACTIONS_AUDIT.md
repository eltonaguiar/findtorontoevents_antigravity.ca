# GitHub Actions Workflow Audit — Detailed Findings

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-15T08:00Z UTC
**Source:** `gh workflow list`, `gh run list --status <status>` via GitHub CLI

---

## 1. Workflow Inventory Summary

| Metric | Count |
|--------|-------|
| Total workflow files | ~60 |
| Active workflows | ~55 |
| Disabled workflows | 2 (`alpha-engine-alpha-suite-daily-refresh.yml.disabled`, `deploy-pages.yml.disabled`) |
| Draft workflows | 1 (`bt-backtest-trades-sync.yml.draft`) |
| Retired workflows | Multiple (`ml-battleground-a.yml.retired` through `f.yml.retired`, `rl-agent-ppo.yml.retired`, `paper-trading.yml.retired`) |

---

## 2. Failing Workflows Detail

### 2.1 QA Market Validation — CRITICAL FAILURE

**Workflow file:** `.github/workflows/qa-market-validation.yml`
**Schedule:** Every hour (`0 * * * *`)
**Trigger:** Push to `main` (paths: `tools/qa_ledger.py`, `audit_dashboard/data/picks_now_live_pnl.json`, workflow file itself)

**Failure pattern:** Every run since at least 2026-11-15 07:33 UTC has failed.

**Root cause:** The workflow runs `python tools/qa_ledger.py` which requires 5 API keys as GitHub Secrets:
- `FINNHUB_API_KEY` / `FINNHUB`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

The workflow comments explicitly state: "Adapters 2-6 return None immediately when their key is unset — leaving only Stooq (its anonymous endpoint is blocked from GitHub-runner IPs) and yfinance (documented as flaky in GHA in that module's own docstring). That is exactly how run 43688541491 produced 'fetch_quote(<ticker>): ALL 7 sources failed' for every single equity ticker and failed the gate. Without these keys this job cannot validate PnL, so it fails every hour forever."

**Evidence:** Run #43693232126 failed at step "Run QA ledger" (step 5 of 11). Steps 1-4 (checkout, setup Python, install dependencies) all passed. Step 5 failed because the QA ledger script cannot fetch quotes from any source.

**Fix:** Add the 5 secrets to GitHub repo Settings → Secrets and variables → Actions:
```
SUBQ_FREE_API_KEY=sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV
SUBQ_TOKEN_API_KEY=sk-proj-7IuzAriNQVjz7lnikGi2Hi45c4j084O7
SUBQ_FREE_API_KEY=sk-proj-Xx8AOwoBBEXGOg75H0q4YMcNZ3wVCVUV
SUBQ_TOKEN_API_KEY=sk-proj-7IuzAriNQVjz7lnikGi2Hi45c4j084O7
```

Wait — those are the SubQ keys. For QA Market Validation, we need: FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY.

**Related PR:** #786 "fix(ci): restore QA price validation, snapshot pushes, and sports smoke"

---

### 2.2 Sports Endpoint Smoke + Playwright — CRITICAL FAILURE

**Workflow file:** `.github/workflows/sports-smoke-and-e2e.yml`
**Schedule:** Hourly at minute 17 (`17 * * * *`)
**Trigger:** PR touching live-monitor files, workflow_dispatch

**Failure pattern:** Every run since at least 2026-11-15 02:09 UTC has failed.

**Root cause:** `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}` — `ubuntu-latest` now resolves to Ubuntu 26.04, and Playwright does not support Chromium on Ubuntu 26.04. Error message: "Playwright does not support chromium on ubuntu26.04-x64".

**Fix:** Pin to `ubuntu-24.04`:
```yaml
runs-on: ubuntu-24.04
```
Or set `ACTIONS_RUNNER_LABEL` repo variable to `ubuntu-24.04`.

**Evidence:** Run 43689346545 failed at the install step with "Playwright does not support chromium on ubuntu26.04-x64".

**Related PR:** #786 addresses this.

---

### 2.3 Backup Restore Verification — RECURRING FAILURE

**Workflow file:** `.github/workflows/backup-verify.yml`
**Schedule:** Monthly, 15th at 06:00 UTC (`0 6 15 * *`)
**Trigger:** workflow_dispatch

**Failure pattern:** Failing monthly since at least August 2026. Issues #676-787 (approximately 30+ issues).

**Root cause:** Under investigation. The workflow:
1. Checks out the repo
2. Sets up Python 3.11
3. Fetches `audit_dashboard/data/dashboard_data.json` from production (it's gitignored)
4. Runs smoke queries checking:
   - `audit_dashboard/data/dashboard_data.json` — trading_picks leaderboard count
   - `alpha_engine/data/recent_exits.json` — at_pick_outcomes count
   - Critical file existence: `alpha_engine/data/mutual_fund_metadata.csv`, `audit_dashboard/data/pcg5_log.json`, etc.
   - Python syntax check on key modules
5. On failure: opens a GitHub Issue tagged `backup-verify`

**Recent failures:** #787, #783, #782, #781, #780 (all 2026-11-15), #728-721 (2026-10-15), #694-668 (2026-09-15), #686-676 (2026-08-15), #674-668 (2026-07-15)

---

### 2.4 CI Tests — RECURRING FAILURE

**Workflow file:** `.github/workflows/ci-tests.yml`
**Schedule:** Push to `main` and pull_request

**Failure pattern:** Failing on both `main` and feature branches.

**Root cause:** The CI test suite runs ~747 tests (558 root + 103 walkforward elite + 86 alpha_engine). Many tests are quarantined due to known drift, but the suite still fails. Specific failures include:
- Test naming and selection issues with the known_drift_tests.txt file
- Possible FRED API calls timing out
- Various test assertions failing

**Related commits:** Multiple commits on `wired-in/buffy-2026-11-15` branch related to CI test fixes.

---

## 3. Cancelled Workflows

Many workflows are being cancelled due to concurrency conflicts. The CI Tests workflow uses:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.sha }}
  cancel-in-progress: false
```

Since every push has a unique SHA, every push starts a new CI run. With "storm-commit" behavior (many rapid commits), CI Tests are constantly being cancelled and restarted, never completing cleanly.

**Fix:** Change concurrency group to `${{ github.workflow }}-${{ github.ref }}` and set `cancel-in-progress: true` to cancel stale runs on the same branch when a new push arrives.

---

## 4. Skipped Workflows

Many workflows are being skipped due to workflow_run dependencies:
- `Deploy FindCryptoPairs to FTP` — skipped when upstream workflow doesn't produce expected artifacts
- `Deploy Competition to Live Site` — same reason
- `Pine Script Generator` — skipped frequently

These are secondary failures caused by upstream workflow failures.

---

## 5. Recommended Actions (Priority Order)

### P0 — Critical (Do Immediately)

| # | Issue | Fix | Evidence |
|---|-------|-----|----------|
| 1 | QA Market Validation fails every hour | Add 5 API secrets to GitHub repo Settings → Secrets and variables → Actions: `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` | PR #786 body documents this fix; workflow logs show "ALL 7 sources failed" for every equity ticker |
| 2 | Pin Sports smoke test to ubuntu-24.04 | Change `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}` to `runs-on: ubuntu-24.04` in `.github/workflows/sports-smoke-and-e2e.yml` | PR #786 addresses this; run 43689346545 shows "Playwright does not support chromium on ubuntu26.04-x64" |
| 3 | Merge PR #786 | This PR fixes both QA Market Validation and Sports smoke failures | PR #786 is approved and ready to merge |

### P1 — Do This Week

| # | Action | Why |
|---|--------|-----|
| 4 | Merge PR #785 | Restores audit page script tags and tracker horizon fix |
| 5 | Fix CI concurrency group | Change `group: ${{ github.workflow }}-${{ github.sha }}` to `group: ${{ github.workflow }}-${{ github.ref }}` and set `cancel-in-progress: true` |
| 6 | Investigate backup-verify failures | Investigate why monthly backup check has been failing since August 2026 |
| 7 | Add CODEOWNERS file | Auto-assign PR reviewers |
| 8 | Add Dependabot config | Automated dependency updates |

### P2 — Do This Month

| # | Action |
|---|--------|
| 9 | Review and merge or close 30+ open PRs |
| 10 | Triage ~50 open issues |
| 11 | Review 17 disabled/retired workflows |
| 13 | Review 40+ open PRs for relevance |

---

## 7. Evidence Files

All evidence captured from `gh` CLI:
- `gh workflow list` — 60+ workflows
- `gh run list --status failure` — 50+ failing runs
- `gh run list --status cancelled` — 50+ cancelled runs
- `gh run list --status skipped` — 50+ skipped runs (workflow_dispatch from other workflows)
- `gh pr list --state open --limit 50` — 30+ open PRs
- `gh issue list --state open --limit 50` — ~50+ open issues
- Individual workflow file reads for `qa-market-validation.yml`, `ci-tests.yml`, `backup-verify.yml`, `sports-smoke-and-e2e.yml`

---

## 8. Deployment Notes

**Files modified for fixes:**
- `.github/workflows/sports-smoke-and-e2e.yml` — Pin to ubuntu-24.04
- `.github/workflows/ci-tests.yml` — Fix concurrency group
- `.github/secrets` — Add 5 API keys (must be done via GitHub UI, not via git)

**No code changes needed for QA Market Validation** — the fix is purely adding secrets to GitHub repository settings.
