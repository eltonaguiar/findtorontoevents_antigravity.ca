# Audit console fixes — dashboard_freshness 404, KuCoin CORS, init dedupe

**Date:** 2026-06-06  
**Goal #1 surface:** `/audit/` main dashboard

## Symptoms (browser console)

1. `dashboard_freshness.js` → **404** (script tag present, file never FTP-deployed)
2. KuCoin candle fetch for `HYPE-USDT` → **CORS blocked** (`api.kucoin.com` has no `Access-Control-Allow-Origin`)
3. `[Dashboard Enhancements] Loaded` logged **3–4×** per page load
4. Top-10 Rank Backtest — EQUITY panel could **flicker/disappear** on re-init race

## Root causes

| Issue | Cause |
|-------|-------|
| freshness 404 | `dashboard_freshness.js` committed locally + referenced in `template.html`, but missing from `audit-dashboard.yml` FTP JS glob and `deploy_audit_files.py` |
| KuCoin CORS | Client-side direct `fetch(kuUrl)` — KuCoin does not allow browser origins |
| 4× init log | `loadExternalDashboardDataIfFresher()` dispatched `dashboard-data-loaded` twice (mid-branch + always at end); enhancements listener re-ran full teardown immediately |
| Top-N flicker | Async `renderTopNRankBacktest()` raced with rapid re-inits; section removed while fetch in flight |

## Changes

### Deploy path
- `.github/workflows/audit-dashboard.yml` — add `dashboard_freshness.js` to all three FTP JS upload loops
- `tools/deploy_audit_files.py` — add `dashboard_freshness.js`, `dashboard_enhancements.js`, `validation_metrics.js` under `audit_js` tag

### template.html
- KuCoin OHLCV: route through `api.allorigins.win/raw?url=` (same pattern as Binance fallback)
- Remove duplicate `dashboard-data-loaded` dispatch inside the external-data branch (keep single fire at function end)
- Add `<div id="enhancements-host"></div>` inside `#tab-overview` for stable panel mount point

### dashboard_enhancements.js
- Debounce `dashboard-data-loaded` refresh (250ms)
- Generation guard on `renderTopNRankBacktest()` to drop stale async completions
- Append panels to `#enhancements-host` instead of `body.firstChild`

## Verification

```bash
# Local syntax
python3 -c "import py_compile; py_compile.compile('tools/deploy_audit_files.py', doraise=True)"

# Deploy (requires FTP_USER/FTP_PASS)
python3 tools/deploy_audit_files.py --only audit_js

# Remote HEAD check
curl -sI 'https://findtorontoevents.ca/audit/dashboard_freshness.js?_=$(date +%s)' | head -3
```

After deploy, reload `/audit/` with cache disabled:
- No 404 on `dashboard_freshness.js`
- No KuCoin CORS errors for HYPE-USDT sparklines
- `[Dashboard Enhancements] Loaded` should appear **twice max** (initial + one post-JSON refresh)

## Wording audit (Copilot triage — 2026-06-06)

**Copilot was correct:** `/audit/` has no React hydration; wording changes are vanilla JS replacing static HTML.

**Copilot was wrong:** `"Top-10 Rank Backtest — EQUITY"` is **not** the Decile Test Results panel. It is injected by `dashboard_enhancements.js` → `renderTopNRankBacktest()` from `data/top_n_rank_backtest.json`. Playwright test 4 confirms it persists after networkidle on live.

**Major Goal banner fix:** JS now caches static forensic HTML in `data-mg-static` and wraps it in a collapsible `<details>` instead of discarding INCIDENT refs / per-symbol breakdowns.

**Playwright:** `tests/audit_wording_audit.spec.ts` — run with `npx playwright test tests/audit_wording_audit.spec.ts --project="Desktop Chrome"`.