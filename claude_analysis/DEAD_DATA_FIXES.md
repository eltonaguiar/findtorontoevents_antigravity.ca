# Dead Data & Staleness Fixes

> Generated: 2026-02-10 by Claude Analysis
> Status: Ready to apply -- each fix includes the exact file, line, old text, and replacement.

---

## ISSUE 1: Stats Page Hardcoded Date Checks (MEDIUM)

Three stats pages use `>= '2025-01-01'` to check data freshness. This should be dynamic
(compute "1 year ago" at runtime) so it never goes stale again.

### File 1: `findmutualfunds2/portfolio2/stats/index.html` (lines 215-216)

**Current:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= '2025-01-01', 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['NAV Freshness', s.nav_date_range && s.nav_date_range.latest >= '2025-01-01', 'Latest: ' + (s.nav_date_range ? s.nav_date_range.latest : 'N/A')],
```

**Replace with:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['NAV Freshness', s.nav_date_range && s.nav_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.nav_date_range ? s.nav_date_range.latest : 'N/A')],
```

### File 2: `findforex2/portfolio/stats/index.html` (lines 228-229)

**Current:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= '2025-01-01', 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['Price Freshness', s.price_date_range && s.price_date_range.latest >= '2025-01-01', 'Latest: ' + (s.price_date_range ? s.price_date_range.latest : 'N/A')],
```

**Replace with:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['Price Freshness', s.price_date_range && s.price_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.price_date_range ? s.price_date_range.latest : 'N/A')],
```

### File 3: `findcryptopairs/portfolio/stats/index.html` (lines 223-224)

**Current:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= '2025-01-01', 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['Price Freshness', s.price_date_range && s.price_date_range.latest >= '2025-01-01', 'Latest: ' + (s.price_date_range ? s.price_date_range.latest : 'N/A')],
```

**Replace with:**
```js
['Pick Freshness', s.pick_date_range && s.pick_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.pick_date_range ? s.pick_date_range.latest : 'N/A')],
['Price Freshness', s.price_date_range && s.price_date_range.latest >= new Date(Date.now()-365*86400000).toISOString().slice(0,10), 'Latest: ' + (s.price_date_range ? s.price_date_range.latest : 'N/A')],
```

---

## ISSUE 2: miracle2_data.json -- All 50 Picks Pending (HIGH)

**File:** `miracle2_data.json`
**Problem:** Created 2026-02-09 18:51:10 -- all 50 picks show `pending: 50, resolved: 0`.
**Root cause:** The `daily-miracle-scan.yml` workflow calls
`https://findtorontoevents.ca/findstocks2_global/api/daily_scan2.php?key=miracle2026`
which generates picks but the **resolution step** (comparing entry_price vs current price
to determine win/loss) may not be running, or these picks are simply too new (< 24h old).

**Action items:**
1. Check GitHub Actions run history for `daily-miracle-scan.yml` -- look for failures
2. Check if `daily_scan2.php` has a separate `?action=resolve` endpoint that needs to be called
3. If picks older than 1 trading day remain pending, the resolve pipeline is broken
4. Consider adding a dedicated resolve step to the workflow YAML

**To check (run manually):**
```bash
gh run list --workflow=daily-miracle-scan.yml --limit=5
```

---

## ISSUE 3: Edge History Price Gaps (MEDIUM)

**Files:** `edge_history2.json`, `edge_history3.json`
**Problem:** 70 picks in each file all show `latest_price: 0` and `price_date: ""`.
All picks are dated 2026-02-09 (Sunday) -- markets were closed, so the price fetch
likely found no data for that date.

**Root cause:** The edge scan ran on a weekend. The `latest_price` fetch uses the
pick_date to look up closing prices, but there is no market data for weekends.

**Fix:** The price lookup logic (in the PHP API that generates these files) should
fall back to the most recent trading day's close when the pick_date is a weekend or holiday.
This is a server-side fix in the edge_finder.php API.

**Workaround:** The next weekday scan (Monday Feb 10) should populate prices correctly.
Verify by checking `edge_history2.json` after the Monday workflow runs.

---

## ISSUE 4: Copyright Date (LOW)

**File:** `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/index.html` (line 599)

**Current:**
```html
© 2024 MovieShows v2.0 Enterprise Platform | 126/400 Updates Complete (31.5%)
```

**Replace with:**
```html
© 2026 MovieShows v2.0 Enterprise Platform | 126/400 Updates Complete (31.5%)
```

---

## ISSUE 5: Mutual Funds v1 Status (INVESTIGATE)

**Directory:** `findmutualfunds/` (v1)
**Question:** Is v1 still active or has v2 (`findmutualfunds2/`) fully replaced it?

**Evidence:**
- The `daily-mutualfund-refresh.yml` workflow refreshes v1 (`findmutualfunds/api/daily_refresh.php`)
- v1 has 10 PHP API files, all still present
- v2 has its own separate API directory
- Both are linked from `index.html`

**Recommendation:** v1 appears alive. Keep both, but add a "v2 available" banner to v1 pages
directing users to the enhanced version. If v1 traffic is zero, consider deprecating.

---

## Summary

| # | Issue | Severity | Auto-fixable? | Status |
|---|-------|----------|---------------|--------|
| 1 | Stats page hardcoded dates | MEDIUM | Yes -- search-replace | Patch ready |
| 2 | miracle2 all pending | HIGH | Needs workflow investigation | Manual check needed |
| 3 | Edge history price=0 | MEDIUM | Self-healing on weekday | Monitor Monday |
| 4 | Copyright 2024 | LOW | Yes -- search-replace | Patch ready |
| 5 | Mutual funds v1 | LOW | N/A -- investigation | Likely alive |
