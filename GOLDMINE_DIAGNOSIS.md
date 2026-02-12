# Goldmine Dashboards Empty State — Diagnosis & Action Plan

**Date:** 2026-02-12  
**Agent:** Goldmine Data Pipeline Agent  
**Status:** Root cause identified — multiple issues requiring fixes

---

## Executive Summary

The Goldmine dashboards show empty "Loading..." states due to **three root causes**:

1. **No data in `gm_unified_picks` table** — The archive workflow may not have run successfully, or source tables are empty
2. **Frontend/API field mismatches** — Dashboard expects different JSON keys than API returns
3. **Workflow schedule may be insufficient** — Archive runs only Tue-Sat at 00:00 UTC and Mon-Fri at 18:00 UTC

**Impact:** All 5 dashboards show empty states:
- `live-monitor/goldmine-dashboard.html` (Claude Goldmine)
- `investments/goldmines/antigravity/index.html` (Antigravity)
- `goldmine_cursor/index.html` (Cursor)
- `investments/goldmines/kimi/kimi-goldmine-client.html` (Kimi)
- `live-monitor/multi-dimensional.html` (6D)

---

## Root Cause Analysis

### Issue 1: Empty Database Table (`gm_unified_picks`)

**Evidence:**
- API test from investigation report: `?action=dashboard` returns `systems[]` with `closed_picks=0` for all systems
- `top_winners` and `top_losers` arrays are empty
- Dashboard shows "No systems found. Run the goldmine tracker to start collecting data."

**Possible causes:**
1. **Archive workflow hasn't run yet** — First run may not have executed
2. **Archive workflow failed silently** — Errors in archive functions (cross-DB connections, missing source tables)
3. **Source tables are empty** — `consensus_tracked`, `lm_signals`, `lm_opportunities`, etc. have no data
4. **Workflow schedule too sparse** — Only runs Tue-Sat 00:00 UTC and Mon-Fri 18:00 UTC (misses Sunday/Monday)

**Verification steps:**
```bash
# Check if workflow has run
# GitHub Actions → goldmine-tracker.yml → Check recent runs

# Check database directly (if access available)
SELECT COUNT(*) FROM gm_unified_picks;
SELECT source_system, COUNT(*) FROM gm_unified_picks GROUP BY source_system;

# Check source tables
SELECT COUNT(*) FROM consensus_tracked;
SELECT COUNT(*) FROM lm_signals;
SELECT COUNT(*) FROM lm_opportunities;
```

---

### Issue 2: Frontend/API Field Mismatches

**Evidence from `GOLDMINE_DASHBOARD_INVESTIGATION_REPORT.md`:**

| API Returns | Dashboard Expects | File:Line | Impact |
|------------|------------------|-----------|--------|
| `top_winners`, `top_losers` | `recent_winners`, `recent_losers` | goldmine-dashboard.html:870 | **Winners/Losers always empty** |
| `source_system` | `sys.name` or `sys.system` | goldmine-dashboard.html:853 | **Health cards show "Unknown"** |
| `final_return_pct` | `w.return_pct` / `l.return_pct` | goldmine-dashboard.html:978, 991 | Return % shows "--" |
| `algorithm_name` | `a.algorithm` | goldmine-dashboard.html:1210, 1237 | **Deep Dive algorithms show "--"** |
| No `win_rate` in algo rows | `a.win_rate` | goldmine-dashboard.html:1212 | **Win Rate column shows "--"** |
| `pick_date` (not `date`/`day`) | `trend[i].date` | goldmine-dashboard.html:1252 | **Daily trend chart empty** |
| `page_url` | `a.page_link` | goldmine-dashboard.html:1337 | **Failure Log links broken** |
| `threshold_value` | `a.threshold` | goldmine-dashboard.html:1330 | Threshold shows "--" |
| `is_active` (1/0) | `a.status` | goldmine-dashboard.html:1326 | Status column empty |

**Impact:** Even if data exists in the database, the dashboard won't display it correctly due to field name mismatches.

---

### Issue 3: Workflow Schedule Gaps

**Current schedule (`.github/workflows/goldmine-tracker.yml`):**
- Daily at 00:00 UTC (Tue-Sat) — misses Sunday/Monday
- Intraday at 18:00 UTC (Mon-Fri) — misses weekends

**Problem:** If the archive runs on Tuesday 00:00 UTC but source data is generated on Sunday, there's a 2-day gap. Weekend data may never be archived.

**Recommendation:** Add Sunday 00:00 UTC run or change schedule to daily.

---

## Action Plan

### Phase 1: Immediate Fixes (Get Data Flowing)

#### Step 1.1: Manually Trigger Archive Workflow
```bash
# GitHub Actions → goldmine-tracker.yml → Run workflow → workflow_dispatch
# OR call API directly:
curl "https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=archive&key=livetrader2026"
```

**Expected result:** Archive functions run and insert picks into `gm_unified_picks`. Check logs for:
- `consolidated: +X archived`
- `live_signal: +X archived`
- `edge: +X archived`
- etc.

**If errors occur:**
- Check cross-DB connections (meme, sports) — credentials may be wrong
- Check source tables exist and have data
- Review archive function error messages

#### Step 1.2: Fix Frontend Field Mismatches

**File:** `live-monitor/goldmine-dashboard.html`

**Changes needed:**

1. **Line ~870 (renderWinnersLosers):**
   ```javascript
   // OLD:
   renderWinnersLosers(data.recent_winners || [], data.recent_losers || []);
   
   // NEW:
   renderWinnersLosers(data.top_winners || [], data.top_losers || []);
   ```

2. **Line ~940 (health cards):**
   ```javascript
   // OLD:
   + '<span class="hc-name">' + (sys.name || sys.source_system || sys.system || 'Unknown') + '</span>'
   
   // NEW:
   + '<span class="hc-name">' + (sys.source_system || 'Unknown') + '</span>'
   ```

3. **Line ~1066 (winners return %):**
   ```javascript
   // OLD:
   + '<div class="li-return pos">+' + fmtNum(w.return_pct || w.final_return_pct) + '%</div>'
   
   // NEW:
   + '<div class="li-return pos">+' + fmtNum(w.final_return_pct || 0) + '%</div>'
   ```

4. **Line ~1079 (losers return %):**
   ```javascript
   // OLD:
   + '<div class="li-return neg">' + fmtNum(l.return_pct || l.final_return_pct) + '%</div>'
   
   // NEW:
   + '<div class="li-return neg">' + fmtNum(l.final_return_pct || 0) + '%</div>'
   ```

5. **Line ~1210 (algorithm name in deep dive):**
   ```javascript
   // OLD:
   '<td>' + (a.algorithm || '--') + '</td>'
   
   // NEW:
   '<td>' + (a.algorithm_name || '--') + '</td>'
   ```

6. **Line ~1212 (algorithm win rate):**
   ```javascript
   // OLD:
   '<td>' + fmtNum(a.win_rate, 1) + '%</td>'
   
   // NEW:
   '<td>' + fmtNum((a.closed > 0 ? ((a.wins / a.closed) * 100) : 0), 1) + '%</td>'
   ```

7. **Line ~1237 (recent picks algorithm):**
   ```javascript
   // OLD:
   '<td>' + (rp.algorithm || '--') + '</td>'
   
   // NEW:
   '<td>' + (rp.algorithm_name || '--') + '</td>'
   ```

8. **Line ~1252-1253 (daily trend chart):**
   ```javascript
   // OLD:
   labels.push(fmtDate(trend[i].date || trend[i].day));
   values.push(parseFloat(trend[i].win_rate || 0));
   
   // NEW:
   labels.push(fmtDate(trend[i].pick_date));
   var wins = parseInt(trend[i].wins || 0);
   var losses = parseInt(trend[i].losses || 0);
   var total = wins + losses;
   values.push(total > 0 ? ((wins / total) * 100) : 0);
   ```

9. **Line ~1330 (failure log threshold):**
   ```javascript
   // OLD:
   '<td>' + (a.threshold ? fmtNum(a.metric_value) + ' / ' + fmtNum(a.threshold) : '--') + '</td>'
   
   // NEW:
   '<td>' + (a.threshold_value ? fmtNum(a.metric_value) + ' / ' + fmtNum(a.threshold_value) : '--') + '</td>'
   ```

10. **Line ~1326 (failure log status):**
    ```javascript
    // OLD:
    '<td>' + alertStatusBadge(a.status) + '</td>'
    
    // NEW:
    '<td>' + alertStatusBadge(a.is_active == 1 ? 'active' : 'resolved') + '</td>'
    ```

11. **Line ~1337-1338 (failure log link):**
    ```javascript
    // OLD:
    var link = a.page_link || '#';
    
    // NEW:
    var link = a.page_url || '#';
    ```

**Verification:** After fixes, dashboard should display:
- System names (not "Unknown")
- Recent winners/losers with return %
- Deep dive algorithms with win rates
- Daily trend chart with dates
- Failure log with working links

---

### Phase 2: Ensure Data Pipeline Runs

#### Step 2.1: Verify Workflow Runs Successfully

**Check GitHub Actions:**
1. Go to `.github/workflows/goldmine-tracker.yml` → Actions tab
2. Review recent runs — check for failures
3. If failed, review logs for:
   - Database connection errors
   - Cross-DB connection failures (meme, sports)
   - Missing source tables
   - Archive function errors

#### Step 2.2: Fix Workflow Schedule (Optional)

**Current:** `cron: '0 0 * * 2-6'` (Tue-Sat only)

**Recommended:** Daily at 00:00 UTC
```yaml
schedule:
  - cron: '0 0 * * *'  # Daily at midnight UTC
  - cron: '0 18 * * 1-5'  # Intraday Mon-Fri
```

#### Step 2.3: Verify Source Tables Have Data

**Check each archive source:**

```sql
-- Consolidated picks
SELECT COUNT(*) FROM consensus_tracked;

-- Live signals
SELECT COUNT(*) FROM lm_signals WHERE signal_strength >= 50;

-- Edge opportunities
SELECT COUNT(*) FROM lm_opportunities;

-- Meme coins (cross-DB)
-- Check ejaguiar1_memecoin.mc_winners

-- Sports (cross-DB)
-- Check ejaguiar1_sportsbet.lm_sports_daily_picks OR stocks DB

-- Horizon picks
-- Check report_cache WHERE cache_key = 'top_picks_v3'

-- Top picks
-- Same as horizon

-- Penny stocks
-- API endpoint: /findstocks/portfolio2/api/penny_stocks.php
```

**If source tables are empty:**
- Check upstream workflows that populate them
- Verify those workflows are running
- Check for data generation errors

---

### Phase 3: Optimize & Monitor

#### Step 3.1: Add Caching for Alerts API

**Issue:** `?action=alerts` times out (from investigation report)

**Fix:** Add caching in `goldmine_tracker.php`:
```php
if ($action === 'alerts') {
    $cached = _gm_cache_get('alerts', 300);  // 5 min cache
    if ($cached) { echo json_encode($cached); exit; }
    
    // ... existing query ...
    
    $data = array('ok' => true, 'active_count' => count($rows), 'alerts' => $rows);
    _gm_cache_set('alerts', $data);
    echo json_encode($data);
    exit;
}
```

#### Step 3.2: Add Database Indexes (if missing)

**Check indexes exist:**
```sql
SHOW INDEXES FROM gm_unified_picks;
SHOW INDEXES FROM gm_failure_alerts;
```

**Add if missing:**
- `gm_unified_picks`: Already has good indexes (from schema)
- `gm_failure_alerts`: May need `idx_active_date` on `(is_active, alert_date)`

#### Step 3.3: Monitor Dashboard Health

**Add health check endpoint:**
```php
if ($action === 'health_check') {
    $stats = array(
        'total_picks' => 0,
        'systems_with_data' => 0,
        'last_archive' => null,
        'source_table_status' => array()
    );
    
    $r = $conn->query("SELECT COUNT(*) as cnt FROM gm_unified_picks");
    if ($r && ($row = $r->fetch_assoc())) {
        $stats['total_picks'] = intval($row['cnt']);
    }
    
    $r = $conn->query("SELECT COUNT(DISTINCT source_system) as cnt FROM gm_unified_picks");
    if ($r && ($row = $r->fetch_assoc())) {
        $stats['systems_with_data'] = intval($row['cnt']);
    }
    
    // Check last archive run (from cache file mtime or DB)
    // ...
    
    echo json_encode(array('ok' => true, 'health' => $stats));
    exit;
}
```

---

## Verification Checklist

After implementing fixes:

- [ ] **Archive workflow runs successfully** — Check GitHub Actions logs
- [ ] **`gm_unified_picks` has data** — `SELECT COUNT(*) FROM gm_unified_picks;` returns > 0
- [ ] **Dashboard shows systems** — Health cards display system names (not "Unknown")
- [ ] **Winners/Losers populated** — Recent Winners/Losers lists show tickers and returns
- [ ] **Deep Dive works** — System Deep Dive shows algorithms with win rates
- [ ] **Daily trend chart renders** — Chart shows dates and win rate values
- [ ] **Failure Log functional** — Links work, status badges show Active/Resolved
- [ ] **Alerts API doesn't timeout** — Caching prevents timeouts
- [ ] **All 5 dashboards work** — Test each dashboard:
  - `live-monitor/goldmine-dashboard.html`
  - `investments/goldmines/antigravity/index.html`
  - `goldmine_cursor/index.html`
  - `investments/goldmines/kimi/kimi-goldmine-client.html`
  - `live-monitor/multi-dimensional.html`

---

## Files to Modify

1. **`live-monitor/goldmine-dashboard.html`** — Fix field mismatches (11 changes)
2. **`.github/workflows/goldmine-tracker.yml`** — Optional: Fix schedule to daily
3. **`live-monitor/api/goldmine_tracker.php`** — Optional: Add alerts caching, health check endpoint

---

## Next Steps

1. **Immediate:** Manually trigger archive workflow and verify data appears
2. **Priority 1:** Fix frontend field mismatches in `goldmine-dashboard.html`
3. **Priority 2:** Verify source tables have data; fix upstream workflows if needed
4. **Priority 3:** Add caching for alerts API; optimize workflow schedule
5. **Priority 4:** Test all 5 dashboards; document any dashboard-specific issues

---

## References

- **Investigation Report:** `live-monitor/GOLDMINE_DASHBOARD_INVESTIGATION_REPORT.md`
- **API:** `live-monitor/api/goldmine_tracker.php`
- **Schema:** `live-monitor/api/goldmine_schema.php`
- **Workflow:** `.github/workflows/goldmine-tracker.yml`
- **Dashboard:** `live-monitor/goldmine-dashboard.html`

---

*End of diagnosis.*
