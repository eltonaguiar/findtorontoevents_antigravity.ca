# GitHub Actions / Pull Requests / Issues Audit Report

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-15T08:00Z UTC (and updated continuously)
**Auditor:** Automated CI/CD audit agent
**Branch audited:** main (plus active worktrees)

---

## 1. Executive Summary

The repository's CI/CD infrastructure is in a **degraded state**. Multiple critical workflows are failing on every run, and several have been failing continuously for days or weeks. The issues fall into three categories:

| Severity | Count | Workflows Affected |
|----------|-------|-------------------|
| **P0 — Critical** | 3 | QA Market Validation, Sports endpoint smoke + Playwright, Backup Restore Verification |
| **P1 — High** | 4 | CI Tests (main + feature branches), EQUITY ML validation |
| **P2 — Medium** | 10+ | Various asset-class scanners, backtests, dashboards |

### Root Causes Identified:

1. **Missing GitHub Secrets** — QA Market Validation fails every hour because 5 API keys (FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY) are **not set** as GitHub Secrets. Adapters 2–6 return `None`, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky in GHA). Every run produces: `"fetch_quote(<ticker>): ALL 7 sources failed"` for every equity ticker.

2. **Ubuntu 26.04 incompatibility** — Sports endpoint smoke + Playwright workflow fails because `ubuntu-latest` now resolves to Ubuntu 26.04, and Playwright does not support Chromium on Ubuntu 26.04. Error: `"Playwright does not support chromium on ubuntu26.04-x64"`.

3. **Monthly backup-verify failures** — Recurring failures since at least August 2026 (30+ open issues).

4. **CI concurrency** — Uses `${{ github.sha }}` as concurrency group, meaning every push starts a new run and cancels in-flight runs with different SHAs.

5. **30+ open PRs** — Several CI-related fixes that have been open for weeks without merge.

---

## 2. GitHub Actions Workflow Audit

### 2.1 Workflow Inventory

Total workflows discovered: **60+** `.yml` files in `.github/workflows/`

#### Workflow Status Summary:
| Status | Count |
|--------|-------|
| Active | ~55 |
| Disabled (.disabled) | 6 |
| Retired (.retired) | 10 |
| Draft (.draft) | 1 |

#### Disabled Workflows:
- `alpha-engine-alpha-suite-daily-refresh.yml.disabled`
- `alpha-suite-daily-refresh.yml.disabled`
- `daily-price-refresh.yml.disabled`
- `deploy-pages.yml.disabled`
- `fast-variants-master.yml.disabled`
- `forward-test-daily.yml.disabled`

#### Retired Workflows (10):
- `ml-battleground-abc-pilots.yml.retired`
- `ml-battleground-a.yml.retired` through `ml-battleground-f.yml.retired`
- `ml-battleground-monitor.yml.retired`
- `paper-trading.yml.retired`
- `rl-agent-ppo.yml.retired`

#### Draft Workflows (1):
- `bt-backtest-trades-sync.yml.draft`

---

## 3. Failing Workflows Detail

### 3.1 QA Market Validation — CRITICAL FAILURE

**Workflow file:** `.github/workflows/qa-market-validation.yml`
**Schedule:** Every hour (`0 * * * *`)
**Trigger:** Push to `main` (paths: `tools/qa_ledger.py`, `audit_dashboard/data/picks_now_live_pnl.json`, workflow file itself)

**Failure pattern:** Every run since at least 2026-11-15 07:33 UTC has failed.

**Root cause:** The workflow runs `python tools/qa_ledger.py` which requires 5 API keys as GitHub Secrets:
- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

**Evidence:** Run #43693232126 failed at step "Run QA ledger" (step 5 of 11). Steps 1-4 (checkout, setup Python, install dependencies) all passed. Step 5 failed because the QA ledger script cannot fetch quotes from any source.

**Workflow comment explicitly states:**
> The chain has 7 adapters, but adapters 2-6 return None immediately when their key is unset — leaving only Stooq (its anonymous endpoint is blocked from GitHub-runner IPs) and yfinance (documented as flaky in GHA in that module's own docstring). That is exactly how run 43688541491 produced "fetch_quote(<ticker>): ALL 7 sources failed" for every single equity ticker and failed the gate. Without these keys this job cannot validate PnL, so it fails every hour forever.

**Fix:** Add the 5 secrets to GitHub repo Settings → Secrets and variables → Actions:
- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

**Related PR:** #786 "fix(ci): restore QA price validation, snapshot pushes, and sports smoke"

---

### 3.2 Sports endpoint smoke + Playwright — CRITICAL FAILURE

**Workflow file:** `.github/workflows/sports-smoke-and-e2e.yml`
**Schedule:** Every hour at minute 17 (`17 * * * *`)
**Trigger:** PR touching live-monitor files, workflow_dispatch

**Failure pattern:** Every run since at least 2026-11-15 02:09 UTC has failed.

**Root cause:** `runs-on: ${{ vars.ACTIONS_RUNNER_LABEL || 'ubuntu-latest' }}` — `ubuntu-latest` now resolves to Ubuntu 26.04, and Playwright does not support Chromium on Ubuntu 26.04. Error: `"Playwright does not support chromium on ubuntu26.04-x64"`.

**Fix:** Pin to `ubuntu-24.04`:
```yaml
runs-on: ubuntu-24.04
```

**Evidence:** Run 43689346545 failed at the install step with "Playwright does not support chromium on ubuntu26.04-x64".

**Related PR:** #786

---

### 3.3 Backup Restore Verification — RECURRING FAILURE

**Workflow file:** `.github/workflows/backup-verify.yml`
**Schedule:** Monthly, 15th at 06:00 UTC (`0 6 15 * *`)
**Trigger:** workflow_dispatch

**Failure pattern:** Failing monthly since at least August 2026. ~30+ open issues titled "[backup-verify] Restore check FAILED".

**Workflow purpose:**
1. Check `trading_picks` count via `dashboard_data.json` proxy
2. Check `at_pick_outcomes` count via `recent_exits.json` proxy
3. Check existence and non-empty state of critical JSON data files
4. Python syntax check of key engine files

**Files checked:**
- `audit_dashboard/data/dashboard_data.json`
- `alpha_engine/data/recent_exits.json`
- `alpha_engine/data/ml_health_status.json`
- `audit_dashboard/data/pcg5_log.json`

**Related Issue:** #748 "Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed"

---

## 4. Open Pull Requests

Total open PRs: **30+**

### Critical PRs (should be merged ASAP):

| PR # | Title | Branch | Base | Created | Author |
|------|-------|--------|------|---------|--------|
| #786 | fix(ci): restore QA price validation, snapshot pushes, and sports smoke | wired-in/buffy-gh-actions-fix-2026-11-15 | main | 2026-11-15T07:33:21Z | eltonaguiar |
| #785 | Restore audit page script tags lost on main + tracker horizon fix | wired-in/buffy-2026-11-15-final | main | 2026-11-15T07:26:36Z | eltonaguiar |
| #766 | docs: add kilo today's ServiceNow/Salesforce Canada jobs scan | add-kilo-todays-servicenow-salesforce-jobs | main | 2026-11-02 | eltonaguiar |
| #765 | docs: add kilo additional skills/certifications | add-kilo-additional-skills | main | 2026-11-02 | eltonaguiar |
| #763 | Add verified sci-fi TV watchlist and upcoming releases to weather | copilot/weather-tv-2026-11-01 | main | 2026-11-01 | eltonaguiar |
| #762 | Job Scan: ServiceNow & Salesforce - Huggle Agent 2026-10-30 | huggle-agent-2026-10-30 | main | 2026-10-30 | eltonaguiar |
| #761 | fix: rotated FTP credentials, no embedded password defaults, verified FTPS | fix/ghcopilot-ftp-credential-loading | main | 2026-10-23 | eltonaguiar |
| #760 | fix: fund walk-forward review fixes (FXAIX same-window CI + identical-pairs proof) | oc/fund-walkforward-review-fixes | main | 2026-10-23 | eltonaguiar |
| #759 | research (opt-in): 95-fund durability audit and genuine zero-expense ETFs | research/ghcopilot-symbol-durability | main | 2026-10-23 | eltonaguiar |
| #758 | Fix BTC evaluator daily drawdown and unsupported gate passes | fix/ghcopilot-btc-mtm-guard | main | 2026-10-22 | eltonaguiar |
| #757 | Fix audit evidence cards and explain strategy readiness | feat/ghcopilot-grok-scorecard | main | 2026-10-22 | eltonaguiar |
| #756 | Fix DSR>1 + resolver batch-close/flat-exit bugs | fix/grok-quickfixes-dsr-resolver | main | 2026-10-22 | eltonaguiar |
| #751 | ci: add GitHub Actions health monitor job | feat/gha-actions-health | main | 2026-10-22 | eltonaguiar |
| #750 | Nemotron Money Ready: Bond Yield Curve Slope Strategy Test | nemotron/money-ready | main | 2026-10-20 | eltonaguiar |
| #749 | fix(resolver): true TP/SL exit time + UNRESOLVED_NO_PRICE (batch-close root cause) | buffy/batch-close-rootcause | main | 2026-10-20 | eltonaguiar |
| #747 | feat(opencode): crypto money-ready backtest + report (no passes) | opencode/money-ready | main | 2026-10-20 | eltonaguiar |
| #746 | spec: KPI page (spec only, no code this week) | opencode/kpi-page-spec | main | 2026-10-20 | eltonaguiar |
| #745 | fix(audit): smart_picks gate-validated only + curated_feed + empty-state reasons | opencode/audit-empty-state-v2 | main | 2026-10-20 | eltonaguiar |
| #744 | fix(forward_validator): enforce BLACKLISTED_STRATEGIES in save_active_picks | fix/blacklist-save-active-picks | main | 2026-10-20 | eltonaguiar |
| #736 | fix(fc+weather): persist category Apply/filter + weather reset-look recovery button | fix/fc-category-persist-weather-reset-look | main | 2026-10-18 | eltonaguiar |
| #735 | fix(audit): symbol→asset-class cache fallback + make the last hard-coded /audit core stats dynamic | fix/assetclass-cache-live-core-stats | main | 2026-10-18 | eltonaguiar |
| #713 | fix(ci): backup-verify false failures + issue spam; speed up dup-guard scan | fix/ci-backup-verify-and-dupguard | main | 2026-10-04 | eltonaguiar |
| #711 | fix(audit): correct two defects in the per-tab/per-class staleness code from #708 | fix/stale-tag-defects | main | 2026-10-04 | eltonaguiar |
| #701 | Preserve pick rationale through *_audit_push normalizers | fix/pick-reason-audit-push | main | 2026-10-04 | eltonaguiar |
| #700 | LLM free-first routing + message tracing; Discord webhook loud-failure + secret scrub | fix/oct3-llm-discord-loud-failure | main | 2026-10-04 | eltonaguiar |
| #696 | fix(discord): read webhooks from secrets only after exposed hook deletion | fix/discord-webhook-secret-rotation | main | 2026-10-03 | eltonaguiar |

**PR #786 is the most critical** — it fixes QA Market Validation (adds missing API secrets) and Sports smoke test (pins to ubuntu-24.04).

---

## 7. Open Issues

Total open issues: **~50+**

### Critical Issues

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

**Recurring issue pattern:** The `[backup-verify] Restore check FAILED` issue has recurred monthly since at least August 2026 (30+ open issues), indicating a systemic problem that has not been resolved.

### Key Issue: #748 — Production Resolver

**Title:** Production resolver predates `_priceless_close` → `exit_price=0.0` flat closes in `recent_closed`
**Author:** eltonaguiar
**Created:** 2026-10-20T02:56:09Z
**Impact:** Production resolver uses `_priceless_close` which results in `exit_price=0.0` flat closes in `recent_closed`. This means many picks have zero exit price, making PnL calculations incorrect.

---

## 8. Fix Plan

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

## 9. Evidence Files

All evidence captured from `gh` CLI:
- `gh workflow list` — 60+ workflows
- `gh run list --status failure` — 50+ failing runs
- `gh run list --status cancelled` — 50+ cancelled runs
- `gh run list --status skipped` — 50+ skipped runs (workflow_dispatch from other workflows)
- `gh pr list --state open --limit 50` — 30+ open PRs
- `gh issue list --state open --limit 50` — ~50+ open issues
- Individual workflow file reads for `qa-market-validation.yml`, `ci-tests.yml`, `backup-verify.yml`, `sports-smoke-and-e2e.yml`

---

## 10. Deployment Notes

**Files modified for fixes:**
- `.github/workflows/sports-smoke-and-e2e.yml` — Pin to ubuntu-24.04
- `.github/workflows/ci-tests.yml` — Fix concurrency group
- `.github/secrets` — Add 5 API keys (must be done via GitHub UI, not via git)

**No code changes needed for QA Market Validation** — the fix is purely adding secrets to GitHub repository settings.
