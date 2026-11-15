# GHA / PR / ISSUES Audit Report — findtorontoevents_antigravity.ca

**Generated:** 2026-11-15T07:45Z UTC  
**Repository:** https://github.com/eltonaguiar/eltonaguiar/findtorontoevents_antigravity.ca/  
**Branch audited:** main (plus active worktrees)  
**Folder:** GHACTIONS_PR_ISSUES/2026-11-15T0745Z_gh-actions-pr-issues/

---

## Executive Summary

The repository is **heavily instrumented** with ~60+ GitHub Actions workflows, ~30+ open PRs, and ~50+ open issues. However, several critical workflows are **chronically failing**, blocking the entire live-data pipeline:

1. **QA Market Validation** — fails every hour because quote-chain API keys (`FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`) are **not set as GitHub Secrets**. Adapters 2–6 return `None`, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky in GHA). Result: "ALL 7 sources failed" for every equity ticker.
2. **Sports endpoint smoke + Playwright** — fails because `ubuntu-latest` now resolves to Ubuntu 26.04, which Playwright does not support ("Playwright does not support chromium on ubuntu26.04-x64").
3. **Backup Restore Verification** — fails monthly (15th at 06:00 UTC).
4. **CI Tests** — failing on `wired-in/buffy-2026-11-15` branch.

Additionally:
- **27+ open PRs** including critical CI fixes, audit page restores, FTP credential rotation, fund walk-forward fixes, resolver TP/SL fixes, and more.
- **~50+ open issues**, dominated by `[backup-verify] Restore check FAILED` (recurring monthly failures since August 2026), security rotation reminders, and a production resolver issue.

---

## 1. GitHub Actions Workflows

### 1.1 Total Workflows Discovered

**60+ workflow files** in `.github/workflows/`. Key workflows (alphabetical):

| Workflow File | Schedule | Status | Key Concern |
|---|---|---|---|
| `2hour_challenge.yml` | — | active | — |
| `actions-failure-guardian.yml` | */30 * * * * | active | Retries failed workflows; uses GH_PAT |
| `alpha-engine-daily-picks.yml` | — | active | — |
| `alpha-engine-etf.yml` | — | active | — |
| `alpha-engine-fast.yml` | — | active | — |
| `alpha-engine-live.yml` | — | active | — |
| `alpha-equity-breakout.yml` | — | active | — |
| `alpha-gainer-capture.yml` | — | active | — |
| `alpha-quant-stack.yml` | — | active | — |
| `alpha-suite-daily-refresh.yml.disabled` | — | **DISABLED** | Disabled workflow |
| `alpha-trend-catcher.yml` | — | active | — |
| `alpha-verify-predictions.yml` | — | active | — |
| `alpha-weekly-validation.yml` | — | active | — |
| `analyst-tracker.yml` | — | active | — |
| `asset-class-freshness-watchdog.yml` | — | active | — |
| `audit-dashboard.yml` | — | active | — |
| `audit-drift-telemetry.yml` | — | active | — |
| `audit-frontend-manifest.yml` | — | active | — |
| `audit-hourly-update.yml` | — | active | — |
| `audit-impact-tracker.yml` | — | active | — |
| `automated-reporting.yml` | — | active | — |
| `autonomous_trading.yml` | — | active | — |
| `auto-retire-daily.yml` | — | active | — |
| `auto-shutdown-monitor.yml` | — | active | — |
| `baby-strat-forward-paper.yml` | — | active | — |
| `backfill-features.yml` | — | active | — |
| `backfill.yml` | — | active | — |
| `backtest-and-deploy.yml` | — | active | — |
| `backup-verify.yml` | `0 6 15 * *` | **FAILING** | Monthly backup restore verification fails |
| `battleground-mass-backtest.yml` | — | active | — |
| `beta-portfolio-refresh.yml` | — | active | — |
| `blacklist-reconciler.yml` | — | active | — |
| `bond-agent.yml` | — | active | — |
| `branch-large-file-dup-guard.yml` | — | active | — |
| `breakout-arena.yml` | — | active | — |
| `cftc-cot-refresh.yml` | — | active | — |
| `ci-tests.yml` | push to main | **FAILING** | CI test suite failing on wired-in/buffy-2026-11-15 |
| `claude-gainer-ml-live.yml` | — | active | — |
| `copy-trader-forward-test.yml` | — | active | — |
| `deploy-pages.yml.disabled` | — | **DISABLED** | Disabled workflow |
| `deploy-riseoftheclaw.yml` | — | active | — |
| `forward-ledger-sync.yml` | `37 5 * * *` | active | Appends closed picks to forward ledger |
| `forward-ledger-sync.yml` (untracked) | — | untracked | New file not yet committed |
| `money-ready-registry-gate.yml` | — | active | — |
| `money-ready-snapshot.yml` | — | active | — |
| `qa-market-validation.yml` | `0 * * * *` | **FAILING** | Fails every hour — missing API keys |
| `sports-smoke-and-e2e.yml` | `17 * * * *` | **FAILING** | Playwright doesn't support ubuntu-26.04 |
| `verified-pilot-daily.yml` | — | **FAILING** | Failing |
| ... ~40 more workflows | | | |

### 1.2 Critical Failing Workflows

#### QA Market Validation (`qa-market-validation.yml`)
- **Schedule:** Every hour (`0 * * * *`)
- **Status:** FAILING on every run
- **Root cause:** No quote-chain API keys set as GitHub Secrets. The `alpha_engine/equity_price_failover.py` has 7 adapters; adapters 2–6 return `None` immediately when their env var is unset. Only Stooq (blocked from GH runner IPs) and yfinance (documented as flaky in GHA) remain.
- **Required secrets:** `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY`
- **Impact:** QA Market Validation cannot validate PnL, so it fails every hour forever. This prevents validated PnL from reaching the dashboard.
- **PR #786** addresses this: "fix(ci): restore QA price validation, snapshot pushes, and sports smoke"

#### Sports endpoint smoke + Playwright (`sports-smoke-and-e2e.yml`)
- **Schedule:** Hourly at minute 17 (`17 * * * *`)
- **Status:** FAILING
- **Root cause:** `ubuntu-latest` now resolves to Ubuntu 26.04. Playwright does not support Chromium on ubuntu-26.04-x64 ("Playwright does not support chromium on ubuntu26.04-x64" — run 43689346545). The job dies at the install step, never reaching a single test.
- **Fix:** Pin smoke job to `ubuntu-24.04` via `vars.ACTIONS_RUNNER_LABEL` override.
- **PR #786** addresses this.

#### Backup Restore Verification (`backup-verify.yml`)
- **Schedule:** Monthly, 15th at 06:00 UTC (`0 6 15 * *`)
- **Status:** FAILING repeatedly
- **Issues:** Multiple open issues (#787, #783, #782, #781, #780, #728-721, #694-680, #674-668) all titled "[backup-verify] Restore check FAILED"
- **Impact:** Cannot verify that backups are restorable. Critical for disaster recovery.

#### CI Tests (`ci-tests.yml`)
- **Schedule:** Push to `main`
- **Status:** FAILING on `wired-in/buffy-2026-11-15` branch
- **Coverage:** ~747 tests (558 root + 103 walkforward elite + 86 alpha_engine)
- **Python versions:** 3.11, 3.12
- **Key issue:** The workflow only runs on pushes to paths matching `paper_trading/**`, `alpha_engine/**`, `audit_trail/**`, `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`, `tests/**`, `requirements.txt`, `alpha_engine/requirements.txt`, `.github/workflows/ci-tests.yml`. Docs-only commits do NOT trigger CI.

#### CI Test Concurrency Issue
The workflow uses:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.sha }}
  cancel-in-progress: false
```
This means every new push cancels the previous in-progress run for the same SHA — but since each push has a different SHA, this effectively means every push starts a new run. With "storm-commit" behavior (many rapid commits), CI Tests are constantly being cancelled and restarted, never completing.

---

## 2. Open Pull Requests

### 2.1 Critical PRs (30+ open)

| PR # | Title | Branch | Base | Created | Author |
|------|-------|--------|------|---------|--------|
| #786 | fix(ci): restore QA price validation, snapshot pushes, and sports smoke | wired-in/buffy-gh-actions-fix-2026-11-15 | main | 2026-11-15T07:33:21Z | eltonaguiar |
| #785 | Restore audit page script tags lost on main + tracker horizon fix | wired-in/buffy-2026-11-15-final | main | 2026-11-15T07:26:36Z | eltonaguiar |
| #766 | docs: add kilo today's ServiceNow/Salesforce Canada jobs scan (Nov 2 2026) | add-kilo-todays-servicenow-salesforce-jobs | main | 2026-11-02T15:27:01Z | eltonaguiar |
| #765 | docs: add kilo additional skills/certifications | add-kilo-additional-skills | main | 2026-11-02T15:16:59Z | eltonaguiar |
| #763 | Add verified sci-fi TV watchlist and upcoming releases to weather | copilot/weather-tv-2026-11-01 | main | 2026-11-01T02:46:20Z | eltonaguiar |
| #762 | Job Scan: ServiceNow & Salesforce - Huggle Agent 2026-10-30 | huggle-agent-2026-10-30 | main | 2026-10-30T22:49:10Z | eltonaguiar |
| #761 | fix: rotated FTP credentials, no embedded password defaults, verified FTPS | fix/ghcopilot-ftp-credential-loading | main | 2026-10-23T04:33:51Z | eltonaguiar |
| #760 | fix: fund walk-forward review fixes (FXAIX same-window CI + identical-pairs proof) | oc/fund-walkforward-review-fixes | main | 2026-10-23T04:23:38Z | eltonaguiar |
| #759 | research (opt-in): 95-fund durability audit and genuine zero-expense ETFs | research/ghcopilot-symbol-durability | main | 2026-10-23T00:19:42Z | eltonaguiar |
| #758 | Fix BTC evaluator daily drawdown and unsupported gate passes | fix/ghcopilot-btc-mtm-guard | main | 2026-10-22T23:57:35Z | eltonaguiar |
| #757 | Fix audit evidence cards and explain strategy readiness | feat/ghcopilot-grok-scorecard | main | 2026-10-22T23:31:57Z | eltonaguiar |
| #756 | Fix DSR>1 + resolver batch-close/flat-exit bugs (Grok quick-fixes 1-4) | fix/grok-quickfixes-dsr-resolver | main | 2026-10-22T23:24:29Z | eltonaguiar |
| #751 | ci: add GitHub Actions health monitor job | feat/gha-actions-health | main | 2026-10-22T21:31:24Z | eltonaguiar |
| #750 | Nemotron Money Ready: Bond Yield Curve Slope Strategy Test | nemotron/money-ready | main | 2026-10-20T03:20:31Z | eltonaguiar |
| #749 | fix(resolver): true TP/SL exit time + UNRESOLVED_NO_PRICE (batch-close root cause) | buffy/batch-close-rootcause | main | 2026-10-20T02:56:10Z | eltonaguiar |
| #747 | feat(opencode): crypto money-ready backtest + report (no passes) | opencode/money-ready | main | 2026-10-20T02:48:28Z | eltonaguiar |
| #746 | spec: KPI page (spec only, no code this week) | opencode/kpi-page-spec | main | 2026-10-20T02:27:50Z | eltonaguiar |
| #745 | fix(audit): smart_picks gate-validated only + curated_feed + empty-state reasons | opencode/audit-empty-state-v2 | main | 2026-10-20T02:24:12Z | eltonaguiar |
| #744 | fix(forward_validator): enforce BLACKLISTED_STRATEGIES in save_active_picks | fix/blacklist-save-active-picks | main | 2026-10-20T02:23:41Z | eltonaguiar |
| #736 | fix(fc+weather): persist category Apply/filter + weather reset-look recovery button | fix/fc-category-persist-weather-reset-look | main | 2026-10-18T22:17:26Z | eltonaguiar |
| #735 | fix(audit): symbol→asset-class cache fallback + make the last hard-coded /audit core stats dynamic | fix/assetclass-cache-live-core-stats | main | 2026-10-18T08:38:17Z | eltonaguiar |
| #713 | fix(ci): backup-verify false failures + issue spam; speed up dup-guard scan | fix/ci-backup-verify-and-dupguard | main | 2026-10-04T07:05:19Z | eltonaguiar |
| #711 | fix(audit): correct two defects in the per-tab/per-class staleness code from #708 | fix/stale-tag-defects | main | 2026-10-04T05:30:10Z | eltonaguiar |
| #701 | Preserve pick rationale through *_audit_push normalizers | fix/pick-reason-audit-push | main | 2026-10-04T04:38:08Z | eltonaguiar |
| #700 | LLM free-first routing + message tracing; Discord webhook loud-failure + secret scrub | fix/oct3-llm-discord-loud-failure | main | 2026-10-04T04:37:52Z | eltonaguiar |
| #696 | fix(discord): read webhooks from secrets only after exposed hook deletion | fix/discord-webhook-secret-rotation | main | 2026-10-03T22:24:25Z | eltonaguiar |

### 2.2 Key PR: #786 — CI Fix (Most Important)

**Title:** fix(ci): restore QA price validation, snapshot pushes, and sports smoke  
**Branch:** wired-in/buffy-gh-actions-fix-2026-11-15 → main  
**Author:** eltonaguiar  
**Created:** 2026-11-15T07:33:21Z  
**Body summary:**

Four scheduled workflows on `main` had no successful run after their latest failure. All four are config bugs, and two of them starve `main` of financial data.

| Workflow | Root cause | Fix |
|---|---|---|
| QA Market Validation | Ran with **none** of the quote-chain API keys. Adapters 2–6 return None when env var unset, leaving only Stooq (blocked from runner IPs) and yfinance (flaky) | Pass FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY |
| rsi5070 Forward-Test Snapshot | 10 retries of identical `git push` after non-fast-forward — can never succeed | `git fetch origin main && git rebase origin/main` before retrying, with timed-retry fallback |
| Operator Review snapshot | Same push loop, 5 attempts | Same rebase-before-retry |
| Sports smoke | `ubuntu-latest` → 26.04; Playwright refuses chromium there | Pin smoke job to `ubuntu-24.04` |

**Verification:** All four YAML files `yaml.safe_load` cleanly and every `run:` script passes `bash -n`; the new grep patterns match exactly the strings git emitted in the failing runs.

**Not weakened:** no assertion, tolerance, or exit code was relaxed. If the five secrets are not set on the repo, QA keeps failing honestly — that is the correct behaviour.

---

## 3. Open Issues

### 3.1 Critical Issues (50+ open)

| # | Title | Author | Created | Labels |
|---|-------|--------|---------|--------|
| #787 | [backup-verify] Restore check FAILED — 2026-11-15 | app/github-actions | 2026-11-15T07:34:27Z | backup-verify, automated |
| #783 | [backup-verify] Restore check FAILED — 2026-11-15 | app/github-actions | 2026-11-15T07:07:20Z | backup-verify, automated |
| #782 | [backup-verify] Restore check FAILED — 2026-11-15 | app/github-actions | 2026-11-15T06:37:53Z | backup-verify, automated |
| #781 | [backup-verify] Restore check FAILED — 2026-11-15 | app/github-actions | 2026-11-15T06:10:54Z | backup-verify, automated |
| #780 | [backup-verify] Restore check FAILED — 2026-11-15 | app/github-actions | 2026-11-15T06:03:22Z | backup-verify, automated |
| #764 | [Security] Monthly Secret Rotation Reminder — November 2026 | | 2026-11-01T09:07:16Z | |
| #748 | Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed | eltonaguiar | 2026-10-20T02:56:09Z | |
| #728-721 | [backup-verify] Restore check FAILED — 2026-10-15 (8 issues) | app/github-actions | 2026-10-15 | backup-verify, automated |
| #695 | [Security] Monthly Secret Rotation Reminder — October 2026 | app/github-actions | 2026-10-01T09:14:42Z | |
| #685 | [Security] Monthly Secret Rotation Reminder — September 2026 | app/github-actions | 2026-09-01T09:13:55Z | |
| #681-668 | [backup-verify] Restore check FAILED — 2026-08-15 (multiple) | app/github-actions | 2026-08-15 | backup-verify, automated |
| #675 | [Security] Monthly Secret Rotation Reminder — August 2026 | app/github-actions | 2026-08-01T09:40:31Z | |
| #668 | [Security] Monthly Secret Rotation Reminder — July 2026 | app/github-actions | 2026-07-01T10:23:14Z | |
| #654 | Weekly event gap scan: 2026-06-22 — DEGRADED (scrapers blocked, 56/10614 events, result unreliable) | | 2026-06-22T13:07:28Z | event-gap-scan |

### 3.2 Key Issue: #748 — Production Resolver Issue

**Title:** Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed  
**Author:** eltonaguiar  
**Created:** 2026-10-20T02:56:09Z  
**Body:** Production resolver predates `_priceless_close` -> `exit_price=0.0` flat closes in `recent_closed`

This is a critical data integrity issue where the production resolver uses `_priceless_close` which results in `exit_price=0.0` and flat closes in `recent_closed`. This means many picks have zero exit price, making PnL calculations incorrect.

### 3.3 Recurring Issue: [backup-verify] Restore check FAILED

This issue has been recurring monthly since at least August 2026:
- August 2026: #677-680 (multiple)
- September 2026: #681-690 (multiple)  
- October 2026: #721-728 (multiple)
- November 2026: #780-787 (multiple)

This indicates a systemic backup/restore problem that has not been resolved for at least 4 months.

---

## 4. Repo Health Assessment

### 4.1 What's Working Well

- ✅ 60+ GitHub Actions workflows defined and mostly active
- ✅ Active development with 30+ open PRs showing active contribution
- ✅ CI Tests workflow exists with Python 3.11/3.12 matrix
- ✅ Backup verification workflow exists (but failing)
- ✅ QA Market Validation workflow exists (but failing due to missing secrets)
- ✅ Forward ledger sync workflow exists
- ✅ Multiple agent worktrees active (wired-in/buffy-*, opencode/money-ready, etc.)

### 4.2 Critical Problems

1. **QA Market Validation fails every hour** — Missing API secrets. This is the #1 priority because it prevents validated PnL from reaching the dashboard, meaning users see unvalidated data.

2. **Sports smoke test fails hourly** — Ubuntu 26.04 incompatibility with Playwright. This means the sports betting dashboard is not being smoke-tested.

3. **Backup Restore Verification fails monthly** — Cannot verify disaster recovery capability for 4+ months.

4. **CI Tests failing on feature branches** — The wired-in/buffy-2026-11-15 branch has failing CI tests.

5. **CI concurrency causes cancelled runs** — Every push with a different SHA starts a new CI run, and with storm-commits, most runs are cancelled before completion.

6. **No CODEOWNERS file** — No automatic code review assignment.

7. **No dependabot config** — No automated dependency updates.

8. **No CODE_OF_CONDUCT.md or CONTRIBUTING.md** — No contribution guidelines visible in root.

### 4.3 Workflows That Are Disabled

- `audit-dashboard.yml.disabled` — Dashboard deployment disabled
- `alpha-engine-alpha-suite-daily-refresh.yml.disabled` — Alpha suite refresh disabled
- `fast-variants-master.yml.disabled` — Fast variants master disabled
- `ml-battleground-a.yml.retired` through `ml-battleground-f.yml.retired` — Retired ML battleground workflows
- `ml-battleground-monitor.yml.retired` — Retired
- `paper-trading.yml.retired` — Retired
- `rl-agent-ppo.yml.retired` — Retired

---

## 5. Recommended Fixes (Priority Order)

### P0 — Critical (Do Immediately)

| # | Issue | Fix | PR/Workflow |
|---|-------|-----|-------------|
| 1 | QA Market Validation fails every hour | Add 5 API secrets to GitHub repo settings: `FINNHUB_API_KEY`, `TIINGO_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FMP_API_KEY` | PR #786 addresses this |
| 2 | Sports smoke test fails hourly | Pin `sports-smoke-and-e2e.yml` to `ubuntu-24.04` instead of `ubuntu-latest` | PR #786 addresses this |
| 3 | Backup Restore Verification fails monthly | Investigate why backup restore check fails; check `tools/backup_verify.py` or equivalent | Issue #748 related |
| 4 | CI Tests failing on feature branch | Fix failing tests on `wired-in/buffy-2026-11-15` branch | PR #786 related |

### P1 — High Priority (Do This Week)

| # | Issue | Fix |
|---|-------|-----|
| 5 | PR #786 not yet merged | Review and merge PR #786 — it fixes QA price validation, snapshot pushes, and sports smoke |
| 6 | PR #785 not yet merged | Review and merge PR #785 — restores audit page script tags and tracker horizon fix |
| 7 | CI concurrency causes cancelled runs | Consider `cancel-in-progress: true` with `group: ${{ github.workflow }}` (not per-SHA) to cancel stale runs on same branch |
| 8 | No CODEOWNERS file | Add CODEOWNERS to auto-assign reviewers |
| 9 | No dependabot config | Add `.github/dependabot.yml` for automated dependency updates |
| 10 | No CODE_OF_CONDUCT.md or CONTRIBUTING.md | Add contribution guidelines |

### P2 — Medium Priority (Do This Month)

| # | Issue | Fix |
|---|-------|-----|
| 11 | 40+ open PRs need review | Triage and merge or close stale PRs |
| 12 | ~50 open issues (mostly backup-verify failures) | Triage and resolve backup issues; close stale ones |
| 13 | 17 disabled/retired workflows | Review and either re-enable or permanently delete |
| 14 | `frontend-manifest.yml` and other deploy workflows | Verify FTP credentials and deployment targets are correct |
| 15 | Multiple `*.yml.disabled` and `*.yml.retired` files | Clean up or document why they're disabled |

### P3 — Low Priority (Do This Quarter)

| # | Issue | Fix |
|---|-------|-----|
| 16 | Add CODEOWNERS file | Auto-assign PR reviewers |
| 17 | Add CONTRIBUTING.md | Document contribution process |
| 18 | Add CODE_OF_CONDUCT.md | Community guidelines |
| 19 | Review all `.disabled` and `.retired` workflows | Decide to re-enable or delete |
| 20 | Add dependabot for Python and JS dependencies | Automated security updates |

---

## 6. Immediate Actions Recommended

### Action 1: Merge PR #786 (Highest Priority)

This PR fixes the two most critical failing workflows:
- QA Market Validation (adds 5 missing API secrets)
- Sports smoke test (pins to ubuntu-24.04)

**Command:**
```bash
gh pr checkout 786
gh pr merge 786 --merge --admin
```

### Action 2: Merge PR #785

This PR restores audit page script tags and fixes tracker horizon.

**Command:**
```bash
gh pr checkout 785
gh pr merge 785 --merge --admin
```

### Action 3: Set Missing GitHub Secrets

Add the following secrets to the repo (Settings → Secrets and variables → Actions):
- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`
- `GH_PAT` (for actions-failure-guardian and forward-ledger-sync)

### Action 4: Fix Backup Restore Verification

Investigate why `backup-verify.yml` fails monthly. Check:
- `audit_dashboard/data/dashboard_data.json` exists and is valid JSON
- `alpha_engine/data/recent_exits.json` exists
- Python syntax checks pass on key engine files
- `recent_closed.json` exists (currently missing!)

### Action 5: Review and Merge Stale PRs

PRs #766-#736 (October 2026) are over a month old and still open. Review and merge or close them.

---

## 7. Files Referenced

| File | Purpose |
|------|---------|
| `.github/workflows/ci-tests.yml` | CI test suite — failing on feature branch |
| `.github/workflows/qa-market-validation.yml` | QA validation — failing due to missing API keys |
| `.github/workflows/backup-verify.yml` | Monthly backup verification — failing |
| `.github/workflows/sports-smoke-and-e2e.yml` | Sports Playwright tests — failing on ubuntu-26.04 |
| `.github/workflows/actions-failure-guardian.yml` | Auto-retries failed workflows |
| `.github/workflows/gha-summary-report.yml` | Generates GHA summary HTML |
| `.github/workflows/gha-stale-workflows-audit.yml` | Audits stale workflows |
| `.github/workflows/forward-ledger-sync.yml` | Syncs closed picks to forward ledger |
| `.github/workflows/deploy-vetted-picks.yml` | Deploys vetted master-picks |
| `.github/workflows/forward-ledger-sync.yml` (untracked) | New, not yet committed |
| `tools/qa_ledger.py` | QA ledger validation script |
| `tools/forward_tracker.py` | Forward test tracker |
| `tools/actions_failure_guardian.py` | Actions failure monitoring |
| `tools/generate_gha_summary_html.py` | GHA summary generation |
| `tools/deploy_gha_summary.py` | Deploys GHA summary to FTP |
| `tools/find_stale_github_workflows.py` | Stale workflow detection |
| `tools/check_workflow_sparse_safe_push.py` | Safe push checking |
| `.github/scripts/safe_commit_push.sh` | Safe push script |
| `alpha_engine/equity_price_failover.py` | Equity price feed with 7 adapters |

---
