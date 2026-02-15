# Empty Database Tables - Investigation & GitHub Actions Enhancement Plan

## Executive Summary

Based on comprehensive investigation of the database, codebase, and GitHub Actions workflows, I've identified **6 empty tables** with different root causes. This document provides detailed findings and a concrete action plan to fix these issues through GitHub Actions enhancements.

---

## 📊 Empty Tables Analysis

### Priority 1: CRITICAL - Broken/Missing Implementation

#### 1. `favcreatorslogs` - NO WRITE OPERATION EXISTS ❌

**Status**: Schema exists, read API exists, but **NO INSERT anywhere**

**Evidence**:
- Schema defined in `favcreators/public/api/db_schema.php` (lines 61-77)
- Read endpoint `get_logs.php` exists and works
- **NO INSERT statements found in any PHP files**

**Root Cause**: 
Logging was planned but never implemented. The table was created for audit logging but no code actually writes to it.

**Files That SHOULD Write Here**:
- `login.php` - Login attempts
- `save_creators.php` - Creator save operations  
- `save_note.php` - Note updates
- `save_link_list.php` - Link list operations
- `update_streamer_last_seen.php` - Already writes to different log table

---

### Priority 2: HIGH - GitHub Actions Not Working

#### 2. `streamer_last_seen` & 3. `streamer_check_log` - Empty Despite Full Implementation

**Status**: Full CRUD exists, GitHub Actions configured, but tables empty

**Evidence**:
- Write API: `update_streamer_last_seen.php` - Full INSERT/UPDATE ✅
- Read API: `get_streamer_last_seen.php` - Full SELECT ✅
- Delete API: `cleanup_streamer_last_seen.php` - Cleanup exists ✅
- GitHub Actions: `.github/workflows/check-streamer-status.yml` - Runs every 5 min ✅
- Python Script: `.github/scripts/check_streamer_status.py` - Complete implementation ✅

**Current GitHub Actions Config**:
```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes
env:
  FC_API_BASE: 'https://findtorontoevents.ca/fc'
  FC_CHECKER_EMAIL: 'github-actions@findtorontoevents.ca'
```

**Likely Root Causes**:
1. **Workflow disabled** in GitHub repository settings
2. **API authentication failing** - The endpoint may require auth that's not provided
3. **ModSecurity blocking** - Server firewall may be blocking GitHub Actions IP ranges
4. **API base URL incorrect** - Should verify `https://findtorontoevents.ca/fc` is correct

---

### Priority 3: MEDIUM - Unused Features

#### 4. `user_link_lists` - Feature Exists But Frontend Not Using

**Status**: Full CRUD exists, auto_increment=2 suggests failed INSERT

**Evidence**:
- SQL export shows: `AUTO_INCREMENT=2` (INSERT was attempted)
- No row with ID=1 exists (transaction rolled back or deleted)
- Full API: `save_link_list.php`, `get_link_lists.php`, `delete_link_list.php`

**Root Cause**: API exists but frontend feature may not be calling it, or there was a DB error during early testing.

#### 5. `user_content_preferences` - Orphaned Table

**Status**: Schema exists, NO API endpoints

**Evidence**:
- Table defined in `db_schema.php`
- **NO PHP files reference this table**
- Truly orphaned with no read/write implementation

#### 6. `streamer_content` - Schema Only

**Status**: Defined but never implemented

**Evidence**:
- Defined in `streamer_last_seen_schema.php`
- No INSERT operations
- No API endpoints
- Likely planned for content caching that was never built

---

## 🔧 GitHub Actions Enhancement Plan

### Phase 1: Fix Streamer Tables (Priority: HIGH)

#### Action 1.1: Debug & Fix Existing Workflow

Create a diagnostic workflow to identify why the current streamer check isn't populating tables:

```yaml
# .github/workflows/debug-streamer-check.yml
name: Debug Streamer Check

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  diagnose:
    runs-on: ubuntu-latest
    steps:
      - name: Test API Connectivity
        run: |
          echo "=== Testing API Endpoints ==="
          
          # Test 1: Check if API is reachable
          curl -sf --max-time 30 \
            "https://findtorontoevents.ca/fc/api/ping.php" \
            -H "User-Agent: GitHub-Actions-Diagnostic/1.0" || echo "PING FAILED"
          
          # Test 2: Try to get streamers list (read-only, should work)
          curl -sf --max-time 30 \
            "https://findtorontoevents.ca/fc/api/get_all_streamers_to_check.php?limit=5" \
            -H "User-Agent: GitHub-Actions-Diagnostic/1.0" | head -c 500
          
          # Test 3: Check if tables exist by querying public endpoint
          curl -sf --max-time 30 \
            "https://findtorontoevents.ca/fc/api/get_streamer_last_seen_public.php" | head -c 500
```

#### Action 1.2: Enhance Streamer Check with Better Logging

Update `.github/scripts/check_streamer_status.py` to provide better diagnostics:

```python
# Add to the beginning of main():
def verify_api_endpoints():
    """Verify all required API endpoints are accessible."""
    endpoints = [
        (f"{API_BASE}/api/ping.php", "GET", "Ping"),
        (f"{API_BASE}/api/get_all_streamers_to_check.php?limit=1", "GET", "Get Streamers"),
    ]
    
    for url, method, name in endpoints:
        try:
            if method == "GET":
                result = _http_get(url, timeout=10)
                log_message(f"{name}: HTTP {result['status']}")
        except Exception as e:
            log_message(f"{name}: FAILED - {str(e)}")

# Call at start of main()
verify_api_endpoints()
```

#### Action 1.3: Add Direct Database Population Fallback

If API calls fail, add direct MySQL connection as fallback:

```yaml
# .github/workflows/populate-streamer-tables.yml
name: Populate Streamer Tables (Direct DB)

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */12 * * *'  # Twice daily as fallback

jobs:
  populate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: pip install pymysql
        
      - name: Populate from guest list
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASS: ${{ secrets.DB_PASS }}
          DB_NAME: ${{ secrets.DB_NAME }}
        run: python .github/scripts/populate_streamer_tables.py
```

---

### Phase 2: Implement favcreatorslogs (Priority: CRITICAL)

#### Action 2.1: Create Logging Helper Function

Create `favcreators/public/api/log_action.php`:

```php
<?php
/**
 * Centralized logging function for favcreatorslogs table
 * Include this file and call log_action() to write logs
 */

function log_action($action, $endpoint, $user_id = null, $user_email = null, 
                    $status = 'success', $message = '', $payload_summary = '', 
                    $error_details = '') {
    
    require_once dirname(__FILE__) . '/db_connect.php';
    
    // Get client IP
    $user_ip = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    
    // Ensure table exists
    $conn->query("CREATE TABLE IF NOT EXISTS favcreatorslogs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(64) NOT NULL,
        endpoint VARCHAR(128),
        user_id INT,
        user_email VARCHAR(255),
        user_ip VARCHAR(45),
        status VARCHAR(16) NOT NULL,
        message TEXT,
        payload_summary TEXT,
        error_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_email (user_email),
        INDEX idx_action (action),
        INDEX idx_created_at (created_at),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    
    // Insert log
    $stmt = $conn->prepare("INSERT INTO favcreatorslogs 
        (action, endpoint, user_id, user_email, user_ip, status, message, payload_summary, error_details) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    $stmt->bind_param("ssissssss", 
        $action, $endpoint, $user_id, $user_email, 
        $user_ip, $status, $message, $payload_summary, $error_details
    );
    
    $result = $stmt->execute();
    $stmt->close();
    $conn->close();
    
    return $result;
}
?>
```

#### Action 2.2: Add Logging to Key Endpoints

Modify these files to include logging:

**login.php** - Add after successful/failed login:
```php
require_once 'log_action.php';
log_action('user_login', 'login.php', $user_id, $email, 
    $success ? 'success' : 'error', 
    $success ? 'Login successful' : 'Login failed: ' . $error);
```

**save_creators.php** - Add after save operation:
```php
require_once 'log_action.php';
log_action('save_creators', 'save_creators.php', $user_id, $user_email,
    $success ? 'success' : 'error',
    'Saved ' . count($creators) . ' creators');
```

**save_note.php** - Add after note save:
```php
require_once 'log_action.php';
log_action('save_note', 'save_note.php', $user_id, null,
    'success', 'Note updated for creator: ' . $creator_id);
```

#### Action 2.3: GitHub Actions to Verify Logging

```yaml
# .github/workflows/verify-favcreators-logs.yml
name: Verify favcreatorslogs Population

on:
  workflow_dispatch:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Check log count
        run: |
          RESP=$(curl -sf --max-time 30 \
            "https://findtorontoevents.ca/fc/api/get_logs.php?limit=1" || echo '{"total":0}')
          TOTAL=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))")
          echo "Total log entries: $TOTAL"
          
          if [ "$TOTAL" -eq 0 ]; then
            echo "WARNING: favcreatorslogs table is empty!"
            exit 1
          fi
```

---

### Phase 3: Cleanup & Monitoring (Priority: MEDIUM)

#### Action 3.1: Database Health Monitor Enhancement

The existing `data-pipeline-master.yml` already includes DB health checks. Enhance it to specifically track empty tables:

```yaml
# Add to data-pipeline-master.yml -> db-health job:

- name: Check specific empty tables
  run: |
    echo "=== Empty Table Check ==="
    
    # Check favcreatorslogs
    LOGS=$(curl -sf --max-time 30 \
      "https://findtorontoevents.ca/fc/api/get_logs.php?limit=1" | \
      python3 -c "import json,sys; print(json.load(sys.stdin).get('total',0))" || echo "0")
    echo "favcreatorslogs: $LOGS rows"
    
    # Check streamer_last_seen
    STREAMERS=$(curl -sf --max-time 30 \
      "https://findtorontoevents.ca/fc/api/get_streamer_last_seen_public.php?limit=1" | \
      python3 -c "import json,sys; print(len(json.load(sys.stdin).get('streamers',[])))" || echo "0")
    echo "streamer_last_seen: $STREAMERS entries"
    
    # Alert if empty
    if [ "$LOGS" -eq 0 ] || [ "$STREAMERS" -eq 0 ]; then
      echo "ALERT: Critical tables are empty!"
      # Could send notification here
    fi
```

#### Action 3.2: Create Table Cleanup Workflow

For truly unused tables (`user_content_preferences`, `streamer_content`):

```yaml
# .github/workflows/cleanup-unused-tables.yml
name: Cleanup Unused Tables

on:
  workflow_dispatch:  # Manual only for safety

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: List potentially unused tables
        run: |
          echo "Tables with no recent activity:"
          echo "- user_content_preferences (no API endpoints)"
          echo "- streamer_content (schema only)"
          echo ""
          echo "Run with caution - verify no code references these tables!"
```

---

## 📋 Implementation Checklist

### Week 1: Critical Fixes
- [ ] Create `debug-streamer-check.yml` workflow to diagnose API issues
- [ ] Test streamer API endpoints from GitHub Actions
- [ ] Fix any authentication/mod_security issues
- [ ] Verify streamer tables start populating

### Week 2: favcreatorslogs Implementation
- [ ] Create `log_action.php` helper
- [ ] Add logging to `login.php`
- [ ] Add logging to `save_creators.php`
- [ ] Add logging to `save_note.php`
- [ ] Create verification workflow

### Week 3: Monitoring & Cleanup
- [ ] Enhance `data-pipeline-master.yml` with specific empty table checks
- [ ] Create alerts for empty critical tables
- [ ] Document unused tables for potential cleanup
- [ ] Create PR with all changes

---

## 🔍 Debugging Commands

### Local Testing
```bash
# Test streamer API locally
curl -X POST https://findtorontoevents.ca/fc/api/update_streamer_last_seen.php \
  -H "Content-Type: application/json" \
  -d '{"creator_id":"test","creator_name":"Test","platform":"tiktok","username":"test","is_live":false}'

# Check logs
curl "https://findtorontoevents.ca/fc/api/get_logs.php?limit=5"

# Check streamer status
curl "https://findtorontoevents.ca/fc/api/get_streamer_last_seen_public.php?limit=5"
```

### GitHub Actions Debugging
```bash
# Check workflow runs
gh run list --workflow=check-streamer-status.yml --limit 5

# View latest run logs
gh run view --job=check-streamers --log
```

---

## 📈 Success Metrics

After implementing these enhancements:

1. **streamer_last_seen**: Should have >0 rows within 1 hour of fixing
2. **streamer_check_log**: Should accumulate rows with each GitHub Actions run
3. **favcreatorslogs**: Should start capturing login/save events immediately
4. **All empty tables**: Should be monitored daily with alerts if they stay empty

---

## 🚨 Risk Mitigation

1. **Backup before changes**: Always backup database before schema changes
2. **Test in staging**: Test all new workflows in staging environment first
3. **Gradual rollout**: Deploy logging changes to one endpoint at a time
4. **Monitor errors**: Watch for increased error rates after deployment
5. **Rollback plan**: Keep previous versions ready for quick rollback

---

*Generated: February 15, 2026*
*Based on: EMPTY_TABLES_INVESTIGATION_REPORT.md and codebase analysis*
