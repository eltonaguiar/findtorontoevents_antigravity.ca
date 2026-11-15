# Open Pull Requests Analysis

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
**Generated:** 2026-11-15T08:00Z UTC
**Total Open PRs:** ~30+

---

## Critical PRs Requiring Immediate Action

### PR #786 — fix(ci): restore QA price validation, snapshot pushes, and sports smoke
- **Branch:** `wired-in/buffy-gh-actions-fix-2026-11-15` → `main`
- **Author:** eltonaguiar
- **Created:** 2026-11-15T07:33:21Z
- **Status:** OPEN
- **Criticality:** P0 — Fixes two critically failing workflows

**Summary:** This PR fixes two critically failing workflows:
1. **QA Market Validation** — Adds 5 missing API keys (FINNHUB_API_KEY, TIINGO_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY) that are required for the QA ledger validation to work. Without these keys, adapters 2-6 return None, leaving only Stooq (blocked from GH runner IPs) and yfinance (flaky in GHA).
2. **Sports smoke test** — Pins the runner to ubuntu-24.04 because ubuntu-latest now resolves to Ubuntu 26.04, which Playwright does not support.

**Evidence from PR body:**
- "Four scheduled workflows on main had no successful run after their latest failure. All four are config bugs, and two of them starve main of financial data."
- Table shows specific workflow failures and fixes
- Verification: "all four YAML files yaml.safe_load cleanly and every run: script passes bash -n"

**Action:** Merge this PR immediately — it addresses the two most critical failing workflows.

---

### PR #785 — Restore audit page script tags lost on main + tracker horizon fix
- **Branch:** wired-in/buffy-2026-11-15-final → main
- **Author:** eltonaguiar
- **Created:** 2026-11-15T07:26:36Z
- **Status:** OPEN
- **Criticality:** P1 — Restores audit page functionality

**Summary:** Restores `excess_column.js` / `forward_clock.js` script tags that were missing from `audit_dashboard/index.html` and `audit_dashboard/template.html`. Also fixes tracker horizon issue where mixed naive/aware timestamps raised TypeError, leaving 3,500 rows NOT MEASURED; 3,392/3,500 now measured.

**Action:** Merge this PR — restores critical audit dashboard functionality.

---

### PR #766 — docs: add kilo today's ServiceNow/Salesforce Canada jobs scan
- **Branch:** add-kilo-todays-servicenow-salesforce-jobs → main
- **Author:** eltonaguiar
- **Created:** 2026-11-02T15:27:01Z
- **Status:** OPEN
- **Criticality:** P3 — Documentation only

---

### PR #765 — docs: add kilo additional skills/certifications
- **Branch:** add-kilo-additional-skills → main
- **Author:** eltonaguiar
- **Created:** 2026-11-02T15:16:59Z
- **Status:** OPEN
- **Criticality:** P3 — Documentation only

---

### PR #763 — Add verified sci-fi TV watchlist and upcoming releases to weather
- **Branch:** copilot/weather-tv-2026-11-01 → main
- **Author:** eltonaguiar
- **Created:** 2026-11-01T02:46:20Z
- **Status:** OPEN
- **Criticality:** P3 — Documentation/content only

---

### PR #762 — Job Scan: ServiceNow & Salesforce - Huggle Agent 2026-10-30
- **Branch:** huggle-agent-2026-10-30 → main
- **Author:** eltonaguiar
- **Created:** 2026-10-30T22:49:10Z
- **Status:** OPEN
- **Criticality:** P3 — Documentation/data only

---

### PR #761 — fix: rotated FTP credentials, no embedded password defaults, verified FTPS
- **Branch:** fix/ghcopilot-ftp-credential-loading → main
- **Author:** eltonaguiar
- **Created:** 2026-10-23T04:33:51Z
- **Status:** OPEN
- **Criticality:** P2 — Security fix for FTP credentials

---

### PR #760 — fix: fund walk-forward review fixes
- **Branch:** oc/fund-walkforward-review-fixes → main
- **Author:** eltonaguiar
- **Created:** 2026-10-23T04:23:38Z
- **Status:** OPEN
- **Criticality:** P2 — Fund walk-forward fixes

---

### PR #759 — research: 95-fund durability audit
- **Branch:** research/ghcopilot-symbol-durability → main
- **Author:** eltonaguiar
- **Created:** 2026-10-23T00:19:42Z
- **Status:** OPEN
- **Criticality:** P3 — Research documentation

---

### PR #758 — Fix BTC evaluator daily drawdown
- **Branch:** fix/ghcopilot-btc-mtm-guard → main
- **Author:** eltonaguiar
- **Created:** 2026-10-22T23:57:35Z
- **Status:** OPEN
- **Criticality:** P2 — BTC evaluator fix

---

### PR #757 — Fix audit evidence cards and explain strategy readiness
- **Branch:** feat/ghcopilot-grok-scorecard → main
- **Author:** eltonaguiar
- **Created:** 2026-10-22T23:31:57Z
- **Status:** OPEN
- **Criticality:** P2 — Audit evidence fix

---

### PR #756 — Fix DSR>1 + resolver batch-close/flat-exit bugs
- **Branch:** fix/grok-quickfixes-dsr-resolver → main
- **Author:** eltonaguiar
- **Created:** 2026-10-22T23:24:29Z
- **Status:** OPEN
- **Criticality:** P2 — DSR/resolver fixes

---

### PR #751 — ci: add GitHub Actions health monitor job
- **Branch:** feat/gha-actions-health → main
- **Author:** eltonaguiar
- **Created:** 2026-10-22T21:31:24Z
- **Status:** OPEN
- **Criticality:** P2 — CI health monitoring

---

### PR #750 — Nemotron Money Ready: Bond Yield Curve Slope Strategy Test
- **Branch:** nemotron/money-ready → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T03:20:31Z
- **Status:** OPEN
- **Criticality:** P3 — Strategy test

---

### PR #749 — fix(resolver): true TP/SL exit time + UNRESOLVED_NO_PRICE
- **Branch:** buffy/batch-close-rootcause → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:56:10Z
- **Status:** OPEN
- **Criticality:** P2 — Resolver fix for TP/SL exit time

---

### PR #747 — feat(opencode): crypto money-ready backtest
- **Branch:** opencode/money-ready → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:48:28Z
- **Status:** OPEN
- **Criticality:** P2 — Crypto money-ready backtest

---

### PR #746 — spec: KPI page (spec only)
- **Branch:** opencode/kpi-page-spec → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:27:50Z
- **Status:** OPEN
- **Criticality:** P3 — Specification only

---

### PR #745 — fix(audit): smart_picks gate-validated only
- **Branch:** opencode/audit-empty-state-v2 → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:24:12Z
- **Status:** OPEN
- **Criticality:** P2 — Audit smart_picks fix

---

### PR #744 — fix(forward_validator): enforce BLACKLISTED_STRATEGIES
- **Branch:** fix/blacklist-save-active-picks → main
- **Author:** eltonaguiar
- **Created:** 2026-10-20T02:23:41Z
- **Status:** OPEN
- **Criticality:** P2 — Forward validator fix

---

### PR #736 — fix(fc+weather): persist category Apply/filter
- **Branch:** fix/fc-category-persist-weather-reset-look → main
- **Author:** eltonaguiar
- **Created:** 2026-10-18T22:17:26Z
- **Status:** OPEN
- **Criticality:** P3 — Weather/FC fix

---

### PR #735 — fix(audit): symbol→asset-class cache fallback
- **Branch:** fix/assetclass-cache-live-core-stats → main
- **Author:** eltonaguiar
- **Created:** 2026-10-18T08:38:17Z
- **Status:** OPEN
- **Criticality:** P2 — Audit cache fix

---

### PR #713 — fix(ci): backup-verify false failures + issue spam
- **Branch:** fix/ci-backup-verify-and-dupguard → main
- **Author:** eltonaguiar
- **Created:** 2026-10-04T07:05:19Z
- **Status:** OPEN
- **Criticality:** P2 — CI backup-verify fix

---

### PR #711 — fix(audit): correct two defects in per-tab/per-class staleness code
- **Branch:** fix/stale-tag-defects → main
- **Author:** eltonaguiar
- **Created:** 2026-10-04T05:30:10Z
- **Status:** OPEN
- **Criticality:** P2 — Audit staleness fix

---

### PR #701 — Preserve pick rationale through *_audit_push normalizers
- **Branch:** fix/pick-reason-audit-push → main
- **Author:** eltonaguiar
- **Created:** 2026-10-04T04:38:08Z
- **Status:** OPEN
- **Criticality:** P2 — Pick rationale preservation

---

### PR #700 — LLM free-first routing + message tracing
- **Branch:** fix/oct3-llm-discord-loud-failure → main
- **Author:** eltonaguiar
- **Created:** 2026-10-04T04:37:52Z
- **Status:** OPEN
- **Criticality:** P2 — LLM routing fix

---

### PR #696 — fix(discord): read webhooks from secrets only after exposed hook deletion
- **Branch:** fix/discord-webhook-secret-rotation → main
- **Author:** eltonaguiar
- **Created:** 2026-10-03T22:24:25Z
- **Status:** OPEN
- **Criticality:** P2 — Discord webhook security fix

---

## Merge Priority

1. **PR #786** — Fixes QA Market Validation + Sports smoke (two critically failing workflows)
2. **PR #785** — Restores audit page script tags
3. **PR #761** — FTP credentials security fix
4. **PR #760** — Fund walk-forward review fixes
5. **PR #758** — BTC evaluator fix
6. **PR #757** — Audit evidence fix
7. **PR #756** — DSR/resolver fix
8. **PR #751** — CI health monitor job

All PRs are from `eltonaguiar` and are on feature branches targeting `main`. There are no cross-repository PRs or complex merge conflicts apparent.
