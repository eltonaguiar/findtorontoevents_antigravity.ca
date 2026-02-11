# Goldmine Dashboard Investigation Report

**Page:** https://findtorontoevents.ca/live-monitor/goldmine-dashboard.html  
**Date:** 2026-02-10  
**Scope:** Live HTML, local files, API endpoints, PHP 5.2, GitHub Actions.

---

## 1. Summary

The Goldmine dashboard loads and displays data from a single API: `goldmine_tracker.php`. Several **API–frontend field mismatches** cause empty or wrong data (winners/losers, system names, deep-dive charts, failure log links/metrics). The **Fundamentals** tab is **placeholder-only** (SEC EDGAR, 13F, Sentiment) and does not call any API. The **alerts** API was observed to **time out** on one fetch. All referenced PHP files pass the **PHP 5.2** validator. One **GitHub Actions** workflow exists for the goldmine tracker.

---

## 2. Dummy / Placeholder Data

### 2.1 Visible on live page

| Location | Content | Type |
|----------|--------|------|
| Overview | "Loading system health..." | Initial state; replaced when API succeeds |
| Overview | "Loading..." in Recent Winners / Recent Losers | Replaced when API succeeds; **stays "No recent winners yet" / "No recent losers yet"** due to bug §3.1 |
| All Picks table | "Loading picks..." | Replaced when API succeeds |
| System Deep Dive | "Select a system above to view detailed analytics." | Placeholder until a system is selected |
| **Fundamentals → Insider Activity** | "SEC EDGAR data loading... This section will display insider cluster buy alerts from SEC Form 4 filings **once sec_edgar.php is deployed**." | **Static placeholder** — no API call |
| **Fundamentals → Fund Holdings** | "13F new position data loading... This section will show newly opened fund positions from 13F filings **once the data pipeline is deployed**." | **Static placeholder** — no API call |
| **Fundamentals → Sentiment** | "News sentiment scores loading... This section will display aggregated sentiment analysis from financial news sources **once news_sentiment.php is deployed**." | **Static placeholder** — no API call |
| Failure Log | "Loading alerts..." | Replaced when API succeeds |

### 2.2 No lorem ipsum or hardcoded fake numbers

- No "TODO", lorem ipsum, or obviously fake numbers were found in the dashboard or alerts HTML or in the API responses sampled.

### 2.3 "Loading..." that never resolves

- If the **dashboard** or **alerts** API fails (e.g. timeout, 5xx), the UI shows "Failed to load dashboard data" or "Failed to load alerts" — it does not spin forever.
- **Winners/Losers** effectively never show real data because of the bug in §3.1 (wrong response keys).

---

## 3. JavaScript / API Issues

### 3.1 Dashboard API response keys vs frontend (critical)

The dashboard calls `goldmine_tracker.php` with:

- `?action=dashboard` — overview, health cards, winners, losers, systems
- `?action=alerts` — alert banner and Failure Log table
- `?action=picks&page=...&limit=50` — All Picks table (with optional filters)
- `?action=system_detail&system=...` — System Deep Dive (KPIs, chart, algorithms, recent picks)

**Mismatches:**

| API returns (goldmine_tracker.php) | Dashboard expects (goldmine-dashboard.html) | File:Line | Effect |
|-----------------------------------|--------------------------------------------|-----------|--------|
| `top_winners`, `top_losers` | `recent_winners`, `recent_losers` | goldmine-dashboard.html:870 | **Recent Winners/Losers lists are always empty**; UI shows "No recent winners yet" / "No recent losers yet" even when API has data. |
| `source_system` (e.g. "consolidated") | `sys.name` or `sys.system` | goldmine-dashboard.html:853 | **Health cards show "Unknown"** for every system name. |
| `final_return_pct` (in top_winners/top_losers) | `w.return_pct` / `l.return_pct` | goldmine-dashboard.html:978, 991 | If keys were fixed, return % would still show "--" unless frontend also uses `final_return_pct`. |
| (system_detail) `algorithm_name` | `a.algorithm` / `rp.algorithm` | goldmine-dashboard.html:1210, 1237 | **Deep Dive "Top Algorithms" and "Recent 20 Picks" show "--"** for algorithm column. |
| (system_detail) Algo rows: `picks`, `wins`, `losses`, no `win_rate` | `a.win_rate` | goldmine-dashboard.html:1212 | **Deep Dive Top Algorithms Win Rate column shows "--".** |
| (system_detail) `daily_trend`: `pick_date`, `picks`, `wins`, `losses` (no `win_rate`, no `date`/`day`) | `trend[i].date` or `trend[i].day`, `trend[i].win_rate` | goldmine-dashboard.html:1252–1253 | **Daily Win Rate Trend chart** gets wrong labels (empty or wrong) and **all zeros** for values. |
| (alerts) `page_url` | `a.page_link` | goldmine-dashboard.html:1337–1338 | **Failure Log "View" link never uses API link**; always falls back to "Details" (goldmine-alerts.html). |
| (alerts) `threshold_value` | `a.threshold` | goldmine-dashboard.html:1330 | **Metric/Threshold column** may show "--" instead of "value / threshold". |
| (alerts) Table has `is_active` (1/0), no `status` | `a.status` for Active/Resolved badge | goldmine-dashboard.html:1326, 1356 | **Failure Log Status column** is empty; alerts are only active (API filters `is_active = 1`). |

**Recommended fixes:**

- **Option A (frontend):** In `goldmine-dashboard.html`, use: `data.top_winners`/`data.top_losers`; `sys.source_system` (or a display name map); `w.final_return_pct`/`l.final_return_pct`; `a.algorithm_name`/`rp.algorithm_name`; compute `win_rate` from `wins`/`losses` for algos; for `daily_trend` use `trend[i].pick_date` and compute `win_rate = (wins/(wins+losses))*100`; use `a.page_url`, `a.threshold_value`, and derive status from `a.is_active`.
- **Option B (API):** Add/alias in API: `recent_winners`/`recent_losers`, `name` (from source_system), `return_pct` (alias final_return_pct), `algorithm` (alias algorithm_name), `win_rate` for algos and daily_trend, `page_link` (alias page_url), `threshold` (alias threshold_value), `status` (e.g. `is_active ? 'active' : 'resolved'`).

Either option (or a mix) will resolve the empty/wrong data and links.

---

### 3.2 Alerts API timeout

- **Observed:** `https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=alerts` was fetched during the investigation and **timed out** (fetch tool reported timeout).
- **Impact:** Alert banner and Failure Log tab can show "Failed to load alerts" or keep "Loading alerts..." until timeout. goldmine-alerts.html would also fail to load its data.
- **Suggestion:** Check server/database response time for `gm_failure_alerts` query and add indexing or caching if needed; consider a shorter timeout and clear error message on the frontend.

---

### 3.3 APIs the page uses

| Endpoint | Purpose |
|---------|--------|
| `GET /live-monitor/api/goldmine_tracker.php?action=dashboard` | Overview: systems, health, winners, losers, active alert count. |
| `GET /live-monitor/api/goldmine_tracker.php?action=alerts` | Alert banner (active alerts), Failure Log table. |
| `GET /live-monitor/api/goldmine_tracker.php?action=picks&page=1&limit=50&system=&asset=&status=&ticker=` | All Picks table (paginated, filterable). |
| `GET /live-monitor/api/goldmine_tracker.php?action=system_detail&system=<name>` | System Deep Dive: stats, algorithms, recent picks, daily trend. |

**Not used by the dashboard:**

- `sec_edgar.php` — Fundamentals tab text says "once sec_edgar.php is deployed" but the dashboard does not call it.
- `news_sentiment.php` — Same for sentiment; no call from the dashboard.
- No dedicated 13F API is called; Fundamentals is static placeholder.

---

### 3.4 API test results (live)

| Endpoint | Result |
|----------|--------|
| `?action=dashboard` | **200 OK.** Returns `systems[]`, `active_alerts`, `top_winners`, `top_losers`, `generated_at`. All systems have `closed_picks=0`, so win_rate is 0; winners/losers arrays empty. |
| `?action=alerts` | **Timeout** during one fetch. When it works, returns `ok`, `active_count`, `alerts[]`. |
| `?action=picks&page=1&limit=10` | **200 OK.** Returns paginated picks; `current_price` and related fields are 0 for open picks (expected until outcomes are updated). |

---

## 4. Local Files Reviewed

| File | Purpose |
|------|--------|
| `live-monitor/goldmine-dashboard.html` | Main dashboard; single inline script; uses relative API path `/live-monitor/api/goldmine_tracker.php`. |
| `live-monitor/goldmine-alerts.html` | Alerts page; calls `goldmine_tracker.php?action=alerts`; has KPIs and suggested actions. |
| `live-monitor/api/goldmine_tracker.php` | Main API: schema, archive, update_outcomes, check_health, dashboard, picks, system_detail, alerts, etc. |
| `live-monitor/api/goldmine_schema.php` | Defines 6 tables: gm_unified_picks, gm_system_health, gm_failure_alerts, gm_sec_insider_trades, gm_sec_13f_holdings, gm_news_sentiment. |
| `live-monitor/api/sec_edgar.php` | SEC EDGAR fetcher (insider/13F); exists and is PHP 5.2 safe; **not called by dashboard**. |
| `live-monitor/api/news_sentiment.php` | Finnhub sentiment; exists and is PHP 5.2 safe; **not called by dashboard**. |

---

## 5. PHP 5.2 Compliance

**Validator:** `python tools/validate_php52.py` (project rule: php52-syntax-check.mdc)

**Files checked:**  
`live-monitor/api/goldmine_tracker.php`, `live-monitor/api/goldmine_schema.php`, `live-monitor/api/sec_edgar.php`, `live-monitor/api/news_sentiment.php`

**Result:** **OK — 4 files checked, all PHP 5.2 compatible.**

- No `[]` arrays, `?:`, `??`, closures, `__DIR__`, or other disallowed constructs reported.

---

## 6. GitHub Actions

**Path:** `.github/workflows/goldmine-tracker.yml`

**Purpose:** Goldmine Tracker — Archive, Outcomes & Health Check.

**Triggers:**

- Schedule: daily 00:00 UTC (Tue–Sat), and 18:00 UTC (Mon–Fri).
- Manual: `workflow_dispatch`.

**Steps:**

1. Ensure schema: `GET goldmine_tracker.php?action=schema`
2. Archive picks: `GET goldmine_tracker.php?action=archive&key=livetrader2026`
3. Update outcomes: `GET goldmine_tracker.php?action=update_outcomes&key=livetrader2026`
4. Check health: `GET goldmine_tracker.php?action=check_health&key=livetrader2026`
5. Fetch news sentiment: `GET news_sentiment.php?action=fetch&key=livetrader2026` (continue-on-error)
6. Dashboard summary: `GET goldmine_tracker.php?action=dashboard` (continue-on-error)

No other workflows reference "goldmine" under `.github/workflows/`.

---

## 7. Issue Checklist (for fixes)

- [ ] **Dashboard:** Use `top_winners` / `top_losers` (and `final_return_pct`) so Recent Winners/Losers show data.
- [ ] **Dashboard:** Use `source_system` (or mapped name) for health card titles so systems are not "Unknown".
- [ ] **Dashboard:** Use `algorithm_name` and computed `win_rate` for System Deep Dive algos and recent picks.
- [ ] **Dashboard:** Use `pick_date` and computed daily `win_rate` for Daily Win Rate Trend chart.
- [ ] **Dashboard:** Use `page_url`, `threshold_value`, and `is_active` (as status) for Failure Log.
- [ ] **Alerts API:** Investigate and fix timeout on `?action=alerts` (and/or add caching/indexing).
- [ ] **Fundamentals:** Either wire SEC EDGAR / 13F / news_sentiment into the dashboard or update copy to say "Coming soon" / remove "loading" wording.

---

## 8. Exact File and Line References

| Issue | File | Line(s) |
|-------|------|--------|
| Winners/losers use wrong keys | live-monitor/goldmine-dashboard.html | 870 |
| Winners/losers use return_pct | live-monitor/goldmine-dashboard.html | 978, 991 |
| System name uses name/system | live-monitor/goldmine-dashboard.html | 853 |
| Algo table uses algorithm | live-monitor/goldmine-dashboard.html | 1210, 1237 |
| Algo win_rate | live-monitor/goldmine-dashboard.html | 1212 |
| Daily trend date/win_rate | live-monitor/goldmine-dashboard.html | 1252–1253 |
| Failure log page_link | live-monitor/goldmine-dashboard.html | 1337–1338 |
| Failure log threshold | live-monitor/goldmine-dashboard.html | 1330 |
| Failure log status (is_active) | live-monitor/goldmine-dashboard.html | 1326, 1356 |
| API returns top_winners/top_losers | live-monitor/api/goldmine_tracker.php | 179–196 |
| API system_detail algorithms/recent_picks/daily_trend shape | live-monitor/api/goldmine_tracker.php | 261–299 |
| gm_failure_alerts schema (page_url, threshold_value, is_active) | live-monitor/api/goldmine_schema.php | 88–106 |
| Fundamentals placeholders | live-monitor/goldmine-dashboard.html | 451–462 |
| GitHub Actions workflow | .github/workflows/goldmine-tracker.yml | (entire file) |

---

*End of report.*
