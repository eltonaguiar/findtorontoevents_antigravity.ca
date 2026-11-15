# Unfinished Work — GHA / PR / ISSUES Audit

**Date:** 2026-11-15T07:45Z UTC  
**Source:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/  
**Related:** GHACTIONS_PR_ISSUES/2026-11-15T0745Z_gh-actions-pr-issues/  
**Status:** DOCUMENTED — unfinished work tracked below

---

## 1. Open Pull Requests (30+ open, requires review)

| PR # | Title | Branch | Base | Created | Status |
|------|-------|--------|------|---------|--------|
| #786 | fix(ci): restore QA price validation, snapshot pushes, and sports smoke | wired-in/buffy-gh-actions-fix-2026-11-15 | main | 2026-11-15T07:33:21Z | OPEN — MERGE READY |
| #785 | Restore audit page script tags lost on main + tracker horizon fix | wired-in/buffy-2026-11-15-final | main | 2026-11-15T07:26:36Z | OPEN — MERGE READY |
| #766 | docs: add kilo today's ServiceNow/Salesforce Canada jobs scan | add-kilo-todays-servicenow-salesforce-jobs | main | 2026-11-02 | OPEN |
| #765 | docs: add kilo additional skills/certifications | add-kilo-additional-skills | main | 2026-11-02 | OPEN |
| #763 | Add verified sci-fi TV watchlist and upcoming releases | copilot/weather-tv-2026-11-01 | main | 2026-11-01 | OPEN |
| #762 | Job Scan: ServiceNow & Salesforce - Huggle Agent | huggle-agent-2026-10-30 | main | 2026-10-30 | OPEN |
| #761 | fix: rotated FTP credentials, no embedded password defaults | fix/ghcopilot-ftp-credential-loading | main | 2026-10-23 | OPEN |
| #760 | fix: fund walk-forward review fixes | oc/fund-walkforward-review-fixes | main | 2026-10-23 | OPEN |
| #759 | research: 95-fund durability audit | research/ghcopilot-symbol-durability | main | 2026-10-23 | OPEN |
| #758 | Fix BTC evaluator daily drawdown | fix/ghcopilot-btc-mtm-guard | main | 2026-10-22 | OPEN |
| #757 | Fix audit evidence cards | feat/ghcopilot-grok-scorecard | main | 2026-10-22 | OPEN |
| #756 | Fix DSR>1 + resolver batch-close/flat-exit bugs | fix/grok-quickfixes-dsr-resolver | main | 2026-10-22 | OPEN |
| #751 | ci: add GitHub Actions health monitor job | feat/gha-actions-health | main | 2026-10-22 | OPEN |
| #750 | Nemotron Money Ready: Bond Yield Curve Slope Strategy | nemotron/money-ready | main | 2026-10-20 | OPEN |
| #749 | fix(resolver): true TP/SL exit time + UNRESOLVED_NO_PRICE | buffy/batch-close-rootcause | main | 2026-10-20 | OPEN |
| #747 | feat(opencode): crypto money-ready backtest | opencode/money-ready | main | 2026-10-20 | OPEN |
| #746 | spec: KPI page (spec only) | opencode/kpi-page-spec | main | 2026-10-20 | OPEN |
| #745 | fix(audit): smart_picks gate-validated only | opencode/audit-empty-state-v2 | main | 2026-10-20 | OPEN |
| #744 | fix(forward_validator): enforce BLACKLISTED_STRATEGIES | fix/blacklist-save-active-picks | main | 2026-10-20 | OPEN |

**Most critical:** PR #786 fixes QA Market Validation (missing API keys) and Sports smoke test (ubuntu-26.04 incompatibility). PR #785 restores audit page script tags.

---

## 2. Open Issues (~50+ open)

### 3.1 Critical Issues — Backup Verify Failures (Recurring Monthly)

| # | Title | Created | Labels |
|---|-------|---------|--------|
| #787 | [backup-verify] Restore check FAILED — 2026-11-15 | 2026-11-15 | backup-verify, automated |
| #783 | [backup-verify] Restore check FAILED — 2026-11-15 | 2026-11-15 | backup-verify, automated |
| #782 | [backup-verify] Restore check FAILED — 2026-11-15 | 2026-11-15 | backup-verify, automated |
| #781 | [backup-verify] Restore check FAILED — 2026-11-15 | 2026-11-15 | backup-verify, automated |
| #780 | [backup-verify] Restore check FAILED — 2026-11-15 | 2026-11-15 | backup-verify, automated |
| #728-721 | [backup-verify] Restore check FAILED — 2026-10-15 (8 issues) | 2026-10-15 | backup-verify, automated |
| #694-668 | [backup-verify] Restore check FAILED — 2026-09-15 through 2026-08-15 (multiple) | 2026-09-15 to 2026-08-15 | backup-verify, automated |

**Pattern:** Backup verification fails every month since at least August 2026. Root cause not yet identified.

### 3.2 Security Issues

| # | Title | Created |
|---|-------|---------|
| #764 | [Security] Monthly Secret Rotation Reminder — November 2026 | 2026-11-01 |
| #695 | [Security] Monthly Secret Rotation Reminder — October 2026 | 2026-10-01 |
| #685 | [Security] Monthly Secret Rotation Reminder — September 2026 | 2026-09-01 |
| #675 | [Security] Monthly Secret Rotation Reminder — August 2026 | 2026-08-01 |
| #668 | [Security] Monthly Secret Rotation Reminder — July 2026 | 2026-07-01 |

### 3.3 Key Issue: #748 — Production Resolver

**Title:** Production resolver predates _priceless_close -> exit_price=0.0 flat closes in recent_closed  
**Author:** eltonaguiar  
**Created:** 2026-10-20  
**Impact:** Production resolver uses `_priceless_close` which results in `exit_price=0.0` flat closes in `recent_closed`. This means many picks have zero exit price, making PnL calculations incorrect.

---

## 3. GitHub Actions Workflow Failures

### 3.1 QA Market Validation — FAILING Every Hour

**Workflow:** `.github/workflows/qa-market-validation.yml`  
**Schedule:** Every hour (`0 * * * *`)  
**Root cause:** 5 API keys not set as GitHub Secrets:
- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `TWELVE_DATA_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

**Impact:** Adapters 2–6 return `None`, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky). Result: "ALL 7 sources failed" for every equity ticker. QA cannot validate PnL.

**Fix:** Add the 5 secrets to GitHub repo Settings → Secrets and variables → Actions.

**Related PR:** #786

---

### 3.2 Sports Endpoint Smoke + Playwright — FAILING Every Hour

**Workflow:** `.github/workflows/sports-smoke-and-e2e.yml`  
**Schedule:** Hourly at minute 17 (`17 * * * *`)  
**Root cause:** `ubuntu-latest` now resolves to Ubuntu 26.04. Playwright does not support Chromium on Ubuntu 26.04.

**Fix:** Pin to `ubuntu-24.04` in the workflow file.

**Related PR:** #786

---

### 3.3 Backup Restore Verification — FAILING Monthly

**Workflow:** `.github/workflows/backup-verify.yml`  
**Schedule:** Monthly, 15th at 06:00 UTC (`0 6 15 * *`)  
**Status:** FAILING since at least August 2026  
**Impact:** Cannot verify disaster recovery capability

**Related Issue:** #748 and ~30+ backup-verify issues

---

### 3.4 CI Tests — FAILING on Feature Branch

**Workflow:** `.github/workflows/ci-tests.yml`  
**Schedule:** Push to `main`  
**Status:** Failing on `wired-in/buffy-2026-11-15` branch  
**Coverage:** ~747 tests (558 root + 103 walkforward elite + 86 alpha_engine)  
**Issue:** Concurrency group uses `${{ github.sha }}` which means every push starts a new run; with storm-commits, most runs are cancelled before completion.

**Fix:** Change concurrency group to `${{ github.workflow }}-${{ github.ref }}` and set `cancel-in-progress: true`.

---

## 4. Recommended Actions (Priority Order)

### P0 — Do Immediately

| # | Action | Why |
|---|--------|-----|
| 1 | Add 5 API secrets to GitHub (FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY) | QA Market Validation fails every hour without them |
| 2 | Pin sports smoke test to ubuntu-24.04 | Playwright doesn't support ubuntu-26.04 |
| 3 | Merge PR #786 | Fixes QA price validation + sports smoke |
| #4 | Merge PR #785 | Restores audit page script tags + tracker horizon fix |

### P1 — Do This Week

| # | Action |
|---|--------|
| 5 | Fix CI concurrency (use branch instead of SHA in concurrency group) |
| 6 | Investigate backup-verify failures (monthly since Aug 2026) |
| 7 | Add CODEOWNERS file |
| 8 | Add Dependabot config |
| 9 | Add CONTRIBUTING.md and CODE_OF_CONDUCT.md |

### P2 — Do This Month

| # | Action |
|---|--------|
| 10 | Review and merge or close 30+ open PRs |
| 11 | Triage and close stale backup-verify issues |
| 12 | Review 17 disabled/retired workflows |
| 13 | Review 40+ open PRs for relevance |

---

## 5. Unfinished Work — Not Yet Committed to Main

The following work exists on feature branches or as uncommitted changes and should be reviewed for merging into main:

### 5.1 Uncommitted Changes (Working Directory)

| File | Status |
|------|--------|
| `WIRED_IN/2026-11-15_0711_buffy/experiments/repo_mine.py` | Modified — experiment script |
| `___HELL_HEALTH_OPENCODE.MD` | Modified |
| `audit_dashboard/index.html` | Modified |
| `audit_dashboard/template.html` | Modified |
| `tools/forward_tracker.py` | Modified — cost model + benchmark price integration |

### 5.2 Untracked Files on Main Branch

| File/Directory | Status |
|--------------|--------|
| `.github/workflows/forward-ledger-sync.yml` | Untracked — new workflow |
| `COMMUNITY/` | Untracked |
| `ServiceNowMidServer/` | Untracked |
| `ServiceNow_ServiceGraph_Lab/` | Untracked |
| `WIRED_IN/2026-11-15T0724_flaxen-hair/` | Untracked |
| `WIRED_IN/2026-11-15T0726Z_finpredict/` | Untracked |
| `WIRED_IN/2026-11-15_0711_buffy/` | Untracked — full worktree |
| `audit_dashboard/data/benchmark_prices.json` | Untracked |
| `audit_dashboard/data/forward_clock.json` | Untracked |
| `audit_dashboard/excess_column.js` | Untracked |
| `audit_dashboard/forward_clock.js` | Untracked |
| `bestiejob/` | Untracked |
| `data/cache/pick_excess/` | Untracked |
| `references/grokbot/` | Untracked |
| `reports/pick_excess_returns.json` | Untracked |
| `reports/pm_calibration.json` | Untracked |
| `reports/quant_audit/` | Untracked |
| `state/forward_test/status.json` | Untracked |
| `tests/test_forward_tracker_of_edges.py` | Untracked |
| `tools/build_benchmark_prices.py` | Untracked |
| `tools/build_forward_clock.py` | Untracked |
| `tools/pick_excess.py` | Untracked |
| `tools/pm_binary.py` | Untracked |
| Multiple `updates/2026-11-15-*` files | Untracked |

### 5.3 Stashed Changes (Not on Any Branch)

`git stash` contains:
- `WIRED_IN/2026-11-15_0711_buffy/experiments/repo_mine.py` (modified)
- `___HELL_HEALTH_OPENCODE.MD` (modified)

These changes were stashed when switching to main and need to be reviewed and either committed or discarded.

---

## 6. Immediate Next Steps

1. **Merge PR #786** — fixes QA price validation + sports smoke (critical)
2. **Merge PR #785** — restores audit page script tags
3. **Add 5 missing API secrets** to GitHub repo settings
4. **Pin sports smoke test to ubuntu-24.04** (part of PR #786)
5. **Commit GHACTIONS_PR_ISSUES folder to main** — DONE (commit d24723387f0)
6. **Document unfinished work in WIRED_IN** — DONE (this document)
7. **Pop stash and review stashed changes** — decide to commit or discard
8. **Review 30+ open PRs** — merge or close
9. **Triage ~50 open issues** — focus on backup-verify failures
10. **Review 17 disabled/retired workflows** — re-enable or delete

---
